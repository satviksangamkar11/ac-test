"""Canonical producer brain — single entry point for the full pipeline.

execute_producer_request(request) is the one function that drives:

  SOURCE → KNOWLEDGE RETRIEVAL → SEMANTIC INTENT → PRODUCER REASONING
  → CAPABILITY CHECK → ROUTE DECISION → REAL CONTROL → READBACK
  → RENDER → MEASURE → DIAGNOSE → ACCEPT/REJECT → EPISODE
  → RETRIEVAL → BETTER NEXT DECISION

Architecture invariants preserved:
  KNOWLEDGE ≠ AUTHORITY
  EPISODE  ≠ AUTHORITY
  RESOLVED ≠ ADMITTED
  Route selection ≠ execution admission

Authority chain (unchanged):
  CapabilityResolver (6.6) → AdmissionHandoff (6.7) → ContractGovernedExecutor (6.8)
  → ADMITTED → real execution backend

There are exactly two real execution backends, each ending in a caller-fed
finalize_*() call — a bare plan is never EXECUTED on its own:

  Serum-internal targets (e.g. Env1.Release):
    ADMITTED → _build_serum_preset_plan() → SERUM_PRESET_PLAN_READY
    → orchestrator: serum-mcp generate_preset() → .SerumPreset + sha256
    → Serum 2.0.21's OWN in-plugin preset browser loads it (never Ableton's
      browser — it does not index .SerumPreset files; never
      set_device_parameter — Serum-internal fields are not on the
      Ableton-exposed parameter surface)
    → real Serum UI readback → finalize_serum_preset_execution()
    This is the ONLY active Serum execution route. An earlier automatic
    executor (_execute_dawdreamer_with_authority, calling
    serum2.evidence.harness.run()) has been removed: harness.py and spec.py
    never existed in this repository, so that call always raised
    ImportError. Do not reintroduce a second Serum execution path.

  Ableton/DAW-session targets on the 127-param MCP surface (e.g. filter
  cutoff, oscillator volume): ADMITTED → _execute_mcp() → MCP_PLAN_READY
  → orchestrator runs the real mcp__AbletonMCP__* calls → real readback
  → finalize_mcp_execution().

This module never modifies frozen Step 6 files.
"""
from __future__ import annotations

import re
import sys
import os
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.knowledge_retrieval_adapter import (
    retrieve_knowledge_for_intent,
    build_knowledge_notes,
)
from serum2.producer.episode_retrieval import retrieve_relevant_episodes
from serum2.producer.route_selection import RouteSelector, ExecutionRoute
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.target_resolution import (
    TargetResolver, Refusal, LEGACY_STATUS_TO_REFUSAL, REFUSED_UNCLASSIFIED, LAYER_UNKNOWN,
)
from serum2.compiler.mcp_intent import parse_intent, MCP_HOST_MAP
from serum2.producer.concept_representation import ConceptDerivationEngine
from serum2.producer.operation_spec import OperationInterpreter
from serum2.producer.request_context import ContextExtractor
from serum2.producer.universal_intent import IntentFormationEngine


# ---- Step 6 frozen layers (imports must live here, never patched) --------
from step_6_2_universal_production_intent import (
    UniversalProductionIntent, SemanticDirection,
)
from step_6_4_semantic_reasoning_integration import SemanticCandidate
from step_6_5_advisory_decision_engine import AdvisoryDecision
from step_6_6_capability_resolution import CapabilityResolver, ResolutionStatus
from step_6_7_admission_handoff import AdmissionHandoff
from step_6_8_contract_governed_execution import ContractGovernedExecutor
from serum2.evidence import admission as admission_mod


# ---------------------------------------------------------------------------
# Intent → universal concept mapping
# ---------------------------------------------------------------------------

_INTENT_TO_CONCEPT: List[tuple[List[str], str, SemanticDirection]] = [
    # MUST precede the generic longer/shorter rules below: resolution is
    # first-match, and "longer Env1.Attack to 1.5 ms" contains "longer" -- it
    # used to resolve to note-release / Env1.Release, i.e. the WRONG control
    # (found by the td22OIHpWuI fresh run).
    # attack → envelope-attack
    (["attack", "faster attack", "slower attack", "attack longer",
      "attack shorter"],
     "envelope-attack", SemanticDirection.SHORTER),
    # Legacy natural-language rules. A bare direction word ("longer", "shorter", "extend",
    # "tighter") must NOT select a target (architecture section 9): only phrases that also name
    # sustain/release do. Explicit canonical targets never reach these rules (see _resolve_concept).
    (["sustain longer", "longer sustain", "more sustain",
      "release longer", "longer release"],
     "note-release", SemanticDirection.LONGER),
    (["shorter release", "less sustain",
      "quicker release"],
     "note-release", SemanticDirection.SHORTER),
    # cutoff / filter (includes bare character adjectives for CREATE-mode
    # creation intents, e.g. "create a dark bass sound" — not just the
    # comparative "brighter"/"darker" used by mutation-style requests)
    (["cutoff", "filter cutoff", "filter frequency",
      "brighter", "darker", "bright", "dark", "warm"],
     "filter-cutoff", SemanticDirection.HIGHER),
    # oscillator volume (MCP-only bridge)
    (["osc volume", "osc1 volume", "osc 1 volume", "oscillator volume",
      "osc louder", "osc quieter", "osc level"],
     "oscillator-volume", SemanticDirection.HIGHER),
    # filter resonance (MCP-only bridge)
    (["resonance", "filter resonance", "filter reso"],
     "filter-resonance", SemanticDirection.HIGHER),
    # master volume (MCP-only bridge)
    (["master volume", "main volume", "master vol", "overall volume", "overall louder"],
     "master-volume", SemanticDirection.HIGHER),
]

# ---------------------------------------------------------------------------
# MCP-only concept bridge (STEP 7)
# Maps universal concept names that are MCP-qualified but not in
# UNIVERSAL_TO_SEMANTIC (which is frozen). step_6_6_capability_resolution.py
# must NOT be modified; this bridge lives in the brain.
# ---------------------------------------------------------------------------
_MCP_CONCEPT_BRIDGE: Dict[str, str] = {
    # concept → MCP semantic target name (must appear in MCP_HOST_MAP)
    "oscillator-volume": "OSC1.Volume",
    "filter-cutoff":     "Filter.Cutoff",
    "filter-resonance":  "Filter.Resonance",
    "master-volume":     "Global.MasterVolume",
}

# ---------------------------------------------------------------------------
# HOST OPERATIONS (pure Ableton session/arrangement control)
#
# Track/clip/note creation is NOT a Serum capability claim — there is no
# CapabilityContract for "create a MIDI track" because it mutates Ableton
# session state, not a Serum synthesis parameter. Per CLAUDE.md's control
# route architecture, this goes straight to Ableton MCP; the Step 6
# authority chain (CapabilityResolver/admission) is scoped to Serum
# semantic targets and does not apply here.
# ---------------------------------------------------------------------------
_HOST_OPERATION_KEYWORDS = [
    "scratch midi track", "scratch track", "midi track", "create a track",
    "create track", "add a note", "place a note", "midi clip", "a clip",
]


def _is_host_operation(intent_text: str) -> bool:
    lower = intent_text.lower()
    return any(kw in lower for kw in _HOST_OPERATION_KEYWORDS)

_CONCEPT_QUERY_PARAMS: Dict[str, Dict[str, str]] = {
    "note-release": {
        "concept": "release",
        "technique": "sustain",
        "free_text": "release envelope sustain longer",
    },
    "envelope-attack": {
        "concept": "attack",
        "technique": "envelope",
        "free_text": "attack envelope onset",
    },
    "filter-cutoff": {
        "concept": "filter",
        "technique": "cutoff",
        "free_text": "filter cutoff frequency brightness",
    },
}


def _resolve_intent_to_concept(
    intent_text: str,
) -> tuple[Optional[str], SemanticDirection]:
    """Map user intent text to (universal_concept, SemanticDirection).

    Returns (None, LONGER) when no pattern matches.
    """
    lower = intent_text.lower()
    for keywords, concept, direction in _INTENT_TO_CONCEPT:
        if any(kw in lower for kw in keywords):
            return concept, direction
    return None, SemanticDirection.LONGER


def _direction_from_words(text: str) -> "SemanticDirection":
    """Advisory direction, read from the wording AFTER a canonical concept is established
    (architecture section 17: heuristics may refine direction, never the target)."""
    t = (text or "").lower()
    for words, d in ((("shorter", "shorten", "less", "lower", "down", "decrease", "reduce", "tighter"),
                      SemanticDirection.SHORTER),
                     (("longer", "more", "higher", "up", "increase", "extend"),
                      SemanticDirection.LONGER)):
        if any(re.search(r"\b%s\b" % re.escape(w), t) for w in words):
            return d
    return SemanticDirection.LONGER


# ---------------------------------------------------------------------------
# Request / Result models
# ---------------------------------------------------------------------------

@dataclass
class ProducerRequest:
    """Input to the canonical producer brain."""
    user_intent: str
    """Natural-language production intent, e.g. 'Make the note sustain longer'."""

    semantic_target: Optional[str] = None
    """Explicit semantic target override (e.g. 'Env1.Release').
    If None, derived from user_intent."""

    source_url: Optional[str] = None
    """Optional YouTube URL / transcript source to ingest before reasoning."""

    musical_context: Optional[str] = None
    """E.g. 'bass patch, ambient track'."""

    mode: str = "EXECUTE"

    visual_mode: str = "AUTO"
    """Visual evidence mode:
    AUTO   = use visual when transcript is operationally insufficient
    ALWAYS = always acquire visual evidence (with transcript when available)
    NEVER  = skip visual evidence even when transcript is insufficient
    """

    transcript_segments: Optional[List[Dict[str, Any]]] = None
    """Timestamped transcript segments ({"timestamp_sec": float, "text": str}),
    when the caller already has them (e.g. from an agent-layer video/transcript
    MCP tool — this Python process cannot call those directly). When present,
    the visual-evidence path uses transcript-first targeted acquisition
    (transcript_query_planner -> acquire_frames_at_timestamps -> observe ->
    deterministic diff -> infer) instead of blind fixed-cadence sampling.
    None falls back to the legacy blind-sampling path, and the fallback is
    recorded in the trace rather than silently taken."""

    stage_a_observation: Optional[Dict[str, Any]] = None
    """The structured Stage-A visual-census dict, produced by the Claude
    Code session directly inspecting the acquired frames (see
    visual_reasoner.ingest_stage_a_observation() for the schema) -- NOT
    from an embedded Anthropic SDK call. When the transcript-first visual
    path is needed and this is None, execution stops with
    execution_status="STAGE_A_REQUIRED" so the orchestrating session can
    inspect the frames named in result.visual_evidence and re-call with
    this field filled in. Ignored when visual evidence isn't needed."""
    """EXECUTE | CREATE | RECREATE_REFERENCE | DISCOVERY

    CREATE is for creation-style requests ("make a dark bass lead") as
    opposed to EXECUTE's mutation-style requests ("make the release
    longer"). Both run through the identical concept-resolution ->
    knowledge-retrieval -> route-selection -> admission chain; CREATE only
    changes how the result is labeled (result.intent_class = "CREATION")
    so callers know an admitted result seeds a new PresetSpec rather than
    mutating an already-loaded one. See CREATION INTENT != MUTATION INTENT
    in ProducerResult.intent_class."""

    advisory_context: Optional[Dict[str, Any]] = None
    """Advisory musical context from ProductionContext.to_dict().
    Used to enrich knowledge retrieval (role, techniques) and advisory reasoning.
    Does NOT modify CapabilityResolver or admission gate.
    Keys: role, character, genre, subgenre, artist_reference, techniques, era."""

    operation: Optional[str] = None
    """Generic structured operation name, e.g. 'ADD_MODULATION_ROUTE'. When
    set, execute() dispatches on this instead of the concept+direction path
    (note-release/envelope-attack/etc. don't fit a 4-argument topology
    operation). This is a PARALLEL route, not a replacement -- concept-based
    intents are unaffected. Still goes through real Resolution (scope check
    against a qualified contract) and real Admission (admission.admit(),
    unmodified 15.4 gate) before any plan is produced. None means the
    existing concept-resolution path runs as before."""

    operation_args: Optional[Dict[str, Any]] = None
    """Structured runtime arguments for `operation`, e.g. for
    ADD_MODULATION_ROUTE: {"source": "LFO1", "destination": "Filter 1 Freq",
    "amount": None, "bipolar": None}. These are evidence-derived data from
    the video interpreter, not hardcoded per-video values -- amount/bipolar
    are None (never invented) when the source evidence doesn't legibly show
    them. The brain must never promote a None here into a guessed number."""


