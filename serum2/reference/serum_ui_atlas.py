"""Serum 2 UI State Atlas v2 -- the STRUCTURE over the one Reference Atlas.

SCOPE NOTE: the frozen local audit (serum_audit.py, 908 records) covers the
mixer, FX, clip, arp, keyboard, browser, sub and noise surfaces in far more
depth than the PDF, so those PDF-derived surfaces were REMOVED from here; only
what the audit lacks (oscillator mode/identities/graphs/regions, filter/env/
LFO/matrix supplements) remains as PDF-derived supplement.

    ReferenceSurface  ->  ReferenceMode  ->  ReferenceElement (+ kind)

serum_atlas.py stays the single registry of canonical control ids. This
module adds (a) the hierarchy -- which surface an element lives on and which
oscillator/FX mode exposes it -- and (b) the elements the flat, schema-only
Atlas could not express: selectors, text identities, graphs, curves, regions,
routes, topology. Elements the flat Atlas already has are NOT redefined; the
hierarchy just points at them (same canonical id). Missing ones are merged
into the flat Atlas by extra_reference_controls(), so there is still one
registry and normalize_control() resolves both.

Evidence for every element is recorded in `source`:
  "schema"        -- already in the serum-mcp schema snapshot (flat Atlas)
  "pdf pN"        -- Serum 2 "What's New" (v1.0.0, 2025-03-17) page N text
  "screenshot pN" -- a label legible in that page's UI screenshot
Nothing here states a range/unit/default the source did not establish, and
where a screenshot label's meaning is not established the note says so.

HARD BOUNDARY: reference knowledge only. It does not decide what a census
looks at (the observer inspects everything visible, Atlas-listed or not), it
is never observed state, and it has no execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

UI_ATLAS_VERSION = "serum-2.0.21-ui-atlas-v2"

CONTROL, SELECTOR, TEXT_IDENTITY, GRAPH, CURVE, REGION, ROUTE, TOPOLOGY, ENABLE_STATE = (
    "CONTROL", "SELECTOR", "TEXT_IDENTITY", "GRAPH", "CURVE", "REGION", "ROUTE",
    "TOPOLOGY", "ENABLE_STATE")
ELEMENT_KINDS = (CONTROL, SELECTOR, TEXT_IDENTITY, GRAPH, CURVE, REGION, ROUTE,
                 TOPOLOGY, ENABLE_STATE)

# flat-Atlas control_type per kind, for elements merged into the one registry
_FLAT_TYPE = {CONTROL: "continuous", SELECTOR: "enum", ENABLE_STATE: "toggle",
              ROUTE: "topology", TOPOLOGY: "topology", TEXT_IDENTITY: "text_identity",
              GRAPH: "graph", CURVE: "curve", REGION: "region"}


@dataclass(frozen=True)
class ReferenceElement:
    element_id: str            # suffix; canonical id = "<instance>.<element_id>"
    kind: str
    label: str
    source: str
    values: Tuple[str, ...] = ()   # selector vocabulary, only if the source lists it
    notes: Optional[str] = None
    aliases: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ReferenceMode:
    mode_id: str
    elements: Tuple[ReferenceElement, ...]
    notes: Optional[str] = None


@dataclass(frozen=True)
class ReferenceSurface:
    surface_id: str
    instances: Tuple[str, ...]     # canonical-id prefixes, e.g. oscA/oscB/oscC
    common: Tuple[ReferenceElement, ...] = ()   # present in every mode
    modes: Tuple[ReferenceMode, ...] = ()
    notes: Optional[str] = None


def E(eid, kind, label, source, values=(), notes=None, aliases=()):
    return ReferenceElement(eid, kind, label, source, tuple(values), notes, tuple(aliases))


_OSC_MODES = ("WAVETABLE", "MULTISAMPLE", "SAMPLE", "GRANULAR", "SPECTRAL")
_WARP_VALUES = ("Off", "Sync", "Alt Warp", "Filter", "Distortion", "FM", "PD", "AM", "RM")
_WARP_NOTE = ("Menu items as shown in the p7 screenshot (plus a 'Swap Warps' action); "
              "submenus (Alt Warp/Filter/Distortion/FM/PD/AM/RM) are not enumerated.")


def _warps(src):
    return (
        E("warp_mode", SELECTOR, "Warp 1 mode", src, _WARP_VALUES, _WARP_NOTE),
        E("warp_amount", CONTROL, "Warp 1 amount", "schema"),
        E("warp_mode2", SELECTOR, "Warp 2 mode (dual warp)", src, _WARP_VALUES, _WARP_NOTE),
        E("warp_amount2", CONTROL, "Warp 2 amount", "schema"),
    )


_SAMPLE_REGIONS = (
    E("sample_region", REGION, "Sample start/end points", "pdf p8",
      notes="Adjustable and modulatable start/end (p8); 'also available in Granular and Spectral'."),
    E("loop_region", REGION, "Loop start/end points (LS/LE)", "pdf p8; screenshot p8"),
    E("sample_loop_mode", SELECTOR, "Playback / loop mode", "schema",
      values=("ONE-SHOT", "FWD LOOP"),
      notes="Values are the two seen in p8 screenshots; the full list is not established."),
    E("sample_loop_start", CONTROL, "Loop start", "schema"),
    E("sample_loop_end", CONTROL, "Loop end", "schema"),
    E("sample_loop_crossfade", CONTROL, "Loop crossfade", "schema"),
    E("slicing_mode", SELECTOR, "Slicing (auto / manual)", "pdf p8",
      notes="'Auto and manual slicing modes with advanced options' -- options not enumerated."),
)

_OSCILLATOR = ReferenceSurface(
    "oscillator", ("oscA", "oscB", "oscC"),
    common=(
        E("mode", SELECTOR, "Oscillator mode", "pdf p6", _OSC_MODES,
          "Determines which mode-specific elements are exposed.", ("oscillator mode",)),
        E("enabled", ENABLE_STATE, "Oscillator on/off", "schema"),
        E("octave", CONTROL, "OCT", "schema"), E("semitone", CONTROL, "SEM", "schema"),
        E("fine", CONTROL, "FIN", "schema"),
        E("crs", CONTROL, "CRS", "screenshot p7",
          notes="Label seen beside OCT/SEM/FIN; its relation to schema kParamCoarsePit "
                "(flat id 'semitone') is not established."),
        E("routing", ROUTE, "Oscillator output routing", "pdf p7; screenshot p7",
          ("Filter", "Main", "Direct", "None"),
          "Menu items from the p7 screenshot; matches schema OscillatorSpec.filter_routing. "
          "'Easy routing to multiple targets' -- multi-target state may need `detail`."),
        E("unison", CONTROL, "UNISON", "schema", notes="Enhanced unison configuration (p7); "
          "extra unison options are not enumerated in the source."),
        E("detune", CONTROL, "DETUNE", "schema"), E("blend", CONTROL, "BLEND", "screenshot p7"),
        E("pan", CONTROL, "PAN", "schema"), E("level", CONTROL, "LEVEL", "schema"),
    ),
    modes=(
        ReferenceMode("WAVETABLE", (
            E("wavetable", TEXT_IDENTITY, "Wavetable name", "schema",
              notes="Raw displayed name is the evidence; never derive it from wt_position."),
            E("wt_position", CONTROL, "WT POS", "schema"),
            E("wt_interpolation_mode", SELECTOR, "WT interpolation (smooth)", "schema"),
            E("tuning_mode", SELECTOR, "Tuning mode", "pdf p7",
              ("semitone", "harmonics", "ratio", "step"),
              "'modes for octaves and semitones' (p7)."),
            *_warps("pdf p7; screenshot p7"),
            E("phase", CONTROL, "Phase", "schema"),
            E("random_phase", CONTROL, "Phase randomization (RAND)", "schema"),
            E("waveform_display", GRAPH, "Wavetable/waveform display", "pdf p7; screenshot p7"),
        )),
        ReferenceMode("MULTISAMPLE", (
            E("instrument_identity", TEXT_IDENTITY, "Multisample instrument name", "screenshot p9",
              notes="SFZ loading supported (p9)."),
            E("timbre", CONTROL, "TIMBRE (timbre shifting)", "pdf p9; screenshot p9"),
            E("vel_track", CONTROL, "VEL TRACK", "screenshot p9"),
            E("sample_envelope", CURVE, "Envelope", "pdf p9"),
            E("random_phase", CONTROL, "RAND", "schema"),
            *_warps("screenshot p9"),
            E("keyzone_display", GRAPH, "Multisample zone display", "screenshot p9"),
        )),
        ReferenceMode("SAMPLE", (
            E("sample_identity", TEXT_IDENTITY, "Sample name", "screenshot p8"),
            E("scan", CONTROL, "SCAN", "screenshot p8"),
            *_SAMPLE_REGIONS, *_warps("pdf p8"),
            E("sample_display", GRAPH, "Sample waveform display", "pdf p8; screenshot p8"),
        )),
        ReferenceMode("GRANULAR", (
            E("sample_identity", TEXT_IDENTITY, "Sample name", "screenshot p9"),
            E("scan", CONTROL, "SCAN", "screenshot p9"),
            E("density", CONTROL, "DENS", "screenshot p9"),
            E("length", CONTROL, "LENGTH", "screenshot p9"),
            E("offset", CONTROL, "OFFSET", "screenshot p9"),
            E("direction", CONTROL, "DIR", "screenshot p9"),
            E("pitch", CONTROL, "PITCH", "screenshot p9"),
            E("grain_rand_1", CONTROL, "RAND (1 of 3)", "screenshot p9",
              notes="Three unlabeled-association RAND knobs; which parameter each randomizes "
                    "is not established."),
            E("grain_rand_2", CONTROL, "RAND (2 of 3)", "screenshot p9"),
            E("grain_rand_3", CONTROL, "RAND (3 of 3)", "screenshot p9"),
            E("grain_count", CONTROL, "Grain count", "pdf p9", notes="'up to 256 grains'."),
            E("window_amount", CONTROL, "Window amount", "pdf p9"),
            E("warp_mode", SELECTOR, "WARP", "screenshot p9", _WARP_VALUES),
            *_SAMPLE_REGIONS,
            E("sample_display", GRAPH, "Granular waveform display", "screenshot p9"),
        ), notes="Complete granular parameter list is not enumerated by the source."),
        ReferenceMode("SPECTRAL", (
            E("sample_identity", TEXT_IDENTITY, "Sample name", "screenshot p9"),
            E("scan", CONTROL, "SCAN (scan rate: speed and direction)", "pdf p9"),
            E("spectral_cut", CONTROL, "CUT", "screenshot p9"),
            E("spectral_filter", CONTROL, "FILTER", "screenshot p9",
              notes="CUT/FILTER/MIX meanings not established beyond 'Hi/Low Freqs' (p9)."),
            E("spectral_mix", CONTROL, "MIX", "screenshot p9"),
            E("spectral_freq_range", REGION, "Hi/Low frequencies", "pdf p9"),
            *_warps("screenshot p9"), *_SAMPLE_REGIONS,
            E("spectral_display", GRAPH, "Spectrogram display", "screenshot p9"),
        )),
    ),
)

_ENV_LFO_NOTE = "LFO 7-10 are headless mod sources with no parameters (audit MATRIX.SOURCE.LFO_7..10)."

_SURFACES: Tuple[ReferenceSurface, ...] = (
    _OSCILLATOR,
    ReferenceSurface("filter", ("filter1", "filter2"), (
        E("enabled", ENABLE_STATE, "Filter on/off ('use one or both')", "schema"),
        E("type", SELECTOR, "Filter type", "schema"),
        E("cutoff", CONTROL, "Cutoff", "schema"), E("resonance", CONTROL, "Resonance", "schema"),
        E("drive", CONTROL, "Drive", "schema"),
        E("drive_mode", SELECTOR, "Drive mode (incl. new Clean)", "pdf p10",
          notes="Only 'Clean' is named by the source."),
        E("wet", CONTROL, "Mix", "schema"), E("key_track", CONTROL, "Key track", "schema"),
        E("response_graph", GRAPH, "Filter response graph (direct cutoff/resonance)", "pdf p10, p16"),
    ), notes="Series/parallel routing is topology.filter_output_routing."),
    ReferenceSurface("topology", ("topology",), (
        E("filter_output_routing", TOPOLOGY, "Filter series/parallel routing", "schema"),
        E("oscillator_filter_routing", TOPOLOGY, "Oscillator -> filter routing", "schema"),
    )),
    ReferenceSurface("envelope", ("env1", "env2", "env3", "env4"), (
        E("attack", CONTROL, "ATK", "schema"), E("hold", CONTROL, "HOLD", "schema"),
        E("decay", CONTROL, "DEC", "schema"), E("sustain", CONTROL, "SUS", "schema"),
        E("release", CONTROL, "REL", "schema"),
        E("time_mode", SELECTOR, "Time mode (MS / BPM)", "pdf p14",
          ("MS", "BPM"), "'MS' is the value read in the real mU6 census; BPM per p14 "
          "('follow host tempo').", ("mode", "time mode", "bpm")),
        E("invert_legato", ENABLE_STATE, "Invert legato", "pdf p14"),
        E("curve_display", GRAPH, "Envelope display", "pdf p11"),
    )),
    ReferenceSurface("lfo", tuple("lfo%d" % i for i in range(1, 7)), (
        E("shape", SELECTOR, "Curve / shape", "schema"), E("rate", CONTROL, "Rate", "schema"),
        E("mode", SELECTOR, "Trigger mode", "schema"),
        E("beat_sync", ENABLE_STATE, "Sync", "schema"),
        E("curve_display", GRAPH, "LFO graph / drawing editor", "pdf p14"),
        E("chaos_mode", SELECTOR, "Chaos mode", "pdf p14", ("Lorenz", "Rossler")),
        E("grid_x", CONTROL, "Grid X", "pdf p14", notes="Independent X/Y grid."),
        E("grid_y", CONTROL, "Grid Y", "pdf p14"),
        E("phase", CONTROL, "Phase", "pdf p14", notes="'Set and modulate the phase'."),
        E("playback_direction", SELECTOR, "Directional playback", "pdf p14"),
        E("preset_identity", TEXT_IDENTITY, "LFO preset", "pdf p14"),
    ), notes=_ENV_LFO_NOTE + " 'Follow swing' is stated by the source but its control is "
             "not identified (schema kParamSwing may be it)."),
    ReferenceSurface("matrix", ("matrix",), (
        E("routes", ROUTE, "Modulation rows (source, destination, amount, polarity, aux)",
          "pdf p15", notes="Structural: use `detail` for per-row source/destination/aux/"
          "bypass/order."),
        E("aux_source", ROUTE, "Aux source", "pdf p15"),
        E("order", TOPOLOGY, "Row ordering", "pdf p15"),
        E("source_curve", CURVE, "Source scale curve", "pdf p15",
          notes="May correspond to schema kParamCurveIn; not established."),
        E("aux_curve", CURVE, "Aux source scale curve", "schema"),
        E("bypass", ENABLE_STATE, "Row bypass", "schema"),
    )),
)

SURFACES: Dict[str, ReferenceSurface] = {s.surface_id: s for s in _SURFACES}


def elements_for(surface_id: str, mode: Optional[str] = None) -> Tuple[ReferenceElement, ...]:
    """Common elements, plus the given mode's elements when `mode` is set."""
    s = SURFACES[surface_id]
    extra = [e for m in s.modes if m.mode_id == mode for e in m.elements]
    return tuple(s.common) + tuple(extra)


