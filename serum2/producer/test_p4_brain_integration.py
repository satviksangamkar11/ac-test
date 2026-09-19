"""P4.4: the selected advisory candidate flows through the REAL Producer Brain path:

  ProducerRequest -> B1 UPI -> CandidateGenerator -> CandidateRanker -> selected Candidate -> to_intent()
  -> (direction into the step-6.2 UPI) -> Capability Resolution -> Admission -> existing plan.

No second brain/executor/gate: these tests exercise ProducerBrain itself.
"""
import builtins
import socket
import subprocess

import pytest

from serum2.producer import candidate_ranking as cr
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer.skill_library import SkillRecord, SkillRetriever
from serum2.producer.target_resolution import LEGACY_STATUS_TO_REFUSAL

ENV1 = "longer Env1.Release"
ENV2 = "longer Env2.Release to 267 ms"


def skill(target="env1.release", op="SET", conf=0.95, sid=None, **kw):
    return SkillRecord(skill_id=sid or "skill:%s:%s" % (target, op.lower()), canonical_target_id=target, target_concept="c",
                       semantic_target="T", operation=op, trigger={"observed_change": {"before": "15 ms", "after": "838 ms"}},
                       preconditions=(), supporting_evidence=({"episode_id": "e", "verified": True},), outcome_stats={},
                       confidence=conf, provenance={"source_episode_ids": ["e"]}, **kw)


def run(text, *skills, brain=None, prior=()):
    brain = brain or ProducerBrain(skill_retriever=SkillRetriever(skills) if skills else None, prior_evidence=prior)
    return brain.execute(ProducerRequest(user_intent=text, mode="EXECUTE", visual_mode="NEVER"))


def decision(r):
    return (bool(r.admitted), r.execution_status, r.semantic_target, r.execution_route, str(r.semantic_direction),
            (getattr(r, "_serum_preset_plan", None) or {}).get("contract_id"),
            (r.refusal or {}).get("code"))


# ---- the candidate layer is on the real path ------------------------------------------------------------
def test_real_brain_records_the_candidate_layer_on_every_canonical_request():
    r = run(ENV1)
    b = r.b1_intent
    assert b["candidate_layer"] == "ADVISORY" and len(b["candidates"]) == 1 and b["selected_overrides_primary"] is False
    assert b["selected_candidate_id"] == b["candidates"][0]["candidate_id"]


def test_multiple_candidates_are_generated_and_ranked_when_skills_exist():
    r = run(ENV1, skill(conf=0.2))
    cands = r.b1_intent["candidates"]
    assert len(cands) == 2 and [c["rank"] for c in cands] == [1, 2]
    assert {c["origin"] for c in cands} == {"PRIMARY", "SKILL_VARIANT"} and all(c["advisory"] for c in cands)


def test_weak_skill_leaves_the_primary_selected():
    assert run(ENV1, skill(conf=0.2)).b1_intent["selected_overrides_primary"] is False


def test_strong_same_target_skill_promotes_a_variant_visibly_and_the_chain_still_admits_it():
    base = run(ENV1)
    r = run(ENV1, skill(conf=0.95))
    b = r.b1_intent
    assert b["selected_overrides_primary"] is True and b["operation"]["operation"] == "set"   # the selected candidate became the UPI
    assert decision(r) == decision(base) and r.admitted is True                                # existing chain, same authority outcome
    assert decision(r)[5] == "envelope_field_release"


def test_selected_candidate_never_changes_the_resolved_target():
    for skills in ([], [skill(conf=1.0)], [skill(conf=1.0), skill("env2.release", conf=1.0)]):
        r = run(ENV1, *skills)
        assert {c["canonical_target"] for c in r.b1_intent["candidates"]} == {"env1.release"}
        assert r.semantic_target == "Env1.Release"


def test_skill_cannot_flip_the_requested_direction():
    base = run(ENV1)
    r = run(ENV1, skill(op="DECREASE", conf=1.0))
    assert len(r.b1_intent["candidates"]) == 1 and str(r.semantic_direction) == str(base.semantic_direction)


def test_skills_of_other_targets_do_not_enter_the_candidate_set():
    assert len(run(ENV1, skill("env2.release", conf=1.0)).b1_intent["candidates"]) == 1


# ---- authority boundaries against the real chain -------------------------------------------------------
@pytest.mark.parametrize("text,variant", [("longer Env2.Release", True), (ENV2, False)])
def test_env2_stays_refused_no_capability_even_with_maximal_skill_evidence(text, variant):
    base = run(text)
    r = run(text, skill("env2.release", conf=1.0), skill("env1.release", conf=1.0))
    assert decision(r) == decision(base)
    assert r.admitted in (None, False) and LEGACY_STATUS_TO_REFUSAL[r.execution_status][0] == "REFUSED_NO_CAPABILITY"
    assert r.b1_intent["selected_overrides_primary"] is variant        # the candidate layer ranked (and, if it could, overrode) ...
    assert {c["canonical_target"] for c in r.b1_intent["candidates"]} == {"env2.release"}   # ... on the same target only, gaining nothing


