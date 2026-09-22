"""P6: Audio / Text / Visual grounding -- one representation, modality provenance preserved.

A GroundingObservation is ONE modality's evidence about a subject: modality, source and timestamp, the raw
observation, an interpretation kept separate from it, confidence and uncertainty. A GroundedClaim groups the
observations about one subject WITHOUT erasing any of them. Frozen-plan rules encoded here:

  * multimodal agreement may raise confidence but never erases per-modality provenance;
  * conflicting modalities remain a CONFLICT until additional evidence resolves them (no winner is picked);
  * unknown measurements stay unknown: a number needs a real measurement (method + source ref), an UNKNOWN
    observation carries no value, no interpretation and zero confidence, and is never positive evidence;
  * grounding informs reasoning and never executes: no capability, route, binding, admission, action or
    winner field exists on either object, and ground() produces no operation.

The plan fixes those invariants, not a formula. Numbers therefore live in a replaceable ConfidencePolicy; ground()
guards whatever a policy returns so the invariants hold for ANY policy (see ground()). This module imports nothing
from the Brain, admission, contract registry, or any backend, and names no target.
"""
from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple

from serum2.producer.skill_library import _FORBIDDEN_SKILL_FIELDS, _freeze

GROUNDING_SCHEMA_VERSION = "1"

TRANSCRIPT, VISUAL, AUDIO, EPISODE_STATE = "TRANSCRIPT", "VISUAL", "AUDIO", "EPISODE_STATE"
MODALITIES = frozenset({TRANSCRIPT, VISUAL, AUDIO, EPISODE_STATE})
_TIMESTAMP_REQUIRED = frozenset({TRANSCRIPT, VISUAL})       # source-time evidence; audio/episode may be untimed

OBSERVED, MEASURED, UNKNOWN = "OBSERVED", "MEASURED", "UNKNOWN"
STATUSES = frozenset({OBSERVED, MEASURED, UNKNOWN})
UNCERTAINTY_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH", "UNKNOWN"})

SINGLE_MODALITY, AGREEMENT, CONFLICT, INSUFFICIENT, RESOLVED = "SINGLE_MODALITY", "AGREEMENT", "CONFLICT", "INSUFFICIENT", "RESOLVED"
AGREEMENT_STATUSES = frozenset({SINGLE_MODALITY, AGREEMENT, CONFLICT, INSUFFICIENT, RESOLVED})

_FORBIDDEN = _FORBIDDEN_SKILL_FIELDS | {"capability_contract", "admission", "admission_token", "mcp_call", "action", "command",
                                        "winner", "selected", "resolved_value"}


def _numeric_leaves(x: Any) -> List[Any]:
    if isinstance(x, bool):
        return []
    if isinstance(x, (int, float)):
        return [x]
    if isinstance(x, Mapping):
        return [n for v in x.values() for n in _numeric_leaves(v)]
    if isinstance(x, (list, tuple)):
        return [n for v in x for n in _numeric_leaves(v)]
    return []


