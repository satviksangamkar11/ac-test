"""Finish Line B live probe: real Serum 2 (DawDreamer, same LiveBackend as run_mcp_execution_harness.py).

Task 1 (12 MISSING_DOMAIN): write out-of-range raw values into the control's body leaf, load, read Serum's own re-saved
state back. What Serum keeps is its effective clamp; nothing is inferred.
Task 2 (4 enums): write every candidate body key (serum-mcp schema list + an obviously invalid control key), load, read
back. A key Serum persists unchanged is a real stored value; anything else is recorded as it came back.

    python probe_finish_line_b.py            -> giant_verify_out/bulk_ui_verification/finish_line_b_probe.jsonl
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set  # noqa: E402
from campaign_derive import base_spec  # noqa: E402
from preset_build import BASE, SPEC0  # noqa: E402
from run_mcp_execution_harness import BUV, ED, LiveBackend  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.schema import FX_PARAMS, VOICE_FILTER_PARAMS  # noqa: E402

DOMAIN_IDS = ["arp.playback.offset", "arp.playback.repeats", "arp.velocity.decay", "global.oversampling",
              "global.portamento_curve", "global.swing_div", "global.voice_amp", "global.voice_control.random.cutoff",
              "global.voice_control.random.detune", "global.voice_control.random.envs",
              "global.voice_control.scaling.envs", "global.voice_control.scaling.lfos"]
DOMAIN_PROBES = [-1e6, -1000.0, -100.0, -1.0, 0.0, 0.5, 1.0, 2.0, 10.0, 100.0, 1000.0, 1e6]
ENUM_IDS = {"fx.distortion.type": list(FX_PARAMS["FXDistortion"]["kParamMode"].enum_values) + ["kTube", "kBOGUS"],
            "fx.reverb.type": list(FX_PARAMS["FXReverb"]["kParamType"].enum_values) + ["kPlate", "kNitrous", "kBasin", "kBOGUS"],
            "fx.filter.type": list(VOICE_FILTER_PARAMS["kParamType"].enum_values) + ["BOGUS"],
            "fx.delay.mode": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, -1.0, 100.0]}


def base_body(row):
    e = row["mcp_edit"]
    if e["kind"] == "fx":
        return apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=e["fx_type"], params={}, wet=100.0)]}))
    return apply_spec(BASE.data, base_spec())


def probe(backend, row, values):
    path = row["expected_raw"][0]["path"]
    base = base_body(row)
    backend.load(base)
    pre = body_get(backend.state(), path)
    out = []
    for v in values:
        body = copy.deepcopy(base)
        body_set(body, path, v)
        rec = {"atlas_id": row["atlas_id"], "path": path, "written": v, "baseline_readback": pre}
        try:
            backend.load(body)
            rec["readback"] = body_get(backend.state(), path)
            rec["persisted_unchanged"] = rec["readback"] == v
        except Exception as ex:
            rec["error"] = repr(ex)
        out.append(rec)
    return out


def main():
    rows = {r["atlas_id"]: r for r in json.load(open(os.path.join(ED, "mcp_execution_contract_v1.json")))["rows"]}
    backend = LiveBackend()
    out_path = os.path.join(BUV, "finish_line_b_probe.jsonl")
    with open(out_path, "w") as f:
        f.write(json.dumps({"serum_sha256": backend.serum_sha256, "probe": "finish_line_b"}) + "\n")
        for aid in DOMAIN_IDS:
            for rec in probe(backend, rows[aid], DOMAIN_PROBES):
                f.write(json.dumps(dict(rec, task="domain"), default=repr) + "\n")
            f.flush()
            print("domain", aid)
        for aid, vals in ENUM_IDS.items():
            for rec in probe(backend, rows[aid], vals):
                f.write(json.dumps(dict(rec, task="enum"), default=repr) + "\n")
            f.flush()
            print("enum", aid, len(vals))
    print("->", out_path)


if __name__ == "__main__":
    main()
