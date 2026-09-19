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
# Observed canonical state — the exact value read from a frame, kept
# separate from UniversalProductionIntent (which carries only
# target_concept + direction, never a magnitude). Execution reproduces
# THIS value; the intent explains WHAT/WHY it changed.
# ---------------------------------------------------------------------------

@dataclass
class ObservedCanonicalState:
    """One exact UI reading tied to a single frame.

    This is a STRUCTURED reading (e.g. a knob's displayed number), distinct
    from VisualObservation's free-text description of the same frame. Two of
    these (before/after) are what CanonicalStateDiff compares.
    """
    target: str
    """Canonical parameter name, e.g. 'Env1.Release'."""

    value: str
    """Exact displayed value with unit, e.g. '220 ms'. A string because the
    display itself is a string (e.g. 'BPM' sync units, '%'); callers that
    need a float parse it themselves."""

    frame_id: str
    timestamp_sec: float
    frame_hash: str
    """sha256 of the frame this reading came from — same value as the
    matching VisualFrameArtifact.artifact_hash, duplicated here so this
    record is independently traceable without a join."""

    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalStateDiff:
    """Before/after comparison of two ObservedCanonicalState readings for the
    SAME target. This is what stage-B inference is allowed to reason from —
    never a single frame in isolation, never genre/title convention.
    """
    target: str
    before: ObservedCanonicalState
    after: ObservedCanonicalState
    changed: bool
    """True iff before.value != after.value (string comparison — the two
    readings are the same display format, so this is exact, not a fuzzy
    numeric compare)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "changed": self.changed,
        }


# ---------------------------------------------------------------------------
# UIStateSnapshot — the COMPLETE observable UI state of one frame, not one
# preselected control. ObservedCanonicalState (above) stays the primitive
# for "one exact reading of one named target"; UIStateSnapshot composes many
# of those (plus free-text controls whose meaning isn't fully resolved) into
# "everything legible in this frame". This is what makes the visual layer
# transcript-independent: it is built by SCANNING the frame, not by looking
# for the one control the transcript named.
# ---------------------------------------------------------------------------

@dataclass
class ControlState:
    """One observed UI control (knob/slider/dropdown/toggle/tab), scanned
    from a frame independent of what the transcript said. Unknown fields
    stay None/UNKNOWN rather than guessed -- a control whose value isn't
    legible in this frame is still worth recording as 'visible but unclear',
    distinct from 'not visible at all' (simply absent from the snapshot)."""
    control_id: str
    """Stable identifier for this control across frames, e.g. 'env1.release',
    'filter1.type' -- NOT tied to any one video's UI label; the same
    control_id should be reused whenever the same knob/dropdown is scanned
    in a later frame, so diffing (see UIStateSnapshot.diff) can match them."""

    control_type: str
    """'knob' | 'slider' | 'dropdown' | 'toggle' | 'tab' | 'badge_count' | 'other'"""

    label: Optional[str] = None
    """The UI's own displayed label, e.g. 'REL', 'Filter 1 Freq' -- kept
    separate from control_id since UI labels vary across contexts/zoom."""

    value: Optional[str] = None
    """Exact displayed value with unit, e.g. '36 ms', 'Band 24', '(5)'.
    None when visible but not legible -- never a guessed value."""

    unit: Optional[str] = None
    confidence: float = 0.5
    frame_id: Optional[str] = None
    frame_hash: Optional[str] = None
    timestamp_sec: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModRouteState:
    """One observed modulation-matrix row, scanned independent of any
    transcript mention of it -- the same completeness principle as
    ControlState, specialized for routing topology (source/destination
    pairs, not a single value)."""
    source: Optional[str] = None
    destination: Optional[str] = None
    amount: Optional[str] = None
    """Displayed amount with unit if legible (e.g. '+50%'); None if only
    the route's existence is legible, not its depth."""
    bipolar: Optional[bool] = None
    route_present: bool = True
    confidence: float = 0.5
    frame_id: Optional[str] = None
    frame_hash: Optional[str] = None
    timestamp_sec: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UIStateSnapshot:
    """Everything observable in ONE frame -- not the single control a
    transcript mention pointed at. Built by scanning the whole visible UI
    (plugin panels, tabs, knobs, mod matrix) once per frame; a frame this
    project never asked about a specific parameter for can still contribute
    a full snapshot."""
    frame_id: str
    frame_hash: str
    timestamp_sec: float
    plugin: Optional[str] = None
    plugin_version: Optional[str] = None
    visible_panel: Optional[str] = None
    """Which UI tab/panel was frontmost, e.g. 'OSC', 'MATRIX', 'ENV1'."""

    controls: List[ControlState] = field(default_factory=list)
    mod_routes: List[ModRouteState] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id, "frame_hash": self.frame_hash,
            "timestamp_sec": self.timestamp_sec, "plugin": self.plugin,
            "plugin_version": self.plugin_version, "visible_panel": self.visible_panel,
            "controls": [c.to_dict() for c in self.controls],
            "mod_routes": [r.to_dict() for r in self.mod_routes],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UIStateSnapshot":
        return cls(
            frame_id=d["frame_id"], frame_hash=d["frame_hash"],
            timestamp_sec=d["timestamp_sec"], plugin=d.get("plugin"),
            plugin_version=d.get("plugin_version"), visible_panel=d.get("visible_panel"),
            controls=[ControlState(**c) for c in d.get("controls", [])],
            mod_routes=[ModRouteState(**r) for r in d.get("mod_routes", [])],
        )


