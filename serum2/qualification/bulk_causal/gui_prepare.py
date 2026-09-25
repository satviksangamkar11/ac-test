"""GUI half of the bulk harness, step 1: turn the SAME manifest into an ordered folder of presets to step through in Serum.

    python gui_prepare.py <manifest.json> <out_dir> <test_id>[,<test_id>...] [--edges]

Uses the same preset_build.expand/write_preset as the causal worker, so contexts, auto Range Test Plans and raw (out-of-schema)
probe writes are identical. For each selected test it writes `<out_dir>/GUInn_<test>__<value>[_probe].SerumPreset` (reference
first) plus `gui_plan.json`. `--edges` keeps only what the UI has to show for a range test: min, max, the first probe above and
the first below, and the 2x-beyond probe (to see a clamp on screen). Put out_dir under Serum's User preset folder; the
alphabetical order IS the plan. The plan records the raw params each preset carries; UI observations are recorded against it
(see merge.py / merge_range.py), never inferred. Pure serum-mcp: no Serum/DawDreamer needed.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy  # noqa: E402
from bulk_engine import body_set, resolve_path  # noqa: E402
from preset_build import BASE, build_context_body, expand, pack_file, write_preset  # noqa: E402
from range_plan import plan as range_plan  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402


def vkey(v):
    return "null" if v is None else ("%g" % v).replace(".", "p").replace("-", "m").replace("+", "")


def edge_values(t):
    vals, probes = t["values"], t.get("probe_values", [])
    hi = [p for p in probes if vals and p > max(x for x in vals if x is not None)]
    lo = [p for p in probes if vals and p < min(x for x in vals if x is not None)]
    keep = [min(v for v in vals if v is not None), max(v for v in vals if v is not None)]
    return keep, [x for x in (hi[:1] + hi[1:3][-1:] + lo[:1]) if x is not None]


def main_bulk(cfg, manifest, out_dir, ids, edges):
    """Bulk (context + parameters) manifests: UI-verification presets are made ONLY here, only for the selected parameters (matched by
    atlas_id or kparam) and only for the edge values a screen has to show; the causal engine itself never writes them."""
    os.makedirs(out_dir, exist_ok=True)
    plan, n = [], 0
    for p in [p for p in cfg["parameters"] if p["atlas_id"] in ids or resolve_path(p["mutation"])[-1] in ids]:
        body0, meta = build_context_body(cfg["contexts"][p["context"]])
        path = resolve_path(p["mutation"])
        vec = range_plan(p["domain"])
        t = {"values": vec["values"], "probe_values": vec["probes"]}
        vals, probes = edge_values(t) if edges else (vec["values"], vec["probes"])
        for kind, v in [("reference", "ref")] + [("value", x) for x in vals] + [("probe", x) for x in probes]:
            n += 1
            name = "GUI%02d_%s__%s%s" % (n, path[-1], "ref" if v == "ref" else vkey(v), "_probe" if kind == "probe" else "")
            body = copy.deepcopy(body0)
            if v != "ref":
                body_set(body, path, v)
            pack_file(SerumPreset(metadata=dict(meta, presetName=name), data=body), os.path.join(out_dir, name + ".SerumPreset"))
            plan.append({"n": n, "preset": name, "test": p["atlas_id"], "atlas_id": p["atlas_id"], "module": p["context"], "kparam": path[-1],
                         "written": None if v == "ref" else v, "kind": kind, "raw_path": path})
    json.dump({"manifest": os.path.abspath(manifest), "presets": plan}, open(os.path.join(out_dir, "gui_plan.json"), "w"), indent=1)
    print(n, "presets ->", out_dir)


def main(manifest, out_dir, ids, edges=False):
    cfg = json.load(open(manifest))
    if cfg.get("kind") == "bulk_context":
        return main_bulk(cfg, manifest, out_dir, ids, edges)
    os.makedirs(out_dir, exist_ok=True)
    plan, n = [], 0
    for raw in [t for t in cfg["tests"] if t["id"] in ids]:
        t = expand(raw, cfg)
        vals, probes = (t["values"], t.get("probe_values", [])) if not edges else edge_values(t)
        for kind, v in [("reference", "ref")] + [("value", x) for x in vals] + [("probe", x) for x in probes]:
            n += 1
            name = "GUI%02d_%s__%s%s" % (n, t["id"], "ref" if v == "ref" else vkey(v), "_probe" if kind == "probe" else "")
            path, _ = write_preset(name, t, None if v == "ref" else v, out_dir, reference=(v == "ref"))
            unit = t["unit"]
            params = dict(unit.get("reference_params", unit.get("params", {})) if v == "ref" else unit.get("params", {}))
            if v not in ("ref", None):
                params[t["candidate"]["kparam"]] = v
            plan.append({"n": n, "preset": name, "test": t["id"], "atlas_id": t.get("atlas_id"), "module": unit["type"],
                         "kparam": t["candidate"]["kparam"], "written": None if v == "ref" else v, "kind": kind, "raw_params": params})
    json.dump({"manifest": os.path.abspath(manifest), "presets": plan}, open(os.path.join(out_dir, "gui_plan.json"), "w"), indent=1)
    print(n, "presets ->", out_dir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(","), "--edges" in sys.argv)
