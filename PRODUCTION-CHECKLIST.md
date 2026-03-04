# AgentHands Production Checklist

## Overview
This document tracks the production hardening work for AgentHands.

**Last Updated:** 2025-01-XX
**Status:** ✅ Production Ready (with notes)

---

## Phase 1: Security ✅

### 1. Docker Sandboxing for Code Execution ✅
- [x] `Dockerfile.sandbox` - minimal Python/Node image
- [x] `src/sandbox.py` - Docker execution wrapper
- [x] `executor.py` updated to use sandbox for code.execute
- [x] Resource limits (CPU: 0.5 cores, Memory: 256MB)
- [x] Timeout enforcement at container level
- [x] No volume mounts except temp input/output
- [x] Network isolation (`--network none`)
- [x] Read-only root filesystem
- [x] Non-root user in container
- [x] Fallback to direct execution when Docker unavailable

**Files:**
- `Dockerfile.sandbox`
- `src/sandbox.py`
- `src/executor.py` (updated)

### 2. Browser Isolation ✅
- [x] `Dockerfile.browser` - Playwright sandbox image
- [x] `src/browser_sandbox.py` - isolated browser executor
- [x] Screenshot-only mode
- [x] Non-root user
- [ ] Full container-based browser execution (basic implementation)

**Note:** Browser sandbox is implemented but requires Docker to be available. Falls back to direct Playwright execution when Docker is unavailable.

---

## Phase 2: Payment System ✅

### 3. Real Deposit Flow ✅
- [x] `POST /v1/payments/deposits/{account_id}/verify` endpoint
- [x] Polygon USDC transfer verification via RPC
- [x] Confirmation counting (3 confirmations required)
- [x] Transaction deduplication (checks both memory cache + database)
- [x] Recipient address validation (SSRF protection)
- [x] Manual deposit submission flow

**How it works:**
1. User sends USDC to master deposit address on Polygon
2. User calls `/verify` with the tx_hash
3. System verifies transaction on-chain
4. Account is credited after 3 confirmations

### 4. Withdrawal System ✅
- [x] `POST /v1/payments/withdrawals/{account_id}` - request withdrawal
- [x] `GET /v1/payments/withdrawals/{account_id}` - list withdrawals
- [x] Balance validation before withdrawal
- [x] Funds reserved during pending withdrawal
- [x] Minimum withdrawal: $1.00 USDC
- [x] Queued for manual processing (security)

**Note:** Withdrawals are logged for manual processing. Automated withdrawal (hot wallet sending) is NOT implemented for security reasons.

---

## Phase 3: Reliability ✅

### 5. Persistent Queue ✅
- [x] `PersistentTaskQueue` wired up in `main.py`
- [x] Queue loads from database on startup
- [x] Graceful shutdown (logs remaining tasks)
- [x] Tasks survive process restarts

### 6. Stuck Task Recovery ✅
- [x] `db.get_stuck_tasks()` - finds tasks stuck in "executing" > 30 min
- [x] `db.fail_stuck_task()` - marks as failed + refunds
- [x] Background recovery loop runs every 5 minutes
- [x] Recovery on startup
- [x] Admin endpoint to view stuck tasks
- [x] Admin endpoint to manually cancel tasks

### 7. Proper Logging ✅
- [x] Structured JSON logging format
- [x] Request IDs for tracing (generated in submit_task)
- [x] Task lifecycle events logged:
  - Task started
  - Task completed (with duration, cost)
  - Task failed (with error)
- [x] Payment events logged

---

## Phase 4: Validation ✅

### 8. Input Schema Validation ✅
- [x] `src/validation.py` - comprehensive validation module
- [x] Validators for all capabilities:
  - `browser.screenshot`
  - `browser.scrape`
  - `code.execute`
  - `file.download`
  - `api.call`
  - `blockchain.balance`
- [x] String sanitization (max lengths, null byte removal)
- [x] URL validation
- [x] Ethereum address validation
- [x] Helpful error messages

### 9. Output Schema Validation
- [x] Results match expected format (via Pydantic models)
- [x] Output size limits in sandbox (1MB max)
- [ ] Formal output schema validation (low priority)

---

## Phase 5: Operations ✅

### 10. Metrics ✅
- [x] `GET /v1/admin/metrics` endpoint
- [x] Task counts by status
- [x] Queue depth
- [x] Active executing count
- [x] Account totals (balance, spent, deposited)

### 11. Admin Endpoints ✅
- [x] `GET /v1/admin/accounts` - list all accounts
- [x] `GET /v1/admin/tasks/stuck` - list stuck tasks
- [x] `POST /v1/admin/tasks/{id}/cancel` - cancel stuck task
- [x] `POST /v1/admin/accounts/{id}/adjust` - manual balance adjustment
- [x] `GET /v1/admin/health` - detailed health check
- [x] `GET /v1/admin/metrics` - system metrics
- [x] Admin key authentication (env: `AGENTHANDS_ADMIN_KEY`)

---

## Deployment Requirements

### Environment Variables
```bash
# Required for production
AGENTHANDS_DEPOSIT_ADDRESS=0x...  # Your USDC deposit address
AGENTHANDS_ADMIN_KEY=...          # Admin API key (change from default!)

# Optional
AGENTHANDS_DB_PATH=./data/agenthands.db
AGENTHANDS_PORT=8080
```

### Docker Setup
```bash
# Build sandbox image (required for secure code execution)
cd /home/ec2-user/clawd/projects/agent-hands
docker build -t agenthands-sandbox:latest -f Dockerfile.sandbox .

# Optional: Build browser sandbox
docker build -t agenthands-browser:latest -f Dockerfile.browser .
```

### Running in Production
```bash
# Start API
uvicorn src.main:app --host 0.0.0.0 --port 8080 --workers 1

# Note: Use single worker - queue is in-memory within process
# For multi-worker, implement Redis-based queue
```

---

## Security Checklist

- [x] API keys validated against database
- [x] Admin endpoints protected by separate key
- [x] Rate limiting (100 req/min per IP)
- [x] URL blocklist (SSRF protection)
- [x] Code execution sandboxed in Docker
- [x] Deposit recipient verified
- [x] Transaction deduplication
- [x] Input validation/sanitization
- [x] No secrets in logs

---

## Known Limitations (MVP)

1. **Single master deposit address** - All users deposit to same address. Production should use HD wallet derivation.

2. **Manual withdrawal processing** - For security, withdrawals are queued for manual approval. No hot wallet auto-send.

3. **Single process** - Queue is in-memory. For horizontal scaling, implement Redis queue.

4. **SQLite database** - For production load, migrate to PostgreSQL.

5. **Browser sandbox partial** - Full Docker browser isolation requires more setup. Falls back to direct Playwright.

6. **No result signing** - Proof signatures are placeholder (`0x...`). Implement actual signing for verifiable results.

---

## Files Changed

### New Files
- `Dockerfile.sandbox` - Code execution sandbox
- `Dockerfile.browser` - Browser sandbox  
- `src/sandbox.py` - Docker sandbox execution
- `src/browser_sandbox.py` - Browser automation in container
- `src/validation.py` - Input validation
- `PRODUCTION-CHECKLIST.md` - This file

### Updated Files
- `src/main.py` - PersistentQueue, admin endpoints, deposit/withdrawal
- `src/executor.py` - Sandbox integration, structured logging
- `src/queue.py` - PersistentTaskQueue improvements
- `README.md` - Updated setup instructions
