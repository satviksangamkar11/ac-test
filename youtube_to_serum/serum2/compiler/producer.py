"""16.5.13: Producer reasoning layer.

Sits above the compiler (produce_goal) and below musical intent.
Adds the reasoning loop that compile-only produce_goal() lacks:

  hypothesis formation → action selection → prediction → execution →
  measurement evaluation → goal verdict → adaptation signal

The four grounding conditions for a prediction:

  1. CAUSAL_VERIFIED control (contract.status)
  2. Same metric used in causal experiment AND EFFECT_OBSERVED
  3. Observed direction matches predicted direction
  4. Claim coverage generalizes beyond INSTANCE
     (derived_coverage_scope() != INSTANCE AND derived_breadth() != SINGLE_INSTANCE)
     -- requires ClaimGroup to be passed to form_prediction()

All four → GROUNDED.
Three (1-3), ClaimGroup not provided or coverage==INSTANCE → PARTIALLY_GROUNDED.
One or two (1-2 only) → HYPOTHESIS.
None → UNGROUNDED.

Execution policy by epistemic status:
  GROUNDED           → NORMAL_EXECUTION
  PARTIALLY_GROUNDED → EXPLORATORY_EXECUTION (allowed, labeled, NOT evidence-admissible)
  HYPOTHESIS         → EXPLORATORY_EXECUTION (allowed, labeled, NOT evidence-admissible)
  UNGROUNDED         → EXECUTION_REFUSED

Critical invariant: an exploratory execution result (GoalVerdict.is_admissible_as_evidence
== False) cannot strengthen a capability claim. That requires the normal evidence
admission path with required isolation, measurement provenance, and ClaimEngine ingestion.
The producer's measurement is informative to the producer loop only.

GoalVerdict separates prediction evaluation from goal evaluation:
  prediction_status: SUPPORTED | CONTRADICTED | INCONCLUSIVE | UNTESTED
  goal_status:       ACHIEVED  | INSUFFICIENT | NOT_VERIFIED  | REFUSED

These are independent. A direction-correct but magnitude-weak result is:
  prediction_status = SUPPORTED
  goal_status       = INSUFFICIENT
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..evidence.capability_contract import CAUSAL_VERIFIED
from ..evidence.claim import (
    ClaimGroup, INSTANCE, SINGLE_INSTANCE,
    SAMPLED, EXHAUSTIVE_BREADTH,
    query_claim_coverage,
)
from .result import produce_goal, GoalField, GoalResult

# ---- epistemic status ----
GROUNDED           = "GROUNDED"
PARTIALLY_GROUNDED = "PARTIALLY_GROUNDED"
HYPOTHESIS         = "HYPOTHESIS"
UNGROUNDED         = "UNGROUNDED"

# ---- execution policy ----
NORMAL_EXECUTION           = "NORMAL_EXECUTION"
EXPLORATORY_EXECUTION      = "EXPLORATORY_EXECUTION"
CAPABILITY_DISCOVERY_NEEDED = "CAPABILITY_DISCOVERY_NEEDED"
EXECUTION_REFUSED          = "EXECUTION_REFUSED"

# HYPOTHESIS → CAPABILITY_DISCOVERY_NEEDED, not exploratory execution.
# HYPOTHESIS means "general synthesis knowledge, not Serum-evidence-backed."
# Executing it inside the producer loop would make the producer a hidden
# research instrument. Instead it produces a DiscoveryRequest naming what
# evidence is missing, which the knowledge loop can turn into an ExperimentSpec.
EXECUTION_POLICY = {
    GROUNDED:           NORMAL_EXECUTION,
    PARTIALLY_GROUNDED: EXPLORATORY_EXECUTION,
    HYPOTHESIS:         CAPABILITY_DISCOVERY_NEEDED,
    UNGROUNDED:         EXECUTION_REFUSED,
}

# ---- goal verdict ---- (declared before GoalVerdict for reference)
GOAL_ACHIEVED              = "ACHIEVED"
GOAL_INSUFFICIENT          = "INSUFFICIENT"
GOAL_NOT_VERIFIED          = "NOT_VERIFIED"
GOAL_REFUSED               = "REFUSED"
GOAL_CAPABILITY_DISCOVERY  = "CAPABILITY_DISCOVERY_NEEDED"

# ---- prediction evaluation ----
PREDICTION_SUPPORTED    = "SUPPORTED"
PREDICTION_CONTRADICTED = "CONTRADICTED"
PREDICTION_INCONCLUSIVE = "INCONCLUSIVE"
PREDICTION_UNTESTED     = "UNTESTED"



@dataclass(frozen=True)
class DiscoveryRequest:
    """Structured description of what evidence is missing to ground a prediction.

    Produced when HYPOTHESIS or UNGROUNDED predictions are refused execution.
    Contains enough information for the knowledge loop to construct an ExperimentSpec
    without re-deriving what was missing.

    This is not an ExperimentSpec itself — it is a request TO the knowledge loop.
    The knowledge loop (evidence path) remains responsible for isolation, condition,
    measurement definition, admission, and ClaimEngine ingestion.
    """
    goal: str                          # the producer goal that was refused
    candidate_control: str             # semantic name the producer considered
    required_effect: str               # what effect is needed, e.g. "brightness decreases"
    required_measurement: str          # metric that would verify the effect
    missing_capability_reason: str     # why the current evidence doesn't support it


@dataclass(frozen=True)
class PredictionBasis:
    """Epistemic provenance for one predicted effect.

    Points back into the existing evidence system; never copies claim content.
    capability_key links to CapabilityContract; measurement_definition_id links
    to the specific measurement kernel used in the causal experiment.

    claim_coverage_scope and claim_breadth are derived from ClaimGroup when
    provided to form_prediction(); None when ClaimGroup was unavailable.
    """
    capability_key: str
    causal_status: str
    metric: str
    metric_sensitivity: str          # EFFECT_OBSERVED | NO_OBSERVED_EFFECT | UNKNOWN
    predicted_direction: str
    epistemic_status: str            # GROUNDED | PARTIALLY_GROUNDED | HYPOTHESIS | UNGROUNDED
    grounding_detail: str
    measurement_definition_id: Optional[str] = None
    claim_coverage_scope: Optional[str] = None   # from ClaimGroup.derived_coverage_scope()
    claim_breadth: Optional[str] = None           # from ClaimGroup.derived_breadth()


@dataclass(frozen=True)
class ProducerAttempt:
    """One producer reasoning step: hypothesis → action → prediction → verification plan.

    Contains an explicit prediction with provenance. The execution_policy is
    derived from prediction_basis.epistemic_status via EXECUTION_POLICY; the
    caller does not choose it.

    goal_threshold_db is a producer-policy parameter: it expresses the minimum
    magnitude change the producer considers meaningful for this goal. It is the
    caller's responsibility to set a justified value; producer.py imposes no default.
    """
    goal_description: str
    selected_control: str            # semantic name, e.g. "OSC1.Volume"
    requested_value: Any             # value to set
    current_value: Optional[Any]     # value in the current patch body (informational)
    predicted_effect: str            # human-readable, e.g. "overall_rms_db decreases"
    prediction_basis: PredictionBasis
    verification_metric: str
    verification_direction: str      # "decrease" | "increase" | "change"
    goal_threshold_db: float         # producer-policy: minimum magnitude for ACHIEVED

    @property
    def execution_policy(self) -> str:
        return EXECUTION_POLICY.get(
            self.prediction_basis.epistemic_status, EXECUTION_REFUSED)

    @property
    def is_executable(self) -> bool:
        return self.execution_policy in (NORMAL_EXECUTION, EXPLORATORY_EXECUTION)

    @property
    def needs_discovery(self) -> bool:
        return self.execution_policy == CAPABILITY_DISCOVERY_NEEDED


@dataclass(frozen=True)
class GoalVerdict:
    """Outcome of one producer attempt.

    prediction_status and goal_status are independent:
      prediction_status=SUPPORTED, goal_status=INSUFFICIENT means the direction
        was confirmed but the magnitude was below the producer's threshold.
      prediction_status=INCONCLUSIVE, goal_status=NOT_VERIFIED means the metric
        could not resolve the change (not the same as contradiction).

    is_admissible_as_evidence: always False for EXPLORATORY_EXECUTION results.
    An exploratory measurement informs the producer loop but does not strengthen
    the underlying capability claim. That requires the normal evidence admission
    path with required isolation, measurement provenance, and ClaimEngine ingestion.
    """
    goal_description: str
    attempt: "ProducerAttempt"
    goal_status: str
    prediction_status: str
    measurement: Optional[Dict[str, Any]]
    detail: str
    goal_result: Optional[GoalResult]
    is_admissible_as_evidence: bool        # True only for NORMAL_EXECUTION + GROUNDED
    discovery_request: Optional[DiscoveryRequest] = None  # set when CAPABILITY_DISCOVERY_NEEDED

    def succeeded(self) -> bool:
        return self.goal_status == GOAL_ACHIEVED


def form_prediction(
    contract,
    requested_metric: str,
    predicted_direction: str,
    record_store: Optional[Dict[str, Any]] = None,
) -> PredictionBasis:
    """Check the evidence system to determine the epistemic status of a prediction.

    Applies the four-condition grounding predicate. Conditions 1-3 are read from
    the CapabilityContract. Condition 4 requires a ClaimGroup to be passed --
    without it, the best achievable status for an otherwise-qualifying prediction
    is PARTIALLY_GROUNDED (coverage could not be verified from the contract alone).

    The ClaimGroup machinery (derived_coverage_scope, derived_breadth) is
    authoritative for condition 4. This function does not re-implement that logic.

    Condition 4 uses query_claim_coverage() from claim.py — the authoritative
    coverage machinery — with an optional record_store containing the supporting
    EvidenceRecords. Without record_store, condition 4 cannot be evaluated and
    PARTIALLY_GROUNDED is the best achievable status.

    This is the single canonical gateway for prediction grounding. No other code
    in the producer layer may implement this check independently.
    """
    capability_key = getattr(contract, "target", "unknown")

    # ---- condition 1: control causally verified? ----
    if contract.status != CAUSAL_VERIFIED:
        return PredictionBasis(
            capability_key=capability_key,
            causal_status=contract.status,
            metric=requested_metric,
            metric_sensitivity="UNKNOWN",
            predicted_direction=predicted_direction,
            epistemic_status=UNGROUNDED,
            grounding_detail=(
                "control has no CAUSAL_VERIFIED evidence (status=%r); "
                "no expected effect can be claimed" % contract.status
            ),
        )

    # ---- condition 2: metric link verified? ----
    measurement = getattr(contract, "measurement", None) or {}
    contract_metric = measurement.get("metric")
    metric_sensitivity = measurement.get("status", "UNKNOWN")
    mdef_id = measurement.get("measurement_definition_id")

    if contract_metric != requested_metric or metric_sensitivity != "EFFECT_OBSERVED":
        return PredictionBasis(
            capability_key=capability_key,
            causal_status=contract.status,
            metric=requested_metric,
            metric_sensitivity=(
                metric_sensitivity if contract_metric == requested_metric else "NOT_USED"),
            predicted_direction=predicted_direction,
            epistemic_status=HYPOTHESIS,
            grounding_detail=(
                "control is CAUSAL_VERIFIED but %r was not the measurement metric "
                "(contract used %r, sensitivity=%r); this prediction is general "
                "synthesis knowledge, not evidence-backed for this synthesizer" % (
                    requested_metric, contract_metric, metric_sensitivity)
            ),
            measurement_definition_id=None,
        )

    # ---- condition 3: observed direction matches? ----
    observed_direction = measurement.get("observed_direction")
    if observed_direction != predicted_direction:
        return PredictionBasis(
            capability_key=capability_key,
            causal_status=contract.status,
            metric=requested_metric,
            metric_sensitivity=metric_sensitivity,
            predicted_direction=predicted_direction,
            epistemic_status=HYPOTHESIS,
            grounding_detail=(
                "metric %r was EFFECT_OBSERVED but direction was %r, not %r; "
                "predicted direction is not supported by existing evidence" % (
                    requested_metric, observed_direction, predicted_direction)
            ),
            measurement_definition_id=mdef_id,
        )

    # ---- condition 4: coverage generalizes beyond INSTANCE? ----
    # Delegates entirely to query_claim_coverage() in claim.py.
    # Without record_store, condition 4 cannot be evaluated.
    coverage_scope = None
    breadth = None

    if record_store is not None:
        cov = query_claim_coverage(contract, record_store)
        coverage_scope = cov.get("coverage_scope")
        breadth = cov.get("breadth")
        if cov.get("generalizes"):
            return PredictionBasis(
                capability_key=capability_key,
                causal_status=contract.status,
                metric=requested_metric,
                metric_sensitivity=metric_sensitivity,
                predicted_direction=predicted_direction,
                epistemic_status=GROUNDED,
                grounding_detail=(
                    "all four grounding conditions met: CAUSAL_VERIFIED, "
                    "metric %r EFFECT_OBSERVED direction=%r, %s" % (
                        requested_metric, predicted_direction, cov.get("detail", ""))
                ),
                measurement_definition_id=mdef_id,
                claim_coverage_scope=coverage_scope,
                claim_breadth=breadth,
            )
        detail = (
            "conditions 1-3 met but coverage does not generalize: %s" %
            cov.get("detail", "coverage_scope=%r breadth=%r" % (coverage_scope, breadth))
        )
    else:
        detail = (
            "conditions 1-3 met; condition 4 (coverage generalization) could not be "
            "evaluated -- no record_store provided to form_prediction(); "
            "PARTIALLY_GROUNDED is the best achievable status without it"
        )

    return PredictionBasis(
        capability_key=capability_key,
        causal_status=contract.status,
        metric=requested_metric,
        metric_sensitivity=metric_sensitivity,
        predicted_direction=predicted_direction,
        epistemic_status=PARTIALLY_GROUNDED,
        grounding_detail=detail,
        measurement_definition_id=mdef_id,
        claim_coverage_scope=coverage_scope,
        claim_breadth=breadth,
    )


def _evaluate_prediction(
    measurement: Optional[Dict[str, Any]],
    predicted_direction: str,
    causal_status_from_record: str,
) -> str:
    """Evaluate whether the measurement supports the predicted direction.

    Uses causal_status (EFFECT_OBSERVED | NO_OBSERVED_EFFECT) from the
    EvidenceRecord, not the producer threshold, to assess direction.
    Separated from goal evaluation deliberately: direction and magnitude
    are different questions.
    """
    if measurement is None:
        return PREDICTION_UNTESTED

    if causal_status_from_record == "NO_OBSERVED_EFFECT":
        return PREDICTION_INCONCLUSIVE

    delta = measurement.get("delta")
    if delta is None:
        return PREDICTION_INCONCLUSIVE

    if predicted_direction == "decrease" and delta < 0:
        return PREDICTION_SUPPORTED
    if predicted_direction == "increase" and delta > 0:
        return PREDICTION_SUPPORTED
    if predicted_direction == "change" and delta != 0:
        return PREDICTION_SUPPORTED
    return PREDICTION_CONTRADICTED


def execute_producer_goal(
    attempt: ProducerAttempt,
    contracts,
    structural_records,
    body: Dict[str, Any],
    *,
    experiment_id: str,
    baseline_overrides=None,
    discovery_request: Optional[DiscoveryRequest] = None,
) -> GoalVerdict:
    """Execute one ProducerAttempt and return a GoalVerdict.

    HYPOTHESIS → CAPABILITY_DISCOVERY_NEEDED: returns immediately with the
    supplied discovery_request (caller must construct it from what form_prediction
    reported is missing). Does not touch Serum.

    UNGROUNDED → EXECUTION_REFUSED: returns immediately.

    NORMAL / EXPLORATORY: runs produce_goal(), evaluates prediction and goal
    independently. is_admissible_as_evidence is True only for GROUNDED + NORMAL.

    The caller supplies discovery_request when the prediction is HYPOTHESIS so
    the verdict carries a structured description of what evidence is missing.
    """
    # HYPOTHESIS: capability discovery required — do not execute
    if attempt.needs_discovery:
        return GoalVerdict(
            goal_description=attempt.goal_description,
            attempt=attempt,
            goal_status=GOAL_CAPABILITY_DISCOVERY,
            prediction_status=PREDICTION_UNTESTED,
            measurement=None,
            detail=(
                "CAPABILITY_DISCOVERY_NEEDED: prediction is %r — "
                "general synthesis knowledge is not sufficient to execute this "
                "goal honestly; Serum-specific evidence must be established first. "
                "grounding_detail: %s" % (
                    attempt.prediction_basis.epistemic_status,
                    attempt.prediction_basis.grounding_detail)
            ),
            goal_result=None,
            is_admissible_as_evidence=False,
            discovery_request=discovery_request,
        )

    # UNGROUNDED: hard refusal
    if not attempt.is_executable:
        return GoalVerdict(
            goal_description=attempt.goal_description,
            attempt=attempt,
            goal_status=GOAL_REFUSED,
            prediction_status=PREDICTION_UNTESTED,
            measurement=None,
            detail=(
                "execution refused: epistemic_status=%r does not permit "
                "execution (policy=%r)" % (
                    attempt.prediction_basis.epistemic_status,
                    attempt.execution_policy)
            ),
            goal_result=None,
            is_admissible_as_evidence=False,
            discovery_request=None,
        )

    goal_result = produce_goal(
        [GoalField(name=attempt.selected_control, requested_value=attempt.requested_value)],
        contracts, structural_records, body,
        experiment_id=experiment_id,
        baseline_overrides=baseline_overrides,
        measure_overall_rms=True,
    )

    if not goal_result.overall_accepted or goal_result.refusal_reason:
        return GoalVerdict(
            goal_description=attempt.goal_description,
            attempt=attempt,
            goal_status=GOAL_REFUSED,
            prediction_status=PREDICTION_UNTESTED,
            measurement=goal_result.measurement,
            detail="produce_goal refused: %s -- %s" % (
                goal_result.refusal_reason, goal_result.refusal_detail),
            goal_result=goal_result,
            is_admissible_as_evidence=False,
            discovery_request=None,
        )

    prediction_status = _evaluate_prediction(
        goal_result.measurement,
        attempt.verification_direction,
        goal_result.causal_status,
    )

    measurement = goal_result.measurement
    delta = measurement.get("delta") if measurement else None

    if prediction_status in (PREDICTION_UNTESTED, PREDICTION_INCONCLUSIVE, PREDICTION_CONTRADICTED):
        goal_status = GOAL_NOT_VERIFIED
        if prediction_status == PREDICTION_INCONCLUSIVE:
            detail = (
                "metric %r showed NO_OBSERVED_EFFECT -- the predicted %s "
                "direction could not be confirmed; INCONCLUSIVE, not contradicted" % (
                    attempt.verification_metric, attempt.verification_direction)
            )
        elif prediction_status == PREDICTION_CONTRADICTED:
            detail = (
                "metric %r moved in the WRONG direction (delta=%.4f, predicted=%s); "
                "prediction CONTRADICTED" % (
                    attempt.verification_metric,
                    delta if delta is not None else 0.0,
                    attempt.verification_direction)
            )
        else:
            detail = "no measurement was taken"
    else:  # SUPPORTED
        magnitude = abs(delta) if delta is not None else 0.0
        if magnitude >= attempt.goal_threshold_db:
            goal_status = GOAL_ACHIEVED
            detail = (
                "goal %r achieved: %r moved %s by %.4f dB "
                "(threshold=%.1f dB, policy=%s, epistemic=%s)" % (
                    attempt.goal_description,
                    attempt.verification_metric,
                    attempt.verification_direction,
                    magnitude,
                    attempt.goal_threshold_db,
                    attempt.execution_policy,
                    attempt.prediction_basis.epistemic_status)
            )
        else:
            goal_status = GOAL_INSUFFICIENT
            detail = (
                "direction confirmed (%s, delta=%.4f dB) but magnitude below "
                "producer threshold %.1f dB -- goal not achieved at required level" % (
                    attempt.verification_direction,
                    magnitude,
                    attempt.goal_threshold_db)
            )

    # Admissibility: only GROUNDED + NORMAL_EXECUTION results are admissible
    # as evidence for the capability claim. Exploratory results inform the
    # producer loop and nothing else.
    is_admissible = (
        attempt.execution_policy == NORMAL_EXECUTION
        and attempt.prediction_basis.epistemic_status == GROUNDED
    )

    return GoalVerdict(
        goal_description=attempt.goal_description,
        attempt=attempt,
        goal_status=goal_status,
        prediction_status=prediction_status,
        measurement=measurement,
        detail=detail,
        goal_result=goal_result,
        is_admissible_as_evidence=is_admissible,
        discovery_request=None,
    )
