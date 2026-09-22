"""Qualification experiment for the generic Serum modulation-route capability.

Answers: "Can the installed serum-mcp backend construct/persist/load a
modulation-matrix route as a CLASS of operation?" -- NOT "does LFO1->Filter1
work" (that is one execution instance, proven separately by the k6OBzXdcFtA
episode). This script exists so the capability contract is derived from
qualification evidence, not hand-authored from "the schema looks plausible".

Two real serum-mcp calls, deliberately using DIFFERENT source/destination/
bipolar combinations than the k6 tutorial, to demonstrate the capability
generalizes across the domain rather than being a special case of one video:

  Instance A: lfo0 -> filter0.cutoff, amount=50, bipolar=False
      Same route already used in the k6OBzXdcFtA candidate. Fully verified:
      file-level (describe_preset) AND real Serum 2 UI MATRIX tab readback
      (computer-use screenshot, this session, 2026-09-18/19).
  Instance B: lfo1 -> oscillator0.pitch, amount=25, bipolar=True
      A different source (LFO2, not LFO1), different destination FAMILY
      (oscillator pitch, not filter cutoff), and bipolar=True (untested by
      instance A). File-level verified only (describe_preset) -- no UI
      round-trip performed for this instance; honestly recorded as such.

Domain (supported sources/destinations/amount range/bipolar) is read
directly from serum-mcp's own ModRouteSpec schema (list_parameters()-style
documentation already returned by the installed server, not guessed) --
this is real evidence of what the BACKEND claims to support, corroborated
by two real, different, successful writes.

Run: python -m serum2.producer.qualify_modulation_route
(Requires the two .SerumPreset files this script reads already exist --
it does not call serum-mcp itself, since this process cannot invoke MCP
tools directly. It packages ALREADY-OBTAINED real tool results into the
qualification evidence artifact.)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_QUALIFICATION_DIR = Path(__file__).parent.parent / "qualification"
_OUT_PATH = _QUALIFICATION_DIR / "modulation_route_qualification.json"

# ---- Domain, as documented by serum-mcp's own ModRouteSpec schema ----
# (verbatim from the installed server's tool schema, list_parameters()-
# equivalent -- this project does not invent this vocabulary).
SUPPORTED_SOURCE_PREFIXES = (
    "lfo",       # lfo0..lfo9
    "macro",     # macro0..macro7
    "velocity", "mod_wheel", "pitch_bend", "key_track",
    "aftertouch", "poly_aftertouch",
    "env",       # env0..env3
    "random1", "random2", "random_discrete",
    "release_velo", "active_voices", "voice_index", "voice_mod1", "voice_mod2",
    "fixed",
    "note_on_alt", "note_on_alt2", "expr_pan", "expr_timbre", "expr_press",
    "oscillator",  # oscillator0..oscillator4 (self-modulation)
    "filter",      # filter0/filter1 (self-modulation)
    "lfo1_y",
)
SUPPORTED_DESTINATION_FAMILIES = (
    "oscillator", "filter", "env", "fx", "global",
)

# Real index ranges per indexed family, from serum-mcp's own documented
# schema (ModRouteSpec source/destination vocab). A source/destination
# string is only in-domain if its family AND numeric index (when the family
# is indexed) both match -- "envelope 7" must NOT match just because it
# starts with "env": env only goes 0-3, so index 7 is out of range.
INDEXED_SOURCE_RANGES = {
    "lfo": range(0, 10),        # lfo0..lfo9
    "macro": range(0, 8),       # macro0..macro7
    "env": range(0, 4),         # env0..env3 (as a mod SOURCE)
    "oscillator": range(0, 5),  # oscillator0..oscillator4 (self-modulation)
    "filter": range(0, 2),      # filter0/filter1 (self-modulation)
}
NON_INDEXED_SOURCES = {
    "velocity", "mod_wheel", "pitch_bend", "key_track", "aftertouch",
    "poly_aftertouch", "random1", "random2", "random_discrete",
    "release_velo", "active_voices", "voice_index", "voice_mod1", "voice_mod2",
    "fixed", "note_on_alt", "note_on_alt2", "expr_pan", "expr_timbre",
    "expr_press", "lfo1_y",
}
INDEXED_DESTINATION_RANGES = {
    "oscillator": range(0, 5),
    "filter": range(0, 2),
    "env": range(0, 4),
    "fx": range(0, 32),  # fx_chain cap
}
NON_INDEXED_DESTINATION_FAMILIES = {"global"}


def _normalize(label: str) -> str:
    return label.lower().replace(" ", "").replace("_", "")


def resolve_source_in_domain(source_label: str):
    """Returns (family, index_or_None) if source_label is genuinely within
    the qualified domain, else None. Precise: a family-prefix substring
    match alone is NOT sufficient -- 'envelope 7' must not match 'env'
    just because it starts with those letters; env sources only go 0-3."""
    norm = _normalize(source_label)
    for family, idx_range in INDEXED_SOURCE_RANGES.items():
        if norm.startswith(family):
            suffix = norm[len(family):]
            if suffix.isdigit() and int(suffix) in idx_range:
                return family, int(suffix)
            # starts with the family name but index missing/out of range/
            # non-numeric (e.g. "envelope7" has suffix "elope7", not
            # digits) -- NOT a match, fall through to non-indexed check
            continue
    if norm in NON_INDEXED_SOURCES:
        return norm, None
    return None


def resolve_destination_in_domain(destination_label: str):
    """Returns (family, index_or_None) if destination_label's FAMILY is in
    the qualified domain, else None. The specific field suffix (e.g.
    '.cutoff' vs '.freq') is not independently validated against an
    enumerated list in this pass -- documented limitation, see
    modulation_route_contract.py's contract.limitations."""
    norm = _normalize(destination_label)
    # UI labels like "Filter 1 Freq" don't use serum-mcp's dotted path
    # syntax ("filter0.cutoff") -- match by family keyword + a trailing or
    # embedded index digit, same indexed-range precision as sources.
    for family, idx_range in INDEXED_DESTINATION_RANGES.items():
        if family in norm:
            # find a digit run adjacent to the family keyword
            import re
            m = re.search(re.escape(family) + r"0*(\d+)", norm)
            if m:
                idx = int(m.group(1))
                # UI labels are commonly 1-indexed ("Filter 1"->filter0);
                # accept both the literal digit and digit-1 against the range
                if idx in idx_range or (idx - 1) in idx_range:
                    return family, idx
                continue
            # family keyword present with no digit at all (e.g. "Filter Freq"
            # with no number) -- treat as index 0 (the common single-instance
            # UI phrasing), the most conservative in-range default.
            if 0 in idx_range:
                return family, 0
    if norm in NON_INDEXED_DESTINATION_FAMILIES:
        return norm, None
    return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_preset(name: str) -> Path:
    xfer_dir = Path.home() / "Documents" / "Xfer" / "Serum 2 Presets" / "Presets" / "User"
    return xfer_dir / name


