"""Serum 2.0.21 Reference Atlas.

Answers ONE question: "what control exists, where, and what does it look
like?" It is knowledge about the instrument, built from serum-mcp's own
real, corpus-verified parameter schema (serum_2_0_21_schema_snapshot.json,
captured via the installed serum-mcp `list_parameters()` tool) -- not
fabricated, not tutorial-specific.

HARD BOUNDARY (do not weaken):
  - This module has NO execution authority. It cannot admit, resolve, or
    execute anything. producer_brain.py / capability_contract.py /
    admission.py remain the only authority chain.
  - REFERENCE_DEFAULT_STATE (this module) is NOT episode evidence. A
    tutorial's actually-observed starting state (visual_evidence.py's
    ControlState/UIStateSnapshot) always wins over whatever this module
    lists as Serum's own shipped default -- never assume a tutorial starts
    from default state.
  - A ReferenceControl answers "what is this control" (identity, unit,
    range, default). It never answers "should this be changed" -- that is
    the Brain's job, downstream and unrelated to this module.

Reuses the existing generic control_id convention already established by
visual_evidence.py's ControlState (e.g. 'env1.release', 'oscA.unison') --
same IDs, so a Stage-A observation and a reference lookup for the same
control always agree on what to call it. No per-category dataclasses:
one ReferenceControl shape covers every panel, matching the project's
existing "generic control_id, not a proliferation of types" convention.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ATLAS_VERSION = "serum-2.0.21-atlas-v1"  # schema-derived control vocabulary; pinned by tests
CONTROL_ATLAS_VERSION = ATLAS_VERSION
SERUM_VERSION = "2.0.21"

_SNAPSHOT_PATH = Path(__file__).parent / "serum_2_0_21_schema_snapshot.json"


@dataclass(frozen=True)
class ReferenceControl:
    """One entry in the Reference Atlas -- static knowledge about a control,
    never a claim about any particular episode's actual state."""
    control_id: str
    display_name: str
    panel: str
    control_type: str  # "continuous" | "enum" | "toggle" | "topology" | "module_identity"
    unit: Optional[str] = None
    default_value: Optional[Any] = None
    """REFERENCE_DEFAULT_STATE: Serum's own shipped default for this field,
    per serum-mcp's schema. NEVER episode evidence -- see module docstring."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()
    source: str = ""
    notes: Optional[str] = None
    audit: Optional[Dict[str, Any]] = None
    """The full raw record from the frozen local UI audit (serum_audit.py) when
    one bridges to this control -- sources/evidence_type/status/notes/
    conditional_visibility preserved verbatim. Never overrides the fields above."""
    audit_bridge: Optional[str] = None  # EXACT_NAME | TABLE | DERIVED_NEW
    element_kind: Optional[str] = None
    """CONTROL/SELECTOR/TEXT_IDENTITY/GRAPH/CURVE/REGION/ROUTE/TOPOLOGY/
    ENABLE_STATE when classifiable without guessing, else None."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id, "display_name": self.display_name,
            "panel": self.panel, "control_type": self.control_type, "unit": self.unit,
            "default_value": self.default_value, "min_value": self.min_value,
            "max_value": self.max_value, "enum_values": list(self.enum_values),
            "aliases": list(self.aliases), "source": self.source, "notes": self.notes,
            "audit_semantic_id": (self.audit or {}).get("semantic_id"),
            "audit_status": (self.audit or {}).get("status"),
            "audit_bridge": self.audit_bridge, "element_kind": self.element_kind,
        }


