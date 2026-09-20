"""P6: audio/text/visual grounding. P6.1 contract + validator and P6.2 ground()/ConfidencePolicy are GREEN; the
validator's re-derivation (P6.3), adapters (P6.4), conflict resolution (P6.5) and Brain boundary (P6.6) are strict-xfail RED
and must flip (losing the marker) when implemented."""
import ast
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from serum2.producer import grounding as g
from serum2.producer.grounding import (
    AGREEMENT, AUDIO, CONFLICT, EPISODE_STATE, INSUFFICIENT, MEASURED, OBSERVED, RESOLVED, SINGLE_MODALITY,
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
    if status == SINGLE_MODALITY and not agreeing:
        agreeing = [o.observation_id for o in members if o.status != UNKNOWN and o.interpretation is not None]
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
    res = {"resolved_by": ["e"], "outcome": "increase", "basis": "readback", "provenance": {"recorded_by": "test"}}
    ok = claim([t, v, e], RESOLVED, agreeing=["t", "e"], conflicting=[["t"], ["v"]], resolution=res)
    assert V.validate_claim(ok) == []
    for by in (["t"], [], ["ghost"]):
        bad = claim([t, v, e], RESOLVED, agreeing=["t", "e"], conflicting=[["t"], ["v"]], resolution={**res, "resolved_by": by})
        assert "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE" in V.validate_claim(bad)
    for drop in ("basis", "provenance"):
        thin = claim([t, v, e], RESOLVED, agreeing=["t", "e"], conflicting=[["t"], ["v"]], resolution={k: x for k, x in res.items() if k != drop})
        assert "CLAIM_RESOLUTION_WITHOUT_PROVENANCE" in V.validate_claim(thin)
    assert "CLAIM_RESOLUTION_WITHOUT_CONFLICT" in V.validate_claim(claim([t], resolution={"resolved_by": ["t"], "outcome": "x", "basis": "y"}))


def test_unknown_observations_cannot_be_counted_as_agreement_or_conflict_evidence():
    t, u = obs("t", TRANSCRIPT), unknown_obs("u")
    assert "CLAIM_UNKNOWN_COUNTED_AS_EVIDENCE" in V.validate_claim(claim([t, u], AGREEMENT, agreeing=["t", "u"]))
    assert V.validate_claim(claim([t, u], SINGLE_MODALITY, conf=0.6)) == []            # kept in the claim, just not evidence


@pytest.mark.parametrize("over,code", [
    ({"advisory": False}, "CLAIM_NOT_ADVISORY"),
    ({"confidence": 1.01}, "CLAIM_CONFIDENCE_OUT_OF_RANGE"),
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


def test_claim_confidence_domain_is_the_unit_interval_and_no_ceiling_is_hardcoded():
    assert V.validate_claim(claim([obs()], conf=1.0)) == [] and V.validate_claim(claim([obs()], conf=0.0)) == []
    assert not hasattr(g, "MAX_GROUNDED_CONFIDENCE")


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


# ---- P6.2 ground() + ConfidencePolicy: invariants hold for ANY policy ------------------------------------------------------
import itertools
from serum2.producer.grounding import DEFAULT_POLICY, ConfidencePolicy, IndependenceConfidencePolicy, ground


class Hostile:
    """Returns out-of-domain garbage everywhere."""
    def evidence_weight(self, o): return 7.0
    def combine(self, cs): return -1.0
    def agreement_effect(self, cs): return float("nan")
    def conflict_effect(self, cs): return 9.0
    def unknown_effect(self, c, us): return 5.0


class Erratic:
    """Valid-looking but violates every monotonicity the plan requires."""
    def evidence_weight(self, o): return o.confidence
    def combine(self, cs): return 0.5
    def agreement_effect(self, cs): return 1.0 / (1 + len(cs)) if cs else 0.0          # more support -> LOWER
    def conflict_effect(self, cs): return min(1.0, max(cs) + 0.3)                        # conflict looks stronger than a side
    def unknown_effect(self, c, us): return min(1.0, c + 0.4)                            # unknowns look like evidence


class SumPolicy:
    """A different, legitimate policy: shows the numbers come from the policy, not from ground()."""
    def evidence_weight(self, o): return o.confidence
    def combine(self, cs): return min(1.0, sum(cs))
    def agreement_effect(self, cs): return min(1.0, sum(cs))
    def conflict_effect(self, cs): return 0.0
    def unknown_effect(self, c, us): return c / (1 + len(us))


POLICIES = [DEFAULT_POLICY, Hostile(), Erratic(), SumPolicy()]
IDS = ["default", "hostile", "erratic", "sum"]
GRID = [0.0, 0.2, 0.5, 0.8, 1.0]


def keep(claim_):
    return {o.observation_id: o for o in claim_.observations}


def test_default_policy_implements_the_full_policy_interface_and_is_replaceable():
    for m in ("evidence_weight", "combine", "agreement_effect", "conflict_effect", "unknown_effect"):
        assert callable(getattr(IndependenceConfidencePolicy(), m))
    assert isinstance(DEFAULT_POLICY, IndependenceConfidencePolicy)
    a = ground([obs("t", TRANSCRIPT, conf=0.4), obs("v", VISUAL, conf=0.5)])
    b = ground([obs("t", TRANSCRIPT, conf=0.4), obs("v", VISUAL, conf=0.5)], policy=SumPolicy())
    assert a.confidence != b.confidence and b.provenance["policy"] == "SumPolicy" and V.validate_claim(b) == []


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_ground_keeps_every_observation_unchanged_with_all_provenance_fields(policy):
    xs = [obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "increase"), obs("a", AUDIO, "increase"), obs("e", EPISODE_STATE, "increase"), unknown_obs("u")]
    c = ground(xs, policy=policy)
    kept = keep(c)
    assert set(kept) == {"t", "v", "a", "e", "u"} and all(kept[o.observation_id] is o for o in xs)      # the very same, unmodified objects
    assert c.modalities == ("AUDIO", "EPISODE_STATE", "TRANSCRIPT", "VISUAL")
    for o in xs:
        for f in ("source", "timestamp", "observation", "interpretation", "modality", "uncertainty", "provenance", "confidence"):
            assert getattr(kept[o.observation_id], f) == getattr(o, f)
    assert V.validate_claim(c) == []


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_ground_is_an_aggregator_not_an_interpreter_or_actor(policy):
    c = ground([obs("t", TRANSCRIPT), obs("v", VISUAL)], policy=policy)
    d = c.to_dict()
    assert set(d) == {"claim_id", "subject", "observations", "modalities", "agreement", "confidence", "conflict_resolution",
                      "provenance", "advisory", "schema_version"}
    assert not g._FORBIDDEN & set(d) and not g._FORBIDDEN & set(d["agreement"])
    assert {o.interpretation["value"] for o in c.observations} == {"increase"}         # only interpretations that were already there
    assert c.advisory is True and c.conflict_resolution is None


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_same_inputs_give_the_same_claim_in_any_order(policy):
    xs = [obs("t", TRANSCRIPT, "increase", 0.6), obs("v", VISUAL, "increase", 0.7), unknown_obs("u"), obs("e", EPISODE_STATE, "increase", 0.9)]
    a, b, c = ground(xs, policy=policy), ground(list(reversed(xs)), policy=policy), ground(xs, policy=policy)
    assert a == b == c and a.claim_id == b.claim_id


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_confidence_is_always_in_the_valid_domain(policy):
    for ct, cv in itertools.product(GRID, GRID):
        for vi in ("increase", "decrease"):
            c = ground([obs("t", TRANSCRIPT, "increase", ct), obs("v", VISUAL, vi, cv), unknown_obs("u")], policy=policy)
            assert 0.0 <= c.confidence <= 1.0 and V.validate_claim(c) == []


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_more_independent_supporting_modalities_never_lower_confidence(policy):
    for ct, cv, ce, ca in itertools.product(GRID, repeat=4):
        t, v, e, a = (obs("t", TRANSCRIPT, conf=ct), obs("v", VISUAL, conf=cv), obs("e", EPISODE_STATE, conf=ce), obs("a", AUDIO, conf=ca))
        c2, c3, c4 = (ground(x, policy=policy).confidence for x in ([t, v], [t, v, e], [t, v, e, a]))
        assert c2 <= c3 <= c4
        assert ground([t, v], policy=policy).agreement["status"] == AGREEMENT


def test_agreement_can_raise_confidence_under_the_default_policy_and_never_lowers_the_best_single_modality():
    for ct, cv in itertools.product(GRID, GRID):
        both = ground([obs("t", TRANSCRIPT, conf=ct), obs("v", VISUAL, conf=cv)]).confidence
        assert both >= max(ct, cv) - 1e-9
    assert ground([obs("t", TRANSCRIPT, conf=0.5), obs("v", VISUAL, conf=0.5)]).confidence > 0.5


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_repeated_observations_from_one_modality_are_not_independent_support(policy):
    c = ground([obs("a", VISUAL, conf=0.6), obs("b", VISUAL, conf=0.7), obs("c", VISUAL, conf=0.5)], policy=policy)
    assert c.agreement["status"] == SINGLE_MODALITY and list(c.agreement["agreeing_observation_ids"]) == ["a", "b", "c"]
    assert c.confidence == ground([obs("b", VISUAL, conf=0.7)], policy=policy).confidence


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_adding_an_unknown_never_raises_confidence_and_it_is_never_evidence(policy):
    for ct, cv in itertools.product(GRID, GRID):
        base = ground([obs("t", TRANSCRIPT, conf=ct), obs("v", VISUAL, conf=cv)], policy=policy)
        with_unknown = ground([obs("t", TRANSCRIPT, conf=ct), obs("v", VISUAL, conf=cv), unknown_obs("u"), unknown_obs("u2", VISUAL)], policy=policy)
        assert with_unknown.confidence <= base.confidence
        assert with_unknown.agreement["agreeing_observation_ids"] == base.agreement["agreeing_observation_ids"]
        assert "u" in keep(with_unknown) and keep(with_unknown)["u"].observation == {"metric": "spectral_centroid_hz", "value": None}
    only = ground([unknown_obs("u")], policy=policy)
    assert only.agreement["status"] == INSUFFICIENT and only.confidence == 0.0 and V.validate_claim(only) == []


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_a_conflict_stays_a_conflict_with_no_winner_and_never_looks_more_confident_than_a_side(policy):
    for ct, cv in itertools.product(GRID, GRID):
        t, v = obs("t", TRANSCRIPT, "increase", ct), obs("v", VISUAL, "decrease", cv)
        c = ground([t, v], policy=policy)
        assert c.agreement["status"] == CONFLICT and c.conflict_resolution is None and V.validate_claim(c) == []
        assert sorted(map(sorted, c.agreement["conflicting_observation_ids"])) == [["t"], ["v"]]
        assert c.confidence <= min(ground([t], policy=policy).confidence, ground([v], policy=policy).confidence)
        assert not hasattr(c, "winner") and set(keep(c)) == {"t", "v"}


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_more_evidence_for_one_side_does_not_resolve_a_conflict(policy):
    t, v, e = obs("t", TRANSCRIPT, "increase", 0.9), obs("v", VISUAL, "decrease", 0.6), obs("e", EPISODE_STATE, "increase", 0.9)
    c = ground([t, v, e], policy=policy)
    assert c.agreement["status"] == CONFLICT and c.conflict_resolution is None                 # only resolve_conflict may settle it
    assert ground([t, v, obs("x", AUDIO, "sideways", 0.9)], policy=policy).agreement["status"] == CONFLICT


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
def test_an_uninterpreted_observation_is_kept_but_is_not_evidence(policy):
    raw_only = obs("r", TRANSCRIPT, interpretation=None)
    c = ground([raw_only], policy=policy)
    assert c.agreement["status"] == INSUFFICIENT and c.confidence == 0.0 and keep(c)["r"] is raw_only
    mixed = ground([raw_only, obs("v", VISUAL, conf=0.7)], policy=policy)
    assert list(mixed.agreement["agreeing_observation_ids"]) == ["v"] and mixed.agreement["status"] == SINGLE_MODALITY


def test_ground_rejects_bad_input():
    with pytest.raises(ValueError):
        ground([])
    with pytest.raises(ValueError):
        ground([obs("a"), obs("b", subject={"canonical_target_id": "env2.release", "aspect": "direction"})])
    with pytest.raises(ValueError):
        ground([obs("a", confidence=7.0)])
    with pytest.raises(ValueError):
        ground([obs("a"), obs("a", VISUAL)])
    with pytest.raises(ValueError):
        ground([obs("a", interpretation={"kind": "direction", "value": "up", "basis": "x"}),
                obs("b", VISUAL, interpretation={"kind": "brightness", "value": "up", "basis": "x"})])


def test_ground_has_no_side_effects(monkeypatch):
    import builtins, socket, subprocess
    real_open = builtins.open
    monkeypatch.setattr(builtins, "open", lambda f, mode="r", *a, **k: (_ for _ in ()).throw(AssertionError("write")) if any(c in mode for c in "wax+") else real_open(f, mode, *a, **k))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("process")))
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert ground([obs("t", TRANSCRIPT), obs("v", VISUAL)]).agreement["status"] == AGREEMENT


