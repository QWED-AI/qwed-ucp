"""Demo: The $10 Tax Error

This demo shows how QWED-UCP catches a common AI mistake:
An AI agent calculates 10% tax instead of 8.25%, costing the business money.
"""

from decimal import Decimal

# Add parent to path for development
import sys
sys.path.insert(0, str(__file__).replace("demo/tax_error_demo.py", "src"))

from qwed_ucp.guards.money import MoneyGuard


def main():
    print("=" * 60)
    print("QWED-UCP Demo: The $10 Tax Error")
    print("=" * 60)
    print()
    
    guard = MoneyGuard()
    
    # Scenario: AI agent creates checkout for $100 item
    # Tax rate is 8.25% but AI hallucinates 10%
    
    print("📦 Scenario: Customer buying $100 item")
    print("   Tax rate: 8.25%")
    print("   Correct tax: $8.25")
    print("   Correct total: $108.25")
    print()
    
    # AI-generated checkout (WITH ERROR)
    ai_checkout = {
        "currency": "USD",
        "status": "ready_for_complete",
        "totals": [
            {"type": "subtotal", "amount": 100.00},
            {"type": "tax", "amount": 10.00},      # WRONG! AI said 10%
            {"type": "total", "amount": 110.00}    # Consistent with wrong tax
        ],
        "line_items": [{"id": "product-1", "quantity": 1, "price": 100.00}]
    }
    
    print("🤖 AI Agent Generated Checkout:")
    print(f"   Subtotal: ${ai_checkout['totals'][0]['amount']:.2f}")
    print(f"   Tax:      ${ai_checkout['totals'][1]['amount']:.2f} (AI calculated)")
    print(f"   Total:    ${ai_checkout['totals'][2]['amount']:.2f}")
    print()
    
    # Check 1: Internal math consistency
    print("🔍 Check 1: Internal Math Consistency")
    result = guard.verify(ai_checkout)
    if result.verified:
        print("   ✅ Math is internally consistent (100 + 10 = 110)")
    else:
        print(f"   ❌ Math error: {result.error}")
    print()
    
    # Check 2: Tax rate verification
    print("🔍 Check 2: Tax Rate Verification (8.25%)")
    tax_result = guard.verify_tax_rate(
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("10.00"),  # What AI claimed
        expected_rate=Decimal("0.0825")  # Actual rate
    )
    
    if tax_result.verified:
        print("   ✅ Tax rate is correct")
    else:
        print(f"   ❌ TAX ERROR CAUGHT!")
        print(f"      {tax_result.error}")
        print(f"      Expected tax: ${tax_result.details['expected_tax']}")
        print(f"      AI's tax:     ${tax_result.details['claimed_tax']}")
        print(f"      Difference:   ${tax_result.details['difference']}")
    print()
    
    # Calculate business impact
    print("=" * 60)
    print("💰 BUSINESS IMPACT")
    print("=" * 60)
    overcharge = Decimal("10.00") - Decimal("8.25")
    print(f"   Per transaction overcharge: ${overcharge}")
    print(f"   At 1,000 transactions/day: ${overcharge * 1000}/day")
    print(f"   Per year (365 days): ${overcharge * 1000 * 365}")
    print()
    print("   ⚠️  This could result in:")
    print("      - Customer complaints")
    print("      - Refund demands")
    print("      - Legal liability")
    print()
    
    print("=" * 60)
    print("✅ QWED-UCP PROTECTED YOUR BUSINESS")
    print("=" * 60)
    print("   By verifying transactions BEFORE payment,")
    print("   QWED-UCP catches AI math errors and prevents losses.")
    print()


if __name__ == "__main__":
    main()
