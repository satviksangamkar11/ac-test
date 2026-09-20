"""STRICT learning gates for a verified REFERENCE-REPRODUCTION episode. Two different learning products:

  VerifiedOperationEvidence  the reproduced OPERATIONS were verified in the live Serum UI (DIRECT_UI). May ground
                             operation-level skills. Says nothing about the rest of the reference.
  VerifiedReferenceEpisode   LIVE_UI_VERIFIED and coverage COMPLETE: every observed Serum-state row was reproduced.
                             The only thing that may ground a whole-reference skill.

A partially reproduced tutorial (e.g. 9 of 178 rows) never becomes a "complete reproduction" lesson. Skills are advisory
memory only: they never grant admission, and a candidate becomes QUALIFIED only through independent verified episodes
(skill.qualify_skill). The legacy extract_skill_from_episode (skill.py) has a much weaker gate and is not used here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from serum2.producer.skill import Skill, SkillProcedureStep, SkillQualificationStatus

OPERATION_EVIDENCE = "VerifiedOperationEvidence"
REFERENCE_EPISODE = "VerifiedReferenceEpisode"


def reference_episode_learnable(record: Dict[str, Any]) -> Optional[str]:
    """None when the episode may ground OPERATION-level learning, otherwise the reason it may not."""
    ref = (record.get("provenance") or {}).get("reference_reproduction")
    if not ref:
        return "not a reference-reproduction episode"
    if ref.get("proof_level") != "LIVE_UI_VERIFIED":
        return "proof level is %r, not LIVE_UI_VERIFIED" % ref.get("proof_level")
    if (record.get("outcome") or {}).get("status") != "VERIFIED":
        return "outcome is not VERIFIED"
    readbacks = [(a.get("evidence") or {}) for a in (record.get("serum_ui_actions") or [])]
    if not any(r.get("domain") == "serum" and r.get("route") == "DIRECT_UI" and r.get("all_match") is True for r in readbacks):
        return "no matching DIRECT_UI Serum readback"
    if (record.get("serum_mcp_call") or {}).get("stage") != "verified":
        return "serum-mcp call did not reach the verified stage"
    if not (record.get("provenance") or {}).get("replay_provenance"):
        return "no replay pins"
    if not ref.get("authorized_operations"):
        return "no authorized operations"
    return None


def episode_kind(record: Dict[str, Any]) -> Optional[str]:
    """Which learning product this episode is, or None if it grounds nothing."""
    if reference_episode_learnable(record) is not None:
        return None
    ref = record["provenance"]["reference_reproduction"]
    return REFERENCE_EPISODE if (ref.get("reference_verified") and ref.get("coverage_status") == "COMPLETE") else OPERATION_EVIDENCE


def extract_skills_from_reference_episode(record: Dict[str, Any]) -> List[Skill]:
    """One CANDIDATE, operation-level skill per authorized and verified operation. Never a whole-reference skill."""
    why = reference_episode_learnable(record)
    if why:
        raise ValueError("episode cannot ground a skill: " + why)
    ref = record["provenance"]["reference_reproduction"]
    rb = next(a["evidence"] for a in record["serum_ui_actions"]
              if (a.get("evidence") or {}).get("route") == "DIRECT_UI" and a["evidence"].get("all_match"))
    epi = record["experience_id"]
    skills = []
    for op in ref["authorized_operations"]:
        tgt = op["target"]
        skills.append(Skill(
            skill_id="skill_ref_%s_%s" % (tgt.replace(".", "_"), epi),
            skill_type="serum_parameter_control", name="reproduce observed %s" % tgt,
            description="Reproduce an observed %s state via an admitted %s operation (contract %s)" % (
                tgt, op["operation"], op["contract_key"]),
            steps=[SkillProcedureStep(
                1, "serum-mcp generate_preset writes the observed operand through the contract-bound accessor %s" % op["binding"],
                "serum_mcp_call", target=tgt, operation=op["operation"], tool_name="generate_preset", evidence_fields=[tgt]),
                SkillProcedureStep(2, "read the value back from the live Serum UI (DIRECT_UI)", "serum_ui_action", target=tgt)],
            applicable_targets=[tgt], episode_refs=[epi],
            input_output_pairs=[{"specified": op["operand"], "readback": rb["observed"].get(tgt), "verified": True}],
            qualification_status=SkillQualificationStatus.CANDIDATE.value, qualification_evidence_count=1, confidence=0.3,
            rationale_for_status="One LIVE_UI_VERIFIED operation; awaiting independent confirmation",
            provenance={"source": "reference_reproduction", "learning_product": OPERATION_EVIDENCE, "scope": "operation-level",
                        "epoch": ref["epoch"], "contract_key": op["contract_key"],
                        "reference_coverage": ref.get("coverage", {}).get("fraction_of_observed_state_reproduced"),
                        "authority": "none -- advisory only; admission still requires a contract in the run's epoch"}))
    return skills


def extract_reference_level_skill(record: Dict[str, Any]) -> Skill:
    """A whole-reference skill. Requires VerifiedReferenceEpisode: LIVE_UI_VERIFIED AND coverage COMPLETE."""
    kind = episode_kind(record)
    if kind != REFERENCE_EPISODE:
        raise ValueError("not a VerifiedReferenceEpisode (kind=%s, coverage=%s)" % (
            kind, record.get("provenance", {}).get("reference_reproduction", {}).get("coverage_status")))
    ref = record["provenance"]["reference_reproduction"]
    ops = extract_skills_from_reference_episode(record)
    return Skill(
        skill_id="skill_reference_%s" % record["experience_id"], skill_type="reference_reproduction",
        name="reproduce reference %s" % ref["source"].get("video_id"),
        description="Whole-reference reproduction verified live in Serum (coverage COMPLETE)",
        applicable_targets=sorted({t for s in ops for t in s.applicable_targets}), episode_refs=[record["experience_id"]],
        qualification_status=SkillQualificationStatus.CANDIDATE.value, qualification_evidence_count=1, confidence=0.3,
        rationale_for_status="One VerifiedReferenceEpisode; awaiting independent confirmation",
        provenance={"source": "reference_reproduction", "learning_product": REFERENCE_EPISODE, "epoch": ref["epoch"],
                    "authority": "none -- advisory only"})
