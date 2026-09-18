"""
STEP 6.4 — KNOWLEDGE + SEMANTIC REASONING INTEGRATION

Bridges semantic intent, knowledge base, and episode context to produce
full advisory recommendations with reasoning chains.

Integration flow:
    User Intent (6.2) → Semantic Mapping (universal concepts)
    ↓
    Knowledge Retrieval (5.7-5.8) → Relevant expertise items
    ↓
    Episode Context (6.3) → Prior patterns and learned strategies
    ↓
    Semantic Reasoning → Candidate generation and ranking
    ↓
    Advisory Proposal (5.10) → Backend-independent recommendation

Key principle:
    REASONING ≠ AUTHORITY

Semantic reasoning produces candidates, rankings, and justifications.
Authority remains separate (handled by CapabilityContract admission).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from step_6_2_universal_production_intent import (
    UniversalProductionIntent,
    SemanticDirection,
)
from step_6_3_episode_context_integration import (
    EpisodeContextBridge,
    MeasurementOutcome,
)


class CandidateReason(Enum):
    """Why a candidate was generated."""
    FROM_KNOWLEDGE = "from_knowledge"  # Knowledge item suggested it
    FROM_EPISODE_PATTERN = "from_episode_pattern"  # Learned pattern suggests it
    FROM_SEMANTIC_MAP = "from_semantic_map"  # Semantic mapping suggests it
    FROM_CONSTRAINT = "from_constraint"  # Constraint satisfaction
    FROM_SYNTHESIS = "from_synthesis"  # Reasoning combined multiple sources


class CandidateStatus(Enum):
    """Status of a candidate."""
    VIABLE = "viable"  # Could work
    RISKY = "risky"  # Has potential downsides
    CONTRADICTED = "contradicted"  # Known to fail in some contexts
    UNKNOWN = "unknown"  # No evidence either way
    FILTERED = "filtered"  # Removed during screening


@dataclass
class SemanticCandidate:
    """
    A candidate operation derived from semantic reasoning.

    Candidates bridge universal concepts to implementable suggestions.
    """

    candidate_id: str
    """Unique identifier."""

    label: str
    """Human-readable label (e.g., 'reduce release time')."""

    target_concept: str
    """Universal target (e.g., 'note-release')."""

    semantic_direction: Optional[SemanticDirection] = None
    """Direction of change."""

    operation: Optional[str] = None
    """Suggested operation (e.g., 'decrease', 'shorten')."""

    confidence: float = 0.5
    """Confidence this candidate is appropriate (0.0-1.0)."""

    source_reasons: List[CandidateReason] = field(default_factory=list)
    """Why this candidate was generated."""

    supporting_knowledge_ids: List[str] = field(default_factory=list)
    """Knowledge items that support this candidate."""

    supporting_episodes: List[str] = field(default_factory=list)
    """Episodes that demonstrated success with this candidate."""

    status: CandidateStatus = CandidateStatus.VIABLE
    """Current status of this candidate."""

    risks: List[str] = field(default_factory=list)
    """Potential downsides or constraints."""

    constraints_satisfied: List[str] = field(default_factory=list)
    """Which user constraints this candidate satisfies."""

    reasoning: str = ""
    """Reasoning chain that produced this candidate."""

    estimated_effect: Optional[str] = None
    """What the user should expect to hear/perceive."""

    backend_hint: Optional[str] = None
    """Optional suggestion for backend implementation (not authoritative)."""


@dataclass
class SemanticReasoningResult:
    """Result of semantic reasoning over intent + context."""

    intent: UniversalProductionIntent
    """The original intent."""

    generated_candidates: List[SemanticCandidate] = field(default_factory=list)
    """All candidates generated."""

    ranked_candidates: List[Tuple[SemanticCandidate, float]] = field(default_factory=list)
    """Candidates ranked by appropriateness (candidate, score)."""

    primary_candidate: Optional[SemanticCandidate] = None
    """Top recommendation."""

    reasoning_chain: List[str] = field(default_factory=list)
    """Steps in the reasoning process."""

    ambiguity_resolved: bool = False
    """Whether semantic reasoning resolved intent ambiguity."""

    confidence: float = 0.5
    """Overall confidence in these recommendations (0.0-1.0)."""

    notes: Optional[str] = None
    """Additional context."""


class SemanticReasoningEngine:
    """
    Performs semantic reasoning to generate advisory candidates.

    Integration points:
    1. Universal intent (what user wants)
    2. Knowledge retrieval (what we know)
    3. Episode context (what worked before)
    4. Constraint satisfaction (user requirements)

    Output: Ranked candidates with reasoning chains
    """

    def __init__(self, episode_bridge: Optional[EpisodeContextBridge] = None):
        """Initialize reasoning engine."""
        self.episode_bridge = episode_bridge or EpisodeContextBridge()
        self.reasoning_steps: List[str] = []

    def reason_about_intent(
        self,
        intent: UniversalProductionIntent,
        knowledge_items: Optional[List[Dict[str, Any]]] = None,
    ) -> SemanticReasoningResult:
        """
        Perform semantic reasoning over intent to generate candidates.

        Args:
            intent: The universal production intent
            knowledge_items: Retrieved knowledge items (optional)

        Returns:
            SemanticReasoningResult with candidates and reasoning
        """
        self.reasoning_steps = []
        result = SemanticReasoningResult(intent=intent)

        # Step 1: Analyze intent
        self._log_reasoning("Analyzing user intent: " + intent.original_user_request)

        if not intent.target_concept:
            self._log_reasoning("Intent lacks specific target concept")
        else:
            self._log_reasoning(f"Target concept identified: {intent.target_concept}")

        # Step 2: Generate candidates from semantic properties
        if intent.target_concept and intent.semantic_direction:
            candidates = self._generate_semantic_candidates(intent)
            result.generated_candidates.extend(candidates)
            self._log_reasoning(f"Generated {len(candidates)} semantic candidates")

        # Step 3: Augment with knowledge
        if knowledge_items:
            knowledge_candidates = self._generate_knowledge_candidates(
                intent, knowledge_items
            )
            result.generated_candidates.extend(knowledge_candidates)
            self._log_reasoning(
                f"Augmented with {len(knowledge_candidates)} knowledge-based candidates"
            )

        # Step 4: Filter with episode context
        episode_context = self.episode_bridge.build_recommendation_context(intent)
        if episode_context.get("learned_strategies"):
            context_candidates = self._generate_context_candidates(
                intent, episode_context
            )
            result.generated_candidates.extend(context_candidates)
            self._log_reasoning(
                f"Added {len(context_candidates)} episode-context candidates"
            )

        # Step 5: Rank candidates
        ranked = self._rank_candidates(result.generated_candidates, intent)
        result.ranked_candidates = ranked
        self._log_reasoning(f"Ranked {len(ranked)} candidates")

        # Step 6: Select primary
        if ranked:
            result.primary_candidate = ranked[0][0]
            result.confidence = ranked[0][1]
            self._log_reasoning(
                f"Primary candidate: {result.primary_candidate.label} "
                f"(confidence: {result.confidence:.2f})"
            )

        result.reasoning_chain = self.reasoning_steps
        return result

    def _generate_semantic_candidates(
        self,
        intent: UniversalProductionIntent
    ) -> List[SemanticCandidate]:
        """Generate candidates directly from intent properties."""
        candidates = []

        if not intent.target_concept or not intent.semantic_direction:
            return candidates

        # Create a primary candidate from intent
        direction_name = intent.semantic_direction.value
        candidate = SemanticCandidate(
            candidate_id=f"sem_{intent.target_concept}_{direction_name}",
            label=f"{direction_name} {intent.target_concept}",
            target_concept=intent.target_concept,
            semantic_direction=intent.semantic_direction,
            operation=intent.operation,
            confidence=intent.confidence,
            source_reasons=[CandidateReason.FROM_SEMANTIC_MAP],
            reasoning=f"Direct mapping from user intent for {intent.target_concept}",
        )

        candidates.append(candidate)

        return candidates

    def _generate_knowledge_candidates(
        self,
        intent: UniversalProductionIntent,
        knowledge_items: List[Dict[str, Any]]
    ) -> List[SemanticCandidate]:
        """Generate candidates from knowledge items."""
        candidates = []

        for item in knowledge_items:
            # Extract suggestion from knowledge item
            if "target_concept" in item and "operation" in item:
                candidate = SemanticCandidate(
                    candidate_id=f"know_{item.get('id', 'unknown')}",
                    label=item.get("title", "Knowledge suggestion"),
                    target_concept=item["target_concept"],
                    operation=item.get("operation"),
                    confidence=0.7,  # Knowledge-backed
                    source_reasons=[CandidateReason.FROM_KNOWLEDGE],
                    supporting_knowledge_ids=[item.get("id", "")],
                    reasoning=f"Suggested by knowledge item: {item.get('title', '')}",
                    estimated_effect=item.get("expected_effect"),
                )
                candidates.append(candidate)

        return candidates

    def _generate_context_candidates(
        self,
        intent: UniversalProductionIntent,
        episode_context: Dict[str, Any]
    ) -> List[SemanticCandidate]:
        """Generate candidates from learned episode patterns."""
        candidates = []

        for strategy in episode_context.get("learned_strategies", []):
            candidate = SemanticCandidate(
                candidate_id=f"ctx_{strategy.get('intent_pattern', 'unknown')}_{id(strategy)}",
                label=f"Apply learned strategy: {strategy.get('candidate_type', 'approach')}",
                target_concept=strategy.get("intent_pattern", ""),
                operation=strategy.get("candidate_type"),
                confidence=strategy.get("confidence", 0.7),
                source_reasons=[CandidateReason.FROM_EPISODE_PATTERN],
                supporting_episodes=[],  # Would be populated with actual episode IDs
                reasoning=strategy.get("reasoning", ""),
                status=CandidateStatus.VIABLE,
            )

            candidates.append(candidate)

        return candidates

    def _rank_candidates(
        self,
        candidates: List[SemanticCandidate],
        intent: UniversalProductionIntent
    ) -> List[Tuple[SemanticCandidate, float]]:
        """
        Rank candidates by appropriateness.

        Scoring factors:
        - Confidence
        - Support from knowledge/episodes
        - Constraint satisfaction
        - Status
        """
        scored = []

        for candidate in candidates:
            score = candidate.confidence  # Base score

            # Boost for multiple sources
            score += len(candidate.source_reasons) * 0.05

            # Boost for knowledge/episode support
            score += min(len(candidate.supporting_knowledge_ids) * 0.03, 0.2)
            score += min(len(candidate.supporting_episodes) * 0.03, 0.2)

            # Penalize risky candidates
            if candidate.status == CandidateStatus.RISKY:
                score *= 0.8
            elif candidate.status == CandidateStatus.UNKNOWN:
                score *= 0.6
            elif candidate.status == CandidateStatus.CONTRADICTED:
                score *= 0.3

            # Normalize to 0-1
            score = min(max(score, 0.0), 1.0)

            scored.append((candidate, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _log_reasoning(self, step: str) -> None:
        """Log a reasoning step."""
        self.reasoning_steps.append(step)


def integrate_semantic_reasoning(
    intent: UniversalProductionIntent,
    knowledge_items: Optional[List[Dict[str, Any]]] = None,
    episode_bridge: Optional[EpisodeContextBridge] = None,
) -> SemanticReasoningResult:
    """
    Top-level function to perform full semantic reasoning.

    Args:
        intent: Universal production intent
        knowledge_items: Optional retrieved knowledge items
        episode_bridge: Optional episode context bridge

    Returns:
        SemanticReasoningResult with candidates and reasoning chain
    """
    engine = SemanticReasoningEngine(episode_bridge)
    return engine.reason_about_intent(intent, knowledge_items)
