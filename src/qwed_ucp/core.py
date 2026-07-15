"""Core UCPVerifier class for verifying UCP transactions."""

from dataclasses import dataclass, field
from typing import Any, Optional

from qwed_ucp.guards.money import MoneyGuard
from qwed_ucp.guards.state import StateGuard
from qwed_ucp.guards.schema import SchemaGuard
from qwed_ucp.types import TrustStatus, reconcile_trust_status, aggregate_status


@dataclass
class GuardResult:
    """Result from a single guard verification."""
    
    guard_name: str
    verified: bool = False
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    status: Optional[TrustStatus] = None
    
    def __post_init__(self):
        self.verified, self.status = reconcile_trust_status(self.verified, self.status)


@dataclass
class UCPVerificationResult:
    """Result from full UCP verification."""
    
    verified: bool = False
    guards: list[GuardResult] = field(default_factory=list)
    error: Optional[str] = None
    engine: str = "QWED-Deterministic-v1"
    verification_mode: str = "deterministic"
    status: Optional[TrustStatus] = None
    
    def __post_init__(self):
        self.verified, self.status = reconcile_trust_status(self.verified, self.status)
    
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
            strict_mode: Deprecated compatibility argument. Final checkout
                verification is always fail-closed and requires all mandatory
                guards to pass.
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
        
        # Determine overall result.
        # Final trust-boundary verification is always fail-closed: all mandatory
        # guards must pass, regardless of compatibility flags.
        all_verified = all(g.verified for g in guards_results)
        
        # Aggregate status — propagate the most-severe guard status
        # (ENGINE_ERROR > QUARANTINED > FAILED > UNVERIFIABLE > UNSUPPORTED > PARTIAL > VERIFIED)
        status = aggregate_status([g.status for g in guards_results])
        
        # Get first error if any
        error = None
        for g in guards_results:
            if not g.verified and g.error:
                error = g.error
                break
        
        return UCPVerificationResult(
            verified=all_verified,
            status=status,
            guards=guards_results,
            error=error
        )
    
    def _run_money_guard(self, checkout: dict[str, Any]) -> GuardResult:
        """Run Money Guard to verify math calculations."""
        try:
            result = self.money_guard.verify(checkout)
            return GuardResult(
                guard_name="Money Guard",
                status=result.status if hasattr(result, 'status') else None,
                verified=result.verified,
                error=result.error if hasattr(result, 'error') else None,
                details=result.details if hasattr(result, 'details') else {}
            )
        except Exception as e:
            return GuardResult(
                guard_name="Money Guard",
                status=TrustStatus.ENGINE_ERROR,
                verified=False,
                error=f"Guard execution error: {str(e)}"
            )
    
    def _run_state_guard(self, checkout: dict[str, Any]) -> GuardResult:
        """Run State Guard to verify checkout state logic."""
        try:
            result = self.state_guard.verify(checkout)
            return GuardResult(
                guard_name="State Guard",
                status=result.status if hasattr(result, 'status') else None,
                verified=result.verified,
                error=result.error if hasattr(result, 'error') else None,
                details=result.details if hasattr(result, 'details') else {}
            )
        except Exception as e:
            return GuardResult(
                guard_name="State Guard",
                status=TrustStatus.ENGINE_ERROR,
                verified=False,
                error=f"Guard execution error: {str(e)}"
            )
    
    def _run_structure_guard(self, checkout: dict[str, Any]) -> GuardResult:
        """Run Structure Guard to verify UCP schema compliance."""
        try:
            result = self.schema_guard.verify(checkout)
            return GuardResult(
                guard_name="Structure Guard",
                status=result.status if hasattr(result, 'status') else None,
                verified=result.verified,
                error=result.error if hasattr(result, 'error') else None,
                details=result.details if hasattr(result, 'details') else {}
            )
        except Exception as e:
            return GuardResult(
                guard_name="Structure Guard",
                status=TrustStatus.ENGINE_ERROR,
                verified=False,
                error=f"Guard execution error: {str(e)}"
            )
    
    def verify_totals_only(self, checkout: dict[str, Any]) -> GuardResult:
        """
        Quick verification of just the totals calculation.
        
        Use this for performance-critical paths where only math verification is needed.
        """
        return self._run_money_guard(checkout)