# ---- P6.4 adapters: wrappers over existing evidence, never interpreters ----------------------------------------------------
import json
from types import SimpleNamespace
from serum2.producer.grounding import (
    ground_by_subject, observations_from_episode, observations_from_measurement, observations_from_production_event,
)

FRAMES = ["frame_a", "frame_b"]


def event(changed=(), fusion=None, excerpt="a bit more release", eid="evt_1", t_at=12.0, fusion_status="AGREEMENT", **diff_extra):
    d = {"before_frame_id": "frame_a", "after_frame_id": "frame_b", "changed_controls": [dict(c) for c in changed],
         "not_observed_controls": [], "added_routes": [], "removed_routes": [], "newly_observed_routes": []}
    d.update(diff_extra)
    if fusion is not None:
        d["control_fusion"] = fusion
    return SimpleNamespace(event_id=eid, start_timestamp_sec=10.0, end_timestamp_sec=35.0, evidence_frame_ids=list(FRAMES),
                           transcript_excerpt=excerpt, transcript_timestamp_sec=t_at, fusion_status=fusion_status, snapshot_diff=d)


REL = {"control_id": "env1.release", "before": "15 ms", "after": "838 ms"}


def fus(visual="increase", transcript="increase", mentioned=True, cls="AGREEMENT"):
    return {"mentioned": mentioned, "visual": visual, "transcript": transcript, "classification": cls}


