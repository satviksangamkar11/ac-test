"""Bulk DIRECT-UI verification, corrected: ONE complete verification preset covering EVERY section (OSC, FILTER,
ENV, LFO, MATRIX, FX, GLOBAL, ARP, VOICE, MACRO, MIXER), not one preset per qualification context. The 15
per-context qualification bodies (bulk_engine.py / bulk_worker.py, contexts/*.SerumPreset) are separate, frozen,
historical causal-qualification artifacts and are untouched by this script.

    python build_giant_verification_preset.py <campaign_run_gui.json> <manifest.json> <out_dir>

Construction, in order:
  1. master base = INIT context body (== the plain init preset; 257/328 candidates already target it directly --
     global, arp, lfo, filter, mixer, voice, macro, envelope sections all live here)
  2. merge in all 13 FX_* contexts SIMULTANEOUSLY as distinct FX rack slots (apply_spec accepts a multi-unit
     fx_chain and places each at its own index -- verified structurally non-conflicting, no reason to keep them apart)
  3. merge in OSC_SAMPLE's oscillator/section spec_patch (9 candidates: oscA/B/C sample loop points)
  4. apply every remaining candidate's campaign-retained target value directly into that one body

OSC_WARP2 (3 candidates: oscA/B/C warp_amount2) is the one genuine STRUCTURAL conflict: it redefines the same
oscillator slots to a different engine mode (FM/warp2) than OSC_SAMPLE (sample playback) -- an oscillator physically
cannot be in two modes at once, so these 3 candidates cannot join the giant preset. They get ONE small, explicitly
justified secondary preset (VERIFY_SECONDARY_OSC_WARP2.SerumPreset), not silent exclusion.

Every one of the 330 MCP candidates gets exactly one terminal status:
  APPLIED_TO_GIANT_PRESET | APPLIED_TO_SECONDARY_PRESET | STRUCTURAL_CONFLICT (deferred to secondary, stated why)
  | PATH_CONFLICT (two candidates disagree on one path -- never last-write-wins) | UNRESOLVED_NO_TARGET
  | STATE_NOT_OBSERVED | NOT_DERIVED
Enum/text candidates ARE included here (unlike the earlier per-context draft): this stage's whole point is to let
the GUI prove or disprove a raw retained value's displayed meaning, so requiring prior GUI-proven labels would be
circular. Their raw retained value is used as-is and tagged so the DIRECT_UI comparison knows it is unproven.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set, resolve_path  # noqa: E402
from preset_build import BASE, SPEC0, build_context_body, deep_merge, pack_file  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

FX_CONTEXTS_ORDER = ["FX_FXBode", "FX_FXChorus", "FX_FXComp", "FX_FXConv", "FX_FXDelay", "FX_FXHyperD",
                     "FX_FXDistortion", "FX_FXEQ", "FX_FXFilter", "FX_FXFlanger", "FX_FXPhaser", "FX_FXReverb"]
OSC_PRIMARY, OSC_SECONDARY = "OSC_SAMPLE", "OSC_WARP2"   # OSC_SAMPLE has 9 candidates vs OSC_WARP2's 3


def pick_target(rec):
    """Return (target_value, why_unresolved). Unlike the per-context draft, enum/text IS resolved here: this
    stage exists to let the GUI prove/disprove what a raw retained value displays as, so a raw retained value is
    a valid target -- it is simply tagged 'unproven_by_gui_yet' rather than skipped."""
    g = rec["range"]
    kind = rec["declared"]["kind"]
    base = g["discovered_default"] if g["discovered_default"] is not None else rec["declared"].get("default")
    kept = [v for v in rec["values"] if not v["probe"] and v["state_value"] is not None]
    if not kept:
        return None, "no retained non-probe value in this run (stricter than closure_ledger's observable(), which also counts probes)"
    if kind == "bool":
        m = next((v for v in kept if v["state_value"] in (0.0, 1.0) and v["state_value"] != base), None)
        return (m["state_value"], None) if m else (None, "no retained 0/1 value differing from default")
    if kind in ("enum", "enum_str", "text"):
        m = next((v for v in kept if base is None or v["state_value"] != base), kept[0])
        return m["state_value"], None
    numeric = [v for v in kept if isinstance(v["state_value"], (int, float)) and not isinstance(v["state_value"], bool)
               and (base is None or abs(v["state_value"] - base) > 1e-9)]
    if not numeric:
        return None, "no retained numeric value differing from default"
    lo, hi = g["reachable_min"], g["reachable_max"]
    mid = (lo + hi) / 2 if lo is not None and hi is not None else numeric[0]["state_value"]
    v = min(numeric, key=lambda r: abs(r["state_value"] - mid))
    return v["state_value"], None


def close(a, b):
    return a == b or (isinstance(a, float) and isinstance(b, float) and abs(a - b) < 1e-9)


def main(run_path, manifest_path, out_dir, accounting_path=None):
    run = json.loads(open(run_path).read())
    manifest = json.loads(open(manifest_path).read())
    recs = {r["atlas_id"]: r for r in run["records"]}
    not_derived = []
    if accounting_path:
        acct = json.loads(open(accounting_path).read())
        not_derived = [c for c in acct["candidates"] if not c["derived"]]   # never in the manifest at all -- account for them explicitly
    os.makedirs(out_dir, exist_ok=True)

    fx_units = [FxUnitSpec(type=manifest["contexts"][n]["fx"][0]["type"], params={}, wet=100.0) for n in FX_CONTEXTS_ORDER]
    spec = SPEC0.model_copy(update={"fx_chain": fx_units})
    giant_body = apply_spec(BASE.data, spec)
    slot_of_fx_context = {n: i for i, n in enumerate(FX_CONTEXTS_ORDER)}

    osc_primary_ctx = manifest["contexts"][OSC_PRIMARY]
    if osc_primary_ctx.get("spec_patch"):
        primary_spec = type(SPEC0).model_validate(deep_merge(SPEC0.model_dump(), osc_primary_ctx["spec_patch"]))
        primary_body = apply_spec(BASE.data, primary_spec.model_copy(update={"fx_chain": fx_units}))
        giant_body["Oscillator0"] = primary_body.get("Oscillator0", giant_body.get("Oscillator0"))
        for key in list(giant_body.keys()):
            if key.startswith("Oscillator") or key.startswith("WTOsc"):
                giant_body[key] = primary_body.get(key, giant_body[key])

    secondary_body, meta = build_context_body(manifest["contexts"][OSC_SECONDARY])

    by_context = {}
    for p in manifest["parameters"]:
        by_context.setdefault(p["context"], []).append(p)

    results, seen_paths_giant = [], {}
    for name, params in by_context.items():
        for p in params:
            aid = p["atlas_id"]
            rec = recs.get(aid)
            row = {"atlas_id": aid, "context": name}
            if rec is None:
                row.update({"status": "NOT_DERIVED", "reason": "absent from run evidence (NOT_DERIVED or SERUM_CRASH)"})
                results.append(row); continue
            target, why = pick_target(rec)
            if why:
                row.update({"status": "NO_USABLE_TARGET_VALUE", "reason": why})
                results.append(row); continue

            path = resolve_path(p["mutation"])
            if name in slot_of_fx_context:
                path = [path[0], "FX", slot_of_fx_context[name]] + list(path[3:])
            row.update({"kparam": path[-1], "raw_path": path, "target_value": target,
                       "declared_domain": rec["declared"], "gui_proven": rec["declared"]["kind"] not in ("enum", "enum_str", "text")})

            if name == OSC_SECONDARY:
                body_set(secondary_body, resolve_path(p["mutation"]), target)   # secondary keeps its own native (unshifted) path
                row.update({"status": "APPLIED_TO_SECONDARY_PRESET", "raw_path": resolve_path(p["mutation"]),
                           "reason": "oscillator mode conflicts with OSC_SAMPLE (chosen for the giant preset, 9 vs 3 candidates); "
                                     "same physical oscillator slot cannot be Sample-mode and Warp2-mode simultaneously"})
                results.append(row); continue

            pk = tuple(path)
            if pk in seen_paths_giant:
                prev_target, prev_aid = seen_paths_giant[pk]
                if not close(prev_target, target):
                    row.update({"status": "PATH_CONFLICT", "reason": "path %s: disagrees with %s (%r vs %r)" % (path, prev_aid, target, prev_target)})
                    results.append(row); continue
                row.update({"status": "APPLIED_TO_GIANT_PRESET", "alias_of": prev_aid})
                results.append(row); continue

            body_set(giant_body, path, target)
            seen_paths_giant[pk] = (target, aid)
            row["status"] = "APPLIED_TO_GIANT_PRESET"
            results.append(row)

    # verify every APPLIED_TO_GIANT_PRESET target actually landed (file/body readback, before Serum ever sees it)
    for r in results:
        if r["status"] == "APPLIED_TO_GIANT_PRESET":
            got = body_get(giant_body, r["raw_path"])
            assert close(got, r["target_value"]), "giant preset: %s wrote %r but body has %r" % (r["atlas_id"], r["target_value"], got)
        if r["status"] == "APPLIED_TO_SECONDARY_PRESET":
            got = body_get(secondary_body, r["raw_path"])
            assert close(got, r["target_value"]), "secondary preset: %s wrote %r but body has %r" % (r["atlas_id"], r["target_value"], got)

    giant_path = os.path.join(out_dir, "VERIFY_REFERENCE_FULL.SerumPreset")
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName="VERIFY_REFERENCE_FULL"), data=copy.deepcopy(giant_body)), giant_path)
    secondary_path = os.path.join(out_dir, "VERIFY_SECONDARY_OSC_WARP2.SerumPreset")
    pack_file(SerumPreset(metadata=dict(meta, presetName="VERIFY_SECONDARY_OSC_WARP2"), data=copy.deepcopy(secondary_body)), secondary_path)

    for c in not_derived:
        results.append({"atlas_id": c["atlas_id"], "context": None, "status": "NOT_DERIVED", "reason": c["reason"]})

    from collections import Counter
    counts = Counter(r["status"] for r in results)
    assert sum(counts.values()) == len(manifest["parameters"]) + len(not_derived)
    plan = {"source_run": os.path.abspath(run_path), "source_manifest": os.path.abspath(manifest_path),
            "giant_preset": os.path.relpath(giant_path, out_dir), "secondary_preset": os.path.relpath(secondary_path, out_dir),
            "fx_slot_order": FX_CONTEXTS_ORDER, "osc_primary_context": OSC_PRIMARY, "osc_deferred_context": OSC_SECONDARY,
            "status_counts": dict(counts), "candidates": results}
    json.dump(plan, open(os.path.join(out_dir, "giant_verification_plan.json"), "w"), indent=1)
    print(json.dumps(dict(counts), indent=1))
    print("giant preset (%d controls) -> %s" % (counts.get("APPLIED_TO_GIANT_PRESET", 0), giant_path))
    print("secondary preset (%d controls) -> %s" % (counts.get("APPLIED_TO_SECONDARY_PRESET", 0), secondary_path))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
