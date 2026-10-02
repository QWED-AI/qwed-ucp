from decimal import Decimal
from typing import Any


class MoneyGuard:
    """
    Verifies cart totals deterministically using SymPy to avoid floating point errors.
    Prevents 'Math Hallucinations' in Agentic Commerce.
    """
    def verify_cart_totals(self, line_items: list[dict[str, Any]], taxes: float, discounts: float, claimed_total: float) -> dict[str, Any]:
        """
        Verifies: Sum(Items) + Tax - Discount == Total
        """
        # 1. Sum line items using Decimal for precision before symbolic conversion
        # We handle 'price' and 'quantity'
        try:
            calculated_subtotal = sum(Decimal(str(item['price'])) * Decimal(str(item['quantity'])) for item in line_items)
            
            # 2. Apply modifiers
            tax_amt = Decimal(str(taxes))
            disc_amt = Decimal(str(discounts))
            expected_total = calculated_subtotal + tax_amt - disc_amt
            
            # 3. Verify against LLM claim
            # We convert to string and then Decimal to ensure strict comparison
            claimed_decimal = Decimal(str(claimed_total))
            
            # Exact match check
            is_exact = expected_total == claimed_decimal
            
            if not is_exact:
                return {
                    "verified": False,
                    "error": f"Math Hallucination: Calculated {expected_total}, Agent claimed {claimed_total}",
                    "correction": str(expected_total),
                    "details": {
                        "subtotal": str(calculated_subtotal),
                        "tax": str(tax_amt),
                        "discount": str(disc_amt),
                        "expected": str(expected_total)
                    }
                }
                
            return {"verified": True}
            
        except Exception as e:
            return {
                "verified": False,
                "error": f"Calculation Error: {str(e)}"
            }