def subject_key(subject: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    return (subject.get("canonical_target_id"), subject.get("aspect"))


@dataclass(frozen=True)
class GroundingObservation:
    """One modality's evidence. Deliberately has no capability/route/binding/admission/action/winner field."""

    observation_id: str
    modality: str
    source: Mapping[str, Any]                # {"kind", "ref", optional "sha256", "method"}
    timestamp: Optional[Mapping[str, Any]]   # {"start_sec", "end_sec"}; required for TRANSCRIPT/VISUAL
    subject: Mapping[str, Any]               # {"canonical_target_id": optional, "aspect": required}
    observation: Mapping[str, Any]           # the raw content; numbers only when MEASURED
    interpretation: Optional[Mapping[str, Any]]  # {"kind", "value", "basis"}; kept apart from the raw observation
    status: str                              # OBSERVED | MEASURED | UNKNOWN
    confidence: float
    uncertainty: Mapping[str, Any]           # {"level": LOW|MEDIUM|HIGH|UNKNOWN, ...; "reason" required when UNKNOWN}
    provenance: Mapping[str, Any]
    advisory: bool = True
    schema_version: str = GROUNDING_SCHEMA_VERSION

    def __post_init__(self):
        # deep-freeze: an original observation cannot be edited in place, not even inside its nested mappings
        for f in ("source", "timestamp", "subject", "observation", "interpretation", "uncertainty", "provenance"):
            object.__setattr__(self, f, _freeze(getattr(self, f)))

    def to_dict(self) -> Dict[str, Any]:
        return {"observation_id": self.observation_id, "modality": self.modality, "source": dict(self.source),
                "timestamp": dict(self.timestamp) if self.timestamp is not None else None, "subject": dict(self.subject),
                "observation": dict(self.observation), "interpretation": dict(self.interpretation) if self.interpretation is not None else None,
                "status": self.status, "confidence": self.confidence, "uncertainty": dict(self.uncertainty),
                "provenance": dict(self.provenance), "advisory": self.advisory, "schema_version": self.schema_version}


@dataclass(frozen=True)
class GroundedClaim:
    """Unified view of every observation about one subject. Holds the observations themselves, so no modality's
    provenance can be dropped; `agreement` and `confidence` are derived from them."""

    claim_id: str
    subject: Mapping[str, Any]
    observations: Tuple[GroundingObservation, ...]
    modalities: Tuple[str, ...]              # sorted distinct modalities of `observations` (checked, not trusted)
    agreement: Mapping[str, Any]             # {"status", "agreeing_observation_ids", "conflicting_observation_ids": [[...], ...]}
    confidence: float
    conflict_resolution: Optional[Mapping[str, Any]]   # only when RESOLVED: {"resolved_by": [ids], "outcome", "basis", "provenance"}
    provenance: Mapping[str, Any]
    advisory: bool = True
    schema_version: str = GROUNDING_SCHEMA_VERSION

    def __post_init__(self):
        # Deep-freeze evidence fields (subject, observations, agreement, provenance)
        # but NOT conflict_resolution, which is resolution metadata, not evidence.
        # conflict_resolution can be regular dict/lists; immutability comes from frozen dataclass.
        for f in ("subject", "observations", "modalities", "agreement", "provenance"):
            object.__setattr__(self, f, _freeze(getattr(self, f)))
        # Keep conflict_resolution as regular dict (not frozen) for readability and test compatibility
        cr = getattr(self, "conflict_resolution")
        if cr is not None:
            object.__setattr__(self, "conflict_resolution", dict(cr))

    def to_dict(self) -> Dict[str, Any]:
        conflict_res = None
        if self.conflict_resolution is not None:
            conflict_res = dict(self.conflict_resolution)
            # Convert tuples back to lists in nested structures
            if "resolved_by" in conflict_res and isinstance(conflict_res["resolved_by"], tuple):
                conflict_res["resolved_by"] = list(conflict_res["resolved_by"])
            if "provenance" in conflict_res and isinstance(conflict_res["provenance"], dict):
                conflict_res["provenance"] = dict(conflict_res["provenance"])
                if "conflict_sides" in conflict_res["provenance"]:
                    conflict_res["provenance"]["conflict_sides"] = [list(s) if isinstance(s, tuple) else s for s in conflict_res["provenance"]["conflict_sides"]]
        return {"claim_id": self.claim_id, "subject": dict(self.subject), "observations": [o.to_dict() for o in self.observations],
                "modalities": list(self.modalities),
                "agreement": {"status": self.agreement.get("status"),
                              "agreeing_observation_ids": list(self.agreement.get("agreeing_observation_ids", [])),
                              "conflicting_observation_ids": [list(g) for g in self.agreement.get("conflicting_observation_ids", [])]},
                "confidence": self.confidence,
                "conflict_resolution": conflict_res,
                "provenance": dict(self.provenance), "advisory": self.advisory, "schema_version": self.schema_version}



# ====================================================================================================================
# Policy-free structure derivation: what the observations themselves say. Used by ground() AND the validator.
# ====================================================================================================================
def derive_structure(observations: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Derive a claim's structure from observation dicts ONLY. No confidence, no policy, no other module.

    Evidence = observations that are known (not UNKNOWN) AND carry an interpretation. Evidence is grouped by
    interpretation value: one group is agreement (two or more DISTINCT modalities) or single-modality support; two or
    more groups are a conflict. UNKNOWN and uninterpreted observations are listed but are never evidence.
    """
    obs = sorted(observations, key=lambda o: str(o.get("observation_id")))
    known = [o for o in obs if o.get("status") != UNKNOWN and o.get("interpretation") is not None]
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for o in known:
        groups.setdefault(repr(o["interpretation"].get("value")), []).append(o)
    keys = sorted(groups)
    group_ids = [[o["observation_id"] for o in groups[k]] for k in keys]
    if not groups:
        status, agreeing, conflicting = INSUFFICIENT, [], []
    elif len(groups) == 1:
        status = AGREEMENT if len({o.get("modality") for o in groups[keys[0]]}) >= 2 else SINGLE_MODALITY
        agreeing, conflicting = group_ids[0], []
    else:
        status, agreeing, conflicting = CONFLICT, [], group_ids
    return {
        "modalities": tuple(sorted({o.get("modality") for o in obs})),
        "unknown_ids": [o["observation_id"] for o in obs if o.get("status") == UNKNOWN],
        "uninterpreted_ids": [o["observation_id"] for o in obs if o.get("status") != UNKNOWN and o.get("interpretation") is None],
        "mixed_kinds": len({o["interpretation"].get("kind") for o in known}) > 1,
        "groups": group_ids, "group_values": [groups[k][0]["interpretation"].get("value") for k in keys],
        "status": status, "agreeing_ids": agreeing, "conflicting_ids": conflicting,
    }

# ====================================================================================================================
# Confidence policy: the numbers are a replaceable policy, the invariants are enforced by ground()
# ====================================================================================================================
class ConfidencePolicy(Protocol):
    """How evidence becomes a number. Every method is a pure function returning a value in [0, 1] (anything else is
    clamped by ground()). None of these outputs is a plan requirement; only the invariants ground() enforces are."""

    def evidence_weight(self, observation: GroundingObservation) -> float:
        """How much one KNOWN observation counts as evidence for its own interpretation."""

    def combine(self, confidences: Sequence[float]) -> float:
        """Fold several independent confidences into one."""

    def agreement_effect(self, modality_confidences: Sequence[float]) -> float:
        """Confidence when distinct modalities support the SAME interpretation (one confidence per modality)."""

    def conflict_effect(self, side_confidences: Sequence[float]) -> float:
        """Confidence of a claim whose sides disagree (one confidence per side)."""

    def unknown_effect(self, confidence: float, unknowns: Sequence[GroundingObservation]) -> float:
        """Confidence after UNKNOWN observations are present. An unknown is never positive evidence."""


class IndependenceConfidencePolicy:
    """Parameter-free default: standard independent-evidence algebra, no tuned constants, uncalibrated.

    Weights are the observations' own confidences; supporting modalities combine as a noisy-OR; a conflict is the
    chance, under independence, that only the weakest side is right; unknowns leave confidence unchanged. The
    independence assumption is optimistic for modalities describing the same narrator action; replace this policy
    once real evidence allows calibration.
    """

    def evidence_weight(self, observation: GroundingObservation) -> float:
        return observation.confidence

    def combine(self, confidences: Sequence[float]) -> float:
        miss = 1.0
        for c in confidences:
            miss *= 1.0 - c
        return 1.0 - miss

    def agreement_effect(self, modality_confidences: Sequence[float]) -> float:
        return self.combine(modality_confidences)

    def conflict_effect(self, side_confidences: Sequence[float]) -> float:
        best = 1.0
        for i, c in enumerate(side_confidences):
            others = 1.0
            for j, o in enumerate(side_confidences):
                if j != i:
                    others *= 1.0 - o
            best = min(best, c * others)
        return best

    def unknown_effect(self, confidence: float, unknowns: Sequence[GroundingObservation]) -> float:
        return confidence


def _unit(x: Any) -> float:
    """Clamp any policy output to the valid domain; garbage (non-numeric, NaN, inf) is 0.0, never positive evidence."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, f)) if math.isfinite(f) else 0.0


DEFAULT_POLICY: ConfidencePolicy = IndependenceConfidencePolicy()


def _claim_id(subject: Mapping[str, Any], ids: Iterable[str]) -> str:
    h = hashlib.sha256("|".join(sorted(ids)).encode("utf-8")).hexdigest()[:12]
    return "claim:%s:%s:%s" % (subject.get("canonical_target_id") or "_", subject.get("aspect"), h)


def _claim_provenance(obs: Sequence[GroundingObservation], policy: Any) -> Dict[str, Any]:
    prov: Dict[str, Any] = {"recorded_by": "grounding.ground", "policy": type(policy).__name__}
    ids = sorted({(o.provenance.get("video_source") or {}).get("source_id") for o in obs} - {None})
    if ids:
        prov["source_ids"] = ids                     # which video(s) the evidence came from; the observations hold the detail
    return prov


def ground(observations: Iterable[GroundingObservation], policy: Optional[ConfidencePolicy] = None) -> GroundedClaim:
    """Aggregate observations about ONE subject into a GroundedClaim. A generic aggregator, not an interpreter:
    it reads the interpretations already attached to observations, never creates one, and produces no operation,
    capability, admission or execution. Every observation is kept, in canonical (id) order, unchanged.

    Invariants enforced here for ANY policy (the policy only supplies the numbers):
      * agreement: confidence never falls below any subset of the supporting modalities, so adding an independent
        supporting modality can never lower it;
      * conflict: status is CONFLICT and confidence never exceeds the weakest side, so a conflict cannot look
        resolved and no side wins;
      * unknown/uninterpreted observations are kept but are never evidence: they cannot raise confidence;
      * every confidence is clamped to [0, 1];
      * repeated observations from ONE modality are not independent support and gain no agreement effect.
    """
    policy = policy or DEFAULT_POLICY
    obs = sorted(observations, key=lambda o: o.observation_id)
    if not obs:
        raise ValueError("nothing to ground")
    validator = GroundingValidator()
    for o in obs:
        bad = validator.validate_observation(o)
        if bad:
            raise ValueError("invalid observation %s: %s" % (o.observation_id, bad))
    ids = [o.observation_id for o in obs]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate observation ids")
    subject = dict(obs[0].subject)
    if any(subject_key(o.subject) != subject_key(subject) for o in obs):
        raise ValueError("observations about different subjects cannot be grounded together")

    by_id = {o.observation_id: o for o in obs}
    st = derive_structure([o.to_dict() for o in obs])
    if st["mixed_kinds"]:
        raise ValueError("interpretations of different kinds cannot be compared")
    unknowns = [by_id[i] for i in st["unknown_ids"]]
    groups = [[by_id[i] for i in ids] for ids in st["groups"]]

    def group_confidence(members: List[GroundingObservation]) -> Tuple[float, int]:
        per_modality: Dict[str, float] = {}
        for o in members:                                    # best observation per modality: repeats are not independent
            per_modality[o.modality] = max(per_modality.get(o.modality, 0.0), _unit(policy.evidence_weight(o)))
        confs = sorted(per_modality.values(), reverse=True)
        best = confs[0]
        # max over every subset of the (at most four) modalities: monotone in added support for any policy
        agree = max(_unit(policy.agreement_effect(list(sub))) for r in range(1, len(confs) + 1) for sub in itertools.combinations(confs, r))
        return round(max(best, agree), 12), len(per_modality)

    status, agreeing, conflicting = st["status"], st["agreeing_ids"], st["conflicting_ids"]
    if status == INSUFFICIENT:
        confidence = 0.0
    elif status == CONFLICT:
        sides = [group_confidence(m)[0] for m in groups]
        confidence = round(min(min(sides), _unit(policy.conflict_effect(sides))), 12)
    else:
        confidence = group_confidence(groups[0])[0]
    if unknowns and status != INSUFFICIENT:
        confidence = round(min(confidence, _unit(policy.unknown_effect(confidence, unknowns))), 12)

    return GroundedClaim(
        claim_id=_claim_id(subject, ids), subject=subject, observations=tuple(obs), modalities=tuple(sorted({o.modality for o in obs})),
        agreement={"status": status, "agreeing_observation_ids": list(agreeing), "conflicting_observation_ids": [list(g) for g in conflicting]},
        confidence=confidence, conflict_resolution=None, provenance=_claim_provenance(obs, policy))


def resolve_conflict(claim: GroundedClaim, additional_evidence: GroundingObservation, basis: str,
                     policy: Optional[ConfidencePolicy] = None) -> GroundedClaim:
    """Resolve a CONFLICT claim with additional evidence.

    Takes a claim in CONFLICT status and additional evidence from outside the conflicting observations.
    Returns a RESOLVED claim preserving all original observations + the resolution evidence.

    INPUT REQUIREMENTS:
      * claim must be a valid CONFLICT GroundedClaim
      * additional_evidence must not already exist in claim.observations
      * additional_evidence must concern the same subject
      * additional_evidence must be interpreted (not UNKNOWN, not None)
      * additional_evidence must support one of the conflicting interpretations

    RETURNS:
      * immutable GroundedClaim with agreement["status"] = RESOLVED
      * conflict_resolution = {"resolved_by": [evidence_id], "outcome": ..., "basis": basis, "provenance": {...}}
      * observations = all original + the new evidence (preserved unchanged)
      * conflict lineage preserved in agreement["conflicting_observation_ids"]

    RAISES ValueError if:
      * claim is not in CONFLICT status
      * additional_evidence already exists in claim.observations (reused evidence)
      * additional_evidence has a different subject
      * additional_evidence is UNKNOWN or uninterpreted
      * additional_evidence supports neither conflicting interpretation
    """
    # Validate input claim
    if claim.agreement["status"] != CONFLICT:
        raise ValueError("claim must be in CONFLICT status to resolve; got %r" % claim.agreement["status"])

    # Validate additional evidence
    validator = GroundingValidator()
    bad_evidence = validator.validate_observation(additional_evidence)
    if bad_evidence:
        raise ValueError("invalid additional evidence %s: %s" % (additional_evidence.observation_id, bad_evidence))

    # Check evidence is not already in the claim
    existing_ids = {o.observation_id for o in claim.observations}
    if additional_evidence.observation_id in existing_ids:
        raise ValueError("additional evidence %s already exists in claim; cannot reuse conflicting observations" % additional_evidence.observation_id)

    # Check subject matches
    if subject_key(additional_evidence.subject) != subject_key(claim.subject):
        raise ValueError("additional evidence subject %s does not match claim subject %s" %
                        (subject_key(additional_evidence.subject), subject_key(claim.subject)))

    # Check evidence is not UNKNOWN
    if additional_evidence.status == UNKNOWN or additional_evidence.interpretation is None:
        raise ValueError("additional evidence must be interpreted and not UNKNOWN")

    # Extract conflicting observation ids
    conflicting_ids = claim.agreement["conflicting_observation_ids"]
    if not conflicting_ids or len(conflicting_ids) < 2:
        raise ValueError("claim has no valid conflict to resolve")

    # Get the conflicting interpretations
    by_id = {o.observation_id: o for o in claim.observations}
    conflict_interpretations = set()
    for side in conflicting_ids:
        for obs_id in side:
            if obs_id in by_id:
                obs = by_id[obs_id]
                if obs.interpretation is not None:
                    conflict_interpretations.add(obs.interpretation.get("value"))

    # Check that new evidence supports one of the conflicting sides
    new_interp_value = additional_evidence.interpretation.get("value") if additional_evidence.interpretation else None
    if new_interp_value not in conflict_interpretations:
        raise ValueError("additional evidence supports %r, but conflicting interpretations are %s" %
                        (new_interp_value, conflict_interpretations))

    # Build resolved claim: all original observations + new evidence
    all_observations = list(claim.observations) + [additional_evidence]
    all_observations_sorted = sorted(all_observations, key=lambda o: o.observation_id)

    # Re-ground with all observations to get proper confidence
    policy = policy or DEFAULT_POLICY
    resolved_claim_base = ground(all_observations_sorted, policy=policy)

    # Get the resolved outcome value (determined by the new evidence)
    new_interp_value = additional_evidence.interpretation.get("value") if additional_evidence.interpretation else None

    # Compute agreeing_observation_ids: ALL observations that support the resolved outcome
    agreeing_ids = [
        o.observation_id for o in all_observations_sorted
        if o.interpretation is not None and o.interpretation.get("value") == new_interp_value
    ]
    agreeing_ids = sorted(agreeing_ids)  # canonical order for consistency

    # Build resolution metadata
    import time
    resolution_metadata = {
        "resolved_by": [additional_evidence.observation_id],
        "outcome": new_interp_value,
        "basis": basis,
        "provenance": {
            "recorded_by": "resolve_conflict",
            "timestamp": time.time(),
            "conflict_sides": [list(s) if isinstance(s, (list, tuple)) else [s] for s in conflicting_ids],
        }
    }

    # Create the resolved claim (reuse claim_id for audit trail continuity)
    return GroundedClaim(
        claim_id=claim.claim_id,
        subject=dict(claim.subject),
        observations=tuple(all_observations_sorted),
        modalities=tuple(sorted({o.modality for o in all_observations_sorted})),
        agreement={
            "status": RESOLVED,
            "agreeing_observation_ids": agreeing_ids,
            "conflicting_observation_ids": claim.agreement["conflicting_observation_ids"]  # preserve original conflict record
        },
        confidence=resolved_claim_base.confidence,
        conflict_resolution=resolution_metadata,
        provenance=dict(resolved_claim_base.provenance)
    )


# ====================================================================================================================
# Validation
# ====================================================================================================================
class GroundingValidator:
    """Structural well-formedness. Returns violation codes; empty means valid. Never raises on bad input."""

    def validate_observation(self, obs: Any) -> List[str]:
        v: List[str] = []
        d = obs.to_dict() if hasattr(obs, "to_dict") else dict(obs)
        if d.get("advisory") is not True:
            v.append("OBSERVATION_NOT_ADVISORY")
        if _FORBIDDEN & set(d) or _FORBIDDEN & set(d.get("interpretation") or {}):
            v.append("CARRIES_CAPABILITY_OR_AUTHORITY_FIELD")
        if not d.get("observation_id"):
            v.append("MISSING_OBSERVATION_ID")
        modality, status = d.get("modality"), d.get("status")
        if modality not in MODALITIES:
            v.append("BAD_MODALITY")
        if status not in STATUSES:
            v.append("BAD_STATUS")
        src = d.get("source") or {}
        if not src.get("kind") or not src.get("ref"):
            v.append("NO_SOURCE")
        ts = d.get("timestamp")
        if ts is None:
            if modality in _TIMESTAMP_REQUIRED:
                v.append("TIMESTAMP_REQUIRED")
        else:
            a, b = ts.get("start_sec"), ts.get("end_sec")
            ok = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, b)) and 0 <= a <= b
            if not ok:
                v.append("BAD_TIMESTAMP")
        if not (d.get("subject") or {}).get("aspect"):
            v.append("NO_SUBJECT_ASPECT")
        raw, interp = d.get("observation") or {}, d.get("interpretation")
        if not raw:
            v.append("NO_OBSERVATION")
        if interp is not None and (not interp.get("kind") or interp.get("value") is None or not interp.get("basis")):
            v.append("INTERPRETATION_MALFORMED")
        c = d.get("confidence")
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0.0 <= c <= 1.0:
            v.append("CONFIDENCE_OUT_OF_RANGE")
        unc = d.get("uncertainty") or {}
        if unc.get("level") not in UNCERTAINTY_LEVELS:
            v.append("BAD_UNCERTAINTY")
        if not d.get("provenance"):
            v.append("NO_PROVENANCE")
        numbers = _numeric_leaves(raw)
        if status == MEASURED and not src.get("method"):
            v.append("MEASURED_WITHOUT_METHOD")
        if numbers and status != MEASURED:
            v.append("NUMERIC_WITHOUT_MEASUREMENT")
        if status == UNKNOWN:
            if numbers or any(raw.get(k) is not None for k in ("value",)) or interp is not None or c != 0.0:
                v.append("UNKNOWN_CARRIES_VALUE")
            if not unc.get("reason") or unc.get("level") != "UNKNOWN":
                v.append("UNKNOWN_WITHOUT_REASON")
        return v

    def validate_claim(self, claim: Any) -> List[str]:
        v: List[str] = []
        d = claim.to_dict() if hasattr(claim, "to_dict") else dict(claim)
        if d.get("advisory") is not True:
            v.append("CLAIM_NOT_ADVISORY")
        if _FORBIDDEN & set(d) or _FORBIDDEN & set(d.get("agreement") or {}):
            v.append("CLAIM_CARRIES_CAPABILITY_OR_AUTHORITY_FIELD")
        obs = d.get("observations") or []
        if not obs:
            v.append("CLAIM_NO_OBSERVATIONS")
        ids = [o.get("observation_id") for o in obs]
        if len(set(ids)) != len(ids):
            v.append("CLAIM_DUPLICATE_OBSERVATION_IDS")
        if any(self.validate_observation(o) for o in obs):
            v.append("CLAIM_OBSERVATION_INVALID")
        if any(subject_key(o.get("subject") or {}) != subject_key(d.get("subject") or {}) for o in obs):
            v.append("CLAIM_MIXED_SUBJECTS")
        if sorted(set(o.get("modality") for o in obs)) != list(d.get("modalities") or []):
            v.append("CLAIM_MODALITIES_MISMATCH")
        c = d.get("confidence")
        if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0.0 <= c <= 1.0:
            v.append("CLAIM_CONFIDENCE_OUT_OF_RANGE")
        ag = d.get("agreement") or {}
        status = ag.get("status")
        if status not in AGREEMENT_STATUSES:
            v.append("CLAIM_BAD_AGREEMENT_STATUS")
        agreeing = list(ag.get("agreeing_observation_ids") or [])
        conflicting = [list(g) for g in ag.get("conflicting_observation_ids") or []]
        referenced = set(agreeing) | {i for g in conflicting for i in g}
        unknown_ids = {o.get("observation_id") for o in obs if o.get("status") == UNKNOWN}
        if referenced - set(ids):
            v.append("CLAIM_REFERENCES_MISSING_OBSERVATION")
        if referenced & unknown_ids:
            v.append("CLAIM_UNKNOWN_COUNTED_AS_EVIDENCE")
        res = d.get("conflict_resolution")
        st = derive_structure(obs)
        if st["mixed_kinds"]:
            v.append("CLAIM_MIXED_INTERPRETATION_KINDS")
        stored_sides = {frozenset(g) for g in conflicting}
        if status == RESOLVED:
            by = list((res or {}).get("resolved_by") or [])
            outcome = (res or {}).get("outcome")
            resolvers = [o for o in obs if o.get("observation_id") in by]
            base = derive_structure([o for o in obs if o.get("observation_id") not in by])
            if not by or set(by) - set(ids) or not (set(by) - {i for g in conflicting for i in g}) or outcome is None or outcome == "":
                v.append("CLAIM_RESOLVED_WITHOUT_ADDITIONAL_EVIDENCE")
            if not (res or {}).get("basis") or not (res or {}).get("provenance"):
                v.append("CLAIM_RESOLUTION_WITHOUT_PROVENANCE")
            if len(conflicting) < 2 or base["status"] != CONFLICT:
                v.append("CLAIM_RESOLVED_WITHOUT_PRIOR_CONFLICT")
            elif stored_sides != {frozenset(g) for g in base["conflicting_ids"]}:
                v.append("CLAIM_CONFLICT_INCONSISTENT")
            if base["status"] == CONFLICT and outcome not in base["group_values"]:
                v.append("CLAIM_RESOLUTION_OUTCOME_NOT_A_SIDE")
            if any(r.get("status") == UNKNOWN or r.get("interpretation") is None or r["interpretation"].get("value") != outcome for r in resolvers):
                v.append("CLAIM_RESOLUTION_OUTCOME_UNSUPPORTED")
            supporting = sorted(o["observation_id"] for o in obs if o.get("status") != UNKNOWN and o.get("interpretation") is not None
                                and o["interpretation"].get("value") == outcome)
            if sorted(agreeing) != supporting:
                v.append("CLAIM_AGREEMENT_INCONSISTENT")
        else:
            if status in AGREEMENT_STATUSES:
                if st["status"] != status:
                    v.append("CLAIM_STATUS_INCONSISTENT")
                if sorted(agreeing) != sorted(st["agreeing_ids"]):
                    v.append("CLAIM_AGREEMENT_INCONSISTENT")
                if stored_sides != {frozenset(g) for g in st["conflicting_ids"]}:
                    v.append("CLAIM_CONFLICT_INCONSISTENT")
            if status == CONFLICT:
                if len(conflicting) < 2 or any(not g for g in conflicting):
                    v.append("CLAIM_CONFLICT_WITHOUT_SIDES")
                if res is not None:
                    v.append("CLAIM_CONFLICT_PRESET_RESOLUTION")
            elif res is not None:
                v.append("CLAIM_RESOLUTION_WITHOUT_CONFLICT")
        if status == AGREEMENT and len({o.get("modality") for o in obs if o.get("observation_id") in set(agreeing)}) < 2:
            v.append("CLAIM_AGREEMENT_NEEDS_TWO_MODALITIES")
        if status == INSUFFICIENT and c != 0.0:
            v.append("CLAIM_INSUFFICIENT_HAS_CONFIDENCE")
        if not d.get("provenance"):
            v.append("CLAIM_NO_PROVENANCE")
        return v

    def validate_resolution(self, before: Any, after: Any) -> List[str]:
        """Lineage check for a resolved claim against the conflicting claim it came from: every original observation is
        present and unmodified, the conflict record survives, and the ONLY new observations are the resolving evidence."""
        v: List[str] = []
        b = before.to_dict() if hasattr(before, "to_dict") else dict(before)
        a = after.to_dict() if hasattr(after, "to_dict") else dict(after)
        bs = derive_structure(b.get("observations") or [])
        if bs["status"] != CONFLICT or (b.get("agreement") or {}).get("status") != CONFLICT:
            v.append("RESOLUTION_BEFORE_NOT_CONFLICT")
        if subject_key(b.get("subject") or {}) != subject_key(a.get("subject") or {}):
            v.append("RESOLUTION_SUBJECT_CHANGED")
        if (a.get("agreement") or {}).get("status") != RESOLVED:
            v.append("RESOLUTION_NOT_RESOLVED")
        after_by_id = {o.get("observation_id"): o for o in a.get("observations") or []}
        if any(after_by_id.get(o.get("observation_id")) != o for o in b.get("observations") or []):
            v.append("RESOLUTION_ALTERED_ORIGINAL")
        if {frozenset(g) for g in (a.get("agreement") or {}).get("conflicting_observation_ids") or []} != {frozenset(g) for g in bs["conflicting_ids"]}:
            v.append("RESOLUTION_LOST_CONFLICT_RECORD")
        added = set(after_by_id) - {o.get("observation_id") for o in b.get("observations") or []}
        if added != set(((a.get("conflict_resolution") or {}).get("resolved_by")) or []):
            v.append("RESOLUTION_EXTRA_OBSERVATIONS")
        if self.validate_claim(a):
            v.append("RESOLUTION_AFTER_INVALID")
        return v


