<div align="center">
  <img src="assets/logo.svg" alt="QWED Logo" width="80" height="80">
  <h1>QWED-UCP</h1>
  <h3>Deterministic Verification Middleware for Universal Commerce Protocol</h3>

  > **Verify AI agent commerce before the money moves.**

  <p>
    QWED-UCP sits between AI agents and payment processors — catching miscalculated totals,<br>
    invalid state transitions, and malformed checkouts <b>before</b> they hit production.
  </p>

  [![PyPI](https://img.shields.io/pypi/v/qwed-ucp?color=blue&label=PyPI)](https://pypi.org/project/qwed-ucp/)
  [![CI](https://github.com/QWED-AI/qwed-ucp/actions/workflows/ci.yml/badge.svg)](https://github.com/QWED-AI/qwed-ucp/actions)
  [![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
  [![Verified by QWED](https://img.shields.io/badge/Verified_by-QWED-00C853?style=flat&logo=checkmarx)](https://github.com/QWED-AI/qwed-ucp)
  [![Snyk](https://snyk.io/test/github/QWED-AI/qwed-ucp/badge.svg)](https://snyk.io/test/github/QWED-AI/qwed-ucp)
  [![GitHub stars](https://img.shields.io/github/stars/QWED-AI/qwed-ucp?style=social)](https://github.com/QWED-AI/qwed-ucp)

  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-the-guards">The Guards</a> ·
  <a href="#-integration">Integration</a> ·
  <a href="#-trust-status">Trust Status</a> ·
  <a href="https://docs.qwedai.com/docs/ucp/overview">📖 Docs</a>
</div>

---

## 🚨 The Problem

AI agents (Gemini, ChatGPT, Claude) now generate e-commerce checkouts directly —
cart totals, tax, discounts, refunds, fees. These agents hallucinate on math:

| Scenario | LLM Output | Correct |
|----------|------------|---------|
| 10% off $99.99 | "$10.00 discount" | $9.999 → $10.00 ✅ |
| 8.25% tax on $100 | "$8.00 tax" | $8.25 ❌ |
| $50 + $30 + $20 cart | "$110.00 total" | $100.00 ❌ |
| Discount applied after tax | Wrong order | Math error ❌ |

QWED-UCP blocks these errors **before they reach a payment processor**.

---

## ✅ What QWED-UCP Is (and Isn't)

### QWED-UCP IS:
- **Verification middleware** that checks AI-generated UCP checkouts
- **Deterministic** — uses Decimal math (no floating-point errors) and Z3 logic proofs
- **Open source** (Apache 2.0) — integrate into any e-commerce workflow
- **A safety layer** — catches calculation errors and invalid state transitions before payment

### QWED-UCP is NOT:
- ~~A shopping cart~~ — use Shopify, WooCommerce, or Stripe for that
- ~~A payment processor~~ — use Stripe, Adyen, or Square for that
- ~~A fraud detection system~~ — use Sift, Signifyd, or Riskified for that
- ~~A replacement for e-commerce platforms~~ — we just verify the math

> **Think of QWED-UCP as the "accountant" that reviews every AI checkout before payment.**
>
> Shopify builds carts. Stripe processes payments. **QWED verifies the math.**

---

## 🆚 How QWED-UCP Differs from E-Commerce Platforms

| Aspect | Shopify / Stripe / Adyen | QWED-UCP |
|--------|--------------------------|----------|
| **Purpose** | Build carts, process payments | Verify calculations |
| **Approach** | Trust AI outputs | Deterministically verify AI outputs |
| **Accuracy** | ~99% (edge cases fail) | 100% deterministic |
| **Tech** | Standard floating-point | Decimal + Z3 + JSON Schema |
| **Integration** | Replace your stack | Sits between AI and payment |
| **Pricing** | Transaction fees | Free (Apache 2.0) |

### Use Together

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   AI Agent   │ ──► │  QWED-UCP    │ ──► │    Stripe    │
│ (checkout)   │     │  (verifies)  │     │  (payment)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 🛡️ The Guards

QWED-UCP ships **10 verification guards** that run as a fail-closed pipeline:

| Guard | Engine | What It Verifies |
|-------|--------|------------------|
| **Money Guard** | Decimal | Cart totals against UCP formula: `Total = Subtotal - Discount + Fulfillment + Tax + Fee` |
| **State Guard** | Z3 SMT Solver | Checkout state machine (draft → ready → complete), rejects illegal transitions |
| **Structure Guard** | JSON Schema | UCP schema compliance (v1.0) |
| **Line Item Guard** | Decimal | Item quantity × price = line total |
| **Discount Guard** | Decimal | Percentage and fixed discount calculations |
| **Currency Guard** | Decimal | Currency precision, $0.01 rounding, supported codes |
| **Refund Guard** | Decimal | Full/partial refund amounts, tax reversals |
| **Tip Guard** | Decimal | Pre/post-tax tip calculations, min/max bounds |
| **Fee Guard** | Decimal | Service fees, delivery fees, platform fees |
| **Attestation Guard** | JWT (PyJWT) | Context-bound attestation tokens with replay-attack protection |

---

## 🚀 Quick Start

### Installation

```bash
pip install qwed-ucp
```

### Verify a Checkout

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
    print("✅ Transaction verified — safe to process!")
else:
    print(f"❌ Verification failed: {result.error}")
```

`verify_checkout()` is always a **full fail-closed trust verdict**: it returns
`verified=True` only when Money Guard, State Guard, and Structure Guard all pass.

### Verify Totals Only

```python
# Math-only check — does not verify state or schema
result = verifier.verify_totals_only(checkout)
```

> ⚠️ Do not treat `verify_totals_only()` as a final transaction verdict.
> It only runs the Money Guard and does not check state or schema validity.

---

## 📊 Interpreting Results

Every guard result and the top-level `UCPVerificationResult` carry:

| Field | Type | Description |
|-------|------|-------------|
| `verified` | `bool` | Convenience flag — `True` only when `status == TrustStatus.VERIFIED` |
| `status` | `TrustStatus` | Typed trust verdict — see [Trust Status](#-trust-status) |
| `engine` | `str` | `"QWED-Deterministic-v1"` |
| `error` | `Optional[str]` | Error message when verification fails |
| `guards` | `list[GuardResult]` | Individual guard outcomes (top-level result only) |

### Branching on `status` (preferred)

```python
from qwed_ucp import UCPVerifier, TrustStatus

verifier = UCPVerifier()
result = verifier.verify_checkout(checkout)

if result.status == TrustStatus.VERIFIED:
    proceed_to_payment(checkout)
elif result.status == TrustStatus.ENGINE_ERROR:
    page_operator("Verifier crashed — manual review required")
else:
    reject_transaction(f"Proof failed: {result.status}")
```

### Aggregation

`verify_checkout()` propagates the most-severe guard status to the top level
(fail-closed ordering):

| Top-level status | Triggered when |
|---|---|
| `ENGINE_ERROR` | Any guard raised an exception |
| `QUARANTINED` | A guard returned `QUARANTINED` (reserved) |
| `FAILED` | A guard deterministically disproved the transaction |
| `UNVERIFIABLE` | Most-severe guard status is `UNVERIFIABLE` |
| `UNSUPPORTED` | Most-severe guard status is `UNSUPPORTED` |
| `PARTIAL` | Most-severe guard status is `PARTIAL` |
| `VERIFIED` | All guards passed |

---

## 🔌 Integration

### FastAPI Middleware

QWED-UCP ships a configurable FastAPI/Starlette middleware that intercepts
checkout requests and verifies them automatically:

```python
from fastapi import FastAPI
from qwed_ucp.middleware.fastapi import QWEDUCPMiddleware

app = FastAPI()
app.add_middleware(QWEDUCPMiddleware)
```

The middleware:
- Intercepts `POST`/`PUT`/`PATCH` to paths matching `/checkout`, `/cart`, `/payment`
- Returns `422 Unprocessable Entity` on verification failure (configurable)
- Sets headers `X-QWED-Verified`, `X-QWED-Guards-Passed`, `X-QWED-Error`
- Runs core guards (Money, State, Schema) plus optional advanced guards
- **Always fail-closed** on empty body, malformed JSON, or non-dict payload

Configuration:

```python
app.add_middleware(QWEDUCPMiddleware,
    block_on_failure=True,       # Block on verification failure (default)
    include_details=True,        # Include guard details in error response
    use_advanced_guards=True,    # Also run Line Items, Discount, Currency guards
    verify_paths=["/checkout"],  # Override default path list
    verify_methods=["POST"],     # Override default method list
)
```

A helper dependency is also available for manual injection:

```python
from qwed_ucp.middleware.fastapi import create_verification_dependency

verify = create_verification_dependency()

@app.post("/checkout")
async def create_checkout(
    checkout: dict,
    verification = Depends(verify)
):
    if not verification["verified"]:
        raise HTTPException(422, verification["error"])
    ...
```

### Express.js Middleware

QWED-UCP also ships an Express.js middleware:

```javascript
const express = require('express');
const { createQWEDUCPMiddleware } = require('qwed-ucp');

const app = express();
app.use(express.json());
app.use(createQWEDUCPMiddleware());

app.post('/checkout', (req, res) => {
    res.json({ status: 'verified', checkout: req.body });
});
```

See [`examples/express_server.js`](examples/express_server.js) for a complete
example with rate limiting and security hardening.

### Stripe

```python
import stripe
from qwed_ucp import UCPVerifier

def create_payment_intent(ucp_checkout):
    verifier = UCPVerifier()
    result = verifier.verify_checkout(ucp_checkout)

    if not result.verified:
        raise ValueError(f"Checkout math error: {result.error}")

    return stripe.PaymentIntent.create(
        amount=int(ucp_checkout["totals"][-1]["amount"] * 100),
        currency=ucp_checkout["currency"].lower()
    )
```

### CI/CD

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

## 🔏 AttestationGuard

For environments that need cryptographic proof of verification:

```python
from qwed_ucp import AttestationGuard, UCPVerifier
import uuid

attester = AttestationGuard(
    secret_key="your-256-bit-secret",
    allow_insecure=True     # Set False in production
)

verifier = UCPVerifier()
result = verifier.verify_checkout(checkout)

attestation = attester.sign_checkout(
    checkout=checkout,
    verification_result=result,
    transaction_attempt_id=str(uuid.uuid4()),
    request_nonce=str(uuid.uuid4()),
    session_id="sess_abc123"
)

# attestation.token is a signed JWT
```

`transaction_attempt_id` and `request_nonce` are **required** for context
binding and replay-attack protection. Set `QWED_ATTESTATION_SECRET` env var
instead of passing `secret_key` in code.

---

## 🏷️ Trust Status

QWED-UCP v0.2.0+ exposes a typed `TrustStatus` enum on every verification
result, replacing the old `verified: bool`-only model:

| State | Meaning |
|-------|---------|
| `VERIFIED` | Deterministic proof succeeded under supported conditions |
| `FAILED` | Proof was attempted and disproved (e.g. totals mismatch) |
| `UNVERIFIABLE` | Proof could not be established (e.g. missing proof basis) |
| `UNSUPPORTED` | Input or state is outside supported semantics |
| `PARTIAL` | Some checks ran, but no final verdict is justified |
| `ENGINE_ERROR` | A verifier dependency or the runtime crashed |
| `QUARANTINED` | Reserved for policy-level rejection |

`verified: bool` is preserved as a backward-compatible derived field:
`result.verified == True` only when `result.status == TrustStatus.VERIFIED`.

---

## 🔒 Security & Privacy

> **Your checkout data never leaves your machine.**

| Concern | QWED-UCP Approach |
|---------|-------------------|
| **Data Transmission** | No API calls, no cloud processing |
| **Storage** | Nothing stored — pure computation |
| **Dependencies** | Local-only (Decimal, Z3, JSON Schema, PyJWT) |
| **PCI Compliance** | No cardholder data processed |

Perfect for: e-commerce with strict privacy requirements, transactions
containing PII, PCI-DSS compliant environments.

---

## 🗺️ Roadmap

### v0.2.0 (Current)
- [x] UCPVerifier with 3 core guards (Money, State, Structure)
- [x] All 10 guards shipped and tested
- [x] TrustStatus enum on every result
- [x] FastAPI middleware (fail-closed on unparseable bodies)
- [x] Express.js middleware
- [x] AttestationGuard with context-bound JWT + replay protection

### In Progress
- [ ] Multi-currency support (exchange rates)
- [ ] Subscription/recurring payment validation
- [ ] TypeScript/npm SDK

### Planned
- [ ] Shopify webhook integration
- [ ] Stripe Checkout session verification
- [ ] WooCommerce plugin
- [ ] Real-time cart verification API

---

## ❓ FAQ

<details>
<summary><b>Is QWED-UCP free?</b></summary>

Yes! Apache 2.0 license. Use it in commercial products, modify it, distribute it — no restrictions.
</details>

<details>
<summary><b>Does it handle floating-point precision issues?</b></summary>

Yes! Uses Python's `Decimal` type with `ROUND_HALF_UP` to 2 decimal places. No `0.1 + 0.2 = 0.30000000000000004` issues.
</details>

<details>
<summary><b>What is the UCP total formula?</b></summary>

`Total = Subtotal - Discount + Fulfillment + Tax + Fee`

QWED-UCP's Money Guard verifies AI outputs against this formula exactly.
</details>

<details>
<summary><b>Can I use it without Google UCP?</b></summary>

Yes! The guards work with any JSON checkout format that has a `totals` array
with `type` and `amount` fields.
</details>

<details>
<summary><b>How fast is verification?</b></summary>

Sub-millisecond to low milliseconds per checkout, depending on the guard set.
The Decimal math engine is optimized for currency calculations; Z3 state checks
are typically under 1ms.
</details>

<details>
<summary><b>Does QWED-UCP expose TrustStatus in the Python SDK?</b></summary>

Yes. `qwed_ucp.TrustStatus` is a 7-state enum on every result dataclass.
The `verified: bool` field is preserved for backward compatibility.
</details>

---

## 🔗 Related QWED Packages

| Package | Purpose |
|---------|---------|
| [qwed-verification](https://github.com/QWED-AI/qwed-verification) | Core verification engine |
| [qwed-finance](https://github.com/QWED-AI/qwed-finance) | Banking & financial verification |
| [qwed-legal](https://github.com/QWED-AI/qwed-legal) | Legal contract verification |
| [qwed-infra](https://github.com/QWED-AI/qwed-infra) | Infrastructure-as-code verification |
| [qwed-tax](https://github.com/QWED-AI/qwed-tax) | Tax compliance verification |
| [qwed-mcp](https://github.com/QWED-AI/qwed-mcp) | Claude Desktop MCP integration |
| [qwed-open-responses](https://github.com/QWED-AI/qwed-open-responses) | OpenAI Responses API guards |

---

## 🔗 Links

| Resource | Link |
|----------|------|
| **Universal Commerce Protocol** | [ucp.dev](https://ucp.dev) |
| **Google UCP Docs** | [developers.google.com/merchant/ucp](https://developers.google.com/merchant/ucp) |
| **QWED Documentation** | [docs.qwedai.com](https://docs.qwedai.com/docs/ucp/overview) |
| **QWED-AI Organization** | [github.com/QWED-AI](https://github.com/QWED-AI) |

---

## 🧑‍💻 Development

### From Source

```bash
git clone https://github.com/QWED-AI/qwed-ucp.git
cd qwed-ucp
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v                # All tests
pytest tests/ -v --cov=src/qwed_ucp --cov-report=html  # With coverage
pytest tests/test_money_guard.py -v  # Single guard
```

### Linting

```bash
ruff check src/ tests/
```

---

## 📄 License

Apache 2.0 — See [LICENSE](LICENSE)

---

<div align="center">

**Built with ❤️ by [QWED-AI](https://github.com/QWED-AI)**

*"AI agents shouldn't guess at math. QWED makes commerce verifiable."*

</div>
