"""Intent bridge: human intent → knowledge retrieval → candidate semantic operation

Smallest possible module connecting human intent to existing knowledge artifacts
and producing machine-readable candidate operations with full source provenance.
"""
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Any


@dataclass
class CandidateOperation:
    target: str
    operation: Optional[str]
    reason: str
    source_knowledge_item_id: str
    source_hypothesis_id: Optional[str]
    source_confidence: float
    measurement_plan: List[str]
    hypothesis_type: str  # PROCEDURAL or BEHAVIORAL


@dataclass
class IntentResolution:
    intent: str
    knowledge_source: str  # e.g., "yt_f507169bd7cb"
    matched_hypotheses: int
    candidate_operations: List[CandidateOperation]
    provenance_preserved: bool = True

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "knowledge_source": self.knowledge_source,
            "matched_hypotheses": self.matched_hypotheses,
            "candidate_operations": [asdict(op) for op in self.candidate_operations],
            "provenance_preserved": self.provenance_preserved,
        }


def resolve_intent_to_candidates(
    human_intent: str,
    hypotheses_file: str,
    target_resolution_file: str,
) -> IntentResolution:
    """
    Resolve human intent to candidate operations using existing knowledge.

    Returns candidate operations with full source provenance.
    No capability filtering at this stage; admission happens later.
    """
    # Load hypothesis and target resolution artifacts
    with open(hypotheses_file) as f:
        hypotheses_data = json.load(f)
    with open(target_resolution_file) as f:
        target_resolution_data = json.load(f)

    # Simple keyword-based matching against hypothesis targets and operations
    # (real implementation would use semantic similarity or intent parsing)
    intent_lower = human_intent.lower()
    candidates = []

    for hyp in hypotheses_data.get("hypotheses", []):
        target = hyp.get("target")
        operation = hyp.get("operation")
        hypothesis_id = hyp.get("hypothesis_id")
        knowledge_item_id = hyp.get("knowledge_item_id")
        measurement_plan = hyp.get("measurement_plan", [])
        hypothesis_type = hyp.get("hypothesis_type", "UNKNOWN")
        source_confidence = hyp.get("source_confidence", 0.0)

        # Match: intent mentions target OR operation
        target_match = target and target.lower() in intent_lower
        operation_match = operation and operation.lower() in intent_lower
        effect_match = "sustain" in intent_lower and target == "Env1.Release"
        release_match = "release" in intent_lower and target == "Env1.Release"

        if target_match or operation_match or effect_match or release_match:
            reason = f"User intent '{human_intent}' matches {target}"
            if operation:
                reason += f" operation '{operation}'"

            candidates.append(
                CandidateOperation(
                    target=target,
                    operation=operation,
                    reason=reason,
                    source_knowledge_item_id=knowledge_item_id,
                    source_hypothesis_id=hypothesis_id,
                    source_confidence=source_confidence,
                    measurement_plan=measurement_plan,
                    hypothesis_type=hypothesis_type,
                )
            )

    return IntentResolution(
        intent=human_intent,
        knowledge_source=hypotheses_data.get("source_id", "unknown"),
        matched_hypotheses=len(candidates),
        candidate_operations=candidates,
        provenance_preserved=True,
    )