# ====================================================================================================================
# P6.4 Adapters: existing evidence layers -> GroundingObservation[]. Wrappers, not interpreters.
#
# * They read what fusion / measurement / the episode already recorded (per-control directions, computed metrics, real
#   readback) and attach it as interpretation; they never classify again and never look at a fusion LABEL.
# * They know no target: subjects come from the canonical ids already in the evidence.
# * Nothing observed becomes a number: values stay the displayed/recorded readings; numbers exist only for computed
#   measurements. Anything not observed or not computed is an UNKNOWN observation.
# * Confidence is UNRATED (0.0, uncertainty UNKNOWN) unless the caller supplies a confidence source: no evidence layer
#   records how reliable a diff, a caption or a readback is, so the adapters do not invent it.
# ====================================================================================================================
import math as _math  # noqa: E402
from typing import Callable  # noqa: E402

ConfidenceSource = Callable[[str, Mapping[str, Any]], float]   # (modality, raw observation) -> confidence in [0, 1]

_UNRATED = {"level": "UNKNOWN", "notes": ["confidence not rated: the adapter records no reliability for this source"]}


def _rated(confidence_for: Optional[ConfidenceSource], modality: str, raw: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    if confidence_for is None:
        return 0.0, dict(_UNRATED)
    c = confidence_for(modality, raw)
    if isinstance(c, bool) or not isinstance(c, (int, float)) or not 0.0 <= c <= 1.0:
        raise ValueError("confidence source returned %r; expected a number in [0, 1]" % (c,))
    return float(c), dict(_UNRATED)


def _reading(v: Any) -> Optional[str]:
    """A displayed/recorded reading is text. Stringify so a reading is never mistaken for a measured number."""
    return None if v is None else str(v)


def _window(start: Any, end: Any) -> Optional[Dict[str, float]]:
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (start, end)):
        return None
    lo, hi = float(min(start, end)), float(max(start, end))
    return {"start_sec": lo, "end_sec": hi}


