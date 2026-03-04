"""
AgentHands - Database Layer
SQLite-based storage for accounts, tasks, and transactions
"""

import aiosqlite
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from .models import (
    Task, TaskStatus, TaskPriority, TaskResult, TaskProof, TaskError,
    Account, Transaction
)

DATABASE_PATH = Path(__file__).parent.parent / "data" / "agenthands.db"


class Database:
    """Async SQLite database wrapper."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DATABASE_PATH)
        self.db: Optional[aiosqlite.Connection] = None
    
    async def init(self):
        """Initialize database and create tables."""
        import os as os_module
        import stat
        
        # Ensure directory exists with secure permissions
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # SECURITY: Set directory permissions to 700 (owner only)
        try:
            os_module.chmod(db_dir, stat.S_IRWXU)
        except OSError:
            pass  # May fail on some filesystems
        
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        
        # Enable foreign key enforcement (SQLite has it disabled by default)
        await self.db.execute("PRAGMA foreign_keys = ON")
        
        await self._create_tables()
        
        # SECURITY: Set database file permissions to 600 (owner read/write only)
        try:
            os_module.chmod(self.db_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass  # May fail on some filesystems
        
        print(f"📦 Database initialized at {self.db_path}")
    
    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()
    
    async def _create_tables(self):
        """Create all required tables."""
        await self.db.executescript("""
            -- Accounts table
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                deposit_address TEXT NOT NULL,
                balance_usdc REAL DEFAULT 0.0,
                reserved_usdc REAL DEFAULT 0.0,
                total_spent_usdc REAL DEFAULT 0.0,
                total_deposited_usdc REAL DEFAULT 0.0,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- Tasks table
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                capability TEXT NOT NULL,
                input_data TEXT NOT NULL,
                account_id TEXT NOT NULL,
                price_usdc REAL NOT NULL,
                status TEXT DEFAULT 'queued',
                priority TEXT DEFAULT 'standard',
                callback_url TEXT,
                metadata TEXT,
                progress REAL DEFAULT 0.0,
                started_at TEXT,
                completed_at TEXT,
                execution_time_ms INTEGER,
                result TEXT,
                proof TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );
            
            -- Transactions table
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount_usdc REAL NOT NULL,
                task_id TEXT,
                tx_hash TEXT,
                description TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );
            
            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_tasks_account ON tasks(account_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_tx_hash ON transactions(tx_hash);
            CREATE INDEX IF NOT EXISTS idx_accounts_api_key ON accounts(api_key);
            
            -- SECURITY: Unique constraint on tx_hash for deposits to prevent double-crediting
            -- Note: This is a partial unique index (only for non-null tx_hash)
            CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_tx_hash_unique 
                ON transactions(tx_hash) WHERE tx_hash IS NOT NULL;
        """)
        await self.db.commit()
    
    # ========================================================================
    # Account Operations
    # ========================================================================
    
    async def create_account(
        self,
        account_id: str,
        api_key: str,
        deposit_address: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Account:
        """Create a new account."""
        now = datetime.utcnow().isoformat()
        
        await self.db.execute("""
            INSERT INTO accounts (
                account_id, api_key, deposit_address, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            account_id, api_key, deposit_address,
            json.dumps(metadata) if metadata else None,
            now, now
        ))
        await self.db.commit()
        
        return Account(
            account_id=account_id,
            api_key=api_key,
            deposit_address=deposit_address,
            metadata=metadata,
            created_at=datetime.fromisoformat(now)
        )
    
    async def get_account(self, account_id: str) -> Optional[Account]:
        """Get account by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM accounts WHERE account_id = ?",
            (account_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_account(row)
    
    async def get_account_by_api_key(self, api_key: str) -> Optional[Account]:
        """Get account by API key."""
        cursor = await self.db.execute(
            "SELECT * FROM accounts WHERE api_key = ?",
            (api_key,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_account(row)
    
    async def update_balance(self, account_id: str, amount: float, is_deposit: bool = True):
        """Update account balance."""
        if is_deposit:
            await self.db.execute("""
                UPDATE accounts 
                SET balance_usdc = balance_usdc + ?,
                    total_deposited_usdc = total_deposited_usdc + ?,
                    updated_at = ?
                WHERE account_id = ?
            """, (amount, amount, datetime.utcnow().isoformat(), account_id))
        else:
            await self.db.execute("""
                UPDATE accounts 
                SET balance_usdc = balance_usdc - ?,
                    total_spent_usdc = total_spent_usdc + ?,
                    updated_at = ?
                WHERE account_id = ?
            """, (amount, amount, datetime.utcnow().isoformat(), account_id))
        await self.db.commit()
    
    async def reserve_funds(self, account_id: str, amount: float) -> bool:
        """
        Reserve funds for a pending task.
        Returns True if successful, False if insufficient balance.
        Uses atomic update to prevent race conditions.
        """
        # Atomic update that only succeeds if balance is sufficient
        cursor = await self.db.execute("""
            UPDATE accounts 
            SET balance_usdc = balance_usdc - ?,
                reserved_usdc = reserved_usdc + ?,
                updated_at = ?
            WHERE account_id = ? AND balance_usdc >= ?
        """, (amount, amount, datetime.utcnow().isoformat(), account_id, amount))
        await self.db.commit()
        
        # Check if update succeeded
        if cursor.rowcount == 0:
            return False
        return True
    
    async def confirm_spend(self, account_id: str, amount: float) -> bool:
        """
        Confirm reserved funds as spent (task completed).
        Uses atomic update to prevent reserved_usdc going negative.
        Returns True if successful, False otherwise.
        """
        cursor = await self.db.execute("""
            UPDATE accounts 
            SET reserved_usdc = reserved_usdc - ?,
                total_spent_usdc = total_spent_usdc + ?,
                tasks_completed = tasks_completed + 1,
                updated_at = ?
            WHERE account_id = ? AND reserved_usdc >= ?
        """, (amount, amount, datetime.utcnow().isoformat(), account_id, amount))
        await self.db.commit()
        return cursor.rowcount > 0
    
    async def refund_reserved(self, account_id: str, amount: float) -> bool:
        """
        Refund reserved funds (task failed).
        Uses atomic update to prevent reserved_usdc going negative.
        Returns True if successful, False otherwise.
        """
        cursor = await self.db.execute("""
            UPDATE accounts 
            SET balance_usdc = balance_usdc + ?,
                reserved_usdc = reserved_usdc - ?,
                tasks_failed = tasks_failed + 1,
                updated_at = ?
            WHERE account_id = ? AND reserved_usdc >= ?
        """, (amount, amount, datetime.utcnow().isoformat(), account_id, amount))
        await self.db.commit()
        return cursor.rowcount > 0
    
    def _row_to_account(self, row) -> Account:
        """Convert database row to Account model."""
        # Safe JSON parsing for metadata (handle corruption)
        metadata = None
        if row['metadata']:
            try:
                metadata = json.loads(row['metadata'])
            except json.JSONDecodeError:
                metadata = {"_error": "corrupted_metadata"}
        
        return Account(
            account_id=row['account_id'],
            api_key=row['api_key'],
            deposit_address=row['deposit_address'],
            balance_usdc=row['balance_usdc'],
            reserved_usdc=row['reserved_usdc'],
            total_spent_usdc=row['total_spent_usdc'],
            total_deposited_usdc=row['total_deposited_usdc'],
            tasks_completed=row['tasks_completed'],
            tasks_failed=row['tasks_failed'],
            metadata=metadata,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
    
    # ========================================================================
    # Task Operations
    # ========================================================================
    
    async def create_task(
        self,
        capability: str,
        input_data: Dict[str, Any],
        account_id: str,
        price_usdc: float,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.STANDARD
    ) -> Task:
        """Create a new task."""
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()
        
        await self.db.execute("""
            INSERT INTO tasks (
                task_id, capability, input_data, account_id, price_usdc,
                priority, callback_url, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id, capability, json.dumps(input_data), account_id, price_usdc,
            priority.value, callback_url,
            json.dumps(metadata) if metadata else None,
            now, now
        ))
        await self.db.commit()
        
        return Task(
            task_id=task_id,
            capability=capability,
            input_data=input_data,
            account_id=account_id,
            price_usdc=price_usdc,
            priority=priority,
            callback_url=callback_url,
            metadata=metadata,
            created_at=datetime.fromisoformat(now)
        )
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        cursor = await self.db.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_task(row)
    
    async def list_tasks(
        self,
        account_id: str,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Task]:
        """List tasks for an account."""
        if status:
            cursor = await self.db.execute("""
                SELECT * FROM tasks 
                WHERE account_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (account_id, status.value, limit, offset))
        else:
            cursor = await self.db.execute("""
                SELECT * FROM tasks 
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (account_id, limit, offset))
        
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]
    
    async def get_queued_tasks(self, limit: int = 10) -> List[Task]:
        """Get queued tasks ordered by priority and creation time."""
        cursor = await self.db.execute("""
            SELECT * FROM tasks 
            WHERE status = 'queued'
            ORDER BY 
                CASE priority 
                    WHEN 'immediate' THEN 0 
                    WHEN 'priority' THEN 1 
                    ELSE 2 
                END,
                created_at ASC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]
    
    async def get_stuck_tasks(self, stuck_threshold_minutes: int = 30) -> List[Task]:
        """
        Get tasks stuck in 'executing' status for too long.
        These may need recovery (re-queue or fail).
        """
        threshold = (datetime.utcnow() - timedelta(minutes=stuck_threshold_minutes)).isoformat()
        cursor = await self.db.execute("""
            SELECT * FROM tasks 
            WHERE status = 'executing' AND started_at < ?
        """, (threshold,))
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]
    
    async def fail_stuck_task(self, task_id: str, reason: str = "Task timed out"):
        """Mark a stuck task as failed and refund the reserved funds."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.EXECUTING:
            return False
        
        # Update task status
        await self.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error=TaskError(
                code="STUCK_TASK_TIMEOUT",
                message=reason,
                details=f"Task was stuck in executing state"
            )
        )
        
        # Refund reserved funds
        await self.refund_reserved(task.account_id, task.price_usdc)
        
        return True
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: float = None,
        result: TaskResult = None,
        proof: TaskProof = None,
        error: TaskError = None,
        execution_time_ms: int = None
    ):
        """Update task status and related fields."""
        now = datetime.utcnow().isoformat()
        updates = ["status = ?", "updated_at = ?"]
        values = [status.value, now]
        
        if progress is not None:
            updates.append("progress = ?")
            values.append(progress)
        
        if status == TaskStatus.EXECUTING:
            updates.append("started_at = ?")
            values.append(now)
        
        if status == TaskStatus.COMPLETED:
            updates.append("completed_at = ?")
            values.append(now)
            if result:
                updates.append("result = ?")
                values.append(result.model_dump_json())
            if proof:
                updates.append("proof = ?")
                values.append(proof.model_dump_json())
            if execution_time_ms:
                updates.append("execution_time_ms = ?")
                values.append(execution_time_ms)
        
        if status == TaskStatus.FAILED and error:
            updates.append("error = ?")
            values.append(error.model_dump_json())
        
        values.append(task_id)
        
        await self.db.execute(f"""
            UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?
        """, values)
        await self.db.commit()
    
    def _row_to_task(self, row) -> Task:
        """Convert database row to Task model."""
        # Safe JSON parsing with error handling
        def safe_json_load(data, default=None):
            if not data:
                return default
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return default
        
        def safe_model_load(model_class, data):
            if not data:
                return None
            try:
                return model_class.model_validate_json(data)
            except Exception:
                return None
        
        return Task(
            task_id=row['task_id'],
            capability=row['capability'],
            input_data=safe_json_load(row['input_data'], {}),
            account_id=row['account_id'],
            price_usdc=row['price_usdc'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            callback_url=row['callback_url'],
            metadata=safe_json_load(row['metadata']),
            progress=row['progress'],
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            execution_time_ms=row['execution_time_ms'],
            result=safe_model_load(TaskResult, row['result']),
            proof=safe_model_load(TaskProof, row['proof']),
            error=safe_model_load(TaskError, row['error']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
    
    # ========================================================================
    # Transaction Operations
    # ========================================================================
    
    async def create_transaction(
        self,
        account_id: str,
        type: str,
        amount_usdc: float,
        task_id: str = None,
        tx_hash: str = None,
        description: str = None
    ) -> Transaction:
        """Record a transaction."""
        transaction_id = f"tx_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()
        
        await self.db.execute("""
            INSERT INTO transactions (
                transaction_id, account_id, type, amount_usdc,
                task_id, tx_hash, description, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id, account_id, type, amount_usdc,
            task_id, tx_hash, description, now
        ))
        await self.db.commit()
        
        return Transaction(
            transaction_id=transaction_id,
            account_id=account_id,
            type=type,
            amount_usdc=amount_usdc,
            task_id=task_id,
            tx_hash=tx_hash,
            description=description,
            timestamp=datetime.fromisoformat(now)
        )
    
    async def get_transactions(
        self,
        account_id: str,
        limit: int = 50
    ) -> List[Transaction]:
        """Get transactions for an account."""
        cursor = await self.db.execute("""
            SELECT * FROM transactions
            WHERE account_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (account_id, limit))
        rows = await cursor.fetchall()
        
        return [
            Transaction(
                transaction_id=row['transaction_id'],
                account_id=row['account_id'],
                type=row['type'],
                amount_usdc=row['amount_usdc'],
                task_id=row['task_id'],
                tx_hash=row['tx_hash'],
                description=row['description'],
                timestamp=datetime.fromisoformat(row['timestamp'])
            )
            for row in rows
        ]
    
    async def get_transactions_by_tx_hash(self, tx_hash: str) -> List[Transaction]:
        """Get transactions by blockchain tx hash (for duplicate detection)."""
        cursor = await self.db.execute("""
            SELECT * FROM transactions
            WHERE tx_hash = ?
        """, (tx_hash,))
        rows = await cursor.fetchall()
        
        return [
            Transaction(
                transaction_id=row['transaction_id'],
                account_id=row['account_id'],
                type=row['type'],
                amount_usdc=row['amount_usdc'],
                task_id=row['task_id'],
                tx_hash=row['tx_hash'],
                description=row['description'],
                timestamp=datetime.fromisoformat(row['timestamp'])
            )
            for row in rows
        ]
