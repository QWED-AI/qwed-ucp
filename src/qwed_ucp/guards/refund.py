"""Refund Guard - Verifies refund calculations.

Validates that:
- Full refunds match original transaction amount
- Partial refunds are calculated correctly
- Tax reversals are proportional to refund percentage

Part of QWED-UCP Deterministic Verification Engine.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from qwed_ucp.types import TrustStatus, reconcile_trust_status


@dataclass
class RefundGuardResult:
    """Result from Refund Guard verification."""
    
    verified: bool = False
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    engine: str = "QWED-Deterministic-v1"
    verification_mode: str = "deterministic"
    status: Optional[TrustStatus] = None

    def __post_init__(self):
        self.verified, self.status = reconcile_trust_status(self.verified, self.status)


class RefundGuard:
    """
    Verify refund calculations in UCP transactions.
    
    Checks:
    1. Full refunds: refund_amount == original_total
    2. Partial refunds: refund_amount == original_total × percentage
    3. Tax reversals: tax_refund == original_tax × refund_percentage
    """
    
    CURRENCY_PRECISION = Decimal("0.01")
    
    def verify_full_refund(
        self,
        original_total: Decimal,
        refund_amount: Decimal
    ) -> RefundGuardResult:
        """
        Verify a full refund equals the original transaction total.
        
        Args:
            original_total: Original transaction total
            refund_amount: Claimed refund amount
            
        Returns:
            RefundGuardResult
        """
        original = original_total.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        refund = refund_amount.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if refund == original:
            return RefundGuardResult(
                verified=True,
                details={
                    "original_total": str(original),
                    "refund_amount": str(refund),
                    "refund_type": "full"
                }
            )
        else:
            return RefundGuardResult(
                verified=False,
                error=f"Full refund mismatch: original {original}, refund {refund}",
                details={
                    "original_total": str(original),
                    "refund_amount": str(refund),
                    "difference": str(abs(original - refund))
                }
            )
    
    def verify_partial_refund(
        self,
        original_total: Decimal,
        refund_amount: Decimal,
        percentage: Decimal
    ) -> RefundGuardResult:
        """
        Verify a partial refund is calculated correctly.
        
        Args:
            original_total: Original transaction total
            refund_amount: Claimed refund amount
            percentage: Refund percentage (e.g., 50 for 50%)
            
        Returns:
            RefundGuardResult
        """
        if percentage < 0 or percentage > 100:
            return RefundGuardResult(
                verified=False,
                error=f"Invalid refund percentage: {percentage}% (must be 0-100)",
                details={"percentage": str(percentage)}
            )
        
        expected_refund = (original_total * percentage / 100).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        actual_refund = refund_amount.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if expected_refund == actual_refund:
            return RefundGuardResult(
                verified=True,
                details={
                    "original_total": str(original_total),
                    "percentage": str(percentage),
                    "expected_refund": str(expected_refund),
                    "actual_refund": str(actual_refund),
                    "refund_type": "partial"
                }
            )
        else:
            return RefundGuardResult(
                verified=False,
                error=f"{percentage}% of {original_total} = {expected_refund}, not {actual_refund}",
                details={
                    "original_total": str(original_total),
                    "percentage": str(percentage),
                    "expected_refund": str(expected_refund),
                    "actual_refund": str(actual_refund),
                    "difference": str(abs(expected_refund - actual_refund))
                }
            )
    
    def verify_tax_reversal(
        self,
        original_tax: Decimal,
        refund_tax: Decimal,
        refund_percentage: Decimal
    ) -> RefundGuardResult:
        """
        Verify tax reversal is proportional to refund percentage.
        
        Args:
            original_tax: Original tax amount
            refund_tax: Claimed tax refund
            refund_percentage: Percentage of order being refunded (e.g., 50 for 50%)
            
        Returns:
            RefundGuardResult
        """
        if refund_percentage < 0 or refund_percentage > 100:
            return RefundGuardResult(
                verified=False,
                error=f"Invalid refund percentage: {refund_percentage}%",
                details={"refund_percentage": str(refund_percentage)}
            )
        
        expected_tax_refund = (original_tax * refund_percentage / 100).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        actual_tax_refund = refund_tax.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if expected_tax_refund == actual_tax_refund:
            return RefundGuardResult(
                verified=True,
                details={
                    "original_tax": str(original_tax),
                    "refund_percentage": str(refund_percentage),
                    "expected_tax_refund": str(expected_tax_refund),
                    "actual_tax_refund": str(actual_tax_refund)
                }
            )
        else:
            return RefundGuardResult(
                verified=False,
                error=f"Tax reversal mismatch: expected {expected_tax_refund}, got {actual_tax_refund}",
                details={
                    "original_tax": str(original_tax),
                    "refund_percentage": str(refund_percentage),
                    "expected_tax_refund": str(expected_tax_refund),
                    "actual_tax_refund": str(actual_tax_refund),
                    "difference": str(abs(expected_tax_refund - actual_tax_refund))
                }
            )
    
    def verify(self, checkout: dict[str, Any], refund: dict[str, Any]) -> RefundGuardResult:
        """
        Verify a refund against an original checkout.
        
        Args:
            checkout: Original UCP checkout object
            refund: Refund object with amount and type
            
        Returns:
            RefundGuardResult
        """
        # Extract original total
        original_totals = checkout.get("totals", [])
        original_total_entry = next(
            (t for t in original_totals if t.get("type") == "total"), None
        )
        
        if original_total_entry is None:
            return RefundGuardResult(
                verified=False,
                error="Original checkout missing 'total' in totals",
                details={"checkout_keys": list(checkout.keys())}
            )
        
        original_total = Decimal(str(original_total_entry.get("amount", 0)))
        refund_amount = Decimal(str(refund.get("amount", 0)))
        refund_type = refund.get("type", "full")
        
        # Check refund doesn't exceed original
        if refund_amount > original_total:
            return RefundGuardResult(
                verified=False,
                error=f"Refund {refund_amount} exceeds original total {original_total}",
                details={
                    "original_total": str(original_total),
                    "refund_amount": str(refund_amount)
                }
            )
        
        # Verify based on type
        if refund_type == "full":
            return self.verify_full_refund(original_total, refund_amount)
        elif refund_type == "partial":
            percentage = Decimal(str(refund.get("percentage", 0)))
            return self.verify_partial_refund(original_total, refund_amount, percentage)
        else:
            return RefundGuardResult(
                verified=False,
                error=f"Unknown refund type: {refund_type}",
                details={"refund_type": refund_type}
            )
