"""P6: audio/text/visual grounding. P6.1 contract + structural validator are GREEN; derivation, resolution, adapters and
integration are strict-xfail RED and must flip (losing the marker) when implemented."""
import ast
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from serum2.producer import grounding as g
from serum2.producer.grounding import (
    AGREEMENT, AUDIO, CONFLICT, EPISODE_STATE, INSUFFICIENT, MAX_GROUNDED_CONFIDENCE, MEASURED, OBSERVED, RESOLVED, SINGLE_MODALITY,
    TRANSCRIPT, UNKNOWN, VISUAL, GroundedClaim, GroundingObservation, GroundingValidator,
)

V = GroundingValidator()
SUBJ = {"canonical_target_id": "env1.release", "aspect": "direction"}


def obs(oid="o1", modality=TRANSCRIPT, value="increase", conf=0.6, subject=None, **over):
    table = {
        TRANSCRIPT: dict(source={"kind": "transcript", "ref": "segments 12-14"}, timestamp={"start_sec": 10.0, "end_sec": 14.0},
                         observation={"text": "a bit more release"}, status=OBSERVED),
        VISUAL: dict(source={"kind": "frame", "ref": "frame_yt_00010000", "sha256": "ab" * 32}, timestamp={"start_sec": 10.0, "end_sec": 10.0},
                     observation={"control_id": "env1.release", "before": "15 ms", "after": "838 ms"}, status=OBSERVED),
        AUDIO: dict(source={"kind": "render", "ref": "sha256:abc", "method": "g8-basic-acoustic-v1"}, timestamp=None,
                    observation={"metric": "spectral_centroid_hz", "value": 3711.6, "unit": "Hz"}, status=MEASURED),
        EPISODE_STATE: dict(source={"kind": "episode", "ref": "vlp1_u8_HEEGN1"}, timestamp=None,
                            observation={"readback": "838 ms"}, status=OBSERVED),
    }
    base = table.get(modality, table[TRANSCRIPT])
    d = dict(observation_id=oid, modality=modality, subject=subject or SUBJ,
             interpretation={"kind": "direction", "value": value, "basis": "test"}, confidence=conf,
             uncertainty={"level": "MEDIUM"}, provenance={"recorded_by": "test"}, **base)
    d.update(over)
    return GroundingObservation(**d)


def unknown_obs(oid="u1", modality=AUDIO, reason="no render was produced"):
    return obs(oid, modality, status=UNKNOWN, confidence=0.0, interpretation=None,
               observation={"metric": "spectral_centroid_hz", "value": None},
               uncertainty={"level": "UNKNOWN", "reason": reason})


def claim(members, status=SINGLE_MODALITY, agreeing=(), conflicting=(), conf=0.6, resolution=None, subject=None, **over):
    mods = tuple(sorted({o.modality for o in members}))
    d = dict(claim_id="claim:1", subject=subject or SUBJ, observations=tuple(members), modalities=mods,
             agreement={"status": status, "agreeing_observation_ids": list(agreeing), "conflicting_observation_ids": [list(x) for x in conflicting]},
             confidence=conf, conflict_resolution=resolution, provenance={"recorded_by": "test"})
    d.update(over)
    return GroundedClaim(**d)


# ---- P6.1 contract ------------------------------------------------------------------------------------------------
def test_observation_has_exactly_the_specified_fields_and_no_authority_fields():
    assert set(GroundingObservation.__dataclass_fields__) == {
        "observation_id", "modality", "source", "timestamp", "subject", "observation", "interpretation", "status", "confidence",
        "uncertainty", "provenance", "advisory", "schema_version"}
    assert not g._FORBIDDEN & set(GroundingObservation.__dataclass_fields__)


def test_claim_has_no_winner_selected_action_or_authority_field():
    assert set(GroundedClaim.__dataclass_fields__) == {
        "claim_id", "subject", "observations", "modalities", "agreement", "confidence", "conflict_resolution", "provenance",
        "advisory", "schema_version"}
    for f in ("winner", "selected", "action", "command", "execute", "route", "binding", "capability", "admitted"):
        assert f not in GroundedClaim.__dataclass_fields__ and f not in GroundingObservation.__dataclass_fields__


def test_objects_are_frozen():
    with pytest.raises(Exception):
        obs().confidence = 1.0
    with pytest.raises(Exception):
        claim([obs()]).confidence = 1.0


@pytest.mark.parametrize("modality", [TRANSCRIPT, VISUAL, AUDIO, EPISODE_STATE])
def test_a_well_formed_observation_of_every_modality_is_valid(modality):
    assert V.validate_observation(obs(modality=modality)) == []


