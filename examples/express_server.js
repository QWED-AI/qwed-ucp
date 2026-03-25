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

const ESCAPE_CHARACTER_CODE = 0x1B;
const BELL_CHARACTER_CODE = 0x07;
const MAX_LOG_LENGTH = 500;
const CSI_FINAL_BYTE_PATTERN = /[@-~]/;
const CONTROL_CHARACTER_PATTERN = /[\p{Cc}\p{Cf}]/u;

function codePointAt(value, index) {
    return value.codePointAt(index);
}

function isEscapeCharacter(value, index) {
    return codePointAt(value, index) === ESCAPE_CHARACTER_CODE;
}

function isBellCharacter(value, index) {
    return codePointAt(value, index) === BELL_CHARACTER_CODE;
}

function skipCsiSequence(value, index) {
    let currentIndex = index + 2;

    while (currentIndex < value.length && !CSI_FINAL_BYTE_PATTERN.test(value[currentIndex])) {
        currentIndex += 1;
    }

    return currentIndex;
}

function skipOscSequence(value, index) {
    let currentIndex = index + 2;

    while (currentIndex < value.length) {
        if (isBellCharacter(value, currentIndex)) {
            return currentIndex;
        }

        if (isEscapeCharacter(value, currentIndex) && value[currentIndex + 1] === '\\') {
            return currentIndex + 1;
        }

        currentIndex += 1;
    }

    return currentIndex;
}

function getAnsiSequenceEndIndex(value, index) {
    const nextCharacter = value[index + 1];

    if (nextCharacter === '[') {
        return skipCsiSequence(value, index);
    }

    if (nextCharacter === ']') {
        return skipOscSequence(value, index);
    }

    return nextCharacter ? index + 1 : index;
}

function stripAnsiSequences(value) {
    let sanitized = '';

    for (let index = 0; index < value.length; index += 1) {
        if (!isEscapeCharacter(value, index)) {
            sanitized += value[index];
            continue;
        }

        index = getAnsiSequenceEndIndex(value, index);
    }

    return sanitized;
}

function normalizeControlCharacters(value) {
    return Array.from(value, (character) => (
        CONTROL_CHARACTER_PATTERN.test(character) ? '_' : character
    )).join('');
}

function sanitizeForLog(value) {
    return normalizeControlCharacters(stripAnsiSequences(String(value ?? 'Verification failed')))
        .slice(0, MAX_LOG_LENGTH);
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
