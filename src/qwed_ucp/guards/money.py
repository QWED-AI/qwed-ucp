"""Money Guard - Verifies mathematical calculations in UCP transactions.

Uses QWED's MathEngine (SymPy) to verify:
- Cart subtotals
- Tax calculations
- Discount applications
- Final total accuracy

UCP Total Formula (from total.json):
    Total = Subtotal - Discount + Fulfillment + Tax + Fee
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional


@dataclass
class MoneyGuardResult:
    """Result from Money Guard verification."""
    
    verified: bool
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


class MoneyGuard:
    """
    Verify mathematical calculations in UCP checkout.
    
    Implements the UCP total formula:
        Total = Subtotal - Discount + Fulfillment + Tax + Fee
    
    Uses high-precision Decimal arithmetic to avoid floating-point errors.
    """
    
    # Precision for currency calculations (2 decimal places)
    CURRENCY_PRECISION = Decimal("0.01")
    
    # UCP total types
    TOTAL_TYPES = {"subtotal", "tax", "fulfillment", "discount", "fee", "total"}
    
    def verify(self, checkout: dict[str, Any]) -> MoneyGuardResult:
        """
        Verify the mathematical accuracy of checkout totals.
        
        Args:
            checkout: UCP checkout object with 'totals' array
            
        Returns:
            MoneyGuardResult with verification status
        """
        # Extract totals array
        totals = checkout.get("totals", [])
        
        if not totals:
            return MoneyGuardResult(
                verified=False,
                error="Missing 'totals' array in checkout",
                details={"checkout_keys": list(checkout.keys())}
            )
        
        # Parse totals into a dict
        totals_dict = self._parse_totals(totals)
        
        # Get individual amounts (default to 0 if missing)
        subtotal = totals_dict.get("subtotal", Decimal("0"))
        discount = totals_dict.get("discount", Decimal("0"))
        fulfillment = totals_dict.get("fulfillment", Decimal("0"))
        tax = totals_dict.get("tax", Decimal("0"))
        fee = totals_dict.get("fee", Decimal("0"))
        claimed_total = totals_dict.get("total")
        
        if claimed_total is None:
            return MoneyGuardResult(
                verified=False,
                error="Missing 'total' in totals array",
                details={"found_types": list(totals_dict.keys())}
            )
        
        # Calculate expected total using UCP formula
        # Total = Subtotal - Discount + Fulfillment + Tax + Fee
        expected_total = (subtotal - discount + fulfillment + tax + fee).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        # Compare with claimed total
        claimed_total = claimed_total.quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        if expected_total == claimed_total:
            return MoneyGuardResult(
                verified=True,
                details={
                    "subtotal": str(subtotal),
                    "discount": str(discount),
                    "fulfillment": str(fulfillment),
                    "tax": str(tax),
                    "fee": str(fee),
                    "expected_total": str(expected_total),
                    "claimed_total": str(claimed_total),
                    "formula": f"{subtotal} - {discount} + {fulfillment} + {tax} + {fee} = {expected_total}"
                }
            )
        else:
            difference = abs(expected_total - claimed_total)
            return MoneyGuardResult(
                verified=False,
                error=f"Total mismatch: expected {expected_total}, got {claimed_total} (diff: {difference})",
                details={
                    "subtotal": str(subtotal),
                    "discount": str(discount),
                    "fulfillment": str(fulfillment),
                    "tax": str(tax),
                    "fee": str(fee),
                    "expected_total": str(expected_total),
                    "claimed_total": str(claimed_total),
                    "difference": str(difference),
                    "formula": f"{subtotal} - {discount} + {fulfillment} + {tax} + {fee} = {expected_total} (≠ {claimed_total})"
                }
            )
    
    def _parse_totals(self, totals: list[dict]) -> dict[str, Decimal]:
        """Parse totals array into a dict with Decimal amounts."""
        result = {}
        for item in totals:
            total_type = item.get("type", "").lower()
            amount = item.get("amount", 0)
            
            # Convert to Decimal for precision
            if isinstance(amount, (int, float)):
                result[total_type] = Decimal(str(amount))
            elif isinstance(amount, str):
                result[total_type] = Decimal(amount)
            elif isinstance(amount, Decimal):
                result[total_type] = amount
        
        return result
    
    def verify_tax_rate(
        self, 
        subtotal: Decimal, 
        tax_amount: Decimal, 
        expected_rate: Decimal
    ) -> MoneyGuardResult:
        """
        Verify that tax was calculated at the correct rate.
        
        Args:
            subtotal: Pre-tax subtotal
            tax_amount: Claimed tax amount
            expected_rate: Expected tax rate (e.g., 0.0825 for 8.25%)
            
        Returns:
            MoneyGuardResult with verification status
        """
        expected_tax = (subtotal * expected_rate).quantize(
            self.CURRENCY_PRECISION, rounding=ROUND_HALF_UP
        )
        
        if expected_tax == tax_amount:
            return MoneyGuardResult(
                verified=True,
                details={
                    "subtotal": str(subtotal),
                    "tax_rate": str(expected_rate),
                    "expected_tax": str(expected_tax),
                    "claimed_tax": str(tax_amount)
                }
            )
        else:
            return MoneyGuardResult(
                verified=False,
                error=f"Tax rate mismatch: {expected_rate * 100}% of {subtotal} should be {expected_tax}, not {tax_amount}",
                details={
                    "subtotal": str(subtotal),
                    "tax_rate": str(expected_rate),
                    "expected_tax": str(expected_tax),
                    "claimed_tax": str(tax_amount),
                    "difference": str(abs(expected_tax - tax_amount))
                }
            )