# control_id suffix -> (display_name, aliases) for each kParam field, applied
# identically across every oscillator/filter/envelope/lfo instance. Aliases
# are semantic vocabulary for transcript alignment ONLY -- they grant no
# execution authority (see module docstring).
_OSC_FIELDS = {
    "kParamEnable": ("enabled", ()),
    "kParamOctave": ("octave", ("octave", "oct")),
    "kParamVolume": ("level", ("level", "volume", "osc level")),
    "kParamPan": ("pan", ("pan",)),
    "kParamFine": ("fine", ("fine", "fine tune", "fin")),
    # Evidence-corrected 2026-09 (parameter_characterization/binding_evidence/
    # oscA_pitch_disambiguation.json): causal DawDreamer probing proved host
    # #24 "A Semi" writes kParamPitch (body range -12..12, integer semitone
    # display), while host #28 "A Coarse Pitch" writes kParamCoarsePit (body
    # range -72..72, fractional display) -- a DIFFERENT field, not an alias.
    # This matches serum-mcp's own canonical mapping ("semitone": "kParamPitch",
    # preset/mapping.py) and a prior independently-qualified binding
    # (qualification/binding_evidence/oscA.semitone.json). The previous table
    # had these two suffixes swapped, so oscA.semitone was built from
    # kParamCoarsePit's schema entry (wrong bounds, wrong field) instead of
    # kParamPitch's.
    "kParamCoarsePit": ("coarse_pitch", ("coarse pitch",)),
    "kParamPitch": ("semitone", ("semitone", "sem", "semi", "pitch")),
    "kParamDetune": ("detune", ("detune",)),
    "kParamDetuneWid": ("detune_width", ("detune width", "unison width")),
    "kParamUnison": ("unison", ("unison", "voices")),
    "kParamUnisonStereo": ("unison_stereo_width", ("unison stereo",)),
    "kParamPitchTrack": ("pitch_track", ("pitch track", "key track")),
    "kParamType": ("engine_type", ("oscillator type", "engine")),
    "kParamLoopMode": ("sample_loop_mode", ("loop mode",)),
    "kParamLoopStart": ("sample_loop_start", ("loop start",)),
    "kParamLoopEnd": ("sample_loop_end", ("loop end",)),
    "kParamLoopCrossfade": ("sample_loop_crossfade", ("loop crossfade",)),
}
_WT_FIELDS = {
    "kParamTablePos": ("wt_position", ("wavetable position", "wt pos", "table position")),
    "kParamWarp": ("warp_amount", ("warp amount", "warp")),
    "kParamWarp2": ("warp_amount2", ("warp 2",)),
    "kParamWarpMenu": ("warp_mode", ("warp mode",)),
    "kParamInitialPhase": ("phase", ("phase",)),
    "kParamRandomPhase": ("random_phase", ("random phase", "rand")),
    "kParamXfadeMode": ("wt_interpolation_mode", ("smooth interpolation", "interpolation mode")),
    "kParamWarpMenu2": ("warp_mode2", ("warp mode 2",)),
    "kParamWarpVar2": ("warp_var2", ("warp var 2",)),
}
_FILTER_FIELDS = {
    "kParamEnable": ("enabled", ()),
    "kParamType": ("type", ("filter type",)),
    "kParamFreq": ("cutoff", ("cutoff", "frequency", "freq", "cut off")),
    "kParamReso": ("resonance", ("resonance", "res")),
    "kParamDrive": ("drive", ("drive",)),
    "kParamVar": ("var", ("var",)),
    "kParamLevelOut": ("level_out", ("level out", "output level")),
    "kParamStereo": ("stereo", ("stereo",)),
    "kParamWet": ("wet", ("wet", "mix")),
    "kParamKeyTrack": ("key_track", ("key track", "keytracking")),
}
_ENV_FIELDS = {
    "kParamAttack": ("attack", ("attack", "atk")),
    "kParamHold": ("hold", ("hold",)),
    "kParamDecay": ("decay", ("decay", "dec")),
    "kParamSustain": ("sustain", ("sustain", "sus")),
    "kParamRelease": ("release", ("release", "rel", "release time", "envelope release")),
    "kParamCurve1": ("attack_curve", ("attack curve",)),
    "kParamCurve2": ("decay_curve", ("decay curve",)),
    "kParamCurve3": ("release_curve", ("release curve",)),
}
_LFO_FIELDS = {
    "kParamRate": ("rate", ("rate",)),
    "kParamMode": ("mode", ("mode", "trigger mode")),
    "kParamBeatSync": ("beat_sync", ("beat sync", "sync")),
    "kParamRise": ("rise", ("rise",)),
    "kParamSmooth": ("smooth", ("smooth",)),
    "kParamDelay": ("delay", ("delay", "fade")),
    "kParamType": ("shape", ("shape", "curve")),
    "kParamMono": ("mono", ("mono",)),
    "kParamSwing": ("swing", ("swing",)),
    "kParamDotted": ("dotted", ("dotted",)),
    "kParamTriplets": ("triplets", ("triplets",)),
    "kParamRate10x": ("rate_10x", ("rate x10",)),
}
_MOD_SLOT_FIELDS = {
    "kParamAmount": ("amount", ("amount", "depth")),
    "kParamBipolar": ("bipolar", ("bipolar",)),
    "kParamAuxInverted": ("aux_inverted", ("aux inverted",)),
    "kParamAuxCurve": ("aux_curve", ("aux curve",)),
    "kParamBypass": ("bypass", ("bypass",)),
    "kParamCurveIn": ("curve_in", ("curve in",)),
    "kParamDelayOffset": ("delay_offset", ("delay offset",)),
    "kParamDelayBeatSync": ("delay_beat_sync", ("delay beat sync",)),
    "kParamSmoothRise": ("smooth_rise", ("smooth rise",)),
    "kParamSmoothFall": ("smooth_fall", ("smooth fall",)),
    "kParamSmoothLink": ("smooth_link", ("smooth link",)),
}
_GLOBAL_FIELDS = {
    "kParamMasterVolume": ("master_volume", ("master volume", "main volume")),
    "kParamMonoToggle": ("mono", ("mono", "poly/mono")),
    "kParamPolyCount": ("poly_count", ("polyphony", "voice count")),
    "kParamPortamentoTime": ("portamento_time", ("portamento", "glide", "glide time")),
    "kParamLimitSameNotePolyphony": ("limit_same_note_polyphony", ()),
    "kParamDirectVol": ("direct_volume", ()),
    "kParamFXBus1Vol": ("fx_bus1_volume", ()),
    "kParamFXBus2Vol": ("fx_bus2_volume", ()),
    "kParamFXBus1Dest": ("fx_bus1_destination", ()),
    "kParamFXBus2Dest": ("fx_bus2_destination", ()),
    "kParamBendRangeUp": ("bend_range_up", ("pitch bend up",)),
    "kParamBendRangeDn": ("bend_range_down", ("pitch bend down",)),
    "kParamLegato": ("legato", ("legato",)),
    "kParamPortaAlways": ("porta_always", ()),
    "kParamPortaScaled": ("porta_scaled", ()),
    "kParamPortamentoCurve": ("portamento_curve", ("glide curve",)),
    "kParamSwing": ("swing", ("swing",)),
    "kParamSwingDiv": ("swing_div", ()),
    "kParamTranspose": ("transpose", ("transpose",)),
    "kParamGlobalTuning": ("global_tuning", ("tuning", "a440")),
    "kParamOversampling": ("oversampling", ("quality",)),
    "kParamS1Compatibility": ("s1_compatibility", ()),
    "kParamUseUltraOnRender": ("use_ultra_on_render", ()),
    "kParamNoteLatch": ("note_latch", ()),
    "kParamVoiceAmp": ("voice_amp", ()),
}

