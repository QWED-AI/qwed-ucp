"""Tests for Schema Guard - JSON schema validation."""

import pytest

from qwed_ucp.guards.schema import SchemaGuard


class TestSchemaGuardBasic:
    """Basic tests for Schema Guard."""
    
    def test_valid_checkout(self):
        """Test valid checkout passes schema validation."""
        guard = SchemaGuard()
        
        checkout = {
            "currency": "USD",
            "status": "incomplete",
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "total", "amount": 100.00}
            ],
            "line_items": [
                {"id": "item-1", "quantity": 1, "price": 100.00}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_minimal_valid_checkout(self):
        """Test minimal valid checkout (just currency)."""
        guard = SchemaGuard()
        
        checkout = {"currency": "USD"}
        
        result = guard.verify(checkout)
        assert result.verified is True


class TestSchemaGuardRequired:
    """Test required field validation."""
    
    def test_missing_currency(self):
        """Test missing required currency fails."""
        guard = SchemaGuard()
        
        checkout = {
            "status": "incomplete",
            "totals": []
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "currency" in result.error.lower()
    
    def test_invalid_currency_format(self):
        """Test invalid currency format fails."""
        guard = SchemaGuard()
        
        checkout = {
            "currency": "dollars"  # Should be 3-letter ISO code
        }
        
        result = guard.verify(checkout)
        assert result.verified is False


class TestSchemaGuardTotals:
    """Test totals array validation."""
    
    def test_valid_totals_array(self):
        """Test valid totals array passes."""
        guard = SchemaGuard()
        
        checkout = {
            "currency": "USD",
            "totals": [
                {"type": "subtotal", "amount": 50.00},
                {"type": "tax", "amount": 4.13},
                {"type": "total", "amount": 54.13}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_totals_missing_type(self):
        """Test totals item missing type fails."""
        guard = SchemaGuard()
        
        checkout = {
            "currency": "USD",
            "totals": [
                {"amount": 100.00}  # Missing "type"
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False


class TestSchemaGuardStatus:
    """Test status enum validation."""
    
    def test_valid_statuses(self):
        """Test all valid statuses pass."""
        guard = SchemaGuard()
        
        valid_statuses = ["incomplete", "ready_for_complete", "completed", "failed", "cancelled"]
        
        for status in valid_statuses:
            checkout = {"currency": "USD", "status": status}
            result = guard.verify(checkout)
            assert result.verified is True, f"Status '{status}' should be valid"
    
    def test_invalid_status(self):
        """Test invalid status fails."""
        guard = SchemaGuard()
        
        checkout = {"currency": "USD", "status": "processing"}
        
        result = guard.verify(checkout)
        assert result.verified is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
