import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class VerificationSessionModel(Base):
    """Stores full verification screening run and officer lifecycle state."""
    __tablename__ = "verification_sessions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    document_type = Column(String(32), nullable=False, index=True)
    checkpoint_id = Column(String(64), default="SSB-CHK-01", index=True)
    officer_id = Column(String(64), default="SSB-OFFICER-DEFAULT", index=True)
    
    overall_verdict = Column(String(32), nullable=False, index=True)  # CLEAR, SUSPICIOUS, INCONCLUSIVE
    officer_recommendation = Column(String(32), nullable=False)       # CLEAR, SECONDARY_INSPECTION, ESCALATE
    
    risk_level = Column(String(32), nullable=False, index=True)        # LOW, MEDIUM, HIGH, CRITICAL
    risk_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    audit_hash = Column(String(64), nullable=False, index=True)
    
    # Human-in-the-loop review state
    officer_action = Column(String(32), nullable=True)                 # CLEAR, SECONDARY_INSPECTION, ESCALATE
    officer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(64), nullable=True)
    
    # Rich structured payloads
    extracted_data = Column(JSON, default=dict)
    explanation = Column(JSON, default=dict)
    telemetry = Column(JSON, default=dict)

    # Relationships
    evidence_records = relationship("EvidenceRecordModel", back_populates="session", cascade="all, delete-orphan")


class EvidenceRecordModel(Base):
    """Individual atomic, tamper-evident evidence items linked to a session."""
    __tablename__ = "evidence_records"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(64), ForeignKey("verification_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    check_id = Column(String(64), nullable=False, index=True)
    check_name = Column(String(128), nullable=False)
    source_type = Column(String(32), nullable=False, index=True)  # DOCUMENT, OCR, FORENSIC, etc.
    status = Column(String(32), nullable=False, index=True)       # PASS, FAIL, WARNING, INCONCLUSIVE
    confidence = Column(Float, nullable=False)
    summary = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    hash_digest = Column(String(64), nullable=False)
    
    raw_data = Column(JSON, default=dict)
    provenance = Column(JSON, default=dict)

    session = relationship("VerificationSessionModel", back_populates="evidence_records")


class AuditBlockModel(Base):
    """Tamper-evident SHA-256 cryptographic chain of screening events."""
    __tablename__ = "audit_blocks"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    block_index = Column(Integer, unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    event_type = Column(String(32), nullable=False, index=True)  # SCREENING, OFFICER_REVIEW
    session_id = Column(String(64), nullable=False, index=True)
    officer_id = Column(String(64), nullable=False)
    
    payload_digest = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)
    block_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    metadata_json = Column(JSON, default=dict)


class BatchJobModel(Base):
    """Asynchronous bulk screening job tracked by Celery."""
    __tablename__ = "batch_jobs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="PENDING", index=True)  # PENDING, PROCESSING, COMPLETED, FAILED
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    results = Column(JSON, default=list)


# Composite indexes for fast telemetry queries
Index("idx_verif_date_verdict", VerificationSessionModel.created_at, VerificationSessionModel.overall_verdict)
Index("idx_verif_type_risk", VerificationSessionModel.document_type, VerificationSessionModel.risk_level)
