# QWED-UCP

**Verification for Universal Commerce Protocol (UCP) Transactions**

[![CI](https://github.com/QWED-AI/qwed-ucp/actions/workflows/ci.yml/badge.svg)](https://github.com/QWED-AI/qwed-ucp/actions)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)

QWED-UCP is a verification layer for Google's [Universal Commerce Protocol](https://ucp.dev), ensuring AI agent commerce transactions are mathematically correct.

## Why QWED-UCP?

AI agents (like Gemini) are now handling e-commerce:
- Cart calculations
- Tax percentages
- Discount math
- Refunds

**Problem:** AI agents hallucinate on math.

**Solution:** QWED-UCP verifies every transaction deterministically.

## The 3 Guards

| Guard | Engine | Verifies |
|-------|--------|----------|
| **Money Guard** | SymPy | Cart totals, tax, discounts |
| **State Guard** | Z3 | Checkout state machine logic |
| **Structure Guard** | JSON Schema | UCP schema compliance |

## Installation

```bash
pip install qwed-ucp
```

## Quick Start

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
    "line_items": [...]
}

result = verifier.verify_checkout(checkout)

if result.verified:
    print("✅ Transaction verified - safe to process!")
else:
    print(f"❌ Verification failed: {result.error}")
```

## Integration with UCP

```python
# Middleware for UCP checkout
def ucp_checkout_middleware(checkout_json):
    verifier = UCPVerifier()
    result = verifier.verify_checkout(checkout_json)
    
    if not result.verified:
        raise UCPVerificationError(result.error)
    
    return proceed_to_payment(checkout_json)
```

## Links

- [Universal Commerce Protocol](https://ucp.dev)
- [QWED Verification](https://github.com/QWED-AI/qwed-verification)
- [Google UCP Docs](https://developers.google.com/merchant/ucp)

## License

Apache 2.0
