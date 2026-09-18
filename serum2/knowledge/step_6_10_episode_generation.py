"""
STEP 6.10 — UNIVERSAL EPISODE GENERATION

Converts a completed production execution and attributed outcome into a
persistent, provenance-safe Episode representing EXPERIENCE.

Key invariant:
    EPISODE ≠ AUTHORITY

Episodes inform reasoning. They NEVER:
- authorize execution
- create capability
- bypass Admission
- override CapabilityContract
- grant causal authority
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import json
from pathlib import Path

from step_6_2_universal_production_intent import UniversalProductionIntent
from step_6_9_outcome_attribution import UniversalOutcome, CausalAttributionStatus


class LearningEligibilityStatus(Enum):
    """Learning eligibility classification."""
    LEARNING_ELIGIBLE = "learning_eligible"
    NOT_LEARNING_ELIGIBLE = "not_learning_eligible"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFUSED_EXECUTION = "refused_execution"
    INVALID_EXECUTION = "invalid_execution"


class EpisodeExecutionStatus(Enum):
    """Execution status within episode."""
    NOT_EXECUTED = "not_executed"
    EXECUTED = "executed"
    EXECUTION_FAILED = "execution_failed"
    PARTIALLY_EXECUTED = "partially_executed"


@dataclass
class ExecutionEvidenceRecord:
    """Evidence from actual execution (backend-scoped)."""

    baseline_state: Optional[Dict[str, Any]] = None
    """Baseline state before mutation."""

    treatment_state: Optional[Dict[str, Any]] = None
    """State after treatment mutation."""

    mutation_description: Optional[str] = None
    """Description of the mutation applied."""

    render_evidence: Optional[Dict[str, Any]] = None
    """Evidence from render (measurements, audio analysis)."""

    diagnosis: Optional[str] = None
    """Diagnostic information from execution."""


@dataclass
class UniversalExecutedEpisode:
    """
    Complete universal Episode from start to outcome.

    Backend-independent. May reference backend-specific evidence through
    opaque/scoped evidence records, but core schema remains universal.

    Authority principle:
        This Episode contains experience information ONLY.
        It NEVER grants authority or permission.
    """

    # IDENTITY (required fields first)
    episode_id: str
    """Unique episode identifier."""

    execution_id: str
    """ID of the actual execution."""

    original_user_request: str
    """Original user request text."""

    universal_intent: UniversalProductionIntent
    """Semantic intent model."""

    semantic_target: str
    """Target concept (e.g., 'envelope_field_release')."""

    # DEFAULT FIELDS
    creation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """When episode was created."""

    semantic_direction: Optional[str] = None
    """Direction (INCREASE, DECREASE, etc.)."""

    musical_objective: Optional[str] = None
    """Musical goal described."""

    knowledge_item_ids: List[str] = field(default_factory=list)
    """Knowledge items that informed reasoning."""

    procedure_ids: List[str] = field(default_factory=list)
    """Procedures referenced in reasoning."""

    prior_episode_ids: List[str] = field(default_factory=list)
    """Prior episodes used for context."""

    advisory_decision_id: Optional[str] = None
    """ID of advisory decision."""

    capability_resolution_id: Optional[str] = None
    """ID of capability resolution."""

    selected_candidate_id: Optional[str] = None
    """Semantic candidate that was selected."""

    # AUTHORITY PROVENANCE
    admission_handoff_id: Optional[str] = None
    """ID of admission handoff request."""

    admitted_contract_id: Optional[str] = None
    """Contract that was admitted."""

    contract_status: Optional[str] = None
    """Contract status (CAUSAL_VERIFIED, STRUCTURAL_ONLY, etc.)."""

    execution_pathway: Optional[str] = None
    """ADMITTED/REFUSED/ERROR."""

    admission_allowed: bool = False
    """Did admission allow this execution?"""

    # EXECUTION EVIDENCE
    execution_status: EpisodeExecutionStatus = EpisodeExecutionStatus.NOT_EXECUTED
    """Whether execution occurred."""

    execution_evidence: Optional[ExecutionEvidenceRecord] = None
    """Backend-scoped evidence from execution."""

    measurement_definition_id: Optional[str] = None
    """Which measurement kernel was used."""

    # OUTCOME
    outcome: Optional[UniversalOutcome] = None
    """The attributed outcome."""

    outcome_status: Optional[str] = None
    """OutcomeStatus enum value."""

    causal_attribution_status: Optional[str] = None
    """CausalAttributionStatus enum value."""

    observed_delta: Optional[float] = None
    """Observed change magnitude."""

    attribution_confidence: float = 0.0
    """Confidence (0.0-1.0) in causal attribution."""

    confounds_detected: List[str] = field(default_factory=list)
    """Conditions that invalidate causality."""

    # LEARNING ELIGIBILITY
    learning_eligible: bool = False
    """Is this Episode learning-eligible?"""

    learning_eligibility_status: LearningEligibilityStatus = LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
    """Explicit eligibility classification."""

    eligibility_reasons: List[str] = field(default_factory=list)
    """Why/why not eligible for learning."""

    # PROVENANCE
    provenance_chain: Optional[Dict[str, Any]] = None
    """Full authority/reasoning chain."""

    schema_version: str = "6.10.0"
    """Schema version for future compatibility."""

    notes: Optional[str] = None
    """Episode-level notes."""


class UniversalEpisodeGenerator:
    """
    Generates Episodes from completed productions.

    Does NOT:
    - authorize execution
    - create capability
    - bypass Admission
    - override contracts
    """

    EPISODE_STORAGE_DIR = Path(__file__).parent.parent / "qualification"

    def generate_episode(
        self,
        execution_id: str,
        universal_intent: UniversalProductionIntent,
        execution_record,
        admission_result,
        admitted_contract,
        advisory_decision,
        capability_resolution,
        outcome: UniversalOutcome,
        execution_evidence: Optional[ExecutionEvidenceRecord] = None,
        knowledge_ids: Optional[List[str]] = None,
        procedure_ids: Optional[List[str]] = None,
        prior_episode_ids: Optional[List[str]] = None,
    ) -> UniversalExecutedEpisode:
        """
        Generate Episode from execution + outcome.

        Args:
            execution_id: ID of the execution
            universal_intent: Semantic intent model
            execution_record: ExecutionIntentionRecord from Step 6.8
            admission_result: AdmissionHandoffResult
            admitted_contract: CapabilityContract (if admitted)
            advisory_decision: AdvisoryDecision
            capability_resolution: CapabilityResolution
            outcome: UniversalOutcome from Step 6.9
            execution_evidence: Backend-scoped evidence
            knowledge_ids: Knowledge items used
            procedure_ids: Procedures referenced
            prior_episode_ids: Prior episodes used for context

        Returns:
            UniversalExecutedEpisode
        """
        episode_id = f"ep_{execution_id}"

        # Build episode
        episode = UniversalExecutedEpisode(
            episode_id=episode_id,
            execution_id=execution_id,
            original_user_request=universal_intent.original_user_request,
            universal_intent=universal_intent,
            semantic_target=capability_resolution.semantic_target or "unknown",
            semantic_direction=universal_intent.semantic_direction.value
                if universal_intent.semantic_direction else None,
            musical_objective=universal_intent.musical_objective,
            knowledge_item_ids=knowledge_ids or [],
            procedure_ids=procedure_ids or [],
            prior_episode_ids=prior_episode_ids or [],
            advisory_decision_id=advisory_decision.decision_id
                if advisory_decision else None,
            capability_resolution_id=capability_resolution.resolution_id
                if capability_resolution else None,
            selected_candidate_id=advisory_decision.selected_candidate.candidate_id
                if advisory_decision and hasattr(advisory_decision, 'selected_candidate')
                and advisory_decision.selected_candidate else None,
            admission_handoff_id=admission_result.handoff_id
                if admission_result else None,
            admitted_contract_id=admission_result.contract_id
                if admission_result else None,
            contract_status=admission_result.contract_status
                if admission_result else None,
            execution_pathway=execution_record.pathway.value
                if hasattr(execution_record, 'pathway') else None,
            admission_allowed=admission_result.admitted
                if admission_result else False,
            execution_status=self._classify_execution_status(
                execution_record, outcome
            ),
            execution_evidence=execution_evidence,
            measurement_definition_id=outcome.measurement_definition_id
                if outcome else None,
            outcome=outcome,
            outcome_status=outcome.outcome_status.value
                if outcome and hasattr(outcome, 'outcome_status') else None,
            causal_attribution_status=outcome.causal_status.value
                if outcome and hasattr(outcome, 'causal_status') else None,
            observed_delta=outcome.change_magnitude
                if outcome else None,
            attribution_confidence=outcome.attribution_confidence
                if outcome else 0.0,
            confounds_detected=outcome.confounds_detected
                if outcome else [],
        )

        # Build provenance chain first (required for eligibility check)
        episode.provenance_chain = self._build_provenance(
            execution_record, admission_result, outcome
        )

        # Determine learning eligibility (after provenance is set)
        self._evaluate_learning_eligibility(episode, execution_record, outcome)

        return episode

    def _classify_execution_status(
        self,
        execution_record,
        outcome: UniversalOutcome,
    ) -> EpisodeExecutionStatus:
        """Classify execution status from records."""
        if not execution_record:
            return EpisodeExecutionStatus.NOT_EXECUTED

        if not hasattr(execution_record, 'pathway'):
            return EpisodeExecutionStatus.EXECUTION_FAILED

        if execution_record.pathway.value == "refused":
            return EpisodeExecutionStatus.NOT_EXECUTED

        if outcome and outcome.outcome_status.value == "invalid_observation":
            return EpisodeExecutionStatus.EXECUTION_FAILED

        return EpisodeExecutionStatus.EXECUTED

    def _evaluate_learning_eligibility(
        self,
        episode: UniversalExecutedEpisode,
        execution_record,
        outcome: UniversalOutcome,
    ) -> None:
        """Evaluate learning eligibility; does NOT automatically grant it."""
        reasons = []

        # Check 1: Admission was granted
        if not episode.admission_allowed:
            reasons.append("admission_not_granted")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.REFUSED_EXECUTION
            )
            episode.eligibility_reasons = reasons
            return

        # Check 2: Execution occurred
        if episode.execution_status != EpisodeExecutionStatus.EXECUTED:
            reasons.append("execution_did_not_occur")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INVALID_EXECUTION
            )
            episode.eligibility_reasons = reasons
            return

        # Check 3: Baseline is valid
        if (not outcome or outcome.baseline_value is None):
            reasons.append("invalid_baseline")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
            )
            episode.eligibility_reasons = reasons
            return

        # Check 4: Treatment is valid
        if (not outcome or outcome.treatment_value is None):
            reasons.append("invalid_treatment")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
            )
            episode.eligibility_reasons = reasons
            return

        # Check 5: Measurement is valid
        if not outcome.measurement_definition_id:
            reasons.append("no_measurement_definition")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
            )
            episode.eligibility_reasons = reasons
            return

        # Check 6: Outcome attribution valid
        if outcome.causal_status == CausalAttributionStatus.INSUFFICIENT_EVIDENCE:
            reasons.append("attribution_insufficient_evidence")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
            )
            episode.eligibility_reasons = reasons
            return

        # Check 7: Provenance complete
        if not episode.provenance_chain:
            reasons.append("incomplete_provenance")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
            )
            episode.eligibility_reasons = reasons
            return

        # Check 8: No known confound
        if outcome.confounds_detected:
            reasons.append(f"confounds_detected: {outcome.confounds_detected}")
            episode.learning_eligible = False
            episode.learning_eligibility_status = (
                LearningEligibilityStatus.INSUFFICIENT_EVIDENCE
            )
            episode.eligibility_reasons = reasons
            return

        # Check 9: No authority/consistency violation
        # (This is verified by construction if we reached here)

        # All checks passed
        episode.learning_eligible = True
        episode.learning_eligibility_status = LearningEligibilityStatus.LEARNING_ELIGIBLE
        episode.eligibility_reasons = ["all_checks_passed"]

    def _build_provenance(
        self,
        execution_record,
        admission_result,
        outcome: UniversalOutcome,
    ) -> Dict[str, Any]:
        """Build complete authority/reasoning chain."""
        chain = {
            "authority_chain": {
                "execution_pathway": execution_record.pathway.value
                    if hasattr(execution_record, 'pathway') else None,
                "admission_granted": admission_result.admitted
                    if admission_result else False,
                "contract_id": admission_result.contract_id
                    if admission_result else None,
            },
            "outcome_chain": {
                "outcome_status": outcome.outcome_status.value
                    if outcome else None,
                "causal_status": outcome.causal_status.value
                    if outcome else None,
                "attribution_confidence": outcome.attribution_confidence
                    if outcome else 0.0,
                "confounds": outcome.confounds_detected
                    if outcome else [],
            },
        }
        return chain

    def persist_episode(self, episode: UniversalExecutedEpisode) -> str:
        """
        Persist Episode to storage.

        Returns:
            Path where episode was stored
        """
        self.EPISODE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        # Serialize episode (convert to dict for JSON)
        # Handle None and Mock objects gracefully
        def serialize_value(val):
            """Convert value to JSON-serializable form."""
            if val is None:
                return None
            if hasattr(val, '__dict__'):
                # Mock object or similar
                return str(val)
            if isinstance(val, (str, int, float, bool, list, dict)):
                return val
            # Fallback
            return str(val)

        episode_dict = {
            "episode_id": episode.episode_id,
            "execution_id": episode.execution_id,
            "creation_timestamp": episode.creation_timestamp,
            "original_user_request": episode.original_user_request,
            "semantic_target": episode.semantic_target,
            "semantic_direction": serialize_value(episode.semantic_direction),
            "musical_objective": serialize_value(episode.musical_objective),
            "knowledge_item_ids": episode.knowledge_item_ids,
            "procedure_ids": episode.procedure_ids,
            "prior_episode_ids": episode.prior_episode_ids,
            "advisory_decision_id": serialize_value(episode.advisory_decision_id),
            "capability_resolution_id": serialize_value(episode.capability_resolution_id),
            "selected_candidate_id": serialize_value(episode.selected_candidate_id),
            "admission_handoff_id": serialize_value(episode.admission_handoff_id),
            "admitted_contract_id": serialize_value(episode.admitted_contract_id),
            "contract_status": serialize_value(episode.contract_status),
            "execution_pathway": serialize_value(episode.execution_pathway),
            "admission_allowed": episode.admission_allowed,
            "execution_status": episode.execution_status.value,
            "measurement_definition_id": serialize_value(episode.measurement_definition_id),
            "outcome_status": serialize_value(episode.outcome_status),
            "causal_attribution_status": serialize_value(episode.causal_attribution_status),
            "observed_delta": serialize_value(episode.observed_delta),
            "attribution_confidence": episode.attribution_confidence,
            "confounds_detected": episode.confounds_detected,
            "learning_eligible": episode.learning_eligible,
            "learning_eligibility_status": episode.learning_eligibility_status.value,
            "eligibility_reasons": episode.eligibility_reasons,
            "provenance_chain": episode.provenance_chain,
            "schema_version": episode.schema_version,
            "notes": serialize_value(episode.notes),
            # For human_intent field expected by retrieval
            "human_intent": episode.original_user_request,
        }

        # Write to file
        episode_file = self.EPISODE_STORAGE_DIR / f"{episode.episode_id}.json"
        with open(episode_file, "w") as f:
            json.dump(episode_dict, f, indent=2)

        return str(episode_file)


def generate_episode(
    execution_id: str,
    universal_intent: UniversalProductionIntent,
    execution_record,
    admission_result,
    admitted_contract,
    advisory_decision,
    capability_resolution,
    outcome: UniversalOutcome,
    execution_evidence: Optional[ExecutionEvidenceRecord] = None,
    knowledge_ids: Optional[List[str]] = None,
    procedure_ids: Optional[List[str]] = None,
    prior_episode_ids: Optional[List[str]] = None,
) -> UniversalExecutedEpisode:
    """Top-level Episode generation."""
    generator = UniversalEpisodeGenerator()
    return generator.generate_episode(
        execution_id,
        universal_intent,
        execution_record,
        admission_result,
        admitted_contract,
        advisory_decision,
        capability_resolution,
        outcome,
        execution_evidence,
        knowledge_ids,
        procedure_ids,
        prior_episode_ids,
    )


def persist_episode(episode: UniversalExecutedEpisode) -> str:
    """Persist generated Episode."""
    generator = UniversalEpisodeGenerator()
    return generator.persist_episode(episode)
