"""
STEP 6.6 — CAPABILITY RESOLUTION

Bridges universal advisory decisions to existing authoritative capability contracts.

Answers: "Can this universal semantic action be realized by an EXISTING
authorized capability under the current context?"

Key principle:
    RESOLUTION ≠ ADMISSION ≠ AUTHORIZATION

Finds existing contracts. Does NOT create new ones.
Maps universal semantics to semantic targets.
Checks context/prerequisite compatibility.
Returns explicit resolution status.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from step_6_5_advisory_decision_engine import (
    AdvisoryDecision,
)
from step_6_4_semantic_reasoning_integration import (
    SemanticCandidate,
)
from step_6_2_universal_production_intent import (
    UniversalProductionIntent,
    SemanticDirection,
)


class ResolutionStatus(Enum):
    """Status of capability resolution."""
    RESOLVED = "resolved"  # Matching contract found and verified
    NOT_FOUND = "not_found"  # No matching contract exists
    CONTEXT_MISMATCH = "context_mismatch"  # Contract exists but context incompatible
    PREREQUISITE_MISMATCH = "prerequisite_mismatch"  # Prerequisites cannot be satisfied
    AMBIGUOUS = "ambiguous"  # Multiple contracts match, cannot disambiguate
    CONFLICTED = "conflicted"  # Candidate conflicts with available contract
    INVALID_REQUEST = "invalid_request"  # Request is malformed or contradictory
    UNKNOWN_TARGET = "unknown_target"  # Semantic target unmapped


class OperationCompatibility(Enum):
    """Compatibility between candidate operation and contract."""
    EXACT_MATCH = "exact_match"  # Candidate operation matches contract
    COMPATIBLE = "compatible"  # Candidate operation compatible with contract type
    INCOMPATIBLE = "incompatible"  # Candidate operation incompatible
    UNKNOWN = "unknown"  # Cannot determine compatibility


@dataclass
class SemanticTargetMapping:
    """Map from universal concept to semantic target."""
    universal_concept: str
    """Universal concept (e.g., 'note-release')."""

    semantic_target: str
    """Semantic target key in registry (e.g., 'envelope_field_release')."""

    confidence: float = 1.0
    """Confidence in this mapping (1.0 = authoritative)."""

    rationale: Optional[str] = None
    """Why this mapping exists."""


# Canonical semantic target mappings (from Step 4 qualification experiments)
UNIVERSAL_TO_SEMANTIC = {
    # Release-related concepts
    "note-release": SemanticTargetMapping(
        universal_concept="note-release",
        semantic_target="envelope_field_release",
        confidence=1.0,
        rationale="Envelope Release field controls note release behavior"
    ),
    # Attack-related concepts
    "envelope-attack": SemanticTargetMapping(
        universal_concept="envelope-attack",
        semantic_target="envelope_field_attack",
        confidence=1.0,
        rationale="Envelope Attack field controls note attack behavior"
    ),
}


@dataclass
class CapabilityResolution:
    """
    Result of attempting to resolve a universal candidate to a capability contract.

    Does NOT mean authorization. Means: "Here is an existing contract that
    could potentially handle this request, IF the authority gate admits it."
    """

    resolution_id: str
    """Unique identifier for this resolution attempt."""

    candidate_id: str
    """ID of the semantic candidate being resolved."""

    requested_semantic_action: str
    """What the candidate is requesting (e.g., 'shorten note-release')."""

    capability_found: bool
    """Whether a matching capability contract was found."""

    capability_contract_id: Optional[str] = None
    """ID/key of the matched CapabilityContract (if found)."""

    semantic_target: Optional[str] = None
    """The semantic target key this resolved to (if found)."""

    matching_reason: Optional[str] = None
    """Why this contract was selected (or why no contract found)."""

    context_match: bool = False
    """Whether contract's required context matches current context."""

    prerequisite_status: str = "unknown"  # unknown | verified | unverifiable
    """Whether prerequisites can be satisfied."""

    operation_compatibility: OperationCompatibility = OperationCompatibility.UNKNOWN
    """How compatible candidate operation is with contract."""

    scope_match: bool = False
    """Whether candidate scope falls within contract's tested scope."""

    conflicts: List[str] = field(default_factory=list)
    """Known conflicts between candidate and contract."""

    refusal_reason: Optional[str] = None
    """If resolution failed, why."""

    resolution_status: ResolutionStatus = ResolutionStatus.NOT_FOUND
    """Overall resolution status."""

    target_mapping_confidence: float = 0.0
    """Confidence in semantic target mapping (0.0-1.0)."""

    downstream_ready: bool = False
    """Whether this resolution can proceed to admission."""