_OSC_SLOTS = ("oscA", "oscB", "oscC")
_ENV_SLOTS = ("env1", "env2", "env3", "env4")
_LFO_SLOTS = tuple("lfo%d" % i for i in range(1, 7))  # LFO 7-10 are headless mod sources (audit)
_FILTER_SLOTS = ("filter1", "filter2")
_MACRO_SLOTS = tuple("macro%d" % i for i in range(1, 9))


def _entry_from_schema(
    control_id: str, display_name: str, panel: str, schema_entry: Dict[str, Any],
    aliases: Tuple[str, ...], source: str,
) -> ReferenceControl:
    kind = schema_entry.get("kind")
    control_type = "toggle" if kind == "bool" else ("continuous" if kind == "float" else "enum")
    return ReferenceControl(
        control_id=control_id, display_name=display_name, panel=panel,
        control_type=control_type, unit=schema_entry.get("unit") or None,
        default_value=schema_entry.get("default"),
        min_value=schema_entry.get("min"), max_value=schema_entry.get("max"),
        enum_values=tuple(schema_entry.get("enum_values", ())),
        aliases=aliases, source=source,
        notes=schema_entry.get("notes") or None,
    )


def _build_atlas() -> Dict[str, ReferenceControl]:
    raw = json.loads(_SNAPSHOT_PATH.read_text())
    snap = raw["snapshot"]
    source_tag = raw["schema_source"]
    atlas: Dict[str, ReferenceControl] = {}

    for slot in _OSC_SLOTS:
        for kparam, (suffix, aliases) in _OSC_FIELDS.items():
            if kparam not in snap["oscillator"]:
                continue
            cid = "%s.%s" % (slot, suffix)
            atlas[cid] = _entry_from_schema(
                cid, suffix.replace("_", " ").title(), slot.upper(),
                snap["oscillator"][kparam], aliases, source_tag + " OscillatorSpec",
            )
        for kparam, (suffix, aliases) in _WT_FIELDS.items():
            if kparam not in snap["wavetable_oscillator"]:
                continue
            cid = "%s.%s" % (slot, suffix)
            atlas[cid] = _entry_from_schema(
                cid, suffix.replace("_", " ").title(), slot.upper(),
                snap["wavetable_oscillator"][kparam], aliases, source_tag + " WavetableOscillator",
            )
        # wavetable IDENTITY (name) -- not a kParam in this schema slice, it's
        # a string field on serum-mcp's own PresetSpec.OscillatorSpec.wavetable
        # (one of simple_wavetables' keys); recorded from that real, separate
        # tool schema this project already fetched (edit_preset/generate_preset
        # arguments), not invented here.
        cid = "%s.wavetable" % slot
        atlas[cid] = ReferenceControl(
            control_id=cid, display_name="Wavetable", panel=slot.upper(),
            control_type="enum", enum_values=tuple(snap["simple_wavetables"].keys()),
            aliases=("wavetable", "table", "wave table"),
            source=source_tag + " PresetSpec.OscillatorSpec.wavetable",
            notes="serum-mcp's curated wavetable set; a real preset may reference a "
                  "wavetable outside this curated list (e.g. a factory/third-party "
                  "table) -- absence from enum_values is not proof a name is invalid.",
        )

    for kparam, (suffix, aliases) in {
        "kParamNoiseType": ("noise_type", ("noise type",)),
        "kParamColor": ("color", ("color", "noise color")),
        "kParamOneShot": ("one_shot", ("one shot",)),
    }.items():
        if kparam not in snap["noise_oscillator"]:
            continue
        cid = "oscNoise.%s" % suffix
        atlas[cid] = _entry_from_schema(
            cid, suffix.replace("_", " ").title(), "NOISE",
            snap["noise_oscillator"][kparam], aliases, source_tag + " NoiseOscillator",
        )
    if "kParamShape" in snap["sub_oscillator"]:
        atlas["oscSub.shape"] = ReferenceControl(
            control_id="oscSub.shape", display_name="Sub Shape", panel="SUB",
            control_type="enum", enum_values=tuple(snap["simple_sub_shapes"].keys()),
            aliases=("sub shape", "sub waveform"), source=source_tag + " SubOscillator",
        )

    for slot in _FILTER_SLOTS:
        for kparam, (suffix, aliases) in _FILTER_FIELDS.items():
            if kparam not in snap["voice_filter"]:
                continue
            cid = "%s.%s" % (slot, suffix)
            entry = _entry_from_schema(
                cid, suffix.replace("_", " ").title(), slot.upper(),
                snap["voice_filter"][kparam], aliases, source_tag + " VoiceFilter",
            )
            if suffix == "type":
                # Filter TYPE has a real, separately-documented enum vocabulary
                # (simple_filter_types) that the raw kParam schema entry doesn't
                # carry on its own -- rebuild with it instead of leaving enum_values empty.
                entry = ReferenceControl(
                    control_id=cid, display_name="Filter Type", panel=slot.upper(),
                    control_type="enum", enum_values=tuple(snap["simple_filter_types"].keys()),
                    aliases=aliases, source=source_tag + " VoiceFilter.type + simple_filter_types",
                )
            atlas[cid] = entry

    for slot in _ENV_SLOTS:
        for kparam, (suffix, aliases) in _ENV_FIELDS.items():
            if kparam not in snap["envelope"]:
                continue
            cid = "%s.%s" % (slot, suffix)
            atlas[cid] = _entry_from_schema(
                cid, suffix.replace("_", " ").title(), slot.upper(),
                snap["envelope"][kparam], aliases, source_tag + " EnvelopeSpec",
            )

    for slot in _LFO_SLOTS:
        for kparam, (suffix, aliases) in _LFO_FIELDS.items():
            if kparam not in snap["lfo"]:
                continue
            cid = "%s.%s" % (slot, suffix)
            atlas[cid] = _entry_from_schema(
                cid, suffix.replace("_", " ").title(), slot.upper(),
                snap["lfo"][kparam], aliases, source_tag + " LfoSpec",
            )

    for slot in _MACRO_SLOTS:
        cid = "%s.value" % slot
        atlas[cid] = _entry_from_schema(
            cid, "Value", "MACROS", snap["macro"]["kParamValue"],
            ("macro value",), source_tag + " MacroSpec",
        )

    for kparam, (suffix, aliases) in _GLOBAL_FIELDS.items():
        if kparam not in snap["global"]:
            continue
        cid = "global.%s" % suffix
        atlas[cid] = _entry_from_schema(
            cid, suffix.replace("_", " ").title(), "GLOBAL",
            snap["global"][kparam], aliases, source_tag + " GlobalSpec",
        )

    # Matrix / modulation -- reuse qualify_modulation_route.py's already-real
    # source/destination domain vocabulary rather than re-deriving it here
    # (that module's SUPPORTED_SOURCE_PREFIXES/SUPPORTED_DESTINATION_FAMILIES
    # is itself read directly from serum-mcp's ModRouteSpec schema).
    from serum2.producer.qualify_modulation_route import (
        SUPPORTED_SOURCE_PREFIXES, SUPPORTED_DESTINATION_FAMILIES,
    )
    for kparam, (suffix, aliases) in _MOD_SLOT_FIELDS.items():
        if kparam not in snap["mod_matrix_slot"]:
            continue
        cid = "matrix.%s" % suffix
        atlas[cid] = _entry_from_schema(
            cid, suffix.replace("_", " ").title(), "MATRIX",
            snap["mod_matrix_slot"][kparam], aliases, source_tag + " ModRouteSpec (per-slot)",
        )
    atlas["matrix.source_vocabulary"] = ReferenceControl(
        control_id="matrix.source_vocabulary", display_name="Modulation Source Families",
        panel="MATRIX", control_type="topology",
        enum_values=SUPPORTED_SOURCE_PREFIXES,
        aliases=("modulation source", "mod source"),
        source="serum2.producer.qualify_modulation_route.SUPPORTED_SOURCE_PREFIXES "
               "(reused, not re-derived)",
        notes="Family prefixes only -- indexed families (lfo/macro/env/oscillator/filter) "
              "also have a real numeric range; see qualify_modulation_route.py's "
              "INDEXED_SOURCE_RANGES for the authoritative per-family bounds.",
    )
    atlas["matrix.destination_vocabulary"] = ReferenceControl(
        control_id="matrix.destination_vocabulary", display_name="Modulation Destination Families",
        panel="MATRIX", control_type="topology",
        enum_values=SUPPORTED_DESTINATION_FAMILIES,
        aliases=("modulation destination", "mod destination"),
        source="serum2.producer.qualify_modulation_route.SUPPORTED_DESTINATION_FAMILIES "
               "(reused, not re-derived)",
    )

    # FX -- module IDENTITY vocabulary only (real, from fx_type_ids). Full
    # per-type parameter enumeration is explicitly NOT done in this pass --
    # marking that gap honestly rather than fabricating coverage.
    for idx, fx_name in snap["fx_type_ids"].items():
        cid = "fx.%s" % fx_name.lower()
        atlas[cid] = ReferenceControl(
            control_id=cid, display_name=fx_name, panel="FX",
            control_type="module_identity",
            aliases=(fx_name.lower().replace("fx", "").strip() or fx_name.lower(),),
            source=source_tag + " fx_type_ids[%s]" % idx,
            notes="Module identity only -- this pass does not enumerate this "
                  "module's own parameter list (see fx_params in the schema "
                  "snapshot for a future pass); not yet in this Atlas.",
        )

    # Topology -- known canonical signal-path relationships, not numeric
    # controls. Recorded from OscillatorSpec.filter_routing / FilterSpec.
    # output_routing's real documented enum values (seen in this session's
    # serum-mcp edit_preset schema fetch).
    atlas["topology.oscillator_filter_routing"] = ReferenceControl(
        control_id="topology.oscillator_filter_routing", display_name="Oscillator -> Filter Routing",
        panel="TOPOLOGY", control_type="topology",
        enum_values=("filter", "master", "direct", "none"),
        aliases=("filter routing",),
        source=source_tag.replace("list_parameters()", "edit_preset schema") + " OscillatorSpec.filter_routing",
        notes="Per-oscillator: which path this oscillator's signal takes after "
              "leaving the oscillator itself.",
    )
    atlas["topology.filter_output_routing"] = ReferenceControl(
        control_id="topology.filter_output_routing", display_name="Filter Output Routing",
        panel="TOPOLOGY", control_type="topology",
        enum_values=("parallel", "series"),
        aliases=("filter routing", "series/parallel"),
        source=source_tag.replace("list_parameters()", "edit_preset schema") + " FilterSpec.output_routing",
        notes="Whether Filter 1/Filter 2 run in parallel (independent) or series (cascaded).",
    )

    # UI State Atlas v2: selectors/identities/graphs/regions/routes the flat
    # schema slice lacks -- merged here so there is still ONE registry.
    from serum2.reference.serum_ui_atlas import extra_reference_controls
    atlas.update(extra_reference_controls(set(atlas)))

    # Frozen local UI audit (908 records): enrich / extend the same registry.
    from serum2.reference.serum_audit import integrate_audit
    integrate_audit(atlas)

    return atlas


