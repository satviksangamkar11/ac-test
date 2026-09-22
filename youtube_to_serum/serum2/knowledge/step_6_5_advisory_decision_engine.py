"""
STEP 6.5 — ADVISORY DECISION ENGINE

Turns semantic candidates (from 6.4) into explainable advisory decisions.

Key principle:
    DECISION = REASONING + CANDIDATE, not AUTHORITY

The engine selects which candidate to prefer and why, without:
    - Authorizing execution
    - Creating CapabilityContracts
    - Generating concrete mutation values
    - Establishing measurement authority
    - Assigning backend target paths as universal

Advisory decision remains inspectable, explainable, and separate from execution.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from step_6_4_semantic_reasoning_integration import (
    SemanticCandidate,
    CandidateStatus,
)
from step_6_3_episode_context_integration import (
    EpisodeContextBridge,
    MeasurementOutcome,
)
from step_6_2_universal_production_intent import (
    UniversalProductionIntent,
)


class DecisionStatus(Enum):
    """Status of an advisory decision."""
    DECIDED = "decided"  # Selected candidate with confidence
    TENTATIVE = "tentative"  # Selected but with caveats
    CONFLICTED = "conflicted"  # Conflicting evidence
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # Too uncertain to decide
    ABSTAINED = "abstained"  # No viable candidate


class EvidenceType(Enum):
    """Type of evidence supporting/opposing a candidate."""
    FROM_KNOWLEDGE = "from_knowledge"
    FROM_EPISODE_SUCCESS = "from_episode_success"
    FROM_EPISODE_FAILURE = "from_episode_failure"
    FROM_SEMANTIC_FIT = "from_semantic_fit"
    FROM_CONSTRAINT = "from_constraint"
    CONTRADICTS_KNOWLEDGE = "contradicts_knowledge"
    CONTRADICTS_EPISODE = "contradicts_episode"


@dataclass
class ScoringFactor:
    """One component of a candidate's score."""
    name: str
    """Name of this factor (e.g., 'semantic fit', 'knowledge support')."""

    value: float
    """Numeric score (0.0-1.0)."""

    weight: float
    """How much this factor contributes to total (0.0-1.0)."""

    reasoning: str
    """Why this factor has this value."""

    evidence_type: EvidenceType
    """Source of this scoring factor."""

    def contribution(self) -> float:
        """Score contribution: value × weight."""
        return self.value * self.weight


@dataclass
class WeightingModel:
    """
    Transparent weighting model for decision scoring.

    Every scoring component is explainable.
    """

    semantic_fit_weight: float = 0.25
    """How much semantic concept matching matters."""

    knowledge_support_weight: float = 0.20
    """How much knowledge relevance matters."""

    episode_precedent_weight: float = 0.20
    """How much prior success matters."""

    constraint_satisfaction_weight: float = 0.15
    """How much user constraint satisfaction matters."""

    risk_penalty_weight: float = 0.10
    """How much candidate risk matters (penalty)."""

    uncertainty_penalty_weight: float = 0.10
    """How much uncertainty matters (penalty)."""

    min_confidence_for_decision: float = 0.60
    """Minimum confidence to make a decision (else INSUFFICIENT_EVIDENCE)."""

    min_confidence_for_tentative: float = 0.40
    """Minimum confidence to mark as TENTATIVE (else ABSTAIN)."""


@dataclass
class CandidateEvaluation:
    """Evaluation of a single candidate."""
    candidate: SemanticCandidate
    """The candidate being evaluated."""

    scoring_factors: List[ScoringFactor] = field(default_factory=list)
    """Breakdown of score components."""

    total_score: float = 0.0
    """Final score (0.0-1.0)."""

    supporting_evidence: List[str] = field(default_factory=list)
    """Evidence supporting this candidate."""

    conflicting_evidence: List[str] = field(default_factory=list)
    """Evidence opposing or conflicting with this candidate."""

    reasons_for_rejection: List[str] = field(default_factory=list)
    """Why this candidate was not selected (if not selected)."""

    was_eliminated_by_constraint: bool = False
    """Whether a user constraint filtered this candidate."""

    def score_breakdown(self) -> Dict[str, float]:
        """Return score components as dict."""
        return {f.name: f.value for f in self.scoring_factors}


