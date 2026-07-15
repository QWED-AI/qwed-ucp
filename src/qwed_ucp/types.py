from enum import Enum, auto
from typing import Optional, Tuple


class TrustStatus(Enum):
    """Typed trust verdict for verification results.
    
    Replaces ambiguous ``verified: bool`` with explicit trust states.
    ``verified`` remains as a derived convenience property.
    """
    VERIFIED = auto()
    FAILED = auto()
    UNVERIFIABLE = auto()
    UNSUPPORTED = auto()
    PARTIAL = auto()
    ENGINE_ERROR = auto()
    QUARANTINED = auto()


# Ordering for aggregation: lower index = more severe
_TRUST_SEVERITY = [
    TrustStatus.ENGINE_ERROR,
    TrustStatus.QUARANTINED,
    TrustStatus.FAILED,
    TrustStatus.UNVERIFIABLE,
    TrustStatus.UNSUPPORTED,
    TrustStatus.PARTIAL,
    TrustStatus.VERIFIED,
]

_TRUST_SEVERITY_INDEX = {s: i for i, s in enumerate(_TRUST_SEVERITY)}


def aggregate_status(statuses: list[TrustStatus]) -> TrustStatus:
    """Return the most-severe trust status from a list (fail-closed)."""
    if not statuses:
        return TrustStatus.FAILED
    return min(statuses, key=lambda s: _TRUST_SEVERITY_INDEX.get(s, 0))


def reconcile_trust_status(
    verified: bool, status: Optional[TrustStatus]
) -> Tuple[bool, TrustStatus]:
    """Reconcile verified/status pair: explicit status takes precedence.
    
    Used in ``__post_init__`` of every result dataclass to keep logic
    in one place instead of duplicating across ~12 classes.
    """
    if status is not None:
        return (status == TrustStatus.VERIFIED, status)
    return (verified, TrustStatus.VERIFIED if verified else TrustStatus.FAILED)
