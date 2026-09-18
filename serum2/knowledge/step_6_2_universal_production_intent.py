"""
STEP 6.2 — UNIVERSAL PRODUCTION INTENT MODEL

Canonical backend-independent representation of producer intent.

Bridges user goals to knowledge retrieval and advisory reasoning, while
remaining completely separate from authority, execution, and measurement
decisions.

Key principle:
    INTENT ≠ TARGET ≠ AUTHORITY ≠ MEASUREMENT

Intent reconciles existing models:
    - serum2/knowledge/semantic_intent_resolver.py (concept mappings)
    - serum2/knowledge/intent_bridge.py (candidate operations)
    - serum2/producer/diagnosis.py (ProducerGoal)

into one canonical representation.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class IntentResolutionStatus(Enum):
    """Status of intent resolution."""
    RESOLVED = "resolved"  # Unambiguous meaning
    AMBIGUOUS = "ambiguous"  # Multiple interpretations
    UNSUPPORTED = "unsupported"  # Cannot be resolved
    PARTIAL = "partial"  # Some dimensions resolved


class SemanticDirection(Enum):
    """Semantic direction without numeric magnitude."""
    INCREASE = "increase"
    DECREASE = "decrease"
    HIGHER = "higher"
    LOWER = "lower"
    LONGER = "longer"
    SHORTER = "shorter"
    TIGHTER = "tighter"
    LOOSER = "looser"
    BRIGHTER = "brighter"
    DARKER = "darker"
    LOUDER = "louder"
    QUIETER = "quieter"
    SOFTER = "softer"
    HARDER = "harder"


class MusicalRole(Enum):
    """Musical role context (optional)."""
    BASS = "bass"
    PAD = "pad"
    LEAD = "lead"
    PLUCK = "pluck"
    PERCUSSION = "percussion"
    MELODY = "melody"
    HARMONY = "harmony"
    TEXTURE = "texture"


class MusicalContext(Enum):
    """Musical production context (optional)."""
    AMBIENT = "ambient"
    DANCE = "dance"
    FILM = "film"
    CLASSICAL = "classical"
    ELECTRONIC = "electronic"
    ACOUSTIC = "acoustic"
    LIVE = "live"


@dataclass
class AmbiguityInfo:
    """Represents ambiguity in intent resolution."""
    is_ambiguous: bool
    candidate_interpretations: List[str] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass
class IntentResolutionProvenance:
    """Tracks how intent was resolved."""
    resolution_method: str  # "keyword_match", "semantic_map", "user_explicit"
    source_field: str  # Which part of user text triggered this
    matched_keywords: List[str] = field(default_factory=list)
    reasoning: Optional[str] = None


@dataclass
class UniversalProductionIntent:
    """
    Canonical universal production intent.

    Backend-independent representation of what the producer wants to achieve.
    Does NOT contain:
        - backend targets (Serum parameters)
        - concrete mutation values
        - authoritative measurement IDs
        - CapabilityContract references

    All fields are optional. Missing information stays missing.
    """

    # ==== CORE INTENT ====
    original_user_request: str
    """The exact user text, unchanged."""

    musical_objective: Optional[str] = None
    """What the user wants to achieve (e.g., 'tighter bass articulation')."""

    desired_change: Optional[str] = None
    """How the user wants things to change (e.g., 'shorter note tail')."""

    # ==== SEMANTIC DIMENSIONS ====
    target_concept: Optional[str] = None
    """Universal music concept (e.g., 'note-release', 'brightness', 'attack').
    Does NOT name a backend target."""

    semantic_direction: Optional[SemanticDirection] = None
    """Direction without magnitude (increase/decrease/shorter/longer/etc)."""

    operation: Optional[str] = None
    """The intended operation (e.g., 'shorten', 'increase', 'reduce').
    Universal, not backend-specific."""

    # ==== CONTEXT ====
    role: Optional[MusicalRole] = None
    """Musical role this applies to (bass, lead, pad, etc)."""

    instrument: Optional[str] = None
    """Instrument or synth type (optional, e.g., 'synth', 'piano')."""

    musical_context: Optional[MusicalContext] = None
    """Production context (ambient, dance, film, etc)."""

    genre: Optional[str] = None
    """Genre hint (optional)."""

    style: Optional[str] = None
    """Style descriptor (optional)."""

    # ==== CONSTRAINTS ====
    constraints: List[str] = field(default_factory=list)
    """Optional constraints (e.g., 'maintain bass weight', 'don't lose sustain')."""

    # ==== VERIFICATION ====
    verification_goal: Optional[str] = None
    """What the producer hopes to observe/hear (NOT the authoritative measurement).
    Examples: 'shorter tail', 'snappier attack', 'less muddy'.
    This is aspirational, not measurement authority."""

    expected_effect: Optional[str] = None
    """What the user expects to happen (optional)."""

    # ==== AMBIGUITY ====
    ambiguity: Optional[AmbiguityInfo] = None
    """If intent is ambiguous, describe alternatives and reasons."""

    # ==== CONFIDENCE ====
    confidence: float = 0.5
    """Confidence in this intent interpretation (0.0-1.0)."""

    resolution_status: IntentResolutionStatus = IntentResolutionStatus.RESOLVED
    """Whether this intent is resolved, ambiguous, etc."""

    # ==== PROVENANCE ====
    provenance: Optional[IntentResolutionProvenance] = None
    """How this intent was resolved from user text."""

    # ==== BACKEND HINT (OPTIONAL, NON-AUTHORITATIVE) ====
    backend_hint: Optional[str] = None
    """Optional hint about preferred backend (e.g., 'Serum').
    Does NOT authorize execution or control values."""

    # ==== AUXILIARY ====
    timestamp: Optional[str] = None
    """When this intent was created (ISO 8601)."""

    notes: Optional[str] = None
    """Additional context or reasoning."""

    def is_valid(self) -> bool:
        """Check if intent has sufficient information."""
        return bool(
            self.original_user_request and
            (self.musical_objective or self.desired_change or self.target_concept)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = {}
        for key, value in asdict(self).items():
            if value is None:
                continue
            if isinstance(value, (Enum)):
                data[key] = value.value
            elif isinstance(value, list) and not value:
                continue
            else:
                data[key] = value
        return data


@dataclass
class UniversalProductionIntentCandidate:
    """A specific candidate interpretation of user intent."""

    intent: UniversalProductionIntent
    """The resolved intent."""

    source_knowledge_item_ids: List[str] = field(default_factory=list)
    """Knowledge items that support this interpretation."""

    source_episode_ids: List[str] = field(default_factory=list)
    """Episodes that support this interpretation."""

    advisory_ranking: Optional[float] = None
    """Score for advisory reasoning (0.0-1.0), if ranked against alternatives."""

    rationale: Optional[str] = None
    """Why this candidate was selected (for decision trace)."""


class UniversalIntentResolver:
    """
    Reconciles existing intent models into canonical form.

    Accepts input from:
    - user natural language
    - semantic_intent_resolver.py mappings
    - intent_bridge.py candidate operations

    Produces: UniversalProductionIntent (backend-independent, universal)
    """

    # Reconciled semantic mappings (from semantic_intent_resolver.py)
    SEMANTIC_MAP = {
        # Release/sustain concepts
        ("release", "shorter"): {
            "target_concept": "note-release",
            "semantic_direction": SemanticDirection.SHORTER,
            "operation": "shorten",
        },
        ("shorter", "bass"): {
            "target_concept": "note-release",
            "semantic_direction": SemanticDirection.SHORTER,
            "operation": "shorten",
        },
        ("bass", "tighter"): {
            "target_concept": "note-release",
            "semantic_direction": SemanticDirection.TIGHTER,
            "operation": "tighten",
        },
        ("sustain", "longer"): {
            "target_concept": "note-sustain",
            "semantic_direction": SemanticDirection.LONGER,
            "operation": "lengthen",
        },
        ("attack", "faster"): {
            "target_concept": "envelope-attack",
            "semantic_direction": SemanticDirection.SHORTER,
            "operation": "decrease",
        },
        ("attack", "slower"): {
            "target_concept": "envelope-attack",
            "semantic_direction": SemanticDirection.LONGER,
            "operation": "increase",
        },
        # Brightness concepts
        ("sound", "brighter"): {
            "target_concept": "brightness",
            "semantic_direction": SemanticDirection.BRIGHTER,
            "operation": "increase",
        },
        ("sound", "darker"): {
            "target_concept": "brightness",
            "semantic_direction": SemanticDirection.DARKER,
            "operation": "decrease",
        },
        # Volume concepts
        ("sound", "louder"): {
            "target_concept": "amplitude",
            "semantic_direction": SemanticDirection.LOUDER,
            "operation": "increase",
        },
        ("sound", "quieter"): {
            "target_concept": "amplitude",
            "semantic_direction": SemanticDirection.QUIETER,
            "operation": "decrease",
        },
    }

    def resolve_from_text(
        self,
        user_text: str,
        role: Optional[MusicalRole] = None,
        context: Optional[MusicalContext] = None,
    ) -> UniversalProductionIntent:
        """
        Resolve user text to universal intent.

        Args:
            user_text: e.g., "Make the bass sound tighter"
            role: optional musical role
            context: optional production context

        Returns:
            UniversalProductionIntent (backend-independent)
        """
        text_lower = user_text.lower()

        intent = UniversalProductionIntent(
            original_user_request=user_text,
            role=role,
            musical_context=context,
        )

        # Try to match keywords against semantic map
        matched = False
        for (keyword1, keyword2), semantic_info in self.SEMANTIC_MAP.items():
            if keyword1 in text_lower and keyword2 in text_lower:
                intent.target_concept = semantic_info.get("target_concept")
                intent.semantic_direction = semantic_info.get("semantic_direction")
                intent.operation = semantic_info.get("operation")
                matched = True
                break

        if matched:
            # Extract objective
            if "bass" in text_lower:
                intent.role = MusicalRole.BASS
                if intent.operation == "shorten":
                    intent.musical_objective = "tighter bass articulation"
                    intent.desired_change = "shorter note tail"
                elif intent.operation == "lengthen":
                    intent.musical_objective = "longer bass sustain"
                    intent.desired_change = "extended note tail"

            intent.resolution_status = IntentResolutionStatus.RESOLVED
            intent.confidence = 0.8
        else:
            # Could not resolve
            intent.resolution_status = IntentResolutionStatus.AMBIGUOUS
            intent.confidence = 0.3
            intent.ambiguity = AmbiguityInfo(
                is_ambiguous=True,
                candidate_interpretations=["unknown"],
                reason="Keywords do not match semantic map"
            )

        return intent


# COMPATIBILITY: Bridge to existing ProducerGoal
def intent_to_producer_goal_requirements(
    intent: UniversalProductionIntent
) -> Dict[str, Any]:
    """
    Extract what a ProducerGoal would need from this intent.

    Returns a dict with:
        - suggested_semantic_target
        - suggested_metric_direction
        - confidence

    This is ADVISORY. ProducerGoal still gets filled by downstream reasoning.
    """
    requirements = {
        "suggested_semantic_target": None,
        "suggested_metric_direction": None,
        "confidence": intent.confidence,
    }

    # Map semantic direction to metric direction
    if intent.semantic_direction == SemanticDirection.SHORTER:
        requirements["suggested_metric_direction"] = "lower_is_better"  # shorter tail
    elif intent.semantic_direction == SemanticDirection.LONGER:
        requirements["suggested_metric_direction"] = "higher_is_better"  # longer tail
    elif intent.semantic_direction in [SemanticDirection.LOUDER, SemanticDirection.BRIGHTER]:
        requirements["suggested_metric_direction"] = "higher_is_better"
    elif intent.semantic_direction in [SemanticDirection.QUIETER, SemanticDirection.DARKER]:
        requirements["suggested_metric_direction"] = "lower_is_better"

    return requirements
