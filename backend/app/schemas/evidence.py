import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.enums import EvidenceStatus, SourceType


class Provenance(BaseModel):
    """Execution provenance and audit trail for an evidence check."""
    engine_id: str = Field(..., description="Engine or subsystem identifier")
    algorithm: str = Field(..., description="Algorithm or rule name applied")
    version: str = Field(default="1.0.0", description="Component software version")
    duration_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of evidence creation"
    )
    status_note: Optional[str] = Field(default=None, description="Diagnostic note e.g. AI_UNAVAILABLE")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional technical telemetry")


class EvidenceItem(BaseModel):
    """Atomic, tamper-evident evidence item produced by a verification check."""
    check_id: str = Field(..., description="Unique check identifier, e.g. MRZ_CHECKSUM_PASS")
    check_name: str = Field(..., description="Human-readable check label")
    source_type: SourceType = Field(..., description="Evidence generation channel")
    status: EvidenceStatus = Field(..., description="PASS, FAIL, WARNING, or INCONCLUSIVE")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.00 and 1.00"
    )
    summary: str = Field(..., description="Brief outcome explanation")
    details: Optional[str] = Field(default=None, description="Detailed forensic / inspection findings")
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value pairs or metrics"
    )
    provenance: Provenance = Field(..., description="Telemetry and execution tracking")
    hash_digest: Optional[str] = Field(
        default=None,
        description="SHA-256 cryptographic digest of the evidence payload for tamper detection"
    )

    def calculate_digest(self) -> str:
        """Compute tamper-evident SHA-256 digest of this item's core fields."""
        payload = {
            "check_id": self.check_id,
            "source_type": self.source_type.value,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "summary": self.summary,
            "engine": self.provenance.engine_id,
            "algorithm": self.provenance.algorithm,
            "timestamp": self.provenance.timestamp.isoformat(),
        }
        dumped = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def seal(self) -> "EvidenceItem":
        """Compute and set the hash_digest if not already set."""
        if not self.hash_digest:
            self.hash_digest = self.calculate_digest()
        return self


class EvidenceSet(BaseModel):
    """Collection of atomic evidence items with categorization helpers."""
    items: List[EvidenceItem] = Field(default_factory=list)

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item.seal())

    def by_source(self, source: SourceType) -> List[EvidenceItem]:
        return [i for i in self.items if i.source_type == source]

    def by_status(self, status: EvidenceStatus) -> List[EvidenceItem]:
        return [i for i in self.items if i.status == status]

    def has_failures(self) -> bool:
        return any(i.status == EvidenceStatus.FAIL for i in self.items)

    def has_warnings(self) -> bool:
        return any(i.status == EvidenceStatus.WARNING for i in self.items)

    def has_inconclusive(self) -> bool:
        return any(i.status == EvidenceStatus.INCONCLUSIVE for i in self.items)