@dataclass
class AdvisoryDecision:
    """
    An advisory production decision.

    Selected candidate with full reasoning and provenance.
    Remains non-authoritative and advisory-only.
    """

    decision_id: str
    """Unique identifier."""

    intent: UniversalProductionIntent
    """The user intent that prompted this decision."""

    selected_candidate: Optional[SemanticCandidate] = None
    """The recommended candidate (None if abstained)."""

    selected_candidate_score: float = 0.0
    """Confidence in selected candidate (0.0-1.0)."""

    alternative_candidates: List[Tuple[SemanticCandidate, float]] = field(default_factory=list)
    """Ranked alternatives (candidate, score) tuples."""

    decision_status: DecisionStatus = DecisionStatus.ABSTAINED
    """Whether decided, tentative, conflicted, insufficient, or abstained."""

    selection_reason: str = ""
    """Why this candidate was selected (main reasoning)."""

    supporting_knowledge_ids: List[str] = field(default_factory=list)
    """Knowledge items that informed this decision."""

    supporting_episode_ids: List[str] = field(default_factory=list)
    """Episodes that influenced this decision."""

    candidate_evaluations: List[CandidateEvaluation] = field(default_factory=list)
    """Full evaluation of each candidate considered."""

    conflicts: List[str] = field(default_factory=list)
    """Known conflicts in evidence."""

    uncertainties: List[str] = field(default_factory=list)
    """Remaining uncertainties."""

    constraints_applied: List[str] = field(default_factory=list)
    """User constraints that affected this decision."""

    decision_trace: List[str] = field(default_factory=list)
    """Step-by-step reasoning trace."""

    confidence: float = 0.0
    """Overall confidence (0.0-1.0)."""

    provenance: Optional[str] = None
    """How this decision was made."""

    notes: Optional[str] = None
    """Additional context."""


