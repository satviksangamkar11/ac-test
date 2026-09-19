"""Canonical Production Experience Record — Producer Brain V2, Phase P0.

Composes with (does not replace) the existing frozen canonical episode,
step_6_10_episode_generation.UniversalExecutedEpisode. That schema already
covers advisory-reasoning provenance, DawDreamer-contract admission
bookkeeping, and outcome attribution, and producer_brain.py states its own
invariant that frozen Step 6 files are never edited. It has no slots for:
source/transcript reference, ProductionContext, MCP-path admission (the
actual path this server uses — the frozen schema is DawDreamer-contract-
centric), serum-mcp calls, Serum UI actions, Ableton MCP calls+readback,
render artifacts, acoustic measurements, user feedback, or reflection.

ProductionExperienceRecord adds exactly those fields and links to
UniversalExecutedEpisode by ID when the DawDreamer path produces one —
composition, not a second competing episode schema.

Evidence staging is real, not decorative: SPECIFIED (a plan was produced)
!= EXECUTED (a real tool call happened) != READ_BACK (the tool's result was
captured) != VERIFIED (the readback was checked against what was specified
and matched). The record is built incrementally, one stage at a time, as
production_pipeline.advance_production() actually progresses — never
reconstructed once from already-collected raw evidence at the end, which
could not truthfully distinguish these stages from each other.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

_EXPERIENCES_DIR = Path(__file__).parent.parent / "data" / "experiences"


class EvidenceStage(Enum):
    SPECIFIED = "specified"    # a plan/action was produced; nothing done yet
    EXECUTED = "executed"      # a real tool call was made
    READ_BACK = "read_back"    # the tool's result/state was captured
    VERIFIED = "verified"      # the readback was checked against intent and matched


@dataclass
class SerumMcpCallRecord:
    """One serum-mcp MCP tool call: what was specified vs what actually happened."""
    tool: str
    args_specified: Dict[str, Any] = field(default_factory=dict)
    stage: str = EvidenceStage.SPECIFIED.value
    result: Optional[Dict[str, Any]] = None
    preset_path: Optional[str] = None
    preset_sha256: Optional[str] = None
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SerumUiActionRecord:
    """One Serum UI interaction: load / configure / verify."""
    action: str  # "load_and_configure" | "verify"
    stage: str = EvidenceStage.SPECIFIED.value
    evidence: Optional[Dict[str, Any]] = None
    controls_matched: Optional[bool] = None
    mutation_applied: Optional[str] = None
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AbletonMcpCallRecord:
    """One Ableton MCP call with its readback evidence."""
    tool: str
    args_specified: Dict[str, Any] = field(default_factory=dict)
    stage: str = EvidenceStage.SPECIFIED.value
    result: Optional[Dict[str, Any]] = None
    readback: Optional[Dict[str, Any]] = None
    readback_verified: Optional[bool] = None
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RenderArtifactRecord:
    render_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_sec: Optional[float] = None
    sha256: Optional[str] = None
    stage: str = EvidenceStage.SPECIFIED.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AcousticMeasurementRecord:
    rms_db: Optional[float] = None
    peak_db: Optional[float] = None
    spectral_centroid_hz: Optional[float] = None
    measurement_definition_id: Optional[str] = None
    kernel_version: Optional[str] = None
    channel_policy: Optional[str] = None
    stage: str = EvidenceStage.SPECIFIED.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductionExperienceRecord:
    """The single canonical production experience record (Brain V2, P0)."""

    experience_id: str
    run_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ---- source / transcript ----
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    transcript_snippet: Optional[str] = None
    transcript_source_ref: Optional[str] = None
    """Pointer to the canonical KnowledgeStore file written by
    ingestion.ingest_canonical() — the full transcript is never duplicated
    here, only referenced."""

    # ---- production context (advisory) ----
    production_context: Optional[Dict[str, Any]] = None

    # ---- producer request snapshot ----
    producer_request: Optional[Dict[str, Any]] = None
    """{'user_intent', 'mode', 'musical_context', 'advisory_context'} —
    exactly what was sent to execute_producer_request()."""

    # ---- canonical brain episode (linked, not duplicated) ----
    canonical_episode_id: Optional[str] = None
    canonical_episode_path: Optional[str] = None

    # ---- brain decision (MCP-path aware; frozen schema has no slot for this) ----
    brain_decision: Optional[Dict[str, Any]] = None
    """resolved_concept, semantic_direction, semantic_target, execution_route,
    admitted, admission_reason, resolution_status, intent_class, mcp_plan."""

    # ---- retrieved knowledge / episodes ----
    retrieved_knowledge_ids: List[str] = field(default_factory=list)
    retrieved_episode_ids: List[str] = field(default_factory=list)

    # ---- external action evidence (incrementally populated) ----
    serum_mcp_call: Optional[Dict[str, Any]] = None
    serum_ui_actions: List[Dict[str, Any]] = field(default_factory=list)
    ableton_calls: List[Dict[str, Any]] = field(default_factory=list)
    render_artifact: Optional[Dict[str, Any]] = None
    acoustic_measurements: Optional[Dict[str, Any]] = None

    # ---- visual evidence (VLP-1) ----
    visual_evidence: Optional[Dict[str, Any]] = None
    """Serialized VisualEvidenceBundle when the visual path was triggered.
    Contains frames (with hashes/timestamps), observations (observed facts),
    interpretations (inferred production meaning), and model_metadata.
    None when transcript was sufficient or visual_mode == 'NEVER'."""

    transcript_sufficiency: Optional[Dict[str, Any]] = None
    """TranscriptSufficiency check result: status, reason, evidence_item_count.
    Explains WHY the visual path was or was not triggered."""

    # ---- outcome / feedback ----
    outcome: Optional[Dict[str, Any]] = None
    user_feedback: Optional[Dict[str, Any]] = None
    """None until a human/agent supplies it. Not populated by this phase."""

    # ---- provenance ----
    provenance: Dict[str, Any] = field(default_factory=dict)
    """Per-field source attribution, e.g.
    {'brain_decision': 'producer_brain.execute_producer_request',
     'production_context': 'production_context.build_from_transcript'}."""

    schema_version: str = "brain_v2.p0.1"

    # reference-data provenance lives in `provenance["reference_provenance"]`
    # (see REFERENCE_PROVENANCE_KEY) -- deliberately NOT a new field, so old
    # records load unchanged and source attribution stays separate from it.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionExperienceRecord":
        return cls(**data)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Builder — called once, right after ADMITTED (everything below is already
# known at that point; nothing here is invented or deferred).
# ---------------------------------------------------------------------------

REFERENCE_PROVENANCE_KEY = "reference_provenance"


def stamp_reference_provenance(record: ProductionExperienceRecord) -> None:
    """Record which Serum reference data (atlas_provenance()) interprets this
    episode. Never overwrites an already-recorded value."""
    if REFERENCE_PROVENANCE_KEY not in record.provenance:
        from serum2.reference.serum_atlas import atlas_provenance
        record.provenance[REFERENCE_PROVENANCE_KEY] = atlas_provenance()


def reference_provenance(record: ProductionExperienceRecord) -> Optional[Dict[str, Any]]:
    """The reference provenance STORED on the episode, or None if it was never
    recorded. Pure read of the record -- never consults the current Atlas, so
    replay needs no local reference files and an old episode is never given
    today's provenance."""
    return record.provenance.get(REFERENCE_PROVENANCE_KEY)