# Normalization match methods -- see normalize_control()'s docstring for
# the exact meaning of each. Mirrors the OBSERVED/OCCLUDED/... convention
# already established for visual_evidence.ControlState.status: a fixed,
# small, honest vocabulary, never silently collapsed.
EXACT = "EXACT"
ALIAS = "ALIAS"
UNRESOLVED = "UNRESOLVED"
AMBIGUOUS = "AMBIGUOUS"

_ATLAS: Optional[Dict[str, ReferenceControl]] = None
_ALIAS_INDEX: Optional[Dict[str, List[str]]] = None


def _ensure_loaded() -> None:
    global _ATLAS, _ALIAS_INDEX
    if _ATLAS is not None:
        return
    _ATLAS = _build_atlas()
    # Every candidate cid an alias could mean is kept (not just the first
    # inserted) -- e.g. "cutoff"/"cut off" are real aliases on BOTH
    # filter1.cutoff and filter2.cutoff (same field, two physical slots).
    # Silently keeping only the first (an earlier version of this index
    # used dict.setdefault() and did exactly that) would have made
    # "cutoff" quietly always mean Filter 1 -- a guess this module must
    # never make. See normalize_control()/resolve_alias_candidates().
    alias_index: Dict[str, List[str]] = {}
    for cid, entry in _ATLAS.items():
        for alias in entry.aliases:
            alias_index.setdefault(alias.lower(), []).append(cid)
    for alias in alias_index:
        alias_index[alias] = sorted(set(alias_index[alias]))
    _ALIAS_INDEX = alias_index


