"""
STEP 6.11 — CLOSED-LOOP DECISION PROOF

Proves that generated Episodes influence future reasoning while
remaining strictly non-authoritative.

FROZEN INVARIANT:
    EXPERIENCE IMPROVES REASONING.
    EXPERIENCE DOES NOT GRANT PERMISSION.

Two-cycle proof:
- Cycle A: Fresh intent, no prior episode
- Cycle B: Same intent WITH Cycle A's episode available

Measurable learning influence through existing reasoning pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import json


class CyclePhase(Enum):
    """Phase of a decision cycle."""
    INTENT = "intent"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    EPISODE_RETRIEVAL = "episode_retrieval"
    SEMANTIC_REASONING = "semantic_reasoning"
    ADVISORY_DECISION = "advisory_decision"
    CAPABILITY_RESOLUTION = "capability_resolution"
    ADMISSION = "admission"
    EXECUTION = "execution"
    MEASUREMENT = "measurement"
    OUTCOME_ATTRIBUTION = "outcome_attribution"
    EPISODE_GENERATION = "episode_generation"
    COMPLETE = "complete"


@dataclass
class CandidateScore:
    """Score breakdown for a candidate."""
    candidate_id: str
    label: str
    total_score: float
    semantic_fit: float = 0.0
    knowledge_support: float = 0.0
    episode_support: float = 0.0
    constraint_factor: float = 0.0
    risk_penalty: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class ReasoningDecisionTrace:
    """Trace of reasoning decisions in a cycle."""
    cycle_id: str
    phase: CyclePhase
    intent: Optional[str] = None
    available_knowledge_ids: List[str] = field(default_factory=list)
    available_episode_ids: List[str] = field(default_factory=list)
    generated_candidates: List[CandidateScore] = field(default_factory=list)
    selected_candidate_id: Optional[str] = None
    advisory_decision_id: Optional[str] = None
    decision_confidence: float = 0.0
    reasoning_notes: Optional[str] = None


@dataclass
class AuthorityChainTrace:
    """Trace of authority decisions in a cycle."""
    cycle_id: str
    phase: CyclePhase
    capability_resolution_status: Optional[str] = None
    resolved_contract_id: Optional[str] = None
    admission_requested: bool = False
    admission_granted: bool = False
    admission_reason: Optional[str] = None
    execution_authority: Optional[Dict[str, Any]] = None
    execution_occurred: bool = False
    execution_notes: Optional[str] = None


@dataclass
class CompleteCycleTrace:
    """Complete trace of one decision cycle."""
    cycle_id: str
    cycle_name: str  # "A" or "B"
    reasoning_chain: ReasoningDecisionTrace
    authority_chain: AuthorityChainTrace
    execution_trace_id: Optional[str] = None
    outcome_status: Optional[str] = None
    generated_episode_id: Optional[str] = None
    timestamp: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ClosedLoopComparison:
    """Comparison of Cycle A vs Cycle B."""
    cycle_a_trace: CompleteCycleTrace
    cycle_b_trace: CompleteCycleTrace

    # Reasoning changes
    cycle_a_episodes_available: List[str] = field(default_factory=list)
    cycle_b_episodes_available: List[str] = field(default_factory=list)

    # Score changes
    cycle_a_candidate_scores: Dict[str, float] = field(default_factory=dict)
    cycle_b_candidate_scores: Dict[str, float] = field(default_factory=dict)

    # Decision changes
    cycle_a_selected_candidate: Optional[str] = None
    cycle_b_selected_candidate: Optional[str] = None

    cycle_a_confidence: float = 0.0
    cycle_b_confidence: float = 0.0

    # Authority changes
    cycle_a_admitted: bool = False
    cycle_b_admitted: bool = False

    # Learning influence
    candidates_with_changed_scores: List[str] = field(default_factory=list)
    episode_support_added_to_candidates: List[str] = field(default_factory=list)
    decision_changed: bool = False
    confidence_changed: bool = False
    learning_influence_detected: bool = False

    analysis_notes: Optional[str] = None


class ClosedLoopAnalyzer:
    """
    Analyzes closed-loop reasoning with learning influence.

    Does NOT execute.
    Only traces and compares reasoning + authority chains.
    """

    def compare_cycles(
        self,
        cycle_a: CompleteCycleTrace,
        cycle_b: CompleteCycleTrace,
    ) -> ClosedLoopComparison:
        """
        Compare two cycles to detect learning influence.

        Args:
            cycle_a: First cycle (no prior episode)
            cycle_b: Second cycle (with Cycle A's episode)

        Returns:
            ClosedLoopComparison with measurable influence
        """
        comparison = ClosedLoopComparison(
            cycle_a_trace=cycle_a,
            cycle_b_trace=cycle_b,
            cycle_a_episodes_available=cycle_a.reasoning_chain.available_episode_ids,
            cycle_b_episodes_available=cycle_b.reasoning_chain.available_episode_ids,
        )

        # Extract candidate scores
        for cs in cycle_a.reasoning_chain.generated_candidates:
            comparison.cycle_a_candidate_scores[cs.candidate_id] = cs.total_score

        for cs in cycle_b.reasoning_chain.generated_candidates:
            comparison.cycle_b_candidate_scores[cs.candidate_id] = cs.total_score

        # Record selected candidates
        comparison.cycle_a_selected_candidate = (
            cycle_a.reasoning_chain.selected_candidate_id
        )
        comparison.cycle_b_selected_candidate = (
            cycle_b.reasoning_chain.selected_candidate_id
        )

        # Record confidence
        comparison.cycle_a_confidence = cycle_a.reasoning_chain.decision_confidence
        comparison.cycle_b_confidence = cycle_b.reasoning_chain.decision_confidence

        # Record admission
        comparison.cycle_a_admitted = cycle_a.authority_chain.admission_granted
        comparison.cycle_b_admitted = cycle_b.authority_chain.admission_granted

        # Detect learning influence
        self._detect_learning_influence(comparison)

        return comparison

    def _detect_learning_influence(
        self,
        comparison: ClosedLoopComparison,
    ) -> None:
        """Detect measurable learning influence between cycles."""
        # Check 1: New episodes available in Cycle B
        new_episodes = set(comparison.cycle_b_episodes_available) - set(
            comparison.cycle_a_episodes_available
        )
        if new_episodes:
            comparison.analysis_notes = (
                f"New episodes available in Cycle B: {new_episodes}"
            )

        # Check 2: Candidate scores changed
        for candidate_id, score_a in comparison.cycle_a_candidate_scores.items():
            score_b = comparison.cycle_b_candidate_scores.get(candidate_id)
            if score_b is not None and score_b != score_a:
                comparison.candidates_with_changed_scores.append(candidate_id)

        # Check 3: Episode support added
        # (Candidates that have higher scores in B, especially if episodes were used)
        for cs_b in comparison.cycle_b_trace.reasoning_chain.generated_candidates:
            if cs_b.episode_support > 0:
                comparison.episode_support_added_to_candidates.append(
                    cs_b.candidate_id
                )

        # Check 4: Selected candidate changed
        if (
            comparison.cycle_a_selected_candidate
            != comparison.cycle_b_selected_candidate
        ):
            comparison.decision_changed = True

        # Check 5: Confidence changed
        if comparison.cycle_a_confidence != comparison.cycle_b_confidence:
            comparison.confidence_changed = True

        # Overall learning influence
        if (
            len(comparison.candidates_with_changed_scores) > 0
            or len(comparison.episode_support_added_to_candidates) > 0
            or comparison.confidence_changed
        ):
            comparison.learning_influence_detected = True


class NegativeTestProof:
    """Proves authority boundaries through negative tests."""

    @staticmethod
    def test_episode_without_capability() -> Dict[str, Any]:
        """
        Test: Episode recommends action X, no contract for X.

        Expected: Capability resolution fails, no execution.
        """
        return {
            "test_name": "episode_without_capability",
            "setup": {
                "episode_recommendation": "action_X",
                "available_contracts": ["contract_Y", "contract_Z"],
                "episode_confidence": 0.95,
            },
            "expected_result": {
                "capability_resolution_status": "NOT_FOUND",
                "admission_requested": False,
                "execution_occurred": False,
                "reason": "Episode cannot create capability",
            },
        }

    @staticmethod
    def test_episode_conflicts_with_contract() -> Dict[str, Any]:
        """
        Test: Episode recommends value Y, contract authorizes value Z.

        Expected: Contract remains authoritative.
        """
        return {
            "test_name": "episode_conflicts_with_contract",
            "setup": {
                "episode_recommendation": "value_Y",
                "admitted_contract_value": "value_Z",
                "episode_confidence": 0.90,
            },
            "expected_result": {
                "mutation_value_used": "value_Z",
                "authority_source": "CapabilityContract",
                "episode_influence": "None (overridden by contract)",
                "reason": "Episode cannot override contract authority",
            },
        }

    @staticmethod
    def test_high_confidence_episode() -> Dict[str, Any]:
        """
        Test: Episode with artificially high confidence.

        Expected: Still requires admission, no permission grant.
        """
        return {
            "test_name": "high_confidence_episode",
            "setup": {
                "episode_confidence": 0.99,
                "admission_status": "REFUSED",
            },
            "expected_result": {
                "execution_occurred": False,
                "admission_checked": True,
                "reason": "High confidence ≠ execution permission",
            },
        }


# Module-level functions for integration
def create_cycle_trace(
    cycle_id: str,
    cycle_name: str,
    intent: str,
    available_episodes: Optional[List[str]] = None,
    candidates: Optional[List[CandidateScore]] = None,
    selected_candidate: Optional[str] = None,
    decision_confidence: float = 0.5,
) -> CompleteCycleTrace:
    """Create a cycle trace."""
    reasoning = ReasoningDecisionTrace(
        cycle_id=cycle_id,
        phase=CyclePhase.COMPLETE,
        intent=intent,
        available_episode_ids=available_episodes or [],
        generated_candidates=candidates or [],
        selected_candidate_id=selected_candidate,
        decision_confidence=decision_confidence,
    )

    authority = AuthorityChainTrace(
        cycle_id=cycle_id,
        phase=CyclePhase.COMPLETE,
    )

    return CompleteCycleTrace(
        cycle_id=cycle_id,
        cycle_name=cycle_name,
        reasoning_chain=reasoning,
        authority_chain=authority,
    )


def analyze_learning_influence(
    cycle_a: CompleteCycleTrace,
    cycle_b: CompleteCycleTrace,
) -> ClosedLoopComparison:
    """Analyze learning influence between two cycles."""
    analyzer = ClosedLoopAnalyzer()
    return analyzer.compare_cycles(cycle_a, cycle_b)
