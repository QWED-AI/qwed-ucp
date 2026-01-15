"""Core UCPVerifier class for verifying UCP transactions."""

from dataclasses import dataclass, field
from typing import Any, Optional

from qwed_ucp.guards.money import MoneyGuard
from qwed_ucp.guards.state import StateGuard
from qwed_ucp.guards.schema import SchemaGuard


@dataclass
class GuardResult:
    """Result from a single guard verification."""
    
    guard_name: str
    verified: bool
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class UCPVerificationResult:
    """Result from full UCP verification."""
    
    verified: bool
    guards: list[GuardResult] = field(default_factory=list)
    error: Optional[str] = None
    
    def __str__(self) -> str:
        if self.verified:
            return "✅ All guards passed"
        failed = [g for g in self.guards if not g.verified]
        return f"❌ {len(failed)} guard(s) failed: {', '.join(g.guard_name for g in failed)}"


class UCPVerifier:
    """
    Verify UCP (Universal Commerce Protocol) transactions using QWED engines.
    
    Implements 3 verification guards:
    1. Money Guard - Verifies math calculations (cart totals, tax, discounts)
    2. State Guard - Verifies checkout state machine logic
    3. Structure Guard - Verifies UCP schema compliance
    
    Example:
        >>> verifier = UCPVerifier()
        >>> checkout = {
        ...     "currency": "USD",
        ...     "totals": [
        ...         {"type": "subtotal", "amount": 100.00},
        ...         {"type": "tax", "amount": 8.25},
        ...         {"type": "total", "amount": 108.25}
        ...     ],
        ...     "status": "ready_for_complete"
        ... }
        >>> result = verifier.verify_checkout(checkout)
        >>> print(result.verified)
        True
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize UCPVerifier.
        
        Args:
            strict_mode: If True, all guards must pass. If False, only Money Guard is required.
        """
        self.strict_mode = strict_mode
        self.money_guard = MoneyGuard()
        self.state_guard = StateGuard()
        self.schema_guard = SchemaGuard()
    
    def verify_checkout(self, checkout: dict[str, Any]) -> UCPVerificationResult:
        """
        Verify a UCP checkout object.
        
        Args:
            checkout: UCP checkout JSON object
            
        Returns:
            UCPVerificationResult with verification status and guard details
        """
        guards_results = []
        
        # Guard 1: Money Guard (Math verification)
        money_result = self._run_money_guard(checkout)
        guards_results.append(money_result)
        
        # Guard 2: State Guard (Logic verification)
        state_result = self._run_state_guard(checkout)
        guards_results.append(state_result)
        
        # Guard 3: Structure Guard (Schema validation)
        structure_result = self._run_structure_guard(checkout)
        guards_results.append(structure_result)
        
        # Determine overall result
        if self.strict_mode:
            all_verified = all(g.verified for g in guards_results)
        else:
            # In non-strict mode, only Money Guard is required
            all_verified = money_result.verified
        
        # Get first error if any
        error = None
        for g in guards_results:
            if not g.verified and g.error:
                error = g.error
                break
        
        return UCPVerificationResult(
            verified=all_verified,
            guards=guards_results,
            error=error
        )
    
    def _run_money_guard(self, checkout: dict[str, Any]) -> GuardResult:
        """Run Money Guard to verify math calculations."""
        try:
            result = self.money_guard.verify(checkout)
            return GuardResult(
                guard_name="Money Guard",
                verified=result.verified,
                error=result.error if hasattr(result, 'error') else None,
                details=result.details if hasattr(result, 'details') else {}
            )
        except Exception as e:
            return GuardResult(
                guard_name="Money Guard",
                verified=False,
                error=f"Guard execution error: {str(e)}"
            )
    
    def _run_state_guard(self, checkout: dict[str, Any]) -> GuardResult:
        """Run State Guard to verify checkout state logic."""
        try:
            result = self.state_guard.verify(checkout)
            return GuardResult(
                guard_name="State Guard",
                verified=result.verified,
                error=result.error if hasattr(result, 'error') else None,
                details=result.details if hasattr(result, 'details') else {}
            )
        except Exception as e:
            return GuardResult(
                guard_name="State Guard",
                verified=False,
                error=f"Guard execution error: {str(e)}"
            )
    
    def _run_structure_guard(self, checkout: dict[str, Any]) -> GuardResult:
        """Run Structure Guard to verify UCP schema compliance."""
        try:
            result = self.schema_guard.verify(checkout)
            return GuardResult(
                guard_name="Structure Guard",
                verified=result.verified,
                error=result.error if hasattr(result, 'error') else None,
                details=result.details if hasattr(result, 'details') else {}
            )
        except Exception as e:
            return GuardResult(
                guard_name="Structure Guard",
                verified=False,
                error=f"Guard execution error: {str(e)}"
            )
    
    def verify_totals_only(self, checkout: dict[str, Any]) -> GuardResult:
        """
        Quick verification of just the totals calculation.
        
        Use this for performance-critical paths where only math verification is needed.
        """
        return self._run_money_guard(checkout)
