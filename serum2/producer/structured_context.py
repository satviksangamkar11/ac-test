"""Structured production context for P7 contextual policy — generic dimensions only.

Context informs candidate preference WITHOUT creating hardcoded parameter mappings.

Allowed dimensions:
  - role (e.g., "bass", "melody", "pad")
  - genre (e.g., "house", "ambient", "dnb")
  - subgenre
  - artist_style
  - technique (e.g., "filtering", "modulation", "fm")
  - era
  - objective

Prohibited:
  - Fixed parameter values
  - Target-specific rules
  - Hardcoded genre→parameter mappings
  - Hardcoded artist→parameter mappings
  - Hardcoded technique→parameter mappings

Context is preference input, not authority. It cannot:
  - Create capability
  - Bypass Capability Resolution
  - Bypass Admission
  - Replace target identity
  - Directly execute

Confidence/uncertainty is explicit. Missing context remains UNKNOWN rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class StructuredProductionContext:
    """Generic structured context for advisory candidate preference.

    Immutable. Fields are optional. Unknown/missing dimensions remain explicit.
    """

    # Core musical role
    role: Optional[str] = None
    role_confidence: float = 0.0
    role_provenance: Optional[Dict[str, Any]] = None

    # Musical genre/era context
    genre: Optional[str] = None
    genre_confidence: float = 0.0
    genre_provenance: Optional[Dict[str, Any]] = None

    subgenre: Optional[str] = None
    subgenre_confidence: float = 0.0
    subgenre_provenance: Optional[Dict[str, Any]] = None

    era: Optional[str] = None
    era_confidence: float = 0.0
    era_provenance: Optional[Dict[str, Any]] = None

    # Artist/style reference
    artist_style: Optional[str] = None
    artist_style_confidence: float = 0.0
    artist_style_provenance: Optional[Dict[str, Any]] = None

    # Technique/method
    technique: Optional[str] = None
    technique_confidence: float = 0.0
    technique_provenance: Optional[Dict[str, Any]] = None

    # Objective/goal
    objective: Optional[str] = None
    objective_confidence: float = 0.0
    objective_provenance: Optional[Dict[str, Any]] = None

    # Global provenance
    provenance: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = "context_v1.p7"

    def __post_init__(self):
        # Deep-freeze provenance for immutability
        from serum2.producer.skill_library import _freeze
        for f in ("role_provenance", "genre_provenance", "subgenre_provenance",
                  "era_provenance", "artist_style_provenance", "technique_provenance",
                  "provenance"):
            val = getattr(self, f)
            if val:
                object.__setattr__(self, f, _freeze(val))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "role_confidence": self.role_confidence,
            "role_provenance": dict(self.role_provenance) if self.role_provenance else None,
            "genre": self.genre,
            "genre_confidence": self.genre_confidence,
            "genre_provenance": dict(self.genre_provenance) if self.genre_provenance else None,
            "subgenre": self.subgenre,
            "subgenre_confidence": self.subgenre_confidence,
            "subgenre_provenance": dict(self.subgenre_provenance) if self.subgenre_provenance else None,
            "era": self.era,
            "era_confidence": self.era_confidence,
            "era_provenance": dict(self.era_provenance) if self.era_provenance else None,
            "artist_style": self.artist_style,
            "artist_style_confidence": self.artist_style_confidence,
            "artist_style_provenance": dict(self.artist_style_provenance) if self.artist_style_provenance else None,
            "technique": self.technique,
            "technique_confidence": self.technique_confidence,
            "technique_provenance": dict(self.technique_provenance) if self.technique_provenance else None,
            "objective": self.objective,
            "objective_confidence": self.objective_confidence,
            "objective_provenance": dict(self.objective_provenance) if self.objective_provenance else None,
            "provenance": dict(self.provenance),
            "schema_version": self.schema_version
        }


class ContextPolicy:
    """Policy interface for context-informed candidate preference.

    Returns advisory preference information, never authority or execution directives.
    """

    def preference(self, candidate: Dict[str, Any], context: StructuredProductionContext,
                   evidence: Any = None) -> Dict[str, Any]:
        """Compute preference score given candidate + context.

        Args:
            candidate: candidate strategy structure
            context: structured production context
            evidence: optional prior evidence

        Returns:
            {
                "score": float [0, 1],
                "reasoning": str,
                "affected_dimensions": [list of context dims that affected score],
                "references": [evidence ids]
            }

        Returns ONLY advisory information. Never authority, capability, admission, or execution.
        """
        raise NotImplementedError()


class DeterministicContextPolicy(ContextPolicy):
    """First deterministic policy: simple dimension weighting.

    No LLM, no embeddings, no learned parameters. Pure generic logic.
    """

    def preference(self, candidate: Dict[str, Any], context: StructuredProductionContext,
                   evidence: Any = None) -> Dict[str, Any]:
        """Score based on context dimension presence and confidence.

        More dimensions present = higher preference. Confidence amplifies.
        No target/parameter mapping; no hardcoding.
        """
        score = 0.0
        affected = []

        # Each context dimension that is known adds to preference
        dimensions = [
            ("role", context.role, context.role_confidence),
            ("genre", context.genre, context.genre_confidence),
            ("subgenre", context.subgenre, context.subgenre_confidence),
            ("era", context.era, context.era_confidence),
            ("artist_style", context.artist_style, context.artist_style_confidence),
            ("technique", context.technique, context.technique_confidence),
            ("objective", context.objective, context.objective_confidence),
        ]

        for dim_name, dim_value, dim_conf in dimensions:
            if dim_value is not None and dim_conf > 0.0:
                score += dim_conf / 7.0  # Average contribution per dimension
                affected.append(dim_name)

        return {
            "score": min(1.0, score),
            "reasoning": f"Context score from {len(affected)} dimension(s)",
            "affected_dimensions": affected,
            "references": []
        }
