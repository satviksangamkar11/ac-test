"""B1.3: Operation/Value Interpretation.

Given a concept and user intent ("shorter", "to 5ms", "increase", etc.),
produce normalized operation specifications. This layer is independent from
concept; the same operation interpretation applies across all concepts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum
import re


class OperationType(Enum):
    """Canonical operation types."""
    NUMERIC_SET = "numeric_set"           # set to exact value
    NUMERIC_INCREASE = "increase"          # increase value
    NUMERIC_DECREASE = "decrease"          # decrease value
    ENUM_SELECT = "enum_select"           # select from enum values
    TOGGLE_ON = "toggle_on"               # enable/on
    TOGGLE_OFF = "toggle_off"             # disable/off
    TOGGLE_SWITCH = "toggle_switch"       # toggle state
    UNKNOWN = "unknown"                   # could not interpret


@dataclass
class OperationSpec:
    """Normalized operation specification.

    Combines user intent language with operation interpretation.
    """

    operation: OperationType
    target_value: Optional[Any] = None     # for SET operations
    direction: Optional[str] = None         # "increase" or "decrease"
    unit: Optional[str] = None              # "ms", "hz", etc.
    base_phrase: str = ""                  # original user phrase (for audit)
    certainty: float = 0.5                 # 0.0–1.0; confidence in interpretation
    interpretation_chain: list[str] = None  # audit trail

    def __post_init__(self):
        if self.interpretation_chain is None:
            self.interpretation_chain = []
        if self.certainty < 0.0 or self.certainty > 1.0:
            raise ValueError(f"Certainty must be 0.0–1.0, got {self.certainty}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging."""
        return {
            "operation": self.operation.value,
            "target_value": self.target_value,
            "direction": self.direction,
            "unit": self.unit,
            "certainty": self.certainty,
            "interpretation_chain": self.interpretation_chain,
        }