def by_mod(out):
    return {o.modality: o for o in out}


def test_p6_4_event_becomes_transcript_and_visual_observations_with_full_provenance():
    out = observations_from_production_event(event([REL], {"env1.release": fus()}))
    assert {o.modality for o in out} == {TRANSCRIPT, VISUAL} and all(V.validate_observation(o) == [] for o in out)
    m = by_mod(out)
    assert m[VISUAL].subject == {"canonical_target_id": "env1.release", "aspect": "direction"} == dict(m[TRANSCRIPT].subject)
    assert dict(m[VISUAL].observation) == {"control_id": "env1.release", "before": "15 ms", "after": "838 ms"}
    assert list(m[VISUAL].source["frame_ids"]) == FRAMES and m[VISUAL].source["ref"] == "frame_a,frame_b"
    assert dict(m[VISUAL].timestamp) == {"start_sec": 10.0, "end_sec": 35.0} and dict(m[TRANSCRIPT].timestamp) == {"start_sec": 12.0, "end_sec": 35.0}
    assert m[TRANSCRIPT].observation["text"] == "a bit more release"
    assert m[VISUAL].interpretation["value"] == m[TRANSCRIPT].interpretation["value"] == "increase"
    assert m[VISUAL].interpretation["basis"] != m[TRANSCRIPT].interpretation["basis"]         # each modality keeps its own basis
    (claim_,) = ground_by_subject(out)
    assert claim_.agreement["status"] == AGREEMENT and claim_.modalities == ("TRANSCRIPT", "VISUAL") and V.validate_claim(claim_) == []


def test_p6_4_a_conflict_comes_from_the_recorded_directions_and_is_never_settled_by_the_adapter():
    out = observations_from_production_event(event([REL], {"env1.release": fus(visual="increase", transcript="decrease", cls="CONFLICT")}))
    (c,) = ground_by_subject(out)
    assert c.agreement["status"] == CONFLICT and c.conflict_resolution is None and {o.modality for o in c.observations} == {TRANSCRIPT, VISUAL}


def test_p6_4_the_adapter_reads_evidence_not_fusion_labels():
    lying = event([REL], {"env1.release": fus(visual="increase", transcript="decrease", cls="AGREEMENT")}, fusion_status="AGREEMENT")
    assert ground_by_subject(observations_from_production_event(lying))[0].agreement["status"] == CONFLICT
    honest_conflict_label = event([REL], {"env1.release": fus(cls="CONFLICT")}, fusion_status="CONFLICT")
    out = observations_from_production_event(honest_conflict_label)
    assert ground_by_subject(out)[0].agreement["status"] == AGREEMENT and out[0].provenance["fusion_status"] == "CONFLICT"      # label only recorded


def test_p6_4_a_transcript_observation_exists_only_where_fusion_says_the_control_was_mentioned():
    other = {"control_id": "filter1.cutoff", "before": "200 Hz", "after": "900 Hz"}
    out = observations_from_production_event(event([REL, other], {"env1.release": fus(), "filter1.cutoff": fus(transcript=None, mentioned=False, cls="UNKNOWN")}))
    assert sorted((o.modality, o.subject["canonical_target_id"]) for o in out) == [
        (TRANSCRIPT, "env1.release"), (VISUAL, "env1.release"), (VISUAL, "filter1.cutoff")]


def test_p6_4_an_unevaluable_transcript_direction_stays_uninterpreted_and_is_not_evidence():
    out = observations_from_production_event(event([REL], {"env1.release": fus(transcript=None, mentioned=True, cls="UNKNOWN")}))
    assert by_mod(out)[TRANSCRIPT].interpretation is None
    (c,) = ground_by_subject(out)
    assert c.agreement["status"] == SINGLE_MODALITY and list(c.agreement["agreeing_observation_ids"]) == [by_mod(out)[VISUAL].observation_id]


def test_p6_4_a_non_directional_change_is_kept_as_an_uninterpreted_reading():
    enum = {"control_id": "lfo1.mode", "before": "Normal", "after": "Chaos: Lorenz"}
    out = observations_from_production_event(event([enum], {"lfo1.mode": fus(visual=None, transcript=None, mentioned=False, cls="UNKNOWN")}, excerpt=None))
    (o,) = out
    assert o.interpretation is None and dict(o.observation)["after"] == "Chaos: Lorenz" and V.validate_observation(o) == []
    assert ground_by_subject(out)[0].agreement["status"] == INSUFFICIENT


def test_p6_4_displayed_readings_are_text_never_numbers():
    numeric = {"control_id": "oscB.unison", "before": 1, "after": 3}                # the census may hold a bare number
    (o,) = observations_from_production_event(event([numeric], None, excerpt=None))
    assert dict(o.observation)["before"] == "1" and dict(o.observation)["after"] == "3" and o.status == OBSERVED and V.validate_observation(o) == []
    assert o.interpretation["value"] == "increase"


def test_p6_4_controls_that_could_not_be_observed_become_unknown_observations():
    out = observations_from_production_event(event([], {}, excerpt=None, not_observed_controls=["fx.hyper.unison"]))
    (o,) = out
    assert o.status == UNKNOWN and o.confidence == 0.0 and o.interpretation is None and dict(o.observation) == {"control_id": "fx.hyper.unison", "before": None, "after": None}
    assert o.uncertainty["reason"] and V.validate_observation(o) == []
    assert ground_by_subject(out)[0].agreement["status"] == INSUFFICIENT


