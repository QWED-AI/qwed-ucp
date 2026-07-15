"""Line Items Guard - Verifies line item calculations.

Validates that:
- price × quantity = line_total for each item
- Sum of line totals = subtotal
- Quantities are positive integers
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from qwed_ucp.types import TrustStatus


@dataclass
class LineItemsGuardResult:
    """Result from Line Items Guard verification."""
    
    verified: bool = True
    status: Optional[TrustStatus] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.status is not None:
            self.verified = (self.status == TrustStatus.VERIFIED)
        else:
            self.status = TrustStatus.VERIFIED if self.verified else TrustStatus.FAILED


class LineItemsGuard:
    """
    Verify line item calculations.
    
    Checks:
    1. Each line item: price × quantity = line_total (if provided)
    2. Sum of all line items = subtotal
    3. Quantities are valid positive integers
    4. Prices are non-negative
    """
    
    def verify(self, checkout: dict[str, Any]) -> LineItemsGuardResult:
        """
        Verify line items are mathematically consistent.
        
        Args:
            checkout: UCP checkout object with line_items
            
        Returns:
            LineItemsGuardResult with verification status
        """
        line_items = checkout.get("line_items", [])
        
        if not line_items:
            return LineItemsGuardResult(
                verified=True,
                details={"message": "No line items to verify", "count": 0}
            )
        
        errors = []
        calculated_subtotal = Decimal("0")
        item_details = []
        
        for i, item in enumerate(line_items):
            item_id = item.get("id", f"item-{i}")
            quantity = item.get("quantity")
            
            # Get price from item or nested item object
            price = item.get("price")
            if price is None and "item" in item:
                price = item["item"].get("price")
            
            # Validate quantity
            if quantity is not None:
                if not isinstance(quantity, int) or quantity < 1:
                    errors.append(f"Item {item_id}: quantity must be positive integer, got {quantity}")
                    continue
            else:
                quantity = 1  # Default to 1 if not specified
            
            # Validate price
            if price is not None:
                try:
                    price_decimal = Decimal(str(price))
                    if price_decimal < 0:
                        errors.append(f"Item {item_id}: price cannot be negative ({price})")
                        continue
                except (ValueError, TypeError):
                    errors.append(f"Item {item_id}: invalid price format ({price})")
                    continue
                
                # Calculate line total
                line_total = (price_decimal * quantity).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                calculated_subtotal += line_total
                
                # Check against provided line_total if available
                provided_total = item.get("total") or item.get("line_total")
                if provided_total is not None:
                    provided_decimal = Decimal(str(provided_total)).quantize(Decimal("0.01"))
                    if line_total != provided_decimal:
                        errors.append(
                            f"Item {item_id}: {price} × {quantity} = {line_total}, "
                            f"but line_total shows {provided_decimal}"
                        )
                
                item_details.append({
                    "id": item_id,
                    "price": float(price_decimal),
                    "quantity": quantity,
                    "calculated_total": float(line_total)
                })
        
        # Check subtotal if available
        totals = checkout.get("totals", [])
        subtotal_entry = next(
            (t for t in totals if t.get("type") == "subtotal"), 
            None
        )
        
        if subtotal_entry is not None:
            provided_subtotal = Decimal(str(subtotal_entry["amount"])).quantize(Decimal("0.01"))
            calculated_subtotal = calculated_subtotal.quantize(Decimal("0.01"))
            
            if calculated_subtotal != provided_subtotal:
                errors.append(
                    f"Subtotal mismatch: sum of line items = {calculated_subtotal}, "
                    f"but subtotal shows {provided_subtotal}"
                )
        
        if errors:
            return LineItemsGuardResult(
                verified=False,
                error="; ".join(errors),
                details={
                    "errors": errors,
                    "item_count": len(line_items),
                    "calculated_subtotal": float(calculated_subtotal),
                    "items": item_details
                }
            )
        
        return LineItemsGuardResult(
            verified=True,
            details={
                "item_count": len(line_items),
                "calculated_subtotal": float(calculated_subtotal),
                "items": item_details
            }
        )
    
    def verify_item(
        self, 
        price: Decimal, 
        quantity: int, 
        expected_total: Decimal
    ) -> LineItemsGuardResult:
        """
        Verify a single line item calculation.
        
        Args:
            price: Unit price
            quantity: Number of items
            expected_total: Expected line total
            
        Returns:
            LineItemsGuardResult
        """
        calculated = (price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        expected = expected_total.quantize(Decimal("0.01"))
        
        if calculated == expected:
            return LineItemsGuardResult(
                verified=True,
                details={
                    "price": float(price),
                    "quantity": quantity,
                    "calculated": float(calculated)
                }
            )
        else:
            return LineItemsGuardResult(
                verified=False,
                error=f"{price} × {quantity} = {calculated}, not {expected}",
                details={
                    "price": float(price),
                    "quantity": quantity,
                    "calculated": float(calculated),
                    "expected": float(expected),
                    "difference": float(calculated - expected)
                }
            )
