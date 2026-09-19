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


@RED
def test_p3_7_advisory_cannot_execute_or_grant_authority():
    from serum2.producer.skill_library import SkillAdvisory, extract_skill
    adv = SkillAdvisory.from_skills([extract_skill(episode())])
    assert adv.advisory_only is True and not hasattr(adv, "execute") and not hasattr(adv, "admitted")


@RED
def test_p3_later_outcome_feedback_updates_statistics_not_authority():
    from serum2.producer.skill_library import record_skill_outcome, extract_skill
    sk = extract_skill(episode())
    new = record_skill_outcome(sk, episode_id="e2", verified=False)
    assert new.outcome_stats["attempts"] == 2 and new.confidence < sk.confidence and new.advisory is True