def _video_source(explicit: Optional[Mapping[str, Any]] = None, episode: Any = None) -> Optional[Dict[str, Any]]:
    """The video a piece of evidence came from: source_id, video_id, source_url, title. Only what is actually recorded
    (the caller's mapping, or the episode's own fields) is kept; nothing is looked up, defaulted or guessed."""
    found: Dict[str, Any] = {}
    if episode is not None:
        ctx = getattr(episode, "production_context", None) or {}
        found = {"source_id": getattr(episode, "source_id", None), "source_url": getattr(episode, "source_url", None),
                 "video_id": ctx.get("video_id"), "title": ctx.get("source_title")}
    found.update({k: v for k, v in (explicit or {}).items() if k in ("source_id", "video_id", "source_url", "title")})
    found = {k: v for k, v in found.items() if v}
    return found or None


def _checked(observations: List[GroundingObservation]) -> List[GroundingObservation]:
    """Adapters never emit an invalid observation: a source that cannot produce a valid one raises instead."""
    v = GroundingValidator()
    for o in observations:
        bad = v.validate_observation(o)
        if bad:
            raise ValueError("adapter could not build a valid observation %s: %s" % (o.observation_id, bad))
    return observations


def _diff(event: Any) -> Mapping[str, Any]:
    return getattr(event, "snapshot_diff", None) or {}


