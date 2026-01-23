# QWED-UCP 🛒

**Deterministic Verification for Universal Commerce Protocol (UCP) Transactions**

[![PyPI](https://img.shields.io/pypi/v/qwed-ucp?color=blue&label=PyPI)](https://pypi.org/project/qwed-ucp/)
[![CI](https://github.com/QWED-AI/qwed-ucp/actions/workflows/ci.yml/badge.svg)](https://github.com/QWED-AI/qwed-ucp/actions)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![GitHub stars](https://img.shields.io/github/stars/QWED-AI/qwed-ucp?style=social)](https://github.com/QWED-AI/qwed-ucp)
[![Verified by QWED](https://img.shields.io/badge/Verified_by-QWED-00C853?style=flat&logo=checkmarx)](https://github.com/QWED-AI/qwed-verification)

> **Verify AI agent commerce before the money moves.**

QWED-UCP is a verification layer for Google's [Universal Commerce Protocol](https://ucp.dev), ensuring AI agent e-commerce transactions are mathematically correct and structurally valid.

---

## 🚨 The Problem

AI agents (like Gemini, ChatGPT) are now handling e-commerce transactions:
- Cart totals and subtotals
- Tax calculations
- Discount math
- Refunds and fees

**Problem:** AI agents hallucinate on math.

| Scenario | LLM Output | Reality |
|----------|------------|---------|
| 10% off $99.99 | "$10.00 discount" | $9.999 → $10.00 ✅ |
| 8.25% tax on $100 | "$8.00 tax" | $8.25 ❌ |
| Cart: $50 + $30 + $20 | "$110.00 total" | $100.00 ❌ |
| Subtotal - Discount + Tax | Wrong order | Math error ❌ |

---

## 💡 What QWED-UCP Is (and Isn't)

### ✅ QWED-UCP IS:
- **Verification middleware** that checks AI-generated UCP checkouts
- **Deterministic** — uses Decimal math (no floating-point errors) and Z3 proofs
- **Open source** — integrate into any e-commerce workflow
- **A safety layer** — catches calculation errors before payment processing

### ❌ QWED-UCP is NOT:
- ~~A shopping cart~~ — use Shopify, WooCommerce, or Stripe for that
- ~~A payment processor~~ — use Stripe, Adyen, or Square for that
- ~~A fraud detection system~~ — use Sift, Signifyd, or Riskified for that
- ~~A replacement for e-commerce platforms~~ — we just verify the math

> **Think of QWED-UCP as the "accountant" that reviews every AI checkout before it goes to payment.**
> 
> Shopify builds carts. Stripe processes payments. **QWED verifies the math.**

---

## 🆚 How We're Different from E-Commerce Platforms

| Aspect | Shopify / Stripe / Adyen | QWED-UCP |
|--------|--------------------------|----------|
| **Purpose** | Build carts, process payments | Verify calculations |
| **Approach** | Trust AI outputs | Mathematically verify AI outputs |
| **Accuracy** | ~99% (edge cases fail) | 100% deterministic |
| **Tech** | Standard floating-point | Decimal + SymPy + Z3 |
| **Integration** | Replace your stack | Sits between AI and payment |
| **Pricing** | Transaction fees | Free (Apache 2.0) |

### Use Together (Best Practice)
```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   AI Agent   │ ──► │  QWED-UCP   │ ──► │    Stripe    │
│ (checkout)   │     │  (verifies) │     │  (payment)   │
└──────────────┘     └─────────────┘     └──────────────┘
```

---

## 🛡️ The Guards

| Guard | Engine | Verifies |
|-------|--------|----------|
| **Money Guard** | Decimal + SymPy | Cart totals, UCP formula: `Total = Subtotal - Discount + Fulfillment + Tax + Fee` |
| **State Guard** | Z3 SMT Solver | Checkout state machine logic (draft → ready → complete) |
| **Structure Guard** | JSON Schema | UCP schema compliance (v1.0) |
| **Discount Guard** | Decimal | Percentage and fixed discount calculations |
| **Currency Guard** | Decimal | Currency precision, $0.01 rounding |
| **Line Item Guard** | SymPy | Item quantity × price = line total |

---

## 🚀 Quick Start

### Installation

```bash
pip install qwed-ucp
```

### Basic Usage

```python
from qwed_ucp import UCPVerifier

verifier = UCPVerifier()

checkout = {
    "currency": "USD",
    "totals": [
        {"type": "subtotal", "amount": 100.00},
        {"type": "tax", "amount": 8.25},
        {"type": "total", "amount": 108.25}
    ],
    "status": "ready_for_complete"
}

result = verifier.verify_checkout(checkout)

if result.verified:
    print("✅ Transaction verified - safe to process!")
else:
    print(f"❌ Verification failed: {result.error}")
```

### Verify Tax Rate

```python
from qwed_ucp import MoneyGuard
from decimal import Decimal

guard = MoneyGuard()

result = guard.verify_tax_rate(
    subtotal=Decimal("100.00"),
    tax_amount=Decimal("8.25"),
    expected_rate=Decimal("0.0825")  # 8.25%
)

print(result.verified)  # True ✅
```

### Verify Discounts

```python
from qwed_ucp import DiscountGuard
from decimal import Decimal

guard = DiscountGuard()

# Percentage discount
result = guard.verify_percentage_discount(
    subtotal=Decimal("200.00"),
    discount_amount=Decimal("20.00"),
    percentage=Decimal("10")  # 10% off
)
print(result.verified)  # True ✅

# Fixed discount (must not exceed subtotal)
result = guard.verify_fixed_discount(
    subtotal=Decimal("50.00"),
    discount_amount=Decimal("75.00")  # AI hallucinated this
)
print(result.verified)  # False ❌ (exceeds subtotal)
```

---

## 🔌 Integration with UCP

### Middleware Pattern

```python
from qwed_ucp import UCPVerifier

def ucp_checkout_middleware(checkout_json):
    """Middleware that blocks invalid checkouts."""
    verifier = UCPVerifier()
    result = verifier.verify_checkout(checkout_json)
    
    if not result.verified:
        raise UCPVerificationError(result.error)
    
    return proceed_to_payment(checkout_json)
```

### With Stripe

```python
import stripe
from qwed_ucp import UCPVerifier

def create_payment_intent(ucp_checkout):
    # QWED verification BEFORE payment
    verifier = UCPVerifier()
    result = verifier.verify_checkout(ucp_checkout)
    
    if not result.verified:
        raise ValueError(f"Checkout math error: {result.error}")
    
    # Safe to process payment
    return stripe.PaymentIntent.create(
        amount=int(ucp_checkout["totals"][-1]["amount"] * 100),  # cents
        currency=ucp_checkout["currency"].lower()
    )
```

### As CI/CD Check

```yaml
# .github/workflows/verify-checkout.yml
name: Verify UCP Checkouts
on: [push]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: QWED-AI/qwed-ucp@v1
        with:
          test-script: tests/verify_checkouts.py
```

---

## 🔒 Security & Privacy

> **Your checkout data never leaves your machine.**

| Concern | QWED-UCP Approach |
|---------|-------------------|
| **Data Transmission** | ❌ No API calls, no cloud processing |
| **Storage** | ❌ Nothing stored, pure computation |
| **Dependencies** | ✅ Local-only (Decimal, Z3, JSON Schema) |
| **PCI Compliance** | ✅ No cardholder data processed |

**Perfect for:**
- E-commerce with strict privacy requirements
- Transactions containing PII
- PCI-DSS compliant environments

---

## ❓ FAQ

<details>
<summary><b>Is QWED-UCP free?</b></summary>

Yes! QWED-UCP is open source under the Apache 2.0 license. Use it in commercial e-commerce products, modify it, distribute it - no restrictions.
</details>

<details>
<summary><b>Does it handle floating-point precision issues?</b></summary>

Yes! QWED-UCP uses Python's `Decimal` type with proper rounding (ROUND_HALF_UP to 2 decimal places). No more `0.1 + 0.2 = 0.30000000000000004` issues.
</details>

<details>
<summary><b>What is the UCP total formula?</b></summary>

`Total = Subtotal - Discount + Fulfillment + Tax + Fee`

This is the standard UCP formula. QWED-UCP verifies that AI outputs match this formula exactly.
</details>

<details>
<summary><b>Can I use it without Google UCP?</b></summary>

Yes! While designed for UCP, the guards work with any JSON checkout format. Just structure your checkout with a `totals` array containing `type` and `amount` fields.
</details>

<details>
<summary><b>How fast is verification?</b></summary>

Typically <5ms per checkout. The Decimal math engine is highly optimized for currency calculations.
</details>

---

## 🗺️ Roadmap

### ✅ Released (v1.0.0)
- [x] UCPVerifier with 3 core guards
- [x] Money Guard: Cart totals, UCP formula
- [x] State Guard: Checkout state machine
- [x] Structure Guard: JSON Schema validation
- [x] Discount Guard: Percentage & fixed discounts
- [x] Currency Guard: Precision handling
- [x] Line Item Guard: Quantity × price verification

### 🚧 In Progress
- [ ] Refund verification
- [ ] Multi-currency support (exchange rates)
- [ ] Subscription/recurring payment validation

### 🔮 Planned
- [ ] TypeScript/npm SDK
- [ ] Shopify webhook integration
- [ ] Stripe Checkout session verification
- [ ] WooCommerce plugin
- [ ] Real-time cart verification API

---

## 🔗 Links

| Resource | Link |
|----------|------|
| **Universal Commerce Protocol** | [ucp.dev](https://ucp.dev) |
| **Google UCP Docs** | [developers.google.com/merchant/ucp](https://developers.google.com/merchant/ucp) |
| **QWED Verification** | [github.com/QWED-AI/qwed-verification](https://github.com/QWED-AI/qwed-verification) |
| **QWED Finance** | [github.com/QWED-AI/qwed-finance](https://github.com/QWED-AI/qwed-finance) |
| **QWED Legal** | [github.com/QWED-AI/qwed-legal](https://github.com/QWED-AI/qwed-legal) |

---

## 📦 Related QWED Packages

| Package | Purpose |
|---------|---------|
| [qwed-verification](https://github.com/QWED-AI/qwed-verification) | Core verification engine |
| [qwed-finance](https://github.com/QWED-AI/qwed-finance) | Banking & financial verification |
| [qwed-legal](https://github.com/QWED-AI/qwed-legal) | Legal contract verification |
| [qwed-mcp](https://github.com/QWED-AI/qwed-mcp) | Claude Desktop integration |

---

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE)

---

<div align="center">

**Built with ❤️ by [QWED-AI](https://github.com/QWED-AI)**

*"AI agents shouldn't guess at math. QWED makes commerce verifiable."*

</div>
