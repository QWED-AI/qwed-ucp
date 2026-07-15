"""Fee Guard - Verifies fee calculations.

Validates that:
- Service fees are calculated correctly
- Delivery fees match distance-based rates
- Platform fees are within valid bounds

Part of QWED-UCP Deterministic Verification Engine.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from qwed_ucp.types import TrustStatus


@dataclass
class FeeGuardResult:
    """Result from Fee Guard verification."""
    
    verified: bool = True
    status: Optional[TrustStatus] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    engine: str = "QWED-Deterministic-v1"
    verification_mode: str = "deterministic"

    def __post_init__(self):
        if self.status is not None:
            self.verified = (self.status == TrustStatus.VERIFIED)
        else:
            self.status = TrustStatus.VERIFIED if self.verified else TrustStatus.FAILED


class FeeGuard:
    """
    Verify fee calculations in UCP transactions.
    
    Checks:
    1. Service fees: fee_amount == subtotal × percentage
    2. Delivery fees: fee_amount == distance × rate_per_km
    3. Platform fees: fee >= 0 and within bounds
    """
    
    CURRENCY_PRECISION = Decimal("0.01")
    
    def verify_service_fee(
        self,
        subtotal: Decimal,
        fee_amount: Decimal,
        percentage: Decimal
    ) -> FeeGuardResult:
        """
        Verify service fee calculated as percentage of subtotal.
        
        Args:
            subtotal: Order subtotal
            fee_amount: Claimed service fee
            percentage: Fee percentage (e.g., 5 for 5%)
            
        Returns:
            FeeGuardResult
        """
        if percentage < 0:
            return FeeGuardResult(
                verified=False,
                error=f"Fee percentage cannot be negative: {percentage}%",
                details={"percentage": str(percentage)}
            )
        
        expected_fee = (subtotal * percentage / 100).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        actual_fee = fee_amount.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if expected_fee == actual_fee:
            return FeeGuardResult(
                verified=True,
                details={
                    "subtotal": str(subtotal),
                    "percentage": str(percentage),
                    "expected_fee": str(expected_fee),
                    "actual_fee": str(actual_fee),
                    "fee_type": "service"
                }
            )
        else:
            return FeeGuardResult(
                verified=False,
                error=f"{percentage}% of {subtotal} = {expected_fee}, not {actual_fee}",
                details={
                    "subtotal": str(subtotal),
                    "percentage": str(percentage),
                    "expected_fee": str(expected_fee),
                    "actual_fee": str(actual_fee),
                    "difference": str(abs(expected_fee - actual_fee))
                }
            )
    
    def verify_delivery_fee(
        self,
        claimed_fee: Decimal,
        distance_km: Decimal,
        rate_per_km: Decimal,
        base_fee: Decimal = Decimal("0")
    ) -> FeeGuardResult:
        """
        Verify delivery fee based on distance and rate.
        
        Formula: fee = base_fee + (distance × rate_per_km)
        
        Args:
            claimed_fee: Claimed delivery fee
            distance_km: Delivery distance in kilometers
            rate_per_km: Rate per kilometer
            base_fee: Base delivery fee (optional)
            
        Returns:
            FeeGuardResult
        """
        if distance_km < 0:
            return FeeGuardResult(
                verified=False,
                error=f"Distance cannot be negative: {distance_km}km",
                details={"distance_km": str(distance_km)}
            )
        
        if rate_per_km < 0:
            return FeeGuardResult(
                verified=False,
                error=f"Rate per km cannot be negative: {rate_per_km}",
                details={"rate_per_km": str(rate_per_km)}
            )
        
        expected_fee = (base_fee + distance_km * rate_per_km).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        actual_fee = claimed_fee.quantize(self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
        
        if expected_fee == actual_fee:
            return FeeGuardResult(
                verified=True,
                details={
                    "base_fee": str(base_fee),
                    "distance_km": str(distance_km),
                    "rate_per_km": str(rate_per_km),
                    "expected_fee": str(expected_fee),
                    "actual_fee": str(actual_fee),
                    "fee_type": "delivery",
                    "formula": f"{base_fee} + ({distance_km} × {rate_per_km}) = {expected_fee}"
                }
            )
        else:
            return FeeGuardResult(
                verified=False,
                error=f"Delivery fee mismatch: expected {expected_fee}, got {actual_fee}",
                details={
                    "base_fee": str(base_fee),
                    "distance_km": str(distance_km),
                    "rate_per_km": str(rate_per_km),
                    "expected_fee": str(expected_fee),
                    "actual_fee": str(actual_fee),
                    "difference": str(abs(expected_fee - actual_fee))
                }
            )
    
    def verify_platform_fee(
        self,
        fee_amount: Decimal,
        subtotal: Decimal,
        max_percentage: Decimal = Decimal("30")
    ) -> FeeGuardResult:
        """
        Verify platform fee is within reasonable bounds.
        
        Args:
            fee_amount: Claimed platform fee
            subtotal: Order subtotal
            max_percentage: Maximum allowed percentage (default 30%)
            
        Returns:
            FeeGuardResult
        """
        if fee_amount < 0:
            return FeeGuardResult(
                verified=False,
                error=f"Platform fee cannot be negative: {fee_amount}",
                details={"fee_amount": str(fee_amount)}
            )
        
        max_fee = (subtotal * max_percentage / 100).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        if fee_amount > max_fee:
            return FeeGuardResult(
                verified=False,
                error=f"Platform fee {fee_amount} exceeds {max_percentage}% of subtotal ({max_fee})",
                details={
                    "fee_amount": str(fee_amount),
                    "subtotal": str(subtotal),
                    "max_percentage": str(max_percentage),
                    "max_fee": str(max_fee)
                }
            )
        
        fee_percentage = (fee_amount / subtotal * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if subtotal > 0 else Decimal("0")
        
        return FeeGuardResult(
            verified=True,
            details={
                "fee_amount": str(fee_amount),
                "subtotal": str(subtotal),
                "fee_percentage": str(fee_percentage),
                "fee_type": "platform"
            }
        )
    
    def verify(self, checkout: dict[str, Any]) -> FeeGuardResult:
        """
        Verify fees in checkout object.
        
        Args:
            checkout: UCP checkout object with totals
            
        Returns:
            FeeGuardResult
        """
        totals = checkout.get("totals", [])
        
        fee_entry = next((t for t in totals if t.get("type") == "fee"), None)
        
        if fee_entry is None:
            return FeeGuardResult(
                verified=True,
                details={"message": "No fee in checkout"}
            )
        
        fee_amount = Decimal(str(fee_entry.get("amount", 0)))
        
        # Fees must be non-negative
        if fee_amount < 0:
            return FeeGuardResult(
                verified=False,
                error=f"Fee cannot be negative: {fee_amount}",
                details={"fee_amount": str(fee_amount)}
            )
        
        # Find subtotal for percentage check
        subtotal_entry = next((t for t in totals if t.get("type") == "subtotal"), None)
        
        if subtotal_entry is not None:
            subtotal = Decimal(str(subtotal_entry.get("amount", 0)))
            return self.verify_platform_fee(fee_amount, subtotal)
        
        return FeeGuardResult(
            verified=True,
            details={
                "fee_amount": str(fee_amount),
                "message": "Fee verified (no subtotal for percentage check)"
            }
        )
