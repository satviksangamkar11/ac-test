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
    refuses it;
  * a variant never contradicts the requested direction (increase <-> decrease).

Evidence inputs are DATA, not decision engines: skill advisories (P3) and PriorEpisodeEvidence (outcome
history). Skills that are CONTRADICTED or RETIRED, or that fail validation, are excluded and reported; STALE
skills are penalised. None of this can create a capability: it only reorders proposals.

The selected candidate is handed to Capability Resolution / Admission unchanged in kind: a
UniversalProductionIntent (see to_intent). Nothing here imports the Brain, admission, or a backend.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from serum2.producer.operation_spec import OperationSpec, OperationType
from serum2.producer.skill_library import (
    CONFIDENCE_PRIOR, SkillAdvisory, SkillQualificationValidator, _FORBIDDEN_SKILL_FIELDS, _freeze, derive_operation,
)

PRIMARY = "PRIMARY"
SKILL_VARIANT = "SKILL_VARIANT"
REFERENCE_ALTERNATIVE = "REFERENCE_ALTERNATIVE"
ORIGINS = frozenset({PRIMARY, SKILL_VARIANT, REFERENCE_ALTERNATIVE})

# Advisory scoring weights (sum to 1). The primary starts ahead (fit 1.0 vs 0.5); a variant overtakes it only with
# strong verified evidence. A single-episode skill has confidence 0.2 and cannot; prior outcomes alone cannot.
WEIGHT_FIT = 0.5
WEIGHT_SKILL = 0.3
WEIGHT_PRIOR = 0.2
STALE_FACTOR = 0.5                                   # STALE skill confidence is halved
EXCLUDED_STATES = frozenset({"CONTRADICTED", "RETIRED"})
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
    evidence: Tuple[Mapping[str, Any], ...] = ()  # (skill_id, confidence, lifecycle_state) supporting this candidate
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


# ---- prior-episode evidence (P4.5): outcome history as DATA for the ranker --------------------------------------
@dataclass(frozen=True)
class PriorEpisodeEvidence:
    """Aggregated outcomes of past episodes for one (target, operation). Data only: no capability, no route."""

    canonical_target_id: str
    operation: str
    attempts: int
    verified_successes: int
    episode_ids: Tuple[str, ...]

    def __post_init__(self):
        if not self.canonical_target_id or not self.operation:
            raise ValueError("prior evidence needs a target and an operation")
        if not (isinstance(self.attempts, int) and isinstance(self.verified_successes, int)
                and 0 <= self.verified_successes <= self.attempts):
            raise ValueError("need 0 <= verified_successes <= attempts")
        if self.attempts and not self.episode_ids:
            raise ValueError("prior evidence needs episode provenance")


@dataclass(frozen=True)
class AttemptOutcome:
    """One attempt's outcome, keyed by attempt_key=(episode_id, event_id-or-target|operation). The SAME key means the
    same execution no matter which representation (skill evidence, prior evidence, reflection) reports it."""

    attempt_key: Tuple[Any, Any]
    canonical_target_id: str
    operation: str
    episode_id: str
    success: bool


def attempts_from_episodes(episodes: Iterable[Any]) -> Tuple[AttemptOutcome, ...]:
    """Admitted decisions are attempts (a refusal is not one); success needs the P3 verification gate."""
    validator = SkillQualificationValidator()
    out: List[AttemptOutcome] = []
    for ep in episodes:
        verified = not validator.validate_episode(ep)
        eid = getattr(ep, "experience_id", None)
        for d in (getattr(ep, "brain_decision", None) or {}).get("decisions") or []:
            if d.get("admitted") is not True or not eid:
                continue
            try:
                op = derive_operation(d).lower()
            except ValueError:
                continue
            t = d["source_control_id"]
            out.append(AttemptOutcome((eid, d.get("event_id") or "%s|%s" % (t, op)), t, op, eid, verified))
    return tuple(out)


def prior_evidence_from_attempts(attempts: Iterable[AttemptOutcome]) -> Tuple[PriorEpisodeEvidence, ...]:
    """Aggregate attempts into per-(target, operation) history. Each attempt counts once however many sources report
    it; the same attempt with different outcomes raises."""
    seen: Dict[Any, bool] = {}
    agg: Dict[Tuple[str, str], List[Any]] = {}
    for a in attempts:
        if a.attempt_key in seen:
            if seen[a.attempt_key] != a.success:
                raise ValueError("conflicting outcomes reported for the same attempt %r" % (a.attempt_key,))
            continue
        seen[a.attempt_key] = a.success
        row = agg.setdefault((a.canonical_target_id, a.operation.lower()), [0, 0, []])
        row[0] += 1
        row[1] += 1 if a.success else 0
        if a.episode_id not in row[2]:
            row[2].append(a.episode_id)
    return tuple(PriorEpisodeEvidence(t, o, r[0], r[1], tuple(r[2])) for (t, o), r in sorted(agg.items()))


