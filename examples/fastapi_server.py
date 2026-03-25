"""Example: FastAPI UCP Server with QWED-UCP Middleware

This demonstrates how to add QWED-UCP verification to a UCP merchant server.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Import QWED-UCP middleware
from qwed_ucp.middleware.fastapi import QWEDUCPMiddleware

app = FastAPI(
    title="QWED-UCP Demo Merchant",
    description="UCP Merchant with QWED verification",
    version="1.0.0"
)

# Add QWED-UCP middleware - automatically verifies all checkout requests
app.add_middleware(
    QWEDUCPMiddleware,
    verify_paths=["/checkout-sessions", "/checkout"],
    block_on_failure=True,  # Return 422 if verification fails
    include_details=True,   # Include guard details in error response
    use_advanced_guards=True  # Also run Line Items, Discount, Currency guards
)


# Models
class LineItem(BaseModel):
    id: str
    quantity: int = 1
    price: float
    title: str


class Total(BaseModel):
    type: str  # subtotal, tax, discount, fulfillment, total
    amount: float


class CheckoutRequest(BaseModel):
    currency: str = "USD"
    line_items: list[LineItem]
    status: str = "incomplete"


class CheckoutResponse(BaseModel):
    id: str
    currency: str
    status: str
    line_items: list[LineItem]
    totals: list[Total]


# Simple in-memory store
checkouts = {}


@app.post("/checkout-sessions", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest):
    """
    Create a new checkout session.
    
    QWED-UCP middleware automatically verifies:
    - Currency format (ISO 4217)
    - Line item calculations
    - Total formula consistency
    
    If verification fails, returns 422 with details.
    """
    import uuid
    
    checkout_id = str(uuid.uuid4())
    
    # Calculate totals
    subtotal = sum(item.price * item.quantity for item in request.line_items)
    tax = round(subtotal * 0.0825, 2)  # 8.25% tax
    total = round(subtotal + tax, 2)
    
    checkout = CheckoutResponse(
        id=checkout_id,
        currency=request.currency,
        status=request.status,
        line_items=request.line_items,
        totals=[
            Total(type="subtotal", amount=subtotal),
            Total(type="tax", amount=tax),
            Total(type="total", amount=total),
        ]
    )
    
    checkouts[checkout_id] = checkout
    return checkout


@app.get("/checkout-sessions/{checkout_id}", response_model=CheckoutResponse)
async def get_checkout(checkout_id: str):
    """Get checkout session by ID."""
    if checkout_id not in checkouts:
        raise HTTPException(404, "Checkout not found")
    return checkouts[checkout_id]


@app.put("/checkout-sessions/{checkout_id}", response_model=CheckoutResponse)
async def update_checkout(checkout_id: str, request: CheckoutRequest):
    """
    Update checkout session.
    
    QWED-UCP will verify the updated checkout before processing.
    """
    if checkout_id not in checkouts:
        raise HTTPException(404, "Checkout not found")
    
    # Recalculate totals
    subtotal = sum(item.price * item.quantity for item in request.line_items)
    tax = round(subtotal * 0.0825, 2)
    total = round(subtotal + tax, 2)
    
    checkout = CheckoutResponse(
        id=checkout_id,
        currency=request.currency,
        status=request.status,
        line_items=request.line_items,
        totals=[
            Total(type="subtotal", amount=subtotal),
            Total(type="tax", amount=tax),
            Total(type="total", amount=total),
        ]
    )
    
    checkouts[checkout_id] = checkout
    return checkout


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "qwed_ucp": "enabled"}


if __name__ == "__main__":
    import uvicorn
    print("Starting QWED-UCP Demo Merchant on http://localhost:8182")
    print("QWED-UCP verification is ENABLED for /checkout-sessions")
    uvicorn.run(app, host="127.0.0.1", port=8182)
