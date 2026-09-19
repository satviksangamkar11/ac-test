"""P5: Reflection Learner -- execution outcomes become structured, advisory lessons.

A ReflectionRecord is evidence about ONE attempt: what was attempted, what was expected, what a real readback
observed, how they differ, and the lesson. It is advisory data. It has no capability, route, binding, admission or
execute field and cannot upgrade a contract, create authority, or override a refusal. This module imports nothing
from the Brain, admission, contract registry, or any backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from serum2.producer.skill_library import _FORBIDDEN_SKILL_FIELDS

REFLECTION_SCHEMA_VERSION = "1"

# Precedence (strongest first): a refusal/non-execution is never a result; no readback proves nothing; a mismatch is a
# definite contradiction; a missing key is inconclusive; otherwise the expectation held.
NOT_EXECUTED = "NOT_EXECUTED"
NO_READBACK = "NO_READBACK"
VALUE_MISMATCH = "VALUE_MISMATCH"
MISSING_OBSERVATION = "MISSING_OBSERVATION"
NONE = "NONE"
DISCREPANCY_CLASSES = frozenset({NOT_EXECUTED, NO_READBACK, VALUE_MISMATCH, MISSING_OBSERVATION, NONE})

CONFIRMED, CONTRADICTED, INCONCLUSIVE, NOT_TESTED = "CONFIRMED", "CONTRADICTED", "INCONCLUSIVE", "NOT_TESTED"
LESSON_KINDS = frozenset({CONFIRMED, CONTRADICTED, INCONCLUSIVE, NOT_TESTED})
KIND_FOR_CLASS = {NONE: CONFIRMED, VALUE_MISMATCH: CONTRADICTED, MISSING_OBSERVATION: INCONCLUSIVE,
                  NO_READBACK: INCONCLUSIVE, NOT_EXECUTED: NOT_TESTED}

_FORBIDDEN = _FORBIDDEN_SKILL_FIELDS | {"capability_contract", "admission", "admission_token", "mcp_call"}
_ATTEMPT_REQUIRED = ("canonical_target_id", "operation", "episode_id")


def classify_discrepancy(expected: Mapping[str, Any], observed: Mapping[str, Any], executed: bool) -> Dict[str, Any]:
    """Generic expected-vs-observed comparison. Knows no target, operation, or backend."""
    if not executed:
        return {"class": NOT_EXECUTED, "differences": []}
    if not expected:
        raise ValueError("an executed attempt needs a non-empty expectation to be compared against")
    if not observed:
        return {"class": NO_READBACK, "differences": []}
    diffs = [{"key": k, "expected": expected[k], "observed": observed.get(k)} for k in sorted(expected)
             if observed.get(k) != expected[k]]
    if any(d["observed"] is not None for d in diffs):
        return {"class": VALUE_MISMATCH, "differences": diffs}
    if diffs:
        return {"class": MISSING_OBSERVATION, "differences": diffs}
    return {"class": NONE, "differences": []}


@dataclass(frozen=True)
class ReflectionRecord:
    """Advisory record about one attempt. Deliberately has no capability/route/binding/admission/execute field."""

    reflection_id: str
    attempt: Mapping[str, Any]              # canonical_target_id, operation, operand?, episode_id, event_id?, executed, execution_status?
    expected_outcome: Mapping[str, Any]     # watched key -> expected value (fixed BEFORE observing)
    observed_outcome: Mapping[str, Any]     # watched key -> value from a real readback ({} when none)
    discrepancy: Mapping[str, Any]          # {"class": ..., "differences": [...]}
    evidence: Tuple[Mapping[str, Any], ...] # readback/execution evidence entries (with provenance)
    confidence: float
    lesson: Mapping[str, Any]               # {"kind": ..., "statement": ..., "advisory": True, ...}
    provenance: Mapping[str, Any]           # {"source_episode_ids": [...], ...}
    advisory: bool = True
    schema_version: str = REFLECTION_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {"reflection_id": self.reflection_id, "attempt": dict(self.attempt),
                "expected_outcome": dict(self.expected_outcome), "observed_outcome": dict(self.observed_outcome),
                "discrepancy": {"class": self.discrepancy["class"], "differences": [dict(d) for d in self.discrepancy["differences"]]},
                "evidence": [dict(e) for e in self.evidence], "confidence": self.confidence, "lesson": dict(self.lesson),
                "provenance": dict(self.provenance), "advisory": self.advisory, "schema_version": self.schema_version}


class ReflectionValidator:
    """Well-formedness + internal consistency of a reflection. Returns violation codes; empty means valid.

    Consistency means the stored discrepancy and lesson kind are RE-DERIVED from expected/observed and must match, so
    a forged "no discrepancy" cannot pass, and an observation must be backed by readback evidence with a route.
    """

    def validate(self, rec: Any) -> List[str]:
        v: List[str] = []
        d = rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
        if d.get("advisory") is not True:
            v.append("REFLECTION_NOT_ADVISORY")
        if _FORBIDDEN & set(d) or _FORBIDDEN & set(d.get("lesson") or {}):
            v.append("REFLECTION_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD")
        att = d.get("attempt") or {}
        if any(not att.get(k) for k in _ATTEMPT_REQUIRED):
            v.append("MISSING_ATTEMPT_FIELDS")
        exp, obs = d.get("expected_outcome") or {}, d.get("observed_outcome") or {}
        cls = (d.get("discrepancy") or {}).get("class")
        if cls not in DISCREPANCY_CLASSES:
            v.append("BAD_DISCREPANCY_CLASS")
        else:
            try:
                if classify_discrepancy(exp, obs, bool(att.get("executed"))) != {
                        "class": cls, "differences": list((d.get("discrepancy") or {}).get("differences", []))}:
                    v.append("DISCREPANCY_INCONSISTENT")
            except ValueError:
                v.append("DISCREPANCY_INCONSISTENT")
        ev = d.get("evidence") or []
        if not ev:
            v.append("NO_EVIDENCE")
        if obs and not any(e.get("kind") == "readback" and e.get("route") for e in ev):
            v.append("OBSERVATION_WITHOUT_READBACK_EVIDENCE")
        c = d.get("confidence")
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0.0 <= c <= 1.0:
            v.append("CONFIDENCE_OUT_OF_RANGE")
        les = d.get("lesson") or {}
        if les.get("kind") not in LESSON_KINDS or les.get("advisory") is not True or not les.get("statement"):
            v.append("BAD_LESSON")
        elif cls in KIND_FOR_CLASS and les["kind"] != KIND_FOR_CLASS[cls]:
            v.append("LESSON_INCONSISTENT_WITH_DISCREPANCY")
        if not (d.get("provenance") or {}).get("source_episode_ids"):
            v.append("NO_PROVENANCE")
        return v
