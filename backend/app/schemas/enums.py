from enum import Enum


class SourceType(str, Enum):
    """Categorization of evidence provenance and generation channel."""
    OFFICIAL = "OFFICIAL"
    DOCUMENT = "DOCUMENT"
    OCR = "OCR"
    FORENSIC = "FORENSIC"
    BIOMETRIC = "BIOMETRIC"
    AI = "AI"
    MOCK = "MOCK"


class EvidenceStatus(str, Enum):
    """Evaluation status for an individual atomic evidence item."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INCONCLUSIVE = "INCONCLUSIVE"


class OverallVerdict(str, Enum):
    """Top-level screening verdict returned by the verification pipeline."""
    CLEAR = "CLEAR"
    SUSPICIOUS = "SUSPICIOUS"
    INCONCLUSIVE = "INCONCLUSIVE"


class RiskLevel(str, Enum):
    """Calibrated fraud / inconsistency risk level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OfficerAction(str, Enum):
    """Human-in-the-loop operational decisions by authorized border officers."""
    CLEAR = "CLEAR"
    SECONDARY_INSPECTION = "SECONDARY_INSPECTION"
    ESCALATE = "ESCALATE"


class DocumentType(str, Enum):
    """Supported anchor document classifications."""
    PASSPORT = "PASSPORT"
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    DRIVING_LICENCE = "DRIVING_LICENSE"
    VOTER_ID = "VOTER_ID"
    VISA = "VISA"
    EDUCATION_CERTIFICATE = "EDUCATION_CERTIFICATE"
    CIVIL_REGISTRATION = "CIVIL_REGISTRATION"
    REVENUE_AND_LAND = "REVENUE_AND_LAND"
    COMMUNITY_AND_INCOME = "COMMUNITY_AND_INCOME"
    FINANCIAL_AND_BANKING = "FINANCIAL_AND_BANKING"
    UTILITY_AND_MUNICIPAL = "UTILITY_AND_MUNICIPAL"
    LEGAL_AND_EMPLOYMENT = "LEGAL_AND_EMPLOYMENT"
    IDENTITY_CARD = "IDENTITY_CARD"
    GOVERNMENT_DOCUMENT = "GOVERNMENT_DOCUMENT"
    GENERAL_DOCUMENT = "GENERAL_DOCUMENT"
    UNKNOWN = "UNKNOWN"



class ConnectorStatus(str, Enum):
    """Standardized responses from authoritative or mock registries."""
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    UNAUTHORIZED = "UNAUTHORIZED"
    TIMEOUT = "TIMEOUT"
