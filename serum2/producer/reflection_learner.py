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


# ====================================================================================================================
# P5.2  record_skill_outcome: real execution + readback evidence -> ReflectionRecord
# ====================================================================================================================
from dataclasses import replace as _replace  # noqa: E402
from typing import Iterable  # noqa: E402

from serum2.producer.candidate_ranking import AttemptOutcome, PriorEpisodeEvidence, prior_evidence_from_attempts  # noqa: E402
from serum2.producer.skill_library import (  # noqa: E402,F401  (lifecycle semantics are owned by P3; re-exported for P5 callers)
    SkillRecord, derive_lifecycle_state, merge_skills, retire_skill, worse_state,
)

MAX_CONFIDENCE = 0.8    # one readback is never certainty; confidence scales with how many watched keys were actually observed


def attempt_id(attempt: Mapping[str, Any]) -> Tuple[Any, Any]:
    """The identity of ONE execution across every advisory representation (skill evidence, prior evidence, reflection)."""
    return (attempt["episode_id"], attempt.get("event_id") or "%s|%s" % (attempt["canonical_target_id"], str(attempt["operation"]).lower()))


def _statement(kind: str, attempt: Mapping[str, Any], expected: Mapping[str, Any], observed: Mapping[str, Any],
               diffs: List[Mapping[str, Any]]) -> str:
    what = "%s on %s%s" % (attempt["operation"], attempt["canonical_target_id"],
                           " (%s)" % attempt["operand"] if attempt.get("operand") else "")
    if kind == CONFIRMED:
        return "%s produced the expected readback %s." % (what, dict(expected))
    if kind == CONTRADICTED:
        return "%s did not produce the expected readback: %s." % (what, "; ".join(
            "%s expected %r observed %r" % (d["key"], d["expected"], d["observed"]) for d in diffs))
    if kind == INCONCLUSIVE:
        return "%s could not be confirmed: no usable readback for %s." % (what, sorted(k for k in expected if observed.get(k) is None))
    return "%s was not executed (%s); nothing is learned about the target." % (what, attempt.get("execution_status") or "no execution")


def record_skill_outcome(*, attempt: Mapping[str, Any], expected: Mapping[str, Any], observed: Optional[Mapping[str, Any]] = None,
                         evidence: Iterable[Mapping[str, Any]] = ()) -> ReflectionRecord:
    """Turn one completed attempt into an advisory ReflectionRecord.

    expected is what was predicted BEFORE observing; observed must come from a real readback and be backed by a
    readback evidence entry with a route. Nothing is inferred from admission: a REFUSED or not-executed attempt is
    NOT_EXECUTED whatever was passed as observed, and an observation without readback evidence is discarded.
    """
    missing = [k for k in _ATTEMPT_REQUIRED if not attempt.get(k)]
    if missing:
        raise ValueError("attempt is missing %s" % missing)
    status = str(attempt.get("execution_status") or "")
    executed = bool(attempt.get("executed")) and not status.startswith("REFUSED")
    ev: List[Dict[str, Any]] = [dict(e) for e in evidence]
    obs = dict(observed or {})
    if not executed:
        obs = {}
        ev.append({"kind": "execution", "executed": False, "execution_status": status or "NOT_EXECUTED"})
    elif obs and not any(e.get("kind") == "readback" and e.get("route") for e in ev):
        obs = {}
        ev.append({"kind": "execution", "note": "observation supplied without readback evidence; discarded"})
    elif not obs and not ev:
        ev.append({"kind": "execution", "note": "executed; no readback supplied"})
    disc = classify_discrepancy(expected, obs, executed)
    cls = disc["class"]
    conf = 0.0 if cls in (NOT_EXECUTED, NO_READBACK) else MAX_CONFIDENCE * sum(1 for k in expected if obs.get(k) is not None) / len(expected)
    kind = KIND_FOR_CLASS[cls]
    att = {k: attempt[k] for k in _ATTEMPT_REQUIRED}
    att.update({k: attempt[k] for k in ("operand", "event_id") if attempt.get(k) is not None})
    att.update(executed=executed, execution_status=status or None)
    aid = attempt_id(att)
    rec = ReflectionRecord(
        reflection_id="refl:%s:%s" % aid, attempt=att, expected_outcome=dict(expected), observed_outcome=obs, discrepancy=disc,
        evidence=tuple(ev), confidence=round(conf, 6),
        lesson={"kind": kind, "statement": _statement(kind, att, expected, obs, disc["differences"]), "advisory": True,
                "applies_to": {"canonical_target_id": att["canonical_target_id"], "operation": att["operation"]}},
        provenance={"source_episode_ids": [att["episode_id"]], "attempt_id": list(aid), "recorded_by": "reflection_learner.record_skill_outcome"})
    bad = ReflectionValidator().validate(rec)
    if bad:
        raise ValueError("reflection failed validation: %s" % bad)
    return rec