REPLAY_PROVENANCE_KEY = "replay_provenance"
REPLAY_PIN_FIELDS = (
    "brain_logic_version", "capability_contract_versions", "capability_binding_versions",
    "admission_policy_version", "execution_backend_versions", "readback_route_versions",
)
# section 29: only Direct UI is the authoritative Serum readback route; the others corroborate.
READBACK_ROUTES = ("DIRECT_UI", "PLUGIN_HOST_READBACK", "STANDALONE_PLUGIN_INSPECTION", "SCREEN_INSPECTION")


def _file_sha256(path) -> Optional[str]:
    import hashlib
    from pathlib import Path as _P
    try:
        return hashlib.sha256(_P(path).read_bytes()).hexdigest()
    except OSError:
        return None


def build_replay_provenance(registry, capability_keys, backends: Dict[str, Any],
                            readbacks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Version pins needed to REPLAY_EXECUTE an episode faithfully (architecture 33.2).

    Pins what was actually used: hashes of the decision/admission code, and for every capability key
    the contract's status + condition signature and its execution binding. `backends` and `readbacks`
    are supplied by the caller from what really ran; anything not supplied is recorded as absent
    (never invented) and shows up as missing in replay_eligibility()."""
    from pathlib import Path as _P
    here = _P(__file__).parent.parent
    contracts, bindings = {}, {}
    for key in capability_keys:
        c = registry.contracts.get(key)
        if c is None:
            contracts[key] = None
            continue
        contracts[key] = {"status": c.status, "condition_signature_hash": (c.scope or {}).get("condition_signature_hash"),
                          "provenance": c.provenance}
        b = c.execution_binding
        bindings[key] = None if b is None else {
            "mutation_type": b.mutation_type, "host_parameter_name": b.host_parameter_name, "body_path": b.body_path,
            "binding_source": b.binding_source, "binding_version": b.binding_version}
    return {
        "brain_logic_version": {f: _file_sha256(here / "producer" / f) for f in
                                ("producer_brain.py", "target_resolution.py", "target_names.py")},
        "capability_contract_versions": contracts,
        "capability_binding_versions": bindings,
        "admission_policy_version": {"evidence/admission.py": _file_sha256(here / "evidence" / "admission.py"),
                                     "knowledge/step_6_7_admission_handoff.py": _file_sha256(here / "knowledge" / "step_6_7_admission_handoff.py")},
        "execution_backend_versions": dict(backends or {}),
        "readback_route_versions": [dict(r) for r in (readbacks or [])],
    }


def stamp_replay_provenance(record: "ProductionExperienceRecord", registry, capability_keys,
                            backends: Dict[str, Any], readbacks=None) -> None:
    """Pin the replay versions on the episode. Never overwrites an existing pin."""
    if REPLAY_PROVENANCE_KEY not in record.provenance:
        record.provenance[REPLAY_PROVENANCE_KEY] = build_replay_provenance(registry, capability_keys, backends, readbacks)


def build_readback_record(*, domain: str, route: str, plugin: str, version: str, delivery_route: Optional[str],
                          watched: List[str], expected: Dict[str, Any], observed: Dict[str, Any],
                          artifact: Optional[str] = None) -> Dict[str, Any]:
    """One readback record (architecture 29). The comparison is computed here from expected vs observed."""
    if route not in READBACK_ROUTES:
        raise ValueError("unknown readback route %r; expected one of %s" % (route, READBACK_ROUTES))
    match = {k: (k in observed and observed[k] == expected[k]) for k in watched}
    return {"domain": domain, "route": route, "plugin": plugin, "version": version, "delivery_route": delivery_route,
            "watched": list(watched), "expected": {k: expected.get(k) for k in watched},
            "observed": {k: observed.get(k) for k in watched}, "comparison": match,
            "all_match": bool(watched) and all(match.values()), "artifact": artifact,
            "recorded_at": datetime.now(timezone.utc).isoformat()}


def is_canonical_serum_readback(rec: Dict[str, Any]) -> bool:
    """Only DIRECT_UI can establish canonical Serum verification (architecture 28/29)."""
    return rec.get("domain") == "serum" and rec.get("route") == "DIRECT_UI" and bool(rec.get("all_match"))


def replay_eligibility(record: "ProductionExperienceRecord") -> Dict[str, Any]:
    """Architecture 33.3 / 34: what this episode may be used for. Never reinterprets a legacy episode
    against today's reference data."""
    if reference_provenance(record) is None:
        return {"status": "LEGACY_NO_PROVENANCE", "replay_execute": False, "replay_simulate": False,
                "missing": ["reference_provenance"]}
    pins = record.provenance.get(REPLAY_PROVENANCE_KEY) or {}
    missing = [f for f in REPLAY_PIN_FIELDS if not pins.get(f)]
    return {"status": "REPLAYABLE" if not missing else "REFERENCE_ONLY",
            "replay_execute": not missing, "replay_simulate": True, "missing": missing}


def create_initial(run, brain_result=None) -> ProductionExperienceRecord:
    """Build the initial record right after ADMITTED.

    run: a state_machine.ProductionRun already advanced through ADMITTED.
    brain_result: the ProducerResult from _run_brain_intent_admission(),
    if available, used to fill mcp_plan (not persisted on ProductionRun).
    """
    intent = run.intent or {}
    admission = run.admission or {}
    production_context = intent.get("production_context")

    brain_decision: Dict[str, Any] = {
        "resolved_concept": getattr(brain_result, "resolved_concept", None),
        "semantic_direction": getattr(brain_result, "semantic_direction", None),
        "semantic_target": intent.get("semantic_target"),
        "execution_route": intent.get("execution_route"),
        "admitted": admission.get("admitted"),
        "admission_reason": admission.get("reason"),
        "resolution_status": admission.get("resolution_status"),
        "intent_class": intent.get("intent_class"),
        "mcp_plan": admission.get("mcp_plan"),
    }

    retrieved_episode_ids: List[str] = []
    if brain_result is not None:
        retrieved_episode_ids = [
            ep.episode_id for ep in getattr(brain_result, "prior_episodes", []) or []
        ]
    retrieved_knowledge_ids: List[str] = []
    if brain_result is not None:
        retrieved_knowledge_ids = [
            k.knowledge_item_id for k in getattr(brain_result, "retrieved_knowledge", []) or []
        ]

    visual_evidence = None
    transcript_sufficiency = None
    if brain_result is not None:
        visual_evidence = getattr(brain_result, "visual_evidence", None)
        if visual_evidence and isinstance(visual_evidence, dict):
            transcript_sufficiency = visual_evidence.get("transcript_sufficiency")

    record = ProductionExperienceRecord(
        experience_id=f"exp_{run.run_id}",
        run_id=run.run_id,
        source_id=run.source_id,
        source_url=run.youtube_url,
        transcript_snippet=run.transcript_snippet,
        transcript_source_ref=(
            f"serum2/knowledge/{run.source_id}_canonical_knowledge_store_5_6.json"
            if run.source_id else None
        ),
        production_context=production_context,
        producer_request={
            "user_intent": intent.get("user_intent_text"),
            "mode": "CREATE",
            "musical_context": None,
            "advisory_context": production_context,
        },
        brain_decision=brain_decision,
        retrieved_knowledge_ids=retrieved_knowledge_ids,
        retrieved_episode_ids=retrieved_episode_ids,
        visual_evidence=visual_evidence,
        transcript_sufficiency=transcript_sufficiency,
        provenance={
            "source_id": "production_pipeline._resolve_transcript",
            "source_url": "state_machine.ProductionRun.youtube_url",
            "transcript_snippet": "production_pipeline._resolve_transcript",
            "transcript_source_ref": "knowledge.ingestion.ingest_canonical",
            "production_context": "production_context.build_from_transcript",
            "producer_request": "production_pipeline._run_brain_intent_admission",
            "brain_decision": "producer_brain.execute_producer_request",
            "retrieved_knowledge_ids": "producer_brain.ProducerResult.retrieved_knowledge",
            "retrieved_episode_ids": "producer_brain.ProducerResult.prior_episodes",
        },
    )
    stamp_reference_provenance(record)
    return record


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save(record: ProductionExperienceRecord, directory: Optional[Path] = None) -> str:
    d = directory or _EXPERIENCES_DIR
    d.mkdir(parents=True, exist_ok=True)
    record.touch()
    path = d / f"{record.experience_id}.json"
    path.write_text(json.dumps(record.to_dict(), indent=2))
    return str(path)


def load(experience_id: str, directory: Optional[Path] = None) -> ProductionExperienceRecord:
    d = directory or _EXPERIENCES_DIR
    path = d / f"{experience_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No experience record: {experience_id}")
    return ProductionExperienceRecord.from_dict(json.loads(path.read_text()))


def load_for_run(run_id: str, directory: Optional[Path] = None) -> ProductionExperienceRecord:
    return load(f"exp_{run_id}", directory=directory)
