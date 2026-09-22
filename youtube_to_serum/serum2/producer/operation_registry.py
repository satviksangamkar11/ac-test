"""Phase C: universal operation registry.

Answers "what operations does this system KNOW ABOUT", as a data-only
registry -- separate from "what's actually QUALIFIED to execute" (that's
still the CapabilityContract/ContractRegistry layer; separate again from
"what's ADMITTED right now" (admission.admit(), unmodified). Registering an
operation here does NOT grant it a capability -- an operation with no
qualified contract correctly REFUSES at resolution/admission, exactly as
before this registry existed. This module exists so new operations are
declared once, generically, instead of adding another
"if concept == 'release': ..." branch to producer_brain.py every time.

No video-specific entries. No "if video == ...". Each entry describes an
OPERATION CLASS (e.g. "set a Serum envelope field"), never one tutorial's
particular instance of it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class OperationDefinition:
    operation_id: str
    """e.g. 'SERUM.add_modulation_route'"""

    domain: str
    """'SERUM' | 'ABLETON'"""

    input_schema: Dict[str, str]
    """field_name -> human-readable type/description. Not a strict JSON
    Schema (no validator here) -- documents what runtime arguments this
    operation expects, e.g. {'source': 'str', 'destination': 'str',
    'amount': 'float | None', 'bipolar': 'bool | None'}."""

    capability_requirement: Optional[str] = None
    """The CapabilityContract target this operation needs ADMITTED before
    it can execute (e.g. 'serum.modulation_route.add'). None for Ableton
    host operations (track/clip/note creation), which are NOT a Serum
    capability claim and go straight to Ableton MCP per the existing
    architecture note in producer_brain.py's _is_host_operation()."""

    readback_requirement: str = "required"
    """'required' | 'not_applicable' -- whether real UI/state readback is
    needed before this operation can be marked EXECUTED (vs just PLAN_READY)."""

    qualified: bool = False
    """Honest flag: True only if capability_requirement actually has a real,
    qualified CapabilityContract loaded in ContractRegistry right now (set
    at registry-construction time by cross-checking, never hand-asserted
    here) OR the operation needs no capability at all (host ops). False
    means: this operation is a known, described CLASS, but nothing has
    qualified the backend to actually perform it yet -- resolution/admission
    will correctly REFUSE it. Registering an operation is not the same as
    proving it works."""

    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id, "domain": self.domain,
            "input_schema": dict(self.input_schema),
            "capability_requirement": self.capability_requirement,
            "readback_requirement": self.readback_requirement,
            "qualified": self.qualified, "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# SERUM operations
# ---------------------------------------------------------------------------

_SERUM_OPERATIONS: List[OperationDefinition] = [
    OperationDefinition(
        operation_id="SERUM.set_parameter",
        domain="SERUM",
        input_schema={"target_concept": "str (e.g. 'note-release')", "direction": "str"},
        capability_requirement=None,  # resolved dynamically per concept via UNIVERSAL_TO_SEMANTIC
        qualified=True,  # at least note-release/envelope-attack are real, qualified instances
        notes=(
            "Generic numeric/scalar Serum field mutation. capability_requirement "
            "is resolved PER-CONCEPT at runtime (e.g. note-release -> "
            "envelope_field_release) via the existing frozen UNIVERSAL_TO_SEMANTIC "
            "mapping -- not a single fixed target, since this operation class "
            "covers many concrete fields. qualified=True reflects that SOME "
            "concepts under this class (release, attack) are real and qualified; "
            "individual concepts still resolve/admit independently -- this flag "
            "is not a blanket guarantee for every possible concept."
        ),
    ),
    OperationDefinition(
        operation_id="SERUM.add_modulation_route",
        domain="SERUM",
        input_schema={"source": "str", "destination": "str", "amount": "float | None", "bipolar": "bool | None"},
        capability_requirement="serum.modulation_route.add",
        notes="Qualified this session via qualify_modulation_route.py (2 real serum-mcp instances, 1 UI-verified).",
    ),
    OperationDefinition(
        operation_id="SERUM.remove_modulation_route",
        domain="SERUM",
        input_schema={"source": "str", "destination": "str"},
        capability_requirement="serum.modulation_route.remove",
        notes="Registered as a known operation CLASS; no qualification evidence exists yet -- correctly REFUSES at admission.",
    ),
    OperationDefinition(
        operation_id="SERUM.set_enum",
        domain="SERUM",
        input_schema={"target": "str (e.g. 'Filter1.Type')", "value": "str (e.g. 'Band 24')"},
        capability_requirement="serum.enum_field.set",
        notes="Covers dropdown/enum fields (filter type, wavetable, noise type, ...). Not yet qualified.",
    ),
    OperationDefinition(
        operation_id="SERUM.configure_envelope",
        domain="SERUM",
        input_schema={"envelope_index": "int", "fields": "dict[str, float] (attack/decay/sustain/release subset)"},
        capability_requirement="serum.envelope.configure_composite",
        notes="Composite multi-field envelope edit in one preset write. Not yet qualified (only single-field release/attack contracts exist).",
    ),
    OperationDefinition(
        operation_id="SERUM.configure_filter",
        domain="SERUM",
        input_schema={"filter_index": "int", "fields": "dict[str, Any] (type/cutoff/resonance/drive subset)"},
        capability_requirement="serum.filter.configure_composite",
        notes="Composite multi-field filter edit. Not yet qualified.",
    ),
    OperationDefinition(
        operation_id="SERUM.configure_oscillator",
        domain="SERUM",
        input_schema={"oscillator_index": "int", "fields": "dict[str, Any] (wavetable/octave/detune/etc.)"},
        capability_requirement="serum.oscillator.configure_composite",
        notes="Composite multi-field oscillator edit. Not yet qualified.",
    ),
    OperationDefinition(
        operation_id="SERUM.load_preset",
        domain="SERUM",
        input_schema={"preset_name": "str"},
        capability_requirement="serum.preset.load_named",
        notes="Loading an arbitrary named (factory/third-party) preset -- distinct from this project's own generated .SerumPreset load step. Not yet qualified.",
    ),
]

