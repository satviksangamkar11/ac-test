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
    d = dict(skill_id="skill:env1.release:increase", target_concept="note-release", semantic_target="Env1.Release",
             operation="increase", trigger={"direction": "increase"}, preconditions=("plugin=Serum 2.0.21",),
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


@RED
def test_p3_4_extracts_env1_release_skill_from_verified_episode():
    from serum2.producer.skill_library import extract_skill
    s = extract_skill(episode())
    assert s.semantic_target == "Env1.Release" and s.operation == "increase" and V.validate_skill(s) == []


@RED
def test_p3_4_extraction_refuses_unverified_episode():
    from serum2.producer.skill_library import extract_skill
    e = episode()
    e.outcome["status"] = "READBACK_MISMATCH"
    with pytest.raises(ValueError):
        extract_skill(e)


@RED
def test_p3_5_store_roundtrip_is_lossless(tmp_path):
    from serum2.producer.skill_library import SkillStore, extract_skill
    st = SkillStore(tmp_path)
    s = extract_skill(episode())
    st.save(s)
    assert st.load(s.skill_id) == s


@RED
def test_p3_6_retriever_is_deterministic_and_never_returns_capability():
    from serum2.producer.skill_library import SkillRetriever, SkillStore, extract_skill
    r = SkillRetriever([extract_skill(episode())])
    a = r.retrieve(semantic_target="Env1.Release", operation="increase")
    assert a == r.retrieve(semantic_target="Env1.Release", operation="increase")
    assert r.retrieve(semantic_target="Filter1.Cutoff", operation="increase") == []


@RED
def test_p3_7_advisory_cannot_execute_or_grant_authority():
    from serum2.producer.skill_library import SkillAdvisory, extract_skill
    adv = SkillAdvisory.from_skills([extract_skill(episode())])
    assert adv.advisory_only is True and not hasattr(adv, "execute") and not hasattr(adv, "admitted")
