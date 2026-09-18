"""Claim layer.

ClaimDefinition -- POLICY: what evidence would qualify for a claim of this type.
ClaimGroup      -- DERIVED: what the referenced evidence actually establishes.

CORE INVARIANT: breadth, coverage_scope, confidence and contradiction_state are
never stored as writable fields. They are exposed only as derived_* methods,
recomputed from supporting evidence + ClaimDefinition on every call.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .canonical import digest
from .record import (
    EvidenceRecord, NOT_RUN, PASS, FAIL, INCONCLUSIVE, NOT_RECORDED,
    OUTCOME_EFFECT, OUTCOME_NO_OBSERVED_EFFECT,
    OUTCOME_INCONCLUSIVE, OUTCOME_NOT_TESTED,
)

# ---- EXPLICIT outcome compatibility ----
# Stated as a positive enumeration rather than relying on absence from a default
# pair list. Only a demonstrated effect and a demonstrated absence of effect can
# contradict. NOT_TESTED contradicts nothing (no measurement was made).
# INCONCLUSIVE contradicts nothing (the measurement did not resolve).
CONTRADICTORY_OUTCOME_PAIRS = frozenset({
    frozenset({OUTCOME_EFFECT, OUTCOME_NO_OBSERVED_EFFECT}),
})


def outcomes_contradict(a: str, b: str) -> bool:
    if a == b:
        return False
    if OUTCOME_NOT_TESTED in (a, b):
        return False
    if OUTCOME_INCONCLUSIVE in (a, b):
        return False
    return frozenset({a, b}) in CONTRADICTORY_OUTCOME_PAIRS

# ---- isolation levels ----
SINGLE_FIELD = "single_field"
CONTROLLED_MULTI_FIELD = "controlled_multi_field"
PRODUCER_UNCONTROLLED = "producer_uncontrolled"

# ---- coverage scopes ----
INSTANCE = "instance"
FAMILY = "family"
BEHAVIOR_CLASS = "behavior_class"
EXHAUSTIVE = "exhaustive"

# ---- breadth ----
SINGLE_INSTANCE = "single_instance"
SAMPLED = "sampled"
EXHAUSTIVE_BREADTH = "exhaustive"

# ---- contradiction state ----
CONSISTENT = "CONSISTENT"
CONTRADICTED = "CONTRADICTED"

# ---- comparability: a mismatch of METHOD, not of RESULT ----
COMPARABLE = "COMPARABLE"
NOT_COMPARABLE = "NOT_COMPARABLE"

# ---- measurability (property of the CLAIM TYPE, not of an experiment) ----
OBJECTIVELY_MEASURABLE = "objectively_measurable"
NOT_OBJECTIVELY_RESOLVED = "not_objectively_resolved"

# ---- attribution kinds ----
FIELD_ATTRIBUTION = "field_attribution"
INTERACTION_ATTRIBUTION = "interaction_attribution"
NO_ATTRIBUTION = "no_attribution"

ATTRIBUTION_BY_ISOLATION = {
    SINGLE_FIELD: FIELD_ATTRIBUTION,
    CONTROLLED_MULTI_FIELD: INTERACTION_ATTRIBUTION,
    PRODUCER_UNCONTROLLED: NO_ATTRIBUTION,
}


def _measurement_condition_hashes(record: EvidenceRecord):
    out = set()
    for m in record.causal_measurements:
        sig = getattr(m, "measurement_condition_signature", None)
        if sig and sig.get("hash"):
            out.add(sig["hash"])
    return out


def _measurement_definition_ids(record: EvidenceRecord):
    return {m.measurement_definition_id for m in record.causal_measurements
            if getattr(m, "measurement_definition_id", None)}


def _shares_measurement_definition(r1: EvidenceRecord, r2: EvidenceRecord) -> bool:
    """Same KERNEL. Two algorithms under one metric name are not comparable."""
    d1, d2 = _measurement_definition_ids(r1), _measurement_definition_ids(r2)
    if not d1 or not d2:
        return False
    return bool(d1 & d2)


def _shares_measurement_condition(r1: EvidenceRecord, r2: EvidenceRecord) -> bool:
    """True when the two records have at least one measurement taken under the
    same measurement condition (experiment condition + identical stimulus)."""
    h1, h2 = _measurement_condition_hashes(r1), _measurement_condition_hashes(r2)
    if not h1 or not h2:
        return False
    return bool(h1 & h2)


def dimension_value(record: EvidenceRecord, dimension: str):
    """Typed extraction of a generalizing dimension from a record."""
    exp = record.experiment
    if dimension == "slot_index":
        return tuple(sorted(m["target_path"] for m in exp["mutations"]))
    if dimension == "route_content":
        return exp.get("mutation_signature")
    if dimension == "destination_module":
        mods = []
        for m in exp["mutations"]:
            v = m.get("value")
            if isinstance(v, dict) and "destModuleTypeString" in v:
                mods.append(v["destModuleTypeString"])
        return tuple(sorted(mods)) or None
    return None


@dataclass(frozen=True)
class ClaimDefinition:
    """Policy. Centralised so requirements cannot be weakened per-instance."""
    claim_type: str
    subject_pattern: Dict[str, Any]
    predicate: str
    required_gate: Dict[str, str]            # gate -> required status
    required_isolation: Tuple[str, ...]
    breadth_rule: Dict[str, Any]             # {"sampled_min": 2}
    coverage_rule: Dict[str, Any]            # {"generalizing_dimensions": [...], "family_min_distinct": 2}
    contradiction_rule: Dict[str, Any]
    dependency_rule: Dict[str, Any]
    measurability: str = OBJECTIVELY_MEASURABLE
    # {metric_name, target} or None. IN the identity hash, so a claim about
    # VoiceFilter.kParamFreq can never collide with one about FXDelay.kParamWet
    # under a shared predicate. No string naming convention rescues grouping.
    required_measurement: Optional[Dict[str, Any]] = None

    @property
    def claim_definition_id(self) -> str:
        return "%s:%s" % (self.claim_type, digest({
            "subject_pattern": self.subject_pattern,
            "predicate": self.predicate,
            "required_gate": self.required_gate,
            "required_isolation": list(self.required_isolation),
            "required_measurement": self.required_measurement,
        }, 8))

    def gates_met(self, gate_completeness: Dict[str, str]) -> bool:
        for gate, required in self.required_gate.items():
            if required in (None, "ANY"):
                continue
            if gate_completeness.get(gate) != required:
                return False
        return True

    def isolation_ok(self, isolation_level: str) -> bool:
        return isolation_level in self.required_isolation

    def attribution_kind(self, isolation_level: str) -> str:
        """controlled_multi_field NEVER yields field attribution."""
        return ATTRIBUTION_BY_ISOLATION.get(isolation_level, NO_ATTRIBUTION)

    def admits(self, record: EvidenceRecord) -> bool:
        """Eligibility. A claim about one property cannot be supported by a
        measurement of a different property."""
        if record.is_synthetic and not self.subject_pattern.get("allow_synthetic", False):
            return False
        if not self.isolation_ok(record.experiment.get("isolation_level")):
            return False
        if self.required_measurement:
            want_metric = self.required_measurement.get("metric_name")
            want_target = self.required_measurement.get("target")
            ok = False
            for m in record.causal_measurements:
                if m.metric != want_metric:
                    continue
                if want_target and m.target.field_path != want_target:
                    continue
                ok = True
                break
            if not ok:
                return False
        return True


@dataclass
class ClaimGroup:
    """References evidence; derives conclusions. No writable derived fields."""
    claim_definition: ClaimDefinition
    condition_signature_hash: str
    supporting_evidence: Tuple[str, ...] = ()
    contradicting_evidence: Tuple[str, ...] = ()
    relationships: Tuple[Dict[str, Any], ...] = ()
    reverify: Dict[str, Any] = field(default_factory=lambda: {
        "required": False, "reason": None, "required_comparison_conditions": []})
    # Single source of truth for records lives in the engine/store. The group
    # stores IDs only; this is a reference to the shared store, never a copy,
    # so the two representations cannot diverge.
    store: Dict[str, EvidenceRecord] = field(default_factory=dict, repr=False)

    @property
    def claim_definition_id(self) -> str:
        return self.claim_definition.claim_definition_id

    # ---- internal ----
    def _supporting_records(self) -> List[EvidenceRecord]:
        return [self.store[e] for e in self.supporting_evidence if e in self.store]

    # ---- measurement cohorts ----
    def _record_definition_ids(self, record) -> set:
        return {m.measurement_definition_id for m in record.causal_measurements
                if getattr(m, "measurement_definition_id", None)}

    def derived_cohorts(self) -> Dict[str, List[str]]:
        """Partition supporting evidence by measurement definition. Records
        measured a DIFFERENT way are not comparable, however similar the
        numbers look."""
        cohorts = {}
        for r in self._supporting_records():
            for did in (self._record_definition_ids(r) or {"<no_measurement>"}):
                cohorts.setdefault(did, []).append(r.experiment_id)
        return cohorts

    def derived_primary_cohort(self):
        cohorts = self.derived_cohorts()
        if not cohorts:
            return None
        return max(cohorts.items(), key=lambda kv: (len(kv[1]), kv[0]))[0]

    def derived_comparability(self) -> Dict[str, str]:
        primary = self.derived_primary_cohort()
        out = {}
        for r in self._supporting_records():
            dids = self._record_definition_ids(r) or {"<no_measurement>"}
            out[r.experiment_id] = COMPARABLE if primary in dids else NOT_COMPARABLE
        return out

    def _qualifying(self) -> List[EvidenceRecord]:
        primary = self.derived_primary_cohort()
        return [r for r in self._supporting_records()
                if self.claim_definition.gates_met(r.gate_completeness())
                and self.claim_definition.isolation_ok(r.experiment.get("isolation_level"))
                and (primary is None
                     or primary in (self._record_definition_ids(r) or {"<no_measurement>"}))]

    # ---- derived values (computed, never assigned) ----
    def derived_gate_completeness(self) -> Dict[str, Dict[str, str]]:
        return {r.experiment_id: r.gate_completeness() for r in self._supporting_records()}

    def derived_breadth(self) -> Optional[str]:
        q = self._qualifying()
        if not q:
            return None
        sampled_min = self.claim_definition.breadth_rule.get("sampled_min", 2)
        if len(q) >= sampled_min:
            return SAMPLED
        return SINGLE_INSTANCE

    def derived_coverage_scope(self) -> Optional[str]:
        """Coverage comes ONLY from the definition's explicit generalization
        rule -- never from evidence count."""
        q = self._qualifying()
        if not q:
            return None
        rule = self.claim_definition.coverage_rule
        dims = rule.get("generalizing_dimensions", [])
        min_distinct = rule.get("family_min_distinct", 2)
        for dim in dims:
            values = {dimension_value(r, dim) for r in q}
            values.discard(None)
            if len(values) >= min_distinct:
                return rule.get("scope_on_satisfy", FAMILY)
        return INSTANCE

    def derived_contradiction_state(self) -> str:
        return CONTRADICTED if self.contradicting_evidence else CONSISTENT

    def derived_attribution(self) -> str:
        kinds = {self.claim_definition.attribution_kind(
            r.experiment.get("isolation_level")) for r in self._qualifying()}
        if not kinds:
            return NO_ATTRIBUTION
        if FIELD_ATTRIBUTION in kinds and len(kinds) == 1:
            return FIELD_ATTRIBUTION
        if INTERACTION_ATTRIBUTION in kinds:
            return INTERACTION_ATTRIBUTION
        return NO_ATTRIBUTION

    def derived_confidence(self) -> str:
        if self.claim_definition.measurability == NOT_OBJECTIVELY_RESOLVED:
            return "not_objectively_resolved"
        if self.contradicting_evidence:
            return "disputed"
        q = self._qualifying()
        if not q:
            return "none"
        if self.derived_coverage_scope() == INSTANCE and self.derived_breadth() == SINGLE_INSTANCE:
            return "instance_only"
        return "generalizing"

    def summary(self) -> Dict[str, Any]:
        return {
            "claim_definition_id": self.claim_definition_id,
            "claim_type": self.claim_definition.claim_type,
            "predicate": self.claim_definition.predicate,
            "condition_signature_hash": self.condition_signature_hash,
            "supporting_evidence": list(self.supporting_evidence),
            "contradicting_evidence": list(self.contradicting_evidence),
            "derived_gate_completeness": self.derived_gate_completeness(),
            "derived_breadth": self.derived_breadth(),
            "derived_coverage_scope": self.derived_coverage_scope(),
            "derived_contradiction_state": self.derived_contradiction_state(),
            "derived_attribution": self.derived_attribution(),
            "derived_confidence": self.derived_confidence(),
            "derived_cohorts": self.derived_cohorts(),
            "derived_primary_cohort": self.derived_primary_cohort(),
            "derived_comparability": self.derived_comparability(),
            "relationships": list(self.relationships),
            "reverify": self.reverify,
        }


def query_claim_coverage(contract, record_store: Dict[str, "EvidenceRecord"]) -> Dict[str, Any]:
    """Read-only claim coverage query for the producer layer.

    Takes a CapabilityContract and a store of EvidenceRecords (keyed by
    experiment_id). Returns breadth and coverage_scope derived from the
    ClaimGroup machinery — the same machinery that ClaimGroup.derived_*
    methods use — without the producer layer needing to own or construct
    ClaimGroup objects.

    Coverage_scope is conservatively INSTANCE when the original ClaimDefinition
    is unavailable (we cannot know its generalizing_dimensions without it).
    Breadth is derived from the number of qualifying supporting records.

    Returns a dict with keys:
      breadth:        SINGLE_INSTANCE | SAMPLED | None
      coverage_scope: INSTANCE | (FAMILY if ClaimDefinition allows it) | None
      n_supporting:   count of supporting experiment IDs in contract provenance
      n_available:    count of those actually present in record_store
      generalizes:    bool -- True only when both breadth==SAMPLED and
                      coverage_scope != INSTANCE; always False without a
                      ClaimDefinition that declares generalizing_dimensions.
    """
    provenance = getattr(contract, "provenance", {}) or {}
    supporting_ids = provenance.get("supporting_evidence", [])
    n_supporting = len(supporting_ids)
    available = [record_store[eid] for eid in supporting_ids if eid in record_store]
    n_available = len(available)

    if not available:
        return {
            "breadth": None,
            "coverage_scope": None,
            "n_supporting": n_supporting,
            "n_available": 0,
            "generalizes": False,
            "detail": "no supporting records available in store",
        }

    # Reconstruct a minimal ClaimGroup to use the authoritative derived_* methods.
    # We don't have the original ClaimDefinition, so we use conservative rules:
    #   breadth_rule: sampled_min=2 (the standard default)
    #   coverage_rule: no generalizing_dimensions (conservative -- cannot claim FAMILY
    #                  without the original definition's explicit generalization rule)
    minimal_def = ClaimDefinition(
        claim_type="__coverage_query__",
        subject_pattern={},
        predicate="coverage_query",
        required_gate={},
        required_isolation=(SINGLE_FIELD, CONTROLLED_MULTI_FIELD, PRODUCER_UNCONTROLLED),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": False},
        dependency_rule={"enabled": False},
    )

    store = {r.experiment_id: r for r in available}
    # Use the first available record's condition hash (informational only for this query)
    cond_hash = available[0].experiment.get(
        "experiment_condition_signature", {}).get("hash", "unknown")
    group = ClaimGroup(
        claim_definition=minimal_def,
        condition_signature_hash=cond_hash,
        supporting_evidence=tuple(r.experiment_id for r in available),
        store=store,
    )

    breadth = group.derived_breadth()
    coverage_scope = group.derived_coverage_scope()

    # Without the real ClaimDefinition's generalizing_dimensions, coverage_scope
    # will always be INSTANCE (the conservative answer). This is correct: we cannot
    # claim FAMILY generalization without the explicit definition that established it.
    generalizes = (breadth in (SAMPLED, EXHAUSTIVE_BREADTH) and coverage_scope != INSTANCE)

    return {
        "breadth": breadth,
        "coverage_scope": coverage_scope,
        "n_supporting": n_supporting,
        "n_available": n_available,
        "generalizes": generalizes,
        "detail": (
            "coverage_scope=%r breadth=%r n_supporting=%d "
            "(conservative: no ClaimDefinition generalizing_dimensions available)" % (
                coverage_scope, breadth, n_supporting)
        ),
    }


class ClaimEngine:
    """Groups records mechanically. No prose interpretation anywhere."""

    def __init__(self, definitions: Dict[str, ClaimDefinition]):
        self.definitions = definitions
        self.groups: Dict[tuple, ClaimGroup] = {}
        self.records: Dict[str, EvidenceRecord] = {}
        self.rejected: List[Dict[str, Any]] = []

    def add(self, record: EvidenceRecord, claim_type: str):
        definition = self.definitions[claim_type]
        self.records[record.experiment_id] = record

        if not definition.admits(record):
            self.rejected.append({
                "experiment_id": record.experiment_id,
                "claim_type": claim_type,
                "reason": "isolation_level %r not permitted by definition, or synthetic"
                          % record.experiment.get("isolation_level"),
            })
            return None

        cond_hash = record.experiment["experiment_condition_signature"]["hash"]
        key = (definition.claim_definition_id, cond_hash)
        group = self.groups.get(key)
        if group is None:
            group = ClaimGroup(claim_definition=definition,
                               condition_signature_hash=cond_hash,
                               store=self.records)   # shared, not copied
            self.groups[key] = group

        # CONTRADICTION: same definition + same condition signature + incompatible outcome
        if self._is_contradiction(group, record):
            group.contradicting_evidence = group.contradicting_evidence + (record.experiment_id,)
            group.reverify = {
                "required": True,
                "reason": "incompatible outcomes under identical condition signature",
                "required_comparison_conditions": [
                    {"experiment_id": e, "condition_signature_hash": cond_hash}
                    for e in list(group.supporting_evidence) + [record.experiment_id]
                ],
            }
            return group

        group.supporting_evidence = group.supporting_evidence + (record.experiment_id,)
        return group

    def _is_contradiction(self, group: ClaimGroup, record: EvidenceRecord) -> bool:
        """Uses the explicit four-state compatibility function. NOT_TESTED and
        INCONCLUSIVE can never contradict anything."""
        rule = group.claim_definition.contradiction_rule
        if not group.supporting_evidence:
            return False
        new_outcome = record.outcome_signature()
        for eid in group.supporting_evidence:
            existing_rec = self.records[eid]
            if not outcomes_contradict(existing_rec.outcome_signature(), new_outcome):
                continue
            if rule.get("require_same_mutation", True):
                existing_sig = existing_rec.experiment.get("mutation_signature")
                if existing_sig != record.experiment.get("mutation_signature"):
                    continue
            # Measurements must be LIKE-FOR-LIKE: only measurements sharing a
            # measurement condition signature (same stimulus) can conflict.
            if rule.get("require_comparable_measurement", True):
                if not _shares_measurement_condition(existing_rec, record):
                    continue
                if not _shares_measurement_definition(existing_rec, record):
                    continue
            return True
        return False


    def derive_relationships(self):
        """Same mutation + DIFFERENT verified condition + different outcome
        => prerequisite_dependency. Correlation alone is never sufficient:
        every requirement in the definition's dependency_rule must be met."""
        entries = []
        for group in self.groups.values():
            for eid in group.supporting_evidence:
                entries.append((group, self.records[eid]))

        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                g1, r1 = entries[i]
                g2, r2 = entries[j]
                rel = self._try_dependency(g1, r1, g2, r2)
                if rel is None:
                    continue
                if rel not in g1.relationships:
                    g1.relationships = g1.relationships + (rel,)
                if rel not in g2.relationships:
                    g2.relationships = g2.relationships + (rel,)

    def _try_dependency(self, g1, r1, g2, r2):
        rule = g1.claim_definition.dependency_rule
        if not rule.get("enabled", True):
            return None

        # same mutation
        if rule.get("require_same_mutation", True):
            if r1.experiment.get("mutation_signature") != r2.experiment.get("mutation_signature"):
                return None

        # condition difference explicitly declared
        if g1.condition_signature_hash == g2.condition_signature_hash:
            return None
        delta = self._condition_delta(r1, r2)
        if rule.get("require_declared_condition_difference", True) and not delta:
            return None

        # relevant condition difference isolated
        if rule.get("require_isolated_condition_difference", True) and len(delta) != 1:
            return None

        # condition difference verified at runtime
        if rule.get("require_runtime_verified", True):
            if not (r1.runtime_verified() and r2.runtime_verified()):
                return None

        if rule.get("require_same_measurement_definition", True):
            if not _shares_measurement_definition(r1, r2):
                return None

        # outcome difference observed
        o1, o2 = r1.outcome_signature(), r2.outcome_signature()
        if rule.get("require_outcome_difference", True) and o1 == o2:
            return None
        # A dependency requires a demonstrated effect AND a demonstrated absence.
        # NOT_TESTED / INCONCLUSIVE can never establish one.
        if {o1, o2} != {OUTCOME_EFFECT, OUTCOME_NO_OBSERVED_EFFECT}:
            return None

        with_effect = r1 if o1 == OUTCOME_EFFECT else r2
        without_effect = r1 if o1 == OUTCOME_NO_OBSERVED_EFFECT else r2
        return {
            "type": "prerequisite_dependency",
            "mutation_signature": r1.experiment.get("mutation_signature"),
            "differing_condition_fields": delta,
            "condition_with_effect": with_effect.experiment["experiment_condition_signature"]["prerequisites"],
            "condition_without_effect": without_effect.experiment["experiment_condition_signature"]["prerequisites"],
            "evidence": sorted([r1.experiment_id, r2.experiment_id]),
        }

    @staticmethod
    def _condition_delta(r1: EvidenceRecord, r2: EvidenceRecord) -> List[str]:
        c1 = {k: v for k, v in r1.experiment["experiment_condition_signature"]["prerequisites"]}
        c2 = {k: v for k, v in r2.experiment["experiment_condition_signature"]["prerequisites"]}
        keys = set(c1) | set(c2)
        return sorted(k for k in keys if c1.get(k) != c2.get(k))
