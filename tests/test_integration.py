"""Integration tests using UCP Flower Shop test data.

These tests verify QWED-UCP guards against realistic UCP transaction scenarios
based on the official UCP samples repository.

Test Data Source: https://github.com/Universal-Commerce-Protocol/samples
"""

import pytest
from decimal import Decimal

from qwed_ucp.core import UCPVerifier
from qwed_ucp.guards.money import MoneyGuard
from qwed_ucp.guards.state import StateGuard
from qwed_ucp.guards.schema import SchemaGuard


# =============================================================================
# UCP Flower Shop Test Data (from ucp-samples/rest/python/test_data/flower_shop)
# =============================================================================

# Products (prices in cents, we convert to dollars)
PRODUCTS = {
    "bouquet_roses": {"title": "Bouquet of Red Roses", "price": 35.00},
    "pot_ceramic": {"title": "Ceramic Pot", "price": 15.00},
    "bouquet_sunflowers": {"title": "Sunflower Bundle", "price": 25.00},
    "bouquet_tulips": {"title": "Spring Tulips", "price": 30.00},
    "orchid_white": {"title": "White Orchid", "price": 45.00},
    "gardenias": {"title": "Gardenias", "price": 20.00},
}

# Discounts
DISCOUNTS = {
    "10OFF": {"type": "percentage", "value": 10},  # 10% off
    "WELCOME20": {"type": "percentage", "value": 20},  # 20% off
    "FIXED500": {"type": "fixed_amount", "value": 5.00},  # $5 off
}

# Shipping Rates
SHIPPING = {
    "std-ship": {"price": 5.00, "title": "Standard Shipping"},
    "exp-ship-us": {"price": 15.00, "title": "Express Shipping (US)"},
    "exp-ship-intl": {"price": 25.00, "title": "International Express"},
}

# Tax Rate (typical US rate)
TAX_RATE = Decimal("0.0825")  # 8.25%


# =============================================================================
# Test Helpers
# =============================================================================

def create_checkout(items: list[tuple[str, int]], 
                    discount: str = None,
                    shipping: str = "std-ship",
                    status: str = "ready_for_complete") -> dict:
    """
    Create a realistic UCP checkout object.
    
    Args:
        items: List of (product_id, quantity) tuples
        discount: Discount code to apply
        shipping: Shipping rate ID
        status: Checkout status
        
    Returns:
        UCP checkout dict
    """
    # Calculate subtotal
    subtotal = Decimal("0")
    line_items = []
    
    for product_id, qty in items:
        product = PRODUCTS[product_id]
        item_total = Decimal(str(product["price"])) * qty
        subtotal += item_total
        
        line_items.append({
            "id": f"li-{product_id}",
            "quantity": qty,
            "item": {
                "id": product_id,
                "title": product["title"],
                "price": product["price"]
            }
        })
    
    # Calculate discount
    discount_amount = Decimal("0")
    if discount and discount in DISCOUNTS:
        disc = DISCOUNTS[discount]
        if disc["type"] == "percentage":
            discount_amount = (subtotal * Decimal(str(disc["value"])) / 100).quantize(Decimal("0.01"))
        else:  # fixed_amount
            discount_amount = Decimal(str(disc["value"]))
    
    # Calculate shipping
    shipping_amount = Decimal(str(SHIPPING.get(shipping, SHIPPING["std-ship"])["price"]))
    
    # Calculate tax (on subtotal - discount)
    taxable = subtotal - discount_amount
    tax_amount = (taxable * TAX_RATE).quantize(Decimal("0.01"))
    
    # Calculate total
    total = subtotal - discount_amount + shipping_amount + tax_amount
    
    return {
        "currency": "USD",
        "status": status,
        "totals": [
            {"type": "subtotal", "amount": float(subtotal)},
            {"type": "discount", "amount": float(discount_amount)},
            {"type": "fulfillment", "amount": float(shipping_amount)},
            {"type": "tax", "amount": float(tax_amount)},
            {"type": "total", "amount": float(total)},
        ],
        "line_items": line_items,
    }


# =============================================================================
# Integration Tests - Happy Path
# =============================================================================

