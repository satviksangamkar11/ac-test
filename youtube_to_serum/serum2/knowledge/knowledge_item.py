"""Canonical KnowledgeItem schema for Step 5 knowledge layer.

A KnowledgeItem represents a SOURCE-DERIVED OBSERVATION.

It is NOT:
  - CapabilityContract
  - EvidenceRecord
  - causal proof
  - execution permission
  - production authority

A KnowledgeItem may inform future reasoning but cannot authorize execution.

Schema Properties:
  - Source provenance is immutable
  - Original source text is immutable
  - Normalized interpretation is separately tracked
  - Ambiguity is preserved rather than invented
  - Epistemic status is explicit (SOURCE_REPORTED, OBSERVED, etc.)
  - Semantic bindings are independent dimensions (target, role, technique, etc.)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import hashlib
from datetime import datetime


class KnowledgeType(Enum):
    """Types of knowledge a source can provide."""
    CONCEPT = "CONCEPT"  # What something is
    PROCEDURE = "PROCEDURE"  # Steps to perform
    PRINCIPLE = "PRINCIPLE"  # Generalized relationship
    OBSERVATION = "OBSERVATION"  # Source-reported observation
    RECOMMENDATION = "RECOMMENDATION"  # Suggested practice or heuristic
    CONDITION = "CONDITION"  # Context in which something applies
    EXAMPLE = "EXAMPLE"  # Concrete illustrative example
    CONTEXT = "CONTEXT"  # Genre, style, role, instrument context
    LIMITATION = "LIMITATION"  # Restriction or qualifier on scope


class EpistemicStatus(Enum):
    """Epistemic status of a knowledge item."""
    SOURCE_REPORTED = "SOURCE_REPORTED"  # Source explicitly stated this
    SOURCE_RECOMMENDED = "SOURCE_RECOMMENDED"  # Source recommends this
    SOURCE_OBSERVED = "SOURCE_OBSERVED"  # Source claims to have observed this
    SYSTEM_INTERPRETATION = "SYSTEM_INTERPRETATION"  # System derived this from source
    EXPERIMENTALLY_VERIFIED = "EXPERIMENTALLY_VERIFIED"  # Evidence qualifies this capability
    UNKNOWN = "UNKNOWN"  # Unclear or ambiguous


@dataclass
class SemanticBinding:
    """A semantic dimension binding for a knowledge item."""
    dimension: str  # e.g., "target", "role", "technique", "intent", "context"
    value: str  # e.g., "Env1.Release", "bass", "envelope shaping", "longer sustain", "pluck"
    confidence: float = 0.8  # 0.0-1.0
    ambiguity: Optional[str] = None  # If ambiguous, describe alternatives


@dataclass
class SourceReference:
    """Reference to source material (immutable)."""
    source_id: str  # e.g., "yt_f507169bd7cb"
    source_type: str  # e.g., "YOUTUBE_VIDEO", "MANUAL", "USER_EXPLANATION"
    source_url: Optional[str] = None  # e.g., "https://www.youtube.com/watch?v=..."
    source_title: Optional[str] = None  # e.g., "Serum 2 Complete Guide"
    segment_ids: List[str] = field(default_factory=list)  # e.g., ["seg_0000", "seg_0001"]
    start_time_sec: Optional[float] = None  # For video/audio sources
    end_time_sec: Optional[float] = None  # For video/audio sources


@dataclass
class ExtractionMetadata:
    """Metadata about how this item was extracted."""
    extraction_timestamp: str  # ISO 8601 timestamp
    extraction_method: str  # e.g., "semantic_extraction_v1", "manual", "import_from_hypothesis"
    extraction_confidence: float  # 0.0-1.0, extraction/interpretation confidence
    raw_extraction_status: str  # e.g., "EXTRACTED", "SOURCE_ONLY", "IMPORTED"
    original_segments_count: Optional[int] = None  # How many source segments combined


@dataclass
class KnowledgeItem:
    """
    Canonical representation of a knowledge item.

    Preserves provenance, original source text, and semantic bindings
    without fabricating connections.
    """

    # ===== IDENTITY =====
    knowledge_item_id: str
    """Deterministic stable ID derived from source reference and proposition."""

    # ===== SOURCE (IMMUTABLE) =====
    source_reference: SourceReference
    """Where this knowledge came from."""

    original_proposition: str
    """Original source text EXACTLY AS ACQUIRED. Never modified."""

    # ===== SEMANTICS =====
    knowledge_type: KnowledgeType
    """Type of knowledge: CONCEPT, PROCEDURE, PRINCIPLE, etc."""

    epistemic_status: EpistemicStatus
    """Clarity about what the source actually claimed."""

    normalized_proposition: Optional[str] = None
    """System-derived interpretation (distinct from original). Can be None."""

    semantic_bindings: List[SemanticBinding] = field(default_factory=list)
    """Independent semantic dimensions: target, role, technique, intent, etc."""

    # ===== UNCERTAINTY =====
    extraction_confidence: float = 0.7
    """Confidence in extraction/classification (0.0-1.0). Separate from epistemic status."""

    ambiguity: Optional[str] = None
    """If ambiguous, describe alternatives explicitly. None means unambiguous."""

    # ===== CONDITIONS & CONSTRAINTS =====
    conditions: List[str] = field(default_factory=list)
    """Conditions under which this knowledge applies."""

    limitations: List[str] = field(default_factory=list)
    """Explicit restrictions or qualifiers on scope."""

    # ===== METADATA =====
    extraction_metadata: Optional[ExtractionMetadata] = None
    """How this item was extracted."""

    notes: Optional[str] = None
    """Additional context or system notes (not source material)."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "knowledge_item_id": self.knowledge_item_id,
            "source_reference": {
                "source_id": self.source_reference.source_id,
                "source_type": self.source_reference.source_type,
                "source_url": self.source_reference.source_url,
                "source_title": self.source_reference.source_title,
                "segment_ids": self.source_reference.segment_ids,
                "start_time_sec": self.source_reference.start_time_sec,
                "end_time_sec": self.source_reference.end_time_sec,
            },
            "original_proposition": self.original_proposition,
            "knowledge_type": self.knowledge_type.value,
            "epistemic_status": self.epistemic_status.value,
            "normalized_proposition": self.normalized_proposition,
            "semantic_bindings": [
                {
                    "dimension": b.dimension,
                    "value": b.value,
                    "confidence": b.confidence,
                    "ambiguity": b.ambiguity,
                }
                for b in self.semantic_bindings
            ],
            "extraction_confidence": self.extraction_confidence,
            "ambiguity": self.ambiguity,
            "conditions": self.conditions,
            "limitations": self.limitations,
            "extraction_metadata": {
                "extraction_timestamp": self.extraction_metadata.extraction_timestamp,
                "extraction_method": self.extraction_metadata.extraction_method,
                "extraction_confidence": self.extraction_metadata.extraction_confidence,
                "raw_extraction_status": self.extraction_metadata.raw_extraction_status,
                "original_segments_count": self.extraction_metadata.original_segments_count,
            } if self.extraction_metadata else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeItem":
        """Deserialize from JSON-compatible dict."""
        src_ref_data = data.get("source_reference", {})
        source_reference = SourceReference(
            source_id=src_ref_data.get("source_id"),
            source_type=src_ref_data.get("source_type"),
            source_url=src_ref_data.get("source_url"),
            source_title=src_ref_data.get("source_title"),
            segment_ids=src_ref_data.get("segment_ids", []),
            start_time_sec=src_ref_data.get("start_time_sec"),
            end_time_sec=src_ref_data.get("end_time_sec"),
        )

        semantic_bindings = [
            SemanticBinding(
                dimension=b.get("dimension"),
                value=b.get("value"),
                confidence=b.get("confidence", 0.8),
                ambiguity=b.get("ambiguity"),
            )
            for b in data.get("semantic_bindings", [])
        ]

        extraction_metadata = None
        if data.get("extraction_metadata"):
            em_data = data["extraction_metadata"]
            extraction_metadata = ExtractionMetadata(
                extraction_timestamp=em_data.get("extraction_timestamp"),
                extraction_method=em_data.get("extraction_method"),
                extraction_confidence=em_data.get("extraction_confidence", 0.7),
                raw_extraction_status=em_data.get("raw_extraction_status"),
                original_segments_count=em_data.get("original_segments_count"),
            )

        return cls(
            knowledge_item_id=data.get("knowledge_item_id"),
            source_reference=source_reference,
            original_proposition=data.get("original_proposition"),
            knowledge_type=KnowledgeType(data.get("knowledge_type")),
            epistemic_status=EpistemicStatus(data.get("epistemic_status")),
            normalized_proposition=data.get("normalized_proposition"),
            semantic_bindings=semantic_bindings,
            extraction_confidence=data.get("extraction_confidence", 0.7),
            ambiguity=data.get("ambiguity"),
            conditions=data.get("conditions", []),
            limitations=data.get("limitations", []),
            extraction_metadata=extraction_metadata,
            notes=data.get("notes"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "KnowledgeItem":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate this KnowledgeItem.

        Returns: (is_valid, list_of_errors)
        """
        errors = []

        # Check identity
        if not self.knowledge_item_id:
            errors.append("Missing knowledge_item_id")

        # Check source
        if not self.source_reference.source_id:
            errors.append("Missing source_reference.source_id")
        if not self.source_reference.source_type:
            errors.append("Missing source_reference.source_type")

        # Check original proposition
        if not self.original_proposition:
            errors.append("Missing original_proposition")
        if self.original_proposition and len(self.original_proposition.strip()) == 0:
            errors.append("original_proposition is empty string")

        # Check knowledge type
        if not isinstance(self.knowledge_type, KnowledgeType):
            errors.append(f"Invalid knowledge_type: {self.knowledge_type}")

        # Check epistemic status
        if not isinstance(self.epistemic_status, EpistemicStatus):
            errors.append(f"Invalid epistemic_status: {self.epistemic_status}")

        # Check confidence bounds
        if not (0.0 <= self.extraction_confidence <= 1.0):
            errors.append(f"extraction_confidence out of bounds: {self.extraction_confidence}")

        # Check semantic bindings
        for b in self.semantic_bindings:
            if not b.dimension:
                errors.append(f"SemanticBinding missing dimension")
            if not b.value:
                errors.append(f"SemanticBinding missing value for dimension {b.dimension}")
            if not (0.0 <= b.confidence <= 1.0):
                errors.append(f"SemanticBinding confidence out of bounds: {b.confidence}")

        # Check that it's not authority
        if hasattr(self, "admission_status") or hasattr(self, "capability_status"):
            errors.append("KnowledgeItem contains authority fields (admission_status/capability_status)")

        return (len(errors) == 0, errors)

    @staticmethod
    def compute_stable_id(source_id: str, segment_ids: List[str], proposition_hash: str) -> str:
        """
        Compute deterministic stable ID for a KnowledgeItem.

        Combines source, source segments, and proposition to create a stable hash.
        """
        combined = f"{source_id}:{'|'.join(segment_ids)}:{proposition_hash}"
        stable_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return f"ki_{stable_hash}"

    @staticmethod
    def compute_proposition_hash(proposition: str) -> str:
        """Hash a proposition for stable ID computation."""
        return hashlib.sha256(proposition.encode()).hexdigest()[:16]