def test_p6_4_route_changes_become_presence_observations_and_newly_observed_routes_claim_nothing():
    out = observations_from_production_event(event([], {}, excerpt=None, added_routes=[{"source": "env2", "destination": "filter1.cutoff"}],
                                                    removed_routes=[{"source": "lfo1", "destination": "osc.a.fine"}],
                                                    newly_observed_routes=[{"source": "env3", "destination": "noise.level"}]))
    assert sorted((o.subject["aspect"], o.interpretation["value"]) for o in out) == [("route:env2->filter1.cutoff", "added"), ("route:lfo1->osc.a.fine", "removed")]


def test_p6_4_a_transcript_without_per_control_fusion_is_kept_as_narration():
    out = observations_from_production_event(event([], None))
    (o,) = out
    assert o.modality == TRANSCRIPT and o.subject == {"canonical_target_id": None, "aspect": "narration"} and o.interpretation is None


def test_p6_4_an_event_with_no_evidence_yields_nothing_and_one_without_a_time_window_is_refused():
    assert observations_from_production_event(event([], {}, excerpt=None)) == []
    e = event([REL], {"env1.release": fus()})
    e.start_timestamp_sec = e.end_timestamp_sec = None
    with pytest.raises(ValueError):
        observations_from_production_event(e)


def test_p6_4_adapters_do_not_invent_confidence_but_take_a_supplied_source():
    out = observations_from_production_event(event([REL], {"env1.release": fus()}))
    assert {o.confidence for o in out} == {0.0} and all(o.uncertainty["level"] == "UNKNOWN" and o.uncertainty["notes"] for o in out)
    rated = observations_from_production_event(event([REL], {"env1.release": fus()}), confidence_for=lambda m, raw: {TRANSCRIPT: 0.4, VISUAL: 0.7}[m])
    assert {o.modality: o.confidence for o in rated} == {TRANSCRIPT: 0.4, VISUAL: 0.7} and all(V.validate_observation(o) == [] for o in rated)
    for bad in (lambda m, r: 1.5, lambda m, r: True, lambda m, r: "high", lambda m, r: -0.1):
        with pytest.raises(ValueError):
            observations_from_production_event(event([REL], {"env1.release": fus()}), confidence_for=bad)


def test_p6_4_event_adapter_is_deterministic_target_agnostic_and_carries_no_authority_field():
    e = event([REL, {"control_id": "filter1.cutoff", "before": "200 Hz", "after": "900 Hz"}], {"env1.release": fus(), "filter1.cutoff": fus()})
    a, b = observations_from_production_event(e), observations_from_production_event(e)
    assert a == b and [o.observation_id for o in a] == sorted(o.observation_id for o in a)
    assert all(not g._FORBIDDEN & set(o.to_dict()) for o in a) and len(ground_by_subject(a)) == 2


def test_p6_4_every_event_of_the_real_heegn1_timeline_adapts_to_valid_observations():
    root = Path(__file__).resolve().parents[1] / "data" / "experiences"
    files = sorted(root.glob("vlp1_u8_HEEGN1_*.json")) if root.exists() else []
    if not files:
        pytest.skip("local run artifact not present (serum2/data is gitignored)")
    timeline = json.loads(files[-1].read_text(encoding="utf-8"))["visual_evidence"]["timeline"]
    total = 0
    for ev in timeline:
        out = observations_from_production_event(SimpleNamespace(**{k: ev.get(k) for k in (
            "event_id", "start_timestamp_sec", "end_timestamp_sec", "evidence_frame_ids", "snapshot_diff", "transcript_excerpt",
            "transcript_timestamp_sec", "fusion_status")}))
        assert all(V.validate_observation(o) == [] for o in out)
        assert all(V.validate_claim(c) == [] for c in ground_by_subject(out))
        total += len(out)
    assert total > 20


# ---- audio ----
COMPUTED = {"status": "MEASURED", "acoustic_status": "COMPUTED", "sha256": "abc123", "measurement_definition_id": "g8-basic-acoustic-v1",
            "rms_db": -23.01, "peak_db": -10.86, "spectral_centroid_hz": 3711.6}


def test_p6_4_computed_measurements_become_measured_observations_with_method_and_source():
    out = observations_from_measurement(COMPUTED)
    assert {o.subject["aspect"] for o in out} == {"rms_db", "peak_db", "spectral_centroid_hz"} and {o.status for o in out} == {MEASURED}
    for o in out:
        assert V.validate_observation(o) == [] and o.source["method"] == "g8-basic-acoustic-v1" and o.source["ref"] == "abc123" and o.timestamp is None
        assert o.observation["value"] == COMPUTED[o.subject["aspect"]] and o.subject["canonical_target_id"] is None and o.interpretation is None


@pytest.mark.parametrize("status,acoustic", [("NO_RENDER", "NOT_ATTEMPTED"), ("FILE_NOT_FOUND", "NOT_ATTEMPTED"), ("EMPTY_AUDIO", "NOT_ATTEMPTED"),
                                              ("MEASUREMENT_ERROR", "NOT_ATTEMPTED"), ("UNSUPPORTED_FORMAT", "UNSUPPORTED_FORMAT"), ("MEASUREMENT_ERROR", "ERROR")])
def test_p6_4_a_measurement_that_was_not_computed_yields_only_unknowns(status, acoustic):
    out = observations_from_measurement({"status": status, "acoustic_status": acoustic, "rms_db": -3.0, "peak_db": -1.0, "spectral_centroid_hz": 999.0})
    assert len(out) == 3 and all(o.status == UNKNOWN and o.confidence == 0.0 and V.validate_observation(o) == [] for o in out)
    assert all(dict(o.observation)["value"] is None for o in out) and all(status in o.uncertainty["reason"] for o in out)          # stray numbers are NOT trusted


def test_p6_4_a_computed_measurement_with_a_bad_metric_marks_only_that_metric_unknown():
    for bad in (None, float("nan"), float("inf"), "loud", True):
        out = by_aspect = {o.subject["aspect"]: o for o in observations_from_measurement({**COMPUTED, "peak_db": bad})}
        assert out["peak_db"].status == UNKNOWN and out["rms_db"].status == MEASURED and out["spectral_centroid_hz"].status == MEASURED
    assert all(o.status == UNKNOWN for o in observations_from_measurement({k: v for k, v in COMPUTED.items() if k != "measurement_definition_id"}))   # no method: not a measurement


def test_p6_4_direction_is_attached_only_between_two_real_computed_measurements():
    louder = {**COMPUTED, "sha256": "new", "rms_db": -20.0, "peak_db": -10.86, "spectral_centroid_hz": 3000.0}
    m = {o.subject["aspect"]: o for o in observations_from_measurement(louder, baseline=COMPUTED)}
    assert [m[k].interpretation["value"] for k in ("rms_db", "peak_db", "spectral_centroid_hz")] == ["increase", "unchanged", "decrease"]
    assert all(o.interpretation is None for o in observations_from_measurement(louder, baseline={"status": "NO_RENDER", "acoustic_status": "NOT_ATTEMPTED"}))
    assert all(o.interpretation is None for o in observations_from_measurement(louder))


