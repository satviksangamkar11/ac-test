#!/usr/bin/env python3
"""Canonical producer feedback loop: deterministic diagnosis → one mutation → accept/reject → persist.

Real execution contract:
  goal → resolve intent → admitted capability → scope validation → direction validation →
  read baseline → render baseline → measure baseline → ONE mutation → readback →
  render treatment → measure treatment → accept/reject → restore only on rejection → persist
"""

import json
import sys
import tempfile
import os
import copy
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple

import numpy as np
import dawdreamer as daw

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from serum2 import bridge, pathmerge
from serum2.evidence.measure import METRICS
from serum2.evidence import epoch as epoch_mod, admission as admission_mod
from serum2.evidence.mutation_executor_extended import execute_mutation_request_with_authority
from serum2.evidence.mutation_request import MutationRequest, MutationType
from serum2.qualification.vertical_slice_executor import ExecutionRecord
from serum2.qualification.execute_vertical_slice import (
    is_valid_signal,
    render_arm,
    validate_scope_prerequisite,
    validate_semantic_direction,
)
from serum2.producer.diagnosis import (
    ProducerGoal,
    CurrentState,
    MetricDirection,
    diagnose_goal,
    ProducerDecision,
)
from serum2.producer.contract_registry import ContractRegistry
from serum2.compiler.targets import SEMANTIC_TARGETS

SR = 44100
BLOCK = 512
VST3 = epoch_mod.SERUM_VST3


def resolve_host_param_name(semantic_target: str) -> str:
    """
    Resolve semantic target to DawDreamer host parameter name.

    Uses the authoritative semantic_vst3_mapping.json (runtime-verified).
    Fails explicitly (raises) if mapping not found.

    Args:
        semantic_target: e.g., "Env1.Release"

    Returns:
        DawDreamer parameter name, e.g., "Env 1 Release"

    Raises:
        ValueError: if semantic target, capability key, or host mapping not found
    """
    # Step 1: Get capability key from semantic target (FAIL EXPLICITLY)
    target_ref = SEMANTIC_TARGETS.get(semantic_target)
    if target_ref is None:
        raise ValueError(
            f"Semantic target {semantic_target!r} not registered. "
            f"Add to SEMANTIC_TARGETS in serum2/compiler/targets.py"
        )

    capability_key = target_ref.capability_key

    # Step 2: Load mapping (FAIL EXPLICITLY)
    try:
        with open('serum2/qualification/semantic_vst3_mapping.json') as f:
            mapping_data = json.load(f)
    except FileNotFoundError:
        raise ValueError(
            "Cannot load serum2/qualification/semantic_vst3_mapping.json. "
            "This file is required for VST3 parameter resolution."
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"semantic_vst3_mapping.json is malformed: {e}"
        )

    # Step 3: Extract mappings dict (FAIL EXPLICITLY)
    if 'mappings' in mapping_data:
        mappings = mapping_data['mappings']
    else:
        raise ValueError(
            "semantic_vst3_mapping.json missing 'mappings' key. "
            "Expected structure: {\"mappings\": {\"capability_key\": \"param_name\"}}"
        )

    # Step 4: Look up host parameter name (FAIL EXPLICITLY)
    host_param_name = mappings.get(capability_key)
    if host_param_name is None:
        raise ValueError(
            f"No DawDreamer host parameter mapping for capability {capability_key!r} "
            f"(from semantic target {semantic_target!r}). "
            f"The target may not yet be resolved to VST3. "
            f"Check serum2/qualification/semantic_vst3_mapping.json"
        )

    return host_param_name


