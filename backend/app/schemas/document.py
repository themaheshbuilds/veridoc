from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.enums import DocumentType


class PassportDocument(BaseModel):
    """Normalized data model for Passports (TD3/ICAO Doc 9303)."""
    document_type: DocumentType = DocumentType.PASSPORT
    passport_number: str = Field(..., description="Passport book/document number")
    issuing_country: str = Field(..., description="3-letter ISO 3166-1 alpha-3 code")
    nationality: str = Field(..., description="3-letter ISO code")
    surname: str = Field(..., description="Primary identifier")
    given_names: str = Field(default="", description="Secondary identifiers")
    date_of_birth: Optional[date] = Field(default=None, description="Date of birth")
    date_of_expiry: Optional[date] = Field(default=None, description="Document expiration date")
    gender: str = Field(default="X", description="M, F, or X")
    mrz_line1: Optional[str] = Field(default=None, description="Upper MRZ line (44 chars)")
    mrz_line2: Optional[str] = Field(default=None, description="Lower MRZ line (44 chars)")
    raw_ocr_fields: Dict[str, Any] = Field(default_factory=dict)


class PANDocument(BaseModel):
    """Normalized data model for Permanent Account Number (PAN) cards."""
    document_type: DocumentType = DocumentType.PAN
    pan_number: str = Field(..., description="10-character alphanumeric PAN")
    full_name: str = Field(..., description="Name of cardholder")
    father_name: Optional[str] = Field(default=None, description="Father's name")
    date_of_birth: Optional[date] = Field(default=None, description="DOB or Date of Incorporation")
    entity_type_code: Optional[str] = Field(default=None, description="4th character: P, C, H, F, A, T, B, L, J, G")
    surname_initial: Optional[str] = Field(default=None, description="5th character of PAN")
    is_format_valid: bool = Field(default=False, description="Whether PAN adheres strictly to ITD regex format")
    qr_payload: Optional[Dict[str, Any]] = Field(default=None, description="Decoded QR payload if present")
    raw_ocr_fields: Dict[str, Any] = Field(default_factory=dict)


class EducationSubjectMarks(BaseModel):
    """Subject-level breakdown for education marksheets."""
    subject_code: Optional[str] = None
    subject_name: str
    max_marks: float
    marks_obtained: float
    grade: Optional[str] = None


class EducationCertificateDocument(BaseModel):
    """Normalized data model for SSC / High School / Board Certificates."""
    document_type: DocumentType = DocumentType.EDUCATION_CERTIFICATE
    roll_number: str = Field(..., description="Student roll / registration / seat number")
    candidate_name: str = Field(..., description="Full student name")
    mother_name: Optional[str] = None
    father_name: Optional[str] = None
    board_or_university: str = Field(..., description="Issuing board, council, or university")
    examination_name: str = Field(default="Secondary School Certificate (SSC)", description="Name of examination")
    passing_year: int = Field(..., description="Year of passing/graduation")
    date_of_birth: Optional[date] = None
    total_max_marks: Optional[float] = None
    total_marks_obtained: Optional[float] = None
    percentage_or_cgpa: Optional[float] = None
    result_status: Optional[str] = Field(default="PASS", description="PASS / FAIL / COMPARTMENT")
    subjects: List[EducationSubjectMarks] = Field(default_factory=list)
    has_board_seal: bool = Field(default=False, description="Detected seal or signature")
    raw_ocr_fields: Dict[str, Any] = Field(default_factory=dict)