def test_p6_4_audio_adapter_takes_a_confidence_source_and_never_defaults_to_one():
    assert {o.confidence for o in observations_from_measurement(COMPUTED)} == {0.0}
    assert {o.confidence for o in observations_from_measurement(COMPUTED, confidence_for=lambda m, r: 0.6)} == {0.6}


def test_p6_4_the_real_g8_measurement_adapts_exactly():
    wav = Path(__file__).resolve().parents[1] / "data" / "renders" / "heegn1_env1release_exec.wav"
    if not wav.exists():
        pytest.skip("local render not present (serum2/data is gitignored)")
    from serum2.evidence.acoustic_measurement import measure_render
    m = measure_render(str(wav))
    out = observations_from_measurement(m)
    assert all(V.validate_observation(o) == [] for o in out)
    assert {o.subject["aspect"]: o.observation["value"] for o in out} == {k: m[k] for k in ("rms_db", "peak_db", "spectral_centroid_hz")}
    assert observations_from_measurement(measure_render(str(wav) + ".missing")) and all(o.status == UNKNOWN for o in observations_from_measurement(measure_render(str(wav) + ".missing")))


# ---- episode state ----
def readback_episode(observed=None, baseline=None, expected=None):
    rb = {"backend": "vst3-host", "expected": expected if expected is not None else {"Env 1 Release": "838 ms"},
          "observed": observed if observed is not None else {"Env 1 Release": "838 ms"}}
    if baseline is not None:
        rb["baseline_untouched_init"] = baseline
    return SimpleNamespace(experience_id="e1", outcome={"real_plugin_readback": rb},
                           brain_decision={"decisions": [{"source_control_id": "env1.release", "admitted": True}]})


def test_p6_4_episode_readback_becomes_episode_state_observations_with_direction_from_the_baseline():
    (o,) = observations_from_episode(readback_episode(baseline={"Env 1 Release": "15 ms"}))
    assert o.modality == EPISODE_STATE and V.validate_observation(o) == [] and o.timestamp is None
    assert o.subject == {"canonical_target_id": "env1.release", "aspect": "direction"}            # unambiguous single decision + single key
    assert dict(o.observation) == {"key": "Env 1 Release", "observed": "838 ms", "expected": "838 ms"} and o.interpretation["value"] == "increase"
    assert o.source["ref"] == "e1" and o.source["route"] == "vst3-host" and list(o.provenance["source_episode_ids"]) == ["e1"]


def test_p6_4_episode_subject_mapping_is_explicit_when_ambiguous():
    ep = readback_episode(observed={"A": "1 ms", "B": "2 ms"}, expected={"A": "1 ms", "B": "2 ms"})
    plain = observations_from_episode(ep)
    assert {o.subject["aspect"] for o in plain} == {"readback:A", "readback:B"} and all(o.subject["canonical_target_id"] is None for o in plain)
    mapped = observations_from_episode(ep, subjects={"A": {"canonical_target_id": "env1.attack", "aspect": "direction"}})
    assert {o.subject["aspect"] for o in mapped} == {"direction", "readback:B"}


def test_p6_4_episode_without_a_baseline_or_a_reading_stays_uninterpreted_or_unknown():
    (o,) = observations_from_episode(readback_episode())
    assert o.interpretation is None and o.status == OBSERVED
    (u,) = observations_from_episode(readback_episode(observed={}, expected={"Env 1 Release": "838 ms"}))
    assert u.status == UNKNOWN and u.confidence == 0.0 and dict(u.observation)["observed"] is None and V.validate_observation(u) == []
    assert observations_from_episode(SimpleNamespace(experience_id="e", outcome={})) == []


def test_p6_4_a_readback_that_disagrees_with_the_expectation_is_recorded_as_read_not_as_expected():
    (o,) = observations_from_episode(readback_episode(observed={"Env 1 Release": "15 ms"}, baseline={"Env 1 Release": "15 ms"}))
    assert dict(o.observation)["observed"] == "15 ms" and dict(o.observation)["expected"] == "838 ms" and o.interpretation is None


def test_p6_4_episode_readback_can_resolve_nothing_by_itself_but_joins_the_claim_for_its_subject():
    ep_obs = observations_from_episode(readback_episode(baseline={"Env 1 Release": "15 ms"}))
    ev_obs = observations_from_production_event(event([REL], {"env1.release": fus(visual="increase", transcript="decrease", cls="CONFLICT")}))
    (c,) = ground_by_subject(ev_obs + ep_obs)
    assert c.agreement["status"] == CONFLICT and c.modalities == ("EPISODE_STATE", "TRANSCRIPT", "VISUAL") and V.validate_claim(c) == []


def test_p6_4_ground_by_subject_partitions_and_is_order_independent():
    obs_ = observations_from_measurement(COMPUTED) + observations_from_production_event(event([REL], {"env1.release": fus()}))
    a, b = ground_by_subject(obs_), ground_by_subject(list(reversed(obs_)))
    assert a == b and len(a) == 4 and all(V.validate_claim(c) == [] for c in a)


# ---- video source provenance: every observation can say which video it came from -----------------------------------------
VIDEO = {"source_id": "yt_test000001", "video_id": "VIDEOID0001", "source_url": "https://example.test/watch?v=VIDEOID0001", "title": "A Tutorial"}


def test_p6_4_observations_record_the_video_they_came_from_when_it_is_known():
    ev = observations_from_production_event(event([REL], {"env1.release": fus()}), video_source=VIDEO)
    me = observations_from_measurement(COMPUTED, video_source=VIDEO)
    assert all(dict(o.provenance["video_source"]) == VIDEO for o in ev + me)
    assert all(V.validate_observation(o) == [] for o in ev + me)


def test_p6_4_no_video_source_is_invented_when_none_is_given():
    for o in observations_from_production_event(event([REL], {"env1.release": fus()})) + observations_from_measurement(COMPUTED):
        assert "video_source" not in o.provenance
    assert all("video_source" not in o.provenance for o in observations_from_episode(readback_episode()))
    partial = observations_from_production_event(event([REL], {"env1.release": fus()}), video_source={"video_id": "V", "junk": "x", "title": ""})
    assert all(dict(o.provenance["video_source"]) == {"video_id": "V"} for o in partial)                  # only recorded, known fields


