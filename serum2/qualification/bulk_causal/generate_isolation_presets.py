"""Bulk isolation presets for every UNPROVEN parameter: generation only (no Serum, no rendering, no verification).

    python generate_isolation_presets.py [out_dir]      (default: giant_verify_out/isolation_presets)

Unproven   = every closure_ledger_v3 candidate whose direct_ui_evidence is not UI_CONFIRMED.
Isolation  = one preset per (parameter, value). The body is that parameter's own campaign context baseline
             (manifest_campaign_v1.json context -> preset_build.build_context_body) with ONLY that parameter's raw
             leaf (or leaf_set leaves) written. Every other parameter stays at its baseline.
Values     = range_plan(domain) in-range values (never out-of-range probes), kept only if the GUI campaign run shows
             Serum RETAINED that exact value without a load error (executable). OPEN domains have no declared range, so
             the distinct values Serum stored (after its own clamping) are used. TEXT (macro names) uses the declared
             words without a retention filter: the campaign never read names back (flagged retention_unconfirmed). Values equal to the baseline are dropped, so every preset
             differs visibly from baseline and from its siblings.
Naming     = <section>/<atlas_id>__<nn>__<value>.SerumPreset, presetName the same, so each file is identifiable in
             Serum's browser. index.json lists every preset with its raw path/value and every skipped parameter + reason.
"""
import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import _leaves_for, body_get, body_set, resolve_path  # noqa: E402
from closure_ledger import ED  # noqa: E402
from preset_build import build_context_body, pack_file  # noqa: E402
from range_plan import close, plan as range_plan  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

MANIFEST = os.path.join(HERE, "manifest_campaign_v1.json")


def local_ctx(ctx):
    """Manifest contexts may hold an absolute sample path from the Windows machine: fall back to the repo-local copy."""
    ctx = copy.deepcopy(ctx)
    for o in (ctx.get("spec_patch") or {}).get("oscillators", []):
        src = o.get("sample_playback_source")
        if src and not os.path.exists(src):
            from campaign_derive import sample_wav
            o["sample_playback_source"] = sample_wav()
    return ctx


def retained(rec):
    """Values the campaign wrote that Serum stored back unchanged, with no load error."""
    out = []
    for v in (rec or {}).get("values", []):
        if v.get("load_error") or v.get("state_value") is None:
            continue
        w = v["written"]
        if isinstance(w, str) or isinstance(v["state_value"], str):
            ok = w == v["state_value"]
        else:
            ok = close(v["state_value"], w)
        if ok:
            out.append(w)
    return out


def pick_values(param, rec, base_value):
    dom = param["domain"]
    kept = retained(rec)
    if dom["kind"] == "open":      # no declared range: the values Serum actually STORED (after its own clamping) are executable
        cand = sorted({v["state_value"] for v in (rec or {}).get("values", [])
                       if v.get("state_value") is not None and not v.get("load_error") and not isinstance(v["state_value"], (str, dict, list))})
    else:
        cand = range_plan(dom)["values"]
    if dom["kind"] not in ("open", "text") and rec is not None:     # executable = retained by Serum in the campaign
        # text (macro names) is free-form; the campaign readback never captured it, so retention is unconfirmed, not failed
        cand = [v for v in cand if any(v == k if isinstance(v, str) else (not isinstance(k, str) and close(k, v)) for k in kept)]
    out = []
    for v in cand:
        same_as_base = (v == base_value) if isinstance(v, str) or isinstance(base_value, str) else (base_value is not None and close(base_value, v))
        if not same_as_base and v not in out:
            out.append(v)
    return out


def slug(x):
    s = ("%g" % x) if isinstance(x, float) else str(x)
    return re.sub(r"[^A-Za-z0-9.+-]+", "_", s)[:40]


def main(out_dir):
    ledger = json.load(open(os.path.join(ED, "closure_ledger_v3.json")))
    manifest = json.load(open(MANIFEST))
    params = {p["atlas_id"]: p for p in manifest["parameters"]}
    run = json.load(open(os.path.join(ED, "campaign_run_gui_v1.json")))
    recs = {r["atlas_id"]: r for r in run["records"]}

    unproven = [e["atlas_id"] for e in ledger["candidates"] if e["direct_ui_evidence"]["status"] != "UI_CONFIRMED"]
    bases, presets, skipped = {}, [], []
    for aid in sorted(unproven):
        p = params.get(aid)
        if p is None:
            skipped.append({"atlas_id": aid, "reason": "no manifest entry (NOT_DERIVED: raw vocabulary unknown)"})
            continue
        if p["context"] not in bases:
            bases[p["context"]] = build_context_body(local_ctx(manifest["contexts"][p["context"]]))
        base, meta = bases[p["context"]]
        path = resolve_path(p["mutation"])
        vals = pick_values(p, recs.get(aid), body_get(base, path))
        if not vals:
            skipped.append({"atlas_id": aid, "reason": "no in-range value that Serum retained and that differs from baseline",
                            "domain": p["domain"]})
            continue
        section = aid.split(".")[0]
        for n, v in enumerate(vals):
            body = copy.deepcopy(base)
            leaves = _leaves_for(p["mutation"], v, path)
            for lp, lv in leaves:
                body_set(body, lp, lv)
            name = "%s__%02d__%s" % (aid, n, slug(v))
            rel = os.path.join(section, name + ".SerumPreset")
            os.makedirs(os.path.join(out_dir, section), exist_ok=True)
            pack_file(SerumPreset(metadata=dict(meta, presetName=name), data=body), os.path.join(out_dir, rel))
            presets.append({"file": rel.replace(os.sep, "/"), "atlas_id": aid, "context": p["context"], "value": v,
                            "leaves": [[lp, lv] for lp, lv in leaves], "baseline_value": body_get(base, path),
                            "retention_unconfirmed": p["domain"]["kind"] == "text"})

    idx = {"generated_only": True, "rendered": False, "verified": False,
           "unproven_rule": "closure_ledger_v3 direct_ui_evidence.status != UI_CONFIRMED",
           "n_unproven": len(unproven), "n_parameters_generated": len({x["atlas_id"] for x in presets}),
           "n_presets": len(presets), "n_skipped": len(skipped), "presets": presets, "skipped": skipped}
    assert idx["n_parameters_generated"] + len(skipped) == len(unproven)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(idx, open(os.path.join(out_dir, "index.json"), "w"), indent=1, default=repr)
    print("unproven %d -> %d parameters, %d presets; skipped %d" % (len(unproven), idx["n_parameters_generated"], len(presets), len(skipped)))
    for s in skipped:
        print("  SKIP %-34s %s" % (s["atlas_id"], s["reason"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "giant_verify_out", "isolation_presets"))
