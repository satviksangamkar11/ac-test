"""Producer diagnosis: identify goal, measure current state, select mutation."""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class MetricDirection(Enum):
    """Direction preference for a metric."""
    HIGHER_IS_BETTER = "higher"  # e.g., loudness, sustain duration
    LOWER_IS_BETTER = "lower"    # e.g., latency, distortion


@dataclass
class ProducerGoal:
    """A producer goal: what change is desired."""
    intent: str  # e.g., "make the note sustain longer"
    semantic_target: str  # e.g., "Env1.Release"
    measurement_metric: str  # e.g., "tail_rms_db"
    metric_direction: MetricDirection  # higher_is_better or lower_is_better

    def to_dict(self) -> dict:
        return {
            'intent': self.intent,
            'semantic_target': self.semantic_target,
            'measurement_metric': self.measurement_metric,
            'metric_direction': self.metric_direction.value,
        }


@dataclass
class CurrentState:
    """Current Serum state and measurement."""
    serum_readback: float  # Current parameter value
    measurement_value: float  # Current metric measurement
    audio_peak: float  # Peak of rendered baseline
    audio_valid: bool  # Signal validity gate passed

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Diagnosis:
    """Diagnosis: what should change and why."""
    goal: ProducerGoal
    current_state: CurrentState
    candidate_targets: List[str]  # All in-scope, qualified targets that could address goal
    selected_target: str  # The ONE target chosen for this mutation
    mutation_direction: int  # +1 for increase, -1 for decrease
    mutation_magnitude: float  # How much to change (absolute value)
    reason: str  # Why this target + direction was chosen
    confidence: float  # 0.0-1.0 confidence in this diagnosis

    def to_dict(self) -> dict:
        return {
            'goal': self.goal.to_dict(),
            'current_state': self.current_state.to_dict(),
            'candidate_targets': self.candidate_targets,
            'selected_target': self.selected_target,
            'mutation_direction': self.mutation_direction,
            'mutation_magnitude': self.mutation_magnitude,
            'reason': self.reason,
            'confidence': self.confidence,
        }


@dataclass
class ProducerDecision:
    """Decision: accept or reject the mutation."""
    accepted: bool
    reason: str
    baseline_measurement: float
    treatment_measurement: float
    delta: float  # treatment - baseline
    metric_direction: MetricDirection

    def improvement_observed(self) -> bool:
        """Check if treatment shows improvement according to metric direction."""
        if self.metric_direction == MetricDirection.HIGHER_IS_BETTER:
            return self.delta > 0
        else:  # LOWER_IS_BETTER
            return self.delta < 0

    def to_dict(self) -> dict:
        return {
            'accepted': self.accepted,
            'reason': self.reason,
            'baseline_measurement': self.baseline_measurement,
            'treatment_measurement': self.treatment_measurement,
            'delta': self.delta,
            'metric_direction': self.metric_direction.value,
        }


def diagnose_goal(
    goal: ProducerGoal,
    current_state: CurrentState,
    qualified_targets: Dict[str, dict],  # {target_name: contract}
) -> Optional[Diagnosis]:
    """
    Create a diagnosis for the goal.

    Args:
        goal: Producer goal
        current_state: Current Serum state
        qualified_targets: Available qualified capabilities

    Returns:
        Diagnosis if possible, None if goal cannot be addressed
    """
    # Find candidates: targets that match the goal + are qualified + in-scope
    #
    # qualified_targets is keyed by (capability_key, condition_signature_hash)
    # tuples (see ContractRegistry.get_contracts_dict()), not by semantic_target
    # strings ("Env1.Release"). goal.semantic_target IS a semantic_target
    # string. The two must be bridged through SEMANTIC_TARGETS.capability_key,
    # matching against contract.target (which is a capability_key), never by
    # substring/family matching (15.4.7 scope guard applies here too).
    from serum2.compiler.targets import SEMANTIC_TARGETS

    target_ref = SEMANTIC_TARGETS.get(goal.semantic_target)
    expected_capability_key = target_ref.capability_key if target_ref else None

    candidates = []
    for _key, contract in qualified_targets.items():
        if expected_capability_key is not None and contract.target == expected_capability_key:
            candidates.append(contract.target)

    if not candidates:
        return None

    # For first version: select the only candidate (or first if multiple)
    selected_target = candidates[0]

    # Infer mutation direction from goal and metric direction
    # "make sustain longer" + "tail_rms_db (higher is better)" → increase parameter
    # This assumes the parameter increases the measured value
    mutation_direction = 1 if goal.metric_direction == MetricDirection.HIGHER_IS_BETTER else -1

    # Select modest mutation magnitude (5-10% of parameter range)
    mutation_magnitude = 0.05

    diagnosis = Diagnosis(
        goal=goal,
        current_state=current_state,
        candidate_targets=candidates,
        selected_target=selected_target,
        mutation_direction=mutation_direction,
        mutation_magnitude=mutation_magnitude,
        reason=f"Selected {selected_target} to {goal.intent}",
        confidence=0.90,
    )

    return diagnosis