def atlas_provenance() -> Dict[str, Any]:
    """Exactly which reference data a resolution/episode used."""
    from serum2.reference.serum_audit import audit_provenance
    from serum2.reference.serum_ui_atlas import UI_ATLAS_VERSION
    return {"serum_version": SERUM_VERSION, "control_atlas_version": CONTROL_ATLAS_VERSION,
            "ui_atlas_version": UI_ATLAS_VERSION, **audit_provenance()}


def get_control(control_id: str) -> Optional[ReferenceControl]:
    _ensure_loaded()
    return _ATLAS.get(control_id)


def all_control_ids() -> List[str]:
    _ensure_loaded()
    return sorted(_ATLAS.keys())


@dataclass(frozen=True)
class Resolution:
    """Outcome of normalizing one raw label. `canonical_id` is set ONLY for
    EXACT/ALIAS; AMBIGUOUS carries every candidate instead of picking one;
    UNRESOLVED carries nothing. Says what a label MEANS, never what was seen
    or what value it holds."""
    status: str
    canonical_id: Optional[str] = None
    candidates: Tuple[str, ...] = ()
    raw: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "canonical_id": self.canonical_id,
                "candidates": list(self.candidates), "raw": self.raw,
                "atlas_version": ATLAS_VERSION, **atlas_provenance()}


