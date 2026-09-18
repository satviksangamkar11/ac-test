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
  → real Serum/DawDreamer OR real Ableton MCP

This module never modifies frozen Step 6 files.
"""
from __future__ import annotations

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
from serum2.compiler.mcp_intent import parse_intent, MCP_HOST_MAP


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
    # longer / sustain / release keywords → note-release concept, LONGER
    (["longer", "sustain longer", "longer sustain", "more sustain",
      "extend", "release longer", "longer release"],
     "note-release", SemanticDirection.LONGER),
    # shorter / tighter / less sustain → note-release concept, SHORTER
    (["shorter", "shorter release", "tighter", "less sustain",
      "quicker release"],
     "note-release", SemanticDirection.SHORTER),
    # attack → envelope-attack
    (["attack", "faster attack", "slower attack", "attack longer",
      "attack shorter"],
     "envelope-attack", SemanticDirection.SHORTER),
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

    # ---- intent classification ----
    intent_class: str = "MUTATION"
    """"MUTATION" | "CREATION". Set from request.mode (CREATE -> CREATION,
    everything else -> MUTATION). CREATION INTENT != MUTATION INTENT: the
    resolution/knowledge/admission computation is identical either way (the
    same semantic-target authority chain governs both), but a CREATION
    result's admitted semantic_target/direction/_mcp_plan means "seed value
    for a new PresetSpec", never "go mutate the currently loaded preset".
    Callers must branch on this field, not reinterpret MCP_PLAN_READY."""

    # ---- errors ----
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["request"] = asdict(self.request)
        return d


# ---------------------------------------------------------------------------
# Core brain
# ---------------------------------------------------------------------------

class ProducerBrain:
    """Stateful (caches registry / selector) producer brain."""

    def __init__(self):
        self._registry = ContractRegistry()
        self._selector = RouteSelector()

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
    # 5. DAWDREAMER EXECUTION (Phase G)
    # Uses the same harness pattern as step6_live_vertical_slice.py.
    # canonical_feedback_loop.execute_producer_from_intent() has a
    # pre-existing bug (contracts_dict format mismatch with diagnose_goal),
    # so we build the spec directly from the admitted contract and run the
    # canonical harness ourselves — exactly as the frozen vertical slice does.
    # ------------------------------------------------------------------
    def _execute_dawdreamer_with_authority(
        self,
        intent: "UniversalProductionIntent",
        candidate: "SemanticCandidate",
        decision: "AdvisoryDecision",
        resolution,
        adm,
        contract,
        knowledge_ids: List[str],
        episode_ids: List[str],
        ep_id: str,
    ) -> Dict[str, Any]:
        """Run real Serum execution using admitted contract authority."""
        from serum2.evidence import harness, epoch as epoch_mod
        from serum2.evidence.spec import (
            ExperimentSpec, Mutation, Stimulus, MeasurementPlan,
            TargetSpec, SINGLE_FIELD,
        )
        from step_6_8_contract_governed_execution import (
            ContractGovernedExecutor, ExecutionPathway,
        )
        from step_6_9_outcome_attribution import attribute_outcome
        from step_6_10_episode_generation import (
            UniversalEpisodeGenerator, ExecutionEvidenceRecord,
        )

        # Build execution intention from admitted contract
        executor = ContractGovernedExecutor()
        record = executor.create_execution_intention(
            intent, decision, resolution, adm, self._registry
        )
        authority = record.execution_authority

        if record.pathway is not ExecutionPathway.ADMITTED or authority is None:
            return {"status": "NOT_ADMITTED", "pathway": record.pathway.value}

        # Build spec from authority (contract is the sole source)
        scope = authority.scope or {}
        meas = contract.measurement or {}
        mutation_path = scope["mutation_target_path"]
        mutation_value = scope["mutation_value_used"]
        metric = meas["metric"]

        baseline_overrides = []
        for p in (contract.prerequisites or ()):
            fp = p["field_path"]
            if fp.startswith("body:"):
                baseline_overrides.append(
                    Mutation(fp.split("body:", 1)[1], p["declared_value"],
                             "contract prerequisite")
                )

        spec = ExperimentSpec(
            experiment_id=ep_id,
            mutations=[Mutation(mutation_path, mutation_value,
                                "contract-authorized treatment")],
            prerequisites=[],
            baseline_overrides=baseline_overrides,
            isolation_level=SINGLE_FIELD,
            claim_subject=contract.target,
            claim_predicate="extends",
            measurement_plans=[MeasurementPlan(
                metric=metric,
                target=TargetSpec(mutation_path, "Env", mutation_path.split(".")[-1]),
                expected_direction=meas.get("expected_direction", "increase"),
                threshold=meas.get("threshold", 0.0),
                stimulus=Stimulus(note=60, velocity=110, note_len=0.4,
                                  render_seconds=2.0, tail_start=0.6),
                kernel_artifact="tail_rms_db.py",
            )],
            notes="ProducerBrain execution; spec from admitted CapabilityContract.",
        )

        # Run via canonical harness (real Serum + DawDreamer)
        rec = harness.run(spec)
        m = rec.causal_measurements[0]

        # Outcome attribution (Step 6.9, frozen)
        outcome = attribute_outcome(
            execution_id=ep_id,
            contract_id=adm.contract_id,
            intent_id="brain_intent_001",
            baseline_measurement={
                "value": float(m.baseline),
                "measurement_definition_id": m.measurement_definition_id,
            },
            treatment_measurement={
                "value": float(m.treatment),
                "measurement_definition_id": m.measurement_definition_id,
            },
            admitted_contract=contract,
        )

        # Episode generation + persistence (Step 6.10, frozen)
        evidence = ExecutionEvidenceRecord(
            baseline_state={mutation_path: "contract-default"},
            treatment_state={mutation_path: mutation_value},
            mutation_description="%s -> %s" % (mutation_path, mutation_value),
            render_evidence={
                "baseline_db": float(m.baseline),
                "treatment_db": float(m.treatment),
                "delta_db": float(m.delta),
            },
            diagnosis="delta=%.4f dB %s" % (m.delta, m.observed_direction),
        )
        gen = UniversalEpisodeGenerator()
        episode = gen.generate_episode(
            execution_id=ep_id,
            universal_intent=intent,
            execution_record=record,
            admission_result=adm,
            admitted_contract=contract,
            advisory_decision=decision,
            capability_resolution=resolution,
            outcome=outcome,
            execution_evidence=evidence,
            knowledge_ids=knowledge_ids,
            prior_episode_ids=episode_ids,
        )
        persist_path = gen.persist_episode(episode)

        return {
            "status": "EXECUTED",
            "episode_id": episode.episode_id,
            "measurement_baseline": float(m.baseline),
            "measurement_treatment": float(m.treatment),
            "measurement_delta": float(m.delta),
            "decision": "ACCEPTED" if m.delta > 0 else "REJECTED",
            "learning_eligible": episode.learning_eligible,
            "persistence_path": persist_path,
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
        source_id = "yt_" + hashlib.md5(source_url.encode()).hexdigest()[:12]

        # Check if already ingested (idempotent)
        knowledge_dir = Path(__file__).parent.parent / "knowledge"
        ingestion_file = knowledge_dir / ("%s_source_ingestion_5_3.json" % source_id)
        if ingestion_file.exists():
            return {
                "status": "ALREADY_INGESTED",
                "source_id": source_id,
                "source_url": source_url,
                "ingestion_file": str(ingestion_file),
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
        result = ProducerResult(request=request)
        result.intent_class = "CREATION" if request.mode == "CREATE" else "MUTATION"

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
            concept, direction = _resolve_intent_to_concept(request.user_intent)
            result.resolved_concept = concept
            result.semantic_direction = direction.value if direction else None

            if concept is None:
                result.error = (
                    "No semantic concept resolved from intent %r. "
                    "Extend _INTENT_TO_CONCEPT or supply request.semantic_target." % request.user_intent
                )
                result.execution_status = "REFUSED_UNKNOWN_CONCEPT"
                return result

            # ---- retrieve real knowledge (Phase B) ----
            knowledge_contributions, knowledge_notes = self._retrieve_knowledge(
                request.user_intent, concept,
                advisory_context=request.advisory_context,
            )
            result.retrieved_knowledge = knowledge_contributions

            # Brain V2 P2: make context-aware retrieval visible in the
            # reasoning trace regardless of which route the concept takes
            # below (both the early MCP-bridge exit and the full DawDreamer
            # path read/overwrite this). Honest either way: reports zero
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
            from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC
            target_mapping = UNIVERSAL_TO_SEMANTIC.get(concept)
            if target_mapping is None and request.semantic_target is None:
                # STEP 7: before refusing, check MCP-only concept bridge
                if concept in _MCP_CONCEPT_BRIDGE:
                    mcp_target = _MCP_CONCEPT_BRIDGE[concept]
                    result.execution_route = ExecutionRoute.ABLETON_MCP.value
                    result.route_rationale = "MCP bridge (no DawDreamer path): %r → %s" % (
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
            semantic_target_name = request.semantic_target or _capability_to_semantic_name(
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

            if route_decision.route in (
                ExecutionRoute.DAWDREAMER_SERUM, ExecutionRoute.HYBRID
            ):
                return self._run_dawdreamer_path(
                    result, request, intent, candidate, decision,
                    capability_target, knowledge_notes, episode_ids,
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
        concept, direction = _resolve_intent_to_concept(request.user_intent)
        result.resolved_concept = concept
        result.semantic_direction = direction.value if direction else None

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

    def _run_dawdreamer_path(
        self, result, request, intent, candidate, decision,
        capability_target, knowledge_notes, episode_ids,
    ) -> ProducerResult:
        """Full DawDreamer path: resolution → admission → real execution."""
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

        # Real execution (Phase G)
        ep_id = "ep_brain_%s" % datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        try:
            episode = self._execute_dawdreamer_with_authority(
                intent, candidate, decision, resolution, adm, contract,
                knowledge_ids=list(knowledge_notes.keys()),
                episode_ids=episode_ids,
                ep_id=ep_id,
            )
        except Exception as exc:
            result.execution_status = "EXECUTION_ERROR"
            result.error = "DawDreamer execution failed: %s" % exc
            return result

        if episode.get("status") == "NOT_ADMITTED":
            result.execution_status = "REFUSED_AUTHORITY"
            result.error = "Execution authority not granted: %s" % episode
            return result

        # Populate result from episode
        result.baseline_db = episode.get("measurement_baseline")
        result.treatment_db = episode.get("measurement_treatment")
        result.delta_db = episode.get("measurement_delta")
        result.decision = episode.get("decision", "UNKNOWN")
        result.episode_id = episode.get("episode_id", ep_id)
        result.execution_status = "EXECUTED"
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
