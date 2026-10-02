"""Tests for Advanced Guards - Line Items, Discount, Currency."""

from decimal import Decimal

import pytest

from qwed_ucp.guards.currency import CurrencyGuard
from qwed_ucp.guards.discount import DiscountGuard
from qwed_ucp.guards.line_items import LineItemsGuard

# =============================================================================
# Line Items Guard Tests
# =============================================================================

class TestLineItemsGuard:
    """Tests for line item calculations."""
    
    def test_single_item(self):
        """Test single item price × quantity."""
        guard = LineItemsGuard()
        
        checkout = {
            "totals": [{"type": "subtotal", "amount": 35.00}],
            "line_items": [
                {"id": "roses", "quantity": 1, "item": {"price": 35.00}}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
        assert result.details["calculated_subtotal"] == 35.00
    
    def test_multiple_items(self):
        """Test multiple items calculate correctly."""
        guard = LineItemsGuard()
        
        # 1 × $35 + 2 × $15 = $35 + $30 = $65
        checkout = {
            "totals": [{"type": "subtotal", "amount": 65.00}],
            "line_items": [
                {"id": "roses", "quantity": 1, "item": {"price": 35.00}},
                {"id": "pot", "quantity": 2, "item": {"price": 15.00}},
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
        assert result.details["calculated_subtotal"] == 65.00
    
    def test_subtotal_mismatch(self):
        """Detect when subtotal doesn't match line items."""
        guard = LineItemsGuard()
        
        checkout = {
            "totals": [{"type": "subtotal", "amount": 100.00}],  # WRONG
            "line_items": [
                {"id": "roses", "quantity": 1, "item": {"price": 35.00}}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "mismatch" in result.error.lower()
    
    def test_invalid_quantity(self):
        """Detect negative or zero quantity."""
        guard = LineItemsGuard()
        
        checkout = {
            "line_items": [
                {"id": "roses", "quantity": -1, "item": {"price": 35.00}}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "positive" in result.error.lower()
    
    def test_verify_single_item_calculation(self):
        """Test single item calculation method."""
        guard = LineItemsGuard()
        
        result = guard.verify_item(
            price=Decimal("15.00"),
            quantity=3,
            expected_total=Decimal("45.00")
        )
        assert result.verified is True
        
        # Wrong total
        result = guard.verify_item(
            price=Decimal("15.00"),
            quantity=3,
            expected_total=Decimal("50.00")  # WRONG
        )
        assert result.verified is False


# =============================================================================
# Discount Guard Tests
# =============================================================================

class TestDiscountGuard:
    """Tests for discount calculations."""
    
    def test_percentage_discount_10(self):
        """Test 10% discount calculation."""
        guard = DiscountGuard()
        
        result = guard.verify_percentage_discount(
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("10.00"),
            percentage=Decimal("10")
        )
        assert result.verified is True
    
    def test_percentage_discount_20(self):
        """Test 20% discount calculation."""
        guard = DiscountGuard()
        
        result = guard.verify_percentage_discount(
            subtotal=Decimal("85.00"),
            discount_amount=Decimal("17.00"),
            percentage=Decimal("20")
        )
        assert result.verified is True
    
    def test_percentage_discount_wrong(self):
        """Detect wrong percentage discount."""
        guard = DiscountGuard()
        
        result = guard.verify_percentage_discount(
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("15.00"),  # WRONG - should be 10
            percentage=Decimal("10")
        )
        assert result.verified is False
    
    def test_fixed_discount_valid(self):
        """Test valid fixed discount."""
        guard = DiscountGuard()
        
        result = guard.verify_fixed_discount(
            subtotal=Decimal("50.00"),
            discount_amount=Decimal("5.00")
        )
        assert result.verified is True
    
    def test_fixed_discount_exceeds_subtotal(self):
        """Detect discount that exceeds subtotal."""
        guard = DiscountGuard()
        
        result = guard.verify_fixed_discount(
            subtotal=Decimal("10.00"),
            discount_amount=Decimal("15.00")  # More than subtotal!
        )
        assert result.verified is False
        assert "exceeds" in result.error.lower()
    
    def test_checkout_with_valid_discount(self):
        """Test discount verification on checkout object."""
        guard = DiscountGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "discount", "amount": 10.00},
                {"type": "total", "amount": 90.00}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True
        assert result.details["discount_percentage"] == 10.0
    
    def test_checkout_discount_exceeds_subtotal(self):
        """Detect invalid discount in checkout."""
        guard = DiscountGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 50.00},
                {"type": "discount", "amount": 75.00}  # Exceeds subtotal!
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is False


# =============================================================================
# Currency Guard Tests
# =============================================================================

class TestCurrencyGuard:
    """Tests for currency validation."""
    
    def test_valid_usd(self):
        """Test valid USD checkout."""
        guard = CurrencyGuard()
        
        checkout = {"currency": "USD", "totals": [{"type": "total", "amount": 100.00}]}
        
        result = guard.verify(checkout)
        assert result.verified is True
        assert result.details["currency"] == "USD"
    
    def test_valid_eur(self):
        """Test valid EUR checkout."""
        guard = CurrencyGuard()
        
        checkout = {"currency": "EUR"}
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_valid_inr(self):
        """Test valid INR (Indian Rupee)."""
        guard = CurrencyGuard()
        
        checkout = {"currency": "INR"}
        
        result = guard.verify(checkout)
        assert result.verified is True
    
    def test_invalid_currency_code(self):
        """Detect invalid currency code."""
        guard = CurrencyGuard()
        
        checkout = {"currency": "DOLLARS"}  # Invalid
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "3-letter" in result.error
    
    def test_unknown_currency(self):
        """Detect unknown currency code."""
        guard = CurrencyGuard()
        
        checkout = {"currency": "XXX"}  # Unknown
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "unknown" in result.error.lower()
    
    def test_missing_currency(self):
        """Detect missing currency."""
        guard = CurrencyGuard()
        
        checkout = {"totals": []}
        
        result = guard.verify(checkout)
        assert result.verified is False
        assert "missing" in result.error.lower()
    
    def test_jpy_no_decimals(self):
        """Test JPY doesn't allow decimals."""
        guard = CurrencyGuard()
        
        # Valid - no decimals
        checkout = {"currency": "JPY", "totals": [{"type": "total", "amount": 1000}]}
        result = guard.verify(checkout)
        assert result.verified is True
        
        # Invalid - has decimals
        checkout = {"currency": "JPY", "totals": [{"type": "total", "amount": 1000.50}]}
        result = guard.verify(checkout)
        assert result.verified is False
    
    def test_currency_conversion(self):
        """Test currency conversion verification."""
        guard = CurrencyGuard()
        
        # 100 USD × 0.92 = 92 EUR
        result = guard.verify_conversion(
            amount=Decimal("100.00"),
            from_currency="USD",
            to_currency="EUR",
            converted_amount=Decimal("92.00"),
            exchange_rate=Decimal("0.92")
        )
        assert result.verified is True
        
        # Wrong conversion
        result = guard.verify_conversion(
            amount=Decimal("100.00"),
            from_currency="USD",
            to_currency="EUR",
            converted_amount=Decimal("95.00"),  # WRONG
            exchange_rate=Decimal("0.92")
        )
        assert result.verified is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