_SLOT_RE = re.compile(
    r"(?<![a-z])(?:(env|lfo|macro|filter)\s*(\d+)|(osc)\s*([abc]|noise|sub)|(global|matrix))(?![a-z0-9])",
    re.I)
_NOISE_WORDS = {"knob", "slider", "control", "dropdown", "panel", "button", "toggle", "the"}


def _slot_of(m: "re.Match") -> str:
    if m.group(5):
        return m.group(5).lower()
    if m.group(1):
        return m.group(1).lower() + str(int(m.group(2)))
    tail = m.group(4)
    return "osc" + (tail.upper() if len(tail) == 1 else tail.capitalize())


def _slots_in(text: str) -> List[str]:
    return sorted({_slot_of(m) for m in _SLOT_RE.finditer(text or "")})


def normalize_control(raw: str, context: str = "") -> Resolution:
    """Map a raw observed label/id to a canonical Atlas control_id.
    The slot (env1, filter2, oscA...) comes from `raw` itself, else from
    `context` (e.g. the observer's screen_region). Two different slots in the
    same source, or a field name shared by several slots with no slot given
    ('cutoff' -> filter1/filter2), is AMBIGUOUS -- never a silent pick.
    EXACT = canonical id, or slot + canonical field/display name; ALIAS =
    matched through the alias vocabulary."""
    _ensure_loaded()
    raw = raw or ""
    if raw in _ATLAS:
        return Resolution(EXACT, raw, (raw,), raw)
    slots = _slots_in(raw) or _slots_in(context)
    known = {c.split(".", 1)[0] for c in _ATLAS}
    if len(slots) > 1:
        return Resolution(AMBIGUOUS, None, tuple(slots), raw)
    if slots and slots[0] not in known:
        return Resolution(UNRESOLVED, None, (), raw)
    field_text = _SLOT_RE.sub(" ", raw) if _slots_in(raw) else raw
    field_text = re.sub(r"[._\-/,>:()]+", " ", field_text.lower())
    field_text = " ".join(w for w in field_text.split() if w not in _NOISE_WORDS)
    if not field_text:
        return Resolution(UNRESOLVED, None, (), raw)
    exact, alias = [], []
    for cid, e in _ATLAS.items():
        if slots and cid.split(".", 1)[0] != slots[0]:
            continue
        if field_text in (cid.split(".", 1)[1].replace("_", " "), e.display_name.lower()):
            exact.append(cid)
        elif field_text in e.aliases:
            alias.append(cid)
    hits = sorted(exact + alias)
    fam = {"filter": "filter", "osc": "osc", "oscillator": "osc", "env": "env",
           "lfo": "lfo", "macro": "macro"}.get(field_text)
    if fam and not slots:  # bare family word: which slot is unknown
        slot_ids = sorted({c.split(".", 1)[0] for c in _ATLAS if c.startswith(fam)})
        return Resolution(AMBIGUOUS, None, tuple(slot_ids + hits), raw)
    if not hits:
        return Resolution(UNRESOLVED, None, (), raw)
    if len(hits) > 1:
        return Resolution(AMBIGUOUS, None, tuple(hits), raw)
    return Resolution(EXACT if exact else ALIAS, hits[0], tuple(hits), raw)