def test_an_unknown_measurement_is_a_valid_observation():
    assert V.validate_observation(unknown_obs()) == []


@pytest.mark.parametrize("over,code", [
    ({"advisory": False}, "OBSERVATION_NOT_ADVISORY"),
    ({"modality": "SMELL"}, "BAD_MODALITY"),
    ({"status": "GUESSED"}, "BAD_STATUS"),
    ({"source": {"kind": "transcript"}}, "NO_SOURCE"),
    ({"source": {}}, "NO_SOURCE"),
    ({"timestamp": None}, "TIMESTAMP_REQUIRED"),
    ({"timestamp": {"start_sec": 5.0, "end_sec": 1.0}}, "BAD_TIMESTAMP"),
    ({"timestamp": {"start_sec": -1.0, "end_sec": 1.0}}, "BAD_TIMESTAMP"),
    ({"subject": {"canonical_target_id": "env1.release"}}, "NO_SUBJECT_ASPECT"),
    ({"observation": {}}, "NO_OBSERVATION"),
    ({"interpretation": {"kind": "direction", "value": "up"}}, "INTERPRETATION_MALFORMED"),
    ({"confidence": 1.2}, "CONFIDENCE_OUT_OF_RANGE"),
    ({"confidence": True}, "CONFIDENCE_OUT_OF_RANGE"),
    ({"uncertainty": {}}, "BAD_UNCERTAINTY"),
    ({"provenance": {}}, "NO_PROVENANCE"),
])
def test_malformed_observation_is_rejected(over, code):
    assert code in V.validate_observation(obs(**over))


def test_source_time_evidence_needs_a_timestamp_but_audio_and_episode_state_may_be_untimed():
    assert "TIMESTAMP_REQUIRED" in V.validate_observation(obs(modality=VISUAL, timestamp=None))
    assert V.validate_observation(obs(modality=AUDIO, timestamp=None)) == []
    assert V.validate_observation(obs(modality=EPISODE_STATE, timestamp=None)) == []


def test_a_number_needs_a_real_measurement_with_a_method():
    fabricated = obs(modality=TRANSCRIPT, observation={"text": "brighter", "value": 3700.0})
    assert "NUMERIC_WITHOUT_MEASUREMENT" in V.validate_observation(fabricated)
    assert "MEASURED_WITHOUT_METHOD" in V.validate_observation(obs(modality=AUDIO, source={"kind": "render", "ref": "sha256:abc"}))
    assert "NUMERIC_WITHOUT_MEASUREMENT" in V.validate_observation(obs(modality=AUDIO, status=OBSERVED))


@pytest.mark.parametrize("over", [
    {"observation": {"metric": "spectral_centroid_hz", "value": 3711.6}},        # a number on an unknown
    {"interpretation": {"kind": "direction", "value": "up", "basis": "x"}},      # an interpretation of nothing
    {"confidence": 0.3},                                                           # confidence in nothing
])
def test_unknown_measurements_stay_unknown(over):
    assert "UNKNOWN_CARRIES_VALUE" in V.validate_observation(replace(unknown_obs(), **over))


def test_unknown_needs_a_stated_reason_and_unknown_uncertainty():
    assert "UNKNOWN_WITHOUT_REASON" in V.validate_observation(replace(unknown_obs(), uncertainty={"level": "UNKNOWN"}))
    assert "UNKNOWN_WITHOUT_REASON" in V.validate_observation(replace(unknown_obs(), uncertainty={"level": "HIGH", "reason": "x"}))


def test_smuggled_authority_or_action_field_is_rejected():
    d = obs().to_dict()
    d["action"] = "set env1.release 838 ms"
    assert "CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate_observation(d)
    d = obs().to_dict()
    d["interpretation"]["execute"] = True
    assert "CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate_observation(d)


# ---- claim structure: provenance is kept, conflicts are not silently settled --------------------------------------------
def test_well_formed_claims_are_valid():
    t, v = obs("t", TRANSCRIPT), obs("v", VISUAL)
    assert V.validate_claim(claim([t])) == []
    assert V.validate_claim(claim([t, v], AGREEMENT, agreeing=["t", "v"], conf=0.7)) == []
    assert V.validate_claim(claim([t, obs("v", VISUAL, value="decrease")], CONFLICT, conflicting=[["t"], ["v"]], conf=0.3)) == []
    assert V.validate_claim(claim([unknown_obs()], INSUFFICIENT, conf=0.0)) == []