@dataclass
class KnowledgeContribution:
    """A single retrieved knowledge item and its role in the decision."""
    knowledge_item_id: str
    original_proposition: str
    epistemic_status: str
    relevance_score: float
    source_id: str
    contribution: str  # how it influenced the reasoning
    matched_via_dimension: Optional[str] = None
    """Which structured retrieval dimension surfaced this item: "role",
    "genre", "subgenre", "artist_style", "technique", "era", or None for
    the primary intent-text query. Makes context-aware retrieval (Brain V2
    P2) auditable in the reasoning trace, not just a silent side effect."""


@dataclass
class EpisodeContribution:
    """A prior episode that influenced the current decision."""
    episode_id: str
    semantic_target: str
    human_intent: str
    outcome: str          # e.g. "ACCEPTED", "REJECTED"
    delta_db: Optional[float]
    influence: str        # what changed in the current decision because of this


@dataclass
class ProducerResult:
    """Full trace of one execute_producer_request() call."""

    # ---- inputs ----
    request: ProducerRequest

    # ---- knowledge ----
    retrieved_knowledge: List[KnowledgeContribution] = field(default_factory=list)
    prior_episodes: List[EpisodeContribution] = field(default_factory=list)

    # ---- reasoning (advisory) ----
    resolved_concept: Optional[str] = None
    # B1 provenance: which brain produced the concept. B1_CANONICAL | LEGACY | REFUSED (never mixed).
    resolution_mode: Optional[str] = None
    b1_intent: Optional[Dict[str, Any]] = None
    semantic_direction: Optional[str] = None
    candidate_operations: List[str] = field(default_factory=list)
    selected_operation: Optional[str] = None
    advisory_rationale: str = ""

    # ---- capability / route ----
    semantic_target: Optional[str] = None
    execution_route: Optional[str] = None  # "dawdreamer_serum" | "ableton_mcp" | ...
    route_rationale: str = ""
    resolution_status: Optional[str] = None

    # ---- authority ----
    admitted: Optional[bool] = None
    admission_reason: Optional[str] = None

    # ---- execution ----
    execution_status: str = "NOT_ATTEMPTED"
    baseline_db: Optional[float] = None
    treatment_db: Optional[float] = None
    delta_db: Optional[float] = None
    decision: Optional[str] = None  # ACCEPTED | REJECTED

    # ---- episode ----
    episode_id: Optional[str] = None

    # ---- real MCP execution evidence (populated by finalize_mcp_execution) ----
    mcp_execution: Optional[Dict[str, Any]] = None
    """Real observed MCP tool results: {before, after, readback, tool_calls}.
    None until an actual MCP tool call has been made and fed back via
    ProducerBrain.finalize_mcp_execution(). A non-None value here is the
    only thing that may justify execution_status == 'EXECUTED' for the
    MCP route — a bare plan must never claim EXECUTED."""

    # ---- real Serum preset execution evidence (populated by
    # finalize_serum_preset_execution) — the canonical Serum route ----
    serum_preset_execution: Optional[Dict[str, Any]] = None
    """Real observed serum-mcp + Serum-UI evidence: {preset_path,
    preset_sha256, ui_readback, readback_verified}. None until
    ProducerBrain.finalize_serum_preset_execution() has been called with
    real evidence. A non-None value here is the only thing that may
    justify execution_status == 'EXECUTED' for the Serum route — a bare
    SERUM_PRESET_PLAN_READY must never claim EXECUTED."""

    # ---- intent classification ----
    intent_class: str = "MUTATION"
    """"MUTATION" | "CREATION". Set from request.mode (CREATE -> CREATION,
    everything else -> MUTATION). CREATION INTENT != MUTATION INTENT: the
    resolution/knowledge/admission computation is identical either way (the
    same semantic-target authority chain governs both), but a CREATION
    result's admitted semantic_target/direction/_mcp_plan means "seed value
    for a new PresetSpec", never "go mutate the currently loaded preset".
    Callers must branch on this field, not reinterpret MCP_PLAN_READY."""

    # ---- visual evidence ----
    visual_evidence: Optional[Dict[str, Any]] = None
    """Serialized VisualEvidenceBundle if visual path was used. Contains:
    - frames: list of VisualFrameArtifact (timestamp, hash, path)
    - observations: what was literally observed per frame
    - interpretations: production inferences derived from observations
    - model_metadata: which model was used (honest, no attestation)
    - transcript_sufficiency: what triggered the visual path
    None when visual path was not triggered."""

    observed_canonical_state: Optional[Dict[str, Any]] = None
    """The exact before/after value(s) Stage A actually read off a frame
    (a CanonicalStateDiff, e.g. {target: 'Env1.Release', before: {value:
    '15 ms', ...}, after: {value: '220 ms', ...}, changed: true}), kept
    SEPARATE from semantic_target/semantic_direction so the exact magnitude
    never has to be forced into UniversalProductionIntent (which only
    carries concept+direction). Execution should reproduce THIS value;
    the intent explains WHAT/WHY. None when the transcript-first path
    wasn't used or found no changed diff."""

    # ---- errors ----
    error: Optional[str] = None

    refusal: Optional[Dict[str, Any]] = None
    """Structured refusal (architecture 7.1 / 19): {code, layer, canonical_target, reason, candidates}.
    execution_status is kept unchanged for compatibility; this is the canonical diagnostic."""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["request"] = asdict(self.request)
        return d


# ---------------------------------------------------------------------------
# Core brain
# ---------------------------------------------------------------------------