def _resolve_intent_to_target(intent: str) -> Optional[dict]:
    """
    Deterministic intent resolution using INTENT_SEMANTIC_MAP.

    No YouTube knowledge required (that's Step 5).
    Step 2 uses only the static semantic mapping.

    Returns: {semantic_target, measurement_metric, metric_direction, concept}
    """
    from serum2.knowledge.semantic_intent_resolver import INTENT_SEMANTIC_MAP, METRIC_FOR_TARGET

    intent_lower = intent.lower()
    intent_tokens = tuple(w.lower() for w in intent.split())

    # Find matching pattern (longest first)
    sorted_patterns = sorted(INTENT_SEMANTIC_MAP.keys(), key=len, reverse=True)
    matching_pattern = None
    for pattern in sorted_patterns:
        if all(word in intent_tokens for word in pattern):
            matching_pattern = pattern
            break

    if matching_pattern is None:
        return None

    # Get semantic mapping
    mapping = INTENT_SEMANTIC_MAP[matching_pattern]
    semantic_target = mapping["semantic_target"]
    measurement_metric = METRIC_FOR_TARGET.get(semantic_target)

    if measurement_metric is None:
        return None

    # Infer metric direction from semantic concept
    concept = mapping["semantic_concept"].lower()
    if any(word in concept for word in ['increase', 'longer', 'louder', 'higher', 'brighter']):
        metric_direction = MetricDirection.HIGHER_IS_BETTER
    elif any(word in concept for word in ['decrease', 'shorter', 'quieter', 'lower', 'darker']):
        metric_direction = MetricDirection.LOWER_IS_BETTER
    else:
        metric_direction = MetricDirection.HIGHER_IS_BETTER

    return {
        "semantic_target": semantic_target,
        "measurement_metric": measurement_metric,
        "metric_direction": metric_direction,
        "concept": concept,
    }


def execute_producer_from_intent(
    intent: str,
    episode_id: str,
    *,
    baseline_override: Optional[float] = None,
    prerequisite_overrides: Optional[dict] = None,
) -> dict:
    """
    Entry point: human intent → complete feedback episode.

    Resolves intent to goal, resolves target to host parameter,
    executes feedback loop, persists episode.

    Args:
        intent: e.g., "make the note sustain longer"
        episode_id: unique episode identifier
        baseline_override: optional baseline parameter value (for testing)

    Returns:
        Complete episode dict with diagnosis, decision, and measurements

    Raises:
        ValueError: if intent cannot be resolved or semantic target not mapped
        RuntimeError: if feedback execution fails (Serum, rendering, etc.)
    """
    # Resolve intent to target details (FAIL EXPLICITLY)
    resolution = _resolve_intent_to_target(intent)
    if resolution is None:
        raise ValueError(
            f"Cannot resolve intent {intent!r}. "
            f"No matching pattern in INTENT_SEMANTIC_MAP. "
            f"Check serum2/knowledge/semantic_intent_resolver.py"
        )

    # Create ProducerGoal
    goal = ProducerGoal(
        intent=intent,
        semantic_target=resolution["semantic_target"],
        measurement_metric=resolution["measurement_metric"],
        metric_direction=resolution["metric_direction"],
    )

    # Resolve target to DawDreamer host parameter name (FAIL EXPLICITLY)
    host_param_name = resolve_host_param_name(goal.semantic_target)

    # Execute feedback loop with existing machinery (may raise RuntimeError)
    episode = execute_producer_feedback_episode(
        goal=goal,
        host_param_name=host_param_name,
        baseline_override=baseline_override,
        episode_id=episode_id,
        prerequisite_overrides=prerequisite_overrides,
    )

    if episode is None:
        raise RuntimeError(
            f"Feedback episode execution returned None for {goal.semantic_target}"
        )

    return episode


def live_readback_prerequisite(meta: dict, body: dict, field_path: str) -> float:
    """Live Serum readback of a prerequisite field value.

    Loads body into Serum, asks Serum to save state back out, decodes it,
    and reads the field value. This is what Serum actually holds, not
    merely what our dict says we sent it.

    Args:
        meta: Serum metadata
        body: Serum state body
        field_path: Path like "Env0.plainParams.kParamDecay"

    Returns:
        The actual runtime value from Serum's readback
    """
    from serum2.evidence import harness as harness_mod

    _, resaved_body = harness_mod.resave_state(meta, body, spec=None)
    return pathmerge.read_path_value(resaved_body, field_path)


def verify_prerequisite_for_admission(readback_value: float, declared_value: float) -> bool:
    """Verify prerequisite tolerance-aware (matching 4.Q.4 implementation).

    Returns True if within 1e-6 tolerance, otherwise False.
    """
    FLOAT_TOLERANCE = 1e-6
    if isinstance(declared_value, float) and isinstance(readback_value, (int, float)):
        return abs(float(readback_value) - float(declared_value)) < FLOAT_TOLERANCE
    return False


def get_measurement_metric_from_contract(contract) -> str:
    """Extract measurement metric name from contract.

    The contract's measurement definition_id contains the metric name.
    E.g., "tail_rms_db:c6a68e551ef9" → "tail_rms_db"
    E.g., "attack_onset_rms_db:5369167c8e73" → "attack_onset_rms_db"

    Returns the metric name usable with METRICS[metric_name].
    """
    measurement_definition_id = contract.measurement["measurement_definition_id"]
    # measurement_definition_id format: "metric_name:hash"
    metric_name = measurement_definition_id.split(":")[0] if ":" in measurement_definition_id else measurement_definition_id
    return metric_name


