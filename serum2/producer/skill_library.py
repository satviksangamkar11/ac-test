"""P3: Skill Library -- advisory knowledge distilled from VerifiedEpisodes.

Invariants (frozen plan, P3): a skill is evidence-derived and provenance-backed; it cannot create a
capability contract, grant authority, or execute anything. Only Capability Resolution and Admission
decide what runs. This module therefore has no import of the Brain, admission, or any backend.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

VERIFIED_STATUS = "ADMITTED_CONTROLS_READBACK_VERIFIED"
SKILL_SCHEMA_VERSION = "1"
LIFECYCLE_STATES = frozenset({"FRESH", "VALIDATED", "DEGRADED", "RETIRED"})
CONFIDENCE_PRIOR = 4   # pseudo-attempts: one verified success alone yields 1/5, never high confidence


@dataclass(frozen=True)
class SkillRecord:
    """Advisory skill. Deliberately has no route, contract, binding, or execute field."""

    skill_id: str
    canonical_target_id: str                 # Atlas canonical id, e.g. "env1.release"
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
    lifecycle_state: str = "FRESH"           # FRESH -> (later stages) VALIDATED / DEGRADED / RETIRED
    schema_version: str = SKILL_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id, "canonical_target_id": self.canonical_target_id, "lifecycle_state": self.lifecycle_state,
            "target_concept": self.target_concept, "semantic_target": self.semantic_target,
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
        for k in ("skill_id", "canonical_target_id", "target_concept", "semantic_target", "operation"):
            if not d.get(k):
                v.append("MISSING_" + k.upper())
        ev = d.get("supporting_evidence") or []
        if not ev or not all(e.get("episode_id") for e in ev):
            v.append("NO_SUPPORTING_EVIDENCE")
        if not (d.get("provenance") or {}).get("source_episode_ids"):
            v.append("NO_PROVENANCE")
        if d.get("lifecycle_state") not in LIFECYCLE_STATES:
            v.append("BAD_LIFECYCLE_STATE")
        c = d.get("confidence")
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0.0 <= c <= 1.0:
            v.append("CONFIDENCE_OUT_OF_RANGE")
        return v


def derive_operation(decision: Mapping[str, Any]) -> str:
    """Operation comes from the decision's own data, never from which target it is.

    An explicit decision["operation"] wins. Otherwise a decision that observed a concrete written
    value (observed_after) is a SET. No usable data -> ValueError (no guessing, no default).
    """
    op = decision.get("operation")
    if op:
        return str(op).upper()
    if decision.get("observed_after") is not None:
        return "SET"
    raise ValueError("decision carries no operation and no observed value")


def extract_skill(episode: Any, index: int = 0) -> SkillRecord:
    """VerifiedEpisode -> validated SkillRecord for one admitted decision. Raises ValueError otherwise.

    Deterministic, no model call. Carries evidence only: no route, contract, or binding.
    """
    validator = SkillQualificationValidator()
    bad = validator.validate_episode(episode)
    if bad:
        raise ValueError("episode cannot source a skill: %s" % bad)
    decisions = episode.brain_decision["decisions"]
    if not 0 <= index < len(decisions):
        raise ValueError("no decision at index %d" % index)
    d, out = decisions[index], episode.outcome
    rb = out["real_plugin_readback"]
    attempts = verified = 1
    operation = derive_operation(d)
    skill = SkillRecord(
        skill_id="skill:%s:%s" % (d["source_control_id"], operation.lower()),
        canonical_target_id=d["source_control_id"],
        target_concept=d["resolved_concept"], semantic_target=d["semantic_target"], operation=operation,
        trigger={"intent_text": d["request_kwargs"].get("user_intent"),
                 "observed_change": {"before": d["observed_before"], "after": d["observed_after"]}},
        preconditions=("verification_level=%s" % out.get("verification_level"), "readback_backend=%s" % rb.get("backend")),
        supporting_evidence=({"episode_id": episode.experience_id, "event_id": d.get("event_id"),
                              "before": d["observed_before"], "after": d["observed_after"],
                              "readback_expected": rb["expected"], "readback_observed": rb["observed"],
                              "fusion_status": d.get("fusion_status")},),
        outcome_stats={"attempts": attempts, "verified_successes": verified, "distinct_episodes": 1},
        confidence=verified / (attempts + CONFIDENCE_PRIOR),
        provenance={"source_episode_ids": [episode.experience_id], "source_id": getattr(episode, "source_id", None),
                    "extracted_by": "skill_library.extract_skill", "schema_version": SKILL_SCHEMA_VERSION},
    )
    bad = validator.validate_skill(skill)
    if bad:
        raise ValueError("extracted skill failed validation: %s" % bad)
    return skill


def skill_from_dict(d: Mapping[str, Any]) -> SkillRecord:
    fields = set(SkillRecord.__dataclass_fields__)
    extra = set(d) - fields
    if extra:
        raise ValueError("unknown skill fields (possible smuggled capability/authority): %s" % sorted(extra))
    d = dict(d)
    d["preconditions"] = tuple(d.get("preconditions", ()))
    d["supporting_evidence"] = tuple(d.get("supporting_evidence", ()))
    return SkillRecord(**d)


class SkillStore:
    """One JSON file per skill. Validates on save AND load; never stores a record that fails the gate.

    ponytail: upsert by skill_id, no merge/versioning; add evidence-merging when a second episode
    for the same target exists (P5).
    """

    def __init__(self, directory: Any):
        self._dir = Path(directory)
        self._validator = SkillQualificationValidator()

    def _path(self, skill_id: str) -> Path:
        return self._dir / (re.sub(r"[^A-Za-z0-9._-]+", "_", skill_id) + ".skill.json")

    def save(self, skill: SkillRecord) -> Path:
        bad = self._validator.validate_skill(skill)
        if bad:
            raise ValueError("refusing to store invalid skill: %s" % bad)
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(skill.skill_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(skill.to_dict(), indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
        return path

    def load(self, skill_id: str) -> SkillRecord:
        skill = skill_from_dict(json.loads(self._path(skill_id).read_text(encoding="utf-8")))
        bad = self._validator.validate_skill(skill)
        if bad:
            raise ValueError("stored skill %s failed validation: %s" % (skill_id, bad))
        return skill

    def all(self) -> List[SkillRecord]:
        if not self._dir.exists():
            return []
        return sorted((self.load_path(p) for p in self._dir.glob("*.skill.json")), key=lambda k: k.skill_id)

    def load_path(self, path: Path) -> SkillRecord:
        return skill_from_dict(json.loads(path.read_text(encoding="utf-8")))


class SkillRetriever:
    """Deterministic exact-match retrieval over canonical target (and optionally operation).

    Returns stored skills unchanged: retrieval never edits confidence, lifecycle, or statistics, and
    never yields anything but SkillRecords (no route, contract, or permission). RETIRED skills are
    excluded. Order: highest confidence first, then skill_id.
    """

    def __init__(self, skills: Iterable[SkillRecord]):
        self._skills = tuple(skills)

    @classmethod
    def from_store(cls, store: SkillStore) -> "SkillRetriever":
        return cls(store.all())

    def retrieve(self, canonical_target_id: str, operation: Optional[str] = None) -> List[SkillRecord]:
        hits = [k for k in self._skills
                if k.canonical_target_id == canonical_target_id
                and (operation is None or k.operation == operation)
                and k.lifecycle_state != "RETIRED"]
        return sorted(hits, key=lambda k: (-k.confidence, k.skill_id))


def _freeze(x: Any) -> Any:
    if isinstance(x, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in x.items()})
    if isinstance(x, (list, tuple)):
        return tuple(_freeze(v) for v in x)
    return x


@dataclass(frozen=True)
class SkillAdvisory:
    """Read-only projection of a SkillRecord for candidate generation/ranking (P4).

    Exactly the relevance fields; deliberately no route, contract, binding, admitted, tool call or
    execute. It is not a ProducerRequest and cannot be turned into one.
    """

    skill_id: str
    canonical_target_id: str
    operation: str
    trigger: Mapping[str, Any]
    preconditions: Tuple[str, ...]
    supporting_evidence: Tuple[Mapping[str, Any], ...]
    outcome_statistics: Mapping[str, Any]
    confidence: float
    provenance: Mapping[str, Any]
    advisory_only: bool = True

    @classmethod
    def from_skill(cls, skill: SkillRecord) -> "SkillAdvisory":
        bad = SkillQualificationValidator().validate_skill(skill)
        if bad:
            raise ValueError("cannot advise from invalid skill: %s" % bad)
        return cls(skill.skill_id, skill.canonical_target_id, skill.operation, _freeze(skill.trigger),
                   _freeze(skill.preconditions), _freeze(skill.supporting_evidence), _freeze(skill.outcome_stats),
                   skill.confidence, _freeze(skill.provenance))

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(json.dumps({f: getattr(self, f) for f in self.__dataclass_fields__}, default=dict))


def advise(retriever: SkillRetriever, canonical_target_id: str, operation: Optional[str] = None) -> List[SkillAdvisory]:
    return [SkillAdvisory.from_skill(k) for k in retriever.retrieve(canonical_target_id, operation)]
