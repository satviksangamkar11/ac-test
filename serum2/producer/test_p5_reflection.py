"""P5: Reflection Learner -- contract, classifier, record_skill_outcome, skill statistics, lifecycle, contradiction
detection, and feedback into P4, with the authority boundaries checked against the real Brain."""
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


# ---- P5.2 record_skill_outcome ------------------------------------------------------------------------------------
from serum2.producer.reflection_learner import (
    apply_reflection, attempt_from_result, attempt_id, detect_contradictions, prior_evidence_from_reflections, record_skill_outcome,
    update_skill_store,
)
from serum2.producer.skill_library import (
    SkillStore, derive_lifecycle_state, extract_skill, retire_skill, worse_state,
)
from serum2.producer.test_p3_skill_library import episode as verified_episode, skill as p3_skill

ATT = {"canonical_target_id": "env1.release", "operation": "set", "operand": "838 ms", "episode_id": "e1", "event_id": "evt1",
       "executed": True, "execution_status": "EXECUTED"}


def outcome(observed, **att):
    return record_skill_outcome(attempt={**ATT, **att}, expected={"Env 1 Release": "838 ms"}, observed=observed, evidence=[READBACK])


def test_p5_2_successful_execution_becomes_a_confirmed_reflection_with_preserved_evidence():
    r = outcome({"Env 1 Release": "838 ms"})
    assert r.discrepancy == {"class": NONE, "differences": []} and r.lesson["kind"] == CONFIRMED and V.validate(r) == []
    assert r.evidence == (READBACK,) and dict(r.observed_outcome) == {"Env 1 Release": "838 ms"}
    assert r.lesson["advisory"] is True and r.advisory is True and r.provenance["source_episode_ids"] == ["e1"]


def test_p5_2_failed_execution_becomes_a_contradicted_reflection_with_the_discrepancy_recorded():
    r = outcome({"Env 1 Release": "15 ms"})
    assert r.lesson["kind"] == CONTRADICTED and r.discrepancy["class"] == VALUE_MISMATCH
    assert r.discrepancy["differences"] == [{"key": "Env 1 Release", "expected": "838 ms", "observed": "15 ms"}]
    assert "15 ms" in r.lesson["statement"] and V.validate(r) == []


def test_p5_2_success_is_not_inferred_from_admission_or_a_claim():
    planned = record_skill_outcome(attempt={**ATT, "executed": False, "execution_status": "SERUM_PRESET_PLAN_READY"},
                                   expected={"Env 1 Release": "838 ms"}, observed={"Env 1 Release": "838 ms"}, evidence=[READBACK])
    assert planned.discrepancy["class"] == NOT_EXECUTED and planned.lesson["kind"] == NOT_TESTED and dict(planned.observed_outcome) == {}
    no_rb = record_skill_outcome(attempt=ATT, expected={"Env 1 Release": "838 ms"}, observed={"Env 1 Release": "838 ms"}, evidence=[])
    assert no_rb.discrepancy["class"] == NO_READBACK and no_rb.lesson["kind"] == INCONCLUSIVE and dict(no_rb.observed_outcome) == {}
    assert V.validate(planned) == [] and V.validate(no_rb) == []


def test_p5_2_a_refusal_is_never_an_outcome_even_with_a_matching_observation():
    r = record_skill_outcome(attempt={**ATT, "executed": True, "execution_status": "REFUSED_NO_EVIDENCE"},
                             expected={"Env 1 Release": "838 ms"}, observed={"Env 1 Release": "838 ms"}, evidence=[READBACK])
    assert r.discrepancy["class"] == NOT_EXECUTED and r.lesson["kind"] == NOT_TESTED and r.attempt["executed"] is False


def test_p5_2_confidence_is_bounded_and_scales_with_observed_coverage():
    full = record_skill_outcome(attempt=ATT, expected={"a": "1", "b": "2"}, observed={"a": "1", "b": "2"}, evidence=[READBACK])
    half = record_skill_outcome(attempt=ATT, expected={"a": "1", "b": "2"}, observed={"a": "1"}, evidence=[READBACK])
    none = record_skill_outcome(attempt=ATT, expected={"a": "1"}, observed={}, evidence=[READBACK])
    assert full.confidence == rl.MAX_CONFIDENCE <= 1.0 and half.confidence == rl.MAX_CONFIDENCE / 2 and none.confidence == 0.0
    assert half.discrepancy["class"] == MISSING_OBSERVATION and half.lesson["kind"] == INCONCLUSIVE