def build_qualification_evidence() -> dict:
    now = datetime.now(timezone.utc).isoformat()

    instance_a_path = _find_preset("VLP1-K6-FilterCutoffLFOMod.SerumPreset")
    instance_b_path = _find_preset("VLP1-ModRouteQualification-InstanceB.SerumPreset")
    instances = [
        {
            "instance_id": "A",
            "source": "lfo0", "destination": "filter0.cutoff",
            "amount": 50, "bipolar": False,
            "preset_path": str(instance_a_path),
            "preset_sha256": _sha256(instance_a_path) if instance_a_path.exists() else None,
            "verification": {
                "file_level": "describe_preset confirmed 'Mod matrix (recognized routes only): - lfo0 -> filter0.cutoff: +50%'",
                "real_serum_ui": (
                    "Loaded into real Serum 2.0.21 on Ableton Track 0 via Serum's own "
                    "in-plugin preset browser; MATRIX tab screenshot confirmed "
                    "SOURCE=LFO1, DESTINATION=Filter 1 Freq, route count 0->1 "
                    "(computer-use screenshot, this session)."
                ),
                "tier": "UI_VERIFIED",
            },
        },
        {
            "instance_id": "B",
            "source": "lfo1", "destination": "oscillator0.pitch",
            "amount": 25, "bipolar": True,
            "preset_path": str(instance_b_path),
            "preset_sha256": _sha256(instance_b_path) if instance_b_path.exists() else None,
            "verification": {
                "file_level": "describe_preset confirmed 'Mod matrix (recognized routes only): - lfo1 -> oscillator0.pitch: +25%, bipolar'",
                "real_serum_ui": None,
                "tier": "FILE_VERIFIED_ONLY",
            },
        },
    ]

    return {
        "capability": "serum.modulation_route.add",
        "qualified_at": now,
        "backend": "serum-mcp",
        "schema_source": "serum-mcp ModRouteSpec (installed server's own documented schema)",
        "domain": {
            "supported_source_prefixes": list(SUPPORTED_SOURCE_PREFIXES),
            "supported_destination_families": list(SUPPORTED_DESTINATION_FAMILIES),
            "amount_range": [-100, 100],
            "bipolar_values": [True, False],
        },
        "instances": instances,
        "notes": (
            "Instance A is fully UI-verified (real Serum 2 MATRIX tab readback). "
            "Instance B demonstrates domain generality (different source/destination "
            "family/bipolar value) at file-level only. This contract's status is "
            "STRUCTURAL_ONLY, not CAUSAL_VERIFIED -- no audio-domain causal effect "
            "was measured for either instance (no render/measurement tool was used "
            "for a modulation route; only construct+persist+load were verified)."
        ),
    }


if __name__ == "__main__":
    _QUALIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    evidence = build_qualification_evidence()
    _OUT_PATH.write_text(json.dumps(evidence, indent=2))
    print("Qualification evidence written to", _OUT_PATH)