# ---------------------------------------------------------------------------
# ABLETON operations -- host/session operations, NOT Serum capability claims.
# Per the existing architecture note in producer_brain.py's
# _is_host_operation(): track/clip/note creation mutates Ableton session
# state, not a Serum synthesis parameter, so no CapabilityContract applies
# and these go straight to Ableton MCP. capability_requirement=None here
# reflects that existing, correct design -- not a gap.
# ---------------------------------------------------------------------------

_ABLETON_OPERATIONS: List[OperationDefinition] = [
    OperationDefinition(
        operation_id="ABLETON.create_track",
        domain="ABLETON",
        input_schema={"track_type": "str ('midi' | 'audio')", "index": "int"},
        capability_requirement=None, qualified=True, readback_requirement="required",
    ),
    OperationDefinition(
        operation_id="ABLETON.create_clip",
        domain="ABLETON",
        input_schema={"track_index": "int", "clip_index": "int", "length_beats": "float"},
        capability_requirement=None, qualified=True,
    ),
    OperationDefinition(
        operation_id="ABLETON.add_notes",
        domain="ABLETON",
        input_schema={"track_index": "int", "clip_index": "int", "notes": "list[dict]"},
        capability_requirement=None, qualified=True,
    ),
    OperationDefinition(
        operation_id="ABLETON.edit_notes",
        domain="ABLETON",
        input_schema={"track_index": "int", "clip_index": "int", "edits": "list[dict]"},
        capability_requirement=None, qualified=True,
    ),
    OperationDefinition(
        operation_id="ABLETON.arrange_clip",
        domain="ABLETON",
        input_schema={"track_index": "int", "clip_index": "int", "destination_time_beats": "float"},
        capability_requirement=None, qualified=True,
    ),
    OperationDefinition(
        operation_id="ABLETON.automation",
        domain="ABLETON",
        input_schema={"track_index": "int", "parameter": "str", "points": "list[dict]"},
        capability_requirement=None, qualified=False,
        notes="Registered as a known operation CLASS; not exercised by any episode yet.",
    ),
    OperationDefinition(
        operation_id="ABLETON.render",
        domain="ABLETON",
        input_schema={"start_beat": "float", "length_beats": "float", "output_path": "str"},
        capability_requirement=None, qualified=False,
        readback_requirement="required",
        notes=(
            "No bounce-to-file MCP tool exists in the installed AbletonMCP "
            "toolset (confirmed twice this session) -- real export currently "
            "requires driving Ableton's own File > Export Audio/Video UI via "
            "computer-use. Registered honestly as unqualified/not runtime-"
            "exercised, not fabricated as working."
        ),
    ),
]


class OperationRegistry:
    """Read-only lookup over the declared operation set. Grants no
    authority -- same role as route_selection.RouteSelector: an advisory
    lookup over what's known, never itself an admission gate.

    `qualified` is cross-checked here against the REAL ContractRegistry at
    construction time, never hand-asserted per entry -- an operation whose
    capability_requirement names a target that isn't actually loaded (e.g.
    no qualification evidence exists) must show qualified=False even if a
    hand-typed default said otherwise. Caught live: the static defaults
    above under-reported serum.modulation_route.add as unqualified despite
    it having a real contract from this session's qualify_modulation_route.py.
    """

    def __init__(self):
        from serum2.producer.contract_registry import ContractRegistry
        registry = ContractRegistry()
        loaded_targets = set(registry.all_targets())

        self._by_id: Dict[str, OperationDefinition] = {}
        for op in (_SERUM_OPERATIONS + _ABLETON_OPERATIONS):
            if op.capability_requirement is None:
                self._by_id[op.operation_id] = op
                continue
            actually_qualified = op.capability_requirement in loaded_targets
            if actually_qualified != op.qualified:
                import dataclasses
                op = dataclasses.replace(op, qualified=actually_qualified)
            self._by_id[op.operation_id] = op

    def get(self, operation_id: str) -> Optional[OperationDefinition]:
        return self._by_id.get(operation_id)

    def all_operations(self) -> List[OperationDefinition]:
        return list(self._by_id.values())

    def by_domain(self, domain: str) -> List[OperationDefinition]:
        return [op for op in self._by_id.values() if op.domain == domain]
