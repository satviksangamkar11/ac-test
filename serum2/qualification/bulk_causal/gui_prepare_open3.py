"""Finish Line B round 3: presets for the last 3 open controls (global.voice_amp, global.swing_div, global.portamento_curve).
Bulk, distinct values: every preset writes a DIFFERENT value on every one of the controls (and on swing / porta time, so the
Swing readout and the CURVE control are active), all inside the verified domain. Each preset is loaded into real Serum and its
re-saved state + host display texts are recorded, so a GUI reading is always tied to what Serum actually holds.

    python gui_prepare_open3.py -> giant_verify_out/bulk_ui_verification/finish_line_b_open3_plan.json
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set  # noqa: E402
from campaign_derive import base_spec  # noqa: E402
from preset_build import BASE, pack_file  # noqa: E402
from run_mcp_execution_harness import BUV, LiveBackend  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.expanduser(r"~\Documents\Xfer\Serum 2 Presets\Presets\User\FINISH_LINE_B")
G = "Global0"
COLS = ["kParamVoiceAmp", "kParamSwingDiv", "kParamPortamentoCurve", "kParamSwing", "kParamPortamentoTime"]
ROWS = {  # amp, swing_div, curve, swing %, porta time -- a different value in every column of every preset
    "FLB_OPEN3_A": [0.0, 0, -100.0, 25.0, 1.5],
    "FLB_OPEN3_B": [0.25, 1, -50.0, 40.0, 3.0],
    "FLB_OPEN3_C": [0.75, 5, 50.0, 60.0, 4.5],
    "FLB_OPEN3_D": [1.0, 6, 100.0, 90.0, 6.0],
}
HOSTS = ["Amp", "Swing", "Swing Div"]


def main():
    backend = LiveBackend()
    base = apply_spec(BASE.data, base_spec())
    plan = {"serum_sha256": backend.serum_sha256, "columns": COLS, "presets": []}
    for name, vals in ROWS.items():
        body = copy.deepcopy(base)
        for k, v in zip(COLS, vals):
            body_set(body, [G, "plainParams", k], v)
        backend.load(body)
        st, hosts = backend.state(), backend.hosts()
        pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), os.path.join(OUT, name + ".SerumPreset"))
        plan["presets"].append({"preset": name, "written": dict(zip(COLS, vals)),
                                "serum_readback": {k: body_get(st, [G, "plainParams", k]) for k in COLS},
                                "host_text": {h: hosts.get(h) for h in HOSTS}})
        print(name, plan["presets"][-1]["serum_readback"], plan["presets"][-1]["host_text"])
    json.dump(plan, open(os.path.join(BUV, "finish_line_b_open3_plan.json"), "w"), indent=1, default=repr)


if __name__ == "__main__":
    main()
