"""Tests for QWED-UCP middleware fail-closed behavior."""

import json

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from qwed_ucp.middleware.fastapi import QWEDUCPMiddleware


def _app():
    """Create a minimal Starlette app with the middleware."""
    async def handler(request):
        body = await request.body()
        return JSONResponse({"received": True, "body_length": len(body)})

    routes = [
        Route("/checkout-sessions", handler, methods=["POST", "GET"]),
        Route("/health", handler, methods=["GET"]),
    ]
    middleware = [Middleware(QWEDUCPMiddleware)]
    return Starlette(routes=routes, middleware=middleware)


client = TestClient(_app())


class TestMiddlewareFailClosed:
    """Tests that the middleware fails closed on unparseable bodies."""

    def test_empty_body_blocked(self):
        """Empty body on a protected path must return 422."""
        resp = client.post("/checkout-sessions", content=b"")
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"
        assert "empty" in data["message"].lower()
        assert resp.headers.get("X-QWED-Verified") == "false"

    def test_malformed_json_blocked(self):
        """Malformed JSON on a protected path must return 422."""
        resp = client.post(
            "/checkout-sessions",
            content=b"not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"
        assert "malformed" in data["message"].lower() or "json" in data["message"].lower()
        assert resp.headers.get("X-QWED-Verified") == "false"

    def test_non_json_content_blocked(self):
        """Non-JSON body (e.g. plain text) on a protected path must return 422."""
        resp = client.post(
            "/checkout-sessions",
            content=b"some=form&data=1",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"
        assert resp.headers.get("X-QWED-Verified") == "false"

    def test_json_array_blocked(self):
        """Valid JSON array (non-object) on a protected path must return 422."""
        resp = client.post(
            "/checkout-sessions",
            content=b"[]",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"
        assert resp.headers.get("X-QWED-Verified") == "false"

    def test_json_number_blocked(self):
        """Valid JSON number (non-object) on a protected path must return 422."""
        resp = client.post(
            "/checkout-sessions",
            content=b"42",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"

    def test_json_null_blocked(self):
        """JSON null on a protected path must return 422."""
        resp = client.post(
            "/checkout-sessions",
            content=b"null",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"

    def test_binary_body_blocked(self):
        """Non-UTF-8 binary body on a protected path must return 422."""
        resp = client.post(
            "/checkout-sessions",
            content=b"\xff\xfe\x00\x01",
            headers={"Content-Type": "application/octet-stream"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == "UNPARSEABLE_REQUEST"

    def test_valid_json_on_protected_path(self):
        """Valid JSON body must proceed to verification (not blocked by parse check)."""
        resp = client.post(
            "/checkout-sessions",
            content=json.dumps({"currency": "USD", "totals": []}),
            headers={"Content-Type": "application/json"},
        )
        # Should not be the parse-error response — even if verification itself
        # fails, the error code is VERIFICATION_FAILED, not a parse error message.
        assert resp.status_code in (200, 422)
        data = resp.json()
        assert "empty" not in data.get("message", "").lower()
        assert "malformed" not in data.get("message", "").lower()

    def test_non_matching_method_passes_through(self):
        """GET on a protected path must pass through (not verified by default)."""
        resp = client.get("/checkout-sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"] is True

    def test_non_matching_path_passes_through(self):
        """Request to a non-protected path must pass through."""
        resp = client.get("/health")
        assert resp.status_code == 200


class TestVerificationDependency:
    """Tests for create_verification_dependency fail-closed behavior."""

    def test_dependency_rejects_array(self):
        """The dependency function must reject non-object JSON."""
        import asyncio

        from unittest.mock import AsyncMock

        from qwed_ucp.middleware.fastapi import create_verification_dependency

        verify = create_verification_dependency()

        request = AsyncMock()
        request.json = AsyncMock(return_value=[])

        result = asyncio.run(verify(request))
        assert result["verified"] is False
        assert "object" in result["error"].lower()

    def test_dependency_rejects_number(self):
        """The dependency function must reject numeric JSON."""
        import asyncio

        from unittest.mock import AsyncMock

        from qwed_ucp.middleware.fastapi import create_verification_dependency

        verify = create_verification_dependency()

        request = AsyncMock()
        request.json = AsyncMock(return_value=42)

        result = asyncio.run(verify(request))
        assert result["verified"] is False

    def test_dependency_rejects_malformed_json(self):
        """The dependency function must reject malformed JSON."""
        import asyncio

        from unittest.mock import AsyncMock

        from qwed_ucp.middleware.fastapi import create_verification_dependency

        verify = create_verification_dependency()

        request = AsyncMock()
        request.json = AsyncMock(side_effect=json.JSONDecodeError("msg", "doc", 0))

        result = asyncio.run(verify(request))
        assert result["verified"] is False
        assert "malformed" in result["error"].lower()

    def test_dependency_rejects_empty_body(self):
        """The dependency function must reject empty body."""
        import asyncio

        from unittest.mock import AsyncMock

        from qwed_ucp.middleware.fastapi import create_verification_dependency

        verify = create_verification_dependency()

        request = AsyncMock()
        request.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))

        result = asyncio.run(verify(request))
        assert result["verified"] is False
