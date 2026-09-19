"""P3: Skill Library -- advisory knowledge distilled from VerifiedEpisodes.

Invariants (frozen plan, P3): a skill is evidence-derived and provenance-backed; it cannot create a
capability contract, grant authority, or execute anything. Only Capability Resolution and Admission
decide what runs. This module therefore has no import of the Brain, admission, or any backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple

VERIFIED_STATUS = "ADMITTED_CONTROLS_READBACK_VERIFIED"
SKILL_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class SkillRecord:
    """Advisory skill. Deliberately has no route, contract, binding, or execute field."""

    skill_id: str
    target_concept: str                      # Brain concept the episode resolved, e.g. "note-release"
    semantic_target: str                     # e.g. "Env1.Release" (identity only, not a binding)
    operation: str                           # generic direction/op observed, e.g. "increase"
    trigger: Mapping[str, Any]               # when the skill is relevant (context, not a rule that fires)
    preconditions: Tuple[str, ...]           # what held in the source episode
    supporting_evidence: Tuple[Mapping[str, Any], ...]  # episode refs + readback observations
    outcome_stats: Mapping[str, Any]         # counts only; recomputed from evidence, never hand-set
    confidence: float
    provenance: Mapping[str, Any]
    advisory: bool = True
    schema_version: str = SKILL_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id, "target_concept": self.target_concept, "semantic_target": self.semantic_target,
            "operation": self.operation, "trigger": dict(self.trigger), "preconditions": list(self.preconditions),
            "supporting_evidence": [dict(e) for e in self.supporting_evidence], "outcome_stats": dict(self.outcome_stats),
            "confidence": self.confidence, "provenance": dict(self.provenance), "advisory": self.advisory,
            "schema_version": self.schema_version,
        }


_FORBIDDEN_SKILL_FIELDS = frozenset({
    "execution_route", "route", "contract_id", "binding", "capability", "capability_key",
    "admitted", "authority", "execute", "backend",
})


class SkillQualificationValidator:
    """Gates (1) which episodes may create a skill and (2) whether a skill record is well-formed.

    Returns a list of violation codes; empty means valid. Never mutates, never raises on bad input.
    """

    def validate_episode(self, episode: Any) -> List[str]:
        v: List[str] = []
        outcome = getattr(episode, "outcome", None) or {}
        decisions = (getattr(episode, "brain_decision", None) or {}).get("decisions") or []
        rb = outcome.get("real_plugin_readback") or {}
        if outcome.get("status") != VERIFIED_STATUS:
            v.append("EPISODE_NOT_VERIFIED")
        if rb.get("match") is not True or not rb.get("expected") or rb.get("expected") != rb.get("observed"):
            v.append("READBACK_NOT_MATCHED")
        if not decisions:
            v.append("NO_DECISIONS")
        elif not all(d.get("admitted") is True for d in decisions):
            v.append("DECISION_NOT_ADMITTED")
        if not getattr(episode, "experience_id", None):
            v.append("NO_EPISODE_ID")
        if not (getattr(episode, "provenance", None) or {}):
            v.append("NO_EPISODE_PROVENANCE")
        level = str(outcome.get("verification_level", ""))
        if "CAUSAL" in level.upper() and "not causal" not in level.lower():
            v.append("UNSUPPORTED_CAUSAL_CLAIM")
        return v

    def validate_skill(self, skill: Any) -> List[str]:
        v: List[str] = []
        d = skill.to_dict() if hasattr(skill, "to_dict") else dict(skill)
        if d.get("advisory") is not True:
            v.append("SKILL_NOT_ADVISORY")
        if _FORBIDDEN_SKILL_FIELDS & set(d):
            v.append("SKILL_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD")
        for k in ("skill_id", "target_concept", "semantic_target", "operation"):
            if not d.get(k):
                v.append("MISSING_" + k.upper())
        ev = d.get("supporting_evidence") or []
        if not ev or not all(e.get("episode_id") for e in ev):
            v.append("NO_SUPPORTING_EVIDENCE")
        if not (d.get("provenance") or {}).get("source_episode_ids"):
            v.append("NO_PROVENANCE")
        c = d.get("confidence")
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0.0 <= c <= 1.0:
            v.append("CONFIDENCE_OUT_OF_RANGE")
        return v
