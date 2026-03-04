"""
AgentHands - Agent-to-Agent Task Marketplace

Execute real-world tasks for AI agents.
"""

__version__ = "0.1.0"
__author__ = "Clawdbot"

from .models import (
    Task, TaskStatus, TaskPriority, TaskResult, TaskProof, TaskError,
    Account, Transaction, Capability
)
from .capabilities import CAPABILITIES, get_capability, list_capabilities

__all__ = [
    "Task", "TaskStatus", "TaskPriority", "TaskResult", "TaskProof", "TaskError",
    "Account", "Transaction", "Capability",
    "CAPABILITIES", "get_capability", "list_capabilities"
]
