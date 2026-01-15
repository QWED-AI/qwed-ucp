"""Tests for State Guard - Checkout state machine logic."""

import pytest

from qwed_ucp.guards.state import StateGuard


class TestStateGuardBasic:
    """Basic tests for State Guard."""
    
    def test_valid_incomplete(self):
        """Test incomplete status passes."""
        guard = StateGuard()
        
        checkout = {
            "status": "incomplete",
            "line_items": []
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_valid_ready_for_complete(self):
        """Test ready_for_complete with line items passes."""
        guard = StateGuard()
        
        checkout = {
            "status": "ready_for_complete",
            "line_items": [{"id": "item-1", "quantity": 1}]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_valid_completed(self):
        """Test completed with order passes."""
        guard = StateGuard()
        
        checkout = {
            "status": "completed",
            "line_items": [{"id": "item-1"}],
            "order": {"id": "order-123", "status": "confirmed"}
        }
        
        result = guard.verify(checkout)
        assert result.verified is True


class TestStateGuardRules:
    """Test state machine rules."""
    
    def test_completed_without_order_fails(self):
        """Test that completed status without order fails."""
        guard = StateGuard()
        
        checkout = {
            "status": "completed",
            "line_items": [{"id": "item-1"}]
            # Missing "order" object
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "order" in result.error.lower()
    
    def test_ready_without_items_fails(self):
        """Test that ready_for_complete without line items fails."""
        guard = StateGuard()
        
        checkout = {
            "status": "ready_for_complete",
            "line_items": []  # Empty
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "line_items" in result.error.lower()
    
    def test_invalid_status(self):
        """Test invalid status is rejected."""
        guard = StateGuard()
        
        checkout = {
            "status": "magic_completed",  # Invalid
            "line_items": [{"id": "item-1"}]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "invalid status" in result.error.lower()


class TestStateGuardTransitions:
    """Test state transitions."""
    
    def test_valid_transition_to_ready(self):
        """Test valid transition from incomplete to ready."""
        guard = StateGuard()
        
        result = guard.verify_transition("incomplete", "ready_for_complete")
        assert result.verified is True
    
    def test_valid_transition_to_completed(self):
        """Test valid transition from ready to completed."""
        guard = StateGuard()
        
        result = guard.verify_transition("ready_for_complete", "completed")
        assert result.verified is True
    
    def test_invalid_transition_skip(self):
        """Test invalid transition (skipping ready)."""
        guard = StateGuard()
        
        result = guard.verify_transition("incomplete", "completed")
        assert result.verified is False
    
    def test_transition_from_completed(self):
        """Test that completed is terminal."""
        guard = StateGuard()
        
        result = guard.verify_transition("completed", "incomplete")
        assert result.verified is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