def test_candidate_layer_creates_no_capability():
    brain = ProducerBrain(skill_retriever=SkillRetriever([skill("env2.release", conf=1.0), skill(conf=1.0)]))
    before = {k: getattr(v, "status", None) for k, v in brain._registry.contracts.items()}
    run(ENV2, brain=brain)
    run(ENV1, brain=brain)
    assert {k: getattr(v, "status", None) for k, v in brain._registry.contracts.items()} == before


def test_every_selected_candidate_still_goes_through_capability_resolution_and_admission(monkeypatch):
    calls = []
    orig = ProducerBrain._resolve_and_admit

    def spy(self, candidate, intent, contract):
        calls.append(str(intent.semantic_direction))
        return orig(self, candidate, intent, contract)

    monkeypatch.setattr(ProducerBrain, "_resolve_and_admit", spy)
    r = run(ENV1, skill(conf=0.95))
    assert r.b1_intent["selected_overrides_primary"] is True and len(calls) == 1 and r.admitted is True


def test_a_failing_admission_is_not_bypassed_by_the_candidate_layer(monkeypatch):
    def deny(self, candidate, intent, contract):
        return None, None, None                                          # resolution/admission produced nothing

    monkeypatch.setattr(ProducerBrain, "_resolve_and_admit", deny)
    r = run(ENV1, skill(conf=1.0))
    assert not r.admitted


def test_candidate_code_has_no_side_effects_or_backend_reach(monkeypatch):
    real_open = builtins.open

    def guard_open(f, mode="r", *a, **k):
        if any(c in mode for c in "wax+"):
            raise AssertionError("candidate layer tried to write %r" % (f,))
        return real_open(f, mode, *a, **k)

    def boom(*a, **k):
        raise AssertionError("candidate layer reached a process/network backend")

    monkeypatch.setattr(builtins, "open", guard_open)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)
    from serum2.producer.skill_library import advise
    from serum2.producer.test_p4_candidate_ranking import intent as mk_intent
    it = mk_intent()
    ranked = cr.CandidateRanker().rank(cr.CandidateGenerator().generate(it, advise(SkillRetriever([skill()]), "env1.release"), ["env2.release"]))
    cr.to_intent(ranked.selected.candidate, it)
    r = run(ENV1, skill(conf=0.95))                                      # whole plan-only Brain path too
    assert r.admitted is True


def test_brain_without_a_retriever_behaves_exactly_as_before_for_admission():
    assert decision(run(ENV1)) == decision(ProducerBrain().execute(ProducerRequest(user_intent=ENV1, mode="EXECUTE", visual_mode="NEVER")))


# ---- P4.5 / P4.6 through the real Brain ---------------------------------------------------------------------
from serum2.producer.candidate_ranking import PriorEpisodeEvidence


def prior(target="env1.release", op="set", n=20):
    return PriorEpisodeEvidence(target, op, n, n, tuple("e%d" % i for i in range(n)))


def test_prior_evidence_influences_the_real_path_visibly_and_admission_is_unchanged():
    base = run(ENV1)
    plain = run(ENV1, skill(conf=0.6))
    tipped = run(ENV1, skill(conf=0.6), prior=(prior(),))
    assert plain.b1_intent["selected_overrides_primary"] is False and tipped.b1_intent["selected_overrides_primary"] is True
    sel = next(c for c in tipped.b1_intent["candidates"] if c["candidate_id"] == tipped.b1_intent["selected_candidate_id"])
    assert sel["features"]["prior_attempts"] == 20 and len(sel["features"]["prior_episode_ids"]) == 20
    assert decision(tipped) == decision(base)


def test_prior_evidence_cannot_create_capability_for_env2():
    base = run(ENV2)
    r = run(ENV2, prior=(prior("env2.release", "set", 500), prior("env2.release", "increase", 500)))
    assert decision(r) == decision(base) and LEGACY_STATUS_TO_REFUSAL[r.execution_status][0] == "REFUSED_NO_CAPABILITY"


def test_contradicted_skill_does_not_influence_the_real_path_and_is_reported():
    r = run(ENV1, skill(conf=1.0, lifecycle_state="CONTRADICTED"))
    assert len(r.b1_intent["candidates"]) == 1 and r.b1_intent["selected_overrides_primary"] is False
    assert r.b1_intent["excluded_skills"] == [{"skill_id": "skill:env1.release:set", "reason": "LIFECYCLE: CONTRADICTED"}]
    assert r.admitted is True


def test_invalid_skill_does_not_break_or_influence_the_request_and_is_reported():
    r = run(ENV1, skill(conf=1.0, advisory=False))
    assert len(r.b1_intent["candidates"]) == 1 and r.admitted is True
    assert r.b1_intent["excluded_skills"][0]["reason"].startswith("INVALID")


def test_stale_skill_is_penalised_on_the_real_path():
    assert run(ENV1, skill(conf=0.95)).b1_intent["selected_overrides_primary"] is True
    assert run(ENV1, skill(conf=0.95, lifecycle_state="STALE")).b1_intent["selected_overrides_primary"] is False


def test_retired_skill_is_dropped():
    r = run(ENV1, skill(conf=1.0, lifecycle_state="RETIRED"))
    assert len(r.b1_intent["candidates"]) == 1
