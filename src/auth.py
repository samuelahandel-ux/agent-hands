"""
AgentHands - Authentication
API key generation and validation
"""

import os
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException, Header, Request

from .database import Database
from .models import AccountResponse


# ============================================================================
# MVP Master Wallet Configuration
# ============================================================================
# IMPORTANT: For MVP, all deposits go to a SINGLE master wallet address.
# Users must include their account_id in the transaction memo/reference.
# In production, use HD wallet derivation for unique per-account addresses.

# Load from environment variable, with fallback (but log warning if using fallback)
_DEFAULT_DEPOSIT_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f5bD47"
MASTER_DEPOSIT_ADDRESS = os.environ.get("AGENTHANDS_DEPOSIT_ADDRESS", _DEFAULT_DEPOSIT_ADDRESS)

if MASTER_DEPOSIT_ADDRESS == _DEFAULT_DEPOSIT_ADDRESS:
    import warnings
    warnings.warn(
        "Using default deposit address! Set AGENTHANDS_DEPOSIT_ADDRESS environment variable for production.",
        UserWarning
    )

# ============================================================================


def generate_api_key() -> str:
    """Generate a new API key."""
    # Format: ah_sk_live_<random>
    random_part = secrets.token_hex(24)
    return f"ah_sk_live_{random_part}"


def generate_account_id() -> str:
    """Generate a new account ID."""
    return f"acc_{secrets.token_hex(8)}"


def get_deposit_info(account_id: str) -> Dict[str, str]:
    """
    Get deposit information for an account.
    
    MVP LIMITATION:
    All deposits go to a single master wallet. Users must include their
    account_id in the transaction memo/input data field for tracking.
    
    For production: Use HD wallet derivation for unique addresses.
    
    Returns:
        dict with deposit_address and memo (account_id for reference)
    """
    return {
        "deposit_address": MASTER_DEPOSIT_ADDRESS,
        "memo": account_id,  # User must include this in tx memo/data
        "note": "Include your account_id in the transaction memo/reference field"
    }


async def create_account(
    db: Database,
    metadata: Optional[Dict[str, Any]] = None
) -> AccountResponse:
    """Create a new account with API key and deposit address."""
    
    account_id = generate_account_id()
    api_key = generate_api_key()
    
    # MVP: Use master deposit address (same for all accounts)
    # User must include account_id in memo for deposit tracking
    deposit_info = get_deposit_info(account_id)
    deposit_address = deposit_info["deposit_address"]
    
    account = await db.create_account(
        account_id=account_id,
        api_key=api_key,
        deposit_address=deposit_address,
        metadata=metadata
    )
    
    return AccountResponse(
        account_id=account.account_id,
        api_key=account.api_key,
        deposit_address=account.deposit_address,
        balance_usdc=account.balance_usdc,
        created_at=account.created_at
    )


def parse_api_key_from_header(authorization: str) -> str:
    """
    Parse API key from Authorization header.
    Returns the API key string.
    Raises HTTPException if invalid format.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Use: Bearer <api_key>"
        )
    
    api_key = parts[1]
    
    # Validate format and length to prevent DoS via extremely long keys
    if len(api_key) > 100:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format"
        )
    
    if not api_key.startswith("ah_sk_"):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format"
        )
    
    return api_key


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    """
    return secrets.compare_digest(a.encode(), b.encode())


async def verify_api_key_with_db(
    request: Request,
    authorization: str = Header(..., description="Bearer token with API key")
) -> str:
    """
    FastAPI dependency to verify API key from Authorization header.
    Checks that the key exists in the database.
    Returns the API key if valid.
    """
    api_key = parse_api_key_from_header(authorization)
    
    # Get database from app.state
    db: Database = request.app.state.db
    
    # Verify API key exists in database
    account = await db.get_account_by_api_key(api_key)
    if not account:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return api_key


# Alias for backwards compatibility - now uses DB verification
verify_api_key = verify_api_key_with_db


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    (Not used in MVP - for production use)
    """
    return hashlib.sha256(api_key.encode()).hexdigest()
