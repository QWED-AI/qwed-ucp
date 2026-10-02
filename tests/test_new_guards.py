"""Tests for New Guards - Refund, Tip, Fee."""

from decimal import Decimal

import pytest

from qwed_ucp.guards.fee import FeeGuard
from qwed_ucp.guards.refund import RefundGuard
from qwed_ucp.guards.tip import TipGuard

# =============================================================================
# Refund Guard Tests
# =============================================================================

class TestRefundGuard:
    """Tests for refund calculations."""
    
    def test_full_refund_valid(self):
        """Test full refund equals original total."""
        guard = RefundGuard()
        
        result = guard.verify_full_refund(
            original_total=Decimal("100.00"),
            refund_amount=Decimal("100.00")
        )
        assert result.verified is True
        assert result.details["refund_type"] == "full"
    
    def test_full_refund_mismatch(self):
        """Detect when full refund doesn't match."""
        guard = RefundGuard()
        
        result = guard.verify_full_refund(
            original_total=Decimal("100.00"),
            refund_amount=Decimal("99.00")
        )
        assert result.verified is False
        assert "mismatch" in result.error.lower()
    
    def test_partial_refund_50_percent(self):
        """Test 50% partial refund."""
        guard = RefundGuard()
        
        result = guard.verify_partial_refund(
            original_total=Decimal("100.00"),
            refund_amount=Decimal("50.00"),
            percentage=Decimal("50")
        )
        assert result.verified is True
        assert result.details["refund_type"] == "partial"
    
    def test_partial_refund_wrong(self):
        """Detect wrong partial refund calculation."""
        guard = RefundGuard()
        
        result = guard.verify_partial_refund(
            original_total=Decimal("100.00"),
            refund_amount=Decimal("60.00"),  # Wrong - should be 50
            percentage=Decimal("50")
        )
        assert result.verified is False
    
    def test_partial_refund_invalid_percentage(self):
        """Detect invalid refund percentage."""
        guard = RefundGuard()
        
        result = guard.verify_partial_refund(
            original_total=Decimal("100.00"),
            refund_amount=Decimal("150.00"),
            percentage=Decimal("150")  # Invalid
        )
        assert result.verified is False
        assert "invalid" in result.error.lower()
    
    def test_tax_reversal(self):
        """Test proportional tax reversal."""
        guard = RefundGuard()
        
        result = guard.verify_tax_reversal(
            original_tax=Decimal("10.00"),
            refund_tax=Decimal("5.00"),
            refund_percentage=Decimal("50")
        )
        assert result.verified is True
    
    def test_verify_checkout_refund(self):
        """Test refund verification on checkout object."""
        guard = RefundGuard()
        
        checkout = {
            "totals": [{"type": "total", "amount": 100.00}]
        }
        
        refund = {"amount": 100.00, "type": "full"}
        
        result = guard.verify(checkout, refund)
        assert result.verified is True
    
    def test_refund_exceeds_original(self):
        """Detect refund that exceeds original."""
        guard = RefundGuard()
        
        checkout = {
            "totals": [{"type": "total", "amount": 100.00}]
        }
        
        refund = {"amount": 150.00, "type": "full"}
        
        result = guard.verify(checkout, refund)
        assert result.verified is False
        assert "exceeds" in result.error.lower()


# =============================================================================
# Tip Guard Tests
# =============================================================================

class TestTipGuard:
    """Tests for tip calculations."""
    
    def test_percentage_tip_18(self):
        """Test 18% pre-tax tip."""
        guard = TipGuard()
        
        result = guard.verify_percentage_tip(
            subtotal=Decimal("50.00"),
            tip_amount=Decimal("9.00"),
            percentage=Decimal("18")
        )
        assert result.verified is True
        assert result.details["tip_type"] == "pre-tax"
    
    def test_percentage_tip_20(self):
        """Test 20% pre-tax tip."""
        guard = TipGuard()
        
        result = guard.verify_percentage_tip(
            subtotal=Decimal("100.00"),
            tip_amount=Decimal("20.00"),
            percentage=Decimal("20")
        )
        assert result.verified is True
    
    def test_percentage_tip_wrong(self):
        """Detect wrong tip calculation."""
        guard = TipGuard()
        
        result = guard.verify_percentage_tip(
            subtotal=Decimal("50.00"),
            tip_amount=Decimal("15.00"),  # Wrong - should be 9
            percentage=Decimal("18")
        )
        assert result.verified is False
    
    def test_post_tax_tip(self):
        """Test post-tax tip calculation."""
        guard = TipGuard()
        
        result = guard.verify_post_tax_tip(
            total=Decimal("108.00"),
            tip_amount=Decimal("21.60"),  # 20% of 108
            percentage=Decimal("20")
        )
        assert result.verified is True
        assert result.details["tip_type"] == "post-tax"
    
    def test_tip_bounds_valid(self):
        """Test tip within bounds."""
        guard = TipGuard()
        
        result = guard.verify_tip_bounds(
            tip_amount=Decimal("20.00"),
            base_amount=Decimal("100.00")
        )
        assert result.verified is True
    
    def test_tip_exceeds_base(self):
        """Detect tip exceeding 100% of base."""
        guard = TipGuard()
        
        result = guard.verify_tip_bounds(
            tip_amount=Decimal("150.00"),
            base_amount=Decimal("100.00")
        )
        assert result.verified is False
        assert "exceeds" in result.error.lower()
    
    def test_negative_tip(self):
        """Detect negative tip."""
        guard = TipGuard()
        
        result = guard.verify_tip_bounds(
            tip_amount=Decimal("-10.00"),
            base_amount=Decimal("100.00")
        )
        assert result.verified is False
        assert "negative" in result.error.lower()
    
    def test_verify_checkout_tip(self):
        """Test tip verification on checkout object."""
        guard = TipGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "tip", "amount": 20.00}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True


