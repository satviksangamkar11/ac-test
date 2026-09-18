"""
STEP 6.9 — UNIVERSAL OUTCOME ATTRIBUTION

Determines what actually happened after contract-governed execution.
Attributes outcomes to admitted contracts WITHOUT redefining authority.

Key invariant:
    MEASURED IMPROVEMENT ≠ CAUSAL PROOF

Attribution must verify authority chain remains intact.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class OutcomeStatus(Enum):
    """Status of the observed outcome."""
    EXPECTED_IMPROVEMENT = "expected_improvement"
    EXPECTED_REGRESSION = "expected_regression"
    UNEXPECTED_CHANGE = "unexpected_change"
    NO_MEANINGFUL_CHANGE = "no_meaningful_change"
    INVALID_OBSERVATION = "invalid_observation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNKNOWN = "unknown"


class CausalAttributionStatus(Enum):
    """Confidence in causal attribution."""
    ATTRIBUTED_TO_TREATMENT = "attributed_to_treatment"
    CONSISTENT_WITH_TREATMENT = "consistent_with_treatment"
    NOT_ATTRIBUTABLE = "not_attributable"
    CONFOUNDED = "confounded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNKNOWN = "unknown"


@dataclass
class UniversalOutcome:
    """
    Universal outcome representation.

    Backend-independent. Contains NO Serum parameter names.
    Authority: contract remains supreme.
    """

    # Execution context
    execution_id: str
    """ID of the actual execution."""

    contract_id: str
    """Admitted contract that governed execution."""

    intent_id: str
    """Original user intent."""

    # Measurements
    baseline_value: Optional[float] = None
    """Measured value before mutation."""

    treatment_value: Optional[float] = None
    """Measured value after mutation."""

    measurement_definition_id: Optional[str] = None
    """Which measurement kernel was used."""

    change_magnitude: Optional[float] = None
    """Difference: treatment - baseline."""

    change_direction: Optional[str] = None
    """Observed direction: increase/decrease/no_change."""

    expected_direction: Optional[str] = None
    """Contract-expected direction (if any)."""

    # Attribution
    outcome_status: OutcomeStatus = OutcomeStatus.UNKNOWN
    """What kind of outcome was observed."""

    causal_status: CausalAttributionStatus = CausalAttributionStatus.UNKNOWN
    """Confidence in causal attribution."""

    attribution_confidence: float = 0.0
    """Confidence (0.0-1.0) that treatment caused outcome."""

    # Safety signals
    confounds_detected: list = field(default_factory=list)
    """Conditions that invalidate causal attribution."""

    validity_checks_passed: list = field(default_factory=list)
    """Checks that DID pass."""

    validity_checks_failed: list = field(default_factory=list)
    """Checks that FAILED."""

    # Provenance
    provenance: Optional[Dict[str, Any]] = None
    """Authority chain: contract → admission → execution."""

    reasoning: Optional[str] = None
    """How this attribution was determined."""

    def is_causally_attributable(self) -> bool:
        """Check if outcome is causally attributable."""
        return self.causal_status == CausalAttributionStatus.ATTRIBUTED_TO_TREATMENT


class UniversalOutcomeAttributor:
    """
    Attributes outcomes to contract-governed executions.

    Does NOT create authority.
    Only interprets measurements within contract constraints.
    """

    def attribute_outcome(
        self,
        execution_id: str,
        contract_id: str,
        intent_id: str,
        baseline_measurement: Optional[Dict[str, Any]],
        treatment_measurement: Optional[Dict[str, Any]],
        admitted_contract,
    ) -> UniversalOutcome:
        """
        Attribute an outcome to an execution.

        Args:
            execution_id: ID of execution
            contract_id: Admitted contract ID
            intent_id: Original intent ID
            baseline_measurement: Baseline measurement result
            treatment_measurement: Treatment measurement result
            admitted_contract: The actual CapabilityContract

        Returns:
            UniversalOutcome with causal attribution status
        """
        outcome = UniversalOutcome(
            execution_id=execution_id,
            contract_id=contract_id,
            intent_id=intent_id,
        )

        # Step 1: Validity checks
        checks_passed = []
        checks_failed = []

        if baseline_measurement is None:
            checks_failed.append("no_baseline_measurement")
        else:
            checks_passed.append("baseline_exists")

        if treatment_measurement is None:
            checks_failed.append("no_treatment_measurement")
        else:
            checks_passed.append("treatment_exists")

        if admitted_contract is None:
            checks_failed.append("no_admitted_contract")
        else:
            checks_passed.append("contract_admitted")

        outcome.validity_checks_passed = checks_passed
        outcome.validity_checks_failed = checks_failed

        # If fundamental evidence is missing, stop here
        if checks_failed:
            outcome.outcome_status = OutcomeStatus.INVALID_OBSERVATION
            outcome.causal_status = CausalAttributionStatus.INSUFFICIENT_EVIDENCE
            outcome.reasoning = f"Cannot attribute: {', '.join(checks_failed)}"
            return outcome

        # Step 2: Measurement consistency check
        baseline_mid = baseline_measurement.get("measurement_definition_id")
        treatment_mid = treatment_measurement.get("measurement_definition_id")

        if baseline_mid != treatment_mid:
            outcome.outcome_status = OutcomeStatus.INVALID_OBSERVATION
            outcome.causal_status = CausalAttributionStatus.NOT_ATTRIBUTABLE
            outcome.confounds_detected.append(
                f"measurement_mismatch: {baseline_mid} vs {treatment_mid}"
            )
            outcome.reasoning = "Measurement kernels differ; cannot compare"
            return outcome

        outcome.measurement_definition_id = baseline_mid

        # Step 3: Extract measurements
        baseline_value = baseline_measurement.get("value")
        treatment_value = treatment_measurement.get("value")

        if baseline_value is None or treatment_value is None:
            outcome.outcome_status = OutcomeStatus.INVALID_OBSERVATION
            outcome.causal_status = CausalAttributionStatus.INSUFFICIENT_EVIDENCE
            outcome.reasoning = "Missing measurement values"
            return outcome

        outcome.baseline_value = baseline_value
        outcome.treatment_value = treatment_value

        # Step 4: Calculate change
        change = treatment_value - baseline_value
        outcome.change_magnitude = change

        if change > 0:
            outcome.change_direction = "increase"
        elif change < 0:
            outcome.change_direction = "decrease"
        else:
            outcome.change_direction = "no_change"

        # Step 5: Determine outcome status
        if outcome.change_direction == "no_change":
            outcome.outcome_status = OutcomeStatus.NO_MEANINGFUL_CHANGE
            outcome.causal_status = CausalAttributionStatus.CONSISTENT_WITH_TREATMENT
            outcome.attribution_confidence = 0.0
            outcome.reasoning = "No meaningful change observed"
            return outcome

        # Try to get expected direction from contract
        expected_direction = None
        if hasattr(admitted_contract, 'scope') and admitted_contract.scope:
            # Contract may indicate expected direction
            # This is advisory; NOT authoritative for causality
            expected_direction = admitted_contract.scope.get("expected_direction")

        outcome.expected_direction = expected_direction

        # Step 6: Compare observed to expected
        if expected_direction:
            if outcome.change_direction == expected_direction:
                outcome.outcome_status = OutcomeStatus.EXPECTED_IMPROVEMENT
            else:
                outcome.outcome_status = OutcomeStatus.UNEXPECTED_CHANGE
                outcome.confounds_detected.append(
                    f"direction_mismatch: expected {expected_direction}, got {outcome.change_direction}"
                )
        else:
            # No expectation; just record observation
            outcome.outcome_status = OutcomeStatus.UNEXPECTED_CHANGE

        # Step 7: Causal attribution
        # CRITICAL: measured improvement alone does NOT prove causality
        if outcome.confounds_detected:
            outcome.causal_status = CausalAttributionStatus.CONFOUNDED
            outcome.attribution_confidence = 0.0
            outcome.reasoning = f"Confounds detected: {', '.join(outcome.confounds_detected)}"
        elif (
            outcome.outcome_status == OutcomeStatus.EXPECTED_IMPROVEMENT
            and outcome.change_magnitude != 0
        ):
            # Consistent with expected direction; sufficient authority chain
            outcome.causal_status = CausalAttributionStatus.ATTRIBUTED_TO_TREATMENT
            outcome.attribution_confidence = 0.7  # Conservative; not 1.0
            outcome.reasoning = "Treatment consistent with observed improvement; attributed to admitted contract"
        else:
            outcome.causal_status = CausalAttributionStatus.CONSISTENT_WITH_TREATMENT
            outcome.attribution_confidence = 0.3
            outcome.reasoning = "Observation consistent with treatment, but causality not strongly established"

        # Store provenance
        outcome.provenance = {
            "contract_id": contract_id,
            "execution_id": execution_id,
            "intent_id": intent_id,
            "measurement_definition_id": outcome.measurement_definition_id,
            "validity_checks": {
                "passed": outcome.validity_checks_passed,
                "failed": outcome.validity_checks_failed,
            },
        }

        return outcome


def attribute_outcome(
    execution_id: str,
    contract_id: str,
    intent_id: str,
    baseline_measurement: Optional[Dict[str, Any]],
    treatment_measurement: Optional[Dict[str, Any]],
    admitted_contract,
) -> UniversalOutcome:
    """Top-level outcome attribution."""
    attributor = UniversalOutcomeAttributor()
    return attributor.attribute_outcome(
        execution_id,
        contract_id,
        intent_id,
        baseline_measurement,
        treatment_measurement,
        admitted_contract,
    )
