"""Visual evidence schema for the VLP-1 visual learning path.

Keeps OBSERVED separate from INFERRED — these are never collapsed into one
statement. Observed facts are grounded in what is literally visible in a frame.
Inferred meanings are interpretations that require production knowledge.

All artifacts are identified by hash (sha256) so claims remain traceable to the
exact source frame regardless of path changes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Frame artifact — identifies one extracted video frame by its hash
# ---------------------------------------------------------------------------

@dataclass
class VisualFrameArtifact:
    """One extracted video frame with immutable provenance."""
    frame_id: str
    """Deterministic: f'frame_{source_id}_{timestamp_ms:08d}'"""

    source_url: str
    source_id: str
    video_id: str

    timestamp_sec: float
    """Exact timestamp in seconds at which the frame was extracted."""

    artifact_path: str
    """Path to the saved frame image file (relative to repo root)."""

    artifact_hash: str
    """sha256 hex digest of the raw frame bytes."""

    width: Optional[int] = None
    """Actual frame pixel width, ffprobe-verified. None for legacy/storyboard
    frames acquired before this field existed."""

    height: Optional[int] = None
    """Actual frame pixel height, ffprobe-verified."""

    source_video_sha256: Optional[str] = None
    """sha256 of the full downloaded source video this frame was extracted
    from (real-video path only; None for storyboard-derived frames)."""

    acquired_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Observed — what is literally visible in a frame, no interpretation
# ---------------------------------------------------------------------------

@dataclass
class VisualObservation:
    """A single factual observation from a video frame.

    Observation describes only what is VISIBLE. No inference about intent,
    technique, or production meaning is made here.

    Examples of valid observations:
        "The Serum 2 filter cutoff knob is positioned at approximately 25%
         of its full clockwise range."
        "The Osc A waveform selector shows a wavetable named 'Basic Shapes'."
        "The LFO 1 rate display reads approximately 0.5 Hz."

    Examples of INVALID observations (these belong in VisualInterpretation):
        "The producer is darkening the bass." (inference)
        "This creates a filtered sound." (inference)
    """
    frame_id: str
    """Which frame this observation came from."""

    timestamp_sec: float
    """Timestamp of the source frame."""

    observation_text: str
    """Verbatim factual description of what is visible. No interpretation."""

    observable_type: str
    """'ui_control' | 'parameter_value' | 'waveform_display' |
    'automation_lane' | 'preset_name' | 'plugin_view' | 'general'"""

    ui_element: Optional[str] = None
    """Identified UI element if any, e.g. 'filter_cutoff_knob',
    'env1_release_slider', 'osc_a_wavetable_selector'. None if unclear."""

    estimated_value: Optional[str] = None
    """Visual estimate of a parameter value, e.g. '25%', '0.5 Hz', 'basic shapes'.
    Always a string with unit context. Not a precise measurement."""

    confidence: float = 0.5
    """Confidence that this observation is correct (0.0-1.0)."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Inferred — production meaning derived from observations
# ---------------------------------------------------------------------------

@dataclass
class VisualInterpretation:
    """A production-technique interpretation inferred from visual observations.

    Interpretation is always one step removed from the frame evidence.
    It must cite the supporting observations that justify it.

    Examples of valid interpretations:
        "The producer reduced filter cutoff to darken the bass sound."
        "The low LFO rate suggests a slow filter sweep modulation."

    The interpretation maps to a concept + direction so it can be converted
    to a UniversalProductionIntent.
    """
    interpretation_text: str
    """The inferred production meaning. References supporting observations."""

    production_concept: str
    """Universal music production concept, e.g. 'filter-cutoff', 'lfo-rate',
    'envelope-release'. Matches concepts in producer_brain._INTENT_TO_CONCEPT."""

    semantic_direction: str
    """Direction: 'increase' | 'decrease' | 'higher' | 'lower' |
    'longer' | 'shorter' | 'brighter' | 'darker'"""

    supporting_frame_ids: List[str] = field(default_factory=list)
    """frame_ids of observations that support this interpretation."""

    confidence: float = 0.5
    """Confidence in this interpretation (0.0-1.0)."""

    production_action: Optional[str] = None
    """Specific actionable description, e.g.
    'Reduce Serum 2 filter cutoff to approximately 30% of full range.'"""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Model metadata — honest provenance for visual reasoning
# ---------------------------------------------------------------------------

