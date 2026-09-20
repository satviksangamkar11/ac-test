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
    ok = claim([t, v, e], RESOLVED, conflicting=[["t"], ["v"]], resolution=res)
    assert V.validate_claim(ok) == []
    for by in (["t"], [], ["ghost"]):
        bad = claim([t, v, e], RESOLVED, conflicting=[["t"], ["v"]], resolution={**res, "resolved_by": by})
        assert "CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE" in V.validate_claim(bad)
    for drop in ("basis", "provenance"):
        thin = claim([t, v, e], RESOLVED, conflicting=[["t"], ["v"]], resolution={k: x for k, x in res.items() if k != drop})
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
    assert c.agreement["status"] == SINGLE_MODALITY and c.agreement["agreeing_observation_ids"] == ["a", "b", "c"]
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
    assert mixed.agreement["agreeing_observation_ids"] == ["v"] and mixed.agreement["status"] == SINGLE_MODALITY


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


# ---- RED: later stages (strict xfail; remove marker when implemented) ------------------------------------------------------
RED = pytest.mark.xfail(strict=True, raises=(ImportError, AttributeError, TypeError), reason="P6 later stage not implemented")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="P6.3: validator does not yet re-derive agreement from the observations")
def test_p6_3_the_validator_rederives_agreement_so_a_forged_claim_is_caught():
    from serum2.producer.grounding import ground
    real = ground([obs("t", TRANSCRIPT, "increase"), obs("v", VISUAL, "decrease")])
    forged = replace(real, agreement={"status": AGREEMENT, "agreeing_observation_ids": ["t", "v"], "conflicting_observation_ids": []}, confidence=0.9)
    assert "CLAIM_AGREEMENT_INCONSISTENT" in V.validate_claim(forged)


@RED
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


@RED
def test_p6_4_adapter_turns_a_fusion_event_into_transcript_and_visual_observations_with_provenance():
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
def test_p6_4_adapter_keeps_measurements_real_and_unknowns_unknown():
    from serum2.producer.grounding import observations_from_measurement
    done = {"status": "MEASURED", "acoustic_status": "COMPUTED", "sha256": "abc", "measurement_definition_id": "g8-basic-acoustic-v1",
            "rms_db": -23.01, "peak_db": -10.86, "spectral_centroid_hz": 3711.6}
    out = observations_from_measurement(done)
    assert {o.status for o in out} == {MEASURED} and all(o.source["method"] == "g8-basic-acoustic-v1" for o in out) and all(V.validate_observation(o) == [] for o in out)
    for status in ("NO_RENDER", "FILE_NOT_FOUND", "EMPTY_AUDIO", "MEASUREMENT_ERROR"):
        unk = observations_from_measurement({"status": status, "acoustic_status": "NOT_ATTEMPTED"})
        assert unk and all(o.status == UNKNOWN and o.confidence == 0.0 and V.validate_observation(o) == [] for o in unk)


@RED
def test_p6_4_adapter_turns_episode_readback_into_episode_state_observations():
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