def test_p5_2_is_target_agnostic_and_deterministic():
    a = {**ATT, "canonical_target_id": "filter1.cutoff", "operand": "900 Hz"}
    r1 = record_skill_outcome(attempt=a, expected={"Filter 1 Freq": "900 Hz"}, observed={"Filter 1 Freq": "900 Hz"}, evidence=[READBACK])
    r2 = record_skill_outcome(attempt=a, expected={"Filter 1 Freq": "900 Hz"}, observed={"Filter 1 Freq": "900 Hz"}, evidence=[READBACK])
    assert r1 == r2 and r1.lesson["kind"] == CONFIRMED and r1.reflection_id == "refl:e1:evt1"


def test_p5_2_bad_attempts_are_refused():
    with pytest.raises(ValueError):
        record_skill_outcome(attempt={"operation": "set"}, expected={"k": "v"}, observed={}, evidence=[])
    with pytest.raises(ValueError):
        record_skill_outcome(attempt=ATT, expected={}, observed={"k": "v"}, evidence=[READBACK])       # nothing to compare against


def test_p5_2_admitted_plan_ready_brain_result_is_not_an_execution_but_a_finalized_one_is():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    res = ProducerBrain().execute(ProducerRequest(user_intent="longer Env1.Release to 838 ms", mode="EXECUTE", visual_mode="NEVER"))
    assert res.execution_status == "SERUM_PRESET_PLAN_READY" and res.admitted is True
    planned = attempt_from_result(res, episode_id="e9")
    assert planned["executed"] is False                                  # admission != execution
    ProducerBrain().finalize_serum_preset_execution(res, preset_path="p", preset_sha256="abc", ui_readback={"Env 1 Release": "838 ms"}, readback_verified=True)
    done = attempt_from_result(res, episode_id="e9")
    assert done["executed"] is True and done["canonical_target_id"] == "env1.release"
    r = record_skill_outcome(attempt=done, expected={"Env 1 Release": "838 ms"}, observed=res.serum_preset_execution["ui_readback"], evidence=[READBACK])
    assert r.lesson["kind"] == CONFIRMED


# ---- P5.3 statistics: one attempt = one count across every representation ----------------------------------------------
def skill_from_episode(eid="e1"):
    return extract_skill(verified_episode(experience_id=eid))


def test_p5_3_same_attempt_is_idempotent_and_agrees_with_the_extracted_evidence():
    s = skill_from_episode("e1")                                          # evidence key ("e1", None)
    same = record_skill_outcome(attempt={**ATT, "event_id": None}, expected={"Env 1 Release": "838 ms"},
                                observed={"Env 1 Release": "838 ms"}, evidence=[READBACK])
    once = apply_reflection(s, same)
    assert once == s and once.outcome_stats["attempts"] == 1               # the P3 extraction already counted this execution
    assert apply_reflection(once, same) == once


def test_p5_3_a_new_episode_merges_statistics_and_recomputes_confidence():
    s = skill_from_episode("e1")
    new = record_skill_outcome(attempt={**ATT, "episode_id": "e2", "event_id": None}, expected={"Env 1 Release": "838 ms"},
                               observed={"Env 1 Release": "15 ms"}, evidence=[READBACK])
    m = apply_reflection(s, new)
    assert m.outcome_stats == {"attempts": 2, "verified_successes": 1, "distinct_episodes": 2} and m.confidence == 1 / 6
    assert [e["episode_id"] for e in m.supporting_evidence] == ["e1", "e2"] and m.provenance["source_episode_ids"] == ["e1", "e2"]
    assert apply_reflection(m, new) == m


def test_p5_3_an_inconclusive_attempt_counts_as_an_attempt_but_not_a_success_or_a_contradiction():
    s = skill_from_episode("e1")
    inc = record_skill_outcome(attempt={**ATT, "episode_id": "e2", "event_id": None}, expected={"Env 1 Release": "838 ms"}, observed={}, evidence=[READBACK])
    m = apply_reflection(s, inc)
    assert m.outcome_stats["attempts"] == 2 and m.outcome_stats["verified_successes"] == 1 and m.lifecycle_state == "FRESH"


