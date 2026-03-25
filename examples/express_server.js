/**
 * Example: Express.js UCP Server with QWED-UCP Middleware
 *
 * Run: npm install express express-rate-limit && node express_server.js
 */

const express = require('express');
const rateLimit = require('express-rate-limit');
const { createQWEDUCPMiddleware } = require('../middleware/express/qwed-ucp-middleware');

const app = express();
app.use(express.json());

const ANSI_ESCAPE_PATTERN = /\x1B(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07\x1B]*(?:\x07|\x1B\\)|[@-_])/g;
const CONTROL_CHARACTER_PATTERN = /[\p{Cc}\p{Cf}]/gu;

function sanitizeForLog(value) {
    return String(value ?? 'Verification failed')
        .replace(ANSI_ESCAPE_PATTERN, '')
        .replace(CONTROL_CHARACTER_PATTERN, '_')
        .slice(0, 500);
}

// Rate limiting - max 100 requests per 15 minutes
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: { error: 'Too many requests, please try again later.' }
});
app.use(limiter);

// Add QWED-UCP middleware
const qwedMiddleware = createQWEDUCPMiddleware({
    verifyPaths: ['/checkout-sessions', '/checkout'],
    blockOnFailure: true,
    onVerified: (result, req) => {
        console.log({
            event: 'qwed_verification_passed',
            guardsPassed: result.guardsPassed
        });
    },
    onFailed: (result, req) => {
        console.log({
            event: 'qwed_verification_failed',
            error: sanitizeForLog(result.error)
        });
    }
});

app.use(qwedMiddleware);

// In-memory store
const checkouts = new Map();
let checkoutIdCounter = 1;

// Create checkout
app.post('/checkout-sessions', (req, res) => {
    const { currency = 'USD', line_items = [], status = 'incomplete' } = req.body;

    const checkoutId = `checkout-${checkoutIdCounter++}`;

    // Calculate totals
    const subtotal = line_items.reduce((sum, item) => {
        const price = item.price || (item.item && item.item.price) || 0;
        const qty = item.quantity || 1;
        return sum + (price * qty);
    }, 0);

    const tax = Math.round(subtotal * 0.0825 * 100) / 100;
    const total = Math.round((subtotal + tax) * 100) / 100;

    const checkout = {
        id: checkoutId,
        currency,
        status,
        line_items,
        totals: [
            { type: 'subtotal', amount: subtotal },
            { type: 'tax', amount: tax },
            { type: 'total', amount: total }
        ]
    };

    checkouts.set(checkoutId, checkout);

    res.status(201).json(checkout);
});

// Get checkout
app.get('/checkout-sessions/:id', (req, res) => {
    const checkout = checkouts.get(req.params.id);

    if (!checkout) {
        return res.status(404).json({ error: 'Checkout not found' });
    }

    res.json(checkout);
});

// Update checkout
app.put('/checkout-sessions/:id', (req, res) => {
    const checkoutId = req.params.id;

    if (!checkouts.has(checkoutId)) {
        return res.status(404).json({ error: 'Checkout not found' });
    }

    const { currency, line_items, status } = req.body;

    // Recalculate totals
    const subtotal = line_items.reduce((sum, item) => {
        const price = item.price || (item.item && item.item.price) || 0;
        const qty = item.quantity || 1;
        return sum + (price * qty);
    }, 0);

    const tax = Math.round(subtotal * 0.0825 * 100) / 100;
    const total = Math.round((subtotal + tax) * 100) / 100;

    const checkout = {
        id: checkoutId,
        currency,
        status,
        line_items,
        totals: [
            { type: 'subtotal', amount: subtotal },
            { type: 'tax', amount: tax },
            { type: 'total', amount: total }
        ]
    };

    checkouts.set(checkoutId, checkout);

    res.json(checkout);
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', qwed_ucp: 'enabled' });
});

// Start server
const PORT = process.env.PORT || 8182;
app.listen(PORT, () => {
    console.log(`QWED-UCP Demo Merchant running on http://localhost:${PORT}`);
    console.log('QWED-UCP verification is ENABLED for /checkout-sessions');
});
