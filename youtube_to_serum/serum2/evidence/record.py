"""EvidenceRecord: immutable observation of ONE experiment.

Carries NO interpretation. No PROVEN/SAMPLED/PARTIAL, no confidence, no
coverage_scope, no breadth, no generalized claims. Those live at the claim
layer and are computed there.

Gate statuses are exactly: NOT_RUN | PASS | FAIL | INCONCLUSIVE
NO_OBSERVED_EFFECT is a causal-measurement status, NOT a record status, and
never implies NON_AUDIBLE_BY_DESIGN.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from serum2.qualification.a3_evidence_extension import PersistenceLifecycleEvidence

# ---- gate statuses ----
NOT_RUN = "NOT_RUN"
PASS = "PASS"
FAIL = "FAIL"
INCONCLUSIVE = "INCONCLUSIVE"
GATE_STATUSES = (NOT_RUN, PASS, FAIL, INCONCLUSIVE)

# ---- causal measurement statuses ----
EFFECT_OBSERVED = "EFFECT_OBSERVED"
NO_OBSERVED_EFFECT = "NO_OBSERVED_EFFECT"
WRONG_DIRECTION = "WRONG_DIRECTION"

# ---- causal OUTCOME domain (record level) ----
# NOT_TESTED is not a negative result. INCONCLUSIVE is not a negative result.
# Only EFFECT vs NO_OBSERVED_EFFECT are ever mutually contradictory.
OUTCOME_EFFECT = "EFFECT"
OUTCOME_NO_OBSERVED_EFFECT = "NO_OBSERVED_EFFECT"
OUTCOME_INCONCLUSIVE = "INCONCLUSIVE"
OUTCOME_NOT_TESTED = "NOT_TESTED"
OUTCOMES = (OUTCOME_EFFECT, OUTCOME_NO_OBSERVED_EFFECT,
            OUTCOME_INCONCLUSIVE, OUTCOME_NOT_TESTED)

# ---- sentinel for historical data that was genuinely never captured ----
NOT_RECORDED = "NOT_RECORDED"

GATES = ("generation", "load", "render", "causal", "persistence", "exercise")


@dataclass(frozen=True)
class MeasurementTarget:
    """Structured. Meaning is never inferred from free text."""
    field_path: str
    module: Optional[str] = None
    parameter: Optional[str] = None


@dataclass(frozen=True)
class CausalMeasurement:
    metric: str
    target: MeasurementTarget
    baseline: Optional[float]
    treatment: Optional[float]
    delta: Optional[float]
    expected_direction: str
    observed_direction: Optional[str]
    threshold: Optional[float]
    status: str                      # EFFECT_OBSERVED | NO_OBSERVED_EFFECT | WRONG_DIRECTION | NOT_RUN
    # experiment condition + this measurement's stimulus. Two measurements are
    # comparable only when these hashes match.
    measurement_condition_signature: Optional[Dict[str, Any]] = None
    # WHICH kernel produced this scalar. Comparability additionally requires
    # this to match -- two algorithms sharing a metric_name are NOT comparable.
    measurement_definition_id: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status == EFFECT_OBSERVED


@dataclass(frozen=True)
class EvidenceArm:
    """Generic experiment arm. 'control'/'treatment' are role VALUES, not
    structural assumptions baked into the model."""
    arm_id: str
    role: str
    declared_context: Dict[str, Any]
    observed_context: Optional[Dict[str, Any]]
    state_observation: Optional[Dict[str, Any]]
    load_status: str
    render_status: str
    artifacts: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    experiment_id: str
    epoch: Dict[str, Any]
    experiment: Dict[str, Any]                     # declared spec (mutations, isolation, signatures)
    arms: Tuple[EvidenceArm, ...]
    runtime_verifications: Tuple[Dict[str, Any], ...]
    state_observation: Dict[str, Any]
    load_observation: Dict[str, Any]
    render_observation: Dict[str, Any]
    causal_measurements: Tuple[CausalMeasurement, ...]
    persistence_observation: Dict[str, Any]
    integrity: Dict[str, Any] = field(default_factory=lambda: {
        "synthetic": False,
        "contradictions": [],
        "relationships": [],
        "reverify_required": False,
    })
    # Populated only when spec.probe_semantics == "NUMERIC_CLAMP_RANGE".
    # Empty dict on all non-clamp records; never inferred from persistence failures.
    structural_observation: Dict[str, Any] = field(default_factory=dict)
    exercise_measurements: Tuple[CausalMeasurement, ...] = field(default_factory=tuple)
    persistence_lifecycle: Optional["PersistenceLifecycleEvidence"] = None

    def __getattr__(self, name: str):
        # Old pickled records lack structural_observation. Return the correct
        # default rather than AttributeError so existing pkl files stay usable.
        if name == "structural_observation":
            return {}
        # Old pickled records lack exercise_measurements. Return empty tuple.
        if name == "exercise_measurements":
            return ()
        # Old pickled records lack persistence_lifecycle. Return default (all NOT_RUN).
        if name == "persistence_lifecycle":
            from serum2.qualification.a3_evidence_extension import DEFAULT_PERSISTENCE_LIFECYCLE
            return DEFAULT_PERSISTENCE_LIFECYCLE
        raise AttributeError(name)

    # ---- gate readings: observations, not verdicts ----
    def gate(self, name: str) -> str:
        if name == "generation":
            return self.state_observation.get("status", NOT_RUN)
        if name == "load":
            return self.load_observation.get("status", NOT_RUN)
        if name == "render":
            return self.render_observation.get("status", NOT_RUN)
        if name == "causal":
            if not self.causal_measurements:
                return NOT_RUN
            statuses = [m.status for m in self.causal_measurements]
            if all(s == EFFECT_OBSERVED for s in statuses):
                return PASS
            if any(s == WRONG_DIRECTION for s in statuses):
                return FAIL
            if all(s == NO_OBSERVED_EFFECT for s in statuses):
                return FAIL
            return INCONCLUSIVE
        if name == "exercise":
            if not self.exercise_measurements:
                return NOT_RUN
            statuses = [m.status for m in self.exercise_measurements]
            if all(s == EFFECT_OBSERVED for s in statuses):
                return PASS
            if any(s == WRONG_DIRECTION for s in statuses):
                return FAIL
            if all(s == NO_OBSERVED_EFFECT for s in statuses):
                return FAIL
            return INCONCLUSIVE
        if name == "persistence":
            return self.persistence_observation.get("status", NOT_RUN)
        raise KeyError(name)

    def gate_completeness(self) -> Dict[str, str]:
        return {g: self.gate(g) for g in GATES}

    def runtime_verified(self) -> bool:
        if not self.runtime_verifications:
            return False
        return all(v.get("verified") is True for v in self.runtime_verifications)

    @property
    def is_synthetic(self) -> bool:
        return bool(self.integrity.get("synthetic", False))

    def outcome_signature(self) -> str:
        """Causal outcome, in the four-valued domain. NOT_TESTED and
        INCONCLUSIVE are explicitly NOT negative results -- collapsing them
        into 'no effect' would manufacture false contradictions."""
        g = self.gate("causal")
        if g == NOT_RUN:
            return OUTCOME_NOT_TESTED
        if g == PASS:
            return OUTCOME_EFFECT
        if g == FAIL:
            return OUTCOME_NO_OBSERVED_EFFECT
        return OUTCOME_INCONCLUSIVE

    def to_dict(self):
        d = asdict(self)
        d["_gate_completeness"] = self.gate_completeness()
        d["_outcome_signature"] = self.outcome_signature()
        return d
