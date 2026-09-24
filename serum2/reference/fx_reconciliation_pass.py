"""FX-only reconciliation pass over the 29 Atlas FX controls whose registry disposition is UNKNOWN.

Writes parameter_characterization/fx_reconciliation_pass.json. Read-only w.r.t. the binding table, surface, and
registry: it never adds a binding. A control is DIRECT_BIND only if serum_mcp_binding_table.json already binds it
(this pass adds none: no control has evidence tying the Atlas control to a raw kParam). Run:
    python -m serum2.reference.fx_reconciliation_pass
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "serum-mcp" / "src"))

REGISTRY = ROOT / "parameter_characterization" / "serum2_master_parameter_registry.json"
BINDINGS = Path(__file__).parent / "serum_mcp_binding_table.json"
OUT = ROOT / "parameter_characterization" / "fx_reconciliation_pass.json"

# Rule-derived by Atlas control_type (no per-control branching).
BY_CONTROL_TYPE = {
    "module_identity": ("STRUCTURAL", "fx_chain[i].type / rack / order (FxUnitSpec.type + FX_TYPE_IDS): chain topology, not a scalar param"),
    "list_with_controls": ("STRUCTURAL", "per-rack module list: order, bypass, remove == fx_chain list edits; no scalar param"),
    "resource_browser": ("BROWSER_EXTERNAL", "IR resource selection; FXConv schema has no IR key and mapping.py has no IR writer"),
    "resource_nav": ("BROWSER_EXTERNAL", "IR list navigation; UI-only traversal of a resource list"),
    "file_dialog": ("BROWSER_EXTERNAL", "external file dialog; Atlas notes it was never opened, no MCP path"),
    "decorative_icon": ("UI_ONLY", "confirmed non-interactive (hover/click/right-click all negative)"),
}
# Reviewed per-control dispositions for the rest. `missing` = the exact evidence still required.
REVIEWED = {
    "fx.flanger.no_separate_delay_knob": ("UI_ONLY", "negative observation, not a control; FXFlanger FX_PARAMS has no delay kParam (Rate/Depth/Feedback/Width/Wet)", None),
    "fx.compressor.mode": ("UNRESOLVED", "SINGLE/MULTIBAND branch; FXComp FX_PARAMS (Thresh/Ratio/Attack/Release/Makeup/Wet) has no mode key and no corpus/mapping evidence names one",
                           "raw kParam key (and value encoding) that toggles Multiband, via a preset diff of Single vs Multiband saved by real Serum"),
    "fx.distortion.filter_position": ("UNRESOLVED", "OFF/PRE/POST; FXDistortion FX_PARAMS has no such key. targets.py lists 'PrePost' but the control matrix marks it NOT_YET_DERIVED",
                                      "raw key + value encoding from a Serum-saved preset toggled OFF/PRE/POST (POST was never observed in the UI either)"),
    "fx.equalizer.left_type": ("UNRESOLVED", "FXEQ.kParamType1 exists in real preset corpora (upstream mapping.py notes; local body_state fixtures) and survives write+introspection, but which band it is and what value means Shelf/Peak/HP is unproven",
                               "Serum-saved preset diffs clicking Left icon Shelf->Peak->HighPass proving Type1==Left and the raw value per icon"),
    "fx.equalizer.right_type": ("UNRESOLVED", "FXEQ.kParamType2 candidate, same situation; Right's 3rd option is Low Pass (differs from Left)",
                                "Serum-saved preset diffs clicking Right icon Shelf->Peak->LowPass proving Type2==Right and the raw value per icon"),
    "fx.reverb.chorus_mod": ("UNRESOLVED", "Rate/Depth knob PAIR (Vintage/Nitrous/Basin only), i.e. two params, type-conditional; FXReverb FX_PARAMS (Type/Size/Delay/Width/Wet) lists neither",
                             "raw kParam names for the two knobs per reverb type, plus proof the pair is one shared key vs per-type keys"),
    "fx.reverb.spin_hall": ("UNRESOLVED", "Rate/Depth pair, Hall only; Atlas deliberately keeps it distinct from chorus_mod",
                            "raw kParam names for Hall's Rate/Depth and whether they equal chorus_mod's keys"),
    "fx.filter.type": ("DIRECT_BIND", "PRE-EXISTING binding FXFilter.kParamType (exact_normalized, unmodified by this pass); NO qualification evidence, and upstream marks kParamType confidence='uncertain' (only a subset of the VoiceFilter enum is FXFilter-safe; Atlas default 'MG Low 6' vs schema default 'L12')",
                        None),
}


CANDIDATE_KPARAMS = {"fx.equalizer.left_type": "kParamType1", "fx.equalizer.right_type": "kParamType2"}


def _offline_roundtrip():
    """Baseline -> mutate ONE param -> observe raw diff -> restore -> verify restoration, all via apply_spec/extract_spec
    on the vendored init preset. Proves WRITE + INTROSPECTION SURVIVAL only; says nothing about Atlas identity."""
    from serum_mcp.generation.spec import FxUnitSpec
    from serum_mcp.preset.introspect import extract_spec
    from serum_mcp.preset.mapping import apply_spec
    from serum_mcp.preset.packer import SerumPreset, pack_bytes, unpack_bytes, unpack_file

    base = unpack_file(ROOT / "vendor" / "serum-mcp" / "fixtures" / "init_preset.SerumPreset")
    spec0 = extract_spec(base.data)
    cases = [("FXEQ", "kParamType1", 1.0), ("FXEQ", "kParamType2", 1.0), ("FXFilter", "kParamType", "H12")]
    out = []
    for fx_type, key, value in cases:
        anchor = {"kParamFreq1": 100.0} if fx_type == "FXEQ" else {"kParamFreq": 0.5}
        mk = lambda p: spec0.model_copy(update={"fx_chain": [FxUnitSpec(type=fx_type, params=p)]})
        a = apply_spec(base.data, mk(dict(anchor)))
        b = apply_spec(base.data, mk({**anchor, key: value}))
        pa, pb = (x["FXRack0"]["FX"][0][fx_type]["plainParams"] for x in (a, b))
        changed = sorted(k for k in set(pa) | set(pb) if pa.get(k) != pb.get(k))
        blob = unpack_bytes(pack_bytes(SerumPreset(metadata=base.metadata, data=b))).data  # file-level round trip
        seen = extract_spec(blob).fx_chain[0].params.get(key)
        restored = apply_spec(base.data, mk(dict(anchor)))
        out.append({"fx_type": fx_type, "kparam": key, "value_written": value, "raw_keys_changed": changed,
                    "survives_pack_unpack_introspect": seen == value, "restoration_matches_baseline": restored == a,
                    "proves": "mapping can write + introspection preserves the key (transport only)",
                    "does_not_prove": "which Atlas control the key is, or what the value means in Serum"})
    return out


def main():
    reg = json.loads(REGISTRY.read_text())["canonical_registry"]
    bound = json.loads(BINDINGS.read_text())["controls"]
    scope = sorted(k for k, v in reg.items() if v["section"] == "FX" and v["disposition"] == "UNKNOWN")
    from serum2.producer.state_ledger import catalog
    from serum2.reference.generate_binding_table import FX_UNIT_TYPES
    schema_keys = catalog()["fx_params"]
    rt = {(c["fx_type"], c["kparam"]): c for c in _offline_roundtrip()}
    rows = {}
    for cid in scope:
        ctype = reg[cid]["control_type"]
        if cid in REVIEWED:
            disp, why, missing = REVIEWED[cid]
        else:
            disp, why = BY_CONTROL_TYPE[ctype]
            missing = None
        pre = cid in bound
        assert (disp == "DIRECT_BIND") == pre, cid  # DIRECT_BIND iff already bound: this pass adds none
        unit = cid.split(".")[1]
        fx_type = (reg[cid]["ui_name"] if ctype == "module_identity" else FX_UNIT_TYPES.get(unit))
        cand = bound[cid]["param"] if pre else CANDIDATE_KPARAMS.get(cid)
        chk = rt.get((fx_type, cand))
        rows[cid] = {"atlas_id": cid, "family": "FX", "ui_identity": reg[cid]["ui_name"], "fx_type": fx_type,
                     "candidate_kparam": cand,
                     "schema_present": bool(cand and cand in schema_keys.get(fx_type, {})),
                     "mapping_supported": None if chk is None else chk["raw_keys_changed"] == [cand],
                     "introspect_supported": None if chk is None else chk["survives_pack_unpack_introspect"],
                     "evidence_status": ("EXISTING_BINDING_UNQUALIFIED" if pre else
                                         "KEY_EXISTS_IDENTITY_UNPROVEN" if cand else "NO_CANDIDATE_KEY"),
                     "binding_kind": "FX_PARAMETER_BINDING (fx_type, kparam) -> fx_chain[i].params[kparam]" if pre else
                                     {"STRUCTURAL": "fx_chain topology (not built)", "UNRESOLVED": None}.get(disp),
                     "final_disposition": disp, "disposition": disp, "control_type": ctype, "reason": why,
                     "rationale": why, "missing_evidence": missing, "pre_existing_binding": bound.get(cid),
                     "newly_bound": False}
    # separate evidence axis (never folded into `disposition`): how far the bulk causal + GUI harness got per candidate
    sem = ROOT / "parameter_characterization" / "bulk_causal_evidence" / "semantic_fx_v1.json"
    if sem.exists():
        for v in json.loads(sem.read_text())["tests"].values():
            if v["atlas_id"] in rows:
                rows[v["atlas_id"]].update({"evidence_tier": v["tier"], "semantic_status": v["status"], "semantic_raw_to_label": v["raw_to_label"],
                                            "candidate_kparam": rows[v["atlas_id"]]["candidate_kparam"] or v["candidate"]["kparam"]})
    counts = {d: sum(r["disposition"] == d for r in rows.values())
              for d in ("DIRECT_BIND", "STRUCTURAL", "UI_ONLY", "BROWSER_EXTERNAL", "UNRESOLVED")}
    ids = lambda d: [c for c, r in rows.items() if r["disposition"] == d]
    res = {"scope": "FX controls with registry disposition UNKNOWN", "total": len(rows), "counts": counts,
           "generic_binding_mechanism": "FX_PARAMETER_BINDING == existing binding-table kind 'fx' {fx_type, param}; no new code, no per-control path",
           "new_bindings": [], "newly_direct_bound": 0, "pre_existing_direct_bind": ids("DIRECT_BIND"),
           "still_unknown": ids("UNRESOLVED"), "ui_only": ids("UI_ONLY"), "browser_external": ids("BROWSER_EXTERNAL"),
           "structural": ids("STRUCTURAL"), "unresolved": {c: rows[c]["missing_evidence"] for c in ids("UNRESOLVED")},
           "offline_write_introspection_checks": list(rt.values()), "controls": rows,
           "scope_note": "Coverage's 110 FX 'UNKNOWN' (mcp surface status) is a different axis than these 29 (registry "
                         "disposition); 28 overlap, fx.filter.type is already an MCP-mutable candidate."}
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(len(rows), counts)


if __name__ == "__main__":
    main()
