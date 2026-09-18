"""
Semantic intent resolver: human producer language → existing knowledge mapping

Maps producer intent to existing KnowledgeItems/hypotheses using deterministic
semantic vocabulary, without requiring lexical overlap with YouTube transcripts.

Provenance always terminates at actual repository artifacts.
"""
import json
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path


@dataclass
class IntentResolution:
    """Result of resolving producer intent to knowledge."""
    intent: str
    semantic_concept: str
    semantic_target: str
    hypothesis_ids: List[str]  # IDs of matching hypotheses in knowledge
    knowledge_item_ids: List[str]  # IDs of knowledge items supporting this
    confidence: float  # 0.0-1.0
    resolution_status: str  # RESOLVED, AMBIGUOUS, UNSUPPORTED
    provenance_reason: str  # Why this resolution was chosen
    measurement_metric: Optional[str] = None  # Associated metric if known


# Semantic intent mapping: human concepts → semantic targets + context
INTENT_SEMANTIC_MAP = {
    # Attack/envelope onset concepts
    ("attack", "slower"): {
        "semantic_concept": "envelope onset time increase",
        "semantic_target": "Env1.Attack",
        "confidence": 0.95,
    },
    ("attack", "faster"): {
        "semantic_concept": "envelope onset time decrease",
        "semantic_target": "Env1.Attack",
        "confidence": 0.95,
    },
    # Pitch/octave concepts
    ("oscillator", "octave", "higher"): {
        "semantic_concept": "oscillator pitch by octave up",
        "semantic_target": "OSC1.Octave",
        "confidence": 0.95,
    },
    ("oscillator", "octave", "lower"): {
        "semantic_concept": "oscillator pitch by octave down",
        "semantic_target": "OSC1.Octave",
        "confidence": 0.95,
    },
    # Fine detune concepts
    ("oscillator", "detune"): {
        "semantic_concept": "oscillator fine pitch adjustment",
        "semantic_target": "OSC1.Detune",
        "confidence": 0.85,
    },
    # Volume/amplitude concepts
    ("sound", "quieter"): {
        "semantic_concept": "overall amplitude decrease",
        "semantic_target": "OSC1.Level",
        "confidence": 0.85,
    },
    ("sound", "louder"): {
        "semantic_concept": "overall amplitude increase",
        "semantic_target": "OSC1.Level",
        "confidence": 0.85,
    },
    # Frequency/brightness concepts
    ("sound", "brighter"): {
        "semantic_concept": "frequency spectrum shift upward",
        "semantic_target": "Filter.Cutoff",
        "confidence": 0.80,
    },
    ("sound", "darker"): {
        "semantic_concept": "frequency spectrum shift downward",
        "semantic_target": "Filter.Cutoff",
        "confidence": 0.80,
    },
    # Release/sustain concepts
    ("note", "sustain", "longer"): {
        "semantic_concept": "release tail duration increase",
        "semantic_target": "Env1.Release",
        "confidence": 0.95,
    },
}

# Measurement metric associations
METRIC_FOR_TARGET = {
    "Env1.Release": "tail_rms_db",
    "Env1.Attack": "rms_db",
    "OSC1.Octave": "pitch_shift_semitones",
    "OSC1.Detune": "pitch_shift_semitones",
    "OSC1.Level": "rms_db",
    "Filter.Cutoff": "spectral_centroid_hz",
}


def _tokenize_intent(intent: str) -> tuple:
    """Tokenize intent into lowercase words."""
    return tuple(w.lower() for w in intent.split())


def _match_intent_pattern(intent_tokens: tuple) -> Optional[tuple]:
    """
    Match intent tokens against known patterns.

    Returns the matching pattern tuple (e.g., ("attack", "slower")) or None.
    Uses longest-match-first to prefer more specific patterns.
    """
    # Sort by pattern length (descending) to prefer longer/more specific matches
    sorted_patterns = sorted(INTENT_SEMANTIC_MAP.keys(), key=len, reverse=True)

    for pattern in sorted_patterns:
        # Check if all pattern words appear in intent (order-insensitive)
        if all(word in intent_tokens for word in pattern):
            return pattern

    return None


def resolve_semantic_intent(
    human_intent: str,
    hypotheses_file: str,
    target_resolution_file: str,
) -> IntentResolution:
    """
    Resolve human producer intent to existing knowledge.

    Args:
        human_intent: Natural language intent (e.g., "make the attack slower")
        hypotheses_file: Path to yt_f507169bd7cb_hypotheses.json
        target_resolution_file: Path to yt_f507169bd7cb_target_resolution.json

    Returns:
        IntentResolution with status (RESOLVED/AMBIGUOUS/UNSUPPORTED) and provenance
    """
    # Load knowledge artifacts
    with open(hypotheses_file) as f:
        hypotheses_data = json.load(f)
    with open(target_resolution_file) as f:
        target_resolution_data = json.load(f)

    # Tokenize intent
    intent_tokens = _tokenize_intent(human_intent)

    # Match against semantic patterns
    pattern = _match_intent_pattern(intent_tokens)

    if pattern is None:
        return IntentResolution(
            intent=human_intent,
            semantic_concept="UNKNOWN",
            semantic_target="UNKNOWN",
            hypothesis_ids=[],
            knowledge_item_ids=[],
            confidence=0.0,
            resolution_status="UNSUPPORTED",
            provenance_reason=f"No semantic pattern matched intent tokens: {intent_tokens}",
        )

    # Look up semantic target from pattern
    mapping = INTENT_SEMANTIC_MAP[pattern]
    semantic_concept = mapping["semantic_concept"]
    semantic_target = mapping["semantic_target"]
    confidence = mapping["confidence"]

    # Verify knowledge support: find all hypotheses for this target
    matching_hypotheses = [
        h
        for h in hypotheses_data.get("hypotheses", [])
        if h.get("target") == semantic_target
    ]

    if not matching_hypotheses:
        # Target has no YouTube hypotheses
        return IntentResolution(
            intent=human_intent,
            semantic_concept=semantic_concept,
            semantic_target=semantic_target,
            hypothesis_ids=[],
            knowledge_item_ids=[],
            confidence=confidence,
            resolution_status="UNSUPPORTED",
            provenance_reason=f"Semantic target '{semantic_target}' has no YouTube hypotheses",
        )

    # Collect hypothesis and knowledge item IDs
    hypothesis_ids = [h.get("hypothesis_id") for h in matching_hypotheses]
    knowledge_item_ids = list(
        set(h.get("knowledge_item_id") for h in matching_hypotheses)
    )

    # Get measurement metric
    metric = METRIC_FOR_TARGET.get(semantic_target)

    return IntentResolution(
        intent=human_intent,
        semantic_concept=semantic_concept,
        semantic_target=semantic_target,
        hypothesis_ids=hypothesis_ids,
        knowledge_item_ids=knowledge_item_ids,
        confidence=confidence,
        resolution_status="RESOLVED",
        provenance_reason=f"Pattern '{pattern}' matched intent. {len(matching_hypotheses)} supporting hypotheses found.",
        measurement_metric=metric,
    )


def resolve_intent_batch(
    intents: List[str],
    hypotheses_file: str,
    target_resolution_file: str,
) -> List[IntentResolution]:
    """Resolve a batch of intents."""
    return [
        resolve_semantic_intent(intent, hypotheses_file, target_resolution_file)
        for intent in intents
    ]