def test_p6_4_the_episode_adapter_takes_the_video_from_the_episodes_own_fields_and_an_explicit_source_wins():
    ep = readback_episode(baseline={"Env 1 Release": "15 ms"})
    ep.source_id, ep.source_url = "yt_ep", "https://example.test/ep"
    ep.production_context = {"video_id": "EPVIDEO0001", "source_title": "Episode Title"}
    (o,) = observations_from_episode(ep)
    assert dict(o.provenance["video_source"]) == {"source_id": "yt_ep", "source_url": "https://example.test/ep", "video_id": "EPVIDEO0001", "title": "Episode Title"}
    (o2,) = observations_from_episode(ep, video_source={"source_id": "override"})
    assert o2.provenance["video_source"]["source_id"] == "override" and o2.provenance["video_source"]["video_id"] == "EPVIDEO0001"


def test_p6_4_a_claim_names_the_videos_its_evidence_came_from_and_keeps_the_detail_on_the_observations():
    a = observations_from_production_event(event([REL], {"env1.release": fus()}), video_source=VIDEO)
    other = observations_from_production_event(event([REL], {"env1.release": fus()}, eid="evt_2"), video_source={**VIDEO, "source_id": "yt_other"})
    (c,) = ground_by_subject(a)
    assert list(c.provenance["source_ids"]) == ["yt_test000001"] and V.validate_claim(c) == []
    (c2,) = ground_by_subject(a[:1] + other[1:])
    assert list(c2.provenance["source_ids"]) == ["yt_other", "yt_test000001"] and all("video_source" in o.provenance for o in c2.observations)
    assert "source_ids" not in ground_by_subject(observations_from_production_event(event([REL], {"env1.release": fus()})))[0].provenance


def test_p6_4_real_episode_evidence_traces_back_to_the_exact_video_frames_and_timestamps():
    root = Path(__file__).resolve().parents[1] / "data" / "experiences"
    files = sorted(root.glob("vlp1_u8_HEEGN1_*.json")) if root.exists() else []
    if not files:
        pytest.skip("local run artifact not present (serum2/data is gitignored)")
    rec = json.loads(files[-1].read_text(encoding="utf-8"))
    ve = rec["visual_evidence"]
    frames = {f["frame_id"]: f for f in ve["frames"]}
    ev = next(e for e in ve["timeline"] if any(c["control_id"] == "env1.release" for c in (e["snapshot_diff"] or {}).get("changed_controls", [])))
    src = {"source_id": rec["source_id"], "source_url": rec["source_url"], "video_id": rec["production_context"]["video_id"], "title": rec["production_context"]["source_title"]}
    out = observations_from_production_event(SimpleNamespace(**{k: ev.get(k) for k in (
        "event_id", "start_timestamp_sec", "end_timestamp_sec", "evidence_frame_ids", "snapshot_diff", "transcript_excerpt",
        "transcript_timestamp_sec", "fusion_status")}), video_source=src)
    vis = next(o for o in out if o.modality == VISUAL and o.subject["canonical_target_id"] == "env1.release")
    assert dict(vis.provenance["video_source"])["video_id"] == "HEEGN1Xl5o4" and dict(vis.provenance["video_source"])["source_id"] == rec["source_id"]
    assert set(vis.source["frame_ids"]) <= set(frames) and all(frames[i]["artifact_hash"] for i in vis.source["frame_ids"])      # exact frames, hashed
    assert all(vis.timestamp["start_sec"] <= frames[i]["timestamp_sec"] <= vis.timestamp["end_sec"] for i in vis.source["frame_ids"])
    assert dict(vis.observation) == {"control_id": "env1.release", "before": "15 ms", "after": "838 ms"}


def test_p6_4_the_grounding_module_contains_no_video_specific_identifiers():
    import re
    tree = ast.parse(Path(g.__file__).read_text(encoding="utf-8"))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not [c for c in consts if re.fullmatch(r"yt_[0-9a-f]{12}", c) or c in ("HEEGN1Xl5o4", "td22OIHpWuI", "k6OBzXdcFtA")]


# ---- RED: later stages (strict xfail; remove marker when implemented) ------------------------------------------------------
RED = pytest.mark.xfail(strict=True, raises=(ImportError, AttributeError, TypeError), reason="P6 later stage not implemented")


# ---- P6.3 policy-free, evidence-derived validation ------------------------------------------------------------------------
import inspect
from serum2.producer.grounding import derive_structure


def conflict_claim(ti="increase", vi="decrease"):
    return ground([obs("t", TRANSCRIPT, ti), obs("v", VISUAL, vi)])


def forged(real, status, agreeing=(), conflicting=(), **over):
    return replace(real, agreement={"status": status, "agreeing_observation_ids": list(agreeing),
                                    "conflicting_observation_ids": [list(x) for x in conflicting]}, **over)


def test_p6_3_observations_say_conflict_claim_says_agreement_is_rejected():
    real = conflict_claim()
    assert real.agreement["status"] == CONFLICT
    codes = V.validate_claim(forged(real, AGREEMENT, agreeing=["t", "v"], confidence=0.9))
    assert "CLAIM_STATUS_INCONSISTENT" in codes and "CLAIM_AGREEMENT_INCONSISTENT" in codes


def test_p6_3_observations_say_agreement_claim_says_conflict_is_rejected():
    real = conflict_claim("increase", "increase")
    assert real.agreement["status"] == AGREEMENT
    codes = V.validate_claim(forged(real, CONFLICT, conflicting=[["t"], ["v"]]))
    assert "CLAIM_STATUS_INCONSISTENT" in codes and "CLAIM_CONFLICT_INCONSISTENT" in codes


def test_p6_3_a_conflict_cannot_be_downgraded_or_have_a_side_hidden():
    real = conflict_claim()
    assert "CLAIM_STATUS_INCONSISTENT" in V.validate_claim(forged(real, SINGLE_MODALITY, agreeing=["t"]))
    hidden = V.validate_claim(forged(real, CONFLICT, conflicting=[["t"]]))
    assert "CLAIM_CONFLICT_WITHOUT_SIDES" in hidden and "CLAIM_CONFLICT_INCONSISTENT" in hidden


def test_p6_3_same_modality_duplicates_are_never_agreement_even_if_the_claim_says_so():
    real = ground([obs("a", VISUAL, "increase"), obs("b", VISUAL, "increase")])
    assert real.agreement["status"] == SINGLE_MODALITY and derive_structure([o.to_dict() for o in real.observations])["status"] == SINGLE_MODALITY
    assert "CLAIM_STATUS_INCONSISTENT" in V.validate_claim(forged(real, AGREEMENT, agreeing=["a", "b"]))


def test_p6_3_unknown_observations_are_never_supporting_evidence_even_if_the_claim_lists_them():
    real = ground([obs("t", TRANSCRIPT), unknown_obs("u")])
    codes = V.validate_claim(forged(real, AGREEMENT, agreeing=["t", "u"]))
    assert "CLAIM_UNKNOWN_COUNTED_AS_EVIDENCE" in codes and "CLAIM_STATUS_INCONSISTENT" in codes
    only = ground([unknown_obs("u")])
    for status in (SINGLE_MODALITY, AGREEMENT):
        assert V.validate_claim(forged(only, status, agreeing=["u"], confidence=0.6))


