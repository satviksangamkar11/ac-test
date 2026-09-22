"""B1.4: Context Extraction (REQUEST METADATA).

Extract and normalize request context for later reasoning phases (ranking, policy).
Context matters for future Brain phases; capture it now in canonical form.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import re


@dataclass
class RequestContext:
    """Extracted and normalized request context.

    Separates what is being asked from how it is being asked.
    """

    # Explicit intent
    explicit_target: Optional[str] = None              # e.g., "env1.decay"
    semantic_target_hint: Optional[str] = None         # e.g., "release" (from natural language)

    # Implicit scope (what/where)
    implicit_scope: Optional[str] = None               # e.g., "the filter", "this oscillator", "global"
    implicit_scope_type: Optional[str] = None          # "filter", "oscillator", "global", "unknown"

    # Temporal/sequential context
    time_marker: Optional[str] = None                  # e.g., "at the end", "gradually", "now"

    # Descriptive/audio context (for later grounding phases)
    audio_descriptors: List[str] = field(default_factory=list)  # ["dark", "warm", "tight", "wide", etc.]

    # Episode/tutorial context
    tutorial_context: Optional[str] = None             # episode ID, frame range, etc.

    # Confidence and audit
    confidence: Dict[str, float] = field(default_factory=dict)  # {field: confidence}
    extraction_chain: List[str] = field(default_factory=list)   # audit trail


class ContextExtractor:
    """B1.4: Extract context from ProducerRequest.

    Maps natural language context markers to canonical context representation.
    """

    # Frozen scope markers (not extensible)
    _FILTER_SCOPE_WORDS = frozenset(("filter", "cutoff", "resonance", "pole", "highpass", "lowpass"))
    _OSCILLATOR_SCOPE_WORDS = frozenset(("oscillator", "osc", "wavetable", "wt", "unison", "detune"))
    _GLOBAL_SCOPE_WORDS = frozenset(("global", "master", "all", "entire"))
    _ENVELOPE_SCOPE_WORDS = frozenset(("envelope", "env", "adsr", "attack", "decay", "release"))
    _LFO_SCOPE_WORDS = frozenset(("lfo", "modulation", "mod", "rate", "sync"))

    # Audio descriptors (for later P6 grounding)
    _AUDIO_DESCRIPTORS = frozenset((
        "dark", "bright", "warm", "cold", "harsh", "soft", "tight", "wide",
        "aggressive", "gentle", "smooth", "rough", "hollow", "full", "thin",
        "thick", "crisp", "muted", "clear", "muddy", "clean", "dirty"
    ))

    # Time markers
    _TIME_MARKERS = {
        "at the start": "start",
        "at the beginning": "start",
        "initially": "start",
        "at the end": "end",
        "finally": "end",
        "gradually": "gradual",
        "slowly": "gradual",
        "immediately": "immediate",
        "now": "immediate",
    }

    def __init__(self):
        pass

    def extract(self, user_intent: str, semantic_target: Optional[str] = None, episode_id: Optional[str] = None) -> RequestContext:
        """Extract context from a production request.

        Args:
            user_intent: User's natural language intent
            semantic_target: Optional semantic target hint (from request)
            episode_id: Optional episode/run ID for tutorial context

        Returns:
            RequestContext with extracted fields and audit trail
        """
        intent_lower = user_intent.lower()
        chain = [f"extract(intent={user_intent!r}, semantic={semantic_target})"]
        ctx = RequestContext(
            semantic_target_hint=semantic_target,
            tutorial_context=episode_id,
        )

        # Extract explicit target (dotted names like "env1.decay", "filter1.cutoff")
        explicit = self._find_explicit_target(user_intent)
        if explicit:
            ctx.explicit_target = explicit
            chain.append(f"explicit_target: {explicit}")
            ctx.confidence["explicit_target"] = 0.95

        # Extract implicit scope
        scope_type, scope_name = self._find_implicit_scope(intent_lower)
        if scope_type:
            ctx.implicit_scope = scope_name
            ctx.implicit_scope_type = scope_type
            chain.append(f"implicit_scope: {scope_type}")
            ctx.confidence["implicit_scope"] = 0.75 if scope_name else 0.60

        # Extract audio descriptors (for P6 grounding phase)
        descriptors = self._find_audio_descriptors(intent_lower)
        if descriptors:
            ctx.audio_descriptors = descriptors
            chain.append(f"audio_descriptors: {descriptors}")
            ctx.confidence["audio_descriptors"] = 0.70

        # Extract time markers
        time_marker = self._find_time_marker(intent_lower)
        if time_marker:
            ctx.time_marker = time_marker
            chain.append(f"time_marker: {time_marker}")
            ctx.confidence["time_marker"] = 0.80

        ctx.extraction_chain = chain
        return ctx

    # ---- Helpers ----

    def _find_explicit_target(self, text: str) -> Optional[str]:
        """Find explicit dotted target names like 'env1.decay', 'Filter1.Cutoff'."""
        # Pattern: word.word (case-insensitive)
        matches = re.findall(r"\b([a-zA-Z0-9]+\.[a-zA-Z0-9_]+)\b", text)
        if matches:
            # Return the first match
            return matches[0]
        return None

    def _find_implicit_scope(self, text_lower: str) -> tuple[Optional[str], Optional[str]]:
        """Infer implicit scope from context words.

        Returns: (scope_type, scope_name)
        e.g., ("filter", "the filter"), ("oscillator", "oscillator A")
        """

        # Filter scope
        for word in self._FILTER_SCOPE_WORDS:
            if word in text_lower:
                # Try to find which filter (1 or 2)
                if "filter 2" in text_lower or "filter2" in text_lower or "second filter" in text_lower:
                    return ("filter", "filter2")
                else:
                    return ("filter", "filter1")  # default

        # Oscillator scope
        for word in self._OSCILLATOR_SCOPE_WORDS:
            if word in text_lower:
                # Try to find which osc (A, B, C, or generic)
                if "osc a" in text_lower or "oscillator a" in text_lower:
                    return ("oscillator", "oscA")
                elif "osc b" in text_lower or "oscillator b" in text_lower:
                    return ("oscillator", "oscB")
                elif "osc c" in text_lower or "oscillator c" in text_lower:
                    return ("oscillator", "oscC")
                else:
                    return ("oscillator", "osc")  # generic

        # Envelope scope
        for word in self._ENVELOPE_SCOPE_WORDS:
            if word in text_lower:
                if "env 1" in text_lower or "envelope 1" in text_lower:
                    return ("envelope", "env1")
                elif "env 2" in text_lower or "envelope 2" in text_lower:
                    return ("envelope", "env2")
                else:
                    return ("envelope", "env")  # generic

        # LFO scope
        for word in self._LFO_SCOPE_WORDS:
            if word in text_lower:
                if "lfo 1" in text_lower:
                    return ("lfo", "lfo1")
                elif "lfo 2" in text_lower:
                    return ("lfo", "lfo2")
                else:
                    return ("lfo", "lfo")  # generic

        # Global scope
        for word in self._GLOBAL_SCOPE_WORDS:
            if word in text_lower:
                return ("global", "global")

        return (None, None)

    def _find_audio_descriptors(self, text_lower: str) -> List[str]:
        """Extract audio descriptor words for later grounding."""
        found = []
        for desc in self._AUDIO_DESCRIPTORS:
            if desc in text_lower:
                found.append(desc)
        return found

    def _find_time_marker(self, text_lower: str) -> Optional[str]:
        """Extract temporal context markers."""
        for phrase, marker in self._TIME_MARKERS.items():
            if phrase in text_lower:
                return marker
        return None