# =============================================================================
# Fee Guard Tests
# =============================================================================

class TestFeeGuard:
    """Tests for fee calculations."""
    
    def test_service_fee_5_percent(self):
        """Test 5% service fee."""
        guard = FeeGuard()
        
        result = guard.verify_service_fee(
            subtotal=Decimal("100.00"),
            fee_amount=Decimal("5.00"),
            percentage=Decimal("5")
        )
        assert result.verified is True
        assert result.details["fee_type"] == "service"
    
    def test_service_fee_wrong(self):
        """Detect wrong service fee calculation."""
        guard = FeeGuard()
        
        result = guard.verify_service_fee(
            subtotal=Decimal("100.00"),
            fee_amount=Decimal("10.00"),  # Wrong - should be 5
            percentage=Decimal("5")
        )
        assert result.verified is False
    
    def test_delivery_fee_distance(self):
        """Test distance-based delivery fee."""
        guard = FeeGuard()
        
        # 5km × $2/km = $10
        result = guard.verify_delivery_fee(
            claimed_fee=Decimal("10.00"),
            distance_km=Decimal("5"),
            rate_per_km=Decimal("2.00")
        )
        assert result.verified is True
        assert result.details["fee_type"] == "delivery"
    
    def test_delivery_fee_with_base(self):
        """Test delivery fee with base fee."""
        guard = FeeGuard()
        
        # $3 base + 5km × $2/km = $13
        result = guard.verify_delivery_fee(
            claimed_fee=Decimal("13.00"),
            distance_km=Decimal("5"),
            rate_per_km=Decimal("2.00"),
            base_fee=Decimal("3.00")
        )
        assert result.verified is True
    
    def test_delivery_fee_wrong(self):
        """Detect wrong delivery fee."""
        guard = FeeGuard()
        
        result = guard.verify_delivery_fee(
            claimed_fee=Decimal("15.00"),  # Wrong
            distance_km=Decimal("5"),
            rate_per_km=Decimal("2.00")
        )
        assert result.verified is False
    
    def test_platform_fee_within_bounds(self):
        """Test platform fee within bounds."""
        guard = FeeGuard()
        
        result = guard.verify_platform_fee(
            fee_amount=Decimal("15.00"),
            subtotal=Decimal("100.00"),
            max_percentage=Decimal("30")
        )
        assert result.verified is True
    
    def test_platform_fee_exceeds_max(self):
        """Detect platform fee exceeding max."""
        guard = FeeGuard()
        
        result = guard.verify_platform_fee(
            fee_amount=Decimal("50.00"),  # 50% - exceeds 30% max
            subtotal=Decimal("100.00"),
            max_percentage=Decimal("30")
        )
        assert result.verified is False
        assert "exceeds" in result.error.lower()
    
    def test_verify_checkout_fee(self):
        """Test fee verification on checkout object."""
        guard = FeeGuard()
        
        checkout = {
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "fee", "amount": 15.00}
            ]
        }
        
        result = guard.verify(checkout)
        assert result.verified is True


# =============================================================================
# Engine Field Tests
# =============================================================================

class TestEngineFields:
    """Test that all guards include engine and verification_mode."""
    
    def test_refund_guard_engine_field(self):
        """RefundGuard includes engine field."""
        guard = RefundGuard()
        result = guard.verify_full_refund(
            Decimal("100.00"), Decimal("100.00")
        )
        assert result.engine == "QWED-Deterministic-v1"
        assert result.verification_mode == "deterministic"
    
    def test_tip_guard_engine_field(self):
        """TipGuard includes engine field."""
        guard = TipGuard()
        result = guard.verify_tip_bounds(
            Decimal("20.00"), Decimal("100.00")
        )
        assert result.engine == "QWED-Deterministic-v1"
        assert result.verification_mode == "deterministic"
    
    def test_fee_guard_engine_field(self):
        """FeeGuard includes engine field."""
        guard = FeeGuard()
        result = guard.verify_platform_fee(
            Decimal("10.00"), Decimal("100.00")
        )
        assert result.engine == "QWED-Deterministic-v1"
        assert result.verification_mode == "deterministic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
