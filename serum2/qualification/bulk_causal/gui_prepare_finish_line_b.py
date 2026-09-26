"""Finish Line B GUI presets. Enum presets put one FX unit per body key in rack order (unit 0 = key left UNSET, i.e.
Serum's own default), so the FX page shows every key's display name at a known rack position. Domain presets write
all 12 MISSING_DOMAIN leaves at -1e6 (FLB_DOMAIN_MIN) / +1e6 (FLB_DOMAIN_MAX) / untouched (FLB_DOMAIN_DEFAULT), so the
GUI shows Serum's own clamp. Every preset is loaded into real Serum and its re-saved state recorded in the plan, so a GUI
reading is always tied to what Serum actually holds, never to what was written.

    python gui_prepare_finish_line_b.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set  # noqa: E402
from campaign_derive import base_spec  # noqa: E402
from preset_build import BASE, SPEC0, pack_file  # noqa: E402
from probe_finish_line_b import DOMAIN_IDS  # noqa: E402
from run_mcp_execution_harness import BUV, ED, LiveBackend  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.expanduser(r"~\Documents\Xfer\Serum 2 Presets\Presets\User\FINISH_LINE_B")
CHUNK = 12
PROBE = os.path.join(BUV, "finish_line_b_probe.jsonl")


def persisted_keys():
    keys = {}
    for l in open(PROBE):
        r = json.loads(l)
        if r.get("task") == "enum" and r.get("persisted_unchanged"):
            keys.setdefault(r["atlas_id"], []).append(r["written"])
    return keys


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = {r["atlas_id"]: r for r in json.load(open(os.path.join(ED, "mcp_execution_contract_v1.json")))["rows"]}
    backend = LiveBackend()
    plan = {"serum_sha256": backend.serum_sha256, "presets": []}

    for aid, keys in persisted_keys().items():
        e = rows[aid]["mcp_edit"]
        seq = [None] + keys
        for c in range(0, len(seq), CHUNK):
            part = seq[c:c + CHUNK]
            units = [FxUnitSpec(type=e["fx_type"], params={} if k is None else {e["param"]: k}, wet=100.0) for k in part]
            body = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": units}))
            name = "FLB_%s_%02d" % (aid.replace(".", "_"), c // CHUNK + 1)
            backend.load(body)
            st = backend.state()
            rb = [body_get(st, ["FXRack0", "FX", i, e["fx_type"], "plainParams", e["param"]]) for i in range(len(part))]
            pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), os.path.join(OUT, name + ".SerumPreset"))
            plan["presets"].append({"preset": name, "atlas_id": aid, "rack_slots": [
                {"slot": i + 1, "written": k, "serum_readback": r} for i, (k, r) in enumerate(zip(part, rb))]})
            print(name, len(part))

    base = apply_spec(BASE.data, base_spec())
    for tag, v in (("DEFAULT", None), ("MIN", -1e6), ("MAX", 1e6)):
        body = copy.deepcopy(base)
        if v is not None:
            for aid in DOMAIN_IDS:
                body_set(body, rows[aid]["expected_raw"][0]["path"], v)
        backend.load(body)
        st = backend.state()
        name = "FLB_DOMAIN_%s" % tag
        pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), os.path.join(OUT, name + ".SerumPreset"))
        plan["presets"].append({"preset": name, "written": v, "controls": [
            {"atlas_id": aid, "path": rows[aid]["expected_raw"][0]["path"],
             "serum_readback": body_get(st, rows[aid]["expected_raw"][0]["path"])} for aid in DOMAIN_IDS]})
        print(name)

    # round 2: exact in-range values, distinct per control, so every GUI field is read against a known raw value and
    # the MIN-preset scaling display (1000% shown for a state of 10.0) can be separated from the -1e6 write itself
    for tag, vals in (("EXACT_LO", [-8.0, 0.0, 0.0, 0.0, -100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, 10.0]),
                      ("EXACT_MID", [-3.0, 5.0, 30.0, 2.0, 50.0, 3.0, 0.25, 40.0, 60.0, 80.0, 50.0, 500.0])):
        body = copy.deepcopy(base)
        for aid, v in zip(DOMAIN_IDS, vals):
            body_set(body, rows[aid]["expected_raw"][0]["path"], v)
        backend.load(body)
        st = backend.state()
        name = "FLB_DOMAIN_%s" % tag
        pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), os.path.join(OUT, name + ".SerumPreset"))
        plan["presets"].append({"preset": name, "controls": [
            {"atlas_id": aid, "path": rows[aid]["expected_raw"][0]["path"], "written": v,
             "serum_readback": body_get(st, rows[aid]["expected_raw"][0]["path"])} for aid, v in zip(DOMAIN_IDS, vals)]})
        print(name)

    p = os.path.join(BUV, "finish_line_b_gui_plan.json")
    json.dump(plan, open(p, "w"), indent=1, default=repr)
    print("->", OUT, p)


if __name__ == "__main__":
    main()
