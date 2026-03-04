"""
AgentHands - Pydantic Models
Data models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import uuid


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    STANDARD = "standard"
    PRIORITY = "priority"      # +50% cost
    IMMEDIATE = "immediate"    # +100% cost


class Capability(BaseModel):
    """A capability that can be executed."""
    id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_description: str
    price_usdc: float
    estimated_time_seconds: int
    tier: int
    examples: Optional[List[Dict[str, Any]]] = None


class PaymentInfo(BaseModel):
    """Payment configuration."""
    chain: str
    token: str
    contract: str
    recipient: str
    min_deposit: float
    note: Optional[str] = None  # Instructions for depositing


class CapabilitiesResponse(BaseModel):
    """Response for /capabilities endpoint."""
    capabilities: List[Capability]
    payment: PaymentInfo


# ============================================================================
# Task Models
# ============================================================================

class TaskSubmission(BaseModel):
    """Request to submit a new task."""
    capability: str = Field(..., description="Capability ID from /capabilities")
    input: Dict[str, Any] = Field(..., description="Input parameters for the capability")
    priority: Optional[TaskPriority] = TaskPriority.STANDARD
    callback_url: Optional[str] = Field(None, description="Webhook URL for completion notification")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Your own reference data")


class TaskResponse(BaseModel):
    """Response after task submission."""
    task_id: str
    status: TaskStatus
    capability: str
    price_usdc: float
    queue_position: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    created_at: datetime


class TaskResult(BaseModel):
    """Result of a completed task."""
    data: Any
    screenshot: Optional[str] = None  # base64 if applicable
    execution_log: Optional[List[Dict[str, Any]]] = None


class TaskProof(BaseModel):
    """Verification proof for a task result."""
    result_hash: str
    signature: str
    timestamp: datetime
    screenshot_url: Optional[str] = None


class TaskError(BaseModel):
    """Error details for a failed task."""
    code: str
    message: str
    details: Optional[str] = None


class Task(BaseModel):
    """Full task record."""
    task_id: str
    capability: str
    input_data: Dict[str, Any]
    account_id: str
    price_usdc: float
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.STANDARD
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Execution tracking
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    
    # Results
    result: Optional[TaskResult] = None
    proof: Optional[TaskProof] = None
    error: Optional[TaskError] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Account Models
# ============================================================================

class AccountCreate(BaseModel):
    """Request to create a new account."""
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (name, etc.)")


class AccountResponse(BaseModel):
    """Response after account creation."""
    account_id: str
    api_key: str
    deposit_address: str
    balance_usdc: float = 0.0
    created_at: datetime


class Account(BaseModel):
    """Full account record."""
    account_id: str
    api_key: str
    deposit_address: str
    balance_usdc: float = 0.0
    reserved_usdc: float = 0.0  # Reserved for pending tasks
    total_spent_usdc: float = 0.0
    total_deposited_usdc: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Transaction(BaseModel):
    """A financial transaction."""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    account_id: str
    type: str  # 'deposit', 'task', 'refund', 'withdrawal'
    amount_usdc: float
    task_id: Optional[str] = None
    tx_hash: Optional[str] = None  # For blockchain transactions
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Error Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: int
    message: str
    details: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail
