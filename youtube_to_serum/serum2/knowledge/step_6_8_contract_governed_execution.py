"""
STEP 6.8 — CONTRACT-GOVERNED EXECUTION INTEGRATION

Bridges Step 6 reasoning (advisory) to Step 4 canonical execution.

Key invariant:
    AFTER ADMISSION, EXECUTION SERVES THE CAPABILITY CONTRACT.

This layer DOES NOT implement execution.
It ONLY integrates Step 6 advisory with EXISTING canonical paths.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

from step_6_7_admission_handoff import (
    AdmissionHandoffResult,
)
from step_6_6_capability_resolution import (
    CapabilityResolution,
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


class ExecutionPathway(Enum):
    """Execution pathway classification."""
    ADMITTED = "admitted"  # AdmissionResult.admitted == True
    REFUSED = "refused"  # AdmissionResult.admitted == False
    ERROR = "error"  # Something went wrong


@dataclass
class ExecutionAuthority:
    """
    Authority for execution.

    Derived ONLY from admitted CapabilityContract.
    Not from knowledge, episodes, intent, or proposals.
    """

    contract_id: str
    """Admitted contract identifier."""

    allowed_operation: str
    """MUTATE_NUMERIC, MUTATE_ENUM, etc. from contract."""

    target: str
    """Semantic target from contract."""

    prerequisites: Dict[str, Any]
    """Prerequisites from contract (already verified by admission)."""

    measurement_definition_id: Optional[str] = None
    """Measurement kernel from contract."""

    scope: Optional[Dict[str, Any]] = None
    """Tested scope from contract."""

    limitations: list = field(default_factory=list)
    """Limitations from contract."""


@dataclass
class ExecutionIntentionRecord:
    """
    Complete execution intention.

    Captures BOTH the reasoning chain AND the authority chain.
    """

    # Reasoning chain (advisory influence)
    original_intent: UniversalProductionIntent
    """User's original request."""

    advisory_decision: AdvisoryDecision
    """The advisory recommendation (NOT authoritative)."""

    capability_resolution: CapabilityResolution
    """Resolution to a capable contract (NOT authoritative)."""

    # Authority chain (execution authority)
    admission_result: AdmissionHandoffResult
    """Actual admission decision (AUTHORITATIVE)."""

    execution_authority: Optional[ExecutionAuthority] = None
    """Authority derived from admitted contract."""

    # Execution state
    pathway: ExecutionPathway = ExecutionPathway.ERROR
    """Which pathway: admitted/refused/error."""

    execution_trace_id: str = ""
    """ID for this execution intention."""

    notes: Optional[str] = None
    """Additional context."""

    def is_authorized(self) -> bool:
        """Check if this intention is authorized to execute."""
        return (
            self.admission_result and
            self.admission_result.admitted and
            self.execution_authority is not None
        )


class ContractGovernedExecutor:
    """
    Integrates Step 6 advisory with Step 4 canonical execution.

    Does NOT implement execution.
    Only creates execution authorities from admitted contracts.
    """

    def build_execution_authority(
        self,
        admission_result: AdmissionHandoffResult,
        contract_registry,
    ) -> Optional[ExecutionAuthority]:
        """
        Build execution authority from admitted contract.

        Args:
            admission_result: Result from Step 7 admission
            contract_registry: To fetch the contract

        Returns:
            ExecutionAuthority if admitted, None otherwise
        """
        if not admission_result.admitted:
            return None

        if not admission_result.contract_id:
            return None

        # Get the actual contract
        contract = contract_registry.get(admission_result.contract_id)
        if not contract:
            return None

        # Build authority from contract ONLY
        # prerequisites may be a list of dicts or a dict; normalize to dict
        prereq_dict = {}
        if contract.prerequisites:
            if isinstance(contract.prerequisites, dict):
                prereq_dict = contract.prerequisites
            elif isinstance(contract.prerequisites, (list, tuple)):
                # Each item is likely a dict with field_path key
                for p in contract.prerequisites:
                    if isinstance(p, dict) and "field_path" in p:
                        prereq_dict[p["field_path"]] = p

        authority = ExecutionAuthority(
            contract_id=admission_result.contract_id,
            allowed_operation=contract.allowed_operation,
            target=contract.target,
            prerequisites=prereq_dict,
            measurement_definition_id=admission_result.measurement_definition_id,
            scope=contract.scope if hasattr(contract, 'scope') else None,
            limitations=list(contract.limitations) if hasattr(contract, 'limitations') else [],
        )

        return authority

    def create_execution_intention(
        self,
        intent: UniversalProductionIntent,
        advisory_decision: AdvisoryDecision,
        capability_resolution: CapabilityResolution,
        admission_result: AdmissionHandoffResult,
        contract_registry,
    ) -> ExecutionIntentionRecord:
        """
        Create complete execution intention.

        Args:
            intent: Original user intent
            advisory_decision: Step 5 advisory decision
            capability_resolution: Step 6 capability resolution
            admission_result: Step 7 admission result
            contract_registry: For contract lookup

        Returns:
            ExecutionIntentionRecord with full trace
        """
        # Determine pathway
        if not admission_result.admitted:
            pathway = ExecutionPathway.REFUSED
            authority = None
        else:
            authority = self.build_execution_authority(
                admission_result,
                contract_registry
            )
            pathway = ExecutionPathway.ADMITTED if authority else ExecutionPathway.ERROR

        # Build record
        record = ExecutionIntentionRecord(
            original_intent=intent,
            advisory_decision=advisory_decision,
            capability_resolution=capability_resolution,
            admission_result=admission_result,
            execution_authority=authority,
            pathway=pathway,
            execution_trace_id=f"exec_{id(admission_result)}",
        )

        return record

    def validate_authority(
        self,
        record: ExecutionIntentionRecord,
    ) -> bool:
        """
        Validate that authority is properly established.

        Key checks:
        - Admission actually granted
        - Contract exists
        - No advisory override attempted
        - Authority comes ONLY from contract

        Args:
            record: Execution intention

        Returns:
            True if valid and authorized, False otherwise
        """
        # Must be admitted
        if not record.admission_result.admitted:
            return False

        # Must have extracted authority
        if not record.execution_authority:
            return False

        # Authority must come from admitted contract ID
        if (record.execution_authority.contract_id !=
            record.admission_result.contract_id):
            return False

        # Resolve must have been successful
        if (record.capability_resolution.resolution_status.value != "resolved"):
            return False

        return True


def create_execution_intention(
    intent: UniversalProductionIntent,
    advisory_decision: AdvisoryDecision,
    capability_resolution: CapabilityResolution,
    admission_result: AdmissionHandoffResult,
    contract_registry,
) -> ExecutionIntentionRecord:
    """
    Top-level function to create execution intention.

    Args:
        intent: User intent
        advisory_decision: Advisory recommendation
        capability_resolution: Capability resolution
        admission_result: Admission decision (AUTHORITATIVE)
        contract_registry: For contract lookup

    Returns:
        ExecutionIntentionRecord with full authority trace
    """
    executor = ContractGovernedExecutor()
    return executor.create_execution_intention(
        intent,
        advisory_decision,
        capability_resolution,
        admission_result,
        contract_registry,
    )
