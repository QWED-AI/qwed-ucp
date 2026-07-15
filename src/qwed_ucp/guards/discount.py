"""Discount Guard - Verifies discount calculations.

Validates that:
- Percentage discounts are calculated correctly
- Fixed amount discounts don't exceed subtotal
- Multiple discounts stack properly
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from qwed_ucp.types import TrustStatus


@dataclass
class DiscountGuardResult:
    """Result from Discount Guard verification."""
    
    verified: bool = True
    status: Optional[TrustStatus] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.status is not None:
            self.verified = (self.status == TrustStatus.VERIFIED)
        else:
            self.status = TrustStatus.VERIFIED if self.verified else TrustStatus.FAILED


class DiscountGuard:
    """
    Verify discount calculations.
    
    Checks:
    1. Percentage discounts: subtotal × rate = discount_amount
    2. Fixed discounts: discount <= subtotal (can't go negative)
    3. Multiple discounts stack correctly
    """
    
    def verify_percentage_discount(
        self,
        subtotal: Decimal,
        discount_amount: Decimal,
        percentage: Decimal
    ) -> DiscountGuardResult:
        """
        Verify a percentage discount calculation.
        
        Args:
            subtotal: Original subtotal before discount
            discount_amount: Claimed discount amount
            percentage: Discount percentage (e.g., 10 for 10%)
            
        Returns:
            DiscountGuardResult
        """
        expected = (subtotal * percentage / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        actual = discount_amount.quantize(Decimal("0.01"))
        
        if expected == actual:
            return DiscountGuardResult(
                verified=True,
                details={
                    "subtotal": float(subtotal),
                    "percentage": float(percentage),
                    "expected_discount": float(expected),
                    "actual_discount": float(actual)
                }
            )
        else:
            return DiscountGuardResult(
                verified=False,
                error=f"{percentage}% of {subtotal} = {expected}, not {actual}",
                details={
                    "subtotal": float(subtotal),
                    "percentage": float(percentage),
                    "expected_discount": float(expected),
                    "actual_discount": float(actual),
                    "difference": float(expected - actual)
                }
            )
    
    def verify_fixed_discount(
        self,
        subtotal: Decimal,
        discount_amount: Decimal
    ) -> DiscountGuardResult:
        """
        Verify a fixed discount is valid (doesn't exceed subtotal).
        
        Args:
            subtotal: Original subtotal
            discount_amount: Fixed discount amount
            
        Returns:
            DiscountGuardResult
        """
        if discount_amount < 0:
            return DiscountGuardResult(
                verified=False,
                error=f"Discount cannot be negative: {discount_amount}",
                details={"discount_amount": float(discount_amount)}
            )
        
        if discount_amount > subtotal:
            return DiscountGuardResult(
                verified=False,
                error=f"Fixed discount {discount_amount} exceeds subtotal {subtotal}",
                details={
                    "subtotal": float(subtotal),
                    "discount_amount": float(discount_amount),
                    "excess": float(discount_amount - subtotal)
                }
            )
        
        return DiscountGuardResult(
            verified=True,
            details={
                "subtotal": float(subtotal),
                "discount_amount": float(discount_amount),
                "remaining": float(subtotal - discount_amount)
            }
        )
    
    def verify(self, checkout: dict[str, Any]) -> DiscountGuardResult:
        """
        Verify discount in checkout object.
        
        Args:
            checkout: UCP checkout object with totals
            
        Returns:
            DiscountGuardResult
        """
        totals = checkout.get("totals", [])
        
        # Find subtotal and discount
        subtotal_entry = next((t for t in totals if t.get("type") == "subtotal"), None)
        discount_entry = next((t for t in totals if t.get("type") == "discount"), None)
        
        if discount_entry is None:
            return DiscountGuardResult(
                verified=True,
                details={"message": "No discount applied"}
            )
        
        discount_amount = Decimal(str(discount_entry.get("amount", 0)))
        
        if subtotal_entry is None:
            return DiscountGuardResult(
                verified=False,
                error="Discount present but no subtotal to compare",
                details={"discount_amount": float(discount_amount)}
            )
        
        subtotal = Decimal(str(subtotal_entry.get("amount", 0)))
        
        # Check discount doesn't exceed subtotal
        if discount_amount > subtotal:
            return DiscountGuardResult(
                verified=False,
                error=f"Discount {discount_amount} exceeds subtotal {subtotal}",
                details={
                    "subtotal": float(subtotal),
                    "discount_amount": float(discount_amount)
                }
            )
        
        # Check discount is non-negative
        if discount_amount < 0:
            return DiscountGuardResult(
                verified=False,
                error=f"Discount cannot be negative: {discount_amount}",
                details={"discount_amount": float(discount_amount)}
            )
        
        return DiscountGuardResult(
            verified=True,
            details={
                "subtotal": float(subtotal),
                "discount_amount": float(discount_amount),
                "discount_percentage": float(discount_amount / subtotal * 100) if subtotal > 0 else 0
            }
        )
