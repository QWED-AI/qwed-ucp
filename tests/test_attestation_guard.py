"""Tests for Attestation Guard replay/context hardening."""

import pytest

from qwed_ucp.guards.attestation import AttestationGuard


class TestAttestationGuard:
    """Attestation replay and binding tests."""

    def setup_method(self):
        self.guard = AttestationGuard(
            secret_key="0123456789abcdef0123456789abcdef",
            allow_insecure=True,
        )
        self.checkout = {
            "currency": "USD",
            "status": "ready_for_complete",
            "totals": [
                {"type": "subtotal", "amount": 100.00},
                {"type": "tax", "amount": 8.25},
                {"type": "total", "amount": 108.25},
            ],
        }
        self.verification_result = {
            "verified": True,
            "errors": [],
        }

    def test_sign_checkout_requires_attempt_and_nonce(self):
        """Attestations must be bound to explicit event context."""
        result = self.guard.sign_checkout(
            self.checkout,
            self.verification_result,
            guards_passed=["Money Guard"],
            transaction_attempt_id="",
            request_nonce="",
        )

        assert result.verified is False
        assert "transaction_attempt_id" in result.error

    def test_attestation_verifies_with_matching_context_once(self):
        """A valid attestation can be consumed once for its exact context."""
        signed = self.guard.sign_checkout(
            self.checkout,
            self.verification_result,
            guards_passed=["Money Guard", "State Guard", "Structure Guard"],
            transaction_attempt_id="attempt-123",
            request_nonce="nonce-abc",
            session_id="session-1",
            merchant_id="merchant-9",
        )

        assert signed.verified is True
        assert signed.details["attestation_id"]

        verified = self.guard.verify_attestation(
            signed.token,
            expected_transaction_attempt_id="attempt-123",
            expected_request_nonce="nonce-abc",
            expected_session_id="session-1",
            expected_merchant_id="merchant-9",
        )

        assert verified.verified is True
        assert verified.details["jti"] == signed.details["attestation_id"]

    def test_attestation_replay_is_rejected_after_consumption(self):
        """Consumed attestations must not be reusable."""
        signed = self.guard.sign_checkout(
            self.checkout,
            self.verification_result,
            transaction_attempt_id="attempt-123",
            request_nonce="nonce-abc",
        )

        first = self.guard.verify_attestation(
            signed.token,
            expected_transaction_attempt_id="attempt-123",
            expected_request_nonce="nonce-abc",
        )
        second = self.guard.verify_attestation(
            signed.token,
            expected_transaction_attempt_id="attempt-123",
            expected_request_nonce="nonce-abc",
        )

        assert first.verified is True
        assert second.verified is False
        assert "already been consumed" in second.error

    def test_attestation_context_mismatch_fails_closed(self):
        """Attempt/nonce mismatch must invalidate the attestation."""
        signed = self.guard.sign_checkout(
            self.checkout,
            self.verification_result,
            transaction_attempt_id="attempt-123",
            request_nonce="nonce-abc",
        )

        result = self.guard.verify_attestation(
            signed.token,
            expected_transaction_attempt_id="attempt-other",
            expected_request_nonce="nonce-abc",
            consume=False,
        )

        assert result.verified is False
        assert "binding mismatch" in result.error

    def test_create_receipt_links_attestation_and_audit_chain(self):
        """Receipts should carry attestation and continuity identifiers."""
        receipt = self.guard.create_receipt(
            self.checkout,
            self.verification_result,
            attestation_id="att-1",
            transaction_attempt_id="attempt-123",
            previous_receipt_id="receipt-older",
        )

        assert receipt["attestation_id"] == "att-1"
        assert receipt["transaction_attempt_id"] == "attempt-123"
        assert receipt["previous_receipt_id"] == "receipt-older"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])