"""B1.5: Candidate Intent Formation (UNIFIED OUTPUT).

Combines concept representation + operation + context into a single
UniversalProductionIntent ready for Capability Resolution and Admission.
This is the final B1 output before entering the frozen execution pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from serum2.producer.concept_representation import ConceptRepresentation
from serum2.producer.operation_spec import OperationSpec
from serum2.producer.request_context import RequestContext


@dataclass
class UniversalProductionIntent:
    """Unified intent representation ready for Capability Resolution.

    B1 produces one of these for every valid user request.
    This is the interface between the Brain (reasoning) and the frozen pipeline
    (Capability Resolution → Admission → Execution).

    All fields are derived from frozen data layers; no hidden state.
    Everything is auditable via the derivation traces.
    """

    # Core intent
    canonical_target: str                              # e.g., "env1.decay"

    # Reasoning artifacts (preserved for audit)
    representation: ConceptRepresentation              # concept derivation result
    operation: OperationSpec                           # operation interpretation result
    context: RequestContext                            # request context extraction result

    # Confidence and audit
    overall_confidence: float = 0.5                    # 0.0–1.0; combined confidence
    derivation_trace: List[str] = field(default_factory=list)  # complete audit trail

    # Original request (for provenance)
    input_request: Any = None                          # ProducerRequest or user input

    # Post-generation fields (filled by Capability Resolution)
    capability_key: Optional[str] = None               # if matched to a contract
    admission_status: Optional[str] = None             # set by Admission gate

    def __post_init__(self):
        """Validate that intent is coherent."""
        if self.overall_confidence < 0.0 or self.overall_confidence > 1.0:
            raise ValueError(f"Confidence must be 0.0–1.0, got {self.overall_confidence}")
        if not self.canonical_target:
            raise ValueError("canonical_target is required")
        if not self.representation or not self.operation or not self.context:
            raise ValueError("representation, operation, and context are all required")

    def is_derivable(self) -> bool:
        """Is this intent derivable and usable?"""
        return self.representation.is_derivable()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/persistence."""
        return {
            "canonical_target": self.canonical_target,
            "overall_confidence": self.overall_confidence,
            "representation": self.representation.to_dict(),
            "operation": self.operation.to_dict(),
            "context": {
                "explicit_target": self.context.explicit_target,
                "implicit_scope": self.context.implicit_scope,
                "implicit_scope_type": self.context.implicit_scope_type,
                "audio_descriptors": self.context.audio_descriptors,
                "time_marker": self.context.time_marker,
            },
            "derivation_trace": self.derivation_trace,
        }


class IntentFormationEngine:
    """B1.5: Combine representation, operation, and context into unified intent.

    This is the final assembly step before the frozen Capability Resolution gate.
    All three components are independent and freely combinable.
    """

    def __init__(self):
        pass

    def form_intent(
        self,
        canonical_target: str,
        representation: ConceptRepresentation,
        operation: OperationSpec,
        context: RequestContext,
        input_request: Any = None,
    ) -> UniversalProductionIntent:
        """Form a unified intent from all components.

        Args:
            canonical_target: the resolved control ID
            representation: concept derivation result
            operation: operation interpretation result
            context: request context extraction result
            input_request: original ProducerRequest (for provenance)

        Returns:
            UniversalProductionIntent ready for Capability Resolution
        """

        trace = []
        trace.append(f"intent_formation(target={canonical_target})")

        # Validate components match the target
        if representation.canonical_target != canonical_target:
            trace.append(f"MISMATCH: representation.target={representation.canonical_target}, expected={canonical_target}")

        trace.extend(representation.derivation_chain)
        trace.extend(operation.interpretation_chain)
        trace.extend(context.extraction_chain)

        # Compute overall confidence as weighted average
        rep_conf = representation.confidence
        op_conf = operation.certainty
        ctx_conf = sum(context.confidence.values()) / len(context.confidence) if context.confidence else 0.5

        # Weight: representation (40%) + operation (40%) + context (20%)
        overall = (rep_conf * 0.4) + (op_conf * 0.4) + (ctx_conf * 0.2)

        trace.append(f"confidence: rep={rep_conf:.2f} + op={op_conf:.2f} + ctx={ctx_conf:.2f} = {overall:.2f}")

        intent = UniversalProductionIntent(
            canonical_target=canonical_target,
            representation=representation,
            operation=operation,
            context=context,
            overall_confidence=overall,
            derivation_trace=trace,
            input_request=input_request,
        )

        return intent


class IntentValidator:
    """Validate that an intent is ready for Capability Resolution.

    Checks that all required fields are present and coherent.
    """

    def validate(self, intent: UniversalProductionIntent) -> tuple[bool, List[str]]:
        """Validate intent readiness.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        if not intent.canonical_target:
            issues.append("canonical_target is empty")

        if not intent.representation.is_derivable():
            issues.append("representation is not derivable (MISSING provenance)")

        if intent.operation.operation.value == "unknown":
            issues.append("operation could not be interpreted")

        if intent.overall_confidence < 0.3:
            issues.append(f"overall confidence too low ({intent.overall_confidence:.2f} < 0.3)")

        # Cross-checks
        if intent.context.explicit_target and intent.context.explicit_target != intent.canonical_target:
            # Not necessarily an error; explicit target might be an alias
            pass

        return len(issues) == 0, issues