def test_p6_3_omitting_a_modality_from_the_provenance_is_rejected():
    real = ground([obs("t", TRANSCRIPT), obs("v", VISUAL), obs("e", EPISODE_STATE)])
    assert "CLAIM_MODALITIES_MISMATCH" in V.validate_claim(replace(real, modalities=("TRANSCRIPT", "VISUAL")))


def test_p6_3_subject_mismatch_is_rejected():
    real = conflict_claim("increase", "increase")
    assert "CLAIM_MIXED_SUBJECTS" in V.validate_claim(replace(real, subject={"canonical_target_id": "env2.release", "aspect": "direction"}))
    other = obs("x", AUDIO, subject={"canonical_target_id": "env2.release", "aspect": "direction"})
    assert "CLAIM_MIXED_SUBJECTS" in V.validate_claim(replace(real, observations=real.observations + (other,), modalities=("AUDIO", "TRANSCRIPT", "VISUAL")))


def test_p6_3_agreement_and_conflict_are_reconstructed_from_the_observations_alone():
    agree = derive_structure([obs("t", TRANSCRIPT, "increase").to_dict(), obs("v", VISUAL, "increase").to_dict(), unknown_obs("u").to_dict()])
    assert (agree["status"], agree["agreeing_ids"], agree["conflicting_ids"], agree["unknown_ids"]) == (AGREEMENT, ["t", "v"], [], ["u"])
    conf = derive_structure([obs("t", TRANSCRIPT, "increase").to_dict(), obs("v", VISUAL, "decrease").to_dict(), obs("e", EPISODE_STATE, "increase").to_dict()])
    assert conf["status"] == CONFLICT and sorted(map(sorted, conf["conflicting_ids"])) == [["e", "t"], ["v"]] and conf["agreeing_ids"] == []
    assert derive_structure([])["status"] == INSUFFICIENT


def test_p6_3_a_claim_missing_its_reconstructed_conflict_is_rejected():
    real = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease"), obs("e", EPISODE_STATE, "increase")])
    assert V.validate_claim(real) == []
    assert "CLAIM_CONFLICT_INCONSISTENT" in V.validate_claim(forged(real, CONFLICT, conflicting=[["t"], ["v"]]))     # dropped e from its side


def resolved(conflict=None, e_value="increase"):
    base = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease"), obs("e", EPISODE_STATE, e_value)])
    res = {"resolved_by": ["e"], "outcome": "increase", "basis": "plugin readback", "provenance": {"recorded_by": "test"}}
    return base, replace(base, agreement={"status": RESOLVED, "agreeing_observation_ids": ["t", "e"], "conflicting_observation_ids": [["t"], ["v"]]},
                         conflict_resolution=res)


def test_p6_3_a_genuine_resolution_is_valid():
    _base, r = resolved()
    assert V.validate_claim(r) == []


@pytest.mark.parametrize("mutate,code", [
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "outcome": "decrease"}), "CLAIM_RESOLUTION_OUTCOME_UNSUPPORTED"),
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "outcome": "sideways"}), "CLAIM_RESOLUTION_OUTCOME_NOT_A_SIDE"),
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "resolved_by": ["t"]}), "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE"),
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "resolved_by": ["v"]}), "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE"),
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "resolved_by": ["ghost"]}), "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE"),
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "resolved_by": []}), "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE"),
    (lambda r: replace(r, conflict_resolution={k: x for k, x in r.conflict_resolution.items() if k != "basis"}), "CLAIM_RESOLUTION_WITHOUT_PROVENANCE"),
    (lambda r: replace(r, conflict_resolution={**r.conflict_resolution, "provenance": {}}), "CLAIM_RESOLUTION_WITHOUT_PROVENANCE"),
    (lambda r: replace(r, agreement={**r.agreement, "conflicting_observation_ids": [["t"]]}), "CLAIM_RESOLVED_WITHOUT_PRIOR_CONFLICT"),
    (lambda r: replace(r, agreement={**r.agreement, "agreeing_observation_ids": ["t", "e", "v"]}), "CLAIM_AGREEMENT_INCONSISTENT"),
])
def test_p6_3_fabricated_resolutions_are_rejected(mutate, code):
    _base, r = resolved()
    assert code in V.validate_claim(mutate(r))


def test_p6_3_a_resolution_by_an_unknown_or_uninterpreted_observation_is_rejected():
    for bad_e in (unknown_obs("e", EPISODE_STATE), obs("e", EPISODE_STATE, interpretation=None)):
        base = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease"), bad_e])
        r = replace(base, agreement={"status": RESOLVED, "agreeing_observation_ids": ["t"], "conflicting_observation_ids": [["t"], ["v"]]},
                    conflict_resolution={"resolved_by": ["e"], "outcome": "increase", "basis": "x", "provenance": {"r": 1}})
        assert "CLAIM_RESOLUTION_OUTCOME_UNSUPPORTED" in V.validate_claim(r)


def test_p6_3_a_resolution_where_there_was_no_conflict_is_rejected():
    agree = ground([obs("t", TRANSCRIPT, "increase"), obs("e", EPISODE_STATE, "increase")])
    r = replace(agree, agreement={"status": RESOLVED, "agreeing_observation_ids": ["t", "e"], "conflicting_observation_ids": []},
                conflict_resolution={"resolved_by": ["e"], "outcome": "increase", "basis": "x", "provenance": {"r": 1}})
    assert "CLAIM_RESOLVED_WITHOUT_PRIOR_CONFLICT" in V.validate_claim(r)


def test_p6_3_lineage_originals_stay_immutable_and_only_the_resolving_evidence_is_added():
    before = conflict_claim()
    base = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease"), obs("e", EPISODE_STATE, "increase")])
    after = replace(base, agreement={"status": RESOLVED, "agreeing_observation_ids": ["t", "e"], "conflicting_observation_ids": [["t"], ["v"]]},
                    conflict_resolution={"resolved_by": ["e"], "outcome": "increase", "basis": "x", "provenance": {"r": 1}})
    assert V.validate_resolution(before, after) == []
    snapshot = before.to_dict()
    assert before.to_dict() == snapshot                                                          # building `after` did not touch `before`
    assert all(orig in after.observations for orig in before.observations)                       # every original is present, equal, unmodified


