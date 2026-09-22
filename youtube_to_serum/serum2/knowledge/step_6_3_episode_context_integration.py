"""
STEP 6.3 — KNOWLEDGE + EPISODE DECISION CONTEXT INTEGRATION

Bridges universal production intent with episode context (prior decisions, outcomes,
learned patterns) to inform advisory recommendations.

Key principle:
    INTENT + EPISODE_CONTEXT → ADVISORY_REASONING (knowledge-informed, authority-independent)

Episode context sources:
  1. Prior production goals (goals, targets, outcomes)
  2. Measurements (what was observed, how did changes affect sound)
  3. Learned patterns (when X was applied, Y typically happened)
  4. Decision trace (what was tried, why it was/wasn't pursued)
  5. Feedback loop closure (did the change match expectations)

Integration points:
  - Match current intent against prior similar goals
  - Retrieve knowledge items relevant to current intent
  - Cross-reference with past episodes for learned patterns
  - Suggest candidates based on intent + episode context + knowledge
  - Preserve decision reasoning for traceability
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime

from step_6_2_universal_production_intent import (
    UniversalProductionIntent,
    SemanticDirection,
    IntentResolutionStatus,
)


class EpisodePhase(Enum):
    """Phase within an episode/session."""
    INTENT_CAPTURE = "intent_capture"
    REASONING = "reasoning"
    DECISION = "decision"
    EXECUTION = "execution"
    MEASUREMENT = "measurement"
    FEEDBACK = "feedback"
    CLOSED = "closed"


class DecisionType(Enum):
    """Type of production decision made."""
    GOAL_SELECTION = "goal_selection"  # Producer selected a goal
    TARGET_SELECTION = "target_selection"  # Selected which parameter to change
    VALUE_DETERMINATION = "value_determination"  # Selected how much to change
    EXECUTION_ATTEMPT = "execution_attempt"  # Tried to apply the change
    SKIP_DECISION = "skip_decision"  # Decided not to pursue this direction


class MeasurementOutcome(Enum):
    """Outcome of measurement comparison."""
    POSITIVE = "positive"  # Change matched expectation (better)
    NEUTRAL = "neutral"  # No detectable difference
    NEGATIVE = "negative"  # Change degraded (worse)
    UNEXPECTED = "unexpected"  # Different from expectation
    UNMEASURED = "unmeasured"  # Not measured


@dataclass
class PriorGoal:
    """A goal from prior episode/session."""
    goal_id: str
    """Unique identifier for this goal."""

    musical_objective: str
    """What was being attempted."""

    target_concept: Optional[str] = None
    """What was targeted (universal concept)."""

    semantic_direction: Optional[SemanticDirection] = None
    """Direction of change attempted."""

    timestamp: Optional[str] = None
    """When this goal was created."""

    outcome: MeasurementOutcome = MeasurementOutcome.UNMEASURED
    """How did this goal's execution turn out?"""

    notes: Optional[str] = None
    """Context about this goal."""

    def similarity_to_intent(self, intent: UniversalProductionIntent) -> float:
        """
        Score similarity to a current intent (0.0-1.0).

        Factors:
        - Target concept match
        - Semantic direction match
        - Objective text similarity (simple substring check)
        """
        score = 0.0

        # Exact target concept match: +0.4
        if (self.target_concept and intent.target_concept and
            self.target_concept == intent.target_concept):
            score += 0.4

        # Semantic direction match: +0.35
        if (self.semantic_direction and intent.semantic_direction and
            self.semantic_direction == intent.semantic_direction):
            score += 0.35

        # Objective similarity (substring): +0.25
        if self.musical_objective and intent.musical_objective:
            obj_lower = self.musical_objective.lower()
            curr_lower = intent.musical_objective.lower()
            if obj_lower in curr_lower or curr_lower in obj_lower:
                score += 0.25

        return min(score, 1.0)