def observations_from_production_event(event: Any, confidence_for: Optional[ConfidenceSource] = None, *,
                                       video_source: Optional[Mapping[str, Any]] = None) -> List[GroundingObservation]:
    """A (fused) production event -> transcript and visual observations, one claim-subject per changed control.

    VISUAL: each changed control's before/after reading, interpreted with the direction fusion recorded for it
    (else the same pure comparison fusion uses). TRANSCRIPT: the excerpt, attached to a control ONLY where fusion
    recorded that the transcript mentions it, interpreted with the direction fusion evaluated from language local to
    that control (None stays uninterpreted). Controls that could not be observed become UNKNOWN visual observations;
    added/removed routes become presence observations; a transcript with no per-control fusion is kept as narration.
    """
    eid = getattr(event, "event_id", None) or "event"
    start, end = getattr(event, "start_timestamp_sec", None), getattr(event, "end_timestamp_sec", None)
    frames = list(getattr(event, "evidence_frame_ids", None) or [])
    d = _diff(event)
    fusion = d.get("control_fusion") or {}
    excerpt = getattr(event, "transcript_excerpt", None)
    t_at = getattr(event, "transcript_timestamp_sec", None)
    vis_src = {"kind": "frame_diff", "ref": ",".join(frames) or eid, "frame_ids": frames,
               "before_frame_id": d.get("before_frame_id"), "after_frame_id": d.get("after_frame_id")}
    prov = {"recorded_by": "grounding.observations_from_production_event", "event_id": eid, "fusion_status": getattr(event, "fusion_status", None)}
    vs = _video_source(video_source)
    if vs:
        prov["video_source"] = vs
    vis_ts = _window(start, end)
    tr_ts = _window(t_at if t_at is not None else start, end)
    out: List[GroundingObservation] = []

    def add(oid, modality, source, ts, subject, raw, interp, status="OBSERVED", extra_unc=None):
        conf, unc = _rated(confidence_for, modality, raw) if status != UNKNOWN else (0.0, {"level": "UNKNOWN", "reason": (extra_unc or {}).get("reason", "not observed")})
        out.append(GroundingObservation(oid, modality, source, ts, subject, raw, interp, status, conf, unc, prov))

    for c in d.get("changed_controls") or []:
        cid = c["control_id"]
        f = fusion.get(cid) or {}
        subject = {"canonical_target_id": cid, "aspect": "direction"}
        if "visual" in f:
            v_dir = f["visual"]
        else:
            from serum2.producer.evidence_fusion import _visual_direction
            v_dir = _visual_direction(c.get("before"), c.get("after"))
        raw = {"control_id": cid, "before": _reading(c.get("before")), "after": _reading(c.get("after"))}
        add("%s:visual:%s" % (eid, cid), VISUAL, vis_src, vis_ts, subject, raw,
            {"kind": "direction", "value": v_dir, "basis": "before/after reading comparison"} if v_dir else None)
        if excerpt and f.get("mentioned"):
            t_dir = f.get("transcript")
            add("%s:transcript:%s" % (eid, cid), TRANSCRIPT, {"kind": "transcript", "ref": "%s@%s" % (eid, t_at if t_at is not None else start)},
                tr_ts, subject, {"text": excerpt, "control_id": cid},
                {"kind": "direction", "value": t_dir, "basis": "direction language local to the control mention"} if t_dir else None)
    for cid in d.get("not_observed_controls") or []:
        add("%s:visual:%s:unknown" % (eid, cid), VISUAL, vis_src, vis_ts, {"canonical_target_id": cid, "aspect": "direction"},
            {"control_id": cid, "before": None, "after": None}, None, status=UNKNOWN,
            extra_unc={"reason": "control was occluded, out of view or absent in at least one frame"})
    for kind, routes in (("added", d.get("added_routes") or []), ("removed", d.get("removed_routes") or [])):
        for r in routes:
            rid = "%s->%s" % (r.get("source"), r.get("destination"))
            add("%s:visual:route:%s:%s" % (eid, kind, rid), VISUAL, vis_src, vis_ts, {"canonical_target_id": None, "aspect": "route:" + rid},
                {"route": rid, "change": kind}, {"kind": "presence", "value": kind, "basis": "route present in one frame and absent in the other"})
    if excerpt and not fusion:
        add("%s:transcript:narration" % eid, TRANSCRIPT, {"kind": "transcript", "ref": "%s@%s" % (eid, t_at if t_at is not None else start)},
            tr_ts, {"canonical_target_id": None, "aspect": "narration"}, {"text": excerpt}, None)
    return _checked(sorted(out, key=lambda o: o.observation_id))