def test_a_claim_cannot_drop_a_modality_from_its_provenance():
    t, v = obs("t", TRANSCRIPT), obs("v", VISUAL)
    assert "CLAIM_MODALITIES_MISMATCH" in V.validate_claim(claim([t, v], AGREEMENT, agreeing=["t", "v"], modalities=("TRANSCRIPT",)))
    assert "CLAIM_MODALITIES_MISMATCH" in V.validate_claim(claim([t, v], AGREEMENT, agreeing=["t", "v"], modalities=("AUDIO", "TRANSCRIPT", "VISUAL")))


def test_agreement_needs_two_distinct_modalities():
    a, b = obs("a", VISUAL), obs("b", VISUAL)
    assert "CLAIM_AGREEMENT_NEEDS_TWO_MODALITIES" in V.validate_claim(claim([a, b], AGREEMENT, agreeing=["a", "b"]))


def test_a_conflict_needs_two_sides_and_may_not_carry_a_resolution():
    t, v = obs("t", TRANSCRIPT), obs("v", VISUAL, value="decrease")
    assert "CLAIM_CONFLICT_WITHOUT_SIDES" in V.validate_claim(claim([t, v], CONFLICT, conflicting=[["t"]]))
    assert "CLAIM_CONFLICT_PRESET_RESOLUTION" in V.validate_claim(
        claim([t, v], CONFLICT, conflicting=[["t"], ["v"]], resolution={"resolved_by": ["t"], "outcome": "increase", "basis": "x"}))


def test_resolution_needs_additional_evidence_outside_the_conflicting_observations():
    t, v, e = obs("t", TRANSCRIPT), obs("v", VISUAL, value="decrease"), obs("e", EPISODE_STATE)
    ok = claim([t, v, e], RESOLVED, conflicting=[["t"], ["v"]], resolution={"resolved_by": ["e"], "outcome": "increase", "basis": "readback"})
    assert V.validate_claim(ok) == []
    for by in (["t"], [], ["ghost"]):
        bad = claim([t, v, e], RESOLVED, conflicting=[["t"], ["v"]], resolution={"resolved_by": by, "outcome": "increase", "basis": "x"})
        assert "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE" in V.validate_claim(bad)
    assert "CLAIM_RESOLUTION_WITHOUT_CONFLICT" in V.validate_claim(claim([t], resolution={"resolved_by": ["t"], "outcome": "x", "basis": "y"}))


def test_unknown_observations_cannot_be_counted_as_agreement_or_conflict_evidence():
    t, u = obs("t", TRANSCRIPT), unknown_obs("u")
    assert "CLAIM_UNKNOWN_COUNTED_AS_EVIDENCE" in V.validate_claim(claim([t, u], AGREEMENT, agreeing=["t", "u"]))
    assert V.validate_claim(claim([t, u], SINGLE_MODALITY, conf=0.6)) == []            # kept in the claim, just not evidence


@pytest.mark.parametrize("over,code", [
    ({"advisory": False}, "CLAIM_NOT_ADVISORY"),
    ({"confidence": 0.99}, "CLAIM_CONFIDENCE_OUT_OF_RANGE"),
    ({"confidence": -0.1}, "CLAIM_CONFIDENCE_OUT_OF_RANGE"),
    ({"provenance": {}}, "CLAIM_NO_PROVENANCE"),
    ({"observations": (), "modalities": ()}, "CLAIM_NO_OBSERVATIONS"),
    ({"agreement": {"status": "WINNER"}}, "CLAIM_BAD_AGREEMENT_STATUS"),
])
def test_malformed_claim_is_rejected(over, code):
    assert code in V.validate_claim(claim([obs()], **over))


def test_claim_rejects_mixed_subjects_duplicate_ids_and_invalid_members():
    a, b = obs("a"), obs("b", subject={"canonical_target_id": "env2.release", "aspect": "direction"})
    assert "CLAIM_MIXED_SUBJECTS" in V.validate_claim(claim([a, b]))
    assert "CLAIM_DUPLICATE_OBSERVATION_IDS" in V.validate_claim(claim([obs("a"), obs("a", VISUAL)]))
    assert "CLAIM_OBSERVATION_INVALID" in V.validate_claim(claim([obs("a", confidence=5.0)]))


def test_a_claim_with_a_winner_or_action_field_is_rejected():
    d = claim([obs()]).to_dict()
    d["winner"] = "o1"
    assert "CLAIM_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate_claim(d)
    d = claim([obs()]).to_dict()
    d["agreement"]["selected"] = "o1"
    assert "CLAIM_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate_claim(d)


