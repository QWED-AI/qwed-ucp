from enum import Enum, auto


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
