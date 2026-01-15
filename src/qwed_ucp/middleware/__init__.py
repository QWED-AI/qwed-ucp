"""Middleware package for QWED-UCP."""

# Note: FastAPI middleware requires starlette which may not be installed
# Import will fail gracefully if dependencies not available

__all__: list[str] = []

try:
    from .fastapi import QWEDUCPMiddleware as _Middleware  # noqa: F401
    from .fastapi import create_verification_dependency as _create_dep  # noqa: F401
    
    # Re-export with proper names
    QWEDUCPMiddleware = _Middleware
    create_verification_dependency = _create_dep
    __all__.extend(["QWEDUCPMiddleware", "create_verification_dependency"])
except ImportError:
    pass  # starlette not installed

