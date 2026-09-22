"""P7.1: Structured production context and deterministic policy.

Context is a preference signal, never parameter mapping or capability creation.
Frozen dimensions: role, genre, subgenre, artist_style, technique, era, objective.

Context CANNOT:
  - Create candidates
  - Replace target identity
  - Create capability
  - Bypass Capability Resolution
  - Bypass Admission
  - Execute

Context CAN:
  - Inform same-target candidate preference
  - Provide audit trail via provenance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Tuple


@dataclass(frozen=True)
class StructuredProductionContext:
    """Generic structured context for advisory candidate preference.

    Immutable. Seven frozen dimensions. Unknown remains explicit (None, confidence=0.0).
    No parameter values, no target mappings, no execution directives.
    """

    role: Optional[str] = None
    genre: Optional[str] = None
    subgenre: Optional[str] = None
    artist_style: Optional[str] = None
    technique: Optional[str] = None
    era: Optional[str] = None
    objective: Optional[str] = None

    # Confidence for each dimension (0.0 = unknown)
    role_confidence: float = 0.0
    genre_confidence: float = 0.0
    subgenre_confidence: float = 0.0
    artist_style_confidence: float = 0.0
    technique_confidence: float = 0.0
    era_confidence: float = 0.0
    objective_confidence: float = 0.0

    # Optional provenance metadata
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Deep-freeze provenance for immutability
        from serum2.producer.skill_library import _freeze
        if self.provenance:
            object.__setattr__(self, "provenance", _freeze(self.provenance))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "genre": self.genre,
            "subgenre": self.subgenre,
            "artist_style": self.artist_style,
            "technique": self.technique,
            "era": self.era,
            "objective": self.objective,
            "role_confidence": self.role_confidence,
            "genre_confidence": self.genre_confidence,
            "subgenre_confidence": self.subgenre_confidence,
            "artist_style_confidence": self.artist_style_confidence,
            "technique_confidence": self.technique_confidence,
            "era_confidence": self.era_confidence,
            "objective_confidence": self.objective_confidence,
            "provenance": dict(self.provenance) if self.provenance else {}
        }


@dataclass(frozen=True)
class ContextPreference:
    """Advisory preference signal from context policy.

    Contains score_delta, reasoning, and provenance. Never authority.
    """

    score_delta: float
    reasons: Tuple[str, ...] = ()
    provenance: Tuple[str, ...] = ()


class ContextPolicy(Protocol):
    """Interface for context-informed candidate preference.

    Must return advisory-only preference information.
    Cannot access capability, admission, execution, or routing.
    """

    def preference(
        self,
        candidate: Dict[str, Any],
        context: StructuredProductionContext,
        evidence: Any = None,
    ) -> ContextPreference:
        """Compute preference given candidate + context.

        Args:
            candidate: candidate from P4
            context: structured production context
            evidence: optional prior evidence

        Returns:
            ContextPreference with score_delta, reasons, provenance.
            Never contains execution, routing, admission, or capability info.
        """
        ...


class DeterministicContextPolicy:
    """Deterministic policy: dimension presence → preference.

    No LLM, embeddings, or learned parameters. Generic dimension weighting.
    More present dimensions = higher preference. Confidence amplifies.
    """

    def preference(
        self,
        candidate: Dict[str, Any],
        context: StructuredProductionContext,
        evidence: Any = None,
    ) -> ContextPreference:
        """Score based on context dimension presence and confidence.

        Each non-None dimension with confidence > 0.0 contributes equally.
        Score is normalized [0, 1].
        """
        score_delta = 0.0
        affected = []

        dimensions = [
            ("role", context.role, context.role_confidence),
            ("genre", context.genre, context.genre_confidence),
            ("subgenre", context.subgenre, context.subgenre_confidence),
            ("artist_style", context.artist_style, context.artist_style_confidence),
            ("technique", context.technique, context.technique_confidence),
            ("era", context.era, context.era_confidence),
            ("objective", context.objective, context.objective_confidence),
        ]

        for dim_name, dim_value, dim_conf in dimensions:
            if dim_value is not None and dim_conf > 0.0:
                # Contribution proportional to confidence
                score_delta += dim_conf / 7.0
                affected.append(dim_name)

        score_delta = min(1.0, score_delta)
        reasons = tuple(
            f"context dimension {dim} present" for dim in affected
        ) if affected else ("no context dimensions present",)

        return ContextPreference(
            score_delta=score_delta,
            reasons=reasons,
            provenance=("deterministic_context_policy",)
        )
