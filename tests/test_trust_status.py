"""Tests for TrustStatus enum and typed trust verdicts."""

from qwed_ucp.types import TrustStatus
from qwed_ucp.core import GuardResult, UCPVerificationResult, UCPVerifier


class TestTrustStatusEnum:
    """TrustStatus enum members are accessible and orderable."""

    def test_all_members_present(self):
        assert len(TrustStatus) == 7
        TrustStatus.VERIFIED
        TrustStatus.FAILED
        TrustStatus.UNVERIFIABLE
        TrustStatus.UNSUPPORTED
        TrustStatus.PARTIAL
        TrustStatus.ENGINE_ERROR
        TrustStatus.QUARANTINED

    def test_verified_is_truthy(self):
        assert TrustStatus.VERIFIED.name == "VERIFIED"


class TestGuardResultTrustStatus:
    """GuardResult derives status from verified and vice versa."""

    def test_default_verified_is_verified_status(self):
        r = GuardResult(guard_name="test")
        assert r.verified is True
        assert r.status == TrustStatus.VERIFIED

    def test_verified_true_sets_status_verified(self):
        r = GuardResult(guard_name="test", verified=True)
        assert r.status == TrustStatus.VERIFIED

    def test_verified_false_sets_status_failed(self):
        r = GuardResult(guard_name="test", verified=False)
        assert r.status == TrustStatus.FAILED

    def test_explicit_status_unverifiable_overrides_verified(self):
        r = GuardResult(guard_name="test", status=TrustStatus.UNVERIFIABLE)
        assert r.verified is False
        assert r.status == TrustStatus.UNVERIFIABLE

    def test_explicit_status_verified(self):
        r = GuardResult(guard_name="test", status=TrustStatus.VERIFIED)
        assert r.verified is True

    def test_status_takes_precedence_when_both_given(self):
        r = GuardResult(guard_name="test", verified=True, status=TrustStatus.ENGINE_ERROR)
        assert r.verified is False
        assert r.status == TrustStatus.ENGINE_ERROR


class TestUCPVerificationResultTrustStatus:
    """UCPVerificationResult derives status the same way."""

    def test_verified_true(self):
        r = UCPVerificationResult(verified=True)
        assert r.status == TrustStatus.VERIFIED

    def test_verified_false(self):
        r = UCPVerificationResult(verified=False)
        assert r.status == TrustStatus.FAILED

    def test_explicit_status(self):
        r = UCPVerificationResult(status=TrustStatus.PARTIAL)
        assert r.verified is False


class TestVerifierStatusPropagation:
    """UCPVerifier propagates guard status to top-level result."""

    def test_engine_error_guard_sets_engine_error_status(self):
        """A guard that raises an exception gets ENGINE_ERROR status."""
        checkout = {"currency": "USD", "totals": [], "status": "incomplete"}

        class FailingGuard:
            def verify(self, _):
                raise RuntimeError("simulated failure")

        verifier = UCPVerifier()
        verifier.money_guard = FailingGuard()
        result = verifier.verify_checkout(checkout)
        assert result.verified is False
        assert result.status == TrustStatus.ENGINE_ERROR
        assert any(
            g.status == TrustStatus.ENGINE_ERROR for g in result.guards
        )

    def test_partial_failure_has_failed_status(self):
        """Checkout with a bad currency yields FAILED status."""
        checkout = {
            "currency": "XYZ",
            "totals": [{"type": "subtotal", "amount": 35.00}],
            "status": "incomplete",
        }
        verifier = UCPVerifier()
        result = verifier.verify_checkout(checkout)
        assert result.verified is False
        assert result.status == TrustStatus.FAILED
