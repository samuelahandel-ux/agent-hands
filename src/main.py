"""
AgentHands - Agent-to-Agent Task Marketplace
Main FastAPI application
"""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pathlib
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import time
import os
from collections import defaultdict
from pydantic import BaseModel, Field
from typing import Optional

from .models import (
    TaskSubmission, TaskResponse, TaskStatus,
    AccountCreate, AccountResponse, Account,
    CapabilitiesResponse, Capability,
    ErrorResponse
)
from .database import Database
from .queue import TaskQueue, PersistentTaskQueue
from .executor import TaskExecutor
from .payment import PaymentVerifier, ManualDepositHandler
from .auth import verify_api_key, create_account, MASTER_DEPOSIT_ADDRESS
from .capabilities import CAPABILITIES
import logging
import uuid as uuid_module

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger("agenthands")

# Initialize components
db = Database()
queue = PersistentTaskQueue()  # Use persistent queue for production
executor = TaskExecutor()
payment = PaymentVerifier()
deposit_handler: ManualDepositHandler = None  # Initialized in lifespan

# Simple in-memory rate limiter with bounded size
rate_limit_store: dict = defaultdict(list)
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds
MAX_RATE_LIMIT_ENTRIES = 10000  # Prevent memory exhaustion


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global deposit_handler
    
    # Startup
    logger.info("Starting AgentHands API...")
    
    # SECURITY: Check Docker sandbox availability
    from .sandbox import get_code_sandbox
    sandbox = get_code_sandbox()
    docker_available = await sandbox.is_available()
    
    if not docker_available:
        allow_unsafe = os.environ.get("AGENTHANDS_ALLOW_UNSAFE_FALLBACK", "").lower() == "true"
        if allow_unsafe:
            logger.critical(
                "⚠️  SECURITY WARNING: Docker unavailable and AGENTHANDS_ALLOW_UNSAFE_FALLBACK=true. "
                "Code execution will run UNSANDBOXED on the host system! "
                "DO NOT USE IN PRODUCTION!"
            )
            print("⚠️  WARNING: Running in UNSAFE mode - code execution is NOT sandboxed!")
        else:
            logger.warning(
                "Docker sandbox unavailable. Code execution capability (code.execute) will be disabled. "
                "Install Docker and build sandbox image: docker build -t agenthands-sandbox:latest -f Dockerfile.sandbox ."
            )
            print("⚠️  Docker unavailable - code execution disabled (safe mode)")
    else:
        logger.info("Docker sandbox available - code execution enabled securely")
        print("🔒 Docker sandbox available - secure mode")
    
    await db.init()
    
    # Wire up persistent queue with database
    queue.set_database(db)
    await queue.start()
    
    # Wire up dependencies for executor
    executor.set_dependencies(db, queue)
    await executor.start()
    
    # Wire up and start payment verifier
    payment.set_database(db)
    await payment.start()
    
    # Initialize deposit handler
    deposit_handler = ManualDepositHandler(payment, db)
    
    # Start stuck task recovery background task
    recovery_task = asyncio.create_task(_stuck_task_recovery_loop())
    
    # Store in app.state for dependency injection
    app.state.db = db
    app.state.queue = queue
    app.state.executor = executor
    app.state.payment = payment
    app.state.deposit_handler = deposit_handler
    
    logger.info("AgentHands API started successfully")
    print("🤖 AgentHands API started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AgentHands API...")
    
    # Cancel recovery task
    recovery_task.cancel()
    try:
        await recovery_task
    except asyncio.CancelledError:
        pass
    
    # Graceful shutdown - let current tasks finish
    await payment.stop()
    await executor.stop()
    await queue.stop()
    await db.close()
    
    logger.info("AgentHands API stopped")
    print("👋 AgentHands API stopped")


async def _stuck_task_recovery_loop():
    """Background task to periodically check for and recover stuck tasks."""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            stuck_tasks = await db.get_stuck_tasks(stuck_threshold_minutes=30)
            
            for task in stuck_tasks:
                logger.warning(f"Recovering stuck task: {task.task_id}")
                await db.fail_stuck_task(
                    task.task_id,
                    reason="Task timed out in executing state"
                )
                
                # Record refund transaction
                await db.create_transaction(
                    account_id=task.account_id,
                    type="refund",
                    amount_usdc=task.price_usdc,
                    task_id=task.task_id,
                    description="Auto-refund: Task timed out"
                )
            
            if stuck_tasks:
                logger.info(f"Recovered {len(stuck_tasks)} stuck tasks")
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in stuck task recovery: {e}")