def test_p5_3_not_tested_reflection_changes_nothing():
    s = skill_from_episode("e1")
    nt = record_skill_outcome(attempt={**ATT, "episode_id": "e3", "executed": False, "execution_status": "SERUM_PRESET_PLAN_READY"},
                              expected={"Env 1 Release": "838 ms"}, observed=None, evidence=[])
    assert apply_reflection(s, nt) is s


def test_p5_3_reflection_cannot_update_a_different_skill_and_conflicting_outcomes_raise():
    s = skill_from_episode("e1")
    other = record_skill_outcome(attempt={**ATT, "canonical_target_id": "filter1.cutoff"}, expected={"k": "1"}, observed={"k": "1"}, evidence=[READBACK])
    with pytest.raises(ValueError):
        apply_reflection(s, other)
    conflict = record_skill_outcome(attempt={**ATT, "episode_id": "e1", "event_id": None}, expected={"Env 1 Release": "838 ms"},
                                    observed={"Env 1 Release": "15 ms"}, evidence=[READBACK])    # e1 was already CONFIRMED
    with pytest.raises(ValueError):
        apply_reflection(s, conflict)


def test_p5_3_one_execution_is_one_attempt_in_skill_prior_and_reflection_representations():
    from serum2.producer.candidate_ranking import attempts_from_episodes, prior_evidence_from_attempts
    ep = verified_episode(experience_id="e1")
    s = extract_skill(ep)
    refl = record_skill_outcome(attempt={**ATT, "event_id": None}, expected={"Env 1 Release": "838 ms"},
                                observed={"Env 1 Release": "838 ms"}, evidence=[READBACK])
    s2 = apply_reflection(s, refl)
    (from_ep,) = prior_evidence_from_attempts(attempts_from_episodes([ep]))
    (from_refl,) = prior_evidence_from_reflections([refl])
    (combined,) = prior_evidence_from_attempts(list(attempts_from_episodes([ep])) + list(rl.attempts_from_reflections([refl])))
    assert s2.outcome_stats["attempts"] == from_ep.attempts == from_refl.attempts == combined.attempts == 1


# ---- P5.4 lifecycle: evidence-driven, monotone, capability untouched ---------------------------------------------------
def test_p5_4_lifecycle_derivation_from_outcomes():
    C, X, I = {"outcome": CONFIRMED}, {"outcome": CONTRADICTED}, {"outcome": INCONCLUSIVE}
    assert derive_lifecycle_state([C]) == "FRESH" and derive_lifecycle_state([C, I, I]) == "FRESH"
    assert derive_lifecycle_state([C, X]) == "STALE" and derive_lifecycle_state([C, C, X]) == "STALE"
    assert derive_lifecycle_state([C, X, X]) == "CONTRADICTED" and derive_lifecycle_state([X]) == "CONTRADICTED"
    assert derive_lifecycle_state([{"verified": True}, {"verified": False}]) == "STALE"          # pre-outcome entries still map


def bad(eid):
    return record_skill_outcome(attempt={**ATT, "episode_id": eid, "event_id": None}, expected={"Env 1 Release": "838 ms"},
                                observed={"Env 1 Release": "15 ms"}, evidence=[READBACK])


def good(eid):
    return record_skill_outcome(attempt={**ATT, "episode_id": eid, "event_id": None}, expected={"Env 1 Release": "838 ms"},
                                observed={"Env 1 Release": "838 ms"}, evidence=[READBACK])


def test_p5_4_contradictions_walk_a_skill_fresh_stale_contradicted():
    s = skill_from_episode("e1")
    assert s.lifecycle_state == "FRESH"
    s = apply_reflection(s, bad("e2"))
    assert s.lifecycle_state == "STALE"
    s = apply_reflection(s, bad("e3"))
    assert s.lifecycle_state == "CONTRADICTED" and s.advisory is True


def test_p5_4_a_contradicted_skill_is_never_healed_by_later_confirmations_or_merging():
    s = apply_reflection(apply_reflection(skill_from_episode("e1"), bad("e2")), bad("e3"))
    for i in range(4, 9):
        s = apply_reflection(s, good("e%d" % i))
    assert derive_lifecycle_state(s.supporting_evidence) == "STALE"                 # the evidence alone would now read STALE ...
    assert s.lifecycle_state == "CONTRADICTED"                                      # ... but the stored state never improves