class AdvisoryDecisionEngine:
    """
    Produces advisory decisions from semantic candidates.

    Integrates:
    - User intent
    - Semantic candidates
    - Knowledge support
    - Episode context
    - User constraints
    - Uncertainty and conflicts

    Output: Explainable, non-authoritative decision.
    """

    def __init__(
        self,
        weighting_model: Optional[WeightingModel] = None,
        episode_bridge: Optional[EpisodeContextBridge] = None,
    ):
        """Initialize decision engine."""
        self.weighting_model = weighting_model or WeightingModel()
        self.episode_bridge = episode_bridge or EpisodeContextBridge()
        self.decision_trace: List[str] = []

    def decide(
        self,
        intent: UniversalProductionIntent,
        candidates: List[SemanticCandidate],
        knowledge_items: Optional[List[Dict[str, Any]]] = None,
        constraints: Optional[List[str]] = None,
    ) -> AdvisoryDecision:
        """
        Make an advisory decision.

        Args:
            intent: User production intent
            candidates: Semantic candidates from 6.4
            knowledge_items: Optional knowledge items
            constraints: Optional user constraints

        Returns:
            AdvisoryDecision with full reasoning and provenance
        """
        self.decision_trace = []
        decision = AdvisoryDecision(
            decision_id=f"adv_{id(intent)}",
            intent=intent,
            provenance="AdvisoryDecisionEngine.decide()",
        )

        self._log("Starting advisory decision")

        # Step 1: Filter candidates by constraints
        viable_candidates = self._apply_constraints(
            candidates, constraints or []
        )
        decision.constraints_applied = constraints or []
        self._log(f"After constraints: {len(viable_candidates)} viable candidates")

        if not viable_candidates:
            self._log("No viable candidates remain")
            decision.decision_status = DecisionStatus.ABSTAINED
            decision.uncertainties.append("No viable candidates after constraint filtering")
            decision.decision_trace = self.decision_trace
            return decision

        # Step 2: Evaluate each candidate
        evaluations = []
        for candidate in viable_candidates:
            eval = self._evaluate_candidate(
                candidate, intent, knowledge_items
            )
            evaluations.append(eval)
            decision.candidate_evaluations.append(eval)

        self._log(f"Evaluated {len(evaluations)} candidates")

        # Step 3: Rank candidates
        ranked = sorted(evaluations, key=lambda e: e.total_score, reverse=True)
        self._log(f"Ranked candidates (top: {ranked[0].total_score:.2f})")

        # Step 4: Check for conflicts
        conflicts = self._detect_conflicts(evaluations)
        decision.conflicts.extend(conflicts)

        # Step 5: Select candidate or abstain
        if ranked:
            top_eval = ranked[0]

            if top_eval.total_score >= self.weighting_model.min_confidence_for_decision:
                decision.selected_candidate = top_eval.candidate
                decision.selected_candidate_score = top_eval.total_score
                decision.decision_status = DecisionStatus.DECIDED
                decision.selection_reason = f"Score {top_eval.total_score:.2f}: {', '.join(top_eval.supporting_evidence)}"
                self._log(f"Selected: {top_eval.candidate.label}")

            elif top_eval.total_score >= self.weighting_model.min_confidence_for_tentative:
                decision.selected_candidate = top_eval.candidate
                decision.selected_candidate_score = top_eval.total_score
                decision.decision_status = DecisionStatus.TENTATIVE
                decision.uncertainties.extend([
                    f"Score {top_eval.total_score:.2f} below decision threshold {self.weighting_model.min_confidence_for_decision}",
                    "Candidate selected tentatively due to limited alternatives",
                ])
                self._log("Selected tentatively (low confidence)")

            else:
                decision.decision_status = DecisionStatus.INSUFFICIENT_EVIDENCE
                decision.uncertainties.append(
                    f"Best candidate score {top_eval.total_score:.2f} below tentative threshold"
                )
                self._log("Insufficient evidence to select")

            # Record alternatives
            if len(ranked) > 1:
                decision.alternative_candidates = [
                    (e.candidate, e.total_score) for e in ranked[1:]
                ]

        decision.confidence = decision.selected_candidate_score if decision.selected_candidate else 0.0
        decision.decision_trace = self.decision_trace

        return decision

    def _apply_constraints(
        self,
        candidates: List[SemanticCandidate],
        constraints: List[str]
    ) -> List[SemanticCandidate]:
        """Filter candidates by user constraints."""
        if not constraints:
            return candidates

        viable = []
        for candidate in candidates:
            # Check if candidate satisfies constraints
            satisfies = all(
                c in candidate.constraints_satisfied
                for c in constraints
            )

            if satisfies:
                viable.append(candidate)
            else:
                self._log(f"Filtered {candidate.label}: does not satisfy constraints")

        return viable

    def _evaluate_candidate(
        self,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
        knowledge_items: Optional[List[Dict[str, Any]]] = None,
    ) -> CandidateEvaluation:
        """Evaluate a single candidate."""
        eval = CandidateEvaluation(candidate=candidate)

        # Semantic fit
        semantic_fit = self._score_semantic_fit(candidate, intent)
        eval.scoring_factors.append(ScoringFactor(
            name="semantic_fit",
            value=semantic_fit,
            weight=self.weighting_model.semantic_fit_weight,
            reasoning=f"Candidate concept matches intent target/direction",
            evidence_type=EvidenceType.FROM_SEMANTIC_FIT,
        ))

        if semantic_fit > 0.7:
            eval.supporting_evidence.append(f"Strong semantic fit ({semantic_fit:.2f})")

        # Knowledge support
        if knowledge_items:
            knowledge_score = self._score_knowledge_support(
                candidate, knowledge_items
            )
            eval.scoring_factors.append(ScoringFactor(
                name="knowledge_support",
                value=knowledge_score,
                weight=self.weighting_model.knowledge_support_weight,
                reasoning=f"Knowledge items support this candidate",
                evidence_type=EvidenceType.FROM_KNOWLEDGE,
            ))

            if knowledge_score > 0.5:
                eval.supporting_evidence.append(f"Knowledge supports ({knowledge_score:.2f})")

        # Episode precedent
        episode_score = self._score_episode_precedent(candidate)
        eval.scoring_factors.append(ScoringFactor(
            name="episode_precedent",
            value=episode_score,
            weight=self.weighting_model.episode_precedent_weight,
            reasoning=f"Prior episodes demonstrate success with similar candidate",
            evidence_type=EvidenceType.FROM_EPISODE_SUCCESS,
        ))

        if episode_score > 0.5:
            eval.supporting_evidence.append(f"Prior success ({episode_score:.2f})")

        # Risk penalty
        risk_penalty = 1.0 - (len(candidate.risks) * 0.1)
        risk_penalty = max(risk_penalty, 0.0)
        eval.scoring_factors.append(ScoringFactor(
            name="risk_penalty",
            value=risk_penalty,
            weight=self.weighting_model.risk_penalty_weight,
            reasoning=f"Candidate has {len(candidate.risks)} known risks",
            evidence_type=EvidenceType.FROM_CONSTRAINT,
        ))

        if candidate.status == CandidateStatus.RISKY:
            eval.conflicting_evidence.append("Candidate marked as risky")

        # Calculate total score
        total = sum(f.contribution() for f in eval.scoring_factors)
        eval.total_score = min(max(total, 0.0), 1.0)

        return eval

    def _score_semantic_fit(
        self,
        candidate: SemanticCandidate,
        intent: UniversalProductionIntent,
    ) -> float:
        """Score how well candidate matches intent."""
        score = 0.0

        # Target concept match
        if (candidate.target_concept and intent.target_concept and
            candidate.target_concept == intent.target_concept):
            score += 0.5

        # Direction match
        if (candidate.semantic_direction and intent.semantic_direction and
            candidate.semantic_direction == intent.semantic_direction):
            score += 0.5

        return min(score, 1.0)

    def _score_knowledge_support(
        self,
        candidate: SemanticCandidate,
        knowledge_items: List[Dict[str, Any]],
    ) -> float:
        """Score knowledge support."""
        if not knowledge_items:
            return 0.0

        supported = sum(
            1 for kid in candidate.supporting_knowledge_ids
            if any(k.get("id") == kid for k in knowledge_items)
        )

        return min(supported / len(knowledge_items) if knowledge_items else 0.0, 1.0)

    def _score_episode_precedent(
        self,
        candidate: SemanticCandidate,
    ) -> float:
        """Score episode precedent."""
        if not candidate.supporting_episodes:
            return 0.3  # No prior episode, default modest score

        # More episodes = higher score (up to 1.0)
        return min(0.3 + (len(candidate.supporting_episodes) * 0.1), 1.0)

    def _detect_conflicts(
        self,
        evaluations: List[CandidateEvaluation],
    ) -> List[str]:
        """Detect conflicting evidence."""
        conflicts = []

        # Check if candidates have contradicting supporting evidence
        for i, eval1 in enumerate(evaluations):
            for eval2 in evaluations[i+1:]:
                if (eval1.conflicting_evidence and eval2.supporting_evidence):
                    for conflict in eval1.conflicting_evidence:
                        for support in eval2.supporting_evidence:
                            if any(word in conflict.lower() and word in support.lower()
                                   for word in ["prior", "episode", "knowledge"]):
                                conflicts.append(
                                    f"Evidence conflict: {eval1.candidate.label} "
                                    f"conflicts with {eval2.candidate.label}"
                                )

        return conflicts

    def _log(self, message: str) -> None:
        """Log a decision step."""
        self.decision_trace.append(message)


def make_advisory_decision(
    intent: UniversalProductionIntent,
    candidates: List[SemanticCandidate],
    knowledge_items: Optional[List[Dict[str, Any]]] = None,
    constraints: Optional[List[str]] = None,
    episode_bridge: Optional[EpisodeContextBridge] = None,
) -> AdvisoryDecision:
    """
    Top-level function to make an advisory decision.

    Args:
        intent: User production intent
        candidates: Semantic candidates from 6.4
        knowledge_items: Optional knowledge items
        constraints: Optional user constraints
        episode_bridge: Optional episode context

    Returns:
        AdvisoryDecision with full reasoning
    """
    engine = AdvisoryDecisionEngine(episode_bridge=episode_bridge)
    return engine.decide(intent, candidates, knowledge_items, constraints)
