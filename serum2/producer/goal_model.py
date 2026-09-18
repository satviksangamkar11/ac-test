"""16.5.61: Goal Model — structured musical intent.

Represents what the user wants, NOT how to achieve it.

CRITICAL INVARIANT: The Goal Model NEVER contains Serum parameters.
Parameters belong downstream in the Compiler, not upstream in intent parsing.

Goal parsing pipeline:

    language → GoalModel (goal + characteristics)

The Goal Model is a contract that the Planner reads, not a control specification.

Characteristics are constrained to a closed vocabulary of musical dimensions:
  - character: musical quality words (dark, bright, warm, clean, etc.)
  - energy: absolute level (low, medium, high)
  - register: frequency range (sub, low, mid, high)
  - density: texture thickness (sparse, medium, dense)
  - attack: envelope shape (slow, medium, fast, punchy)
  - sustain_level: amplitude envelope sustain (short, medium, long)
  - spread: spatial width (mono, medium, wide)

Sources of characteristic values:
  1. Direct from user (e.g., "dark" in intent text)
  2. Derived from context (e.g., if role="bass" and section="intro", energy defaults to "low")
  3. Absent (unknown) — treated as unconstrained

The Planner will:
  1. Query the World Model for current role state
  2. Compare goal characteristics against measured/current characteristics
  3. Identify gaps (what is missing or contradictory)
  4. Map gaps to capability-backed actions
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class Character(str, Enum):
    """Musical quality descriptors."""
    DARK = "dark"
    BRIGHT = "bright"
    WARM = "warm"
    CLEAN = "clean"
    PUNCHY = "punchy"
    SMOOTH = "smooth"
    HARSH = "harsh"
    SOFT = "soft"
    AGGRESSIVE = "aggressive"
    MELLOW = "mellow"


class Energy(str, Enum):
    """Absolute energy level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Register(str, Enum):
    """Frequency range."""
    SUB = "sub"        # < 60 Hz
    LOW = "low"        # 60-250 Hz
    MID = "mid"        # 250-2k Hz
    HIGH = "high"      # > 2k Hz


class Density(str, Enum):
    """Texture thickness."""
    SPARSE = "sparse"
    MEDIUM = "medium"
    DENSE = "dense"


class AttackProfile(str, Enum):
    """Envelope attack shape."""
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"
    PUNCHY = "punchy"  # very fast


class SustainLength(str, Enum):
    """Sustain envelope duration."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Spread(str, Enum):
    """Spatial width."""
    MONO = "mono"
    MEDIUM = "medium"
    WIDE = "wide"


@dataclass(frozen=True)
class MusicalCharacteristics:
    """Constraint set for a role or goal.

    None values mean unconstrained; empty lists mean explicitly forbidden.
    For example, character=[] means "do not apply any of the character constraints."
    """
    character: List[Character] = field(default_factory=list)
    energy: Optional[Energy] = None
    register: Optional[Register] = None
    density: Optional[Density] = None
    attack: Optional[AttackProfile] = None
    sustain_length: Optional[SustainLength] = None
    spread: Optional[Spread] = None

    def is_constrained(self) -> bool:
        """True if any dimension is constrained."""
        return (
            bool(self.character)
            or self.energy is not None
            or self.register is not None
            or self.density is not None
            or self.attack is not None
            or self.sustain_length is not None
            or self.spread is not None
        )


@dataclass(frozen=True)
class GoalModel:
    """Structured musical goal from user intent.

    INVARIANTS:
    1. No Serum parameter names (e.g., no "Filter1Freq" in the goal)
    2. role is required; section_name is optional
    3. characteristics describe what, not how
    4. user_phrasing is the original intent text for audit

    Example:
        GoalModel(
            user_phrasing="Make the bass darker and punchier for the drop",
            role="bass",
            section_name="peak",
            characteristics=MusicalCharacteristics(
                character=[Character.DARK, Character.PUNCHY],
                energy=Energy.HIGH,
                register=Register.LOW,
            )
        )
    """
    user_phrasing: str
    role: str                   # "bass", "pad", "lead", etc.
    characteristics: MusicalCharacteristics
    section_name: Optional[str] = None  # "intro", "peak", "outro", etc.

    def to_dict(self) -> Dict:
        """Serialize to dict for audit/logging."""
        return {
            "user_phrasing": self.user_phrasing,
            "role": self.role,
            "section_name": self.section_name,
            "characteristics": {
                "character": [c.value for c in self.characteristics.character],
                "energy": self.characteristics.energy.value if self.characteristics.energy else None,
                "register": self.characteristics.register.value if self.characteristics.register else None,
                "density": self.characteristics.density.value if self.characteristics.density else None,
                "attack": self.characteristics.attack.value if self.characteristics.attack else None,
                "sustain_length": self.characteristics.sustain_length.value if self.characteristics.sustain_length else None,
                "spread": self.characteristics.spread.value if self.characteristics.spread else None,
            }
        }