@dataclass
class EpisodeDecision:
    """A single decision point within an episode."""
    decision_id: str
    """Unique identifier."""

    episode_id: str
    """Which episode this decision belongs to."""

    decision_type: DecisionType
    """What kind of decision was made."""

    phase: EpisodePhase
    """Production phase when decision was made."""

    intent: UniversalProductionIntent
    """The user intent at this decision point."""

    reasoning: str
    """Why this decision was made."""

    candidates_considered: List[str] = field(default_factory=list)
    """Candidate options that were evaluated."""

    chosen_candidate: Optional[str] = None
    """Which candidate was selected."""

    knowledge_items_referenced: List[str] = field(default_factory=list)
    """Knowledge item IDs that informed this decision."""

    measurement_outcome: Optional[MeasurementOutcome] = None
    """How did this decision turn out? (filled after measurement phase)."""

    feedback: Optional[str] = None
    """Producer's feedback on this decision (how it sounded, etc)."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    """When this decision was made."""

    confidence: float = 0.5
    """Confidence in this decision (0.0-1.0)."""


@dataclass
class Episode:
    """
    A complete production session/episode.

    Episodes track:
    - What the producer wanted (intent)
    - What candidates were considered (reasoning)
    - What was decided (decision trace)
    - What was learned (measurements and feedback)
    """

    episode_id: str
    """Unique episode identifier."""

    initial_intent: UniversalProductionIntent
    """What the producer started with."""

    phase: EpisodePhase = EpisodePhase.INTENT_CAPTURE
    """Current phase of this episode."""

    decisions: List[EpisodeDecision] = field(default_factory=list)
    """All decisions made in this episode."""

    prior_goals: List[PriorGoal] = field(default_factory=list)
    """Goals from earlier episodes (used for pattern learning)."""

    learned_patterns: List[str] = field(default_factory=list)
    """Patterns learned from this episode (for future reference)."""

    timestamp_created: str = field(default_factory=lambda: datetime.now().isoformat())
    """When this episode was created."""

    timestamp_closed: Optional[str] = None
    """When this episode was closed."""

    notes: Optional[str] = None
    """Episode-level notes."""

    def add_decision(self, decision: EpisodeDecision) -> None:
        """Add a decision to this episode."""
        self.decisions.append(decision)
        self.phase = decision.phase

    def close_episode(self, learned: Optional[List[str]] = None) -> None:
        """Mark this episode as complete."""
        self.phase = EpisodePhase.CLOSED
        self.timestamp_closed = datetime.now().isoformat()
        if learned:
            self.learned_patterns.extend(learned)

    def get_positive_outcomes(self) -> List[EpisodeDecision]:
        """Get decisions that had positive measurement outcomes."""
        return [
            d for d in self.decisions
            if d.measurement_outcome == MeasurementOutcome.POSITIVE
        ]

    def get_learned_strategies(self) -> List[Dict[str, Any]]:
        """Extract generalizable strategies from this episode."""
        strategies = []

        for decision in self.get_positive_outcomes():
            if decision.chosen_candidate:
                strategy = {
                    "intent_pattern": decision.intent.target_concept,
                    "direction": decision.intent.semantic_direction.value if decision.intent.semantic_direction else None,
                    "candidate_type": decision.chosen_candidate,
                    "reasoning": decision.reasoning,
                    "confidence": decision.confidence,
                }
                strategies.append(strategy)

        return strategies


class EpisodeContextBridge:
    """
    Bridges episode context (history, learned patterns) with current intent
    to inform advisory recommendations.

    Integration flow:
        1. Current intent arrives
        2. Search prior episodes for similar goals
        3. Retrieve knowledge items for intent
        4. Cross-reference learned patterns
        5. Suggest candidates based on (intent + context + knowledge)
        6. Return advisory recommendations with reasoning
    """

    def __init__(self):
        """Initialize bridge."""
        self.episodes: Dict[str, Episode] = {}
        self.learned_strategies: List[Dict[str, Any]] = []

    def add_episode(self, episode: Episode) -> None:
        """Store an episode for future reference."""
        self.episodes[episode.episode_id] = episode
        self.learned_strategies.extend(episode.get_learned_strategies())

    def find_similar_prior_goals(
        self,
        intent: UniversalProductionIntent,
        threshold: float = 0.5
    ) -> List[Tuple[PriorGoal, float]]:
        """
        Find prior goals similar to current intent.

        Returns: List of (goal, similarity_score) tuples, sorted by similarity.
        """
        similar = []

        for episode in self.episodes.values():
            for goal in episode.prior_goals:
                sim = goal.similarity_to_intent(intent)
                if sim >= threshold:
                    similar.append((goal, sim))

        # Sort by similarity (highest first)
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar

    def find_learned_strategies_for_intent(
        self,
        intent: UniversalProductionIntent
    ) -> List[Dict[str, Any]]:
        """
        Find learned strategies matching the current intent.

        Returns: Strategies where intent_pattern matches intent.target_concept
        """
        matching = []

        for strategy in self.learned_strategies:
            if (intent.target_concept and
                strategy.get("intent_pattern") == intent.target_concept):
                # Direction match strengthens score
                if (intent.semantic_direction and
                    strategy.get("direction") == intent.semantic_direction.value):
                    matching.append((strategy, 1.0))
                else:
                    matching.append((strategy, 0.7))

        # Sort by confidence
        matching.sort(key=lambda x: x[0].get("confidence", 0.5), reverse=True)
        return matching

    def build_recommendation_context(
        self,
        intent: UniversalProductionIntent
    ) -> Dict[str, Any]:
        """
        Build full context for advisory recommendation.

        Returns dict with:
            - similar_prior_goals
            - learned_strategies
            - contextual_reasoning
            - confidence_adjustment (based on episode context)
        """
        context = {
            "intent": intent.to_dict() if hasattr(intent, 'to_dict') else asdict(intent),
            "similar_prior_goals": [],
            "learned_strategies": [],
            "contextual_reasoning": None,
            "confidence_adjustment": 0.0,
        }

        # Find similar prior goals
        similar_goals = self.find_similar_prior_goals(intent)
        if similar_goals:
            context["similar_prior_goals"] = [
                {
                    "goal": g.musical_objective,
                    "target": g.target_concept,
                    "outcome": g.outcome.value,
                    "similarity": sim,
                }
                for g, sim in similar_goals
            ]

            # Boost confidence if similar goals had positive outcomes
            positive_count = sum(
                1 for g, _ in similar_goals
                if g.outcome == MeasurementOutcome.POSITIVE
            )
            context["confidence_adjustment"] = min(0.2, positive_count * 0.05)

        # Find learned strategies
        learned = self.find_learned_strategies_for_intent(intent)
        if learned:
            context["learned_strategies"] = [
                s[0] for s in learned
            ]

        # Build reasoning
        reasoning_parts = []
        if similar_goals:
            reasoning_parts.append(
                f"Found {len(similar_goals)} similar prior goals with {positive_count} positive outcomes"
            )
        if learned:
            reasoning_parts.append(
                f"Found {len(learned)} learned strategies for this intent pattern"
            )

        if reasoning_parts:
            context["contextual_reasoning"] = "; ".join(reasoning_parts)

        return context


def integrate_intent_with_episode_context(
    intent: UniversalProductionIntent,
    bridge: EpisodeContextBridge
) -> Dict[str, Any]:
    """
    Top-level function to integrate intent with episode context.

    Returns:
        Dict with:
            - original_intent
            - episode_context
            - recommended_reasoning
            - suggested_next_steps
    """

    result = {
        "original_intent": intent.to_dict() if hasattr(intent, 'to_dict') else asdict(intent),
        "episode_context": bridge.build_recommendation_context(intent),
        "recommended_reasoning": None,
        "suggested_next_steps": [],
    }

    # Build reasoning summary
    context = result["episode_context"]

    # Step 1: Similar prior goals suggest patterns
    if context["similar_prior_goals"]:
        best_goal = context["similar_prior_goals"][0]
        if best_goal["outcome"] == "positive":
            result["recommended_reasoning"] = (
                f"Prior goals for '{best_goal['goal']}' succeeded; "
                f"similar strategy likely applicable here."
            )
            result["suggested_next_steps"] = [
                "Retrieve knowledge items for this target concept",
                "Propose candidates based on prior success pattern",
                "Present to producer for confirmation",
            ]
        elif best_goal["outcome"] == "negative":
            result["recommended_reasoning"] = (
                f"Prior goal '{best_goal['goal']}' failed; "
                f"consider alternative strategies."
            )
            result["suggested_next_steps"] = [
                "Retrieve alternative approaches from knowledge",
                "Propose different candidates",
            ]

    # Step 2: Learned strategies provide direct guidance
    if context["learned_strategies"]:
        strat = context["learned_strategies"][0]
        result["recommended_reasoning"] = (
            f"Learned strategy applies: {strat['reasoning']}"
        )
        result["suggested_next_steps"] = [
            f"Consider candidate: {strat['candidate_type']}",
            "Verify prerequisites are met",
            "Present to producer",
        ]

    return result
