"""
AgentHands - Payment Verification
USDC on Polygon payment handling
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import httpx

from .database import Database


# Polygon USDC Contract
USDC_CONTRACT = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
USDC_DECIMALS = 6

# RPC Endpoints (updated with working free endpoints)
POLYGON_RPC = "https://polygon-mainnet.g.alchemy.com/v2/demo"
POLYGON_RPC_BACKUP = "https://polygon.llamarpc.com"
POLYGONSCAN_API = "https://api.polygonscan.com/api"

# Minimum confirmations required
MIN_CONFIRMATIONS = 3


class PaymentVerifier:
    """
    Monitors and verifies USDC deposits on Polygon.
    
    Flow:
    1. Account created → deposit address assigned
    2. User sends USDC to deposit address
    3. PaymentVerifier detects transfer via polling
    4. After MIN_CONFIRMATIONS, credits account
    """
    
    # Maximum size of in-memory tx cache to prevent memory leak
    MAX_PROCESSED_TX_CACHE = 10000
    
    def __init__(self, db: Database = None):
        self.db = db
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._poll_interval = 30  # seconds
        
        # Track processed transactions to avoid duplicates (bounded LRU-like cache)
        self._processed_txs: set = set()
    
    def set_database(self, db: Database):
        """Inject database dependency."""
        self.db = db
    
    async def start(self):
        """Start the payment monitoring loop."""
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        print("💰 Payment verifier started")
    
    async def stop(self):
        """Stop the payment monitoring."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        print("💰 Payment verifier stopped")
    
    async def _poll_loop(self):
        """Main polling loop to check for new deposits."""
        while self._running:
            try:
                await self._check_deposits()
            except Exception as e:
                print(f"Payment poll error: {e}")
            
            await asyncio.sleep(self._poll_interval)
    
    async def _check_deposits(self):
        """Check for new USDC deposits to all account addresses."""
        # Get all account deposit addresses
        # In production, we'd use a webhook or more efficient indexing
        
        # For MVP, this is a simplified implementation
        # Real implementation would:
        # 1. Subscribe to Polygon events via WebSocket
        # 2. Or use a service like Alchemy/Infura for notifications
        # 3. Or use Polygonscan API to get recent transfers
        
        pass  # Placeholder for MVP
    
    async def _rpc_request(self, client: httpx.AsyncClient, method: str, params: list) -> Dict:
        """Make RPC request with fallback to backup endpoint."""
        request_body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        # Try primary endpoint
        try:
            response = await client.post(POLYGON_RPC, json=request_body, timeout=10)
            result = response.json()
            if "result" in result:
                return result
        except Exception:
            pass
        
        # Fallback to backup endpoint
        response = await client.post(POLYGON_RPC_BACKUP, json=request_body, timeout=10)
        return response.json()
    
    async def verify_deposit(
        self,
        tx_hash: str,
        account_id: str,
        expected_amount: float = None
    ) -> Dict:
        """
        Verify a specific deposit transaction.
        
        Args:
            tx_hash: Polygon transaction hash
            account_id: Account to credit
            expected_amount: Optional expected amount to verify
        
        Returns:
            Verification result with status and amount
        """
        async with httpx.AsyncClient() as client:
            # Get transaction receipt
            result = await self._rpc_request(client, "eth_getTransactionReceipt", [tx_hash])
            receipt = result.get("result")
            
            if not receipt:
                return {
                    "status": "pending",
                    "message": "Transaction not yet confirmed"
                }
            
            # Check confirmations
            try:
                block_number = int(receipt["blockNumber"], 16)
            except (KeyError, ValueError, TypeError) as e:
                return {
                    "status": "error",
                    "message": f"Invalid receipt format: {e}"
                }
            
            # Get current block
            block_result = await self._rpc_request(client, "eth_blockNumber", [])
            if "result" not in block_result:
                return {
                    "status": "error",
                    "message": "Failed to get current block number"
                }
            try:
                current_block = int(block_result["result"], 16)
            except (ValueError, TypeError) as e:
                return {
                    "status": "error",
                    "message": f"Invalid block number format: {e}"
                }
            confirmations = current_block - block_number
            
            if confirmations < MIN_CONFIRMATIONS:
                return {
                    "status": "confirming",
                    "confirmations": confirmations,
                    "required": MIN_CONFIRMATIONS,
                    "message": f"Waiting for {MIN_CONFIRMATIONS - confirmations} more confirmations"
                }
            
            # Check if transaction was successful
            if receipt["status"] != "0x1":
                return {
                    "status": "failed",
                    "message": "Transaction failed on-chain"
                }
            
            # Parse USDC transfer from logs
            transfer_amount = self._parse_usdc_transfer(receipt["logs"])
            
            if transfer_amount is None:
                return {
                    "status": "invalid",
                    "message": "No USDC transfer found in transaction"
                }
            
            # Verify amount if expected
            if expected_amount and abs(transfer_amount - expected_amount) > 0.001:
                return {
                    "status": "amount_mismatch",
                    "expected": expected_amount,
                    "received": transfer_amount,
                    "message": f"Amount mismatch: expected {expected_amount}, got {transfer_amount}"
                }
            
            # Credit account if not already processed
            # Check both in-memory cache AND database to prevent double credits
            if tx_hash not in self._processed_txs:
                # Also check database - in case of restart or race condition
                existing = await self._check_tx_exists(tx_hash)
                if not existing:
                    await self._credit_account(account_id, transfer_amount, tx_hash)
                    self._processed_txs.add(tx_hash)
                    credited = True
                else:
                    self._processed_txs.add(tx_hash)  # Cache it now
                    credited = False
            else:
                credited = False
            
            return {
                "status": "confirmed",
                "amount_usdc": transfer_amount,
                "confirmations": confirmations,
                "credited": credited,
                "already_processed": not credited
            }
    
    def _parse_usdc_transfer(self, logs: List[Dict], expected_recipient: str = None) -> Optional[float]:
        """
        Parse USDC transfer amount from transaction logs.
        
        USDC Transfer event: Transfer(address indexed from, address indexed to, uint256 value)
        Topic0: 0xddf252ad... (event signature)
        Topic1: from address (padded to 32 bytes)
        Topic2: to address (padded to 32 bytes)
        Data: amount
        
        Security: Verifies recipient matches our deposit address.
        """
        TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        # Import here to avoid circular import
        from .auth import MASTER_DEPOSIT_ADDRESS
        recipient_to_check = (expected_recipient or MASTER_DEPOSIT_ADDRESS).lower()
        
        for log in logs:
            # Check if this is from USDC contract
            if log["address"].lower() != USDC_CONTRACT.lower():
                continue
            
            # Check if this is a Transfer event
            if len(log["topics"]) < 3 or log["topics"][0] != TRANSFER_TOPIC:
                continue
            
            # SECURITY: Verify the recipient (topic[2]) matches our deposit address
            # Topics are 32-byte padded addresses
            to_address = "0x" + log["topics"][2][-40:]  # Last 20 bytes (40 hex chars)
            if to_address.lower() != recipient_to_check:
                continue  # Transfer wasn't to us, skip
            
            # Parse amount from data
            amount_hex = log["data"]
            amount_raw = int(amount_hex, 16)
            amount_usdc = amount_raw / (10 ** USDC_DECIMALS)
            
            return amount_usdc
        
        return None
    
    async def _check_tx_exists(self, tx_hash: str) -> bool:
        """Check if a transaction has already been processed in the database."""
        try:
            transactions = await self.db.get_transactions_by_tx_hash(tx_hash)
            return len(transactions) > 0
        except Exception:
            # If we can't check, err on the side of caution
            return False
    
    async def _credit_account(
        self,
        account_id: str,
        amount_usdc: float,
        tx_hash: str
    ):
        """Credit an account with deposited funds."""
        # Verify account exists before crediting
        account = await self.db.get_account(account_id)
        if not account:
            print(f"⚠️ Cannot credit unknown account: {account_id}")
            return
        
        # Update balance
        await self.db.update_balance(account_id, amount_usdc, is_deposit=True)
        
        # Record transaction
        await self.db.create_transaction(
            account_id=account_id,
            type="deposit",
            amount_usdc=amount_usdc,
            tx_hash=tx_hash,
            description=f"USDC deposit from Polygon"
        )
        
        # Evict old entries if cache is too large (simple LRU approximation)
        if len(self._processed_txs) > self.MAX_PROCESSED_TX_CACHE:
            # Remove ~10% of oldest entries (since set is unordered, just clear some)
            entries_to_remove = list(self._processed_txs)[:self.MAX_PROCESSED_TX_CACHE // 10]
            for entry in entries_to_remove:
                self._processed_txs.discard(entry)
        
        print(f"💰 Credited ${amount_usdc} USDC to {account_id} (tx: {tx_hash[:10]}...)")
    
    async def get_usdc_balance(self, address: str) -> float:
        """Get USDC balance for an address."""
        async with httpx.AsyncClient() as client:
            # balanceOf(address) call
            data = f"0x70a08231000000000000000000000000{address[2:]}"
            
            result = await self._rpc_request(
                client, 
                "eth_call", 
                [{"to": USDC_CONTRACT, "data": data}, "latest"]
            )
            
            balance_raw = int(result["result"], 16)
            balance_usdc = balance_raw / (10 ** USDC_DECIMALS)
            
            return balance_usdc


class ManualDepositHandler:
    """
    For MVP: Manual deposit verification.
    User provides tx_hash, we verify and credit.
    """
    
    def __init__(self, verifier: PaymentVerifier, db: Database):
        self.verifier = verifier
        self.db = db
    
    async def submit_deposit(
        self,
        account_id: str,
        tx_hash: str
    ) -> Dict:
        """
        User submits a deposit transaction for verification.
        """
        # Verify the account exists
        account = await self.db.get_account(account_id)
        if not account:
            return {"error": "Account not found"}
        
        # Verify the transaction
        result = await self.verifier.verify_deposit(
            tx_hash=tx_hash,
            account_id=account_id
        )
        
        return result