def test_p5_4_retiring_is_explicit_sticky_and_needs_a_reason(tmp_path):
    s = skill_from_episode("e1")
    with pytest.raises(ValueError):
        retire_skill(s, " ")
    r = retire_skill(s, "superseded by a better-evidenced skill")
    assert r.lifecycle_state == "RETIRED" and r.provenance["retired_reason"]
    st = SkillStore(tmp_path)
    st.save(r)
    st.add_episode(verified_episode(experience_id="e7"))
    assert st.load(r.skill_id).lifecycle_state == "RETIRED"                          # new verified evidence cannot revive it
    assert worse_state("FRESH", "STALE") == "STALE" and worse_state("RETIRED", "FRESH") == "RETIRED"


# ---- P5.5 contradiction detection ---------------------------------------------------------------------------------------
def test_p5_5_detect_contradictions_is_generic_across_targets_and_filters_by_skill():
    other = record_skill_outcome(attempt={**ATT, "canonical_target_id": "filter1.cutoff"}, expected={"F": "900 Hz"}, observed={"F": "200 Hz"}, evidence=[READBACK])
    refs = [good("e1"), bad("e2"), other, record_skill_outcome(attempt=ATT | {"episode_id": "e5", "event_id": "x"}, expected={"k": "1"}, observed={}, evidence=[READBACK])]
    assert {r.attempt["canonical_target_id"] for r in detect_contradictions(refs)} == {"env1.release", "filter1.cutoff"}
    assert [r.attempt["episode_id"] for r in detect_contradictions(refs, skill_from_episode())] == ["e2"]


def test_p5_5_invalid_reflections_are_ignored_not_trusted():
    forged = reflection(observed_outcome={"Env 1 Release": "15 ms"})                 # claims NONE but differs
    assert detect_contradictions([forged]) == []


# ---- P5.6 feedback into P4 -------------------------------------------------------------------------------------------
def test_p5_6_reflections_become_p4_prior_evidence_counting_each_attempt_once():
    refs = [good("e1"), good("e1"), bad("e2"), record_skill_outcome(attempt={**ATT, "episode_id": "e3", "executed": False}, expected={"k": "v"}, evidence=[])]
    (p,) = prior_evidence_from_reflections(refs)
    assert (p.canonical_target_id, p.operation, p.attempts, p.verified_successes, p.episode_ids) == ("env1.release", "set", 2, 1, ("e1", "e2"))


def test_p5_6_update_skill_store_updates_existing_skills_but_never_creates_one(tmp_path):
    st = SkillStore(tmp_path)
    assert update_skill_store(st, bad("e2")) is None and st.all() == []              # reflection cannot create a skill
    st.add_episode(verified_episode(experience_id="e1"))
    got = update_skill_store(st, bad("e2"))
    assert got.lifecycle_state == "STALE" and got.outcome_stats["attempts"] == 2
    path = st._path(got.skill_id)
    raw = path.read_bytes()
    update_skill_store(st, bad("e2"))
    assert path.read_bytes() == raw                                                  # repeated same episode: idempotent on disk


# ---- P5 boundaries against the real Brain ------------------------------------------------------------------------------
def _decision(text, retriever=None):
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.target_resolution import LEGACY_STATUS_TO_REFUSAL
    r = ProducerBrain(skill_retriever=retriever).execute(ProducerRequest(user_intent=text, mode="EXECUTE", visual_mode="NEVER"))
    return r, (bool(r.admitted), r.execution_status, r.semantic_target, r.execution_route, str(r.semantic_direction),
               (getattr(r, "_serum_preset_plan", None) or {}).get("contract_id"), (r.refusal or {}).get("code"))


def test_p5_reflection_cannot_change_admission_for_a_qualified_target_even_when_it_contradicts_the_skill(tmp_path):
    from serum2.producer.skill_library import SkillRetriever
    _, before = _decision("longer Env1.Release")
    st = SkillStore(tmp_path)
    st.add_episode(verified_episode(experience_id="e1"))
    update_skill_store(st, bad("e2"))
    update_skill_store(st, bad("e3"))
    assert st.load("skill:env1.release:set").lifecycle_state == "CONTRADICTED"
    res, after = _decision("longer Env1.Release", SkillRetriever.from_store(st))
    assert after == before and after[0] is True and after[5] == "envelope_field_release"        # Admission unchanged
    assert res.b1_intent["excluded_skills"][0]["reason"] == "LIFECYCLE: CONTRADICTED" and len(res.b1_intent["candidates"]) == 1