def diff_snapshots(before: UIStateSnapshot, after: UIStateSnapshot) -> Dict[str, Any]:
    """Deterministic, control-by-control diff between two snapshots.
    Pure function, no model call -- same determinism guarantee as
    diff_observed_states() in visual_reasoner.py. Matches controls by
    control_id; a control present in only one snapshot is reported as
    added/removed, not silently ignored. Mod routes are matched by
    (source, destination) pair."""
    before_by_id = {c.control_id: c for c in before.controls}
    after_by_id = {c.control_id: c for c in after.controls}

    changed_controls = []
    for cid, a in after_by_id.items():
        b = before_by_id.get(cid)
        if b is None:
            continue  # a control absent from `before` isn't a "change", see new_controls
        if b.value != a.value:
            changed_controls.append({"control_id": cid, "before": b.value, "after": a.value})
    new_controls = [cid for cid in after_by_id if cid not in before_by_id]
    removed_controls = [cid for cid in before_by_id if cid not in after_by_id]

    def _route_key(r: ModRouteState):
        return (r.source, r.destination)

    before_routes = {_route_key(r): r for r in before.mod_routes if r.route_present}
    after_routes = {_route_key(r): r for r in after.mod_routes if r.route_present}
    added_routes = [after_routes[k].to_dict() for k in after_routes if k not in before_routes]
    removed_routes = [before_routes[k].to_dict() for k in before_routes if k not in after_routes]

    return {
        "before_frame_id": before.frame_id, "after_frame_id": after.frame_id,
        "changed_controls": changed_controls,
        "new_controls": new_controls, "removed_controls": removed_controls,
        "added_routes": added_routes, "removed_routes": removed_routes,
    }


@dataclass
class ProductionEvent:
    """One grouped production action spanning several frames -- the object
    the Brain reasons over, replacing 'the single knob the transcript
    named'. Groups a UI diff (everything that actually changed, whether or
    not the narrator mentioned it) with whatever transcript evidence
    overlaps that time window."""
    event_id: str
    start_timestamp_sec: float
    end_timestamp_sec: float

    evidence_frame_ids: List[str] = field(default_factory=list)
    snapshot_diff: Optional[Dict[str, Any]] = None
    """diff_snapshots() output between the event's before/after frames."""

    transcript_excerpt: Optional[str] = None
    transcript_timestamp_sec: Optional[float] = None

    observed: List[str] = field(default_factory=list)
    """Plain-language observed facts, e.g. 'Env1.Release: 15ms -> 36ms'."""
    inferred: List[str] = field(default_factory=list)
    """Interpretations, always downstream of `observed`, never replacing it."""
    unknown: List[str] = field(default_factory=list)

    fusion_status: Optional[str] = None
    """'AGREEMENT' | 'VISUAL_ONLY' | 'TRANSCRIPT_ONLY' | 'CONFLICT' | 'UNKNOWN'
    -- set by evidence_fusion.fuse_transcript_and_visual(). None until fusion
    has actually run."""

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

    observed_canonical_states: List[ObservedCanonicalState] = field(default_factory=list)
    """Stage-A exact readings (target/value/frame_hash). Populated by
    VisualReasoner.observe_frames() when the query plan names a specific
    target to read, in addition to the free-text `observations`."""

    canonical_diffs: List[CanonicalStateDiff] = field(default_factory=list)
    """Before/after comparisons derived from observed_canonical_states.
    Stage-B inference (infer_from_diff) reasons from these, not from a
    single frame."""

    query_plan: Optional[Dict[str, Any]] = None
    """The VisualQueryPlan (as a dict) that drove targeted frame acquisition,
    when transcript-first planning was used. None for legacy fixed-cadence
    acquisition."""

    unknown: List[str] = field(default_factory=list)
    """Things Stage A (observe_frames) explicitly could not determine, e.g.
    'exact UI gesture used to change the value'. Kept separate from
    observations/interpretations — an honest gap, not a silent omission."""

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
            "observed_canonical_states": [s.to_dict() for s in self.observed_canonical_states],
            "canonical_diffs": [d.to_dict() for d in self.canonical_diffs],
            "query_plan": self.query_plan,
            "unknown": self.unknown,
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
        bundle.observed_canonical_states = [
            ObservedCanonicalState(**s) for s in data.get("observed_canonical_states", [])
        ]
        bundle.canonical_diffs = [
            CanonicalStateDiff(
                target=d["target"],
                before=ObservedCanonicalState(**d["before"]),
                after=ObservedCanonicalState(**d["after"]),
                changed=d["changed"],
            )
            for d in data.get("canonical_diffs", [])
        ]
        bundle.query_plan = data.get("query_plan")
        bundle.unknown = data.get("unknown", [])
        if data.get("model_metadata"):
            bundle.model_metadata = VisualModelMetadata(**data["model_metadata"])
        if data.get("transcript_sufficiency"):
            bundle.transcript_sufficiency = TranscriptSufficiency(**data["transcript_sufficiency"])
        return bundle
