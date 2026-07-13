"""FastAPI Middleware for QWED-UCP.

Automatically verify UCP transactions before processing.
Intercepts checkout requests and validates them using QWED guards.

Usage:
    from fastapi import FastAPI
    from qwed_ucp.middleware.fastapi import QWEDUCPMiddleware
    
    app = FastAPI()
    app.add_middleware(QWEDUCPMiddleware)
"""

import json
import logging
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from qwed_ucp.core import UCPVerifier
from qwed_ucp.guards.line_items import LineItemsGuard
from qwed_ucp.guards.discount import DiscountGuard
from qwed_ucp.guards.currency import CurrencyGuard

logger = logging.getLogger("qwed_ucp.middleware")


class QWEDUCPMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware for QWED-UCP verification.
    
    Intercepts checkout-related requests and validates them
    before passing to the handler.
    
    Configuration:
        - verify_paths: List of paths to verify (default: /checkout-sessions)
        - verify_methods: HTTP methods to verify (default: POST, PUT, PATCH)
        - block_on_failure: If True, return 422 on verification failure
        - include_details: If True, include verification details in response
    """
    
    # Default paths that contain checkout data
    DEFAULT_VERIFY_PATHS = [
        "/checkout-sessions",
        "/checkout",
        "/cart",
        "/payment",
    ]
    
    # HTTP methods that modify data
    DEFAULT_VERIFY_METHODS = ["POST", "PUT", "PATCH"]
    
    def __init__(
        self,
        app,
        verify_paths: Optional[list[str]] = None,
        verify_methods: Optional[list[str]] = None,
        block_on_failure: bool = True,
        include_details: bool = True,
        use_advanced_guards: bool = True,
    ):
        """
        Initialize QWED-UCP middleware.
        
        Args:
            app: FastAPI/Starlette application
            verify_paths: Paths to verify (partial match)
            verify_methods: HTTP methods to verify
            block_on_failure: Block request if verification fails
            include_details: Include guard details in error response
            use_advanced_guards: Also run Line Items, Discount, Currency guards
        """
        super().__init__(app)
        self.verify_paths = verify_paths or self.DEFAULT_VERIFY_PATHS
        self.verify_methods = verify_methods or self.DEFAULT_VERIFY_METHODS
        self.block_on_failure = block_on_failure
        self.include_details = include_details
        self.use_advanced_guards = use_advanced_guards
        
        self.verifier = UCPVerifier()
        self.line_items_guard = LineItemsGuard() if use_advanced_guards else None
        self.discount_guard = DiscountGuard() if use_advanced_guards else None
        self.currency_guard = CurrencyGuard() if use_advanced_guards else None
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """Process request and verify if applicable."""
        
        # Check if this request should be verified
        if not self._should_verify(request):
            return await call_next(request)
        
        # Read and parse request body — fail closed on unparseable input
        try:
            body = await request.body()
            if not body:
                return self._create_error_response({
                    "verified": False,
                    "error": "Empty request body: cannot verify empty payload",
                    "guards_passed": 0,
                    "guards_failed": 0,
                    "details": [],
                }, code="UNPARSEABLE_REQUEST")
            
            checkout_data = json.loads(body)
            if not isinstance(checkout_data, dict):
                return self._create_error_response({
                    "verified": False,
                    "error": "Invalid request body: expected JSON object",
                    "guards_passed": 0,
                    "guards_failed": 0,
                    "details": [],
                }, code="UNPARSEABLE_REQUEST")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._create_error_response({
                "verified": False,
                "error": "Malformed request body: expected JSON",
                "guards_passed": 0,
                "guards_failed": 0,
                "details": [],
            }, code="UNPARSEABLE_REQUEST")
        
        # Run verification
        verification_result = self._verify_checkout(checkout_data)
        
        # Add verification headers
        response = await call_next(request)
        
        if verification_result["verified"]:
            response.headers["X-QWED-Verified"] = "true"
            response.headers["X-QWED-Guards-Passed"] = str(
                verification_result["guards_passed"]
            )
        else:
            response.headers["X-QWED-Verified"] = "false"
            response.headers["X-QWED-Error"] = verification_result.get("error", "Unknown")
            
            if self.block_on_failure:
                return self._create_error_response(verification_result)
        
        return response
    
    def _should_verify(self, request: Request) -> bool:
        """Check if request should be verified."""
        # Check method
        if request.method not in self.verify_methods:
            return False
        
        # Check path
        path = request.url.path
        return any(vp in path for vp in self.verify_paths)
    
    def _verify_checkout(self, checkout_data: dict) -> dict:
        """Run all verification guards."""
        results = {
            "verified": True,
            "guards_passed": 0,
            "guards_failed": 0,
            "details": []
        }
        
        # Core verification (Money, State, Schema)
        core_result = self.verifier.verify_checkout(checkout_data)
        
        if not core_result.verified:
            results["verified"] = False
            results["error"] = "Core verification failed"
        
        for guard in core_result.guards:
            if guard.verified:
                results["guards_passed"] += 1
            else:
                results["guards_failed"] += 1
                if "error" not in results:
                    results["error"] = guard.error
            
            results["details"].append({
                "guard": guard.guard_name,
                "verified": guard.verified,
                "error": guard.error
            })
        
        # Advanced guards
        if self.use_advanced_guards:
            # Line Items
            if self.line_items_guard:
                li_result = self.line_items_guard.verify(checkout_data)
                self._add_guard_result(results, "Line Items Guard", li_result)
            
            # Discount
            if self.discount_guard:
                disc_result = self.discount_guard.verify(checkout_data)
                self._add_guard_result(results, "Discount Guard", disc_result)
            
            # Currency
            if self.currency_guard:
                curr_result = self.currency_guard.verify(checkout_data)
                self._add_guard_result(results, "Currency Guard", curr_result)
        
        return results
    
    def _add_guard_result(self, results: dict, name: str, guard_result) -> None:
        """Add a guard result to the results dict."""
        if guard_result.verified:
            results["guards_passed"] += 1
        else:
            results["guards_failed"] += 1
            results["verified"] = False
            if "error" not in results:
                results["error"] = guard_result.error
        
        results["details"].append({
            "guard": name,
            "verified": guard_result.verified,
            "error": guard_result.error
        })
    
    def _create_error_response(self, verification_result: dict, code: str = "VERIFICATION_FAILED") -> JSONResponse:
        """Create error response for failed verification."""
        content = {
            "error": "QWED-UCP Verification Failed",
            "message": verification_result.get("error", "Transaction verification failed"),
            "code": code
        }
        
        if self.include_details:
            content["details"] = {
                "guards_passed": verification_result["guards_passed"],
                "guards_failed": verification_result["guards_failed"],
                "guards": verification_result["details"]
            }
        
        return JSONResponse(
            status_code=422,
            content=content,
            headers={
                "X-QWED-Verified": "false",
                "X-QWED-Error": verification_result.get("error", "Unknown")[:100]
            }
        )


def create_verification_dependency(
    verifier: Optional[UCPVerifier] = None,
    use_advanced_guards: bool = True
):
    """
    Create a FastAPI dependency for manual verification.
    
    Usage:
        from fastapi import Depends
        
        verify = create_verification_dependency()
        
        @app.post("/checkout")
        async def create_checkout(
            checkout: dict,
            verification = Depends(verify)
        ):
            if not verification["verified"]:
                raise HTTPException(422, verification["error"])
            ...
    """
    _verifier = verifier or UCPVerifier()
    _li_guard = LineItemsGuard() if use_advanced_guards else None
    _disc_guard = DiscountGuard() if use_advanced_guards else None
    _curr_guard = CurrencyGuard() if use_advanced_guards else None
    
    async def verify_checkout(request: Request):
        try:
            body = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {
                "verified": False,
                "error": "Malformed request body: expected JSON",
                "guards": [],
            }
        
        if not isinstance(body, dict):
            return {
                "verified": False,
                "error": "Invalid request body: expected JSON object",
                "guards": [],
            }
        
        result = {"verified": True, "guards": []}
        
        # Core
        core = _verifier.verify_checkout(body)
        if not core.verified:
            result["verified"] = False
            result["error"] = "Core verification failed"
        
        for g in core.guards:
            result["guards"].append({"name": g.guard_name, "ok": g.verified})
        
        # Advanced
        if _li_guard:
            li = _li_guard.verify(body)
            if not li.verified:
                result["verified"] = False
                result["error"] = li.error
            result["guards"].append({"name": "LineItems", "ok": li.verified})
        
        return result
    
    return verify_checkout
