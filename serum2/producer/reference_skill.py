"""STRICT skill extraction from a verified REFERENCE-REPRODUCTION episode.

The legacy extract_skill_from_episode (skill.py) accepts any dict with a truthy `admitted`, `semantic_target` and
`readback`; it never checks the readback route, a comparison, or a verified outcome. This module is the strict gate
for the reference-reproduction path. Every condition is required; nothing weaker qualifies.

A skill is advisory memory only: it never grants admission. A candidate becomes QUALIFIED only through independent
verified episodes (skill.qualify_skill).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from serum2.producer.skill import Skill, SkillProcedureStep, SkillQualificationStatus


def reference_episode_learnable(record: Dict[str, Any]) -> Optional[str]:
    """None when the episode may ground a skill, otherwise the reason it may not."""
    ref = (record.get("provenance") or {}).get("reference_reproduction")
    if not ref:
        return "not a reference-reproduction episode"
    if ref.get("verification_level") != "LIVE_UI_VERIFIED":
        return "verification level is %r, not LIVE_UI_VERIFIED" % ref.get("verification_level")
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


def extract_skills_from_reference_episode(record: Dict[str, Any]) -> List[Skill]:
    """One CANDIDATE skill per authorized and verified operation."""
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
            rationale_for_status="One LIVE_UI_VERIFIED reference-reproduction episode; awaiting independent confirmation",
            provenance={"source": "reference_reproduction", "epoch": ref["epoch"], "contract_key": op["contract_key"],
                        "authority": "none -- advisory only; admission still requires a contract in the run's epoch"}))
    return skills
