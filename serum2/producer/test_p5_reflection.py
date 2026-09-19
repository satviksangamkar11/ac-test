"""P5: Reflection Learner. P5.1 contract/classifier/validator are GREEN; later stages are strict-xfail RED and must
flip (losing the marker) when implemented."""
import ast
import copy
from pathlib import Path

import pytest

from serum2.producer import reflection_learner as rl
from serum2.producer.reflection_learner import (
    CONFIRMED, CONTRADICTED, DISCREPANCY_CLASSES, INCONCLUSIVE, KIND_FOR_CLASS, MISSING_OBSERVATION, NO_READBACK, NONE,
    NOT_EXECUTED, NOT_TESTED, VALUE_MISMATCH, ReflectionRecord, ReflectionValidator, classify_discrepancy,
)

V = ReflectionValidator()
READBACK = {"kind": "readback", "route": "PLUGIN_HOST_PARAMETER", "backend": "vst3-host", "state_sha256": "abc"}


def reflection(**over):
    d = dict(reflection_id="refl:e1:evt1", attempt={"canonical_target_id": "env1.release", "operation": "set", "operand": "838 ms",
                                                    "episode_id": "e1", "event_id": "evt1", "executed": True, "execution_status": "EXECUTED"},
             expected_outcome={"Env 1 Release": "838 ms"}, observed_outcome={"Env 1 Release": "838 ms"},
             discrepancy={"class": NONE, "differences": []}, evidence=(READBACK,), confidence=0.8,
             lesson={"kind": CONFIRMED, "statement": "expectation held", "advisory": True},
             provenance={"source_episode_ids": ["e1"]})
    d.update(over)
    return ReflectionRecord(**d)


# ---- classifier: generic, precedence-ordered -------------------------------------------------------------------
@pytest.mark.parametrize("exp,obs,executed,cls", [
    ({"k": "1"}, {"k": "1"}, True, NONE),
    ({"k": "1"}, {"k": "2"}, True, VALUE_MISMATCH),
    ({"k": "1"}, {"other": "1"}, True, MISSING_OBSERVATION),
    ({"k": "1"}, {"k": None}, True, MISSING_OBSERVATION),
    ({"k": "1"}, {}, True, NO_READBACK),
    ({"k": "1"}, {"k": "1"}, False, NOT_EXECUTED),               # a refusal/no-run is never a result, whatever was "observed"
    ({"a": "1", "b": "2"}, {"a": "9"}, True, VALUE_MISMATCH),     # one definite mismatch outranks a missing key
    ({"a": "1", "b": "2"}, {"a": "1"}, True, MISSING_OBSERVATION),
])
def test_classifier_precedence(exp, obs, executed, cls):
    assert classify_discrepancy(exp, obs, executed)["class"] == cls


def test_classifier_lists_differences_and_is_target_agnostic():
    got = classify_discrepancy({"Filter 1 Freq": "900 Hz", "Osc A Level": "50 %"}, {"Filter 1 Freq": "200 Hz", "Osc A Level": "50 %"}, True)
    assert got == {"class": VALUE_MISMATCH, "differences": [{"key": "Filter 1 Freq", "expected": "900 Hz", "observed": "200 Hz"}]}


def test_classifier_refuses_an_empty_expectation_for_an_executed_attempt():
    with pytest.raises(ValueError):
        classify_discrepancy({}, {"k": "1"}, True)


def test_every_discrepancy_class_maps_to_exactly_one_lesson_kind():
    assert set(KIND_FOR_CLASS) == set(DISCREPANCY_CLASSES) and set(KIND_FOR_CLASS.values()) == {CONFIRMED, CONTRADICTED, INCONCLUSIVE, NOT_TESTED}


# ---- contract --------------------------------------------------------------------------------------------------
def test_reflection_has_exactly_the_specified_fields_and_no_authority_fields():
    assert set(ReflectionRecord.__dataclass_fields__) == {
        "reflection_id", "attempt", "expected_outcome", "observed_outcome", "discrepancy", "evidence", "confidence", "lesson",
        "provenance", "advisory", "schema_version"}
    assert not rl._FORBIDDEN & set(ReflectionRecord.__dataclass_fields__)
    for f in ("capability", "route", "binding", "admission", "execute", "admitted"):
        assert f not in ReflectionRecord.__dataclass_fields__


def test_well_formed_reflection_is_valid():
    assert V.validate(reflection()) == []


@pytest.mark.parametrize("over,code", [
    ({"advisory": False}, "REFLECTION_NOT_ADVISORY"),
    ({"attempt": {"canonical_target_id": "env1.release", "operation": "set", "executed": True}}, "MISSING_ATTEMPT_FIELDS"),
    ({"evidence": ()}, "NO_EVIDENCE"),
    ({"confidence": 1.2}, "CONFIDENCE_OUT_OF_RANGE"),
    ({"confidence": True}, "CONFIDENCE_OUT_OF_RANGE"),
    ({"provenance": {}}, "NO_PROVENANCE"),
    ({"lesson": {"kind": "SOMETHING", "statement": "x", "advisory": True}}, "BAD_LESSON"),
    ({"lesson": {"kind": CONFIRMED, "statement": "x", "advisory": False}}, "BAD_LESSON"),
    ({"discrepancy": {"class": "WEIRD", "differences": []}}, "BAD_DISCREPANCY_CLASS"),
])
def test_malformed_reflection_is_rejected(over, code):
    assert code in V.validate(reflection(**over))


