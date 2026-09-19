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
    """Canonical U3 operation types. Target-independent."""
    # Numeric
    SET = "set"                           # set to exact value
    INCREASE = "increase"                 # increase value (direction only)
    DECREASE = "decrease"                 # decrease value (direction only)
    # Enum
    SELECT = "enum_select"                # select from enum values
    # Toggle
    TOGGLE_ON = "toggle_on"               # enable/on
    TOGGLE_OFF = "toggle_off"             # disable/off
    TOGGLE_SWITCH = "toggle_switch"       # toggle state
    # Structured / collection
    PATCH = "patch"                       # partial update of a structured value
    ADD = "add"                           # add an element (e.g. modulation route)
    REMOVE = "remove"                     # remove an element
    # Legacy aliases (keep for callers that predate U3)
    NUMERIC_SET = "set"                   # alias for SET
    NUMERIC_INCREASE = "increase"         # alias for INCREASE
    NUMERIC_DECREASE = "decrease"         # alias for DECREASE
    ENUM_SELECT = "enum_select"           # alias for SELECT
    UNKNOWN = "unknown"                   # could not interpret


@dataclass
class Operand:
    """U3: Typed operand for an operation.

    Exactly one of (value, boolean_value, enum_value) is populated;
    the others are None. normalized_value is set by a downstream layer
    that maps the raw value into the native Atlas range.
    """
    value: Optional[Any] = None             # numeric value (raw, user-supplied)
    unit: Optional[str] = None              # user-supplied unit string ("ms", "hz", …)
    normalized_value: Optional[float] = None  # filled by value-mapping layer
    enum_value: Optional[str] = None        # for SELECT
    boolean_value: Optional[bool] = None    # for TOGGLE_ON / TOGGLE_OFF

    _UNIT_COMPAT: dict = None  # populated lazily; not a real field

    def validate_against(self, value_domain) -> tuple[bool, str]:
        """Check this operand is compatible with value_domain.

        Returns (ok, reason). reason is empty when ok is True.
        """
        vd_type = getattr(value_domain, "type", None)
        vd_unit = getattr(value_domain, "unit", None)

        # Toggle domain
        if vd_type == "toggle":
            if self.boolean_value is None:
                return False, "toggle domain requires boolean_value"
            return True, ""

        # Enum domain
        if vd_type == "enum":
            evs = getattr(value_domain, "enum_values", None) or []
            if self.enum_value is None:
                return False, "enum domain requires enum_value"
            if evs and self.enum_value.lower() not in {e.lower() for e in evs}:
                return False, f"{self.enum_value!r} not in enum vocabulary {evs}"
            return True, ""

        # Numeric / direction-only (no value = direction-only = always compatible)
        if self.boolean_value is not None or self.enum_value is not None:
            return False, f"non-numeric operand against {vd_type!r} domain"
        if self.value is None:
            return True, ""  # direction-only (INCREASE / DECREASE)

        # Unit compatibility check (loose: ms↔seconds are compatible time units)
        if self.unit and vd_unit:
            time_units = {"ms", "s", "seconds", "milliseconds"}
            freq_units = {"hz", "khz", "hz"}
            def family(u): return (
                "time" if u.lower() in time_units else
                "freq" if u.lower() in freq_units else u.lower()
            )
            if family(self.unit) != family(vd_unit):
                # Still accept if both domains are generic numeric
                if vd_type not in ("normalized", "numeric", "percentage"):
                    return False, f"unit {self.unit!r} incompatible with domain unit {vd_unit!r}"

        return True, ""