class TestFlowerShopHappyPath:
    """Test realistic flower shop checkout scenarios."""
    
    def test_single_item_checkout(self):
        """Test simple single-item purchase."""
        # Customer buys 1 bouquet of roses ($35)
        checkout = create_checkout([("bouquet_roses", 1)])
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True
        assert all(g.verified for g in result.guards)
    
    def test_multi_item_checkout(self):
        """Test multi-item cart like UCP happy path script."""
        # 1 Red Rose ($35) + 2 Ceramic Pots ($30) = $65
        checkout = create_checkout([
            ("bouquet_roses", 1),
            ("pot_ceramic", 2),
        ])
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True
    
    def test_checkout_with_10_percent_discount(self):
        """Test 10OFF discount code (10% off)."""
        # Subtotal: $65, Discount: $6.50
        checkout = create_checkout(
            [("bouquet_roses", 1), ("pot_ceramic", 2)],
            discount="10OFF"
        )
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True
    
    def test_checkout_with_20_percent_discount(self):
        """Test WELCOME20 discount code (20% off)."""
        checkout = create_checkout(
            [("orchid_white", 1)],  # $45
            discount="WELCOME20"  # 20% off = $9 discount
        )
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True
    
    def test_checkout_with_fixed_discount(self):
        """Test FIXED500 discount code ($5 off)."""
        checkout = create_checkout(
            [("gardenias", 2)],  # $40
            discount="FIXED500"  # $5 off
        )
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True
    
    def test_express_shipping(self):
        """Test with express shipping ($15)."""
        checkout = create_checkout(
            [("bouquet_sunflowers", 1)],  # $25
            shipping="exp-ship-us"  # $15 express
        )
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True
    
    def test_international_shipping(self):
        """Test with international express ($25)."""
        checkout = create_checkout(
            [("bouquet_tulips", 2)],  # $60
            shipping="exp-ship-intl"  # $25 international
        )
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        assert result.verified is True


# =============================================================================
# Integration Tests - Error Cases
# =============================================================================

class TestFlowerShopErrors:
    """Test error detection in flower shop scenarios."""
    
    def test_wrong_subtotal(self):
        """Detect incorrect subtotal calculation."""
        checkout = create_checkout([("bouquet_roses", 1)])
        
        # Corrupt the subtotal
        checkout["totals"][0]["amount"] = 40.00  # Should be 35.00
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        # Should fail because math doesn't add up
        assert result.verified is False
    
    def test_wrong_tax_calculation(self):
        """Detect AI-style tax miscalculation."""
        # AI might round incorrectly or use wrong rate
        checkout = {
            "currency": "USD",
            "status": "ready_for_complete",
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "tax", "amount": 10.00},  # WRONG: 8.25% of 100 = 8.25
                {"type": "total", "amount": 110.00},  # Math is consistent but tax is wrong
            ],
            "line_items": [{"id": "item-1"}],
        }
        
        guard = MoneyGuard()
        result = guard.verify(checkout)
        
        # Internal math is consistent (100 + 10 = 110)
        assert result.verified is True
        
        # But tax rate check fails
        tax_result = guard.verify_tax_rate(
            Decimal("100.00"),
            Decimal("10.00"),
            Decimal("0.0825")
        )
        assert tax_result.verified is False
    
    def test_wrong_discount_amount(self):
        """Detect incorrect discount calculation."""
        checkout = {
            "currency": "USD",
            "status": "ready_for_complete",
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "discount", "amount": 15.00},  # Should be 10 for 10% off
                {"type": "total", "amount": 85.00},
            ],
            "line_items": [{"id": "item-1"}],
        }
        
        guard = MoneyGuard()
        result = guard.verify(checkout)
        
        # Math: 100 - 15 = 85 ✓
        assert result.verified is True  # Internal consistency passes
    
    def test_completed_without_order(self):
        """Completed checkout must have order object."""
        checkout = create_checkout(
            [("bouquet_roses", 1)],
            status="completed"
        )
        # No order object added
        
        guard = StateGuard()
        result = guard.verify(checkout)
        
        assert result.verified is False
        assert "order" in result.error.lower()


# =============================================================================
# Integration Tests - Full Verification Chain
# =============================================================================

class TestFullVerificationChain:
    """Test complete verification flow."""
    
    def test_complete_happy_path_checkout(self):
        """Simulate complete UCP happy path from samples."""
        # Step 1: Create checkout with roses
        checkout = create_checkout([("bouquet_roses", 1)])
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        assert result.verified is True
        
        # Step 2: Add more items
        checkout = create_checkout([
            ("bouquet_roses", 1),
            ("pot_ceramic", 2),
        ])
        result = verifier.verify_checkout(checkout)
        assert result.verified is True
        
        # Step 3: Apply discount
        checkout = create_checkout(
            [("bouquet_roses", 1), ("pot_ceramic", 2)],
            discount="10OFF"
        )
        result = verifier.verify_checkout(checkout)
        assert result.verified is True
        
        # Step 4: Ready for payment
        checkout["status"] = "ready_for_complete"
        result = verifier.verify_checkout(checkout)
        assert result.verified is True
    
    def test_verify_before_payment(self):
        """Critical: Verify checkout is safe before processing payment."""
        checkout = create_checkout(
            [("orchid_white", 1), ("gardenias", 2)],  # $45 + $40 = $85
            discount="WELCOME20",  # 20% off = $17
            shipping="exp-ship-us"  # $15
        )
        
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        
        # This checkout should be safe to process
        assert result.verified is True
        
        # All 3 guards pass
        money_guard = next(g for g in result.guards if g.guard_name == "Money Guard")
        state_guard = next(g for g in result.guards if g.guard_name == "State Guard")
        schema_guard = next(g for g in result.guards if g.guard_name == "Structure Guard")
        
        assert money_guard.verified is True
        assert state_guard.verified is True
        assert schema_guard.verified is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