def test_max_grounded_confidence_is_below_certainty():
    assert MAX_GROUNDED_CONFIDENCE < 1.0
    assert V.validate_claim(claim([obs()], conf=MAX_GROUNDED_CONFIDENCE)) == []


def test_grounding_module_imports_no_brain_admission_contract_or_backend_code():
    tree = ast.parse(Path(g.__file__).read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not [m for m in mods if any(b in m for b in ("producer_brain", "admission", "contract_registry", "capability", "backend", "serum_mcp", "dawdreamer", "candidate", "skill_library.SkillStore"))]


def test_grounding_module_names_no_target_and_has_no_timestamp_to_action_rules():
    tree = ast.parse(Path(g.__file__).read_text(encoding="utf-8"))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not [c for c in consts if any(t in c.lower() for t in ("env1", "env2", "filter1", "osc", "release", "cutoff"))]
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Dict) and any(isinstance(k, ast.Constant) and isinstance(k.value, (int, float)) for k in n.keys)]


# ---- RED: later stages (strict xfail; remove marker when implemented) ------------------------------------------------------
RED = pytest.mark.xfail(strict=True, raises=(ImportError, AttributeError, TypeError), reason="P6 later stage not implemented")


@RED
def test_p6_2_agreement_across_modalities_raises_confidence_but_keeps_every_modalitys_provenance():
    from serum2.producer.grounding import ground
    t, v = obs("t", TRANSCRIPT, conf=0.6), obs("v", VISUAL, conf=0.7)
    c = ground([t, v])
    assert c.agreement["status"] == AGREEMENT and 0.7 < c.confidence <= MAX_GROUNDED_CONFIDENCE
    assert {o.observation_id for o in c.observations} == {"t", "v"} and c.modalities == ("TRANSCRIPT", "VISUAL")
    assert c.observations[0].source != c.observations[1].source and V.validate_claim(c) == []


@RED
def test_p6_2_same_modality_agreement_gets_no_multimodal_bonus():
    from serum2.producer.grounding import ground
    c = ground([obs("a", VISUAL, conf=0.6), obs("b", VISUAL, conf=0.7)])
    assert c.agreement["status"] == SINGLE_MODALITY and c.confidence == 0.7


@RED
def test_p6_2_conflicting_modalities_stay_a_conflict_with_no_winner_and_no_confidence_gain():
    from serum2.producer.grounding import ground
    t, v = obs("t", TRANSCRIPT, "increase", 0.8), obs("v", VISUAL, "decrease", 0.7)
    c = ground([t, v])
    assert c.agreement["status"] == CONFLICT and c.conflict_resolution is None
    assert sorted(map(sorted, c.agreement["conflicting_observation_ids"])) == [["t"], ["v"]]
    assert c.confidence < 0.7 and V.validate_claim(c) == []
    assert not hasattr(c, "winner") and {o.observation_id for o in c.observations} == {"t", "v"}


@RED
def test_p6_2_unknowns_stay_in_the_claim_but_never_count_as_agreement_or_conflict():
    from serum2.producer.grounding import ground
    c = ground([obs("t", TRANSCRIPT), unknown_obs("u")])
    assert c.agreement["status"] == SINGLE_MODALITY and "u" not in c.agreement["agreeing_observation_ids"] and len(c.observations) == 2
    only_unknown = ground([unknown_obs("u")])
    assert only_unknown.agreement["status"] == INSUFFICIENT and only_unknown.confidence == 0.0


@RED
def test_p6_2_grounding_is_deterministic_and_order_independent():
    from serum2.producer.grounding import ground
    xs = [obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "increase"), unknown_obs("u"), obs("e", EPISODE_STATE, "increase", 0.9)]
    a, b = ground(xs), ground(list(reversed(xs)))
    assert (a.agreement, a.confidence, a.modalities) == (b.agreement, b.confidence, b.modalities) and a.claim_id == b.claim_id


@RED
def test_p6_2_ground_rejects_mixed_subjects_and_invalid_observations():
    from serum2.producer.grounding import ground
    with pytest.raises(ValueError):
        ground([obs("a"), obs("b", subject={"canonical_target_id": "env2.release", "aspect": "direction"})])
    with pytest.raises(ValueError):
        ground([obs("a", confidence=7.0)])
    with pytest.raises(ValueError):
        ground([])