def _all_entries():
    """(canonical_id, element, surface_id, modes-exposing-it) for every instance."""
    for s in _SURFACES:
        by_el: Dict[str, Tuple[ReferenceElement, List[str]]] = {}
        for m in s.modes:
            for e in m.elements:
                by_el.setdefault(e.element_id, (e, []))[1].append(m.mode_id)
        for inst in s.instances:
            for e in s.common:
                yield "%s.%s" % (inst, e.element_id), e, s.surface_id, ()
            for e, modes in by_el.values():
                if s.surface_id == "fx":  # module-specific: id carries the module
                    for mod in modes:
                        yield "%s.%s.%s" % (inst, mod.lower(), e.element_id), e, s.surface_id, (mod,)
                else:
                    yield "%s.%s" % (inst, e.element_id), e, s.surface_id, tuple(modes)


def describe(canonical_id: str) -> Optional[Dict[str, object]]:
    """Where a canonical id sits, or None if neither the v2 hierarchy nor the
    audit places it. Audit-backed ids add module/status/conditional_visibility;
    `modes` is the v2 (PDF-derived) placement, falling back to the audit's own
    mode-dependence note; the audit's list is always exposed as `audit_modes`."""
    from serum2.reference.serum_atlas import get_control
    out: Optional[Dict[str, object]] = None
    for cid, e, sid, modes in _all_entries():
        if cid == canonical_id:
            out = {"surface": sid, "kind": e.kind, "modes": list(modes), "source": e.source}
            break
    c = get_control(canonical_id)
    rec = c.audit if c else None
    if rec:
        out = out or {"surface": rec["section"].lower(), "kind": c.element_kind, "modes": [],
                      "source": "audit"}
        cv = rec.get("conditional_visibility") or ""
        out.update(audit_id=rec["semantic_id"], module=rec.get("module"),
                   audit_status=rec.get("status"), conditional_visibility=cv or None)
        if "Mode-dependent rendering" in cv:
            # the audit's own statement (all five modes share the slot); kept
            # SEPARATE from `modes` (the PDF-derived per-mode placement) so the
            # two sources are never silently merged or contradicted
            out["mode_dependent"] = True
            out["audit_modes"] = [m.upper() for m in _OSC_MODE_NAMES if m.lower() in cv.lower()]
            out["modes"] = out["modes"] or out["audit_modes"]
    return out


_OSC_MODE_NAMES = ("Wavetable", "Sample", "Multisample", "Granular", "Spectral")


def extra_reference_controls(existing_ids):
    """ReferenceControl entries for v2 elements the flat Atlas lacks; merged by
    serum_atlas._build_atlas so there is a single registry. Existing entries are
    never overridden."""
    from serum2.reference.serum_atlas import ReferenceControl
    out = {}
    for cid, e, sid, _modes in _all_entries():
        if cid in existing_ids or cid in out:
            continue
        out[cid] = ReferenceControl(
            control_id=cid, display_name=e.label, panel=sid.upper(),
            control_type=_FLAT_TYPE[e.kind], enum_values=e.values,
            aliases=tuple(a.lower() for a in e.aliases),
            source="ui-atlas-v2 (%s)" % e.source, notes=e.notes)
    return out
