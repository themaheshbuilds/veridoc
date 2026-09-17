from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.enums import DocumentType, OfficerAction, OverallVerdict, RiskLevel
from app.schemas.evidence import EvidenceItem


class BoundingBox(BaseModel):
    """Normalized or pixel bounding box coordinates for evidence visualization."""
    x: float = Field(..., description="X coordinate (percentage 0-100 or pixels)")
    y: float = Field(..., description="Y coordinate (percentage 0-100 or pixels)")
    width: float = Field(..., description="Width (percentage 0-100 or pixels)")
    height: float = Field(..., description="Height (percentage 0-100 or pixels)")
    label: str = Field(..., description="Detection label (e.g. SUSPICIOUS_ELA, FACE, QR_CODE)")
    severity: str = Field(default="INFO", description="SUSPICIOUS, WARNING, INFO, PASS")
    details: Optional[str] = None


class DocumentQualityReport(BaseModel):
    """Real optical quality analysis results before deeper pipeline execution."""
    quality_verdict: str = Field(..., description="GOOD, ACCEPTABLE, or POOR")
    blur_score: float = Field(..., description="Laplacian variance sharpness score")
    is_blurry: bool
    brightness: float = Field(..., description="Mean pixel intensity 0-255")
    contrast: float = Field(..., description="Pixel standard deviation")
    width: int
    height: int
    skew_deg: float = Field(default=0.0, description="Estimated skew angle in degrees")
    issues: List[str] = Field(default_factory=list, description="Specific quality defects identified")
    remediation_advice: Optional[str] = None


class PreprocessingReport(BaseModel):
    """Details of image enhancement and geometry correction applied before OCR."""
    rotation_corrected_deg: float = Field(default=0.0, description="Angle rotated to achieve upright orientation")
    perspective_corrected: bool = Field(default=False, description="Whether 4-point quadrilateral warping was applied")
    boundary_detected: bool = Field(default=False, description="Whether document physical perimeter was segmented")
    crop_applied: bool = Field(default=False, description="Whether background margins were clipped")
    denoising_applied: bool = Field(default=True, description="Whether edge-preserving denoising was executed")
    contrast_enhanced: bool = Field(default=True, description="Whether CLAHE histogram equalization was performed")
    resolution_upscaled: bool = Field(default=False, description="Whether image was super-resolved for text clarity")
    variants_tested: int = Field(default=1, description="Number of preprocessed visual candidate variants evaluated")
    selected_variant: str = Field(default="clahe_enhanced", description="The variant yielding highest OCR confidence")
    ocr_engine_used: str = Field(default="RapidOCR (ONNX Deep Learning Offline)", description="Primary OCR engine pipeline used")
    languages_detected: List[str] = Field(default_factory=lambda: ["English"], description="Detected script languages")
    enhanced_image_base64: Optional[str] = Field(default=None, description="Base64 preview of enhanced image used for OCR")


class DynamicDocumentCategory(BaseModel):
    """Dynamic document classification discovered from characteristics."""
    category: str = Field(default="GENERAL_DOCUMENT", description="Broad functional category")
    sub_category: Optional[str] = Field(default=None, description="Fine-grained document type")
    confidence: float = Field(default=1.0, description="Classification confidence score")
    visual_characteristics: List[str] = Field(default_factory=list, description="Identified visual elements e.g. seals, letterheads, bilingual layout")
    detected_institution: Optional[str] = Field(default=None, description="Issuing board, university, or ministry")
    detected_state_or_country: Optional[str] = Field(default=None, description="Detected jurisdiction or state")


class ExtractedFields(BaseModel):
    """Structured fields extracted from OCR, PDF text, or QR payload."""
    document_type: str = "UNKNOWN"
    document_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    raw_text: Optional[str] = None
    qr_payload: Optional[str] = None
    qr_data_parsed: Dict[str, Any] = Field(default_factory=dict)
    checksums_valid: Optional[bool] = None
    checksum_details: Optional[str] = None

    # Extended Demographic & Multilingual Fields
    name_regional: Optional[str] = None
    care_of: Optional[str] = None
    care_of_regional: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    vid: Optional[str] = None
    enrolment_number: Optional[str] = None

    # Dynamic Field Extraction & Open Categorization
    dynamic_category: Optional[DynamicDocumentCategory] = None
    dynamic_fields: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary key-value pairs dynamically discovered")

    barcode_payload: Optional[str] = None
    barcode_format: Optional[str] = None

    # Uncertainty & Low-Confidence Management (Never hallucinate text)
    ocr_confidence: float = Field(default=1.0, description="Calculated OCR character and dictionary confidence")
    is_uncertain: bool = Field(default=False, description="True if document optical clarity prevents confident extraction")
    uncertain_fields: List[str] = Field(default_factory=list, description="Fields with ambiguous optical clarity")
    clarity_advisory: Optional[str] = Field(default=None, description="User guidance when scan is unclear")



class ForensicAnalysisReport(BaseModel):
    """Real image tampering and computer vision forensic findings."""
    ela_anomaly_score: float = Field(default=0.0, description="Error Level Analysis discrepancy ratio 0.0-1.0")
    ela_heatmap_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded ELA difference heatmap (data:image/png;base64,...) for frontend 3-column display"
    )
    tampering_detected: bool = False
    frankenstein_forgery: bool = Field(
        default=False,
        description="True when OCR-extracted text critically mismatches QR cryptographic payload (composite forgery)"
    )
    face_detected: bool = False
    face_count: int = 0
    face_boxes: List[BoundingBox] = Field(default_factory=list)
    qr_detected: bool = False
    qr_boxes: List[BoundingBox] = Field(default_factory=list)
    qr_payload: Optional[str] = None
    qr_payloads: List[str] = Field(default_factory=list)
    qr_decoded_data: Optional[Dict[str, Any]] = Field(default=None, description="Decoded statutory QR / barcode payload and cryptographic verification status")
    barcode_detected: bool = False
    barcode_boxes: List[BoundingBox] = Field(default_factory=list)
    barcode_payload: Optional[str] = None
    barcode_format: Optional[str] = None
    suspicious_regions: List[BoundingBox] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)


