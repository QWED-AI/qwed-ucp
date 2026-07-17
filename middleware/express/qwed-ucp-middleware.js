/**
 * QWED-UCP Express.js Middleware
 * 
 * Verify UCP transactions in Express.js applications.
 * This is a reference implementation that can be used with the QWED-UCP Python API.
 * 
 * Usage:
 *   const { qwedUCPMiddleware } = require('./qwed-ucp-middleware');
 *   app.use('/checkout', qwedUCPMiddleware({ apiUrl: 'http://localhost:8000' }));
 */

const https = require('https');
const http = require('http');

/**
 * Create QWED-UCP verification middleware for Express.js
 * 
 * @param {Object} options - Configuration options
 * @param {string} options.apiUrl - QWED-UCP API URL (default: http://localhost:8000)
 * @param {string[]} options.verifyPaths - Paths to verify (default: ['/checkout', '/payment'])
 * @param {string[]} options.verifyMethods - Methods to verify (default: ['POST', 'PUT', 'PATCH'])
 * @param {boolean} options.blockOnFailure - Block request on verification failure (default: true)
 * @param {Function} options.onVerified - Callback when verified successfully
 * @param {Function} options.onFailed - Callback when verification fails
 */
function createQWEDUCPMiddleware(options = {}) {
    const {
        apiUrl = 'http://localhost:8000',
        verifyPaths = ['/checkout', '/checkout-sessions', '/payment', '/cart'],
        verifyMethods = ['POST', 'PUT', 'PATCH'],
        blockOnFailure = true,
        onVerified = null,
        onFailed = null,
    } = options;

    return async function qwedUCPMiddleware(req, res, next) {
        // Check if this request should be verified
        if (!verifyMethods.includes(req.method)) {
            return next();
        }

        const shouldVerify = verifyPaths.some(path => req.path.includes(path));
        if (!shouldVerify) {
            return next();
        }

        // Get checkout data from request body
        const checkoutData = req.body;
        if (!req.is('application/json') || !checkoutData || typeof checkoutData !== 'object' || Array.isArray(checkoutData)) {
            res.set('X-QWED-Verified', 'false');
            res.set('X-QWED-Error', 'Empty or non-JSON body: cannot verify');
            return res.status(422).json({
                error: 'QWED-UCP Verification Failed',
                message: 'Empty or non-JSON request body: cannot verify unparseable payload',
                code: 'UNPARSEABLE_REQUEST'
            });
        }

        try {
            // Verify using local guards (no API call needed for basic checks)
            const result = verifyCheckoutLocally(checkoutData);

            // Set verification headers
            res.set('X-QWED-Verified', result.verified.toString());
            res.set('X-QWED-Guards-Passed', result.guardsPassed.toString());

            if (result.verified) {
                if (onVerified) await Promise.resolve(onVerified(result, req));
                return next();
            } else {
                res.set('X-QWED-Error', result.error || 'Verification failed');

                if (onFailed) await Promise.resolve(onFailed(result, req));

                if (blockOnFailure) {
                    return res.status(422).json({
                        error: 'QWED-UCP Verification Failed',
                        message: result.error,
                        code: 'VERIFICATION_FAILED',
                        details: result.details
                    });
                }

                return next();
            }
        } catch (error) {
            console.error('QWED-UCP Middleware Error:', error);
            res.set('X-QWED-Verified', 'false');
            res.set('X-QWED-Error', 'Internal verification error');

            return res.status(500).json({
                error: 'QWED-UCP Verification Failed',
                message: 'Internal verification error: verification could not be completed',
                code: 'INTERNAL_VERIFICATION_ERROR'
            });
        }
    };
}

/**
 * Verify checkout data locally using JavaScript guards
 * This provides basic verification without needing the Python API
 */
function verifyCheckoutLocally(checkout) {
    const result = {
        verified: true,
        guardsPassed: 0,
        guardsFailed: 0,
        details: [],
        error: null
    };

    // Guard 1: Currency (required)
    const currencyResult = verifyCurrency(checkout);
    addGuardResult(result, 'Currency Guard', currencyResult);

    // Guard 2: Totals Math
    const mathResult = verifyTotalsMath(checkout);
    addGuardResult(result, 'Money Guard', mathResult);

    // Guard 3: State Machine
    const stateResult = verifyState(checkout);
    addGuardResult(result, 'State Guard', stateResult);

    // Guard 4: Line Items
    const lineItemsResult = verifyLineItems(checkout);
    addGuardResult(result, 'Line Items Guard', lineItemsResult);

    return result;
}