app = FastAPI(
    title="AgentHands API",
    description="Execute real-world tasks for AI agents. Browser automation, code execution, blockchain operations, and more.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for browser-based clients
# SECURITY: Configure specific origins in production
_cors_origins = os.environ.get("AGENTHANDS_CORS_ORIGINS", "")
_allowed_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    # SECURITY: Use specific origins in production, not "*" with credentials
    allow_origins=_allowed_origins,
    # Only allow credentials when specific origins are configured
    allow_credentials=bool(_cors_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Note: Strict-Transport-Security should be set by reverse proxy
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple in-memory rate limiter per IP address."""
    # Skip rate limiting for health checks
    if request.url.path in ["/", "/health"]:
        return await call_next(request)
    
    # Get client IP (handle proxies)
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW
    
    # Clean old entries and count recent requests
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip] if ts > window_start
    ]
    
    # Remove empty entries to prevent memory leak
    if not rate_limit_store[client_ip]:
        del rate_limit_store[client_ip]
        rate_limit_store[client_ip] = []  # Re-create for this request
    
    # Prevent memory exhaustion from too many unique IPs
    if len(rate_limit_store) > MAX_RATE_LIMIT_ENTRIES:
        # Evict oldest entries (crude LRU)
        oldest_ips = sorted(rate_limit_store.keys(), 
                          key=lambda ip: min(rate_limit_store[ip]) if rate_limit_store[ip] else 0)
        for ip in oldest_ips[:MAX_RATE_LIMIT_ENTRIES // 10]:
            del rate_limit_store[ip]
    
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": 429, "message": f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds."}}
        )
    
    # Record this request
    rate_limit_store[client_ip].append(current_time)
    
    response = await call_next(request)
    return response


# ============================================================================
# Public Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Serve landing page."""
    static_path = pathlib.Path(__file__).parent.parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(static_path)
    return {
        "name": "AgentHands",
        "version": "0.1.0",
        "description": "Real-world task execution for AI agents",
        "docs": "/docs",
        "capabilities": "/v1/capabilities"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "queue_size": await queue.size(),
        "active_tasks": await executor.active_count()
    }


@app.get("/v1/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """List all available capabilities and pricing."""
    return CapabilitiesResponse(
        capabilities=list(CAPABILITIES.values()),
        payment={
            "chain": "polygon",
            "token": "USDC",
            "contract": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            "recipient": MASTER_DEPOSIT_ADDRESS,
            "min_deposit": 0.10,
            "note": "Include your account_id in the transaction memo/data field for tracking"
        }
    )


# ============================================================================
# Account Endpoints
# ============================================================================

@app.post("/v1/accounts", response_model=AccountResponse)
async def create_new_account(request: AccountCreate):
    """Create a new prepaid account."""
    account = await create_account(db, request.metadata)
    return account


@app.get("/v1/accounts/{account_id}", response_model=Account)
async def get_account(
    account_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get account details and balance."""
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Verify API key belongs to this account
    if account.api_key != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return account


# ============================================================================
# Task Endpoints
# ============================================================================

@app.post("/v1/tasks", response_model=TaskResponse)
async def submit_task(
    request: TaskSubmission,
    background_tasks: BackgroundTasks,
    http_request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Submit a new task for execution."""
    from .validation import validate_task_input
    
    # Generate request ID for tracing
    request_id = f"req_{uuid_module.uuid4().hex[:12]}"
    
    # Validate capability exists
    if request.capability not in CAPABILITIES:
        logger.warning(f"[{request_id}] Unknown capability requested: {request.capability}")
        raise HTTPException(
            status_code=400,
            detail=f"Unknown capability: {request.capability}. See /v1/capabilities for available options."
        )
    
    capability = CAPABILITIES[request.capability]
    
    # Validate input
    validated_input, validation_error = validate_task_input(request.capability, request.input)
    if validation_error:
        logger.warning(f"[{request_id}] Validation error: {validation_error}")
        raise HTTPException(status_code=400, detail=validation_error)
    
    # Use validated input
    request.input = validated_input
    
    # Get account and verify balance
    account = await db.get_account_by_api_key(api_key)
    if not account:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if account.balance_usdc < capability.price_usdc:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient balance. Required: ${capability.price_usdc}, Available: ${account.balance_usdc}"
        )
    
    # Reserve funds (debit on completion, refund on failure)
    # Uses atomic check to prevent race condition overdrawing
    reserved = await db.reserve_funds(account.account_id, capability.price_usdc)
    if not reserved:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient balance (concurrent request may have depleted funds). Required: ${capability.price_usdc}"
        )
    
    # Create task
    task = await db.create_task(
        capability=request.capability,
        input_data=request.input,
        account_id=account.account_id,
        price_usdc=capability.price_usdc,
        callback_url=request.callback_url,
        metadata=request.metadata
    )
    
    # Add to queue
    queue_position = await queue.enqueue(task.task_id, priority=request.priority or "standard")
    
    # Trigger execution check
    background_tasks.add_task(executor.check_queue)
    
    return TaskResponse(
        task_id=task.task_id,
        status=TaskStatus.QUEUED,
        capability=request.capability,
        price_usdc=capability.price_usdc,
        queue_position=queue_position,
        created_at=task.created_at
    )


@app.get("/v1/tasks/{task_id}")
async def get_task(
    task_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get task status and result."""
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify ownership
    account = await db.get_account_by_api_key(api_key)
    if task.account_id != account.account_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = {
        "task_id": task.task_id,
        "status": task.status,
        "capability": task.capability,
        "created_at": task.created_at
    }
    
    if task.status == TaskStatus.QUEUED:
        response["queue_position"] = await queue.position(task_id)
    
    elif task.status == TaskStatus.EXECUTING:
        response["started_at"] = task.started_at
        response["progress"] = task.progress
    
    elif task.status == TaskStatus.COMPLETED:
        response["result"] = task.result
        response["proof"] = task.proof
        response["execution_time_ms"] = task.execution_time_ms
        response["completed_at"] = task.completed_at
    
    elif task.status == TaskStatus.FAILED:
        response["error"] = task.error
        response["refund"] = {
            "status": "credited",
            "amount_usdc": task.price_usdc,
            "account_id": task.account_id
        }
    
    return response


@app.get("/v1/tasks")
async def list_tasks(
    api_key: str = Depends(verify_api_key),
    status: TaskStatus = None,
    limit: int = 50,
    offset: int = 0
):
    """List tasks for the authenticated account."""
    # Validate pagination parameters to prevent DOS
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100  # Cap maximum
    if offset < 0:
        offset = 0
    
    account = await db.get_account_by_api_key(api_key)
    tasks = await db.list_tasks(
        account_id=account.account_id,
        status=status,
        limit=limit,
        offset=offset
    )
    return {
        "tasks": tasks,
        "count": len(tasks),
        "limit": limit,
        "offset": offset
    }


# ============================================================================
# Payment Endpoints
# ============================================================================

@app.get("/v1/payments/deposit-address/{account_id}")
async def get_deposit_address(
    account_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get the USDC deposit address for an account."""
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Verify ownership
    if account.api_key != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "account_id": account_id,
        "deposit_address": MASTER_DEPOSIT_ADDRESS,
        "memo": account_id,  # User must include this in transaction
        "chain": "polygon",
        "token": "USDC",
        "contract": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "min_deposit": 0.10,
        "confirmations_required": 3,
        "important": "Include your account_id in the transaction memo/input data for deposit tracking"
    }


@app.get("/v1/payments/transactions/{account_id}")
async def get_transactions(
    account_id: str,
    api_key: str = Depends(verify_api_key),
    limit: int = 50
):
    """Get transaction history for an account."""
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.api_key != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transactions = await db.get_transactions(account_id, limit=limit)
    return {
        "account_id": account_id,
        "balance_usdc": account.balance_usdc,
        "transactions": transactions
    }


# ============================================================================
# Deposit Verification Endpoint
# ============================================================================

class DepositSubmission(BaseModel):
    """Request to verify and credit a deposit."""
    tx_hash: str = Field(..., description="Polygon transaction hash", min_length=66, max_length=66)


@app.post("/v1/payments/deposits/{account_id}/verify")
async def verify_deposit(
    account_id: str,
    request: DepositSubmission,
    api_key: str = Depends(verify_api_key)
):
    """
    Verify a USDC deposit and credit the account.
    
    Submit the Polygon transaction hash after sending USDC to your deposit address.
    The system will verify the transaction, check confirmations, and credit your account.
    """
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.api_key != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify the deposit
    result = await deposit_handler.submit_deposit(
        account_id=account_id,
        tx_hash=request.tx_hash
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ============================================================================
# Withdrawal System
# ============================================================================

class WithdrawalRequest(BaseModel):
    """Request to withdraw funds."""
    amount_usdc: float = Field(..., gt=0, description="Amount to withdraw in USDC")
    destination_address: str = Field(..., description="Polygon address to receive funds", min_length=42, max_length=42)


class WithdrawalStatus(BaseModel):
    """Withdrawal status response."""
    withdrawal_id: str
    status: str  # pending, processing, completed, failed
    amount_usdc: float
    destination_address: str
    created_at: str
    tx_hash: Optional[str] = None


@app.post("/v1/payments/withdrawals/{account_id}")
async def request_withdrawal(
    account_id: str,
    request: WithdrawalRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Request a withdrawal of USDC to an external address.
    
    Withdrawals are queued and processed manually for security.
    Minimum withdrawal: $1.00 USDC.
    """
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.api_key != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate minimum withdrawal
    if request.amount_usdc < 1.0:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is $1.00 USDC")
    
    # Check balance
    if account.balance_usdc < request.amount_usdc:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient balance. Available: ${account.balance_usdc:.2f}"
        )
    
    # Validate destination address format
    if not request.destination_address.startswith("0x"):
        raise HTTPException(status_code=400, detail="Invalid destination address format")
    
    # Reserve the funds
    reserved = await db.reserve_funds(account_id, request.amount_usdc)
    if not reserved:
        raise HTTPException(status_code=402, detail="Failed to reserve funds")
    
    # Create withdrawal record
    withdrawal_id = f"wd_{uuid_module.uuid4().hex[:12]}"
    
    await db.create_transaction(
        account_id=account_id,
        type="withdrawal_pending",
        amount_usdc=-request.amount_usdc,
        description=f"Withdrawal to {request.destination_address[:10]}...{request.destination_address[-4:]}"
    )
    
    # TODO: In production, add to withdrawal queue for processing
    # For now, log for manual processing
    logger.info(f"Withdrawal requested: {withdrawal_id} - ${request.amount_usdc} to {request.destination_address}")
    
    return {
        "withdrawal_id": withdrawal_id,
        "status": "pending",
        "amount_usdc": request.amount_usdc,
        "destination_address": request.destination_address,
        "message": "Withdrawal queued for processing. Please allow up to 24 hours.",
        "note": "Withdrawals are processed manually for security."
    }


@app.get("/v1/payments/withdrawals/{account_id}")
async def list_withdrawals(
    account_id: str,
    api_key: str = Depends(verify_api_key),
    limit: int = 20
):
    """List pending and completed withdrawals for an account."""
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.api_key != api_key:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get withdrawal transactions
    transactions = await db.get_transactions(account_id, limit=limit)
    withdrawals = [t for t in transactions if t.type.startswith("withdrawal")]
    
    return {
        "account_id": account_id,
        "withdrawals": withdrawals
    }


# ============================================================================
# Admin Endpoints (protected by admin key)
# ============================================================================

# SECURITY: Admin key MUST be set - no default value
ADMIN_API_KEY = os.environ.get("AGENTHANDS_ADMIN_KEY")
if not ADMIN_API_KEY:
    import logging
    logging.getLogger("agenthands").critical(
        "SECURITY: AGENTHANDS_ADMIN_KEY environment variable not set! "
        "Admin endpoints will be disabled."
    )


async def verify_admin_key(
    authorization: str = Header(..., description="Bearer token with admin API key")
) -> bool:
    """Verify admin API key."""
    # SECURITY: Reject if admin key not configured
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints disabled: AGENTHANDS_ADMIN_KEY not configured"
        )
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid Authorization header format")
        
        key = parts[1]
        
        # Constant-time comparison to prevent timing attacks
        import secrets
        if not secrets.compare_digest(key.encode(), ADMIN_API_KEY.encode()):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return True
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail="Admin access required")


@app.get("/v1/admin/accounts")
async def admin_list_accounts(
    _: bool = Depends(verify_admin_key),
    limit: int = 100,
    offset: int = 0
):
    """[ADMIN] List all accounts."""
    cursor = await db.db.execute("""
        SELECT * FROM accounts ORDER BY created_at DESC LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = await cursor.fetchall()
    
    accounts = []
    for row in rows:
        accounts.append({
            "account_id": row["account_id"],
            "balance_usdc": row["balance_usdc"],
            "reserved_usdc": row["reserved_usdc"],
            "total_spent_usdc": row["total_spent_usdc"],
            "total_deposited_usdc": row["total_deposited_usdc"],
            "tasks_completed": row["tasks_completed"],
            "tasks_failed": row["tasks_failed"],
            "created_at": row["created_at"]
        })
    
    return {"accounts": accounts, "count": len(accounts)}


@app.get("/v1/admin/tasks/stuck")
async def admin_list_stuck_tasks(
    _: bool = Depends(verify_admin_key),
    threshold_minutes: int = 30
):
    """[ADMIN] List stuck tasks."""
    stuck = await db.get_stuck_tasks(threshold_minutes)
    return {"stuck_tasks": [t.model_dump() for t in stuck], "count": len(stuck)}


@app.post("/v1/admin/tasks/{task_id}/cancel")
async def admin_cancel_task(
    task_id: str,
    _: bool = Depends(verify_admin_key)
):
    """[ADMIN] Cancel a stuck task and refund."""
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.QUEUED, TaskStatus.EXECUTING]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} state")
    
    # Fail the task
    success = await db.fail_stuck_task(task_id, reason="Cancelled by admin")
    
    if success:
        await db.create_transaction(
            account_id=task.account_id,
            type="refund",
            amount_usdc=task.price_usdc,
            task_id=task_id,
            description="Admin cancelled task"
        )
    
    return {"status": "cancelled", "task_id": task_id, "refunded": success}


class BalanceAdjustment(BaseModel):
    """Manual balance adjustment."""
    amount_usdc: float = Field(..., description="Amount to add (positive) or subtract (negative)")
    reason: str = Field(..., description="Reason for adjustment")


@app.post("/v1/admin/accounts/{account_id}/adjust")
async def admin_adjust_balance(
    account_id: str,
    request: BalanceAdjustment,
    _: bool = Depends(verify_admin_key)
):
    """[ADMIN] Manually adjust account balance."""
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update balance
    if request.amount_usdc > 0:
        await db.update_balance(account_id, request.amount_usdc, is_deposit=True)
    else:
        await db.update_balance(account_id, abs(request.amount_usdc), is_deposit=False)
    
    # Record transaction
    await db.create_transaction(
        account_id=account_id,
        type="adjustment",
        amount_usdc=request.amount_usdc,
        description=f"Admin adjustment: {request.reason}"
    )
    
    logger.info(f"Admin balance adjustment: {account_id} += ${request.amount_usdc} ({request.reason})")
    
    return {
        "account_id": account_id,
        "adjustment": request.amount_usdc,
        "reason": request.reason,
        "new_balance": account.balance_usdc + request.amount_usdc
    }


@app.get("/v1/admin/metrics")
async def admin_metrics(
    _: bool = Depends(verify_admin_key)
):
    """[ADMIN] Get system metrics."""
    # Task counts by status
    cursor = await db.db.execute("""
        SELECT status, COUNT(*) as count FROM tasks GROUP BY status
    """)
    status_counts = {row["status"]: row["count"] for row in await cursor.fetchall()}
    
    # Queue depth
    queue_stats = await queue.get_stats()
    
    # Active tasks
    active_count = await executor.active_count()
    
    # Total accounts and balances
    cursor = await db.db.execute("""
        SELECT 
            COUNT(*) as total_accounts,
            SUM(balance_usdc) as total_balance,
            SUM(reserved_usdc) as total_reserved,
            SUM(total_spent_usdc) as total_spent,
            SUM(total_deposited_usdc) as total_deposited
        FROM accounts
    """)
    account_stats = await cursor.fetchone()
    
    return {
        "tasks": {
            "by_status": status_counts,
            "queue_depth": queue_stats["total"],
            "active_executing": active_count
        },
        "accounts": {
            "total": account_stats["total_accounts"] or 0,
            "total_balance_usdc": account_stats["total_balance"] or 0,
            "total_reserved_usdc": account_stats["total_reserved"] or 0,
            "total_spent_usdc": account_stats["total_spent"] or 0,
            "total_deposited_usdc": account_stats["total_deposited"] or 0
        }
    }


@app.get("/v1/admin/health")
async def admin_health(
    _: bool = Depends(verify_admin_key)
):
    """[ADMIN] Detailed health check."""
    from .sandbox import get_code_sandbox
    
    sandbox = get_code_sandbox()
    docker_available = await sandbox.is_available()
    
    return {
        "status": "healthy",
        "components": {
            "database": "ok",
            "queue": "ok",
            "executor": "ok",
            "payment_verifier": "ok",
            "docker_sandbox": "ok" if docker_available else "unavailable (fallback mode)"
        },
        "queue_size": await queue.size(),
        "active_tasks": await executor.active_count()
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