@dataclass
class OperationSpec:
    """U3: Normalized, target-independent operation specification."""

    operation: OperationType
    operand: Optional[Operand] = None       # U3: typed operand
    # Legacy scalar fields preserved for callers that predate U3
    target_value: Optional[Any] = None
    direction: Optional[str] = None
    unit: Optional[str] = None
    base_phrase: str = ""
    certainty: float = 0.5
    interpretation_chain: list[str] = None

    def __post_init__(self):
        if self.interpretation_chain is None:
            self.interpretation_chain = []
        if self.certainty < 0.0 or self.certainty > 1.0:
            raise ValueError(f"Certainty must be 0.0–1.0, got {self.certainty}")

    def validate_against(self, value_domain) -> tuple[bool, str]:
        """Validate this spec against a ValueDomain.

        Direction-only operations (INCREASE/DECREASE) are always valid for
        numeric domains. All others delegate to operand.
        """
        vd_type = getattr(value_domain, "type", None)
        if self.operation in (OperationType.INCREASE, OperationType.DECREASE):
            if vd_type in ("toggle", "enum"):
                return False, f"{self.operation.value} not valid for {vd_type!r} domain"
            return True, ""
        if self.operation in (OperationType.TOGGLE_ON, OperationType.TOGGLE_OFF):
            if vd_type != "toggle":
                return False, f"toggle operation against {vd_type!r} domain"
            return True, ""
        if self.operand is None:
            return True, ""
        return self.operand.validate_against(value_domain)

    def to_dict(self) -> dict[str, Any]:
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

        if operation_type == "enum":
            enum_match = self._extract_enum_selection(phrase_lower)
            if enum_match:
                value, extracted = enum_match
                chain.append(f"enum_match(contract is enum): {extracted!r}")
                return OperationSpec(operation=OperationType.SELECT, target_value=value,
                                     operand=Operand(enum_value=value),
                                     base_phrase=phrase, certainty=0.75, interpretation_chain=chain)

        # Try to extract numeric value (e.g., "to 100ms", "= 50", "at 200")
        numeric_match = self._extract_numeric_value(phrase_lower)
        if numeric_match:
            value, unit, extracted = numeric_match
            chain.append(f"numeric_match: {extracted} → value={value}, unit={unit}")
            words = self._tokenize(phrase_lower)
            inc = sum(1 for t in words if t in self._INCREASE_WORDS)
            dec = sum(1 for t in words if t in self._DECREASE_WORDS)
            return OperationSpec(
                operation=OperationType.SET,
                target_value=value,
                operand=Operand(value=value, unit=unit),
                direction="increase" if inc > dec else ("decrease" if dec > inc else None),
                unit=unit,
                base_phrase=phrase,
                certainty=0.90,
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
                    operand=Operand(boolean_value=True),
                    base_phrase=phrase, certainty=0.85, interpretation_chain=chain,
                )
            if any(t in self._TOGGLE_OFF_WORDS for t in tokens):
                chain.append("toggle_detection: OFF words found")
                return OperationSpec(
                    operation=OperationType.TOGGLE_OFF,
                    operand=Operand(boolean_value=False),
                    base_phrase=phrase, certainty=0.85, interpretation_chain=chain,
                )

        # Check for numeric direction (increase/decrease)
        increase_count = sum(1 for t in tokens if t in self._INCREASE_WORDS)
        decrease_count = sum(1 for t in tokens if t in self._DECREASE_WORDS)

        if increase_count > decrease_count and increase_count > 0:
            chain.append(f"direction_detection: INCREASE ({increase_count} words)")
            return OperationSpec(
                operation=OperationType.INCREASE,
                direction="increase",
                base_phrase=phrase,
                certainty=0.80 if increase_count >= 1 else 0.60,
                interpretation_chain=chain,
            )

        if decrease_count > increase_count and decrease_count > 0:
            chain.append(f"direction_detection: DECREASE ({decrease_count} words)")
            return OperationSpec(
                operation=OperationType.DECREASE,
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
                operand=Operand(boolean_value=True),
                base_phrase=phrase, certainty=0.75, interpretation_chain=chain,
            )

        if toggle_off_match:
            chain.append("toggle_fallback: OFF detected")
            return OperationSpec(
                operation=OperationType.TOGGLE_OFF,
                operand=Operand(boolean_value=False),
                base_phrase=phrase, certainty=0.75, interpretation_chain=chain,
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
        pattern = r"(?<![A-Za-z0-9_.])(-?\d+(?:\.\d+)?)\s*(ms|s|hz|khz|db|%|cents)?(?![A-Za-z0-9_])"
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
        """Enum value = the raw text after 'to' / 'select' / 'choose'. No value vocabulary lives here;
        validity is the capability contract's business."""
        m = re.search(r"(?:^|\s)(?:to|select|choose|as)\s+(.+)$", phrase)
        if m and m.group(1).strip():
            return m.group(1).strip(), m.group(0)
        return None

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: split on whitespace and punctuation."""
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        return tokens