@dataclass
class VisualModelMetadata:
    """Provenance record for the visual reasoning model call.

    provider_attestation is null unless an actual cryptographic attestation
    exists. Never fabricated.
    """
    requested_model: str
    response_model: Optional[str] = None
    """Model actually used, as reported in the API response. May differ from
    requested_model if the provider substituted a model."""

    request_id: Optional[str] = None
    """API request ID from the response headers, if available."""

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    provider: str = "anthropic"
    provider_attestation: None = None
    """Always null. No cryptographic model attestation exists in this system."""

    called_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provider_attestation"] = None  # always null, never fabricated
        return d


# ---------------------------------------------------------------------------
# Transcript sufficiency
# ---------------------------------------------------------------------------

@dataclass
class TranscriptSufficiency:
    """Result of checking whether the transcript alone is sufficient for a
    given production action.

    SUFFICIENT            transcript contains the complete production procedure
    INSUFFICIENT_OPERATIONAL  transcript exists but lacks actionable detail
    UNAVAILABLE           no transcript at all
    """
    status: str  # "SUFFICIENT" | "INSUFFICIENT_OPERATIONAL" | "UNAVAILABLE"
    reason: str
    evidence_item_count: int = 0
    """Number of knowledge items from the canonical store for this source."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Bundle — the complete visual evidence package for one source
# ---------------------------------------------------------------------------

@dataclass
class VisualEvidenceBundle:
    """Complete visual evidence for one source video.

    Built incrementally:
        1. frames populated by acquire_visual_evidence()
        2. observations and interpretations populated by VisualReasoner
        3. model_metadata populated after the API call completes

    The bundle is self-contained: it can be persisted and later used to
    reconstruct production intent without re-running vision.
    """
    source_url: str
    source_id: str
    video_id: str

    acquired_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    frames: List[VisualFrameArtifact] = field(default_factory=list)
    observations: List[VisualObservation] = field(default_factory=list)
    interpretations: List[VisualInterpretation] = field(default_factory=list)

    model_metadata: Optional[VisualModelMetadata] = None
    """Populated after VisualReasoner completes. None if reasoning not yet run."""

    transcript_sufficiency: Optional[TranscriptSufficiency] = None
    """Result of the transcript sufficiency check that triggered this visual path."""

    acquisition_error: Optional[str] = None
    """Non-None if frame acquisition failed."""

    reasoning_error: Optional[str] = None
    """Non-None if visual reasoning failed."""

    source_video_info: Optional[Dict[str, Any]] = None
    """Provenance for the acquisition source when real video was downloaded:
    format_id, requested_resolution, selected_resolution, width, height,
    fps, codec, container, duration_sec, source_video_sha256, fallback_reason,
    yt_dlp_version. None when frames came from the storyboard fallback."""

    def best_interpretation(self) -> Optional[VisualInterpretation]:
        """Return the highest-confidence interpretation, if any."""
        if not self.interpretations:
            return None
        return max(self.interpretations, key=lambda i: i.confidence)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "source_url": self.source_url,
            "source_id": self.source_id,
            "video_id": self.video_id,
            "acquired_at": self.acquired_at,
            "frames": [f.to_dict() for f in self.frames],
            "observations": [o.to_dict() for o in self.observations],
            "interpretations": [i.to_dict() for i in self.interpretations],
            "model_metadata": self.model_metadata.to_dict() if self.model_metadata else None,
            "transcript_sufficiency": self.transcript_sufficiency.to_dict() if self.transcript_sufficiency else None,
            "acquisition_error": self.acquisition_error,
            "reasoning_error": self.reasoning_error,
        }
        return d

    @classmethod
    def load(cls, path: str) -> "VisualEvidenceBundle":
        """Deserialize from a persisted JSON file."""
        import json
        from pathlib import Path
        data = json.loads(Path(path).read_text())
        bundle = cls(
            source_url=data["source_url"],
            source_id=data["source_id"],
            video_id=data["video_id"],
            acquired_at=data.get("acquired_at", ""),
            acquisition_error=data.get("acquisition_error"),
            reasoning_error=data.get("reasoning_error"),
        )
        bundle.frames = [VisualFrameArtifact(**f) for f in data.get("frames", [])]
        bundle.observations = [VisualObservation(**o) for o in data.get("observations", [])]
        bundle.interpretations = [VisualInterpretation(**i) for i in data.get("interpretations", [])]
        if data.get("model_metadata"):
            bundle.model_metadata = VisualModelMetadata(**data["model_metadata"])
        if data.get("transcript_sufficiency"):
            bundle.transcript_sufficiency = TranscriptSufficiency(**data["transcript_sufficiency"])
        return bundle