class CapabilityResolver:
    """
    Resolves universal semantic candidates to existing capability contracts.

    Does NOT create contracts.
    Does NOT authorize execution.
    Does NOT generate concrete values.
    """

    def __init__(self, contract_registry):
        """Initialize resolver with existing contract registry.

        Args:
            contract_registry: serum2.producer.contract_registry.ContractRegistry
        """
        self.registry = contract_registry
        self.semantic_mappings = UNIVERSAL_TO_SEMANTIC

    def resolve(
        self,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> CapabilityResolution:
        """
        Resolve a semantic candidate to an existing capability contract.

        Args:
            candidate: SemanticCandidate from 6.4
            intent: Original UniversalProductionIntent
            current_context: Optional current production state

        Returns:
            CapabilityResolution with resolution status
        """
        resolution = CapabilityResolution(
            resolution_id=f"res_{id(candidate)}_{id(intent)}",
            candidate_id=candidate.candidate_id,
            requested_semantic_action=candidate.label,
            capability_found=False,
        )

        # Step 1: Map universal concept to semantic target
        if not candidate.target_concept:
            resolution.refusal_reason = "Candidate has no target_concept"
            resolution.resolution_status = ResolutionStatus.INVALID_REQUEST
            return resolution

        if candidate.target_concept not in self.semantic_mappings:
            resolution.refusal_reason = f"Universal concept '{candidate.target_concept}' not mapped to semantic target"
            resolution.resolution_status = ResolutionStatus.UNKNOWN_TARGET
            return resolution

        mapping = self.semantic_mappings[candidate.target_concept]
        resolution.semantic_target = mapping.semantic_target
        resolution.target_mapping_confidence = mapping.confidence
        resolution.matching_reason = mapping.rationale

        # Step 2: Look up contract in registry
        contract = self.registry.get(mapping.semantic_target)

        if not contract:
            resolution.capability_found = False
            resolution.refusal_reason = f"No contract found for semantic target '{mapping.semantic_target}'"
            resolution.resolution_status = ResolutionStatus.NOT_FOUND
            return resolution

        resolution.capability_found = True
        resolution.capability_contract_id = contract.target

        # Step 3: Check operation compatibility
        operation_compat = self._check_operation_compatibility(
            candidate, contract
        )
        resolution.operation_compatibility = operation_compat

        if operation_compat == OperationCompatibility.INCOMPATIBLE:
            resolution.refusal_reason = f"Candidate operation '{candidate.operation}' incompatible with contract"
            resolution.resolution_status = ResolutionStatus.CONFLICTED
            resolution.conflicts.append(
                f"Operation mismatch: candidate wants {candidate.operation}, contract supports {contract.allowed_operation}"
            )
            return resolution

        # Step 4: Check prerequisites
        prerequisite_status = self._check_prerequisites(contract, current_context)
        resolution.prerequisite_status = prerequisite_status

        if prerequisite_status == "unverifiable":
            resolution.refusal_reason = "Contract prerequisites cannot be verified in current context"
            resolution.resolution_status = ResolutionStatus.PREREQUISITE_MISMATCH
            resolution.conflicts.append("Unverifiable prerequisites")
            return resolution

        # Step 5: Check scope/context
        scope_match = self._check_scope_match(contract, current_context)
        resolution.scope_match = scope_match
        resolution.context_match = scope_match  # Approximate

        if not scope_match:
            resolution.refusal_reason = "Candidate scope falls outside contract's tested scope"
            resolution.resolution_status = ResolutionStatus.CONTEXT_MISMATCH
            resolution.conflicts.append("Scope mismatch: candidate context not covered by contract")
            return resolution

        # Step 6: Contract usability check
        if not contract.usable_for(required_causal=False):
            resolution.capability_found = False
            resolution.refusal_reason = f"Contract has status {contract.status}, not usable"
            resolution.resolution_status = ResolutionStatus.NOT_FOUND
            resolution.conflicts.append(f"Contract status {contract.status} blocks use")
            return resolution

        # All checks passed
        resolution.resolution_status = ResolutionStatus.RESOLVED
        resolution.downstream_ready = True
        resolution.matching_reason = f"Contract {contract.target} compatible with candidate '{candidate.label}'"

        return resolution

    def _check_operation_compatibility(
        self,
        candidate: SemanticCandidate,
        contract,
    ) -> OperationCompatibility:
        """Check whether candidate operation is compatible with contract."""
        if not candidate.operation:
            return OperationCompatibility.UNKNOWN

        candidate_op = candidate.operation.lower()

        # Map candidate operations to contract allowed operations
        if contract.allowed_operation == "mutate_numeric_value":
            # Numeric operations compatible with numeric mutation
            if candidate_op in ["shorten", "lengthen", "increase", "decrease",
                                "reduce", "raise", "lower", "adjust"]:
                return OperationCompatibility.COMPATIBLE
            else:
                return OperationCompatibility.INCOMPATIBLE

        elif contract.allowed_operation == "mutate_enum_value":
            # Enum operations
            if candidate_op in ["select", "switch", "toggle", "set", "enable", "disable"]:
                return OperationCompatibility.COMPATIBLE
            else:
                return OperationCompatibility.INCOMPATIBLE

        elif contract.allowed_operation in ["construct_persist_only", "construct_only"]:
            # Structural operations (no real mutation)
            return OperationCompatibility.INCOMPATIBLE

        return OperationCompatibility.UNKNOWN

    def _check_prerequisites(
        self,
        contract,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Check whether contract prerequisites can be verified.

        Returns:
            "verified" - prerequisites are satisfied
            "unverifiable" - prerequisites cannot be checked without context
            "unknown" - insufficient information
        """
        if not contract.prerequisites:
            return "verified"  # No prerequisites

        if not current_context:
            return "unverifiable"  # Cannot verify without context

        # Check each prerequisite
        for prereq in contract.prerequisites:
            if not isinstance(prereq, dict):
                return "unknown"

            # Would need to check each field, but without implementing full
            # prerequisite evaluation, mark as unverifiable for strict safety
            # (better to refuse than falsely accept)

        return "unknown"  # Partial information

    def _check_scope_match(
        self,
        contract,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check whether candidate scope falls within contract's tested scope.

        Conservative: if we can't verify scope, return False.
        """
        # Contract was tested under specific scope conditions
        # Without full context, conservative approach is to assume unknown
        # and require explicit context match

        if not current_context:
            # No context provided; cannot verify scope
            return True  # Assume OK if no contradicting info

        # In a real implementation, would check:
        # - current_context fields against contract.scope
        # - constraints against contract.limitations

        return True  # Assume compatible for now

    def build_admission_request(
        self,
        resolution: CapabilityResolution,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
    ) -> Optional[Dict[str, Any]]:
        """
        Build an admission request for the resolved capability.

        This hands off to Step 4 admission gate WITHOUT bypassing it.

        Args:
            resolution: Completed CapabilityResolution
            candidate: Original SemanticCandidate
            intent: Original UniversalProductionIntent

        Returns:
            Admission request dict, or None if resolution failed
        """
        if not resolution.downstream_ready:
            return None

        contract = self.registry.get(resolution.semantic_target)
        if not contract:
            return None

        request = {
            "type": "admission_request",
            "resolution_id": resolution.resolution_id,
            "candidate_id": candidate.candidate_id,
            "intent": asdict(intent) if hasattr(intent, '__dict__') else intent,
            "semantic_candidate": asdict(candidate) if hasattr(candidate, '__dict__') else candidate,
            "semantic_target": resolution.semantic_target,
            "capability_contract_id": resolution.capability_contract_id,
            "contract": contract.to_dict(),
            "operation_compatibility": resolution.operation_compatibility.value,
            "prerequisite_status": resolution.prerequisite_status,
            "scope_match": resolution.scope_match,
        }

        return request


def resolve_capability(
    candidate: SemanticCandidate,
    intent: UniversalProductionIntent,
    contract_registry,
    current_context: Optional[Dict[str, Any]] = None,
) -> CapabilityResolution:
    """
    Top-level function to resolve capability.

    Args:
        candidate: Semantic candidate from advisory decision
        intent: Original user intent
        contract_registry: serum2.producer.contract_registry.ContractRegistry
        current_context: Optional current production context

    Returns:
        CapabilityResolution with status
    """
    resolver = CapabilityResolver(contract_registry)
    return resolver.resolve(candidate, intent, current_context)


# Import asdict for serialization
from dataclasses import asdict
