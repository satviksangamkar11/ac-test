"""Verified-episode and learning-gate tests for the reference-reproduction path (committed fixtures, never skipped)."""
import copy
import json
from pathlib import Path

import pytest

from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.reference_skill import (OPERATION_EVIDENCE, REFERENCE_EPISODE, episode_kind,
                                             extract_reference_level_skill, extract_skills_from_reference_episode,
                                             reference_episode_learnable)
from serum2.producer.skill import SkillQualificationStatus
from serum2.server.experience_record import is_canonical_serum_readback, replay_eligibility
from serum2.server.reference_reproduction import NotVerified, run_reference_reproduction, to_experience_record

FIX = Path(__file__).parent / "fixtures" / "reference_reproduction"


@pytest.fixture(scope="module")
def ui():
    return json.loads((FIX / "ui_readback_authorized_9.json").read_text(encoding="utf-8"))


def _run(ui_readback):
    return run_reference_reproduction(FIX / "stage_a_observation.json", FIX / "reread_log.json", FIX / "stage_a_corrections.json",
                                      source={"video_id": "HEEGN1Xl5o4"}, name="test-reference-episode", epoch=EPOCH_2_0_23,
                                      ui_readback=ui_readback, subfolder="VLP1-tests")


def test_proof_level_and_coverage_are_separate_axes(ui):
    run = _run(ui)
    assert run.proof_level == "LIVE_UI_VERIFIED"
    assert run.coverage_status == "PARTIAL"
    assert run.operation_evidence_eligible and not run.reference_verified      # 9 of 178 is NOT a verified reference
    assert _run(None).proof_level == "FILE_READBACK_VERIFIED_ONLY" and not _run(None).operation_evidence_eligible


def test_only_a_live_ui_verified_run_becomes_an_episode(ui):
    with pytest.raises(NotVerified):
        to_experience_record(_run(None), ui, run_id="t1")               # file readback only
    rec = to_experience_record(_run(ui), ui, run_id="t2")
    assert rec.outcome["status"] == "VERIFIED" and rec.outcome["proof_level"] == "LIVE_UI_VERIFIED"
    assert rec.outcome["kind"] == OPERATION_EVIDENCE and rec.outcome["reference_verified"] is False
    assert is_canonical_serum_readback(rec.serum_ui_actions[0]["evidence"])
    assert replay_eligibility(rec)["status"] == "REPLAYABLE"
    cov = rec.outcome["coverage"]
    assert cov["authorized_and_compiled"] <= 9 and cov["fraction_of_observed_state_reproduced"] < 0.1   # never over-claims


def test_a_wrong_or_missing_ui_readback_is_not_verified(ui):
    bad = copy.deepcopy(ui)
    bad["values"]["oscB.octave"] = "0"
    run = _run(bad)
    assert run.verification_level == "UI_READBACK_FAILED_OR_INCOMPLETE" and not run.operation_evidence_eligible
    assert run.coverage_status == "FAILED"
    missing = copy.deepcopy(ui)
    del missing["values"]["env2.decay"]
    assert _run(missing).ui_comparison["field_counts"].get("UNREADABLE") == 1


def test_operation_level_learning_never_becomes_whole_reference_learning(ui):
    rec = to_experience_record(_run(ui), ui, run_id="t3").to_dict()
    assert reference_episode_learnable(rec) is None and episode_kind(rec) == OPERATION_EVIDENCE
    skills = extract_skills_from_reference_episode(rec)
    assert len(skills) >= 7 and all(s.qualification_status == SkillQualificationStatus.CANDIDATE.value for s in skills)
    assert all(s.provenance["authority"].startswith("none") and s.provenance["scope"] == "operation-level" for s in skills)
    with pytest.raises(ValueError):
        extract_reference_level_skill(rec)                              # 9/178 cannot ground a whole-reference skill
    complete = copy.deepcopy(rec)                                       # synthetic: gate logic only
    complete["provenance"]["reference_reproduction"].update(coverage_status="COMPLETE", reference_verified=True)
    assert episode_kind(complete) == REFERENCE_EPISODE
    assert extract_reference_level_skill(complete).provenance["learning_product"] == REFERENCE_EPISODE
    incomplete_flag = copy.deepcopy(complete)
    incomplete_flag["provenance"]["reference_reproduction"]["coverage_status"] = "PARTIAL"
    with pytest.raises(ValueError):
        extract_reference_level_skill(incomplete_flag)                  # both fields must agree


def test_skills_only_from_strictly_verified_episodes(ui):
    rec = to_experience_record(_run(ui), ui, run_id="t4").to_dict()
    for mutate in (lambda r: r["provenance"]["reference_reproduction"].update(proof_level="FILE_READBACK_VERIFIED_ONLY"),
                   lambda r: r["outcome"].update(status="MISMATCH"),
                   lambda r: r["serum_ui_actions"][0]["evidence"].update(route="SCREEN_INSPECTION"),
                   lambda r: r["serum_ui_actions"][0]["evidence"].update(all_match=False),
                   lambda r: r["serum_mcp_call"].update(stage="specified"),
                   lambda r: r["provenance"].pop("replay_provenance")):
        weak = copy.deepcopy(rec)
        mutate(weak)
        assert reference_episode_learnable(weak) is not None and episode_kind(weak) is None
        with pytest.raises(ValueError):
            extract_skills_from_reference_episode(weak)
