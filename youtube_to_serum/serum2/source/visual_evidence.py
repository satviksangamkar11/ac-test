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

OBSERVED = "OBSERVED"
NOT_OBSERVED = "NOT_OBSERVED"
OCCLUDED = "OCCLUDED"
OUT_OF_VIEW = "OUT_OF_VIEW"
AMBIGUOUS = "AMBIGUOUS"
"""Observation-status vocabulary for ControlState/ModRouteState.status.
A control absent from a snapshot's `controls` list, or present with a
status other than OBSERVED, must never be read as 'removed' or 'reset' --
see diff_snapshots(), which keeps these strictly separate from a genuine
value change."""


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
    screen_region: Optional[str] = None
    """Where on the frame this was read, e.g. 'ENV1 panel, REL knob' or a
    'x0,y0,x1,y1' pixel box -- provenance for a human/audit re-check,
    not used by any diffing/fusion logic."""
    status: str = OBSERVED
    """One of OBSERVED/NOT_OBSERVED/OCCLUDED/OUT_OF_VIEW/AMBIGUOUS. Only
    OBSERVED entries carry a meaningful `value`; a scanner that couldn't
    read this control in this frame should still emit a ControlState with
    status=OCCLUDED (visible panel, blocked view) or OUT_OF_VIEW (wrong
    tab/panel entirely) rather than omitting it, wherever the scanner
    positively knows WHY it couldn't read it -- omitting the entry means
    'not scanned at all', which diff_snapshots treats identically to an
    explicit NOT_OBSERVED."""
    confidence: float = 0.5
    frame_id: Optional[str] = None
    frame_hash: Optional[str] = None
    timestamp_sec: Optional[float] = None
    detail: Optional[Dict[str, Any]] = None
    """Structured payload for state that is not one scalar: graph/curve
    points, region bounds (start/end/loop), per-row route data, topology or
    ordering. Observer-supplied and opaque to the Atlas; `value` still holds
    the raw displayed text. None = nothing structured was captured."""
    resolution: Optional[Dict[str, Any]] = None
    """Atlas normalization provenance (set by ingest_stage_a_observation):
    {status EXACT|ALIAS|UNRESOLVED|AMBIGUOUS, canonical_id, candidates,
    raw_control_id, raw label, atlas_version}. Identification only -- never
    touches value/status. None = not normalized."""

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
    status: str = OBSERVED
    confidence: float = 0.5
    frame_id: Optional[str] = None
    frame_hash: Optional[str] = None
    timestamp_sec: Optional[float] = None
    resolution: Optional[Dict[str, Any]] = None
    """Atlas provenance: {"source": {...}, "destination": {...}}, each with
    status EXACT|ALIAS|UNRESOLVED|AMBIGUOUS, canonical_id, candidates and the
    raw observed text. source/destination hold the canonical id only when
    resolved; otherwise the raw text stays. None = not normalized."""

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
    control_id.

    Invariants (do not weaken these without re-reading the architecture
    note this function was written against):
      - changed_controls   requires OBSERVED values at BOTH snapshots that
                            differ. Never inferred from one-sided evidence.
      - unchanged_controls requires OBSERVED values at BOTH snapshots that
                            are equal.
      - newly_observed_controls means 'visible in `after`, absent from
                            `before`'s scan' -- i.e. newly OBSERVED, NOT a
                            claim the control was newly created/added to
                            the production state. A control can easily
                            have existed all along outside a prior frame's
                            visible panel/tab.
      - not_observed_controls means insufficient visual evidence in at
                            least one snapshot (absent entirely, or status
                            OCCLUDED/OUT_OF_VIEW/NOT_OBSERVED/AMBIGUOUS).
                            'Couldn't see it' must never collapse into
                            'it changed' or 'it was removed'.
      - removed_controls   requires POSITIVE disappearance evidence -- a
                            scan that clearly shows the control/module/
                            route no longer exists in the UI, not merely
                            its absence from one snapshot's controls list.
                            Nothing in this data model currently supplies
                            that positive signal, so this stays honestly
                            empty; it exists so a future caller with real
                            disappearance evidence (e.g. a tab-structure
                            diff) has somewhere to put it, rather than
                            repurposing not_observed_controls for it.
    Mod routes get the same not-observed-vs-removed split, matched by
    (source, destination) pair."""

    def _observed(c: ControlState) -> bool:
        return c.status == OBSERVED

    before_by_id = {c.control_id: c for c in before.controls}
    after_by_id = {c.control_id: c for c in after.controls}

    changed_controls = []
    unchanged_controls = []
    not_observed_controls = []
    newly_observed_controls = []

    all_ids = set(before_by_id) | set(after_by_id)
    for cid in sorted(all_ids):
        b, a = before_by_id.get(cid), after_by_id.get(cid)
        b_ok, a_ok = b is not None and _observed(b), a is not None and _observed(a)
        if b_ok and a_ok:
            if b.value != a.value:
                changed_controls.append({"control_id": cid, "before": b.value, "after": a.value})
            else:
                unchanged_controls.append(cid)
        elif a_ok and b is None:
            newly_observed_controls.append(cid)  # OBSERVED in `after`, wasn't in `before` at all
        else:
            not_observed_controls.append(cid)  # occluded/out-of-view/absent in either frame

    removed_controls: List[str] = []

    def _route_key(r: ModRouteState):
        return (r.source, r.destination)

    before_routes = {_route_key(r): r for r in before.mod_routes if r.route_present and r.status == OBSERVED}
    after_routes = {_route_key(r): r for r in after.mod_routes if r.route_present and r.status == OBSERVED}
    # A route table that was EXPLICITLY not observed on one side (control
    # 'matrix.routes' present with a non-OBSERVED status, e.g. the MATRIX tab
    # wasn't frontmost) gives no basis to call a route added/removed -- same
    # newly-observed != newly-created rule as for controls. Snapshots that
    # carry no such control keep the original behavior.
    def _matrix_unobserved(snap: UIStateSnapshot) -> bool:
        return any(c.control_id == "matrix.routes" and c.status != OBSERVED for c in snap.controls)

    if _matrix_unobserved(before):
        added_routes = []
        newly_observed_routes = [after_routes[k].to_dict() for k in after_routes if k not in before_routes]
    else:
        added_routes = [after_routes[k].to_dict() for k in after_routes if k not in before_routes]
        newly_observed_routes = []
    if _matrix_unobserved(after):
        removed_routes = []
        not_observed_routes = [before_routes[k].to_dict() for k in before_routes if k not in after_routes]
    else:
        removed_routes = [before_routes[k].to_dict() for k in before_routes if k not in after_routes]
        not_observed_routes = []

    return {
        "before_frame_id": before.frame_id, "after_frame_id": after.frame_id,
        "changed_controls": changed_controls,
        "unchanged_controls": unchanged_controls,
        "newly_observed_controls": newly_observed_controls,
        "not_observed_controls": not_observed_controls,
        "removed_controls": removed_controls,
        "added_routes": added_routes, "removed_routes": removed_routes,
        "newly_observed_routes": newly_observed_routes, "not_observed_routes": not_observed_routes,
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
    acquisition. NOTE: this plan governs WHICH TIMESTAMPS get frames, never
    which controls get scanned once a frame exists -- see ui_state_snapshots."""

    stage_a_provenance: Optional[Dict[str, Any]] = None
    """Machine-checkable proof of HOW ui_state_snapshots was produced, e.g.
    {"observer": "claude_code", "observation_mode": "direct_visual_inspection",
    "model_api_used": false}. Populated by
    visual_reasoner.ingest_stage_a_observation() from the observation dict's
    own top-level provenance fields -- this is what makes "no API was used"
    a checkable fact on the persisted bundle/episode, not just a claim in a
    session transcript."""

    ui_state_snapshots: List["UIStateSnapshot"] = field(default_factory=list)
    """One full panel-by-panel census per frame, populated by
    VisualReasoner.observe_frames(). Independent of any transcript-named
    target -- observe_frames() enumerates every legible control/route in
    every visible panel, regardless of what (if anything) the transcript
    mentioned. This is the primary Stage-A output; observed_canonical_states
    (below) is a narrower, target-scoped convenience view derived from the
    same frames for Stage B's diff_observed_states()/infer_from_diffs()."""

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
            "ui_state_snapshots": [s.to_dict() for s in self.ui_state_snapshots],
            "stage_a_provenance": self.stage_a_provenance,
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
        bundle.ui_state_snapshots = [
            UIStateSnapshot.from_dict(s) for s in data.get("ui_state_snapshots", [])
        ]
        bundle.stage_a_provenance = data.get("stage_a_provenance")
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