class AIAnalysisReport(BaseModel):
    """Stage-2 deeper AI-assisted forensic reasoning."""
    triggered: bool = False
    trigger_reason: Optional[str] = None
    findings: List[str] = Field(default_factory=list)
    confidence_impact: float = 0.0


class CrossDocumentMismatch(BaseModel):
    """Field inconsistency between two documents in the same session."""
    field_name: str
    doc1_type: str
    doc1_value: str
    doc2_type: str
    doc2_value: str
    severity: str = "HIGH"
    description: str


class CrossDocumentReport(BaseModel):
    """Cross-referencing results across multiple uploaded documents."""
    total_documents: int
    consistent: bool
    mismatches: List[CrossDocumentMismatch] = Field(default_factory=list)
    summary: str


class VerificationRequest(BaseModel):
    """Screening submission payload."""
    declared_document_type: Optional[DocumentType] = Field(
        default=None,
        description="Optional pre-declared document type hint"
    )
    checkpoint_id: str = Field(default="SSB-CHK-01", description="Border checkpoint / station code")
    officer_id: str = Field(default="SSB-OFFICER-01", description="Screening officer badge/ID")
    force_deep_ai: bool = Field(
        default=False,
        description="Explicitly force Tier-2 deep AI analysis even if fast checks pass"
    )


class ExplanationResult(BaseModel):
    """Transparent, explainable synthesis of all collected evidence."""
    primary_rationale: str = Field(..., description="High-level human-readable verdict explanation")
    positive_factors: List[str] = Field(default_factory=list, description="Passed checks reinforcing authenticity")
    negative_factors: List[str] = Field(default_factory=list, description="Failed/anomalous checks indicating risk")
    inconclusive_factors: List[str] = Field(default_factory=list, description="Degraded or unverifiable signals")


class RiskReport(BaseModel):
    """Calculated risk breakdown and overall decision support."""
    risk_level: RiskLevel = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Normalized risk score from 0 (clean) to 100 (maximum risk)")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Aggregate confidence in this assessment from 0% to 100%")
    overall_verdict: OverallVerdict = Field(..., description="CLEAR, SUSPICIOUS, or INCONCLUSIVE")


class VerificationTelemetry(BaseModel):
    """Performance telemetry and pipeline execution tracking."""
    quality_check_ms: float = 0.0
    forensic_scan_ms: float = 0.0
    extraction_ms: float = 0.0
    total_duration_ms: float = 0.0
    ai_escalated: bool = False
    ai_status_note: Optional[str] = None


class VerificationResponse(BaseModel):
    """Complete screening result returned by the real verification engine."""
    session_id: str = Field(..., description="Unique screening session identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filename: Optional[str] = None
    document_type: DocumentType = Field(..., description="Classified document category")
    overall_verdict: OverallVerdict = Field(..., description="CLEAR, SUSPICIOUS, or INCONCLUSIVE")
    officer_recommendation: OfficerAction = Field(
        ...,
        description="System decision-support recommendation: CLEAR, SECONDARY_INSPECTION, or ESCALATE"
    )
    status_label: str = Field(default="Low Risk", description="Low Risk, Review Required, High Risk, or Insufficient Quality")
    risk: RiskReport
    quality: DocumentQualityReport
    forensics: ForensicAnalysisReport
    extracted_fields: ExtractedFields
    ai_analysis: AIAnalysisReport
    explanation: ExplanationResult
    evidence: List[EvidenceItem]
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    preprocessing: Optional[PreprocessingReport] = None
    telemetry: VerificationTelemetry
    audit_hash: str = Field(..., description="Cryptographic SHA-256 seal of this screening session")
    preview_image_base64: Optional[str] = Field(default=None, description="Rendered visual data URL of the document page for UI viewport")


class MultiVerificationResponse(BaseModel):
    """Response when multiple documents are uploaded and cross-checked together."""
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_documents: int
    individual_results: List[VerificationResponse]
    cross_document_report: CrossDocumentReport
    overall_verdict: OverallVerdict
    audit_hash: str


class OfficerReviewRequest(BaseModel):
    """Human-in-the-loop review submission by authorized personnel."""
    session_id: str
    officer_id: str
    action: OfficerAction = Field(..., description="CLEAR, SECONDARY_INSPECTION, or ESCALATE")
    notes: str = Field(..., min_length=3, description="Operational justification and inspection notes")


class OfficerReviewResponse(BaseModel):
    """Outcome of recorded officer action."""
    session_id: str
    action: OfficerAction
    officer_id: str
    recorded_at: datetime
    audit_block_id: str
    message: str = "Officer operational decision recorded and sealed in tamper-evident ledger."


class BulkVerificationSummary(BaseModel):
    """Summary metrics of a bulk verification job."""
    total_processed: int
    low_risk_count: int
    review_required_count: int
    high_risk_count: int
    insufficient_quality_count: int
    average_risk_score: float
    items: List[VerificationResponse]
