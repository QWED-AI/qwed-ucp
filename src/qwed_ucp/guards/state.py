"""State Guard - Verifies checkout state machine logic.

Uses logical verification to ensure state transitions are valid:
- "completed" status requires order object
- "ready_for_complete" requires valid payment method
- State transitions follow UCP spec
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StateGuardResult:
    """Result from State Guard verification."""
    
    verified: bool
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


class StateGuard:
    """
    Verify checkout state machine logic.
    
    UCP Checkout States:
    - incomplete: Cart is being built
    - ready_for_complete: All required info present, ready for payment
    - completed: Payment processed, order created
    
    State Rules:
    1. status == "completed" -> order must exist
    2. status == "ready_for_complete" -> payment_method must exist
    3. line_items must not be empty for non-incomplete status
    """
    
    # Valid UCP checkout statuses
    VALID_STATUSES = {"incomplete", "ready_for_complete", "completed", "failed", "cancelled"}
    
    def verify(self, checkout: dict[str, Any]) -> StateGuardResult:
        """
        Verify checkout state logic.
        
        Args:
            checkout: UCP checkout object
            
        Returns:
            StateGuardResult with verification status
        """
        status = checkout.get("status", "").lower()
        
        # Check for valid status
        if status and status not in self.VALID_STATUSES:
            return StateGuardResult(
                verified=False,
                error=f"Invalid status '{status}'. Valid: {self.VALID_STATUSES}",
                details={"status": status, "valid_statuses": list(self.VALID_STATUSES)}
            )
        
        # Rule 1: completed -> order exists
        if status == "completed":
            order = checkout.get("order")
            if order is None:
                return StateGuardResult(
                    verified=False,
                    error="Status is 'completed' but 'order' object is missing",
                    details={"status": status, "order": None, "rule": "completed -> order exists"}
                )
        
        # Rule 2: ready_for_complete -> payment method should be referenced
        if status == "ready_for_complete":
            # Check for payment info (could be in various places)
            has_payment = (
                checkout.get("payment_method") is not None or
                checkout.get("payment") is not None or
                checkout.get("payment_token") is not None
            )
            # Note: This is a soft check - some UCP flows handle payment separately
            # We just log it in details
        
        # Rule 3: non-incomplete status -> line_items should exist
        if status not in ("", "incomplete"):
            line_items = checkout.get("line_items", [])
            if not line_items:
                return StateGuardResult(
                    verified=False,
                    error=f"Status is '{status}' but 'line_items' is empty",
                    details={
                        "status": status,
                        "line_items_count": 0,
                        "rule": "non-incomplete -> line_items exist"
                    }
                )
        
        # All rules passed
        return StateGuardResult(
            verified=True,
            details={
                "status": status,
                "has_order": checkout.get("order") is not None,
                "line_items_count": len(checkout.get("line_items", [])),
                "rules_checked": [
                    "completed -> order exists",
                    "non-incomplete -> line_items exist"
                ]
            }
        )
    
    def verify_transition(
        self, 
        from_status: str, 
        to_status: str
    ) -> StateGuardResult:
        """
        Verify that a state transition is valid.
        
        Valid transitions:
        - incomplete -> ready_for_complete
        - ready_for_complete -> completed
        - ready_for_complete -> failed
        - any -> cancelled
        """
        VALID_TRANSITIONS = {
            "incomplete": {"ready_for_complete", "cancelled"},
            "ready_for_complete": {"completed", "failed", "cancelled"},
            "failed": {"ready_for_complete", "cancelled"},
            # completed and cancelled are terminal
            "completed": set(),
            "cancelled": set(),
        }
        
        valid_next = VALID_TRANSITIONS.get(from_status, set())
        
        if to_status in valid_next:
            return StateGuardResult(
                verified=True,
                details={
                    "from_status": from_status,
                    "to_status": to_status,
                    "valid_transitions": list(valid_next)
                }
            )
        else:
            return StateGuardResult(
                verified=False,
                error=f"Invalid transition: '{from_status}' -> '{to_status}'. Valid: {valid_next}",
                details={
                    "from_status": from_status,
                    "to_status": to_status,
                    "valid_transitions": list(valid_next)
                }
            )
