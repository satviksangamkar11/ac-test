"""Finish Line B: Serum's own host-parameter display text for the MISSING_DOMAIN controls that ARE host parameters
(Swing Div, Amp, Cutoff Rand, Osc Detune Rnd, Env Rand), with the FLB_DOMAIN_{DEFAULT,EXACT_LO,EXACT_MID,MIN,MAX}
bodies loaded into real Serum (DawDreamer). Raw text only; nothing is converted or inferred.

    python probe_finish_line_b_hosttext.py -> giant_verify_out/bulk_ui_verification/finish_line_b_hosttext.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from preset_build import unpack_file  # noqa: E402
from run_mcp_execution_harness import BUV, LiveBackend  # noqa: E402

PRESETS = os.path.expanduser(r"~\Documents\Xfer\Serum 2 Presets\Presets\User\FINISH_LINE_B")
HOSTS = ["Swing Div", "Amp", "Cutoff Rand", "Osc Detune Rnd", "Env Rand"]


def main():
    b = LiveBackend()
    out = {"serum_sha256": b.serum_sha256, "host_parameters": HOSTS, "presets": {}}
    for tag in ("DEFAULT", "EXACT_LO", "EXACT_MID", "MIN", "MAX"):
        name = "FLB_DOMAIN_%s" % tag
        b.load(unpack_file(os.path.join(PRESETS, name + ".SerumPreset")).data)
        hosts = b.hosts()
        out["presets"][name] = {h: hosts.get(h) for h in HOSTS}
        print(name, out["presets"][name])
    json.dump(out, open(os.path.join(BUV, "finish_line_b_hosttext.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
