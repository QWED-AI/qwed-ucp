"""Tip Guard - Verifies tip calculations.

Validates that:
- Percentage tips are calculated correctly (pre or post-tax)
- Tips are within reasonable bounds (0-100% of amount)
- Tip amounts are non-negative

Part of QWED-UCP Deterministic Verification Engine.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from qwed_ucp.types import TrustStatus, reconcile_trust_status


@dataclass
class TipGuardResult:
    """Result from Tip Guard verification."""
    
    verified: bool = False
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    engine: str = "QWED-Deterministic-v1"
    verification_mode: str = "deterministic"
    status: Optional[TrustStatus] = None

    def __post_init__(self):
        self.verified, self.status = reconcile_trust_status(self.verified, self.status)


class TipGuard:
    """
    Verify tip calculations in UCP transactions.
    
    Checks:
    1. Pre-tax tip: tip_amount == subtotal × percentage
    2. Post-tax tip: tip_amount == total × percentage
    3. Tip bounds: 0 <= tip_amount <= 100% of base amount
    """
    
    CURRENCY_PRECISION = Decimal("0.01")
    MAX_TIP_PERCENTAGE = Decimal("100")  # 100% max tip
    
    def verify_percentage_tip(
        self,
        subtotal: Decimal,
        tip_amount: Decimal,
        percentage: Decimal
    ) -> TipGuardResult:
        """
        Verify tip calculated as percentage of subtotal (pre-tax).
        
        Args:
            subtotal: Pre-tax subtotal
            tip_amount: Claimed tip amount
            percentage: Tip percentage (e.g., 18 for 18%)
            
        Returns:
            TipGuardResult
        """
        if percentage < 0:
            return TipGuardResult(
                verified=False,
                error=f"Tip percentage cannot be negative: {percentage}%",
                details={"percentage": str(percentage)}
            )
        
        if percentage > self.MAX_TIP_PERCENTAGE:
            return TipGuardResult(
                verified=False,
                error=f"Tip percentage exceeds maximum: {percentage}% > {self.MAX_TIP_PERCENTAGE}%",
                details={"percentage": str(percentage), "max": str(self.MAX_TIP_PERCENTAGE)}
            )
        
        expected_tip = (subtotal * percentage / 100).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        actual_tip = tip_amount.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if expected_tip == actual_tip:
            return TipGuardResult(
                verified=True,
                details={
                    "subtotal": str(subtotal),
                    "percentage": str(percentage),
                    "expected_tip": str(expected_tip),
                    "actual_tip": str(actual_tip),
                    "tip_type": "pre-tax"
                }
            )
        else:
            return TipGuardResult(
                verified=False,
                error=f"{percentage}% of {subtotal} = {expected_tip}, not {actual_tip}",
                details={
                    "subtotal": str(subtotal),
                    "percentage": str(percentage),
                    "expected_tip": str(expected_tip),
                    "actual_tip": str(actual_tip),
                    "difference": str(abs(expected_tip - actual_tip))
                }
            )
    
    def verify_post_tax_tip(
        self,
        total: Decimal,
        tip_amount: Decimal,
        percentage: Decimal
    ) -> TipGuardResult:
        """
        Verify tip calculated as percentage of total (post-tax).
        
        Args:
            total: Post-tax total (before tip)
            tip_amount: Claimed tip amount
            percentage: Tip percentage (e.g., 20 for 20%)
            
        Returns:
            TipGuardResult
        """
        if percentage < 0:
            return TipGuardResult(
                verified=False,
                error=f"Tip percentage cannot be negative: {percentage}%",
                details={"percentage": str(percentage)}
            )
        
        if percentage > self.MAX_TIP_PERCENTAGE:
            return TipGuardResult(
                verified=False,
                error=f"Tip percentage exceeds maximum: {percentage}% > {self.MAX_TIP_PERCENTAGE}%",
                details={"percentage": str(percentage)}
            )
        
        expected_tip = (total * percentage / 100).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        actual_tip = tip_amount.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if expected_tip == actual_tip:
            return TipGuardResult(
                verified=True,
                details={
                    "total": str(total),
                    "percentage": str(percentage),
                    "expected_tip": str(expected_tip),
                    "actual_tip": str(actual_tip),
                    "tip_type": "post-tax"
                }
            )
        else:
            return TipGuardResult(
                verified=False,
                error=f"{percentage}% of {total} = {expected_tip}, not {actual_tip}",
                details={
                    "total": str(total),
                    "percentage": str(percentage),
                    "expected_tip": str(expected_tip),
                    "actual_tip": str(actual_tip),
                    "difference": str(abs(expected_tip - actual_tip))
                }
            )
    
    def verify_tip_bounds(
        self,
        tip_amount: Decimal,
        base_amount: Decimal
    ) -> TipGuardResult:
        """
        Verify tip is within reasonable bounds.
        
        Args:
            tip_amount: Claimed tip amount
            base_amount: Base amount (subtotal or total)
            
        Returns:
            TipGuardResult
        """
        if tip_amount < 0:
            return TipGuardResult(
                verified=False,
                error=f"Tip cannot be negative: {tip_amount}",
                details={"tip_amount": str(tip_amount)}
            )
        
        max_tip = base_amount  # 100% of base
        
        if tip_amount > max_tip:
            return TipGuardResult(
                verified=False,
                error=f"Tip {tip_amount} exceeds 100% of base amount {base_amount}",
                details={
                    "tip_amount": str(tip_amount),
                    "base_amount": str(base_amount),
                    "max_allowed": str(max_tip)
                }
            )
        
        tip_percentage = (tip_amount / base_amount * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if base_amount > 0 else Decimal("0")
        
        return TipGuardResult(
            verified=True,
            details={
                "tip_amount": str(tip_amount),
                "base_amount": str(base_amount),
                "tip_percentage": str(tip_percentage)
            }
        )
    
    def verify(self, checkout: dict[str, Any]) -> TipGuardResult:
        """
        Verify tip in checkout object.
        
        Args:
            checkout: UCP checkout object with totals including tip
            
        Returns:
            TipGuardResult
        """
        totals = checkout.get("totals", [])
        
        tip_entry = next((t for t in totals if t.get("type") == "tip"), None)
        
        if tip_entry is None:
            return TipGuardResult(
                verified=True,
                details={"message": "No tip in checkout"}
            )
        
        tip_amount = Decimal(str(tip_entry.get("amount", 0)))
        
        # Find subtotal for bounds check
        subtotal_entry = next((t for t in totals if t.get("type") == "subtotal"), None)
        
        if subtotal_entry is None:
            return TipGuardResult(
                verified=False,
                error="Tip present but no subtotal to validate against",
                details={"tip_amount": str(tip_amount)}
            )
        
        subtotal = Decimal(str(subtotal_entry.get("amount", 0)))
        
        return self.verify_tip_bounds(tip_amount, subtotal)
