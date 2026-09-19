"""P3: Skill Library. P3.1 contract + P3.2 validator are GREEN; later stages are strict-xfail RED
and must flip (and lose the marker) when their step is implemented."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from serum2.producer import skill_library as sl
from serum2.producer.skill_library import SkillQualificationValidator, SkillRecord, VERIFIED_STATUS


def episode(**over):
    ep = SimpleNamespace(
        experience_id="vlp1_u8_HEEGN1_test",
        provenance={"brain_decision": "ProducerBrain.execute"},
        brain_decision={"decisions": [{
            "source_control_id": "env1.release", "observed_before": "15 ms", "observed_after": "838 ms",
            "resolved_concept": "note-release", "semantic_target": "Env1.Release", "admitted": True,
            "request_kwargs": {"user_intent": "longer Env1.Release to 838 ms"}}]},
        outcome={"status": VERIFIED_STATUS,
                 "verification_level": "PLUGIN_HOST_PARAMETER_READBACK (not DIRECT_UI, not causal)",
                 "real_plugin_readback": {"match": True, "expected": {"Env 1 Release": "838 ms"},
                                          "observed": {"Env 1 Release": "838 ms"}}})
    for k, v in over.items():
        setattr(ep, k, v)
    return ep


def skill(**over):
    d = dict(skill_id="skill:env1.release:set", canonical_target_id="env1.release", target_concept="note-release", semantic_target="Env1.Release",
             operation="SET", trigger={"observed_change": {"before": "15 ms", "after": "838 ms"}}, preconditions=("plugin=Serum 2.0.21",),
             supporting_evidence=({"episode_id": "e1", "before": "15 ms", "after": "838 ms"},),
             outcome_stats={"episodes": 1, "verified": 1}, confidence=0.5,
             provenance={"source_episode_ids": ["e1"]})
    d.update(over)
    return SkillRecord(**d)


V = SkillQualificationValidator()


# ---- P3.2 episode gate -------------------------------------------------------------------------
def test_verified_episode_passes_gate():
    assert V.validate_episode(episode()) == []


@pytest.mark.parametrize("mutate,code", [
    (lambda e: e.outcome.update(status="READBACK_MISMATCH"), "EPISODE_NOT_VERIFIED"),
    (lambda e: e.outcome["real_plugin_readback"].update(match=False), "READBACK_NOT_MATCHED"),
    (lambda e: e.outcome["real_plugin_readback"].update(observed={"Env 1 Release": "15 ms"}), "READBACK_NOT_MATCHED"),
    (lambda e: e.brain_decision.update(decisions=[]), "NO_DECISIONS"),
    (lambda e: e.brain_decision["decisions"][0].update(admitted=False), "DECISION_NOT_ADMITTED"),
    (lambda e: setattr(e, "provenance", {}), "NO_EPISODE_PROVENANCE"),
    (lambda e: e.outcome.update(verification_level="CAUSAL_VERIFIED"), "UNSUPPORTED_CAUSAL_CLAIM"),
])
def test_unverified_episode_is_rejected(mutate, code):
    e = copy.deepcopy(episode())
    mutate(e)
    assert code in V.validate_episode(e)


# ---- P3.1/P3.2 skill contract ------------------------------------------------------------------
def test_well_formed_skill_is_valid():
    assert V.validate_skill(skill()) == []


def test_skill_has_no_capability_or_authority_fields():
    assert not sl._FORBIDDEN_SKILL_FIELDS & set(SkillRecord.__dataclass_fields__)


@pytest.mark.parametrize("over,code", [
    ({"advisory": False}, "SKILL_NOT_ADVISORY"),
    ({"supporting_evidence": ()}, "NO_SUPPORTING_EVIDENCE"),
    ({"supporting_evidence": ({"before": "x"},)}, "NO_SUPPORTING_EVIDENCE"),
    ({"provenance": {}}, "NO_PROVENANCE"),
    ({"confidence": 1.5}, "CONFIDENCE_OUT_OF_RANGE"),
    ({"confidence": True}, "CONFIDENCE_OUT_OF_RANGE"),
    ({"operation": ""}, "MISSING_OPERATION"),
])
def test_malformed_skill_is_rejected(over, code):
    assert code in V.validate_skill(skill(**over))


def test_skill_dict_smuggling_authority_field_is_rejected():
    d = skill().to_dict()
    d["execution_route"] = "dawdreamer_serum"
    assert "SKILL_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD" in V.validate_skill(d)


def test_skill_library_imports_no_brain_admission_or_backend():
    tree = ast.parse(Path(sl.__file__).read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not [m for m in mods if any(b in m for b in ("producer_brain", "admission", "backend", "serum_mcp", "dawdreamer"))]


# ---- RED: later stages (strict xfail; remove marker when implemented) --------------------------
RED = pytest.mark.xfail(strict=True, raises=(ImportError, AttributeError), reason="P3 later stage not implemented")


def test_p3_4_extracts_env1_release_skill_from_verified_episode():
    from serum2.producer.skill_library import extract_skill
    s = extract_skill(episode())
    assert (s.canonical_target_id, s.semantic_target, s.operation, s.lifecycle_state) == ("env1.release", "Env1.Release", "SET", "FRESH")
    assert s.outcome_stats == {"attempts": 1, "verified_successes": 1, "distinct_episodes": 1}
    assert s.confidence == 0.2 and V.validate_skill(s) == []
    assert s.supporting_evidence[0]["episode_id"] == "vlp1_u8_HEEGN1_test" and s.provenance["source_episode_ids"] == ["vlp1_u8_HEEGN1_test"]


def test_p3_4_extracted_skill_carries_no_route_contract_or_binding():
    from serum2.producer.skill_library import extract_skill
    blob = repr(extract_skill(episode()).to_dict())
    for leak in ("dawdreamer_serum", "envelope_field_release", "execution_route", "contract_id", "admitted"):
        assert leak not in blob


@pytest.mark.parametrize("mutate", [
    lambda e: e.outcome.update(status="READBACK_MISMATCH"),
    lambda e: e.outcome["real_plugin_readback"].update(match=False),
    lambda e: e.brain_decision["decisions"][0].update(admitted=False),
])
def test_p3_4_extraction_refuses_unverified_episode(mutate):
    from serum2.producer.skill_library import extract_skill
    e = copy.deepcopy(episode())
    mutate(e)
    with pytest.raises(ValueError):
        extract_skill(e)


def test_p3_4_extraction_is_deterministic_and_bounds_confidence_with_one_episode():
    from serum2.producer.skill_library import extract_skill
    assert extract_skill(episode()) == extract_skill(episode()) and extract_skill(episode()).confidence < 0.5


def test_p3_4_real_heegn1_episode_yields_a_valid_skill():
    import json
    from serum2.producer.skill_library import extract_skill
    ref = Path(__file__).resolve().parents[1] / "data/runs/HEEGN1Xl5o4/exec/episode_ref.json"
    if not ref.exists():
        pytest.skip("local run artifact not present (serum2/data is gitignored)")
    from serum2.server.experience_record import load
    s = extract_skill(load(json.loads(ref.read_text())["experience_id"]))
    assert s.canonical_target_id == "env1.release" and s.trigger["observed_change"] == {"before": "15 ms", "after": "838 ms"}


def test_p3_5_store_roundtrip_is_lossless(tmp_path):
    from serum2.producer.skill_library import SkillStore, extract_skill
    st = SkillStore(tmp_path)
    s = extract_skill(episode())
    st.save(s)
    assert st.load(s.skill_id) == s and st.all() == [s]


def test_p3_5_store_refuses_invalid_skill_and_writes_nothing(tmp_path):
    from serum2.producer.skill_library import SkillStore
    with pytest.raises(ValueError):
        SkillStore(tmp_path).save(skill(advisory=False))
    assert list(tmp_path.glob("*")) == []


def test_p3_5_store_rejects_tampered_file_with_authority_field(tmp_path):
    import json
    from serum2.producer.skill_library import SkillStore, extract_skill
    st = SkillStore(tmp_path)
    path = st.save(extract_skill(episode()))
    d = json.loads(path.read_text())
    d["execution_route"] = "dawdreamer_serum"
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        st.load("skill:env1.release:set")


def test_p3_5_store_rejects_tampered_confidence(tmp_path):
    import json
    from serum2.producer.skill_library import SkillStore, extract_skill
    st = SkillStore(tmp_path)
    path = st.save(extract_skill(episode()))
    d = json.loads(path.read_text())
    d["advisory"] = False
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError):
        st.load("skill:env1.release:set")


def test_p3_6_retriever_is_deterministic_and_never_returns_capability():
    from serum2.producer.skill_library import SkillRetriever, extract_skill
    r = SkillRetriever([extract_skill(episode())])
    a = r.retrieve(canonical_target_id="env1.release", operation="SET")
    assert a == r.retrieve(canonical_target_id="env1.release", operation="SET") and len(a) == 1
    assert r.retrieve(canonical_target_id="filter1.cutoff", operation="SET") == []
    assert r.retrieve(canonical_target_id="env1.release", operation="TOGGLE") == []


def test_p3_6_retrieval_order_and_retired_exclusion_are_deterministic():
    from serum2.producer.skill_library import SkillRetriever
    lo = skill(skill_id="skill:b", confidence=0.2)
    hi = skill(skill_id="skill:a", confidence=0.4)
    dead = skill(skill_id="skill:c", confidence=0.9, lifecycle_state="RETIRED")
    got = SkillRetriever([lo, dead, hi]).retrieve(canonical_target_id="env1.release")
    assert [k.skill_id for k in got] == ["skill:a", "skill:b"]


def test_p3_6_retriever_from_store(tmp_path):
    from serum2.producer.skill_library import SkillRetriever, SkillStore, extract_skill
    st = SkillStore(tmp_path)
    st.save(extract_skill(episode()))
    assert len(SkillRetriever.from_store(st).retrieve(canonical_target_id="env1.release")) == 1


def test_p3_6_stored_and_retrieved_skill_is_not_thereby_more_trusted_or_permitted():
    from serum2.producer.skill_library import SkillRetriever, extract_skill
    sk = extract_skill(episode())
    (got,) = SkillRetriever([sk]).retrieve(canonical_target_id="env1.release", operation="SET")
    assert got == sk and got.confidence == 0.2 and got.lifecycle_state == "FRESH" and got.advisory is True


def test_p3_operation_is_data_derived_not_target_conditioned():
    from serum2.producer.skill_library import extract_skill
    e = copy.deepcopy(episode())
    d = e.brain_decision["decisions"][0]
    d.update(source_control_id="filter1.cutoff", semantic_target="Filter1.Cutoff", resolved_concept="filter-cutoff",
             observed_before="200 Hz", observed_after="900 Hz")
    assert extract_skill(e).operation == "SET"                       # same data shape, different target
    d["operation"] = "toggle"
    assert extract_skill(e).operation == "TOGGLE"                    # explicit data wins
    d.pop("operation"); d["observed_after"] = None
    with pytest.raises(ValueError):                                  # no data -> no guessed default
        extract_skill(e)


def test_p3_skill_library_source_names_no_target():
    tree = ast.parse(Path(sl.__file__).read_text(encoding="utf-8"))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not [c for c in consts if any(t in c.lower() for t in ("env1", "env2", "filter1", "osc"))]


def test_p3_7_advisory_has_only_relevance_fields():
    from serum2.producer.skill_library import SkillAdvisory
    assert set(SkillAdvisory.__dataclass_fields__) == {
        "skill_id", "canonical_target_id", "operation", "trigger", "preconditions", "supporting_evidence",
        "outcome_statistics", "confidence", "provenance", "lifecycle_state", "advisory_only"}
    assert not sl._FORBIDDEN_SKILL_FIELDS & set(SkillAdvisory.__dataclass_fields__)


def test_p3_7_advisory_is_read_only_and_deeply_immutable():
    from serum2.producer.skill_library import SkillAdvisory, extract_skill
    adv = SkillAdvisory.from_skill(extract_skill(episode()))
    with pytest.raises(Exception):
        adv.confidence = 1.0
    with pytest.raises(TypeError):
        adv.outcome_statistics["verified_successes"] = 99
    with pytest.raises(TypeError):
        adv.trigger["observed_change"]["after"] = "x"


def test_p3_7_advisory_cannot_execute_or_grant_authority():
    from serum2.producer.skill_library import SkillAdvisory, extract_skill
    adv = SkillAdvisory.from_skill(extract_skill(episode()))
    assert adv.advisory_only is True
    for attr in ("execute", "admitted", "execution_route", "contract_id", "binding", "capability", "run"):
        assert not hasattr(adv, attr)


def test_p3_7_advisory_cannot_be_used_as_an_execution_request():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.skill_library import SkillAdvisory, extract_skill
    adv = SkillAdvisory.from_skill(extract_skill(episode()))
    with pytest.raises(TypeError):
        ProducerRequest(**adv.to_dict())
    with pytest.raises(Exception):
        ProducerBrain().execute(adv)


def test_p3_7_advisory_refuses_invalid_skill():
    from serum2.producer.skill_library import SkillAdvisory
    with pytest.raises(ValueError):
        SkillAdvisory.from_skill(skill(advisory=False))


def test_p3_7_advise_projects_retrieved_skills_in_retrieval_order():
    from serum2.producer.skill_library import SkillRetriever, advise
    r = SkillRetriever([skill(skill_id="skill:b", confidence=0.2), skill(skill_id="skill:a", confidence=0.4)])
    assert [a.skill_id for a in advise(r, "env1.release")] == ["skill:a", "skill:b"]


# ---- P3.8 hard boundary: Skill != Capability != Authority, against the real Brain ------------------
def _brain_outcome(intent):
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.target_resolution import LEGACY_STATUS_TO_REFUSAL
    r = ProducerBrain().execute(ProducerRequest(user_intent=intent, mode="EXECUTE", visual_mode="NEVER"))
    return (bool(r.admitted), r.execution_status, LEGACY_STATUS_TO_REFUSAL.get(r.execution_status or "", (None,))[0],
            (getattr(r, "_serum_preset_plan", None) or {}).get("contract_id"))


def _env2_episode():
    e = copy.deepcopy(episode())
    e.brain_decision["decisions"][0].update(source_control_id="env2.release", semantic_target="Env2.Release",
                                            resolved_concept="canonical:env2.release", observed_after="267 ms")
    e.outcome["real_plugin_readback"].update(expected={"Env 2 Release": "267 ms"}, observed={"Env 2 Release": "267 ms"})
    return e


def test_p3_8_skill_for_unqualified_target_does_not_create_capability(tmp_path):
    from serum2.producer.skill_library import SkillRetriever, SkillStore, advise, extract_skill
    intent = "longer Env2.Release to 267 ms"
    before = _brain_outcome(intent)
    assert before[0] is False and before[2] == "REFUSED_NO_CAPABILITY"
    st = SkillStore(tmp_path)
    st.save(extract_skill(_env2_episode()))                          # skill exists
    (adv,) = advise(SkillRetriever.from_store(st), "env2.release", "SET")   # retrieved + advisory produced
    assert adv.canonical_target_id == "env2.release"
    after = _brain_outcome(intent)                                   # Capability Resolution + Admission
    assert after == before and after[0] is False and after[2] == "REFUSED_NO_CAPABILITY"


def test_p3_8_skill_for_qualified_target_leaves_capability_decision_unchanged(tmp_path):
    from serum2.producer.skill_library import SkillRetriever, SkillStore, advise, extract_skill
    intent = "longer Env1.Release to 838 ms"
    before = _brain_outcome(intent)
    assert before[0] is True and before[3] == "envelope_field_release"
    st = SkillStore(tmp_path)
    st.save(extract_skill(episode()))
    advise(SkillRetriever.from_store(st), "env1.release")
    assert _brain_outcome(intent) == before


def test_p3_8_retrieval_never_promotes_confidence_lifecycle_or_statistics(tmp_path):
    from serum2.producer.skill_library import SkillRetriever, SkillStore, advise, extract_skill
    st = SkillStore(tmp_path)
    path = st.save(extract_skill(episode()))
    raw = path.read_bytes()
    r = SkillRetriever.from_store(st)
    for _ in range(5):
        (adv,) = advise(r, "env1.release")
        (got,) = r.retrieve("env1.release")
    assert path.read_bytes() == raw                                  # store untouched by retrieval
    assert (got.confidence, got.lifecycle_state, dict(got.outcome_stats)) == (0.2, "FRESH", {
        "attempts": 1, "verified_successes": 1, "distinct_episodes": 1})
    assert adv.confidence == 0.2 and st.load(got.skill_id) == got


def test_p3_8_skill_library_cannot_reach_capability_or_admission_code():
    tree = ast.parse(Path(sl.__file__).read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not [m for m in mods if any(b in m for b in ("contract_registry", "capability", "admission", "producer_brain", "backend_dispatcher"))]


@RED
def test_p3_later_outcome_feedback_updates_statistics_not_authority():
    from serum2.producer.skill_library import record_skill_outcome, extract_skill
    sk = extract_skill(episode())
    new = record_skill_outcome(sk, episode_id="e2", verified=False)
    assert new.outcome_stats["attempts"] == 2 and new.confidence < sk.confidence and new.advisory is True


# ---- P3.9 evidence/statistics merge --------------------------------------------------------------
def ev(episode_id, verified=True, event_id="evt"):
    return {"episode_id": episode_id, "event_id": event_id, "before": "15 ms", "after": "838 ms", "verified": verified}


def sk(*evidence, **over):
    ids = list(dict.fromkeys(e["episode_id"] for e in evidence))
    return skill(supporting_evidence=tuple(evidence), provenance={"source_episode_ids": ids}, **over)


def test_p3_9_merge_of_success_and_failed_attempt_recomputes_everything():
    from serum2.producer.skill_library import merge_skills
    m = merge_skills(sk(ev("A")), sk(ev("B", verified=False)))
    assert m.outcome_stats == {"attempts": 2, "verified_successes": 1, "distinct_episodes": 2}
    assert [e["episode_id"] for e in m.supporting_evidence] == ["A", "B"]
    assert m.provenance["source_episode_ids"] == ["A", "B"]
    assert m.confidence == 1 / 6 and m.confidence not in (0.2, 0.5)     # recomputed, not copied from either


def test_p3_9_same_episode_twice_is_idempotent(tmp_path):
    from serum2.producer.skill_library import SkillStore, extract_skill, merge_skills
    s1 = extract_skill(episode(experience_id="A"))
    assert merge_skills(s1, s1) == s1
    st = SkillStore(tmp_path)
    path = st.save(s1)
    raw = path.read_bytes()
    st.save(s1)
    st.add_episode(episode(experience_id="A"))
    assert path.read_bytes() == raw and st.load(s1.skill_id).outcome_stats["attempts"] == 1


def test_p3_9_different_verified_episodes_are_both_preserved(tmp_path):
    from serum2.producer.skill_library import SkillStore
    st = SkillStore(tmp_path)
    st.add_episode(episode(experience_id="A"))
    st.add_episode(episode(experience_id="B"))
    got = st.load("skill:env1.release:set")
    assert got.provenance["source_episode_ids"] == ["A", "B"]
    assert [e["episode_id"] for e in got.supporting_evidence] == ["A", "B"]
    assert got.outcome_stats == {"attempts": 2, "verified_successes": 2, "distinct_episodes": 2}
    assert got.confidence == 2 / 6
    assert V.validate_skill(got) == [] and got.advisory is True


def test_p3_9_numbers_are_order_independent():
    from serum2.producer.skill_library import merge_skills
    ab = merge_skills(sk(ev("A")), sk(ev("B", verified=False)))
    ba = merge_skills(sk(ev("B", verified=False)), sk(ev("A")))
    assert (ab.outcome_stats, ab.confidence) == (ba.outcome_stats, ba.confidence)


def test_p3_9_merge_refuses_different_identity_and_store_is_unchanged(tmp_path):
    from serum2.producer.skill_library import SkillStore, merge_skills
    a = sk(ev("A"))
    with pytest.raises(ValueError):
        merge_skills(a, sk(ev("B"), operation="TOGGLE"))
    with pytest.raises(ValueError):
        merge_skills(a, sk(ev("B"), target_concept="other"))
    st = SkillStore(tmp_path)
    path = st.save(a)
    raw = path.read_bytes()
    with pytest.raises(ValueError):
        st.save(sk(ev("B"), operation="TOGGLE", skill_id=a.skill_id))
    assert path.read_bytes() == raw


def test_p3_9_merge_never_promotes_lifecycle_or_advisory():
    from serum2.producer.skill_library import merge_skills
    m = merge_skills(sk(ev("A")), sk(ev("B"), lifecycle_state="STALE"))
    assert m.lifecycle_state == "FRESH" and m.advisory is True


def test_p3_9_merge_is_generic_across_targets(tmp_path):
    from serum2.producer.skill_library import SkillStore
    st = SkillStore(tmp_path)
    for eid in ("A", "B"):
        e = episode(experience_id=eid)
        e.brain_decision["decisions"][0].update(source_control_id="filter1.cutoff", semantic_target="Filter1.Cutoff",
                                                resolved_concept="filter-cutoff", observed_after="900 Hz")
        st.add_episode(e)
    got = st.load("skill:filter1.cutoff:set")
    assert got.outcome_stats["attempts"] == 2 and got.confidence == 2 / 6


def test_p3_9_add_episode_refuses_unverified_and_leaves_library_untouched(tmp_path):
    from serum2.producer.skill_library import SkillStore
    st = SkillStore(tmp_path)
    path = st.add_episode(episode(experience_id="A"))
    raw = path.read_bytes()
    bad = episode(experience_id="B")
    bad.outcome["status"] = "READBACK_MISMATCH"
    with pytest.raises(ValueError):
        st.add_episode(bad)
    assert path.read_bytes() == raw


def test_p3_9_legacy_evidence_without_flag_counts_as_verified():
    from serum2.producer.skill_library import merge_skills
    legacy = skill(supporting_evidence=({"episode_id": "A", "event_id": "e"},), provenance={"source_episode_ids": ["A"]})
    assert merge_skills(None, legacy).outcome_stats["verified_successes"] == 1


def test_p4_6_lifecycle_vocabulary_and_advisory_exposure():
    from serum2.producer.skill_library import LIFECYCLE_STATES, SkillAdvisory
    assert LIFECYCLE_STATES == {"FRESH", "STALE", "CONTRADICTED", "RETIRED"}
    for st in LIFECYCLE_STATES:
        assert SkillAdvisory.from_skill(skill(lifecycle_state=st)).lifecycle_state == st
    assert "BAD_LIFECYCLE_STATE" in V.validate_skill(skill(lifecycle_state="DEGRADED"))