class ProducerBrain:
    """Stateful (caches registry / selector) producer brain."""

    def __init__(self, skill_retriever=None, prior_evidence=(), grounding_claims=None):
        # Optional advisory inputs (P3 skills, P4.5 prior outcomes, P6 grounding). They only feed reasoning; no authority.
        self._skill_retriever = skill_retriever
        self._prior_evidence = tuple(prior_evidence)
        self._grounding_claims = tuple(grounding_claims) if grounding_claims else ()
        self._registry = ContractRegistry()
        self._selector = RouteSelector()
        # Ordered explicit-target resolution over EXISTING registries (architecture 17/18): no tables here.
        from serum2.compiler.targets import SEMANTIC_TARGETS
        from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC, SemanticTargetMapping
        self._derived_mappings: Dict[str, Any] = {}
        self._target_resolver = TargetResolver(
            self._registry, SEMANTIC_TARGETS, MCP_HOST_MAP, UNIVERSAL_TO_SEMANTIC,
            _MCP_CONCEPT_BRIDGE, SemanticTargetMapping)
        # B1 consumes the resolver's result; it owns no target/contract table.
        self._b1_derivation = ConceptDerivationEngine(
            self._registry, SEMANTIC_TARGETS, MCP_HOST_MAP, target_resolver=self._target_resolver)
        self._b1_operation = OperationInterpreter()
        self._b1_context = ContextExtractor()
        self._b1_intent = IntentFormationEngine()

    # ------------------------------------------------------------------
    # 1. KNOWLEDGE RETRIEVAL (Phase B)
    # ------------------------------------------------------------------
    def _retrieve_knowledge(
        self,
        intent_text: str,
        concept: Optional[str],
        advisory_context: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[KnowledgeContribution], Dict[str, Dict[str, Any]]]:
        """Retrieve real knowledge from the 343-item store.

        Brain V2 P2: wires ProductionContext into retrieval as structured,
        individually-labeled query dimensions (role, genre, subgenre,
        artist_style, technique), not a single anonymous free-text blob.
        Each dimension is run as its own supplementary query (see
        knowledge_retrieval_adapter.retrieve_knowledge_for_intent's
        context_terms) and the resulting items carry matched_via_dimension
        so the reasoning trace shows exactly which context caused which
        item to surface. The concept-anchored `technique` query param
        (e.g. "cutoff" for filter-cutoff) is never overridden by context —
        it must remain authoritative for the resolved semantic concept.

        Only evidence already present in the canonical KnowledgeItem store
        is ever used. No dimension is fabricated when the corpus lacks
        matching content — a term with zero corpus coverage (e.g. an
        artist/genre name absent from every ingested source) legitimately
        contributes zero items, proven empirically per-dimension in
        test_context_aware_retrieval.py. Retrieval remains advisory: it
        feeds knowledge_notes/rationale only, never CapabilityResolver or
        admission (see _resolve_and_admit / _run_mcp_path, which take no
        advisory_context input at all).
        """
        qparams = _CONCEPT_QUERY_PARAMS.get(concept or "", {
            "free_text": intent_text,
        })

        # Extract advisory enrichment from ProductionContext (advisory only).
        # Dimension names match UniversalQuery's own field names
        # (genre/subgenre/artist_style/technique) so the reasoning trace is
        # auditable against the retrieval model's own vocabulary, even
        # though ProductionContext's own field is named artist_reference.
        ctx = advisory_context or {}
        role = ctx.get("role")
        context_terms: List[tuple] = []
        for dimension, value in (
            ("genre", ctx.get("genre")),
            ("subgenre", ctx.get("subgenre")),
            ("artist_style", ctx.get("artist_reference")),
            ("era", ctx.get("era")),
        ):
            if value:
                context_terms.append((dimension, value))
        for technique_term in (ctx.get("techniques") or []):
            context_terms.append(("technique", technique_term))

        items = retrieve_knowledge_for_intent(
            intent_text=qparams.get("free_text", intent_text),
            concept=qparams.get("concept"),
            technique=qparams.get("technique"),
            top_k=6,
            role=role,
            context_terms=context_terms if context_terms else None,
        )
        contributions = [
            KnowledgeContribution(
                knowledge_item_id=it["knowledge_item_id"],
                original_proposition=it["original_proposition"][:160],
                epistemic_status=it["epistemic_status"],
                relevance_score=it["relevance_score"],
                source_id=it["source_reference"]["source_id"],
                contribution="relevance=%.2f via %s%s" % (
                    it["relevance_score"],
                    it.get("primary_match_type", "unknown"),
                    " context=%s" % it["matched_via_dimension"]
                    if it.get("matched_via_dimension") else "",
                ),
                matched_via_dimension=it.get("matched_via_dimension"),
            )
            for it in items
        ]
        knowledge_notes = build_knowledge_notes(items)
        return contributions, knowledge_notes

    # ------------------------------------------------------------------
    # 2. PRIOR EPISODE RETRIEVAL (Phase K)
    # ------------------------------------------------------------------
    def _retrieve_episodes(
        self, semantic_target: str, intent: str
    ) -> tuple[List[EpisodeContribution], List[str]]:
        """Retrieve prior learning episodes and derive their influence."""
        raw = retrieve_relevant_episodes(
            semantic_target=semantic_target,
            intent=intent,
            learning_eligible_only=True,
        )
        contributions = []
        ids = []
        for ep in raw:
            ep_id = ep.get("episode_id", "?")
            ids.append(ep_id)
            delta = ep.get("measurement_delta")
            outcome = ep.get("decision", "UNKNOWN")
            influence = (
                "Prior run ACCEPTED (delta=%.2f dB) → increases confidence in operation"
                % delta if outcome == "ACCEPTED" and delta is not None
                else "Prior run REJECTED → caution, may try different magnitude"
                if outcome == "REJECTED"
                else "Prior run recorded (no quantified influence)"
            )
            contributions.append(EpisodeContribution(
                episode_id=ep_id,
                semantic_target=ep.get("semantic_target", ""),
                human_intent=ep.get("human_intent", ""),
                outcome=outcome,
                delta_db=delta,
                influence=influence,
            ))
        return contributions, ids

    # ------------------------------------------------------------------
    # 3. SEMANTIC CANDIDATE BUILDING (Phase D)
    # ------------------------------------------------------------------
    def _build_advisory_chain(
        self,
        intent: UniversalProductionIntent,
        concept: str,
        episode_ids: List[str],
        knowledge_notes: Dict[str, Dict[str, Any]],
        episode_contributions: List[EpisodeContribution],
    ) -> tuple[SemanticCandidate, AdvisoryDecision, float]:
        """Build candidate and advisory decision.

        Episodes are used to ADJUST confidence (advisory, not authority).
        Prior accepted runs increase confidence; rejected runs lower it.
        """
        base_confidence = 0.75

        # Episode influence on confidence (advisory only)
        for ep in episode_contributions:
            if ep.outcome == "ACCEPTED" and ep.delta_db and ep.delta_db > 0:
                base_confidence = min(0.95, base_confidence + 0.08)
            elif ep.outcome == "REJECTED":
                base_confidence = max(0.50, base_confidence - 0.10)

        op_name = {
            SemanticDirection.LONGER: "lengthen",
            SemanticDirection.SHORTER: "shorten",
            SemanticDirection.HIGHER: "increase",
            SemanticDirection.LOWER: "decrease",
            SemanticDirection.INCREASE: "increase",
            SemanticDirection.DECREASE: "decrease",
        }.get(intent.semantic_direction, "modify")
        # Enum / toggle contracts are SET, not lengthened or increased. Derived from the contract's own
        # allowed_operation; 'select' is a word Capability Resolution's enum check already accepts.
        _m = self._mapping_for(concept)
        _c = self._registry.get(_m.semantic_target) if _m else None
        if _c is not None and _c.allowed_operation == "mutate_enum_value":
            op_name = "select"

        candidate = SemanticCandidate(
            candidate_id="c_%s_%s" % (concept.replace("-", "_"), op_name),
            label="%s_%s" % (op_name, concept.replace("-", "_")),
            target_concept=concept,
            operation=op_name,
            confidence=base_confidence,
        )

        k_ids = list(knowledge_notes.keys())
        decision = AdvisoryDecision(
            decision_id="adv_%s" % datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            intent=intent,
            selected_candidate=candidate,
            decision_status="decided",
            confidence=base_confidence,
        )

        rationale_parts = []
        if k_ids:
            rationale_parts.append("knowledge=%s" % k_ids[:3])
        if episode_ids:
            rationale_parts.append("episodes=%s" % episode_ids)
        rationale_parts.append("confidence=%.2f" % base_confidence)

        return candidate, decision, base_confidence

    # ------------------------------------------------------------------
    # 4. CAPABILITY RESOLUTION + ADMISSION (Phase E)
    # ------------------------------------------------------------------
    def _resolve_and_admit(
        self,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
        contract,
    ) -> tuple[Any, Any, Any]:
        """Run 6.6 resolution → 6.7 admission. Returns (resolution, adm_request, adm_result)."""
        # Build caller's declared context from contract prerequisites
        ctx = {}
        for p in (contract.prerequisites or ()):
            fp = p["field_path"]
            ctx[fp] = p.get("declared_value")

        resolver = CapabilityResolver(self._registry)
        resolver.semantic_mappings = dict(resolver.semantic_mappings, **self._derived_mappings)
        resolution = resolver.resolve(candidate, intent, current_context=ctx)

        if resolution.resolution_status != ResolutionStatus.RESOLVED:
            return resolution, None, None

        # Caller-side prerequisite confirmation (Step 4)
        prereq_verified = {}
        for p in (contract.prerequisites or ()):
            fp = p["field_path"]
            prereq_verified[fp] = p.get("declared_value")

        handoff = AdmissionHandoff(admission_mod, self._registry)
        req = handoff.prepare_request(resolution, candidate, intent)
        if req is None:
            return resolution, None, None
        req.proposed_prerequisites_verified = prereq_verified
        adm = handoff.submit_to_admission(req)
        return resolution, req, adm

    # ------------------------------------------------------------------
    # 5. SERUM EXECUTION PLAN (Phase G)
    #
    # CANONICAL SERUM EXECUTION ROUTE (the only active one — see module
    # docstring): resolution -> admission -> serum-mcp preset creation ->
    # Serum 2.0.21 UI load -> UI readback -> state verification. The brain's
    # own responsibility ends at ADMITTED; it hands back the admitted
    # contract's authorized mutation target/value so the orchestrating agent
    # can perform the real serum-mcp call and real Serum UI load/readback.
    # Only finalize_serum_preset_execution() (below), fed with REAL observed
    # evidence, may mark this EXECUTED — a bare plan is never EXECUTED.
    #
    # An earlier version of this method additionally called a "canonical
    # harness" (serum2.evidence.harness.run(spec), built on
    # serum2.evidence.spec.ExperimentSpec) to auto-run DawDreamer and
    # fabricate baseline/treatment measurements + a Step 6.10 episode from
    # them. Those two modules do not exist in this repository — the call
    # always raised ImportError, caught by the caller as EXECUTION_ERROR.
    # That auto-executor has been removed, not repaired: there is exactly
    # one active Serum execution route now, and it is the one documented
    # above. ContractGovernedExecutor (Step 6.8, frozen) is still used
    # below — it is the real authority-granting layer, not the broken part.
    # ------------------------------------------------------------------
    def _build_serum_preset_plan(
        self,
        intent: "UniversalProductionIntent",
        candidate: "SemanticCandidate",
        decision: "AdvisoryDecision",
        resolution,
        adm,
        contract,
    ) -> Dict[str, Any]:
        """Resolve admitted-contract authority into a Serum preset target.

        Returns a plan dict for the orchestrator to execute via serum-mcp +
        the real Serum UI. Never calls a Serum/DawDreamer backend itself.
        """
        from step_6_8_contract_governed_execution import (
            ContractGovernedExecutor, ExecutionPathway,
        )

        # Frozen Step 6.8 authority layer — real, unmodified. This is what
        # actually grants execution authority; it has nothing to do with
        # the removed auto-harness call.
        executor = ContractGovernedExecutor()
        record = executor.create_execution_intention(
            intent, decision, resolution, adm, self._registry
        )
        authority = record.execution_authority

        if record.pathway is not ExecutionPathway.ADMITTED or authority is None:
            return {"status": "NOT_ADMITTED", "pathway": record.pathway.value}

        scope = authority.scope or {}
        mutation_path = scope["mutation_target_path"]
        mutation_value = scope["mutation_value_used"]

        return {
            "status": "SERUM_PRESET_PLAN_READY",
            "contract_id": adm.contract_id,
            "mutation_target_path": mutation_path,
            "mutation_value_used": mutation_value,
            "capability_key": contract.target,
            "execution_steps": [
                "1. serum-mcp generate_preset(spec) with %s set to the "
                "admitted value" % mutation_path,
                "2. record preset_path + sha256 of the written .SerumPreset",
                "3. Load the preset into the real Serum 2 instance via "
                "Serum's own in-plugin preset browser (NOT Ableton's "
                "browser — it does not index .SerumPreset files, and NOT "
                "set_device_parameter — Serum-internal fields are not on "
                "the Ableton-exposed parameter surface)",
                "4. Screenshot/read back the real Serum UI to confirm the "
                "loaded value matches the admitted target",
                "5. Call finalize_serum_preset_execution(plan, preset_path, "
                "preset_sha256, ui_readback, readback_verified)",
            ],
        }

    # ------------------------------------------------------------------
    # 6. ABLETON MCP EXECUTION (Phase H)
    # ------------------------------------------------------------------
    def _execute_mcp(
        self, intent_text: str, semantic_target: str
    ) -> Dict[str, Any]:
        """Compile MCP intent → structured execution plan.

        ARCHITECTURE BOUNDARY:
        The brain's responsibility ends at plan production. Execution of actual
        Ableton MCP tools happens in the orchestrating runtime (Claude Code).
        This is correct per CLAUDE.md control-route architecture: the brain is
        advisory; only real, measured execution counts. The caller must:
          1. Execute each tool per execution_steps
          2. Capture tool outputs (before, after, readback)
          3. Call finalize_mcp_execution(tool_calls, before, after, readback_verified)

        Only then does the result become EXECUTED (not PLAN_READY).

        When semantic_target is a pre-resolved MCP target name (e.g. "OSC1.Volume"),
        the intent parser is bypassed and the value is derived from the raw intent text
        directional keywords. This supports the MCP bridge path (STEP 7).

        Plan dict keys:
          status        PLAN_READY | REFUSED
          semantic_target_name
          host_param_index   int — 0-based param index in Serum's 127-param surface
          host_param_label   str — human-readable param name
          value_kind         "absolute" | "relative"
          value              float — absolute 0-1 OR signed relative delta
          track_index        int — which Ableton track hosts Serum (default 0)
          device_index       int — which device slot on that track (default 0)
          execution_steps    list[str] — ordered MCP operations the caller must run
        """
        from serum2.compiler.mcp_intent import (
            compile_intent as _compile, MCP_HOST_MAP, _detect_value, RELATIVE,
        )
        from serum2.compiler.targets import SEMANTIC_TARGETS

        # Fast path: semantic_target already resolved (from MCP bridge)
        if semantic_target and semantic_target in MCP_HOST_MAP:
            host = MCP_HOST_MAP[semantic_target]
            ref = SEMANTIC_TARGETS.get(semantic_target)
            # Extract directional value from intent text
            val_result = _detect_value(intent_text.lower())
            if val_result is None:
                val_result = (RELATIVE, 0.20)  # default: slight increase
            value_kind, value = val_result
            return self._build_mcp_plan_dict(
                semantic_target_name=semantic_target,
                capability_key=ref.capability_key if ref else semantic_target,
                host=host, value_kind=value_kind, value=value,
            )

        # Standard path: parse intent text
        plan = _compile(intent_text)
        if hasattr(plan, "reason"):
            return {
                "status": "REFUSED",
                "reason": plan.reason,
                "detail": getattr(plan, "detail", ""),
                "semantic_target": semantic_target,
            }
        return self._build_mcp_plan_dict(
            semantic_target_name=plan.semantic_target.name,
            capability_key=plan.capability_key,
            host=plan.host_param,
            value_kind=plan.value_kind,
            value=plan.value_spec,
        )

    def _build_mcp_plan_dict(
        self, semantic_target_name: str, capability_key: str,
        host: Any, value_kind: str, value: float,
    ) -> Dict[str, Any]:
        """Assemble the PLAN_READY dict from resolved components."""
        return {
            "status": "PLAN_READY",
            "semantic_target_name": semantic_target_name,
            "capability_key": capability_key,
            "host_param_index": host.index,
            "host_param_label": host.name,
            "host_param_description": host.description,
            "track_index": host.track_index,
            "device_index": host.device_index,
            "value_kind": value_kind,
            "value": value,
            "execution_steps": [
                "1. get_device_parameters(track_index=%d, device_index=%d)"
                % (host.track_index, host.device_index),
                "2. read current value at param index %d (%r)"
                % (host.index, host.name),
                "3. resolve_host_value(current, kind=%r, value=%s)"
                % (value_kind, value),
                "4. set_device_parameter(track_index=%d, device_index=%d, "
                "parameter=%d, value=<resolved>)"
                % (host.track_index, host.device_index, host.index),
                "5. get_device_parameters again → readback to verify write",
                "6. make_audit_record(plan, before, after)",
            ],
        }

    def _build_host_operation_plan(self, intent_text: str) -> Dict[str, Any]:
        """Build a plan for a pure Ableton host/session operation.

        No capability contract applies (no Serum parameter is being
        mutated); this is direct session control per CLAUDE.md's control
        route architecture. Still routes through the same
        plan → real MCP call → finalize_mcp_execution() seam so no
        execution is ever claimed without a real, verified MCP readback.
        """
        wants_note = "note" in intent_text.lower()
        return {
            "status": "PLAN_READY",
            "operation_class": "HOST_OPERATION",
            "semantic_target_name": "Ableton.ScratchMidiTrack",
            "execution_steps": [
                "1. create_midi_track(index=-1)",
                "2. create_clip(track_index=<new>, clip_index=0, length=4.0)",
            ] + (
                ["3. add_notes_to_clip(track_index=<new>, clip_index=0, notes=[...])",
                 "4. get_clip_notes(track_index=<new>, clip_index=0)  # readback"]
                if wants_note else
                ["3. get_track_info(track_index=<new>)  # readback"]
            ),
            "wants_note": wants_note,
        }

    def _make_discovery_request(
        self, concept: str, semantic_target_name: str
    ) -> Dict[str, Any]:
        """Build a DiscoveryRequest dict for a concept with no MCP mapping.

        STEP 9: Called when a concept is recognized but the MCP_HOST_MAP
        does not cover it. Returns DISCOVERABLE status with experiment spec.
        Does NOT auto-execute discovery (user authorization required).
        """
        return {
            "status": "DISCOVERABLE",
            "concept": concept,
            "semantic_target": semantic_target_name,
            "discovery_request": {
                "experiment_type": "MCP_PARAMETER_PROBE",
                "objective": (
                    "Identify which Ableton/Serum MCP parameter index controls %r "
                    "(%r) so it can be added to MCP_HOST_MAP." % (concept, semantic_target_name)
                ),
                "steps": [
                    "Load Serum 2 on a scratch MIDI track (track_index=scratch)",
                    "Call get_device_parameters to enumerate all 127 params",
                    "Search param names for keywords matching %r" % semantic_target_name,
                    "For each candidate: set_device_parameter + readback + verify audible effect",
                    "If confirmed: record MCPHostParam(index, name, desc) in MCP_HOST_MAP",
                ],
                "authorization_required": True,
                "note": "Discovery generates new MCP evidence. "
                        "User must authorize before the experiment runs.",
            },
        }

    # ------------------------------------------------------------------
    # VISUAL EVIDENCE PATH (VLP-1)
    # ------------------------------------------------------------------

    def _check_transcript_sufficiency(
        self, source_id: Optional[str], intent_text: str
    ):
        """Check whether transcript evidence is operationally sufficient.

        Loads the canonical knowledge store for source_id and checks whether
        the available items contain actionable production technique information
        relevant to intent_text.

        Returns a TranscriptSufficiency dataclass.
        """
        from serum2.source.visual_evidence import TranscriptSufficiency

        if source_id is None:
            return TranscriptSufficiency(
                status="UNAVAILABLE",
                reason="No source_id (no source URL was provided)",
                evidence_item_count=0,
            )

        knowledge_dir = Path(__file__).parent.parent / "knowledge"
        store_path = knowledge_dir / ("%s_canonical_knowledge_store_5_6.json" % source_id)

        if not store_path.exists():
            return TranscriptSufficiency(
                status="UNAVAILABLE",
                reason="Canonical knowledge store not found for %s" % source_id,
                evidence_item_count=0,
            )

        try:
            data = json.loads(store_path.read_text())
            items = data.get("items", {})
            item_count = len(items)
        except Exception as exc:
            return TranscriptSufficiency(
                status="UNAVAILABLE",
                reason="Failed to read knowledge store: %s" % exc,
                evidence_item_count=0,
            )

        # Insufficient if very few items (punctuation bug) or no actionable content
        # The known issue: auto-generated transcript without punctuation → 1 chunk only
        if item_count <= 1:
            return TranscriptSufficiency(
                status="INSUFFICIENT_OPERATIONAL",
                reason=(
                    "Canonical store has only %d item(s) — transcript is likely "
                    "unpunctuated (auto-generated) causing the full content to be "
                    "collapsed into one chunk with insufficient detail" % item_count
                ),
                evidence_item_count=item_count,
            )

        # Check if any items contain actionable production technique detail
        # Look for parameter values, numeric references, or technique-specific language
        actionable_keywords = [
            "set", "turn", "adjust", "increase", "decrease", "lower", "raise",
            "filter", "cutoff", "resonance", "attack", "release", "knob", "slider",
            "%", "hz", "db", "ms", "sec",
        ]
        intent_lower = intent_text.lower()
        actionable_count = 0
        for item in items.values():
            prop = (item.get("original_proposition") or "").lower()
            if any(kw in prop for kw in actionable_keywords):
                actionable_count += 1

        if actionable_count == 0:
            return TranscriptSufficiency(
                status="INSUFFICIENT_OPERATIONAL",
                reason=(
                    "%d items found but none contain actionable production "
                    "technique information (no parameter values, settings, "
                    "or technique-specific language)" % item_count
                ),
                evidence_item_count=item_count,
            )

        return TranscriptSufficiency(
            status="SUFFICIENT",
            reason="%d items; %d contain actionable production detail" % (
                item_count, actionable_count
            ),
            evidence_item_count=item_count,
        )

    def _acquire_and_reason_visual(
        self,
        source_url: str,
        source_id: Optional[str],
        intent_text: str,
        transcript_sufficiency,
        force: bool = False,
    ):
        """Acquire visual evidence and run VisualReasoner.

        Returns a VisualEvidenceBundle (with observations + interpretations).
        """
        from serum2.source.acquire_visual_evidence import acquire_visual_evidence
        from serum2.producer.visual_reasoner import VisualReasoner

        bundle = acquire_visual_evidence(
            source_url=source_url,
            transcript_sufficiency=transcript_sufficiency,
            force=force,
        )
        if bundle.acquisition_error:
            return bundle

        reasoner = VisualReasoner()
        reasoner.reason(bundle)
        return bundle

    def _acquire_and_reason_visual_transcript_first(
        self,
        source_url: str,
        transcript_segments: List[Dict[str, Any]],
        transcript_sufficiency,
        stage_a_observation: Optional[Dict[str, Any]] = None,
    ):
        """Transcript-first visual evidence pipeline (VLP-1 canonical architecture).

        transcript_query_planner locates WHERE to look (action-bearing
        mention + before/after window) -> acquire_frames_at_timestamps
        fetches ONLY those exact timestamps (no blind cadence sampling) ->
        Stage A reads exact UI values + a full panel census per frame ->
        diff_observed_states computes the before/after change
        deterministically (no model call) -> infer_from_diffs derives
        production meaning FROM the diff (also deterministic — the exact
        value can never drift from what Stage A actually read off a frame).

        CANONICAL PATH: Stage A vision is performed by the Claude Code
        session itself (this project's model runtime), never by an embedded
        Anthropic SDK client. `stage_a_observation` is the structured
        observation dict Claude Code produces by directly inspecting the
        acquired frames (see visual_reasoner.ingest_stage_a_observation()
        for the exact contract/schema). When it is None, this method stops
        right after frame acquisition and reports bundle.reasoning_error
        asking the orchestrating session to inspect the acquired frames and
        call this method again with stage_a_observation filled in -- it
        does NOT fall back to VisualReasoner.observe_frames()'s legacy
        Anthropic-SDK path, which is non-canonical (see that method's
        docstring) and stays unused by this pipeline.

        Returns a VisualEvidenceBundle. bundle.query_plan records the plan
        that drove acquisition; bundle.acquisition_error is set (and the
        bundle otherwise empty) if no known target was mentioned in the
        transcript at all — that is an honest BLOCKED outcome, not a
        silent fallback to blind sampling.
        """
        from serum2.source.transcript_query_planner import (
            plan_visual_queries, TranscriptSegment,
        )
        from serum2.source.acquire_visual_evidence import acquire_frames_at_timestamps
        from serum2.producer.visual_reasoner import (
            ingest_stage_a_observation, diff_observed_states, infer_from_diffs,
        )

        segments = [
            TranscriptSegment(
                timestamp_sec=float(s["timestamp_sec"]), text=str(s.get("text", "")),
            )
            for s in transcript_segments
        ]
        plan = plan_visual_queries(segments)

        bundle = None
        if not plan.targets:
            from serum2.source.visual_evidence import VisualEvidenceBundle
            from serum2.source.youtube_url import extract_youtube_video_id
            bundle = VisualEvidenceBundle(
                source_url=source_url,
                source_id="",
                video_id=extract_youtube_video_id(source_url),
                transcript_sufficiency=transcript_sufficiency,
            )
            bundle.acquisition_error = (
                "Transcript-first planning found no mention of a known "
                "production target (release/attack/cutoff/resonance) — "
                "BLOCKED rather than falling back to blind sampling, which "
                "is what produced the invalidated genre-inferred episode."
            )
            return bundle

        bundle = acquire_frames_at_timestamps(
            source_url=source_url, timestamps=plan.timestamps(),
        )
        bundle.transcript_sufficiency = transcript_sufficiency
        bundle.query_plan = plan.to_dict()
        if bundle.acquisition_error:
            return bundle

        if stage_a_observation is None:
            bundle.reasoning_error = (
                "STAGE_A_REQUIRED: frames acquired at %r; the orchestrating "
                "Claude Code session must now directly inspect them (a full "
                "panel census, not scoped to target_hint=%r) and re-call "
                "this method with stage_a_observation set to the resulting "
                "observation dict. No Anthropic SDK call happens here by "
                "design." % (plan.timestamps(), plan.target_name_hint)
            )
            return bundle

        ingest_stage_a_observation(bundle, stage_a_observation, target_hint=plan.target_name_hint)

        diffs = diff_observed_states(bundle)
        infer_from_diffs(bundle, diffs)
        return bundle

    def _visual_evidence_to_intent(
        self, bundle, user_intent: str
    ) -> Optional["UniversalProductionIntent"]:
        """Convert the best visual interpretation to a UniversalProductionIntent.

        This does NOT bypass admission — it produces an intent that then goes
        through the existing authority chain unchanged.

        Returns None if no actionable interpretation was found.
        """
        interp = bundle.best_interpretation()
        if interp is None:
            return None

        from serum2.source.visual_evidence import VisualInterpretation

        # Map interpretation's production_concept + direction to SemanticDirection
        concept = interp.production_concept
        direction_str = interp.semantic_direction.lower()

        direction_map = {
            "increase": SemanticDirection.INCREASE,
            "decrease": SemanticDirection.DECREASE,
            "higher": SemanticDirection.HIGHER,
            "lower": SemanticDirection.LOWER,
            "longer": SemanticDirection.LONGER,
            "shorter": SemanticDirection.SHORTER,
            "brighter": SemanticDirection.BRIGHTER,
            "darker": SemanticDirection.DARKER,
            "louder": SemanticDirection.LOUDER,
            "quieter": SemanticDirection.QUIETER,
        }
        direction = direction_map.get(direction_str, SemanticDirection.HIGHER)

        # Build a user_intent string that the brain's concept resolver can match
        # Use the production_action if available, otherwise the interpretation text
        effective_intent = interp.production_action or interp.interpretation_text

        intent = UniversalProductionIntent(
            original_user_request=user_intent,
            musical_objective=interp.interpretation_text,
            desired_change=interp.production_action,
            target_concept=concept,
            semantic_direction=direction,
            notes=(
                "Derived from visual evidence (VisualReasoner). "
                "Confidence=%.2f. Supporting frames: %s" % (
                    interp.confidence,
                    ", ".join(interp.supporting_frame_ids[:3]),
                )
            ),
        )
        return intent

    # ------------------------------------------------------------------
    # SOURCE URL INGESTION (STEP 6)
    # ------------------------------------------------------------------
    def _ingest_source_url(self, source_url: str) -> Dict[str, Any]:
        """Ingest a YouTube source URL using the canonical phase1/phase2_3 pipeline.

        Mirrors experiments/new_source_run/phase1_ingest.py and
        phase2_3_extract_normalize.py logic without duplicating frozen Step 5.

        Returns a dict with status and ingested source_id / item_count.
        Does NOT modify frozen step_5_* files.
        """
        import hashlib
        from serum2.source.youtube_url import extract_youtube_video_id
        source_id = "yt_" + hashlib.md5(source_url.encode()).hexdigest()[:12]
        knowledge_dir = Path(__file__).parent.parent / "knowledge"

        # Check if already ingested under this (md5-based) source_id (idempotent)
        ingestion_file = knowledge_dir / ("%s_source_ingestion_5_3.json" % source_id)
        if ingestion_file.exists():
            return {
                "status": "ALREADY_INGESTED",
                "source_id": source_id,
                "source_url": source_url,
                "ingestion_file": str(ingestion_file),
            }

        # Older sources were ingested under a video-id-based source_id
        # (e.g. "yt_k6OBzXdcFtA") rather than this md5-based scheme. Recognize
        # an existing canonical store under that naming instead of attempting
        # to re-ingest (and failing) a source that already has evidence.
        try:
            legacy_source_id = "yt_" + extract_youtube_video_id(source_url)
        except ValueError:
            legacy_source_id = None
        if legacy_source_id:
            legacy_store = knowledge_dir / (
                "%s_canonical_knowledge_store_5_6.json" % legacy_source_id
            )
            if legacy_store.exists():
                return {
                    "status": "ALREADY_INGESTED",
                    "source_id": legacy_source_id,
                    "source_url": source_url,
                    "ingestion_file": str(legacy_store),
                }

        # Phase 1: transcript acquisition
        try:
            import subprocess
            phase1 = Path(__file__).parent.parent.parent / "experiments" / "new_source_run" / "phase1_ingest.py"
            if not phase1.exists():
                return {"status": "SKIPPED", "reason": "phase1_ingest.py not found", "source_id": source_id}
            # Run as subprocess to avoid polluting this process
            env_copy = os.environ.copy()
            env_copy["VIDEO_URL_OVERRIDE"] = source_url
            proc = subprocess.run(
                [sys.executable, str(phase1)],
                capture_output=True, text=True, timeout=120, env=env_copy,
            )
            if proc.returncode != 0:
                return {
                    "status": "INGESTION_FAILED",
                    "source_id": source_id,
                    "stderr": proc.stderr[-500:],
                }
        except Exception as exc:
            return {"status": "INGESTION_ERROR", "source_id": source_id, "error": str(exc)}

        return {
            "status": "INGESTED",
            "source_id": source_id,
            "source_url": source_url,
        }

    # ------------------------------------------------------------------
    # MAIN ENTRY
    # ------------------------------------------------------------------
    def execute(self, request: ProducerRequest) -> ProducerResult:
        """Canonical entry point. Runs the decision flow, then guarantees every refused request
        carries a structured refusal record (code + emitting layer) next to the legacy status."""
        result = self._execute_inner(request)
        if result.refusal is None and str(result.execution_status).startswith("REFUSED"):
            code, layer = LEGACY_STATUS_TO_REFUSAL.get(result.execution_status, (REFUSED_UNCLASSIFIED, LAYER_UNKNOWN))
            result.refusal = Refusal(code, layer, result.semantic_target,
                                     result.error or result.execution_status).to_dict()
        return result

    def _resolve_concept(self, request: ProducerRequest):
        """Ordered resolution (architecture 17/18). Returns (concept, direction, refusal, resolution).

        An explicit canonical target (named in the intent or as semantic_target) is resolved through
        the reference Atlas and the existing target registries ONLY; keyword heuristics never see it.
        Without an explicit target the legacy natural-language path runs (its bare direction words
        no longer select a target)."""
        res = self._target_resolver.resolve(request.user_intent, request.semantic_target)
        if res is None:
            concept, direction = _resolve_intent_to_concept(request.user_intent)
            return concept, direction, None, None
        if res.refusal is not None:
            return None, SemanticDirection.LONGER, res.refusal, res
        if res.mapping is not None:
            self._derived_mappings[res.concept] = res.mapping
        return res.concept, self._direction_for(res, request.user_intent), None, res

    def _direction_for(self, res, text: str):
        """Direction after the target is fixed. An enum/toggle contract has no numeric direction
        (SemanticDirection has no neutral member), so INCREASE is a placeholder there."""
        contract = self._registry.contracts.get(res.capability_key) if res.capability_key else None
        if contract is not None and contract.allowed_operation == "mutate_enum_value":
            return SemanticDirection.INCREASE
        return _direction_from_words(text)

    def _record_resolution(self, result, request, direction, refusal, explicit):
        """Label which brain produced the concept and, on the canonical path, run B1.

        explicit is the TargetResolver result. With an explicit canonical target B1 forms the
        UniversalProductionIntent from it (B1 never re-resolves the target). Without one, the concept
        came from the LEGACY natural-language table and B1 was NOT used. B1 has no execution authority:
        the intent it forms goes on to Capability Resolution and Admission unchanged."""
        if explicit is None:
            result.resolution_mode = "LEGACY"
            result.b1_intent = {"resolution_mode": "LEGACY", "brain_source": "_INTENT_TO_CONCEPT", "b1_used": False}
            return direction
        if refusal is not None:
            result.resolution_mode = "REFUSED"
            result.b1_intent = {"resolution_mode": "REFUSED", "b1_used": False, "refusal_code": refusal.code}
            return direction
        rep = self._b1_derivation.derive_from_resolution(explicit)
        hint = rep.operation_type if rep.operation_type in ("numeric", "enum", "toggle") else None
        op = self._b1_operation.interpret(request.user_intent, hint)
        ctx = self._b1_context.extract(request.user_intent, request.semantic_target)
        intent = self._b1_intent.form_intent(rep.canonical_target, rep, op, ctx, input_request=request)
        result.resolution_mode = "B1_CANONICAL"
        # P4: advisory candidates -> ranking -> selected candidate becomes the intent handed on to Capability
        # Resolution and Admission (unchanged). The candidate layer cannot execute, admit or add capability.
        from serum2.producer.candidate_ranking import (
            CandidateGenerator, CandidateRanker, collect_advisories, collect_grounding_advisory, to_intent
        )
        advisories, excluded = collect_advisories(self._skill_retriever, intent.canonical_target) if self._skill_retriever else ([], [])
        grounding_advisory = collect_grounding_advisory(self._grounding_claims, intent)
        ranked = CandidateRanker().rank(CandidateGenerator().generate(intent, advisories), self._prior_evidence,
                                        grounding_advisory)
        intent = to_intent(ranked.selected.candidate, intent)
        result.b1_intent = dict(intent.to_dict(), resolution_mode="B1_CANONICAL", b1_used=True,
                                excluded_skills=excluded, **ranked.to_audit())
        op = intent.operation
        if op.direction == "decrease":
            return SemanticDirection.SHORTER
        if op.direction == "increase":
            return SemanticDirection.LONGER
        return direction

    def _mapping_for(self, concept: str):
        from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC
        return UNIVERSAL_TO_SEMANTIC.get(concept) or self._derived_mappings.get(concept)

    def _execute_inner(self, request: ProducerRequest) -> ProducerResult:
        result = ProducerResult(request=request)
        result.intent_class = "CREATION" if request.mode == "CREATE" else "MUTATION"

        # ---- generic structured operation path (parallel to concept-based
        # intents; e.g. ADD_MODULATION_ROUTE) ----
        if request.operation:
            return self._run_structured_operation(result, request)

        try:
            # ---- source URL ingestion (STEP 6) ----
            ingested_source_id = None
            if request.source_url:
                ingest_result = self._ingest_source_url(request.source_url)
                ingested_source_id = ingest_result.get("source_id")
                ingest_status = ingest_result.get("status")

                # Verify ingestion completed and canonical store is available
                if ingest_status in ("INGESTED", "ALREADY_INGESTED"):
                    # Wait for canonical store to be available before proceeding
                    knowledge_dir = Path(__file__).parent.parent / "knowledge"
                    canonical_store = knowledge_dir / (
                        "%s_canonical_knowledge_store_5_6.json" % ingested_source_id
                    )
                    if not canonical_store.exists():
                        result.error = (
                            "Source ingestion completed but canonical store %s "
                            "not found. Ingestion pipeline may have failed." % canonical_store.name
                        )
                        result.execution_status = "INGESTION_STORE_MISSING"
                        return result
                else:
                    result.error = (
                        "Source ingestion failed with status %r. "
                        "Details: %s" % (ingest_status, ingest_result.get("error", "unknown"))
                    )
                    result.execution_status = "INGESTION_FAILED"
                    return result

                result.advisory_rationale = (
                    "source_url ingestion: status=%s source_id=%s verified_store=yes" % (
                        ingest_status, ingested_source_id
                    )
                )

            # ---- visual evidence path (VLP-1) ----
            if request.source_url and request.visual_mode != "NEVER":
                ts_check = self._check_transcript_sufficiency(
                    ingested_source_id, request.user_intent
                )
                needs_visual = (
                    request.visual_mode == "ALWAYS"
                    or ts_check.status in ("INSUFFICIENT_OPERATIONAL", "UNAVAILABLE")
                )
                if needs_visual:
                    if request.transcript_segments:
                        bundle = self._acquire_and_reason_visual_transcript_first(
                            source_url=request.source_url,
                            transcript_segments=request.transcript_segments,
                            transcript_sufficiency=ts_check,
                            stage_a_observation=request.stage_a_observation,
                        )
                        if bundle.reasoning_error and bundle.reasoning_error.startswith("STAGE_A_REQUIRED"):
                            result.visual_evidence = bundle.to_dict()
                            result.execution_status = "STAGE_A_REQUIRED"
                            result.error = bundle.reasoning_error
                            return result
                    else:
                        bundle = self._acquire_and_reason_visual(
                            source_url=request.source_url,
                            source_id=ingested_source_id,
                            intent_text=request.user_intent,
                            transcript_sufficiency=ts_check,
                        )
                        result.advisory_rationale = (
                            (result.advisory_rationale or "") +
                            " | visual path: no transcript_segments supplied, "
                            "used legacy blind fixed-cadence sampling"
                        )
                    result.visual_evidence = bundle.to_dict()

                    changed_diff = next(
                        (d for d in bundle.canonical_diffs if d.changed), None
                    )
                    if changed_diff:
                        result.observed_canonical_state = changed_diff.to_dict()

                    # If visual reasoning produced interpretations, use the best
                    # one to override/augment the user intent for concept resolution
                    if bundle.interpretations and not bundle.reasoning_error:
                        visual_intent = self._visual_evidence_to_intent(
                            bundle, request.user_intent
                        )
                        if visual_intent and visual_intent.target_concept:
                            # Inject visual concept into the request so the
                            # existing concept resolver finds it
                            result.advisory_rationale = (
                                (result.advisory_rationale or "") +
                                " | visual_evidence: %d frames, %d obs, %d interp; "
                                "best_concept=%r dir=%s conf=%.2f" % (
                                    len(bundle.frames),
                                    len(bundle.observations),
                                    len(bundle.interpretations),
                                    visual_intent.target_concept,
                                    visual_intent.semantic_direction.value
                                    if visual_intent.semantic_direction else "?",
                                    bundle.best_interpretation().confidence,
                                )
                            )
                            # If no explicit user_intent provided a concept,
                            # use the visual concept (still goes through existing
                            # authority chain unchanged)
                            if not any(
                                any(kw in request.user_intent.lower() for kw in kws)
                                for kws, _, _ in _INTENT_TO_CONCEPT
                            ):
                                # User intent is ambiguous; use visual concept
                                request = ProducerRequest(
                                    user_intent=(
                                        visual_intent.production_action
                                        or visual_intent.musical_objective
                                        or request.user_intent
                                    ),
                                    source_url=request.source_url,
                                    mode=request.mode,
                                    musical_context=request.musical_context,
                                    advisory_context=request.advisory_context,
                                    visual_mode="NEVER",  # prevent recursion
                                )
                    elif bundle.reasoning_error:
                        result.advisory_rationale = (
                            (result.advisory_rationale or "") +
                            " | visual_reasoning_error: %s" % bundle.reasoning_error
                        )

            # ---- RECREATE_REFERENCE mode (STEP 8) ----
            if request.mode == "RECREATE_REFERENCE":
                return self._execute_recreate_reference(request, result)

            # ---- pure Ableton host operation (no Serum capability applies) ----
            if _is_host_operation(request.user_intent):
                result.resolved_concept = "host-operation"
                result.execution_route = ExecutionRoute.ABLETON_MCP.value
                result.route_rationale = (
                    "Pure Ableton session operation (track/clip/note creation). "
                    "No Serum CapabilityContract applies; routes directly to "
                    "Ableton MCP per CLAUDE.md control route architecture."
                )
                plan = self._build_host_operation_plan(request.user_intent)
                result.execution_status = "MCP_PLAN_READY"
                result.admitted = True
                result.admission_reason = "HOST_OPERATION_NO_CONTRACT_REQUIRED"
                result.resolution_status = "host_operation"
                result.selected_operation = "create_scratch_midi_track" + (
                    "_with_note" if plan.get("wants_note") else ""
                )
                result.advisory_rationale = (
                    "Host operation plan: steps=%d" % len(plan["execution_steps"])
                )
                result._mcp_plan = plan  # type: ignore[attr-defined]
                return result

            # ---- resolve intent to concept ----
            concept, direction, refusal, explicit = self._resolve_concept(request)
            direction = self._record_resolution(result, request, direction, refusal, explicit)
            result.resolved_concept = concept
            result.semantic_direction = direction.value if direction else None

            if refusal is not None:
                result.refusal = refusal.to_dict()
                result.error = refusal.reason
                result.execution_status = "REFUSED_UNKNOWN_CONCEPT"   # legacy status kept for compatibility
                return result
            if concept is None:
                result.error = (
                    "No semantic concept resolved from intent %r. "
                    "Supply an explicit canonical target (request.semantic_target)." % request.user_intent
                )
                result.execution_status = "REFUSED_UNKNOWN_CONCEPT"
                return result
            explicit_target = explicit.registry_target if explicit is not None else None

            # ---- retrieve real knowledge (Phase B) ----
            knowledge_contributions, knowledge_notes = self._retrieve_knowledge(
                request.user_intent, concept,
                advisory_context=request.advisory_context,
            )
            result.retrieved_knowledge = knowledge_contributions

            # Brain V2 P2: make context-aware retrieval visible in the
            # reasoning trace regardless of which route the concept takes
            # below (both the early MCP-bridge exit and the full Serum
            # route read/overwrite this). Honest either way: reports zero
            # matched dimensions plainly rather than omitting the note.
            matched_dims = sorted({
                kc.matched_via_dimension for kc in knowledge_contributions
                if kc.matched_via_dimension
            })
            result.advisory_rationale = (
                "Retrieved %d knowledge items (context dimensions matched: %s)"
                % (len(knowledge_contributions), matched_dims)
                if matched_dims else
                "Retrieved %d knowledge items (no context dimension matched; "
                "primary intent-text query only)" % len(knowledge_contributions)
            )

            # ---- determine semantic target ----
            target_mapping = self._mapping_for(concept)
            if target_mapping is None and request.semantic_target is None and explicit_target is None:
                # STEP 7: before refusing, check MCP-only concept bridge
                if concept in _MCP_CONCEPT_BRIDGE:
                    mcp_target = _MCP_CONCEPT_BRIDGE[concept]
                    result.execution_route = ExecutionRoute.ABLETON_MCP.value
                    result.route_rationale = "MCP bridge (no Serum route): %r → %s" % (
                        concept, mcp_target
                    )
                    return self._run_mcp_path(result, request, mcp_target, concept=concept)
                result.error = (
                    "Universal concept %r has no UNIVERSAL_TO_SEMANTIC mapping "
                    "and no MCP bridge entry. No execution path available." % concept
                )
                result.execution_status = "REFUSED_NO_MAPPING"
                return result

            capability_target = (
                target_mapping.semantic_target if target_mapping else None
            )
            semantic_target_name = explicit_target or request.semantic_target or _capability_to_semantic_name(
                capability_target
            )
            result.semantic_target = semantic_target_name or capability_target

            # ---- route selection (Phase F) ----
            lookup_name = semantic_target_name or capability_target or "unknown"
            route_decision = self._selector.select_route(lookup_name)
            result.execution_route = route_decision.route.value
            result.route_rationale = route_decision.rationale

            # ---- build intent model ----
            intent = UniversalProductionIntent(
                original_user_request=request.user_intent,
                target_concept=concept,
                semantic_direction=direction,
                musical_objective=request.musical_context or (
                    "Producer operation: %s %s" % (direction.value, concept)
                ),
            )

            # ---- retrieve prior episodes (Phase K) ----
            episode_contributions, episode_ids = self._retrieve_episodes(
                semantic_target=capability_target or lookup_name,
                intent=request.user_intent,
            )
            result.prior_episodes = episode_contributions

            # ---- advisory chain (Phase D) ----
            candidate, decision, confidence = self._build_advisory_chain(
                intent, concept, episode_ids, knowledge_notes, episode_contributions
            )
            result.candidate_operations = [
                "%s %s" % (candidate.operation, concept)
            ]
            result.selected_operation = "%s %s (confidence=%.2f)" % (
                candidate.operation, concept, confidence
            )
            k_ids = list(knowledge_notes.keys())
            result.advisory_rationale += (
                " | ids=%s. Prior episodes=%s. Confidence=%.2f" % (
                    k_ids[:3], episode_ids, confidence,
                )
            )

            # ---- MCP bridge: reroute MCP-only concepts (STEP 7) ----
            if concept in _MCP_CONCEPT_BRIDGE and route_decision.route != ExecutionRoute.DAWDREAMER_SERUM:
                # Force MCP route for concepts only in the MCP bridge
                result.execution_route = ExecutionRoute.ABLETON_MCP.value
                result.route_rationale = "MCP bridge: %r → %s" % (concept, _MCP_CONCEPT_BRIDGE[concept])
                return self._run_mcp_path(result, request,
                                          _MCP_CONCEPT_BRIDGE[concept], concept=concept)

            # ---- execute by route ----
            if route_decision.route == ExecutionRoute.REFUSE:
                result.execution_status = "REFUSED_NO_EVIDENCE"
                result.error = route_decision.rationale
                return result

            if route_decision.route == ExecutionRoute.DAWDREAMER_SERUM:
                return self._run_serum_preset_path(
                    result, request, intent, candidate, decision,
                    capability_target,
                )

            if route_decision.route == ExecutionRoute.ABLETON_MCP:
                return self._run_mcp_path(result, request, semantic_target_name, concept=concept)

        except Exception as exc:
            result.error = "%s: %s" % (type(exc).__name__, exc)
            result.execution_status = "BRAIN_ERROR"

        return result

    # ------------------------------------------------------------------
    # RECREATE_REFERENCE mode (STEP 8)
    # ------------------------------------------------------------------
    def _execute_recreate_reference(
        self, request: "ProducerRequest", result: "ProducerResult"
    ) -> "ProducerResult":
        """Execute RECREATE_REFERENCE mode.

        Pipeline:
          1. If source_url provided: ingestion result already stored in rationale
          2. Retrieve knowledge for the intent
          3. Interpret sonic objectives (via concept resolution)
          4. Build candidate operations (same as EXECUTE)
          5. Execute the best-admitted operation
          6. Classify: RECREATED / PARTIALLY_RECREATED / BLOCKED / INSUFFICIENT_EVIDENCE
        """
        concept, direction, refusal, _explicit = self._resolve_concept(request)
        direction = self._record_resolution(result, request, direction, refusal, _explicit)
        result.resolved_concept = concept
        result.semantic_direction = direction.value if direction else None

        if refusal is not None:
            result.refusal = refusal.to_dict()
            result.error = refusal.reason
            result.execution_status = "REFUSED_UNKNOWN_CONCEPT"
            return result

        if concept is None:
            result.execution_status = "BLOCKED"
            result.error = (
                "RECREATE_REFERENCE: no concept resolved from %r; "
                "provide more specific intent or semantic_target." % request.user_intent
            )
            return result

        knowledge_contributions, knowledge_notes = self._retrieve_knowledge(
            request.user_intent, concept
        )
        result.retrieved_knowledge = knowledge_contributions

        if not knowledge_contributions:
            result.execution_status = "INSUFFICIENT_EVIDENCE"
            result.error = "RECREATE_REFERENCE: no knowledge items found for concept %r" % concept
            return result

        # Delegate to standard EXECUTE path (reuse all authority layers)
        request_exec = ProducerRequest(
            user_intent=request.user_intent,
            semantic_target=request.semantic_target,
            musical_context=request.musical_context,
            mode="EXECUTE",
        )
        exec_result = self.execute(request_exec)

        # Classify based on execution outcome
        if exec_result.execution_status == "EXECUTED" and exec_result.decision == "ACCEPTED":
            recreate_status = "RECREATED"
        elif exec_result.execution_status == "MCP_PLAN_READY":
            recreate_status = "PARTIALLY_RECREATED"
        elif exec_result.execution_status in ("REFUSED_NO_CONTRACT", "REFUSED_ADMISSION",
                                               "REFUSED_NO_EVIDENCE", "DISCOVERABLE"):
            recreate_status = "BLOCKED"
        else:
            recreate_status = "INSUFFICIENT_EVIDENCE"

        # Merge exec result into this result
        result.semantic_target = exec_result.semantic_target
        result.execution_route = exec_result.execution_route
        result.route_rationale = exec_result.route_rationale
        result.resolution_status = exec_result.resolution_status
        result.admitted = exec_result.admitted
        result.admission_reason = exec_result.admission_reason
        result.baseline_db = exec_result.baseline_db
        result.treatment_db = exec_result.treatment_db
        result.delta_db = exec_result.delta_db
        result.decision = exec_result.decision
        result.episode_id = exec_result.episode_id
        result.prior_episodes = exec_result.prior_episodes
        result.execution_status = recreate_status
        result.advisory_rationale = (
            (result.advisory_rationale or "") +
            " | RECREATE_REFERENCE exec_status=%s inner_status=%s" % (
                recreate_status, exec_result.execution_status
            )
        )
        return result

    # ------------------------------------------------------------------
    # GENERIC STRUCTURED OPERATIONS (e.g. ADD_MODULATION_ROUTE)
    #
    # Distinct from the concept+direction path above: these operations carry
    # multiple structured runtime arguments (source/destination/amount/
    # bipolar) that don't fit UniversalProductionIntent's target_concept +
    # semantic_direction shape. Still goes through real Resolution (a scope
    # check against a qualified CapabilityContract's domain -- not a guess)
    # and real Admission (the unmodified 15.4 admission.admit() gate) before
    # any plan is produced. No operation reaches a plan by any other path.
    # ------------------------------------------------------------------
    _STRUCTURED_OPERATIONS = {"ADD_MODULATION_ROUTE"}

    def _run_structured_operation(self, result: ProducerResult, request: ProducerRequest) -> ProducerResult:
        if request.operation not in self._STRUCTURED_OPERATIONS:
            result.execution_status = "REFUSED_UNKNOWN_OPERATION"
            result.error = (
                "Unknown structured operation %r. Supported: %s"
                % (request.operation, sorted(self._STRUCTURED_OPERATIONS))
            )
            return result

        if request.operation == "ADD_MODULATION_ROUTE":
            return self._run_modulation_route_operation(result, request)

        result.execution_status = "REFUSED_UNKNOWN_OPERATION"
        return result

    def _run_modulation_route_operation(self, result: ProducerResult, request: ProducerRequest) -> ProducerResult:
        """ADD_MODULATION_ROUTE: source/destination/amount/bipolar are runtime
        data (evidence-derived, e.g. from visual interpretation), never
        hardcoded per-video values. amount/bipolar may legitimately be None
        ("not legible in the source evidence") -- that is preserved as None
        through resolution, admission, and the plan; never coerced into an
        invented number.
        """
        from serum2.producer.modulation_route_contract import CAPABILITY_TARGET
        from serum2.evidence import admission as admission_mod

        args = request.operation_args or {}
        source = args.get("source")
        destination = args.get("destination")
        amount = args.get("amount")      # may be None -- UNKNOWN, never guessed
        bipolar = args.get("bipolar")    # may be None -- UNKNOWN, never guessed

        result.resolved_concept = "modulation-route-add"
        result.semantic_target = CAPABILITY_TARGET

        if not source or not destination:
            result.execution_status = "REFUSED_MISSING_ARGUMENTS"
            result.error = "ADD_MODULATION_ROUTE requires source and destination (got source=%r destination=%r)" % (source, destination)
            return result

        contract = self._registry.get(CAPABILITY_TARGET)
        if contract is None:
            result.execution_status = "REFUSED_NO_CONTRACT"
            result.error = "No qualified contract for %r -- capability was never qualified" % CAPABILITY_TARGET
            return result

        # ---- Resolution (this producer-layer code, not frozen Step 6):
        # scope-check the RUNTIME source/destination against the QUALIFIED
        # domain using PRECISE indexed-range matching (a loose substring
        # match would wrongly accept e.g. "Envelope 7" just because it
        # starts with "env" -- env sources only go 0-3; caught live while
        # testing this exact operation). This is "RESOLVED", distinct from
        # "ADMITTED" below -- a candidate that fails this check never
        # reaches admission.admit() at all. ----
        from serum2.producer.qualify_modulation_route import (
            resolve_source_in_domain, resolve_destination_in_domain,
        )
        source_hit = resolve_source_in_domain(source)
        dest_hit = resolve_destination_in_domain(destination)

        if source_hit is None or dest_hit is None:
            result.resolution_status = "out_of_scope"
            result.execution_status = "REFUSED_OUT_OF_SCOPE"
            result.error = (
                "source=%r (resolved=%r) / destination=%r (resolved=%r) "
                "outside the qualified domain for %r. Qualified source families: %s. "
                "Qualified destination families: %s. REFUSED -- not a guess, "
                "not routed to any backend."
                % (source, source_hit, destination, dest_hit, CAPABILITY_TARGET,
                   contract.scope["supported_source_prefixes"],
                   contract.scope["supported_destination_families"])
            )
            return result

        result.resolution_status = "resolved"

        # ---- Admission: the REAL, unmodified 15.4 gate. required_causal
        # is correctly False here -- a topology/routing operation has no
        # before/after-dB causal shape to prove; STRUCTURAL_ONLY (construct
        # +persist+load verified) is the right and only tier this class of
        # operation can ever reach. ----
        contracts_dict = self._registry.get_contracts_dict()
        adm = admission_mod.admit(contracts_dict, CAPABILITY_TARGET, required_causal=False)

        if not adm.admitted:
            result.admitted = False
            result.admission_reason = adm.reason
            result.execution_status = "REFUSED_ADMISSION"
            result.error = adm.detail
            return result

        result.admitted = True
        result.admission_reason = adm.reason

        plan = {
            "status": "MODULATION_ROUTE_PLAN_READY",
            "operation": "ADD_MODULATION_ROUTE",
            "source": source, "destination": destination,
            "amount": amount, "bipolar": bipolar,
            "capability_target": CAPABILITY_TARGET,
            "resolver_operation_id": contract.execution_binding.resolver_operation_id,
            "execution_steps": [
                "1. serum-mcp edit_preset(spec) with mod_routes=[{source, destination, "
                "amount: <amount or a documented placeholder if amount is None>, bipolar}]",
                "2. record preset_path + sha256 of the written .SerumPreset",
                "3. Load the preset into the real Serum 2 instance via Serum's own "
                "in-plugin preset browser",
                "4. Read the real Serum MATRIX tab to confirm SOURCE/DESTINATION match "
                "and route count increased",
                "5. Call finalize_modulation_route_execution(plan, preset_path, "
                "preset_sha256, matrix_readback, readback_verified)",
            ],
        }
        result.execution_status = "MODULATION_ROUTE_PLAN_READY"
        result.advisory_rationale = (
            "ADD_MODULATION_ROUTE resolved+admitted: source=%r destination=%r "
            "amount=%r bipolar=%r (contract=%s status=%s)"
            % (source, destination, amount, bipolar, CAPABILITY_TARGET, contract.status)
        )
        result._modulation_route_plan = plan  # type: ignore[attr-defined]
        return result

    def finalize_modulation_route_execution(
        self,
        result: ProducerResult,
        *,
        preset_path: str,
        preset_sha256: str,
        matrix_readback: Dict[str, Any],
        readback_verified: bool,
    ) -> ProducerResult:
        """Record REAL observed serum-mcp + Serum-MATRIX execution evidence.
        Same seam shape as finalize_serum_preset_execution / finalize_mcp_execution
        -- requires the plan-ready state, requires a real hash, only then sets
        EXECUTED. A bare MODULATION_ROUTE_PLAN_READY must never be EXECUTED."""
        if result.execution_status != "MODULATION_ROUTE_PLAN_READY":
            raise ValueError(
                "finalize_modulation_route_execution() requires a result with "
                "execution_status == 'MODULATION_ROUTE_PLAN_READY' (got %r). "
                "This prevents finalizing a REFUSED result as EXECUTED."
                % result.execution_status
            )
        if not preset_sha256:
            raise ValueError(
                "preset_sha256 is required -- an empty hash would let a plan "
                "be marked EXECUTED without a real preset file ever existing."
            )

        result.serum_preset_execution = {
            "preset_path": preset_path,
            "preset_sha256": preset_sha256,
            "matrix_readback": matrix_readback,
            "readback_verified": readback_verified,
        }
        result.execution_status = "EXECUTED" if readback_verified else "EXECUTION_UNVERIFIED"
        result.decision = "ACCEPTED" if readback_verified else "REJECTED"
        return result

    def _run_serum_preset_path(
        self, result, request, intent, candidate, decision,
        capability_target,
    ) -> ProducerResult:
        """Canonical Serum execution route: resolution -> admission ->
        serum-mcp preset plan. See _build_serum_preset_plan's docstring for
        the full external flow (serum-mcp -> Serum UI load -> readback ->
        finalize_serum_preset_execution)."""
        contract = self._registry.get(capability_target)
        if contract is None:
            result.error = "No contract for capability target %r" % capability_target
            result.execution_status = "REFUSED_NO_CONTRACT"
            return result

        # Capability resolution + admission (Phase E)
        resolution, adm_req, adm = self._resolve_and_admit(candidate, intent, contract)
        result.resolution_status = resolution.resolution_status.value

        if resolution.resolution_status != ResolutionStatus.RESOLVED:
            result.execution_status = "REFUSED_RESOLUTION_FAILED"
            result.error = "6.6 resolution failed: %s" % resolution.refusal_reason
            return result

        if adm is None or not adm.admitted:
            result.admitted = False
            result.admission_reason = adm.admission_reason if adm else "handoff_failed"
            result.execution_status = "REFUSED_ADMISSION"
            return result

        result.admitted = True
        result.admission_reason = adm.admission_reason

        # Serum preset plan (Phase G) — see _build_serum_preset_plan's
        # docstring for why this stops at a plan rather than auto-executing.
        plan = self._build_serum_preset_plan(
            intent, candidate, decision, resolution, adm, contract,
        )

        if plan.get("status") == "NOT_ADMITTED":
            result.execution_status = "REFUSED_AUTHORITY"
            result.error = "Execution authority not granted: %s" % plan
            return result

        result.execution_status = "SERUM_PRESET_PLAN_READY"
        result.advisory_rationale += (
            " | Serum preset plan: target=%r value=%r contract_id=%r" % (
                plan.get("mutation_target_path"),
                plan.get("mutation_value_used"),
                plan.get("contract_id"),
            )
        )
        result._serum_preset_plan = plan  # type: ignore[attr-defined]
        return result

    def _run_mcp_path(
        self, result, request, semantic_target_name, concept: Optional[str] = None
    ) -> ProducerResult:
        """MCP path: compile intent → structured plan OR DISCOVERABLE status.

        STEP 5/9: For MCP-bridge concepts, resolves the semantic_target_name
        from _MCP_CONCEPT_BRIDGE then compiles the plan. When the target has
        no MCP_HOST_MAP entry, returns DISCOVERABLE instead of hard REFUSED.
        """
        # Resolve via MCP bridge when the brain resolved an MCP-only concept
        if concept and concept in _MCP_CONCEPT_BRIDGE and not semantic_target_name:
            semantic_target_name = _MCP_CONCEPT_BRIDGE[concept]

        plan = self._execute_mcp(request.user_intent, semantic_target_name or "")

        if plan.get("status") == "REFUSED":
            reason = plan.get("reason", "")
            # STEP 9: If the concept is recognized but just not in MCP_HOST_MAP,
            # return DISCOVERABLE instead of hard REFUSED.
            if reason in ("NO_MCP_MAPPING", "UNKNOWN_SEMANTIC_TARGET"):
                disc = self._make_discovery_request(
                    concept or "unknown",
                    semantic_target_name or plan.get("semantic_target", ""),
                )
                result.execution_status = "DISCOVERABLE"
                result.error = None
                result.advisory_rationale += (
                    " | DISCOVERABLE: %s" % disc["discovery_request"]["objective"]
                )
                result.resolution_status = "discoverable_no_mcp_mapping"
                result.admitted = False
                result.admission_reason = "DISCOVERY_REQUIRED"
                # Stash discovery details in a non-standard field for the caller
                result._discovery_request = disc  # type: ignore[attr-defined]
                return result
            result.execution_status = "REFUSED_MCP"
            result.error = "%s: %s" % (reason, plan.get("detail", ""))
            return result

        result.execution_status = "MCP_PLAN_READY"
        result.advisory_rationale += (
            " | MCP plan: host_param=%r index=%s track=%s device=%s steps=%d" % (
                plan.get("host_param_label"),
                plan.get("host_param_index"),
                plan.get("track_index"),
                plan.get("device_index"),
                len(plan.get("execution_steps", [])),
            )
        )
        # Admission for MCP path: MCP_HOST_MAP membership = admission
        result.admitted = True
        result.admission_reason = "MCP_HOST_MAP_QUALIFIED"
        result.resolution_status = "mcp_qualified"
        # Stash full plan for caller
        result._mcp_plan = plan  # type: ignore[attr-defined]
        return result

    # ------------------------------------------------------------------
    # REAL MCP EXECUTION FEEDBACK (closes the plan → real tool → readback loop)
    #
    # Python in this process cannot invoke mcp__AbletonMCP__* tools directly —
    # those exist only in the orchestrating agent's tool-calling layer, not as
    # an importable Python client (confirmed: no MCP socket/OSC client exists
    # in this repo; serum2/qualification/a3_mcp_executor.py's MCPControlExecutor
    # takes an injected mcp_session and stubs when None, same constraint).
    #
    # finalize_mcp_execution() is therefore the seam: the orchestrator executes
    # the REAL Ableton MCP tool calls per the plan this brain produced, then
    # feeds the REAL observed before/after/readback values back in. Only after
    # this call does execution_status become EXECUTED. A plan alone is never
    # sufficient — MCP_PLAN_READY without a finalize() call must never be
    # reported as EXECUTED by any caller.
    # ------------------------------------------------------------------
    def finalize_mcp_execution(
        self,
        result: ProducerResult,
        *,
        tool_calls: List[Dict[str, Any]],
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        readback_verified: bool,
    ) -> ProducerResult:
        """Record REAL observed Ableton MCP execution evidence on a result.

        Args:
            result: a ProducerResult previously returned with
                execution_status == "MCP_PLAN_READY" (has result._mcp_plan)
            tool_calls: ordered list of {"tool": name, "input": {...}, "output": {...}}
                dicts — the ACTUAL mcp__AbletonMCP__* calls made and their
                ACTUAL returned payloads (never fabricated)
            before_state: real state read back BEFORE mutation
            after_state: real state read back AFTER mutation (the readback proof)
            readback_verified: True iff after_state actually reflects the
                intended change (caller must have compared, not assumed)

        Returns:
            The same result object, mutated: execution_status="EXECUTED",
            mcp_execution populated, decision set from readback_verified.
        """
        if result.execution_status != "MCP_PLAN_READY":
            raise ValueError(
                "finalize_mcp_execution() requires a result with "
                "execution_status == 'MCP_PLAN_READY' (got %r). "
                "This prevents finalizing a REFUSED/DISCOVERABLE result as EXECUTED."
                % result.execution_status
            )
        if not tool_calls:
            raise ValueError(
                "tool_calls must contain at least one real MCP tool invocation. "
                "Empty tool_calls would let a plan be marked EXECUTED without "
                "any real MCP call ever happening."
            )

        result.mcp_execution = {
            "tool_calls": tool_calls,
            "before_state": before_state,
            "after_state": after_state,
            "readback_verified": readback_verified,
        }
        result.execution_status = "EXECUTED" if readback_verified else "EXECUTION_UNVERIFIED"
        result.decision = "ACCEPTED" if readback_verified else "REJECTED"
        return result

    # ------------------------------------------------------------------
    # REAL SERUM PRESET EXECUTION FEEDBACK
    #
    # Same seam shape as finalize_mcp_execution() above, for the OTHER real
    # route: this Python process cannot call mcp__serum-mcp__* or take a
    # screenshot of the real Serum UI either — those are orchestrating-agent
    # tools. The orchestrator generates the preset via serum-mcp, loads it
    # into the real Serum 2 instance through Serum's own in-plugin preset
    # browser, reads back the live UI, and feeds the REAL evidence in here.
    # Only after this call does execution_status become EXECUTED. A bare
    # SERUM_PRESET_PLAN_READY must never be reported as EXECUTED.
    # ------------------------------------------------------------------
    def finalize_serum_preset_execution(
        self,
        result: ProducerResult,
        *,
        preset_path: str,
        preset_sha256: str,
        ui_readback: Dict[str, Any],
        readback_verified: bool,
    ) -> ProducerResult:
        """Record REAL observed serum-mcp + Serum-UI execution evidence.

        Args:
            result: a ProducerResult previously returned with
                execution_status == "SERUM_PRESET_PLAN_READY"
                (has result._serum_preset_plan)
            preset_path: absolute path of the .SerumPreset serum-mcp wrote
            preset_sha256: sha256 of that file (never fabricated)
            ui_readback: real values read off the actual Serum UI (e.g. a
                screenshot-derived dict), never a planned/expected value
            readback_verified: True iff ui_readback actually matches the
                plan's mutation_target_path/mutation_value_used (caller
                must have compared, not assumed)

        Returns:
            The same result object, mutated: execution_status="EXECUTED",
            serum_preset_execution populated, decision set from
            readback_verified.
        """
        if result.execution_status != "SERUM_PRESET_PLAN_READY":
            raise ValueError(
                "finalize_serum_preset_execution() requires a result with "
                "execution_status == 'SERUM_PRESET_PLAN_READY' (got %r). "
                "This prevents finalizing a REFUSED result as EXECUTED."
                % result.execution_status
            )
        if not preset_sha256:
            raise ValueError(
                "preset_sha256 is required — an empty hash would let a plan "
                "be marked EXECUTED without a real preset file ever existing."
            )

        result.serum_preset_execution = {
            "preset_path": preset_path,
            "preset_sha256": preset_sha256,
            "ui_readback": ui_readback,
            "readback_verified": readback_verified,
        }
        result.execution_status = "EXECUTED" if readback_verified else "EXECUTION_UNVERIFIED"
        result.decision = "ACCEPTED" if readback_verified else "REJECTED"
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capability_to_semantic_name(capability_key: Optional[str]) -> Optional[str]:
    """Reverse-map capability key to a semantic target name for RouteSelector."""
    from serum2.compiler.targets import SEMANTIC_TARGETS
    if capability_key is None:
        return None
    for name, ref in SEMANTIC_TARGETS.items():
        if ref.capability_key == capability_key:
            return name
    return None


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_BRAIN: Optional[ProducerBrain] = None


def execute_producer_request(request: ProducerRequest) -> ProducerResult:
    """Canonical entry point. One brain, one decision flow.

    Args:
        request: ProducerRequest with user_intent and optional fields

    Returns:
        ProducerResult with full reasoning trace, execution evidence, episode
    """
    global _BRAIN
    if _BRAIN is None:
        _BRAIN = ProducerBrain()
    return _BRAIN.execute(request)
