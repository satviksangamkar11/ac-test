"""Bridge from the frozen local Serum 2 UI audit into the ONE Reference Atlas.

Source: serum2/reference/audit/SERUM2_SEMANTIC_INVENTORY_FINAL.json -- a
verbatim copy of D:\\ableton claude\\serum2\\reconciliation\\ (908 records,
Serum 2.0.21 live-UI/tutorial/code evidence). Its SHA-256 is pinned by the
audit's own freeze manifest and re-verified at load; a mismatch raises.

This module adds NO second registry: integrate_audit() enriches existing
Atlas entries (never overriding schema-derived fields) or adds the audit
records the Atlas lacked, under Atlas-style canonical ids. Every entry keeps
its full raw audit record (sources, evidence_type, status, notes,
conditional_visibility) in ReferenceControl.audit.

What the audit is NOT: an observation checklist, execution authority, or a
per-mode/graph-coordinate model. It records mode-dependence only as a text
note, has no structured screen coordinates, and no oscillator-mode selector
or wavetable-identity element (those remain PDF-derived supplements in
serum_ui_atlas.py).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

_DIR = Path(__file__).parent / "audit"
_AUDIT_PATH = _DIR / "SERUM2_SEMANTIC_INVENTORY_FINAL.json"
_MANIFEST_PATH = _DIR / "SERUM2_SEMANTIC_FREEZE_MANIFEST.json"

_NS = {"OSC1": "oscA", "OSC2": "oscB", "OSC3": "oscC", "FILTER1": "filter1",
       "FILTER2": "filter2", "SUB_OSC": "oscSub", "NOISE_OSC": "oscNoise"}
# Audit field -> existing Atlas suffix, where the names differ but denote the
# same kParam/UI control. Same-name (case-insensitive) fields need no entry.
# These are NAME-EQUIVALENCE bridges (basis "TABLE"), not independently
# verified against Serum.
_FIELD_TABLE = {
    "OSC": {"SEMI": "semitone", "WT_POS": "wt_position", "UNI_DETUNE": "detune",
            "UNI_BLEND": "blend", "RAND_PHASE": "random_phase", "WARP": "warp_amount",
            "WARP_2": "warp_amount2", "WARP_2_MODE": "warp_mode2",
            "LOOP_X-FADE": "sample_loop_crossfade", "LOOP_START": "sample_loop_start",
            "LOOP_END": "sample_loop_end", "LOOP_MODE": "sample_loop_mode"},
    "FILTER": {"KEYTRACK": "key_track"},
    "ENV": {"LEGATOINVERTED": "invert_legato", "ATK_CURVE": "attack_curve",
            "DEC_CURVE": "decay_curve", "REL_CURVE": "release_curve"},
    "LFO": {"TYPE": "shape", "TEMPO_SYNC": "beat_sync", "TRIPLET": "triplets",
            "DIRECTION": "playback_direction", "WAVEFORM_GRAPH": "curve_display",
            "PRESET": "preset_identity", "TRIGGER_MODE": "mode"},
}
# The audit itself (R7 ownership resolution) retracted OSC Enable/Level/Pan as
# duplicates of the MIXER records: one semantic, several UI surfaces. So
# MIXER.OSC_x.{ENABLE,PAN,LEVEL} ARE the oscillator's own controls.
_MIXER_OSC = {"OSC_A": "oscA", "OSC_B": "oscB", "OSC_C": "oscC"}
_MIXER_FIELDS = {"ENABLE": "enabled", "PAN": "pan", "LEVEL": "level"}


_CACHE: Optional[Dict[str, Any]] = None


def load_audit() -> Dict[str, Any]:
    """Verified audit: {"meta", "records", "sha256", "manifest"}."""
    global _CACHE
    if _CACHE is None:
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        digest = hashlib.sha256(_AUDIT_PATH.read_bytes()).hexdigest()
        if digest != manifest["artifact_sha256"]:
            raise RuntimeError("audit hash %s != frozen manifest %s"
                               % (digest, manifest["artifact_sha256"]))
        d = json.loads(_AUDIT_PATH.read_text(encoding="utf-8"))
        if len(d["records"]) != manifest["semantic_count"]:
            raise RuntimeError("audit record count != manifest semantic_count")
        _CACHE = {"meta": d["meta"], "records": d["records"], "sha256": digest,
                  "manifest": manifest}
    return _CACHE


def audit_provenance() -> Dict[str, Any]:
    a = load_audit()
    return {"source_audit_file": "SERUM2_SEMANTIC_INVENTORY_FINAL.json",
            "source_audit_version": a["meta"]["inventory_version"],
            "source_audit_hash": a["sha256"],
            "source_audit_record_count": len(a["records"])}


def _slot(head: str) -> Optional[str]:
    if head in _NS:
        return _NS[head]
    m = re.fullmatch(r"(ENV|LFO)(\d+)", head)
    return m.group(1).lower() + m.group(2) if m else None


def bridge(semantic_id: str, atlas_ids) -> tuple:
    """(canonical_id, basis). basis: EXACT_NAME | TABLE | DERIVED_NEW."""
    parts = semantic_id.split(".")
    if parts[0] == "MACRO" and len(parts) == 3 and parts[1].isdigit():
        cid = "macro%d.%s" % (int(parts[1]), parts[2].lower())
        return cid, ("EXACT_NAME" if cid in atlas_ids else "DERIVED_NEW")
    if (parts[0] == "MIXER" and len(parts) == 3 and parts[1] in _MIXER_OSC
            and parts[2] in _MIXER_FIELDS):
        return "%s.%s" % (_MIXER_OSC[parts[1]], _MIXER_FIELDS[parts[2]]), "TABLE"
    slot = _slot(parts[0])
    if slot and len(parts) == 2:
        fam = "OSC" if slot in ("oscA", "oscB", "oscC") else re.sub(r"\d+$", "", slot).upper()
        tbl = _FIELD_TABLE.get(fam, {})
        if parts[1] in tbl and "%s.%s" % (slot, tbl[parts[1]]) in atlas_ids:
            return "%s.%s" % (slot, tbl[parts[1]]), "TABLE"
        cid = "%s.%s" % (slot, parts[1].lower().replace("-", "_"))
        if cid in atlas_ids:
            return cid, "EXACT_NAME"
    prefix = slot or parts[0].lower()
    rest = ".".join(p.lower().replace("-", "_").replace("#", "num") for p in parts[1:])
    return "%s.%s" % (prefix, rest), "DERIVED_NEW"


_CONTROL = {"continuous", "knob", "scalar", "integer", "fader", "draggable_value", "stepper",
            "slider", "numeric", "numeric_stepper", "draggable_slider", "range_slider"}
_SELECTOR = ("dropdown", "enum", "menu", "tab_selector", "submenu_select", "cascading_menu")
_ROUTE = ("source_target", "destination_target", "structural_source_selection")
_TOPOLOGY = ("topology_module", "nested_rack", "compound_module", "drag_reorder", "tree")


def element_kind(semantic_id: str, control_type: Optional[str]) -> Optional[str]:
    """Conservative classification of an audit record into the UI-atlas element
    kinds; None = not classifiable without guessing (raw control_type is kept)."""
    ct = (control_type or "").lower()
    sid = semantic_id.upper()
    if "GRAPH" in sid or ct.startswith(("graph", "display")):
        return "GRAPH"
    if "curve" in ct:
        return "CURVE"
    if ct in _CONTROL:
        return "CONTROL"
    if ct == "identity" or ct.startswith("text"):
        return "TEXT_IDENTITY"
    if ct in _ROUTE or ct.startswith(("destination_target", "source_target")):
        return "ROUTE"
    if ct in _TOPOLOGY:
        return "TOPOLOGY"
    if ct.startswith(_SELECTOR) or ct.endswith("_select"):
        return "SELECTOR"
    if ct in ("toggle", "boolean", "checkbox", "toggle_buttons") and re.search(r"ENABLE|BYPASS|MUTE", sid):
        return "ENABLE_STATE"
    return None


def integrate_audit(atlas: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich/extend the Atlas registry in place from the verified audit."""
    from serum2.reference.serum_atlas import ReferenceControl, _SLOT_RE
    ids = set(atlas)
    seen: Dict[str, str] = {}
    for rec in load_audit()["records"]:
        sid = rec["semantic_id"]
        cid, basis = bridge(sid, ids)
        if cid in seen:
            raise RuntimeError("audit ids %s and %s both bridge to %s" % (seen[cid], sid, cid))
        seen[cid] = sid
        label = _SLOT_RE.sub(" ", rec.get("label") or "").lower()
        label = " ".join(re.sub(r"[._\-/,]+", " ", label).split())
        kind = element_kind(sid, rec.get("control_type"))
        if cid in atlas:
            e = atlas[cid]
            atlas[cid] = dataclasses.replace(
                e, audit=rec, audit_bridge=basis, element_kind=kind or e.element_kind,
                aliases=tuple(dict.fromkeys(e.aliases + ((label,) if label else ()))))
        else:
            vr = rec.get("value_range")
            lo, hi = (vr if isinstance(vr, list) and len(vr) == 2
                      and all(isinstance(v, (int, float)) for v in vr) else (None, None))
            atlas[cid] = ReferenceControl(
                control_id=cid, display_name=rec.get("label") or sid, panel=rec["section"],
                control_type=rec.get("control_type") or "unknown", default_value=rec.get("default"),
                min_value=lo, max_value=hi,
                enum_values=tuple(o for o in (rec.get("options") or []) if isinstance(o, str)),
                aliases=(label,) if label else (),
                source="audit:SERUM2_SEMANTIC_INVENTORY_FINAL#" + sid,
                notes=rec.get("notes"), audit=rec, audit_bridge=basis, element_kind=kind)
    return atlas


def mod_source_slots() -> frozenset:
    """lfo1..lfo10 / env1..4 / macro1..8 as the audit's MATRIX.SOURCE.* records
    establish them (LFO 7-10 exist as mod sources only)."""
    out = set()
    for rec in load_audit()["records"]:
        m = re.fullmatch(r"MATRIX\.SOURCE\.(LFO|ENV|MACRO)_(\d+)", rec["semantic_id"])
        if m:
            out.add(m.group(1).lower() + m.group(2))
    return frozenset(out)
