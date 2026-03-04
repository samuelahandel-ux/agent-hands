"""
Tests for AgentHands data models
"""

import pytest
from datetime import datetime
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from src.models import (
    Task, TaskStatus, TaskPriority, TaskResult, TaskProof, TaskError,
    Account, Transaction, Capability, TaskSubmission
)


class TestTaskModels:
    """Test task-related models."""
    
    def test_task_creation(self):
        """Task should be created with defaults."""
        task = Task(
            task_id="task_123",
            capability="browser.screenshot",
            input_data={"url": "https://example.com"},
            account_id="acc_123",
            price_usdc=0.01
        )
        
        assert task.task_id == "task_123"
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.STANDARD
        assert task.progress == 0.0
    
    def test_task_status_enum(self):
        """Task status should have all states."""
        assert TaskStatus.QUEUED == "queued"
        assert TaskStatus.EXECUTING == "executing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
    
    def test_task_submission_validation(self):
        """Task submission should validate required fields."""
        submission = TaskSubmission(
            capability="browser.screenshot",
            input={"url": "https://example.com"}
        )
        assert submission.capability == "browser.screenshot"
        assert submission.priority == TaskPriority.STANDARD
    
    def test_task_result(self):
        """Task result should hold execution data."""
        result = TaskResult(
            data={"title": "Example"},
            screenshot="base64...",
            execution_log=[{"t": 0, "action": "start"}]
        )
        assert result.data["title"] == "Example"
        assert result.screenshot == "base64..."
    
    def test_task_proof(self):
        """Task proof should contain verification data."""
        proof = TaskProof(
            result_hash="sha256:abc123",
            signature="0x...",
            timestamp=datetime.utcnow()
        )
        assert proof.result_hash.startswith("sha256:")


class TestAccountModels:
    """Test account-related models."""
    
    def test_account_creation(self):
        """Account should be created with defaults."""
        account = Account(
            account_id="acc_123",
            api_key="ah_sk_live_xxx",
            deposit_address="0x..."
        )
        
        assert account.balance_usdc == 0.0
        assert account.reserved_usdc == 0.0
        assert account.tasks_completed == 0
    
    def test_transaction(self):
        """Transaction should record financial events."""
        tx = Transaction(
            account_id="acc_123",
            type="deposit",
            amount_usdc=10.0,
            tx_hash="0x..."
        )
        
        assert tx.type == "deposit"
        assert tx.amount_usdc == 10.0


class TestCapabilityModel:
    """Test capability model."""
    
    def test_capability_schema(self):
        """Capability should have proper schema."""
        cap = Capability(
            id="test.cap",
            name="Test Capability",
            description="A test capability",
            input_schema={"url": {"type": "string", "required": True}},
            output_description="Test output",
            price_usdc=0.01,
            estimated_time_seconds=10,
            tier=1
        )
        
        assert cap.id == "test.cap"
        assert cap.price_usdc == 0.01
        assert "url" in cap.input_schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
