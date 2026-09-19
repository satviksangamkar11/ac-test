"""P4: Candidate generation and ranking -- advisory only.

A candidate is a *proposal* about (target, operation). It carries no route, contract, binding,
admission or tool call and cannot execute. Ranking orders candidates; it never executes, admits,
invents a capability, or silently replaces a target:

  * the intent's own primary candidate is always present, so a same-target fallback always exists;
  * SAME target: candidates genuinely compete on score, and evidence may promote a same-target operation
    variant over the primary. Such an override is never silent: RankedSet.selected_overrides_primary and
    the audit record say so;
  * DIFFERENT target: a candidate that changes the target sits in a lower tier than every same-target
    candidate, so it is never selected (target replacement is structurally impossible) and to_intent
    refuses it.

The selected candidate is handed to Capability Resolution / Admission unchanged in kind: a
UniversalProductionIntent (see to_intent). Nothing here imports the Brain, admission, or a backend.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from serum2.producer.operation_spec import OperationSpec, OperationType
from serum2.producer.skill_library import SkillAdvisory, _freeze, _FORBIDDEN_SKILL_FIELDS

PRIMARY = "PRIMARY"
SKILL_VARIANT = "SKILL_VARIANT"
REFERENCE_ALTERNATIVE = "REFERENCE_ALTERNATIVE"
ORIGINS = frozenset({PRIMARY, SKILL_VARIANT, REFERENCE_ALTERNATIVE})

# Ranking weights (advisory scoring only). The primary starts ahead (fit 1.0 vs 0.5); a variant overtakes it only
# with strong verified evidence (a single-episode skill has confidence 0.2 and cannot).
WEIGHT_FIT = 0.5
WEIGHT_SKILL = 0.3
_OPPOSITE = {"increase": "decrease", "decrease": "increase"}
_FIT = {PRIMARY: 1.0, SKILL_VARIANT: 0.5, REFERENCE_ALTERNATIVE: 0.5}


@dataclass(frozen=True)
class Candidate:
    """Advisory proposal. Deliberately has no route/contract/binding/admitted/execute field."""

    candidate_id: str
    canonical_target: str
    operation: str                              # OperationType.value, e.g. "set"
    operand: Optional[Mapping[str, Any]]        # raw operand hint, e.g. {"raw": "838 ms"}
    origin: str
    target_changed: bool                        # differs from the intent's primary target
    evidence: Tuple[Mapping[str, Any], ...] = ()  # (skill_id, confidence) supporting this candidate
    rationale: Tuple[str, ...] = ()
    advisory: bool = True

    def __post_init__(self):
        if self.origin not in ORIGINS:
            raise ValueError("unknown candidate origin %r" % self.origin)
        if self.advisory is not True:
            raise ValueError("candidates are advisory")
        if not self.canonical_target or not self.operation:
            raise ValueError("candidate needs canonical_target and operation")
        if _FORBIDDEN_SKILL_FIELDS & set(self.__dataclass_fields__):
            raise ValueError("candidate carries capability/authority field")

    def to_dict(self) -> Dict[str, Any]:
        return {"candidate_id": self.candidate_id, "canonical_target": self.canonical_target, "operation": self.operation,
                "operand": dict(self.operand) if self.operand else None, "origin": self.origin,
                "target_changed": self.target_changed, "evidence": [dict(e) for e in self.evidence],
                "rationale": list(self.rationale), "advisory": self.advisory}


def _operand_hint(spec: OperationSpec) -> Optional[Mapping[str, Any]]:
    op = spec.operand
    raw = None
    if op is not None:
        for v in (op.value, op.enum_value, op.boolean_value):
            if v is not None:
                raw = "%s %s" % (v, op.unit) if op.unit else str(v)
                break
    if raw is None and spec.target_value is not None:
        raw = "%s %s" % (spec.target_value, spec.unit) if spec.unit else str(spec.target_value)
    return _freeze({"raw": raw}) if raw is not None else None


def _cid(target: str, operation: str, origin: str, operand: Optional[Mapping[str, Any]]) -> str:
    return "cand:%s:%s:%s:%s" % (target, operation, origin.lower(), (operand or {}).get("raw", "-"))


class CandidateGenerator:
    """UniversalProductionIntent (+ optional skill advisories, reference alternatives) -> candidates.

    Deterministic; never invents a target. Reference alternatives must be Atlas-resolvable ids supplied by the
    caller (e.g. the candidate set of an AMBIGUOUS reference); unknown ids are an error, not a guess.
    """

    def generate(self, intent: Any, advisories: Sequence[SkillAdvisory] = (),
                 reference_alternatives: Iterable[str] = ()) -> Tuple[Candidate, ...]:
        from serum2.reference.serum_atlas import normalize_control, EXACT, ALIAS

        target = intent.canonical_target
        p_op = intent.operation.operation.value
        p_operand = _operand_hint(intent.operation)
        same = [a for a in advisories if a.canonical_target_id == target]
        support = tuple(_freeze({"skill_id": a.skill_id, "confidence": a.confidence})
                        for a in same if a.operation.lower() == p_op)
        out = [Candidate(_cid(target, p_op, PRIMARY, p_operand), target, p_op, p_operand, PRIMARY, False, support,
                         ("the request's own interpretation",) + (("supported by prior verified skill",) if support else ()))]
        for a in same:
            op = a.operation.lower()
            if op == p_op:
                continue
            try:
                OperationType(op)
            except ValueError:
                continue                                    # skill operation not in the generic operation model
            if _OPPOSITE.get(p_op) == op:
                continue                                    # never contradict the direction the request asked for
            raw = (a.trigger.get("observed_change") or {}).get("after")
            operand = _freeze({"raw": str(raw)}) if raw is not None else None
            out.append(Candidate(_cid(target, op, SKILL_VARIANT, operand), target, op, operand, SKILL_VARIANT, False,
                                 (_freeze({"skill_id": a.skill_id, "confidence": a.confidence}),),
                                 ("alternative operation seen in a verified episode",)))
        for alt in reference_alternatives:
            res = normalize_control(alt)
            if res.status not in (EXACT, ALIAS):
                raise ValueError("reference alternative %r is not an Atlas identity" % alt)
            if res.canonical_id == target:
                continue
            out.append(Candidate(_cid(res.canonical_id, p_op, REFERENCE_ALTERNATIVE, p_operand), res.canonical_id, p_op,
                                 p_operand, REFERENCE_ALTERNATIVE, True, (),
                                 ("alternative reading of an ambiguous reference",)))
        seen, uniq = set(), []
        for c in out:
            if c.candidate_id not in seen:
                seen.add(c.candidate_id)
                uniq.append(c)
        return tuple(uniq)


@dataclass(frozen=True)
class RankedCandidate:
    candidate: Candidate
    rank: int
    score: float
    features: Mapping[str, Any]


@dataclass(frozen=True)
class RankedSet:
    ranked: Tuple[RankedCandidate, ...]
    advisory: bool = True

    @property
    def selected(self) -> RankedCandidate:
        return self.ranked[0]

    @property
    def selected_overrides_primary(self) -> bool:
        return self.selected.candidate.origin != PRIMARY

    def to_audit(self) -> Dict[str, Any]:
        return {"candidate_layer": "ADVISORY",
                "candidates": [dict(r.candidate.to_dict(), rank=r.rank, score=r.score, features=dict(r.features)) for r in self.ranked],
                "selected_candidate_id": self.selected.candidate.candidate_id,
                "selected_overrides_primary": self.selected_overrides_primary}


class CandidateRanker:
    """Deterministic ranking: (target-change tier, -score, id). Advisory; returns ordering + features only."""

    def rank(self, candidates: Sequence[Candidate]) -> RankedSet:
        if not candidates:
            raise ValueError("no candidates to rank")
        if not any(c.origin == PRIMARY for c in candidates):
            raise ValueError("the primary candidate must be present (a target/operation may not be silently replaced)")
        rows = []
        for c in candidates:
            skill = max((float(e["confidence"]) for e in c.evidence), default=0.0)
            score = WEIGHT_FIT * _FIT[c.origin] + WEIGHT_SKILL * skill
            rows.append((1 if c.target_changed else 0, -score, c.candidate_id, c, score,
                         {"tier": 1 if c.target_changed else 0, "primary_fit": _FIT[c.origin], "skill_prior": skill}))
        rows.sort(key=lambda r: r[:3])
        return RankedSet(tuple(RankedCandidate(r[3], i + 1, round(r[4], 12), _freeze(r[5])) for i, r in enumerate(rows)))


def to_intent(candidate: Candidate, intent: Any) -> Any:
    """Selected candidate -> UniversalProductionIntent for Capability Resolution / Admission.

    The primary candidate returns the original intent object untouched. A same-target operation variant
    returns a copy whose OperationSpec carries the variant. Target changes are refused here: re-deriving a
    concept for another target is a different, explicit step, never a side effect of ranking.
    """
    if candidate.canonical_target != intent.canonical_target:
        raise ValueError("candidate changes the target; ranking may not replace a target")
    if candidate.origin == PRIMARY:
        return intent
    op = OperationType(candidate.operation)
    spec = OperationSpec(operation=op,
                         direction=op.value if op in (OperationType.INCREASE, OperationType.DECREASE) else None,
                         target_value=(candidate.operand or {}).get("raw"),
                         base_phrase=intent.operation.base_phrase, certainty=intent.operation.certainty,
                         interpretation_chain=list(intent.operation.interpretation_chain) +
                         ["advisory candidate %s (not authority)" % candidate.candidate_id])
    return replace(intent, operation=spec)
