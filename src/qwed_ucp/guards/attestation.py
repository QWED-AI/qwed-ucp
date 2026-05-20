import jwt
import time
import json
import hashlib
import os
import secrets
import threading
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AttestationResult:
    """Result from attestation signing."""
    
    token: Optional[str] = None
    verified: bool = False
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    engine: str = "QWED-Deterministic-v1"
    verification_mode: str = "deterministic"


class AttestationGuard:
    """
    Generates cryptographic proofs (JWTs) for UCP verification results.
    
    Creates tamper-proof tokens that attest:
    - A checkout was verified at a specific time
    - The verification result (pass/fail)
    - Which guards ran and their outcomes
    """
    
    def __init__(self, secret_key: str = None, allow_insecure: bool = False):
        """
        Initialize AttestationGuard.
        
        Args:
            secret_key: Secret key for JWT signing (or set QWED_ATTESTATION_SECRET)
            allow_insecure: Allow dev mode with insecure default secret
        """
        self.secret = secret_key or os.environ.get("QWED_ATTESTATION_SECRET")
        self._consumed_attestation_ids: set[str] = set()
        self._consumed_attestation_ids_lock = threading.Lock()
        if not self.secret:
            if allow_insecure or os.environ.get("QWED_DEV_MODE") == "1":
                # Generate random secret for dev mode - not hardcoded
                self.secret = secrets.token_hex(32)
            else:
                raise ValueError("QWED_ATTESTATION_SECRET required. Set allow_insecure=True for dev mode.")
    
    def sign_checkout(
        self,
        checkout: Dict[str, Any],
        verification_result: Dict[str, Any],
        guards_passed: list = None,
        *,
        transaction_attempt_id: str,
        request_nonce: str,
        session_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        previous_attestation_id: Optional[str] = None,
    ) -> AttestationResult:
        """
        Create a JWT attesting that a checkout was verified.
        
        Args:
            checkout: The UCP checkout object
            verification_result: Result from UCPVerifier.verify_checkout()
            guards_passed: List of guards that passed (optional)
            transaction_attempt_id: Unique ID for this verification attempt
            request_nonce: One-time nonce bound to this verification event
            session_id: Optional session binding
            merchant_id: Optional merchant binding
            previous_attestation_id: Optional audit-chain predecessor
            
        Returns:
            AttestationResult with signed JWT token
        """
        try:
            if not transaction_attempt_id:
                raise ValueError("transaction_attempt_id is required for attestation")
            if not request_nonce:
                raise ValueError("request_nonce is required for attestation")

            # Create hash of checkout to link attestation without storing PII
            checkout_hash = hashlib.sha256(
                json.dumps(checkout, sort_keys=True).encode('utf-8')
            ).hexdigest()
            attestation_id = str(uuid.uuid4())
            
            payload = {
                "iss": "qwed-ucp-attestation",
                "jti": attestation_id,
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,  # 1 hour expiry
                "checkout_hash": checkout_hash,
                "transaction_attempt_id": transaction_attempt_id,
                "request_nonce": request_nonce,
                "session_id": session_id,
                "merchant_id": merchant_id,
                "previous_attestation_id": previous_attestation_id,
                "verified": verification_result.get("verified", False),
                "guards_passed": guards_passed or [],
                "errors": verification_result.get("errors", []),
                "engine": "QWED-Deterministic-v1",
                "verification_mode": "deterministic"
            }
            
            token = jwt.encode(payload, self.secret, algorithm="HS256")
            
            return AttestationResult(
                token=token,
                verified=True,
                details={
                    "attestation_id": attestation_id,
                    "checkout_hash": checkout_hash,
                    "transaction_attempt_id": transaction_attempt_id,
                    "request_nonce": request_nonce,
                    "session_id": session_id,
                    "merchant_id": merchant_id,
                    "previous_attestation_id": previous_attestation_id,
                    "issued_at": payload["iat"],
                    "expires_at": payload["exp"]
                }
            )
        except Exception as e:
            return AttestationResult(
                verified=False,
                error=f"Failed to create attestation: {str(e)}"
            )
    
    def verify_attestation(
        self,
        token: str,
        *,
        expected_transaction_attempt_id: str,
        expected_request_nonce: str,
        expected_session_id: Optional[str] = None,
        expected_merchant_id: Optional[str] = None,
        consume: bool = True,
    ) -> AttestationResult:
        """
        Verify a QWED-UCP attestation token.
        
        Args:
            token: JWT token to verify
            expected_transaction_attempt_id: Expected attempt binding
            expected_request_nonce: Expected nonce binding
            expected_session_id: Optional expected session binding
            expected_merchant_id: Optional expected merchant binding
            consume: Mark the attestation as consumed after successful verification
            
        Returns:
            AttestationResult with decoded payload
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])

            self._validate_attestation_context(
                payload,
                expected_transaction_attempt_id=expected_transaction_attempt_id,
                expected_request_nonce=expected_request_nonce,
                expected_session_id=expected_session_id,
                expected_merchant_id=expected_merchant_id,
            )

            attestation_id = payload.get("jti")
            if not attestation_id:
                raise jwt.InvalidTokenError("Attestation missing jti")
            with self._consumed_attestation_ids_lock:
                if attestation_id in self._consumed_attestation_ids:
                    raise jwt.InvalidTokenError("Attestation token has already been consumed")
                if consume:
                    self._consumed_attestation_ids.add(attestation_id)

            return AttestationResult(
                token=token,
                verified=True,
                details=payload
            )
        except ValueError as e:
            return AttestationResult(
                verified=False,
                error=f"Invalid attestation context: {str(e)}"
            )
        except jwt.ExpiredSignatureError:
            return AttestationResult(
                verified=False,
                error="Attestation token expired"
            )
        except jwt.InvalidTokenError as e:
            return AttestationResult(
                verified=False,
                error=f"Invalid attestation: {str(e)}"
            )
    
    def create_receipt(
        self,
        checkout: Dict[str, Any],
        verification_result: Dict[str, Any],
        *,
        attestation_id: str,
        transaction_attempt_id: str,
        previous_receipt_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a verification receipt (non-cryptographic summary).
        
        Args:
            checkout: The UCP checkout object
            verification_result: Result from verification
            attestation_id: Unique attestation ID for audit linkage
            transaction_attempt_id: Verification attempt binding
            previous_receipt_id: Optional audit-chain predecessor
            
        Returns:
            Receipt dictionary
        """
        try:
            checkout_hash = hashlib.sha256(
                json.dumps(checkout, sort_keys=True).encode('utf-8')
            ).hexdigest()[:16]  # Short hash for receipt
        except (TypeError, ValueError):
            # Fallback for non-JSON-serializable objects
            checkout_hash = hashlib.sha256(
                str(checkout).encode('utf-8')
            ).hexdigest()[:16]
        
        receipt_id = f"QWED-{attestation_id.upper()}"

        return {
            "receipt_id": receipt_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "attestation_id": attestation_id,
            "transaction_attempt_id": transaction_attempt_id,
            "previous_receipt_id": previous_receipt_id,
            "verified": verification_result.get("verified", False),
            "engine": "QWED-Deterministic-v1",
            "verification_mode": "deterministic",
            "errors": verification_result.get("errors", [])
        }

    def _validate_attestation_context(
        self,
        payload: Dict[str, Any],
        *,
        expected_transaction_attempt_id: str,
        expected_request_nonce: str,
        expected_session_id: Optional[str],
        expected_merchant_id: Optional[str],
    ) -> None:
        """Fail closed when attestation context does not match expected event binding."""
        required_fields = {
            "jti": payload.get("jti"),
            "transaction_attempt_id": payload.get("transaction_attempt_id"),
            "request_nonce": payload.get("request_nonce"),
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            raise ValueError(f"missing required attestation fields: {', '.join(missing_fields)}")

        if payload["transaction_attempt_id"] != expected_transaction_attempt_id:
            raise ValueError("transaction attempt binding mismatch")
        if payload["request_nonce"] != expected_request_nonce:
            raise ValueError("request nonce binding mismatch")
        if expected_session_id is not None and payload.get("session_id") != expected_session_id:
            raise ValueError("session binding mismatch")
        if expected_merchant_id is not None and payload.get("merchant_id") != expected_merchant_id:
            raise ValueError("merchant binding mismatch")
