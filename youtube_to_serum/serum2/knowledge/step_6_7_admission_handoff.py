"""
STEP 6.7 — ADMISSION HANDOFF

Hands resolved advisory capabilities to the EXISTING Step 4 admission gate.

Key principle:
    RESOLUTION ≠ ADMISSION

This layer reuses the frozen Step 4 admission implementation.
No new authority mechanisms are created.
Knowledge and episodes do NOT influence admission.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from enum import Enum

from step_6_6_capability_resolution import (
    CapabilityResolution,
    ResolutionStatus,
)
from step_6_5_advisory_decision_engine import (
    AdvisoryDecision,
)
from step_6_4_semantic_reasoning_integration import (
    SemanticCandidate,
)
from step_6_2_universal_production_intent import (
    UniversalProductionIntent,
)


@dataclass
class AdmissionHandoffRequest:
    """
    Request prepared for Step 4 admission gate.

    Contains all information needed for admission to verify,
    but NOTHING that bypasses the gate.
    """

    handoff_id: str
    """Unique identifier for this handoff."""

    resolution_id: str
    """ID of the CapabilityResolution that led here."""

    candidate_id: str
    """ID of the semantic candidate."""

    intent: UniversalProductionIntent
    """Original user intent (for traceability)."""

    semantic_candidate: SemanticCandidate
    """The proposed action (for traceability)."""

    semantic_target: str
    """The semantic target (e.g., 'envelope_field_release')."""

    target_for_admission: str
    """The exact target to pass to admission.admit()."""

    proposed_prerequisites_verified: Dict[str, bool] = field(default_factory=dict)
    """Which prerequisites are verified in current context."""

    required_causal: bool = False
    """Does this request require causal verification?"""

    required_persistence: bool = False
    """Does this request require persistence verification?"""

    required_measurement_definition_id: Optional[str] = None
    """Expected measurement kernel ID."""

    context_state: Optional[Dict[str, Any]] = None
    """Current production context (for prerequisite verification)."""

    notes: Optional[str] = None
    """Additional context for admission."""


@dataclass
class AdmissionHandoffResult:
    """
    Result of admission handoff.

    Contains the actual admission decision from Step 4.
    """

    handoff_id: str
    """Corresponding handoff ID."""

    admitted: bool
    """Did admission allow this?"""

    admission_reason: str
    """ADMITTED or REFUSED_* from step 4 admission module."""

    admission_detail: str
    """Full explanation from admission gate."""

    contract_id: Optional[str] = None
    """Contract used (if any)."""

    contract_status: Optional[str] = None
    """Status of contract (CAUSAL_VERIFIED, STRUCTURAL_ONLY, etc)."""

    contract_allowed_operation: Optional[str] = None
    """What operation does contract allow?"""

    measurement_definition_id: Optional[str] = None
    """Measurement kernel ID (if any)."""

    resolution_id: str = ""
    """Traceability to original resolution."""

    candidate_id: str = ""
    """Traceability to semantic candidate."""


class AdmissionHandoff:
    """
    Hands resolved capabilities to the existing Step 4 admission gate.

    Reuses: serum2.evidence.admission.admit()
    Does NOT create new authority.
    Does NOT modify existing contracts.
    """

    def __init__(self, admission_module, contract_registry):
        """
        Initialize handoff.

        Args:
            admission_module: serum2.evidence.admission
            contract_registry: serum2.producer.contract_registry.ContractRegistry
        """
        self.admission = admission_module
        self.registry = contract_registry

    def prepare_request(
        self,
        resolution: CapabilityResolution,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AdmissionHandoffRequest]:
        """
        Prepare an admission request from capability resolution.

        Args:
            resolution: CapabilityResolution from step 6.6
            candidate: Semantic candidate
            intent: Original user intent
            current_context: Current production state

        Returns:
            AdmissionHandoffRequest if resolution allows, None otherwise
        """
        # Only RESOLVED capabilities reach admission
        if resolution.resolution_status != ResolutionStatus.RESOLVED:
            return None

        if not resolution.capability_found or not resolution.capability_contract_id:
            return None

        # Get contract to determine requirements
        contract = self.registry.get(resolution.semantic_target)
        if not contract:
            return None

        # Prepare prerequisites verification
        proposed_prerequisites_verified = {}
        if contract.prerequisites:
            for prereq in contract.prerequisites:
                field_path = prereq.get("field_path")
                if field_path:
                    # Conservative: mark as verified only if we have explicit confirmation
                    proposed_prerequisites_verified[field_path] = False

        # Build request
        request = AdmissionHandoffRequest(
            handoff_id=f"adm_{id(resolution)}",
            resolution_id=resolution.resolution_id,
            candidate_id=resolution.candidate_id,
            intent=intent,
            semantic_candidate=candidate,
            semantic_target=resolution.semantic_target,
            target_for_admission=resolution.capability_contract_id,
            proposed_prerequisites_verified=proposed_prerequisites_verified,
            required_causal=False,  # Default; can be overridden by caller
            required_persistence=False,
            required_measurement_definition_id=contract.measurement.get("measurement_definition_id")
            if contract.measurement else None,
            context_state=current_context,
            notes=f"From advisory decision {resolution.resolution_id}",
        )

        return request

    def submit_to_admission(
        self,
        request: AdmissionHandoffRequest,
    ) -> AdmissionHandoffResult:
        """
        Submit request to the existing Step 4 admission gate.

        Args:
            request: AdmissionHandoffRequest prepared for admission

        Returns:
            AdmissionHandoffResult with actual admission decision
        """
        # Get contracts in format expected by admission.admit()
        contracts_dict = self.registry.get_contracts_dict()

        # Call the frozen Step 4 admission gate
        admission_result = self.admission.admit(
            contracts=contracts_dict,
            target=request.target_for_admission,
            required_causal=request.required_causal,
            required_persistence=request.required_persistence,
            proposed_prerequisites_verified=request.proposed_prerequisites_verified,
            required_measurement_definition_id=request.required_measurement_definition_id,
        )

        # Package result
        contract = None
        if admission_result.contract:
            contract = admission_result.contract

        handoff_result = AdmissionHandoffResult(
            handoff_id=request.handoff_id,
            admitted=admission_result.admitted,
            admission_reason=admission_result.reason,
            admission_detail=admission_result.detail,
            contract_id=contract.target if contract else None,
            contract_status=contract.status if contract else None,
            contract_allowed_operation=contract.allowed_operation if contract else None,
            measurement_definition_id=contract.measurement.get("measurement_definition_id")
            if contract and contract.measurement else None,
            resolution_id=request.resolution_id,
            candidate_id=request.candidate_id,
        )

        return handoff_result

    def handle(
        self,
        resolution: CapabilityResolution,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AdmissionHandoffResult]:
        """
        Handle complete admission handoff.

        Args:
            resolution: CapabilityResolution from 6.6
            candidate: Semantic candidate
            intent: User intent
            current_context: Current production state

        Returns:
            AdmissionHandoffResult, or None if resolution not admissible
        """
        # Prepare request
        request = self.prepare_request(resolution, candidate, intent, current_context)
        if not request:
            return None

        # Submit to admission
        return self.submit_to_admission(request)


def handle_admission_handoff(
    resolution: CapabilityResolution,
    candidate: SemanticCandidate,
    intent: UniversalProductionIntent,
    admission_module,
    contract_registry,
    current_context: Optional[Dict[str, Any]] = None,
) -> Optional[AdmissionHandoffResult]:
    """
    Top-level function for admission handoff.

    Args:
        resolution: Resolved capability from 6.6
        candidate: Semantic candidate
        intent: User intent
        admission_module: serum2.evidence.admission
        contract_registry: serum2.producer.contract_registry.ContractRegistry
        current_context: Current production state

    Returns:
        AdmissionHandoffResult, or None if not admissible
    """
    handoff = AdmissionHandoff(admission_module, contract_registry)
    return handoff.handle(resolution, candidate, intent, current_context)