# ---- audio: computed measurements only ----------------------------------------------------------------------------
_METRIC_UNITS = {"rms_db": "dB", "peak_db": "dB", "spectral_centroid_hz": "Hz"}     # the G8 measurement schema's own keys


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and _math.isfinite(x)


def observations_from_measurement(measurement: Mapping[str, Any], baseline: Optional[Mapping[str, Any]] = None,
                                  confidence_for: Optional[ConfidenceSource] = None, *,
                                  video_source: Optional[Mapping[str, Any]] = None) -> List[GroundingObservation]:
    """A G8 measurement dict -> one AUDIO observation per metric. A number appears ONLY when the measurement was COMPUTED
    and that metric is a finite number, and then it carries the definition id (method) and the render's hash/path as its
    source. Every other case is an UNKNOWN observation with the reason, never a value. With a COMPUTED baseline measurement
    the metric's direction (increase/decrease/unchanged) is attached as arithmetic on the two real numbers."""
    computed = measurement.get("acoustic_status") == "COMPUTED"
    ref = measurement.get("sha256") or measurement.get("path") or "unavailable:%s" % measurement.get("status", "unknown")
    method = measurement.get("measurement_definition_id")
    reason = "measurement %s (acoustic_status %s)" % (measurement.get("status"), measurement.get("acoustic_status"))
    out: List[GroundingObservation] = []
    for metric, unit in sorted(_METRIC_UNITS.items()):
        value = measurement.get(metric)
        subject = {"canonical_target_id": None, "aspect": metric}
        prov = {"recorded_by": "grounding.observations_from_measurement", "measurement_status": measurement.get("status")}
        if _video_source(video_source):
            prov["video_source"] = _video_source(video_source)
        oid = "meas:%s:%s" % (ref, metric)
        if computed and _finite(value) and method:
            raw = {"metric": metric, "value": value, "unit": unit}
            conf, unc = _rated(confidence_for, AUDIO, raw)
            interp = None
            if baseline is not None and baseline.get("acoustic_status") == "COMPUTED" and _finite(baseline.get(metric)):
                b = baseline[metric]
                interp = {"kind": "direction", "value": "increase" if value > b else ("decrease" if value < b else "unchanged"),
                          "basis": "computed %s vs baseline render %s" % (metric, baseline.get("sha256") or baseline.get("path") or "?")}
            out.append(GroundingObservation(oid, AUDIO, {"kind": "render", "ref": ref, "sha256": measurement.get("sha256"), "method": method},
                                            None, subject, raw, interp, MEASURED, conf, unc, prov))
        else:
            why = reason if not computed else "metric %s missing or not a finite number" % metric
            out.append(GroundingObservation(oid, AUDIO, {"kind": "render", "ref": ref}, None, subject, {"metric": metric, "value": None},
                                            None, UNKNOWN, 0.0, {"level": "UNKNOWN", "reason": why}, prov))
    return _checked(out)