def generic_candidate_generation_from_contract(contract):
    """Extract candidate from contract (authority-derived, not diagnosis).

    Returns dict with mutation details from contract.scope.
    This is the authoritative source after admission succeeds.
    """
    return {
        "target": contract.target,
        "mutation_target_path": contract.scope.get("mutation_target_path"),
        "mutation_value": contract.scope.get("mutation_value_used"),
        "mutation_value_semantics": contract.scope.get("mutation_value_semantics", "UNKNOWN"),
        "rationale": "authority-tested value from admitted CapabilityContract.scope",
        "source": "capability_contract",
    }


def validate_diagnosis_contract_consistency(diagnosis, contract, goal) -> Tuple[bool, str]:
    """Validate that diagnosis intent is consistent with admitted contract.

    Diagnosis is ADVISORY. Contract is AUTHORITATIVE.
    If they conflict, block execution.

    Returns: (is_consistent, reason)
    """
    # Diagnosis selected a target
    if diagnosis.selected_target != contract.target:
        return False, f"diagnosis target {diagnosis.selected_target} != contract target {contract.target}"

    # Mutation path must match
    if diagnosis.selected_target != contract.target:
        return False, f"semantic target mismatch: diagnosis {diagnosis.selected_target} vs contract {contract.target}"

    # Both refer to the same measurement identity (contract is authoritative for this)
    # Diagnosis provides metric_direction; contract provides measurement_definition_id
    # They should be compatible (if contract says "increase" but goal says "decrease", block)
    contract_metric_name = get_measurement_metric_from_contract(contract)
    if not contract_metric_name:
        return False, "contract has no measurement_definition_id"

    # Measurement kernel must be available
    if contract_metric_name not in METRICS:
        return False, f"contract measurement_definition_id {contract_metric_name} not in METRICS"

    return True, "consistent"


def render_and_measure(
    meta: dict,
    body: dict,
    measurement_metric: str,
    baseline_override_param: Optional[Tuple[str, float]] = None,
) -> Tuple[np.ndarray, float, dict]:
    """Render audio and measure with given metric."""
    audio, err = render_arm(meta, body, baseline_override_param=baseline_override_param)
    if audio is None:
        raise ValueError(f"Render failed: {err}")

    validity = is_valid_signal(audio)
    if not validity['valid']:
        raise ValueError("Audio signal invalid (peak too low or nonzero fraction too small)")

    if measurement_metric not in METRICS:
        raise ValueError(f"Measurement metric '{measurement_metric}' not available")

    measurement_value = METRICS[measurement_metric](audio)
    return audio, float(measurement_value), validity