def test_p5_reflection_cannot_create_capability_or_override_a_refusal_for_env2(tmp_path):
    from serum2.producer.producer_brain import ProducerBrain
    from serum2.producer.skill_library import SkillRetriever
    from serum2.producer.target_resolution import LEGACY_STATUS_TO_REFUSAL
    text = "longer Env2.Release to 267 ms"
    _, before = _decision(text)
    assert before[0] is False and LEGACY_STATUS_TO_REFUSAL[before[1]][0] == "REFUSED_NO_CAPABILITY"
    confirmed = [record_skill_outcome(attempt={**ATT, "canonical_target_id": "env2.release", "episode_id": "e%d" % i, "event_id": None},
                                      expected={"Env 2 Release": "267 ms"}, observed={"Env 2 Release": "267 ms"}, evidence=[READBACK]) for i in range(20)]
    prior = prior_evidence_from_reflections(confirmed)
    assert prior[0].attempts == 20 and prior[0].verified_successes == 20
    brain = ProducerBrain(prior_evidence=prior)
    registry_before = {k: getattr(v, "status", None) for k, v in brain._registry.contracts.items()}
    from serum2.producer.producer_brain import ProducerRequest
    r = brain.execute(ProducerRequest(user_intent=text, mode="EXECUTE", visual_mode="NEVER"))
    assert bool(r.admitted) is False and r.execution_status == before[1] and (r.refusal or {}).get("code") == before[6]
    assert {k: getattr(v, "status", None) for k, v in brain._registry.contracts.items()} == registry_before


def test_p5_stale_skill_cannot_silently_become_authoritative(tmp_path):
    from serum2.producer.skill_library import SkillRetriever
    st = SkillStore(tmp_path)
    st.add_episode(verified_episode(experience_id="e1"))
    update_skill_store(st, bad("e2"))                                               # 1 vs 1 -> STALE
    r, _ = _decision("longer Env1.Release", SkillRetriever.from_store(st))
    sel = next(c for c in r.b1_intent["candidates"] if c["candidate_id"] == r.b1_intent["selected_candidate_id"])
    assert st.load("skill:env1.release:set").lifecycle_state == "STALE"
    assert all(e["lifecycle_state"] == "STALE" for c in r.b1_intent["candidates"] for e in c["evidence"]) and sel["origin"] == "PRIMARY"


def test_p5_full_loop_verified_episode_to_skill_to_candidate_to_execution_to_reflection_to_next_ranking(tmp_path):
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.skill_library import SkillRetriever
    st = SkillStore(tmp_path)
    st.add_episode(verified_episode(experience_id="e1"))                            # VerifiedEpisode -> Skill
    brain = ProducerBrain(skill_retriever=SkillRetriever.from_store(st))
    res = brain.execute(ProducerRequest(user_intent="longer Env1.Release to 838 ms", mode="EXECUTE", visual_mode="NEVER"))
    assert res.b1_intent["candidates"][0]["evidence"]                               # the skill supported the P4 candidate
    brain.finalize_serum_preset_execution(res, preset_path="p", preset_sha256="s", ui_readback={"Env 1 Release": "15 ms"}, readback_verified=False)
    att = attempt_from_result(res, episode_id="e2")                                 # Execution
    assert att["executed"] is True and res.execution_status == "EXECUTION_UNVERIFIED"
    refl = record_skill_outcome(attempt=att, expected={"Env 1 Release": "838 ms"}, observed=res.serum_preset_execution["ui_readback"], evidence=[READBACK])
    assert refl.lesson["kind"] == CONTRADICTED                                      # Readback -> Reflection / Lesson
    updated = update_skill_store(st, refl)                                          # -> skill evidence/lifecycle
    assert updated.lifecycle_state == "STALE" and updated.outcome_stats["attempts"] == 2
    nxt, _ = _decision("longer Env1.Release to 838 ms", SkillRetriever.from_store(st))   # -> future P4 ranking
    assert nxt.b1_intent["candidates"][0]["evidence"][0]["lifecycle_state"] == "STALE" and nxt.admitted is True


def test_p5_module_imports_stay_advisory_only():
    tree = ast.parse(Path(rl.__file__).read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not [m for m in mods if any(b in m for b in ("producer_brain", "admission", "contract_registry", "capability", "backend", "serum_mcp", "dawdreamer"))]