def prior_evidence_from_episodes(episodes: Iterable[Any]) -> Tuple[PriorEpisodeEvidence, ...]:
    return prior_evidence_from_attempts(attempts_from_episodes(episodes))


# ---- advisories (P4.6: lifecycle-aware collection) -------------------------------------------------------------
def collect_advisories(retriever: Any, canonical_target_id: str) -> Tuple[List[SkillAdvisory], List[Dict[str, str]]]:
    """Retrieved skills -> (usable advisories, reported exclusions). Never raises on a bad skill.

    Excluded, with a reason: records failing validation, CONTRADICTED skills. (RETIRED skills are already dropped by
    the retriever.) STALE skills are kept here and penalised by the ranker.
    """
    validator = SkillQualificationValidator()
    usable: List[SkillAdvisory] = []
    excluded: List[Dict[str, str]] = []
    for rec in retriever.retrieve(canonical_target_id):
        bad = validator.validate_skill(rec)
        if bad:
            excluded.append({"skill_id": getattr(rec, "skill_id", "?"), "reason": "INVALID: " + ",".join(bad)})
        elif rec.lifecycle_state in EXCLUDED_STATES:
            excluded.append({"skill_id": rec.skill_id, "reason": "LIFECYCLE: " + rec.lifecycle_state})
        else:
            usable.append(SkillAdvisory.from_skill(rec))
    return usable, excluded


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


def _skill_ref(a: SkillAdvisory) -> Mapping[str, Any]:
    return _freeze({"skill_id": a.skill_id, "confidence": a.confidence, "lifecycle_state": a.lifecycle_state})


class CandidateGenerator:
    """UniversalProductionIntent (+ optional skill advisories, reference alternatives) -> candidates.

    Deterministic; never invents a target. Reference alternatives must be Atlas-resolvable ids supplied by the
    caller (e.g. the candidate set of an AMBIGUOUS reference); unknown ids are an error, not a guess. Advisories that
    are CONTRADICTED/RETIRED contribute nothing.
    """

    def generate(self, intent: Any, advisories: Sequence[SkillAdvisory] = (),
                 reference_alternatives: Iterable[str] = ()) -> Tuple[Candidate, ...]:
        from serum2.reference.serum_atlas import normalize_control, EXACT, ALIAS

        target = intent.canonical_target
        p_op = intent.operation.operation.value
        p_operand = _operand_hint(intent.operation)
        same = [a for a in advisories if a.canonical_target_id == target and a.lifecycle_state not in EXCLUDED_STATES]
        support = tuple(_skill_ref(a) for a in same if a.operation.lower() == p_op)
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
                                 (_skill_ref(a),), ("alternative operation seen in a verified episode",)))
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


def _skill_weight(e: Mapping[str, Any]) -> float:
    state = e.get("lifecycle_state", "FRESH")
    if state in EXCLUDED_STATES:
        return 0.0
    return float(e["confidence"]) * (STALE_FACTOR if state == "STALE" else 1.0)


class CandidateRanker:
    """Deterministic ranking: (target-change tier, -score, id). Advisory; returns ordering + features only."""

    def rank(self, candidates: Sequence[Candidate], prior_evidence: Sequence[PriorEpisodeEvidence] = ()) -> RankedSet:
        if not candidates:
            raise ValueError("no candidates to rank")
        if not any(c.origin == PRIMARY for c in candidates):
            raise ValueError("the primary candidate must be present (a target/operation may not be silently replaced)")
        rows = []
        for c in candidates:
            skill = max((_skill_weight(e) for e in c.evidence), default=0.0)
            mine = [p for p in prior_evidence if p.canonical_target_id == c.canonical_target and p.operation.lower() == c.operation]
            attempts = sum(p.attempts for p in mine)
            outcome = sum(p.verified_successes for p in mine) / (attempts + CONFIDENCE_PRIOR) if attempts else 0.0
            score = WEIGHT_FIT * _FIT[c.origin] + WEIGHT_SKILL * skill + WEIGHT_PRIOR * outcome
            tier = 1 if c.target_changed else 0
            feats = {"tier": tier, "primary_fit": _FIT[c.origin], "skill_prior": skill, "prior_outcome": outcome,
                     "prior_attempts": attempts, "prior_episode_ids": tuple(i for p in mine for i in p.episode_ids)}
            rows.append((tier, -score, c.candidate_id, c, score, feats))
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