function addGuardResult(result, name, guardResult) {
    if (guardResult.verified) {
        result.guardsPassed++;
    } else {
        result.guardsFailed++;
        result.verified = false;
        if (!result.error) {
            result.error = guardResult.error;
        }
    }
    result.details.push({
        guard: name,
        verified: guardResult.verified,
        error: guardResult.error
    });
}

// Currency Guard
function verifyCurrency(checkout) {
    const currency = checkout.currency;

    if (!currency) {
        return { verified: false, error: 'Currency is required' };
    }

    if (typeof currency !== 'string' || currency.length !== 3) {
        return { verified: false, error: `Currency must be 3-letter ISO code, got: ${currency}` };
    }

    return { verified: true, error: null };
}

// Money Guard - Verify totals add up
function verifyTotalsMath(checkout) {
    const totals = checkout.totals || [];

    if (totals.length === 0) {
        return { verified: true, error: null }; // No totals to verify
    }

    // Find required totals
    const getTotal = (type) => {
        const entry = totals.find(t => t.type === type);
        return entry ? parseFloat(entry.amount) || 0 : 0;
    };

    const subtotal = getTotal('subtotal');
    const discount = getTotal('discount');
    const fulfillment = getTotal('fulfillment');
    const tax = getTotal('tax');
    const fee = getTotal('fee');
    const total = getTotal('total');

    if (total === 0) {
        return { verified: true, error: null }; // No total to verify against
    }

    // Formula: Total = Subtotal - Discount + Fulfillment + Tax + Fee
    const calculated = subtotal - discount + fulfillment + tax + fee;
    const diff = Math.abs(calculated - total);

    if (diff > 0.01) {
        return {
            verified: false,
            error: `Total mismatch: calculated ${calculated.toFixed(2)}, declared ${total.toFixed(2)}`
        };
    }

    return { verified: true, error: null };
}

// State Guard - Verify checkout state
function verifyState(checkout) {
    const status = (checkout.status || '').toLowerCase();
    const validStatuses = ['incomplete', 'ready_for_complete', 'completed', 'failed', 'cancelled'];

    if (status && !validStatuses.includes(status)) {
        return { verified: false, error: `Invalid status: ${status}` };
    }

    // completed -> order must exist
    if (status === 'completed' && !checkout.order) {
        return { verified: false, error: "Status is 'completed' but order is missing" };
    }

    // non-incomplete -> line_items should exist
    if (status && status !== 'incomplete') {
        const lineItems = checkout.line_items || [];
        if (lineItems.length === 0) {
            return { verified: false, error: `Status is '${status}' but line_items is empty` };
        }
    }

    return { verified: true, error: null };
}

// Line Items Guard - Verify line item calculations
function verifyLineItems(checkout) {
    const lineItems = checkout.line_items || [];
    const totals = checkout.totals || [];

    if (lineItems.length === 0) {
        return { verified: true, error: null };
    }

    let calculatedSubtotal = 0;

    for (const item of lineItems) {
        const quantity = item.quantity || 1;
        const price = item.price || (item.item && item.item.price) || 0;

        if (quantity < 1) {
            return { verified: false, error: `Item ${item.id}: quantity must be positive` };
        }

        calculatedSubtotal += price * quantity;
    }

    // Check against subtotal
    const subtotalEntry = totals.find(t => t.type === 'subtotal');
    if (subtotalEntry) {
        const declaredSubtotal = parseFloat(subtotalEntry.amount) || 0;
        const diff = Math.abs(calculatedSubtotal - declaredSubtotal);

        if (diff > 0.01) {
            return {
                verified: false,
                error: `Subtotal mismatch: line items sum to ${calculatedSubtotal.toFixed(2)}, but subtotal is ${declaredSubtotal.toFixed(2)}`
            };
        }
    }

    return { verified: true, error: null };
}

// Export for use in Express.js
module.exports = {
    createQWEDUCPMiddleware,
    verifyCheckoutLocally,
    verifyCurrency,
    verifyTotalsMath,
    verifyState,
    verifyLineItems
};
