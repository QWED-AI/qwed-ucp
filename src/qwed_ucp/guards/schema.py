"""Schema Guard - Verifies UCP JSON schema compliance.

Validates that checkout objects conform to UCP specification:
- Required fields are present
- Data types are correct
- Enums contain valid values
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


@dataclass
class SchemaGuardResult:
    """Result from Schema Guard verification."""
    
    verified: bool
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


# Minimal checkout schema (subset of UCP spec)
# Full schema available at: https://github.com/Universal-Commerce-Protocol/ucp
CHECKOUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["currency"],
    "properties": {
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code",
            "pattern": "^[A-Z]{3}$"
        },
        "status": {
            "type": "string",
            "enum": ["incomplete", "ready_for_complete", "completed", "failed", "cancelled"]
        },
        "totals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "amount"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["subtotal", "tax", "fulfillment", "discount", "fee", "total"]
                    },
                    "amount": {
                        "type": "number",
                        "minimum": 0
                    }
                }
            }
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "price": {"type": "number", "minimum": 0}
                }
            }
        },
        "order": {
            "type": ["object", "null"],
            "properties": {
                "id": {"type": "string"},
                "status": {"type": "string"}
            }
        }
    }
}


class SchemaGuard:
    """
    Verify UCP schema compliance.
    
    Validates checkout objects against the UCP JSON schema specification.
    Uses jsonschema library for validation if available, falls back to
    manual validation for required fields.
    """
    
    def __init__(self, schema: Optional[dict] = None):
        """
        Initialize Schema Guard.
        
        Args:
            schema: Optional custom schema. Defaults to UCP checkout schema.
        """
        self.schema = schema or CHECKOUT_SCHEMA
    
    def verify(self, checkout: dict[str, Any]) -> SchemaGuardResult:
        """
        Verify checkout against UCP schema.
        
        Args:
            checkout: UCP checkout object to validate
            
        Returns:
            SchemaGuardResult with validation status
        """
        if HAS_JSONSCHEMA:
            return self._verify_with_jsonschema(checkout)
        else:
            return self._verify_manual(checkout)
    
    def _verify_with_jsonschema(self, checkout: dict[str, Any]) -> SchemaGuardResult:
        """Verify using jsonschema library."""
        try:
            jsonschema.validate(checkout, self.schema)
            return SchemaGuardResult(
                verified=True,
                details={
                    "validation_method": "jsonschema",
                    "schema_version": self.schema.get("$schema", "unknown")
                }
            )
        except jsonschema.ValidationError as e:
            return SchemaGuardResult(
                verified=False,
                error=f"Schema validation failed: {e.message}",
                details={
                    "validation_method": "jsonschema",
                    "path": list(e.path),
                    "validator": e.validator,
                    "message": e.message
                }
            )
        except jsonschema.SchemaError as e:
            return SchemaGuardResult(
                verified=False,
                error=f"Invalid schema: {e.message}",
                details={"validation_method": "jsonschema", "schema_error": True}
            )
    
    def _verify_manual(self, checkout: dict[str, Any]) -> SchemaGuardResult:
        """Fallback manual validation for required fields."""
        errors = []
        
        # Check required fields
        required = self.schema.get("required", [])
        for field_name in required:
            if field_name not in checkout:
                errors.append(f"Missing required field: '{field_name}'")
        
        # Check currency format if present
        currency = checkout.get("currency")
        if currency is not None:
            if not isinstance(currency, str) or len(currency) != 3:
                errors.append(f"Invalid currency format: '{currency}' (expected 3-letter ISO code)")
        
        # Check totals format if present
        totals = checkout.get("totals")
        if totals is not None:
            if not isinstance(totals, list):
                errors.append(f"'totals' must be an array, got {type(totals).__name__}")
            else:
                for i, item in enumerate(totals):
                    if not isinstance(item, dict):
                        errors.append(f"totals[{i}] must be an object")
                    elif "type" not in item or "amount" not in item:
                        errors.append(f"totals[{i}] missing 'type' or 'amount'")
        
        # Check status if present
        status = checkout.get("status")
        valid_statuses = {"incomplete", "ready_for_complete", "completed", "failed", "cancelled"}
        if status is not None and status not in valid_statuses:
            errors.append(f"Invalid status: '{status}'")
        
        if errors:
            return SchemaGuardResult(
                verified=False,
                error="; ".join(errors),
                details={
                    "validation_method": "manual",
                    "errors": errors,
                    "error_count": len(errors)
                }
            )
        else:
            return SchemaGuardResult(
                verified=True,
                details={
                    "validation_method": "manual",
                    "fields_checked": ["currency", "totals", "status"]
                }
            )
    
    @classmethod
    def load_schema_from_file(cls, path: str) -> "SchemaGuard":
        """
        Load schema from a JSON file.
        
        Args:
            path: Path to JSON schema file
            
        Returns:
            SchemaGuard instance with loaded schema
        """
        with open(path, "r") as f:
            schema = json.load(f)
        return cls(schema=schema)