def normalize_mod_source(raw: str) -> Resolution:
    """Route source: lfoN/envN/macroN (Atlas slot ids) or a non-indexed
    source name. A bare family ('LFO') is AMBIGUOUS across its slots."""
    _ensure_loaded()
    from serum2.producer.qualify_modulation_route import NON_INDEXED_SOURCES
    raw = raw or ""
    norm = re.sub(r"[\s\-]+", "_", raw.strip().lower())
    if norm in NON_INDEXED_SOURCES:
        return Resolution(EXACT, norm, (norm,), raw)
    from serum2.reference.serum_audit import mod_source_slots
    slots = _slots_in(raw)
    known = mod_source_slots()  # audit MATRIX.SOURCE.*: lfo1-10, env1-4, macro1-8
    if len(slots) == 1 and re.match(r"(lfo|env|macro)\d", slots[0]):
        return (Resolution(EXACT, slots[0], (slots[0],), raw) if slots[0] in known
                else Resolution(UNRESOLVED, None, (), raw))
    fam = re.sub(r"\s+", "", raw.lower())
    if fam in ("lfo", "env", "macro"):
        return Resolution(AMBIGUOUS, None, tuple(sorted(k for k in known if k.startswith(fam))), raw)
    return Resolution(UNRESOLVED, None, (), raw)