@RED
def test_p6_3_the_validator_rederives_agreement_so_a_forged_claim_is_caught():
    from serum2.producer.grounding import ground
    real = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease")])
    forged = replace(real, agreement={"status": AGREEMENT, "agreeing_observation_ids": ["t", "v"], "conflicting_observation_ids": []}, confidence=0.9)
    assert "CLAIM_AGREEMENT_INCONSISTENT" in V.validate_claim(forged)


@RED
def test_p6_4_a_conflict_resolves_only_with_additional_evidence_and_keeps_the_originals():
    from serum2.producer.grounding import ground, resolve_conflict
    c = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease")])
    e = obs("e", EPISODE_STATE, "increase", 0.9)
    r = resolve_conflict(c, e, basis="plugin readback")
    assert r.agreement["status"] == RESOLVED and r.conflict_resolution["resolved_by"] == ["e"] and r.conflict_resolution["outcome"] == "increase"
    assert {o.observation_id for o in r.observations} == {"t", "v", "e"} and V.validate_claim(r) == []
    with pytest.raises(ValueError):
        resolve_conflict(c, c.observations[0], basis="reusing a conflicting observation is not new evidence")
    with pytest.raises(ValueError):
        resolve_conflict(c, obs("x", EPISODE_STATE, "sideways"), basis="outcome is neither conflicting interpretation")
    with pytest.raises(ValueError):
        resolve_conflict(ground([obs("t", TRANSCRIPT)]), e, basis="nothing to resolve")


@RED
def test_p6_5_adapter_turns_a_fusion_event_into_transcript_and_visual_observations_with_provenance():
    from types import SimpleNamespace
    from serum2.producer.grounding import observations_from_production_event
    ev = SimpleNamespace(event_id="evt_1", start_timestamp_sec=10.0, end_timestamp_sec=35.0, evidence_frame_ids=["frame_a"],
                         transcript_excerpt="a bit more release", transcript_timestamp_sec=12.0, fusion_status="AGREEMENT",
                         snapshot_diff={"changed_controls": [{"control_id": "env1.release", "before": "15 ms", "after": "838 ms"}]})
    out = observations_from_production_event(ev)
    assert {o.modality for o in out} == {TRANSCRIPT, VISUAL} and all(V.validate_observation(o) == [] for o in out)
    vis = next(o for o in out if o.modality == VISUAL)
    assert vis.subject["canonical_target_id"] == "env1.release" and vis.source["ref"] == "frame_a"


@RED
def test_p6_5_adapter_keeps_measurements_real_and_unknowns_unknown():
    from serum2.producer.grounding import observations_from_measurement
    done = {"status": "MEASURED", "acoustic_status": "COMPUTED", "sha256": "abc", "measurement_definition_id": "g8-basic-acoustic-v1",
            "rms_db": -23.01, "peak_db": -10.86, "spectral_centroid_hz": 3711.6}
    out = observations_from_measurement(done)
    assert {o.status for o in out} == {MEASURED} and all(o.source["method"] == "g8-basic-acoustic-v1" for o in out) and all(V.validate_observation(o) == [] for o in out)
    for status in ("NO_RENDER", "FILE_NOT_FOUND", "EMPTY_AUDIO", "MEASUREMENT_ERROR"):
        unk = observations_from_measurement({"status": status, "acoustic_status": "NOT_ATTEMPTED"})
        assert unk and all(o.status == UNKNOWN and o.confidence == 0.0 and V.validate_observation(o) == [] for o in unk)


@RED
def test_p6_5_adapter_turns_episode_readback_into_episode_state_observations():
    from types import SimpleNamespace
    from serum2.producer.grounding import observations_from_episode
    ep = SimpleNamespace(experience_id="e1", outcome={"real_plugin_readback": {"backend": "vst3-host", "expected": {"k": "838 ms"}, "observed": {"k": "838 ms"}}})
    out = observations_from_episode(ep)
    assert out and all(o.modality == EPISODE_STATE and V.validate_observation(o) == [] for o in out)


@RED
def test_p6_6_grounding_cannot_change_a_real_brain_decision_and_cannot_execute():
    from serum2.producer.grounding import ground
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    strong = ground([obs("t", TRANSCRIPT, conf=0.95, subject={"canonical_target_id": "env2.release", "aspect": "direction"}),
                     obs("v", VISUAL, conf=0.95, subject={"canonical_target_id": "env2.release", "aspect": "direction"})])
    req = ProducerRequest(user_intent="longer Env2.Release to 267 ms", mode="EXECUTE", visual_mode="NEVER")
    before = ProducerBrain().execute(req)
    after = ProducerBrain(grounding_claims=[strong]).execute(req)
    assert bool(after.admitted) is False and after.execution_status == before.execution_status
