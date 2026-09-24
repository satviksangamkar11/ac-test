"""GUI half of the bulk harness, step 1: turn the SAME manifest into an ordered folder of presets to step through in Serum.

    python gui_prepare.py <manifest.json> <out_dir> <test_id>[,<test_id>...]

For each selected test and each value (incl. probe values) it writes `<out_dir>/GUInn_<test>__<value>.SerumPreset` (baseline
first) plus `gui_plan.json`. Put out_dir under Serum's User preset folder, open the first preset, and step with the browser's
next arrow: the alphabetical order IS the plan. Pure serum-mcp; no Serum/DawDreamer, so it is importable anywhere.
The plan records the raw state each preset carries; the UI observations are recorded against it in gui_evidence (see
gui_merge.py), never inferred.
"""
import copy
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "vendor", "serum-mcp", "src"))
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.introspect import extract_spec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset, pack_file, unpack_file  # noqa: E402


def vkey(v):
    return "null" if v is None else str(v).replace(".", "p")


def main(manifest, out_dir, ids):
    cfg = json.load(open(manifest))
    base = unpack_file(os.path.join(REPO, "vendor", "serum-mcp", "fixtures", "init_preset.SerumPreset"))
    spec0 = extract_spec(base.data)
    os.makedirs(out_dir, exist_ok=True)
    plan, n = [], 0
    for t in [t for t in cfg["tests"] if t["id"] in ids]:
        kp, unit = t["candidate"]["kparam"], t["unit"]
        for label, v in [("REF", "ref")] + [("V", v) for v in t["values"]] + [("P", v) for v in t.get("probe_values", [])]:
            params = copy.deepcopy(unit.get("reference_params", unit.get("params", {})) if v == "ref" else unit["params"])
            if v not in ("ref", None):
                params[kp] = v
            n += 1
            name = "GUI%02d_%s__%s%s" % (n, t["id"], "ref" if v == "ref" else vkey(v), "_probe" if label == "P" else "")
            fx = FxUnitSpec(type=unit["type"], params=params, wet=unit.get("wet", 100.0))
            data = apply_spec(base.data, spec0.model_copy(update={"fx_chain": [fx]}))
            meta = dict(base.metadata, presetName=name)
            pack_file(SerumPreset(metadata=meta, data=data), os.path.join(out_dir, name + ".SerumPreset"))
            plan.append({"n": n, "preset": name, "test": t["id"], "atlas_id": t.get("atlas_id"), "module": unit["type"], "kparam": kp,
                         "written": None if v == "ref" else v, "kind": "reference" if v == "ref" else ("probe" if label == "P" else "value"),
                         "raw_params": params})
    json.dump({"manifest": os.path.abspath(manifest), "presets": plan}, open(os.path.join(out_dir, "gui_plan.json"), "w"), indent=1)
    print(n, "presets ->", out_dir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(","))
