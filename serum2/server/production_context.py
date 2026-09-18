"""ProductionContext — advisory musical context for one production run.

Advisory only. Nothing here grants execution authority; all authority remains
in the existing admission chain (6.6 → 6.7 → 6.8).

Flow:
  transcript → build_from_transcript() → ProductionContext
      → to_musical_context_string()
      → ProducerRequest.musical_context (free-text advisory field)
      → UniversalProductionIntent.musical_objective (inside brain)

The brain uses musical_objective in semantic reasoning; it does NOT map
any genre or artist directly to Serum parameters.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class ProductionContext:
    """Advisory musical context for a production run.

    All fields optional — only present when derivable from transcript
    or supplied explicitly by the caller.
    """
    role: Optional[str] = None           # "bass" | "pad" | "lead" | "pluck"
    character: Optional[str] = None      # "dark" | "bright" | "warm" | "gritty"
    genre: Optional[str] = None          # e.g. "melodic techno"
    subgenre: Optional[str] = None       # e.g. "dark minimal"
    artist_reference: Optional[str] = None   # e.g. "Burial"
    track_reference: Optional[str] = None    # e.g. "Archangel"
    era: Optional[str] = None            # e.g. "2000s"
    techniques: List[str] = field(default_factory=list)   # ["reverb", "granular"]
    reference_sources: List[str] = field(default_factory=list)  # source_ids

    def to_musical_context_string(self) -> str:
        """Serialize to free-text string for ProducerRequest.musical_context.

        The brain treats this as an advisory musical objective, not a command.
        Format: '<role> <character> | genre: <g> | artist: <a> | ...'
        """
        parts = []
        if self.role or self.character:
            parts.append(" ".join(filter(None, [self.role, self.character])))
        if self.genre:
            sub = f" ({self.subgenre})" if self.subgenre else ""
            parts.append(f"genre: {self.genre}{sub}")
        if self.artist_reference:
            parts.append(f"artist: {self.artist_reference}")
        if self.track_reference:
            parts.append(f"track: {self.track_reference}")
        if self.era:
            parts.append(f"era: {self.era}")
        if self.techniques:
            parts.append(f"techniques: {', '.join(self.techniques)}")
        return " | ".join(parts) if parts else "sound design"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Transcript-based builder (keyword extraction — advisory, not authoritative)
# ---------------------------------------------------------------------------

_GENRE_PATTERNS = [
    # longer patterns first to avoid partial matches
    (["melodic techno", "melodic-techno"],    "melodic techno"),
    (["dark techno", "industrial techno"],    "techno", "dark minimal"),
    (["techno", "berlin", "minimal techno"],  "techno"),
    (["deep house", "deep-house"],            "house", "deep"),
    (["tech house", "tech-house"],            "house", "tech"),
    (["house music", "house"],                "house"),
    (["drum and bass", "drum & bass", "dnb"], "drum and bass"),
    (["dubstep", "wobble bass"],              "dubstep"),
    (["ambient", "drone", "soundscape"],      "ambient"),
    (["trap", "808 trap"],                    "hip hop", "trap"),
    (["lo-fi", "lofi", "lo fi"],             "hip hop", "lo-fi"),
    (["hip hop", "hip-hop", "hiphop"],        "hip hop"),
    (["trance", "psytrance"],                 "trance"),
]

_TECHNIQUE_KEYWORDS = [
    "reverb", "delay", "distortion", "saturation", "compression",
    "sidechain", "filter", "lfo", "modulation", "granular", "fm",
    "wavetable", "unison", "detune", "chord", "arpeggio", "glide",
    "portamento", "velocity", "automation", "envelope",
]

_ERA_PATTERNS = [
    (r"\b(198\d)s?\b|\b80s\b",   "1980s"),
    (r"\b(199\d)s?\b|\b90s\b",   "1990s"),
    (r"\b(200\d)s?\b|\b2000s\b", "2000s"),
    (r"\b(201\d)s?\b|\b2010s\b", "2010s"),
    (r"\b(202\d)s?\b|\b2020s\b", "2020s"),
]


def build_from_transcript(
    transcript_text: str,
    *,
    role: Optional[str] = None,
    character: Optional[str] = None,
    artist_reference: Optional[str] = None,
    track_reference: Optional[str] = None,
    source_id: Optional[str] = None,
) -> ProductionContext:
    """Build ProductionContext from transcript text + optional explicit overrides.

    Keyword extraction is advisory — produces context for brain reasoning,
    never maps directly to Serum parameters.
    """
    low = transcript_text.lower()

    # Genre / subgenre
    genre = subgenre = None
    for entry in _GENRE_PATTERNS:
        keywords, *rest = entry
        if any(kw in low for kw in keywords):
            genre = rest[0]
            subgenre = rest[1] if len(rest) > 1 else None
            break

    # Era
    era = None
    for pattern, label in _ERA_PATTERNS:
        if re.search(pattern, low):
            era = label
            break

    # Techniques mentioned
    techniques = [t for t in _TECHNIQUE_KEYWORDS if t in low]

    ctx = ProductionContext(
        role=role,
        character=character,
        genre=genre,
        subgenre=subgenre,
        artist_reference=artist_reference,
        track_reference=track_reference,
        era=era,
        techniques=techniques[:6],  # cap at 6; advisory, not exhaustive
        reference_sources=[source_id] if source_id else [],
    )
    return ctx