def test_forged_no_discrepancy_is_caught_by_rederivation():
    forged = reflection(observed_outcome={"Env 1 Release": "15 ms"})            # observed differs, but claims class NONE
    assert "DISCREPANCY_INCONSISTENT" in V.validate(forged)


def test_lesson_must_agree_with_the_discrepancy():
    r = reflection(observed_outcome={"Env 1 Release": "15 ms"},
                   discrepancy={"class": VALUE_MISMATCH, "differences": [{"key": "Env 1 Release", "expected": "838 ms", "observed": "15 ms"}]})
    assert "LESSON_INCONSISTENT_WITH_DISCREPANCY" in V.validate(r)               # still says CONFIRMED


def test_an_observation_needs_readback_evidence_with_a_route():
    assert "OBSERVATION_WITHOUT_READBACK_EVIDENCE" in V.validate(reflection(evidence=({"kind": "execution", "note": "ran"},)))
    assert "OBSERVATION_WITHOUT_READBACK_EVIDENCE" in V.validate(reflection(evidence=({"kind": "readback"},)))


def test_smuggled_authority_field_in_dict_or_lesson_is_rejected():
    d = reflection().to_dict()
    d["execution_route"] = "dawdreamer_serum"
    assert "REFLECTION_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate(d)
    d = reflection().to_dict()
    d["lesson"]["admitted"] = True
    assert "REFLECTION_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate(d)


def test_not_executed_reflection_is_valid_and_carries_no_observation():
    r = reflection(attempt={"canonical_target_id": "env2.release", "operation": "set", "episode_id": "e2", "executed": False,
                            "execution_status": "REFUSED_NO_EVIDENCE"},
                   observed_outcome={}, discrepancy={"class": NOT_EXECUTED, "differences": []},
                   lesson={"kind": NOT_TESTED, "statement": "not executed", "advisory": True}, evidence=({"kind": "execution", "note": "refused"},),
                   confidence=0.0, provenance={"source_episode_ids": ["e2"]})
    assert V.validate(r) == []


def test_reflection_module_imports_no_brain_admission_contract_or_backend_code():
    tree = ast.parse(Path(rl.__file__).read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not [m for m in mods if any(b in m for b in ("producer_brain", "admission", "contract_registry", "capability", "backend", "serum_mcp", "dawdreamer"))]


def test_reflection_module_names_no_target():
    tree = ast.parse(Path(rl.__file__).read_text(encoding="utf-8"))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not [c for c in consts if any(t in c.lower() for t in ("env1", "env2", "filter1", "osc"))]


# ---- RED: later stages (strict xfail; remove marker when implemented) ------------------------------------------
RED = pytest.mark.xfail(strict=True, raises=(ImportError, AttributeError), reason="P5 later stage not implemented")


@RED
def test_p5_2_record_skill_outcome_from_real_readback_evidence():
    from serum2.producer.reflection_learner import record_skill_outcome
    r = record_skill_outcome(attempt={"canonical_target_id": "env1.release", "operation": "set", "operand": "838 ms", "episode_id": "e1",
                                      "event_id": "evt1", "executed": True, "execution_status": "EXECUTED"},
                             expected={"Env 1 Release": "838 ms"}, observed={"Env 1 Release": "838 ms"}, evidence=[READBACK])
    assert r.discrepancy["class"] == NONE and r.lesson["kind"] == CONFIRMED and V.validate(r) == []


@RED
def test_p5_3_apply_reflection_updates_skill_statistics_idempotently():
    from serum2.producer.reflection_learner import apply_reflection
    from serum2.producer.test_p3_skill_library import skill
    s = skill(supporting_evidence=({"episode_id": "e0", "event_id": "x", "verified": True},), provenance={"source_episode_ids": ["e0"]})
    once = apply_reflection(s, reflection())
    assert once.outcome_stats["attempts"] == 2 and apply_reflection(once, reflection()) == once


@RED
def test_p5_4_contradicting_outcomes_worsen_lifecycle_and_never_improve_it():
    from serum2.producer.reflection_learner import derive_lifecycle_state
    assert derive_lifecycle_state([{"outcome": CONFIRMED}]) == "FRESH"
    assert derive_lifecycle_state([{"outcome": CONFIRMED}, {"outcome": CONTRADICTED}]) == "STALE"
    assert derive_lifecycle_state([{"outcome": CONFIRMED}, {"outcome": CONTRADICTED}, {"outcome": CONTRADICTED}]) == "CONTRADICTED"


@RED
def test_p5_5_detect_contradictions_is_generic():
    from serum2.producer.reflection_learner import detect_contradictions
    assert detect_contradictions([reflection()]) == []


@RED
def test_p5_6_reflections_become_p4_prior_evidence():
    from serum2.producer.reflection_learner import prior_evidence_from_reflections
    (p,) = prior_evidence_from_reflections([reflection()])
    assert (p.canonical_target_id, p.operation, p.attempts, p.verified_successes) == ("env1.release", "set", 1, 1)