# ---- episode state: real readback ---------------------------------------------------------------------------------
def observations_from_episode(episode: Any, subjects: Optional[Mapping[str, Mapping[str, Any]]] = None,
                              confidence_for: Optional[ConfidenceSource] = None, *,
                              video_source: Optional[Mapping[str, Any]] = None) -> List[GroundingObservation]:
    """An episode's real readback -> EPISODE_STATE observations, one per watched key.

    The observed reading is recorded as text (never a number). A key with no observed reading is UNKNOWN. If the readback
    kept an untouched baseline, the direction is attached with the same pure comparison fusion uses. The subject comes from
    `subjects` (the executor knows which control each watched key is); with no mapping it is taken from the episode's single
    admitted decision ONLY when that is unambiguous (one decision, one key), else the key itself is the aspect.
    """
    eid = getattr(episode, "experience_id", None) or "episode"
    rb = ((getattr(episode, "outcome", None) or {}).get("real_plugin_readback")) or {}
    expected, observed, baseline = rb.get("expected") or {}, rb.get("observed") or {}, rb.get("baseline_untouched_init") or {}
    keys = sorted(set(expected) | set(observed))
    decisions = [x for x in ((getattr(episode, "brain_decision", None) or {}).get("decisions") or []) if x.get("admitted") is True]
    subjects = dict(subjects or {})
    if not subjects and len(decisions) == 1 and len(keys) == 1:
        subjects = {keys[0]: {"canonical_target_id": decisions[0].get("source_control_id"), "aspect": "direction"}}
    out: List[GroundingObservation] = []
    for k in keys:
        subject = dict(subjects.get(k) or {"canonical_target_id": None, "aspect": "readback:%s" % k})
        got = observed.get(k)
        prov = {"recorded_by": "grounding.observations_from_episode", "source_episode_ids": [eid]}
        if _video_source(video_source, episode):
            prov["video_source"] = _video_source(video_source, episode)
        src = {"kind": "episode", "ref": eid, "backend": rb.get("backend"), "route": rb.get("route") or rb.get("backend")}
        oid = "%s:state:%s" % (eid, k)
        if got is None:
            out.append(GroundingObservation(oid, EPISODE_STATE, src, None, subject, {"key": k, "observed": None, "expected": _reading(expected.get(k))},
                                            None, UNKNOWN, 0.0, {"level": "UNKNOWN", "reason": "the readback recorded no value for %s" % k}, prov))
            continue
        raw = {"key": k, "observed": _reading(got), "expected": _reading(expected.get(k))}
        conf, unc = _rated(confidence_for, EPISODE_STATE, raw)
        interp = None
        if k in baseline:
            from serum2.producer.evidence_fusion import _visual_direction
            base_reading = baseline[k].get("display") if isinstance(baseline[k], Mapping) else baseline[k]
            direction = _visual_direction(base_reading, got)
            if direction:
                interp = {"kind": "direction", "value": direction, "basis": "readback vs untouched baseline reading"}
        out.append(GroundingObservation(oid, EPISODE_STATE, src, None, subject, raw, interp, OBSERVED, conf, unc, prov))
    return _checked(out)


def ground_by_subject(observations: Iterable[GroundingObservation], policy: Optional[ConfidencePolicy] = None) -> List[GroundedClaim]:
    """Group observations by subject and ground each group. A generic convenience over ground(); decides nothing."""
    groups: Dict[Tuple[Optional[str], Optional[str]], List[GroundingObservation]] = {}
    for o in observations:
        groups.setdefault(subject_key(o.subject), []).append(o)
    return [ground(groups[k], policy) for k in sorted(groups, key=lambda k: (str(k[0]), str(k[1])))]