class OperationInterpreter:
    """B1.3: Interpret user intent into normalized OperationSpec.

    Frozen direction vocabulary (§9, §22):
    - INCREASE: "more", "up", "raise", "increase", "longer", "louder", "higher", "bigger"
    - DECREASE: "off", "less", "lower", "down", "reduce", "decrease", "shorter", "tighter"
    - TOGGLE_ON: "on", "enable", "turn on"
    - TOGGLE_OFF: "off", "disable", "turn off"
    - NUMERIC_SET: "to <number>", "at <number>", "= <number>"

    All vocabulary is generic (not tutorial-specific).
    """

    # Frozen frozen vocabulary
    _INCREASE_WORDS = frozenset((
        "more", "up", "raise", "increase", "longer", "louder", "higher", "bigger",
        "larger", "extend", "boost", "strengthen", "amplify", "brighten", "sharpen"
    ))

    _DECREASE_WORDS = frozenset((
        "off", "less", "lower", "down", "reduce", "decrease", "shorter", "shorten",
        "quieter", "smaller", "tighter", "weaken", "dampen", "darken", "dull"
    ))

    _TOGGLE_ON_WORDS = frozenset((
        "on", "enable", "turn on", "activate", "switch on"
    ))

    _TOGGLE_OFF_WORDS = frozenset((
        "off", "disable", "turn off", "deactivate", "switch off"
    ))

    def __init__(self):
        """Initialize the interpreter."""
        pass

    def interpret(self, phrase: str, operation_type: Optional[str] = None) -> OperationSpec:
        """Interpret a user phrase into an OperationSpec.

        Args:
            phrase: User's intent phrase (e.g., "shorter", "to 100ms", "increase")
            operation_type: Hint about expected operation ("numeric", "enum", "toggle")

        Returns:
            OperationSpec with normalized operation and audit trail
        """
        chain = [f"interpret(phrase={phrase!r}, op_type={operation_type})"]
        phrase_lower = phrase.lower().strip()

        # Try to extract numeric value (e.g., "to 100ms", "= 50", "at 200")
        numeric_match = self._extract_numeric_value(phrase_lower)
        if numeric_match:
            value, unit, extracted = numeric_match
            chain.append(f"numeric_match: {extracted} → value={value}, unit={unit}")
            return OperationSpec(
                operation=OperationType.NUMERIC_SET,
                target_value=value,
                unit=unit,
                base_phrase=phrase,
                certainty=0.90,
                interpretation_chain=chain,
            )

        # Try to extract enum selection (e.g., "to Band 24", "select BP12")
        enum_match = self._extract_enum_selection(phrase_lower)
        if enum_match:
            value, extracted = enum_match
            chain.append(f"enum_match: {extracted} → value={value}")
            return OperationSpec(
                operation=OperationType.ENUM_SELECT,
                target_value=value,
                base_phrase=phrase,
                certainty=0.75,
                interpretation_chain=chain,
            )

        # Tokenize and check for direction words
        tokens = self._tokenize(phrase_lower)
        chain.append(f"tokens: {tokens}")

        # Check for toggle operations (if hint suggests toggle)
        if operation_type == "toggle":
            if any(t in self._TOGGLE_ON_WORDS for t in tokens):
                chain.append("toggle_detection: ON words found")
                return OperationSpec(
                    operation=OperationType.TOGGLE_ON,
                    base_phrase=phrase,
                    certainty=0.85,
                    interpretation_chain=chain,
                )
            if any(t in self._TOGGLE_OFF_WORDS for t in tokens):
                chain.append("toggle_detection: OFF words found")
                return OperationSpec(
                    operation=OperationType.TOGGLE_OFF,
                    base_phrase=phrase,
                    certainty=0.85,
                    interpretation_chain=chain,
                )

        # Check for numeric direction (increase/decrease)
        increase_count = sum(1 for t in tokens if t in self._INCREASE_WORDS)
        decrease_count = sum(1 for t in tokens if t in self._DECREASE_WORDS)

        if increase_count > decrease_count and increase_count > 0:
            chain.append(f"direction_detection: INCREASE ({increase_count} words)")
            return OperationSpec(
                operation=OperationType.NUMERIC_INCREASE,
                direction="increase",
                base_phrase=phrase,
                certainty=0.80 if increase_count >= 1 else 0.60,
                interpretation_chain=chain,
            )

        if decrease_count > increase_count and decrease_count > 0:
            chain.append(f"direction_detection: DECREASE ({decrease_count} words)")
            return OperationSpec(
                operation=OperationType.NUMERIC_DECREASE,
                direction="decrease",
                base_phrase=phrase,
                certainty=0.80 if decrease_count >= 1 else 0.60,
                interpretation_chain=chain,
            )

        # Toggle check for generic phrases like "enable" or "disable"
        toggle_on_match = any(t in self._TOGGLE_ON_WORDS for t in tokens)
        toggle_off_match = any(t in self._TOGGLE_OFF_WORDS for t in tokens)

        if toggle_on_match:
            chain.append("toggle_fallback: ON detected")
            return OperationSpec(
                operation=OperationType.TOGGLE_ON,
                base_phrase=phrase,
                certainty=0.75,
                interpretation_chain=chain,
            )

        if toggle_off_match:
            chain.append("toggle_fallback: OFF detected")
            return OperationSpec(
                operation=OperationType.TOGGLE_OFF,
                base_phrase=phrase,
                certainty=0.75,
                interpretation_chain=chain,
            )

        # Could not interpret
        chain.append("NO_INTERPRETATION")
        return OperationSpec(
            operation=OperationType.UNKNOWN,
            base_phrase=phrase,
            certainty=0.0,
            interpretation_chain=chain,
        )

    # ---- Helpers ----

    def _extract_numeric_value(self, phrase: str) -> Optional[tuple[Any, Optional[str], str]]:
        """Try to extract a numeric value and unit from the phrase.

        Matches patterns like: "to 100ms", "= 50", "at 200 hz", "shorter 100"
        """
        # Pattern: (to|at|=|shorter|longer) <number> <optional_unit>
        pattern = r"(?:to|at|=|shorter|longer|by)?\s*(-?[\d.]+)\s*(ms|s|hz|khz|db|%|cents)?"
        match = re.search(pattern, phrase, re.IGNORECASE)

        if match:
            value_str, unit = match.groups()
            try:
                # Try int first, then float
                if "." in value_str:
                    value = float(value_str)
                else:
                    value = int(value_str)

                unit_normalized = (unit.lower() if unit else None)
                extracted = match.group(0)

                return value, unit_normalized, extracted
            except ValueError:
                return None

        return None

    def _extract_enum_selection(self, phrase: str) -> Optional[tuple[str, str]]:
        """Try to extract an enum value selection.

        Matches patterns like: "to Band 24", "select BP12", "choose sine"
        """
        # Very conservative: only recognize known enum patterns
        known_enums = {
            "sine": ["sine", "sine wave"],
            "triangle": ["triangle", "tri"],
            "square": ["square"],
            "sawtooth": ["sawtooth", "saw"],
            "bp12": ["band 24", "bp12", "bandpass 12"],
            "lp12": ["low 12", "lp12", "lowpass 12"],
            "hp12": ["high 12", "hp12", "highpass 12"],
            "remap": ["remap"],
        }

        for canonical, aliases in known_enums.items():
            for alias in aliases:
                if alias in phrase:
                    return canonical, alias

        return None

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: split on whitespace and punctuation."""
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        return tokens