def attempt_from_result(result: Any, *, episode_id: str, event_id: Optional[str] = None) -> Dict[str, Any]:
    """Duck-typed adapter from a Producer result. `executed` is true ONLY for a result that was actually executed
    (finalized with real readback); an admitted/plan-ready result is not an execution."""
    b1 = getattr(result, "b1_intent", None) or {}
    op = b1.get("operation") or {}
    status = getattr(result, "execution_status", None)
    if not b1.get("canonical_target") or not op.get("operation"):
        raise ValueError("result carries no canonical target/operation to reflect on")
    att = {"canonical_target_id": b1["canonical_target"], "operation": op["operation"], "episode_id": episode_id,
           "executed": status in ("EXECUTED", "EXECUTION_UNVERIFIED"), "execution_status": status}
    if op.get("target_value") is not None:
        att["operand"] = str(op["target_value"])
    if event_id:
        att["event_id"] = event_id
    return att


# ====================================================================================================================
# P5.3  apply a reflection to a skill: one attempt counts once, however many representations report it
# ====================================================================================================================
def apply_reflection(skill: SkillRecord, reflection: ReflectionRecord) -> SkillRecord:
    """Merge the reflection's outcome into the skill's evidence via the P3 merge (idempotent per attempt). A reflection
    can update an existing skill; it cannot create one, and it changes evidence/lifecycle only -- never capability."""
    bad = ReflectionValidator().validate(reflection)
    if bad:
        raise ValueError("cannot apply an invalid reflection: %s" % bad)
    att = reflection.attempt
    if att["canonical_target_id"] != skill.canonical_target_id or str(att["operation"]).upper() != skill.operation.upper():
        raise ValueError("reflection about %s/%s cannot update skill %s" % (att["canonical_target_id"], att["operation"], skill.skill_id))
    kind = reflection.lesson["kind"]
    if kind == NOT_TESTED:
        return skill                                            # nothing was tried
    entry = {"episode_id": att["episode_id"], "event_id": att.get("event_id"), "verified": kind == CONFIRMED, "outcome": kind,
             "reflection_id": reflection.reflection_id, "discrepancy_class": reflection.discrepancy["class"],
             "readback_expected": dict(reflection.expected_outcome), "readback_observed": dict(reflection.observed_outcome)}
    incoming = _replace(skill, supporting_evidence=(entry,), provenance={"source_episode_ids": [att["episode_id"]]})
    return merge_skills(skill, incoming)


def update_skill_store(store: Any, reflection: ReflectionRecord) -> Optional[SkillRecord]:
    """Apply a reflection to the stored skill for its target/operation. Returns None if no such skill exists: reflections
    never create skills (only verified episodes do, in P3)."""
    att = reflection.attempt
    skill_id = "skill:%s:%s" % (att["canonical_target_id"], str(att["operation"]).lower())
    try:
        skill = store.load(skill_id)
    except FileNotFoundError:
        return None
    store.save(apply_reflection(skill, reflection))
    return store.load(skill_id)


# ====================================================================================================================
# P5.5  contradiction detection (generic)      P5.6  reflections as P4 prior evidence
# ====================================================================================================================
def detect_contradictions(reflections: Iterable[ReflectionRecord], skill: Optional[SkillRecord] = None) -> List[ReflectionRecord]:
    """Reflections whose observation contradicted their expectation, optionally only those about `skill`."""
    out = []
    for r in reflections:
        if ReflectionValidator().validate(r):
            continue
        a = r.attempt
        if skill is not None and (a["canonical_target_id"] != skill.canonical_target_id or str(a["operation"]).upper() != skill.operation.upper()):
            continue
        if r.discrepancy["class"] == VALUE_MISMATCH:
            out.append(r)
    return out


def attempts_from_reflections(reflections: Iterable[ReflectionRecord]) -> Tuple[AttemptOutcome, ...]:
    out = []
    for r in reflections:
        bad = ReflectionValidator().validate(r)
        if bad:
            raise ValueError("invalid reflection: %s" % bad)
        if r.lesson["kind"] == NOT_TESTED:
            continue
        a = r.attempt
        out.append(AttemptOutcome(attempt_id(a), a["canonical_target_id"], str(a["operation"]).lower(), a["episode_id"],
                                  r.lesson["kind"] == CONFIRMED))
    return tuple(out)


def prior_evidence_from_reflections(reflections: Iterable[ReflectionRecord]) -> Tuple[PriorEpisodeEvidence, ...]:
    """The authoritative outcome record P4 consumes: aggregated from reflections, each attempt counted once."""
    return prior_evidence_from_attempts(attempts_from_reflections(reflections))