@pytest.mark.parametrize("mutate,code", [
    (lambda a: replace(a, observations=tuple(replace(o, interpretation={"kind": "direction", "value": "increase", "basis": "edited"}) if o.observation_id == "v" else o for o in a.observations)), "RESOLUTION_ALTERED_ORIGINAL"),
    (lambda a: replace(a, observations=tuple(o for o in a.observations if o.observation_id != "v")), "RESOLUTION_ALTERED_ORIGINAL"),
    (lambda a: replace(a, agreement={**a.agreement, "conflicting_observation_ids": []}), "RESOLUTION_LOST_CONFLICT_RECORD"),
    (lambda a: replace(a, observations=a.observations + (obs("z", AUDIO, "increase"),), modalities=("AUDIO", "EPISODE_STATE", "TRANSCRIPT", "VISUAL")), "RESOLUTION_EXTRA_OBSERVATIONS"),
    (lambda a: replace(a, subject={"canonical_target_id": "env2.release", "aspect": "direction"}), "RESOLUTION_SUBJECT_CHANGED"),
    (lambda a: replace(a, agreement={**a.agreement, "status": CONFLICT}), "RESOLUTION_NOT_RESOLVED"),
])
def test_p6_3_lineage_violations_are_rejected(mutate, code):
    before = conflict_claim()
    base = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease"), obs("e", EPISODE_STATE, "increase")])
    after = replace(base, agreement={"status": RESOLVED, "agreeing_observation_ids": ["t", "e"], "conflicting_observation_ids": [["t"], ["v"]]},
                    conflict_resolution={"resolved_by": ["e"], "outcome": "increase", "basis": "x", "provenance": {"r": 1}})
    assert code in V.validate_resolution(before, mutate(after))


def test_p6_3_resolving_something_that_was_not_a_conflict_is_rejected_by_lineage():
    agree = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "increase")])
    assert "RESOLUTION_BEFORE_NOT_CONFLICT" in V.validate_resolution(agree, agree)


def test_p6_3_originals_are_deeply_immutable_and_to_dict_returns_independent_copies():
    c = conflict_claim()
    o = c.observations[0]
    for attempt in (lambda: setattr(o, "confidence", 1.0),
                    lambda: o.interpretation.__setitem__("value", "hijacked"),
                    lambda: o.source.__setitem__("ref", "forged"),
                    lambda: o.observation.__setitem__("x", 1),
                    lambda: c.agreement.__setitem__("status", AGREEMENT),
                    lambda: c.subject.__setitem__("aspect", "other")):
        with pytest.raises((TypeError, AttributeError)):
            attempt()
    d = c.to_dict()
    d["observations"][0]["interpretation"]["value"] = "hijacked"
    d["agreement"]["status"] = AGREEMENT
    assert c.observations[0].interpretation["value"] != "hijacked" and c.agreement["status"] == CONFLICT


def test_p6_3_validity_is_policy_free():
    xs = [obs("t", TRANSCRIPT, "increase", 0.6), obs("v", VISUAL, "decrease", 0.7), unknown_obs("u")]
    for policy in POLICIES:
        assert V.validate_claim(ground(xs, policy=policy)) == []                       # any policy's claim has the same valid structure
    assert list(inspect.signature(GroundingValidator.validate_claim).parameters) == ["self", "claim"]
    tree = ast.parse(Path(g.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in ("GroundingValidator", "derive_structure"):
            names = {n.id.lower() for n in ast.walk(node) if isinstance(n, ast.Name)} | {n.attr.lower() for n in ast.walk(node) if isinstance(n, ast.Attribute)}
            assert not [x for x in names if "policy" in x or "confidence_policy" in x], (node.name, names)


def test_p6_3_exhaustive_small_space_ground_output_validates_and_every_status_forgery_is_rejected():
    mods = [(TRANSCRIPT, "t"), (VISUAL, "v"), (AUDIO, "a"), (EPISODE_STATE, "e")]
    build = {"A": lambda m, i: obs(i, m, "increase", 0.6), "B": lambda m, i: obs(i, m, "decrease", 0.7),
             "U": lambda m, i: unknown_obs(i, m), "R": lambda m, i: obs(i, m, interpretation=None)}
    checked = 0
    for combo in itertools.product([None, "A", "B", "U", "R"], repeat=4):
        members = [build[k](m, i) for k, (m, i) in zip(combo, mods) if k]
        if not members:
            continue
        real = ground(members)
        assert V.validate_claim(real) == [], (combo, V.validate_claim(real))
        for alt in (SINGLE_MODALITY, AGREEMENT, CONFLICT, INSUFFICIENT):
            if alt == real.agreement["status"]:
                continue
            fake = forged(real, alt, agreeing=real.agreement["agreeing_observation_ids"] or [m.observation_id for m in members],
                          conflicting=real.agreement["conflicting_observation_ids"] or [[m.observation_id] for m in members[:2]],
                          confidence=0.0 if alt == INSUFFICIENT else real.confidence)
            assert V.validate_claim(fake), (combo, alt)
            checked += 1
    assert checked > 1000


def test_p6_5_a_conflict_resolves_only_with_additional_evidence_and_keeps_every_original():
    from serum2.producer.grounding import ground, resolve_conflict
    c = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease")])
    e = obs("e", EPISODE_STATE, "increase", 0.9)
    r = resolve_conflict(c, e, basis="plugin readback")
    assert r.agreement["status"] == RESOLVED and r.conflict_resolution["resolved_by"] == ["e"] and r.conflict_resolution["outcome"] == "increase"
    assert r.conflict_resolution["basis"] == "plugin readback" and r.conflict_resolution["provenance"]
    assert {o.observation_id for o in r.observations} == {"t", "v", "e"} and V.validate_claim(r) == []
    assert all(any(o is orig for o in r.observations) for orig in c.observations)              # A and B kept, unmodified, not replaced by X
    assert r.agreement["conflicting_observation_ids"] == c.agreement["conflicting_observation_ids"] and 0.0 <= r.confidence <= 1.0
    with pytest.raises(ValueError):
        resolve_conflict(c, c.observations[0], basis="reusing a conflicting observation is not new evidence")
    with pytest.raises(ValueError):
        resolve_conflict(c, obs("x", EPISODE_STATE, "sideways"), basis="outcome is neither conflicting interpretation")
    with pytest.raises(ValueError):
        resolve_conflict(ground([obs("t", TRANSCRIPT)]), e, basis="nothing to resolve")


def test_p6_6_grounding_cannot_change_a_real_brain_decision_and_cannot_execute():
    from serum2.producer.grounding import ground
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    strong = ground([obs("t", TRANSCRIPT, conf=0.95, subject={"canonical_target_id": "env2.release", "aspect": "direction"}),
                     obs("v", VISUAL, conf=0.95, subject={"canonical_target_id": "env2.release", "aspect": "direction"})])
    req = ProducerRequest(user_intent="longer Env2.Release to 267 ms", mode="EXECUTE", visual_mode="NEVER")
    before = ProducerBrain().execute(req)
    after = ProducerBrain(grounding_claims=[strong]).execute(req)
    assert bool(after.admitted) is False and after.execution_status == before.execution_status
