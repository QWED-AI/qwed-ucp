# qwed-ucp

[![npm version](https://badge.fury.io/js/qwed-ucp.svg)](https://badge.fury.io/js/qwed-ucp)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Verification guards for Universal Commerce Protocol (UCP) - Catch AI math errors before payment.**

When AI agents shop on behalf of users, they can make calculation errors. QWED-UCP catches these errors before payment is processed.

## Installation

```bash
npm install qwed-ucp
```

## Quick Start

```javascript
const express = require('express');
const { createQWEDUCPMiddleware } = require('qwed-ucp');

const app = express();
app.use(express.json());

// Add QWED-UCP middleware
app.use(createQWEDUCPMiddleware());

app.post('/checkout-sessions', (req, res) => {
  // If we get here, checkout is verified!
  res.status(201).json({ status: 'created' });
});

app.listen(8182);
```

## What It Verifies

| Guard | Verification |
|-------|-------------|
| **Currency** | Valid ISO 4217 codes (USD, EUR, JPY, etc.) |
| **Money** | `total = subtotal - discount + tax + shipping` |
| **State** | Valid checkout state transitions |
| **Line Items** | `price × quantity = line_total` |

## Configuration

```javascript
app.use(createQWEDUCPMiddleware({
  verifyPaths: ['/checkout-sessions', '/checkout'],
  verifyMethods: ['POST', 'PUT', 'PATCH'],
  blockOnFailure: true,
  onVerified: (result, req) => {
    console.log('✅ Verified:', result.guardsPassed, 'guards passed');
  },
  onFailed: (result, req) => {
    console.log('❌ Failed:', result.error);
  }
}));
```

## Response Headers

| Header | Description |
|--------|-------------|
| `X-QWED-Verified` | `true` or `false` |
| `X-QWED-Guards-Passed` | Number of guards passed |
| `X-QWED-Error` | Error message (on failure) |

## Manual Verification

```javascript
const { verifyCheckoutLocally } = require('qwed-ucp');

const result = verifyCheckoutLocally({
  currency: 'USD',
  totals: [
    { type: 'subtotal', amount: 100.00 },
    { type: 'tax', amount: 8.25 },
    { type: 'total', amount: 108.25 }
  ]
});

console.log(result.verified); // true
```

## Links

- **Documentation:** [docs.qwedai.tech/docs/ucp/overview](https://docs.qwedai.tech/docs/ucp/overview)
- **GitHub:** [QWED-AI/qwed-ucp](https://github.com/QWED-AI/qwed-ucp)
- **Python Package:** [pip install qwed-ucp](https://pypi.org/project/qwed-ucp/)

## License

Apache 2.0 - see [LICENSE](LICENSE)