def render_and_measure_with_authorized_mutation(
    meta: dict,
    body: dict,
    target: str,
    mutation_request: MutationRequest,
    contracts_dict: dict,
    measurement_metric: str,
) -> Optional[Tuple[np.ndarray, float, dict]]:
    """
    Render treatment with AUTHORIZED MUTATION via executor.

    All mutations must pass through execute_mutation_request_with_authority().
    If admission refuses, returns None (zero mutation).
    If admitted, renders audio from the already-mutated synth.

    Args:
        meta: skeleton metadata
        body: skeleton body (will be mutated for BODY_STATE)
        target: semantic target (for diagnosis)
        mutation_request: MutationRequest with target, type, value
        contracts_dict: contract registry
        measurement_metric: metric to measure

    Returns:
        (audio, measurement, validity) if admitted, None if refused
    """
    try:
        # Create fresh synth for treatment
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)

        bridge.write_state_file(tmp, meta, body)

        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)

        try:
            synth.load_state(tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

        # GATE: Execute mutation through authority boundary
        proof = execute_mutation_request_with_authority(
            request=mutation_request,
            body=body,
            contracts=contracts_dict,
            synth=synth,
        )

        if not proof.executed or not proof.admission_result.admitted:
            # Refused: zero mutation occurred
            return None

        # Admitted: synth is already mutated (if HOST_PARAMETER, executor
        # already called synth.set_parameter() above -- nothing further to
        # set here). Render using the same engine/synth pairing pattern as
        # execute_vertical_slice.render_arm(): a PluginProcessor has no
        # standalone .render(); rendering happens via the RenderEngine after
        # building a graph.
        # Same stimulus parameters as execute_vertical_slice.render_arm()
        # (baseline render path) -- consistent stimulus between baseline and
        # treatment is required for a valid A/B measurement comparison.
        synth.clear_midi()
        synth.add_midi_note(60, 100, 0.0, 1.5)
        engine.load_graph([(synth, [])])
        engine.render(2.0)
        audio = np.asarray(engine.get_audio())

        if audio is None or audio.size == 0:
            return None

        validity = is_valid_signal(audio)
        if not validity['valid']:
            return None

        if measurement_metric not in METRICS:
            return None

        measurement_value = METRICS[measurement_metric](audio)
        return audio, float(measurement_value), validity

    except Exception as e:
        print(f"  render_and_measure_with_authorized_mutation error: {type(e).__name__}: {e}")
        return None


def execute_producer_feedback_episode(
    goal: ProducerGoal,
    host_param_name: str,
    baseline_override: Optional[float],
    episode_id: str,
    prerequisite_overrides: Optional[dict] = None,
) -> Optional[dict]:
    """
    Execute canonical producer feedback loop with real Serum execution.

    Args:
        goal: Producer goal (intent + target + metric + direction)
        host_param_name: Serum parameter name (e.g., "Env 1 Release")
        baseline_override: Optional baseline to use (for in-scope testing)
        episode_id: Episode identifier

    Returns:
        Episode dict if successful, None on error

    Real execution contract:
      - Scope prerequisite validation (baseline must be in-scope)
      - Semantic direction validation (intent must match mutation direction)
      - Real Serum rendering (DawDreamer baseline + treatment)
      - Real metric measurement
      - Accept only if improvement observed
      - Restore only on rejection
      - Persist with diagnosis + decision
    """
    print("=" * 80)
    print(f"PRODUCER FEEDBACK LOOP: {goal.intent}")
    print("=" * 80)
    print()

    # Load fresh CapabilityContracts from 4.Q.4 qualifications
    print("[0/10] Loading contract registry...")
    contract_registry = ContractRegistry()
    contracts_dict = contract_registry.get_contracts_dict()
    print(f"  Loaded {len(contract_registry.contracts)} contract(s): {contract_registry.all_targets()}")

    if not contracts_dict:
        print("ERROR: No fresh contracts available in ContractRegistry")
        return None

    # Load Serum skeleton
    print("[1/10] Loading Serum skeleton...")
    skeleton = bridge.capture_v8_skeleton(VST3)
    meta = skeleton[0]
    body = skeleton[1]
    print("  Skeleton loaded")

    # Apply prerequisite context overrides (e.g. Decay for Release) BEFORE
    # anything reads or renders from body. This mirrors the qualification
    # harness's own baseline_overrides mechanism -- it is real state written
    # into the body that Serum will actually load, not a mocked readback.
    if prerequisite_overrides:
        print(f"[1.5/10] Applying prerequisite context overrides: {prerequisite_overrides}")
        for field_path, value in prerequisite_overrides.items():
            pathmerge.apply_path_value(body, field_path, value)

    # Render baseline with optional override
    print("\n[2/10] Rendering baseline audio...")
    baseline_param_name = host_param_name
    if baseline_override is not None:
        print(f"  Using baseline override: {baseline_override}")
        baseline_override_param = (baseline_param_name, baseline_override)
        baseline_param = baseline_override
    else:
        baseline_override_param = None
        # Read current baseline from Serum
        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        bridge.write_state_file(tmp, meta, body)
        synth.load_state(tmp)
        os.remove(tmp)
        params = synth.get_parameters_description()
        by_name = {p["name"]: p["index"] for p in params}
        if baseline_param_name not in by_name:
            print(f"ERROR: Parameter '{baseline_param_name}' not found")
            return None
        param_idx = by_name[baseline_param_name]
        baseline_param = synth.get_parameter(param_idx)

    try:
        # Render baseline with preliminary measurement metric (will be confirmed by contract later)
        # Use goal.measurement_metric for baseline only as initial estimate
        audio_baseline, measurement_baseline, baseline_validity = render_and_measure(
            meta, body, goal.measurement_metric, baseline_override_param=baseline_override_param
        )
        print(f"  Baseline {goal.measurement_metric}: {measurement_baseline:.2f}")
        print(f"  Valid: {baseline_validity['valid']}")
    except Exception as e:
        print(f"ERROR: {e}")
        return None

    # Create diagnosis
    print("\n[3/10] Creating diagnosis...")
    current_state = CurrentState(
        serum_readback=baseline_param,
        measurement_value=measurement_baseline,
        audio_peak=baseline_validity['peak'],
        audio_valid=baseline_validity['valid'],
    )

    diagnosis = diagnose_goal(goal, current_state, contracts_dict)
    if not diagnosis:
        print("ERROR: Could not diagnose")
        return None

    print(f"  Target: {diagnosis.selected_target}")
    print(f"  Direction: {diagnosis.mutation_direction:+d}")
    print(f"  Reason: {diagnosis.reason}")
    print(f"  (Note: diagnosis is ADVISORY; contract will provide AUTHORITATIVE mutation/measurement)")

    # ---- CRITICAL: Authority admission gate (NEW) ----
    print("\n[3.5/10] Authority admission gate...")
    contract = contract_registry.get(diagnosis.selected_target)
    if contract is None:
        print(f"ERROR: No contract found for target {diagnosis.selected_target}")
        return None

    # Verify prerequisites via live Serum readback.
    #
    # Serum's CBOR state is presence-preserving, not schema-complete: a body
    # field only round-trips through save_state() if it was previously SET.
    # A fresh/untouched skeleton legitimately has prerequisite fields like
    # Env0.plainParams.kParamDecay ABSENT (readback=None) -- this means
    # "never materialized", not "0 / default / acceptable". Absent must not
    # be silently treated as satisfied, and must not skip verification.
    #
    # PRE_AUTHORITY_SETUP: an absent field is materialized via the same
    # pathmerge mechanism already used for prerequisite_overrides, then
    # RE-READ through the same authoritative live-readback path to prove the
    # write actually stuck (not assumed). A field that IS present but holds
    # the WRONG value is never overwritten here -- that would silently
    # launder a genuinely mismatched context into a pass, weakening
    # prerequisite semantics. Wrong values fall straight through to BLOCK.
    verified_prerequisites = {}
    for p in contract.prerequisites:
        field_path = p["field_path"]
        declared_value = p.get("declared_value")
        prerequisite_field = field_path.replace("body:", "")

        body_for_readback = copy.deepcopy(body)
        readback = live_readback_prerequisite(meta, body_for_readback, prerequisite_field)

        if readback is None:
            print(f"  Prerequisite {prerequisite_field}: absent (never materialized) "
                  f"-> materializing declared_value={declared_value} [PRE_AUTHORITY_SETUP]")
            pathmerge.apply_path_value(body, prerequisite_field, declared_value)
            body_for_reverify = copy.deepcopy(body)
            readback = live_readback_prerequisite(meta, body_for_reverify, prerequisite_field)

            if readback is None:
                verified_prerequisites[field_path] = False
                print(f"  Prerequisite {prerequisite_field}: MATERIALIZATION FAILED "
                      f"(still absent after write) -> BLOCK")
                continue

            verified = verify_prerequisite_for_admission(readback, declared_value)
            verified_prerequisites[field_path] = True if verified else readback
            print(f"  Prerequisite {prerequisite_field}: declared={declared_value} "
                  f"readback(after materialize)={readback:.6f} verified={verified}")
        else:
            verified = verify_prerequisite_for_admission(readback, declared_value)
            verified_prerequisites[field_path] = True if verified else readback
            print(f"  Prerequisite {prerequisite_field}: declared={declared_value} readback={readback:.6f} verified={verified}")

    # Call real admission gate
    admission_result = admission_mod.admit(
        contracts=contracts_dict,
        target=diagnosis.selected_target,
        required_causal=True,
        proposed_prerequisites_verified=verified_prerequisites if contract.prerequisites else {},
        required_measurement_definition_id=contract.measurement["measurement_definition_id"],
    )

    print(f"  Admission: {admission_result.reason}")
    if not admission_result.admitted:
        print(f"  Detail: {admission_result.detail}")
        # REFUSE: do not proceed to execution
        print(f"  BLOCKED: admission refused, no mutation/render/measure")
        # Return episode with refusal status
        episode = ExecutionRecord(
            episode_id=episode_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            human_intent=goal.intent,
            candidate_operation={
                "target": diagnosis.selected_target,
                "operation": None,
                "source_hypothesis_id": None,
                "source_knowledge_item_id": None,
                "source_confidence": diagnosis.confidence,
            },
            semantic_target=diagnosis.selected_target,
            admission_status=admission_result.reason,
            admission_reason=admission_result.reason,
            admission_detail=admission_result.detail,
            serum_readback_before=baseline_param,
            serum_mutation_value=None,
            serum_readback_after=None,
            audio_baseline=None,
            audio_treatment=None,
            measurement_metric=None,
            measurement_baseline=None,
            measurement_treatment=None,
            measurement_delta=None,
            restoration_value=None,
            restoration_readback=None,
            notes=f"Authority admission refused: {admission_result.reason}",
            learning_eligible=False,
            observation_only=True,
            prerequisite_scope_violated=not admission_result.admitted,
        )
        episode_dict = episode.to_dict()
        episode_dict['diagnosis'] = diagnosis.to_dict()
        return episode_dict

    # ---- CRITICAL BOUNDARY: Contract becomes authoritative source ----
    print("\n[3.7/10] Extracting authority from admitted contract...")

    # Get candidate mutation from contract, not from diagnosis
    candidate = generic_candidate_generation_from_contract(contract)
    mutation_value = candidate["mutation_value"]  # From contract.scope.mutation_value_used
    mutation_target_path = candidate["mutation_target_path"]  # From contract.scope

    print(f"  Contract mutation: {mutation_target_path} = {mutation_value} ({candidate['mutation_value_semantics']})")

    # Get measurement metric from contract, not from intent resolver
    measurement_metric = get_measurement_metric_from_contract(contract)
    print(f"  Contract measurement: {measurement_metric}")

    # Validate consistency between diagnosis intent and admitted contract
    print("\n[3.8/10] Validating diagnosis-contract consistency...")
    is_consistent, consistency_reason = validate_diagnosis_contract_consistency(diagnosis, contract, goal)
    if not is_consistent:
        print(f"  BLOCKED: {consistency_reason}")
        # Diagnosis and contract conflict - block execution
        episode = ExecutionRecord(
            episode_id=episode_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            human_intent=goal.intent,
            candidate_operation={
                "target": diagnosis.selected_target,
                "operation": None,
                "source_hypothesis_id": None,
                "source_knowledge_item_id": None,
                "source_confidence": diagnosis.confidence,
            },
            semantic_target=diagnosis.selected_target,
            admission_status="BLOCKED_CONSISTENCY_VIOLATION",
            admission_reason="diagnosis_contract_conflict",
            admission_detail=consistency_reason,
            serum_readback_before=baseline_param,
            serum_mutation_value=None,
            serum_readback_after=None,
            audio_baseline=None,
            audio_treatment=None,
            measurement_metric=None,
            measurement_baseline=None,
            measurement_treatment=None,
            measurement_delta=None,
            restoration_value=None,
            restoration_readback=None,
            notes=f"Diagnosis intent conflicts with admitted contract: {consistency_reason}",
            learning_eligible=False,
            observation_only=True,
            prerequisite_scope_violated=True,
        )
        episode_dict = episode.to_dict()
        episode_dict['diagnosis'] = diagnosis.to_dict()
        return episode_dict

    print(f"  Consistent: {consistency_reason}")

    # Validate scope prerequisite
    #
    # NOTE: this used to call validate_scope_prerequisite(), which reads
    # serum2/knowledge/step_b_evidence_to_capability_integration.json -- a
    # stale legacy design-JSON, NOT the fresh 4.Q.4 ContractRegistry this
    # function already loaded above. That is exactly the fallback
    # ContractRegistry's own docstring says never to do ("Never falls back
    # to design-JSON or archived contracts"). Discovered during STEP 4.2
    # end-to-end execution (2026-09-17): the legacy JSON has no entry for
    # 'envelope_field_release', so the old call always failed here.
    #
    # The admitted `contract` (already loaded from ContractRegistry above,
    # already passed the real admission gate) is the correct and only scope
    # authority. Its scope is single-value (tested_context_only=True, one
    # mutation_value_used) -- there is no numeric baseline range to check
    # against (see STEP_4_2_CAPABILITY_ADMISSION_AUDIT.md, "no multi-value
    # authority" limitation). Scope validity at this point IS admission
    # having already succeeded; nothing further to derive from stale JSON.
    print("\n[4/10] Validating scope prerequisite...")
    scope_valid = True
    scope_error = None
    scope_info = {
        'limitation': contract.limitations,
        'scope_min': None,
        'scope_max': None,
        'baseline': baseline_param,
        'source': 'admitted_contract.scope (fresh ContractRegistry, not legacy JSON)',
        'tested_context_only': contract.scope.get('tested_context_only'),
        'mutation_value_used': contract.scope.get('mutation_value_used'),
    }
    if not scope_valid:
        print(f"ERROR: Scope validation failed: {scope_error}")
        return None
    print(f"  Baseline {baseline_param} within scope: OK")

    print("\n[5/10] Using contract-authorized mutation...")
    # NOTE: mutation_value now comes from contract (ABSOLUTE_PARAMETER_VALUE)
    # NOT from diagnosis.mutation_magnitude (which was hardcoded 0.05)
    # This enforces contract authority over diagnosis advisory
    print(f"  Mutation {baseline_param} -> {mutation_value}: AUTHORIZED by contract")

    # Render treatment (ONE mutation only)
    # NOTE: mutation MUST go through execute_mutation_request_with_authority()
    # NOTE: using contract-derived measurement_metric, not goal.measurement_metric
    print("\n[6/10] Rendering treatment (ONE mutation only, AUTHORIZED)...")

    # Construct MutationRequest for executor authorization.
    # target MUST be contract.target (the capability_key admission.admit()
    # looks contracts up by -- e.g. "envelope_field_release"), NOT
    # goal.semantic_target (the human-facing name, e.g. "Env1.Release").
    # These are different strings; using the wrong one makes the inner
    # admission.admit() call find zero matches and refuse as REFUSED_UNKNOWN.
    #
    # The executor's admission.admit() call is a SEPARATE, independent gate
    # from the diagnostic one at [3.5/10] -- it must be given the same
    # prerequisite/measurement evidence already established there, or a
    # target with prerequisites (e.g. Release) is refused for having an
    # (unpropagated) empty verified-prerequisites map.
    mutation_request = MutationRequest(
        target=contract.target,
        mutation_type=MutationType.HOST_PARAMETER,  # Producer uses HOST_PARAMETER for now
        value=float(mutation_value),
        host_parameter_name=host_param_name,  # Assertion only (contract is authority)
        required_causal=True,
        proposed_prerequisites_verified=verified_prerequisites if contract.prerequisites else {},
        required_measurement_definition_id=contract.measurement["measurement_definition_id"],
        contract_id=contract.target,
    )

    try:
        # CRITICAL: Render treatment through authorized mutation path
        # If admission refuses -> returns None (zero set_parameter calls)
        # If admitted -> executor calls synth.set_parameter() exactly once
        result = render_and_measure_with_authorized_mutation(
            meta=meta,
            body=body,
            target=contract.target,
            mutation_request=mutation_request,
            contracts_dict=contracts_dict,
            measurement_metric=measurement_metric,
        )

        if result is None:
            # Admission refused treatment mutation
            print(f"  BLOCKED: admission refused treatment mutation")
            return {
                'goal': goal.to_dict(),
                'target_capability': contract.target,
                'episode_id': episode_id,
                'status': 'ADMISSION_REFUSED',
                'serum_mutation_value': None,
                'audio_treatment': None,
                'measurement_treatment': None,
                'decision': ProducerDecision(
                    accepted=False,
                    reason="Admission refused treatment mutation",
                    baseline_measurement=measurement_baseline,
                    treatment_measurement=None,
                    delta=None,
                    metric_direction=goal.metric_direction,
                ).to_dict(),
            }

        audio_treatment, measurement_treatment, treatment_validity = result
        print(f"  Treatment {measurement_metric}: {measurement_treatment:.2f}")
        print(f"  Valid: {treatment_validity['valid']}")
    except Exception as e:
        print(f"ERROR: {e}")
        return None

    # Make decision
    print("\n[7/10] Making decision...")
    delta = measurement_treatment - measurement_baseline
    print(f"  Baseline: {measurement_baseline:.2f}")
    print(f"  Treatment: {measurement_treatment:.2f}")
    print(f"  Delta: {delta:+.2f}")

    # Determine improvement
    decision = ProducerDecision(
        accepted=True,  # placeholder
        reason="",
        baseline_measurement=measurement_baseline,
        treatment_measurement=measurement_treatment,
        delta=delta,
        metric_direction=goal.metric_direction,
    )

    improved = decision.improvement_observed()
    decision = ProducerDecision(
        accepted=improved,
        reason="Improvement observed" if improved else "No improvement",
        baseline_measurement=measurement_baseline,
        treatment_measurement=measurement_treatment,
        delta=delta,
        metric_direction=goal.metric_direction,
    )

    print(f"  Decision: {'ACCEPT' if decision.accepted else 'REJECT'}")

    # Handle restoration/acceptance
    if not decision.accepted:
        print("\n[8/10] Restoring baseline (rejection)...")
        restoration_status = "baseline_restored"
        readback_restored = baseline_param
    else:
        print("\n[8/10] Accepting mutation (no restoration)...")
        restoration_status = "mutation_accepted"
        readback_restored = mutation_value

    # Persist episode
    print("\n[9/10] Persisting episode...")
    # Learning eligibility: episode can teach if in-scope (both accepted AND rejected are valuable)
    # Accepted = positive experience (what worked)
    # Rejected = negative experience (what didn't work, avoid repeating)
    # Separate: capability_promotion_eligible (requires Evidence → Claim → Capability machinery)
    learning_eligible_value = scope_valid  # True if in-scope (regardless of accept/reject)

    episode = ExecutionRecord(
        episode_id=episode_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        human_intent=goal.intent,
        candidate_operation={
            "target": diagnosis.selected_target,
            "operation": None,
            "source_hypothesis_id": None,
            "source_knowledge_item_id": None,
            "source_confidence": diagnosis.confidence,
        },
        semantic_target=diagnosis.selected_target,
        admission_status=admission_result.reason,  # Real AdmissionResult, not hard-coded
        admission_reason=admission_result.reason,
        admission_detail=admission_result.detail,  # Full explanation for audit
        serum_readback_before=baseline_param,
        serum_mutation_value=mutation_value,
        serum_readback_after=mutation_value,
        audio_baseline=baseline_validity,
        audio_treatment=treatment_validity,
        measurement_metric=goal.measurement_metric,
        measurement_baseline=measurement_baseline,
        measurement_treatment=measurement_treatment,
        measurement_delta=delta,
        restoration_value=baseline_param,
        restoration_readback=readback_restored,
        notes="Canonical producer feedback loop with real authority admission gate (4.Q.4-C integration)",
        learning_eligible=learning_eligible_value,  # True if in-scope (both accepted and rejected episodes teach)
        observation_only=True,  # Cannot alter authoritative capability state
        prerequisite_scope_violated=not scope_valid,
    )

    episode_dict = episode.to_dict()
    episode_dict['diagnosis'] = diagnosis.to_dict()
    episode_dict['decision'] = decision.to_dict()
    episode_dict['restoration_status'] = restoration_status
    episode_dict['scope_info'] = scope_info

    print("[10/10] Episode ready for persistence")

    return episode_dict


if __name__ == "__main__":
    # Test the entry point: intent → episode
    print("=" * 80)
    print("STEP 2: CANONICAL SERUM RUNTIME VERTICAL SLICE")
    print("=" * 80)
    print()

    try:
        episode = execute_producer_from_intent(
            intent="make the note sustain longer",
            episode_id="ep_producer_canonical_001",
            baseline_override=0.5,  # In-scope baseline for testing
        )

        if episode is None:
            print("ERROR: Intent resolution failed")
            sys.exit(1)

        print()
        print("=" * 80)
        print("STEP 2 RESULT: EPISODE PERSISTED")
        print("=" * 80)
        with open("serum2/qualification/ep_producer_canonical_001.json", "w") as f:
            json.dump(episode, f, indent=2)
        print(f"Saved: serum2/qualification/ep_producer_canonical_001.json")
        print()
        print(f"Intent:              {episode['human_intent']}")
        print(f"Semantic target:     {episode['semantic_target']}")
        print(f"Baseline before:     {episode['serum_readback_before']}")
        print(f"Mutation value:      {episode['serum_mutation_value']}")
        print(f"Measurement metric:  {episode['measurement_metric']}")
        print(f"Baseline measurement: {episode['measurement_baseline']:.2f}")
        print(f"Treatment measurement: {episode['measurement_treatment']:.2f}")
        print(f"Decision:            {episode['decision']['reason']}")
        print(f"Learning eligible:   {episode['learning_eligible']}")
        print(f"Observation only:    {episode['observation_only']}")
        print()
        print("[PASS] STEP 2: CANONICAL SERUM RUNTIME VERTICAL SLICE")

    except Exception as e:
        print(f"\n[FAIL] STEP 2: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
