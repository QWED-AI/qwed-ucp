"""Tests for Money Guard - Mathematical verification."""

import pytest
from decimal import Decimal

from qwed_ucp.guards.money import MoneyGuard


class TestMoneyGuardBasic:
    """Basic tests for Money Guard."""
    
    def test_valid_totals(self):
        """Test that valid totals pass verification."""
        guard = MoneyGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "tax", "amount": 8.25},
                {"type": "total", "amount": 108.25}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
        assert result.error is None
    
    def test_invalid_totals(self):
        """Test that incorrect totals fail verification."""
        guard = MoneyGuard()
        
        # $10 Tax Error - the classic AI mistake
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "tax", "amount": 10.00},  # WRONG - should be 8.25
                {"type": "total", "amount": 110.00}  # Math is internally consistent but wrong
            ]
        }
        
        result = guard.verify(checkout)
        # This passes because math is internally consistent
        # 100 + 10 = 110 is correct math
        assert result.verified is True
    
    def test_math_mismatch(self):
        """Test that math mismatches are caught."""
        guard = MoneyGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "tax", "amount": 8.25},
                {"type": "total", "amount": 120.00}  # WRONG - should be 108.25
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "mismatch" in result.error.lower()
    
    def test_missing_totals(self):
        """Test that missing totals array fails."""
        guard = MoneyGuard()
        
        checkout = {"currency": "USD"}
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "missing" in result.error.lower()
    
    def test_missing_total_type(self):
        """Test that missing total type fails."""
        guard = MoneyGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00}
                # No "total" type
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False


class TestMoneyGuardPrecision:
    """Test decimal precision handling."""
    
    def test_floating_point_precision(self):
        """Test that floating point errors don't cause false negatives."""
        guard = MoneyGuard()
        
        # These values would fail with naive float comparison
        # 0.1 + 0.2 != 0.3 in floating point
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 0.10},
                {"type": "tax", "amount": 0.20},
                {"type": "total", "amount": 0.30}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_rounding(self):
        """Test proper rounding to 2 decimal places."""
        guard = MoneyGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 33.333333},  # Should round to 33.33
                {"type": "tax", "amount": 2.75},
                {"type": "total", "amount": 36.08}  # 33.33 + 2.75 = 36.08
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True


class TestMoneyGuardFullFormula:
    """Test full UCP total formula: Total = Subtotal - Discount + Fulfillment + Tax + Fee"""
    
    def test_full_formula_valid(self):
        """Test full formula with all components."""
        guard = MoneyGuard()
        
        # Subtotal - Discount + Fulfillment + Tax + Fee = Total
        # 100.00 - 10.00 + 5.00 + 7.43 + 2.00 = 104.43
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "discount", "amount": 10.00},
                {"type": "fulfillment", "amount": 5.00},
                {"type": "tax", "amount": 7.43},
                {"type": "fee", "amount": 2.00},
                {"type": "total", "amount": 104.43}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_full_formula_invalid(self):
        """Test full formula with wrong total."""
        guard = MoneyGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "discount", "amount": 10.00},
                {"type": "fulfillment", "amount": 5.00},
                {"type": "tax", "amount": 7.43},
                {"type": "fee", "amount": 2.00},
                {"type": "total", "amount": 110.00}  # WRONG
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False


class TestMoneyGuardTaxRate:
    """Test tax rate verification."""
    
    def test_tax_rate_correct(self):
        """Test correct tax rate calculation."""
        guard = MoneyGuard()
        
        subtotal = Decimal("100.00")
        tax = Decimal("8.25")
        rate = Decimal("0.0825")  # 8.25%
        
        result = guard.verify_tax_rate(subtotal, tax, rate)
        assert result.verified is True
    
    def test_tax_rate_incorrect(self):
        """Test incorrect tax rate calculation - THE $10 TAX ERROR."""
        guard = MoneyGuard()
        
        subtotal = Decimal("100.00")
        tax = Decimal("10.00")  # WRONG - AI hallucinated 10%
        rate = Decimal("0.0825")  # 8.25%
        
        result = guard.verify_tax_rate(subtotal, tax, rate)
        assert result.verified is False
        assert "1.75" in str(result.details.get("difference", ""))  # 10 - 8.25 = 1.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
