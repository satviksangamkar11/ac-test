"""Step 4: bisect which giant-preset candidate(s) make lfo1.mode='Envelope' show FREE in Serum.

Known (DIRECT_UI_FINDING_RAW_WRITE_GAP.md): structural merge + lfo1.mode alone -> ENVELOPE; + all other candidates -> FREE.
Every preset built here = that same structural body + lfo1.mode + a SUBSET of the other giant-preset candidates.

    python bisect_lfo1_mode_causality.py start            builds CONTROL_ALL (expect FREE) and the first half
    python bisect_lfo1_mode_causality.py FREE|ENVELOPE    your reading of the preset it last told you to load
    python bisect_lfo1_mode_causality.py status

Offline build (no Serum needed to BUILD); you load each preset in the Serum GUI and read LFO1's FREE/RETRIG/ENVELOPE
buttons (NOT the shape dropdown above them). Single-culprit bisection: each round tests the first half of the suspects;
FREE -> culprit is in it, ENVELOPE -> culprit is in the other half. When one candidate is left, a CONFIRM preset
(structural + lfo1.mode + that one) is built; if it reads ENVELOPE the trigger needs more than one candidate and the
script says so instead of naming a false culprit. State lives in giant_verify_out/bisect/bisect_state.json.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_set  # noqa: E402
from build_giant_verification_preset import FX_CONTEXTS_ORDER, OSC_PRIMARY  # noqa: E402
from preset_build import BASE, SPEC0, deep_merge, pack_file  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.join(HERE, "giant_verify_out", "bisect")
STATE = os.path.join(OUT, "bisect_state.json")
PLAN = os.path.join(HERE, "giant_verify_out", "giant_verification_plan.json")
MANIFEST = os.path.join(HERE, "manifest_campaign_v1.json")
SUBJECT = "lfo1.mode"


def structural_body(manifest):
    """Steps 1-3 of build_giant_verification_preset.main: INIT + 12 FX slots + OSC_SAMPLE oscillators, no candidates."""
    fx_units = [FxUnitSpec(type=manifest["contexts"][n]["fx"][0]["type"], params={}, wet=100.0) for n in FX_CONTEXTS_ORDER]
    body = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": fx_units}))
    patch = manifest["contexts"][OSC_PRIMARY].get("spec_patch")
    if patch:
        patch = copy.deepcopy(patch)
        for o in patch.get("oscillators", []):   # manifest holds an absolute D:\ path; fall back to the repo-local copy
            src = o.get("sample_playback_source")
            if src and not os.path.exists(src):
                from campaign_derive import sample_wav
                o["sample_playback_source"] = sample_wav()
        spec = type(SPEC0).model_validate(deep_merge(SPEC0.model_dump(), patch))
        primary = apply_spec(BASE.data, spec.model_copy(update={"fx_chain": fx_units}))
        for key in list(body.keys()):
            if key.startswith("Oscillator") or key.startswith("WTOsc"):
                body[key] = primary.get(key, body[key])
    return body


def writes():
    """atlas_id -> (raw_path, target) for every giant-preset candidate, in plan order (aliases share a path+target)."""
    plan = json.load(open(PLAN))
    return {c["atlas_id"]: (c["raw_path"], c["target_value"]) for c in plan["candidates"] if c["status"] == "APPLIED_TO_GIANT_PRESET"}


def build(name, ids, w, base):
    body = copy.deepcopy(base)
    for aid in [SUBJECT] + list(ids):
        body_set(body, *w[aid])
    path = os.path.join(OUT, "BISECT_%s.SerumPreset" % name)
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName="BISECT_" + name), data=body), path)
    return path


def save(st):
    json.dump(st, open(STATE, "w"), indent=1)


def next_test(st, w, base):
    s = st["suspects"]
    if len(s) == 1:
        st["pending"] = {"name": "CONFIRM_" + s[0].replace(".", "_"), "ids": s, "kind": "confirm"}
    else:
        st["round"] += 1
        half = s[: len(s) // 2]
        st["pending"] = {"name": "R%02d_%d_of_%d" % (st["round"], len(half), len(s)), "ids": half, "kind": "half"}
    p = build(st["pending"]["name"], st["pending"]["ids"], w, base)
    save(st)
    print("LOAD %s  -> then run: python %s FREE|ENVELOPE" % (p, os.path.basename(__file__)))


def main(cmd):
    os.makedirs(OUT, exist_ok=True)
    w = writes()
    base = structural_body(json.load(open(MANIFEST)))
    if cmd == "start":
        others = [a for a in w if a != SUBJECT]
        st = {"subject": SUBJECT, "suspects": others, "round": 0, "log": [], "done": None}
        p = build("CONTROL_ALL", others, w, base)
        st["pending"] = {"name": "CONTROL_ALL", "ids": others, "kind": "control"}
        save(st)
        print("%d suspects. LOAD %s first (should read FREE, reproducing the finding)" % (len(others), p))
        print("then run: python %s FREE|ENVELOPE" % os.path.basename(__file__))
        return
    st = json.load(open(STATE))
    if cmd == "status":
        print(json.dumps({k: st[k] for k in ("round", "done", "pending")}, indent=1), "suspects:", len(st["suspects"]))
        return
    if st["done"]:
        print("finished:", st["done"])
        return
    reading = cmd.upper()
    if reading not in ("FREE", "ENVELOPE"):
        sys.exit("reading must be FREE or ENVELOPE (RETRIG: record it by hand, it breaks the single-culprit assumption)")
    t = st["pending"]
    st["log"].append({"preset": t["name"], "n_ids": len(t["ids"]), "reading": reading})
    if t["kind"] == "control":
        if reading != "FREE":
            st["done"] = "CONTROL_ALL read ENVELOPE: finding did not reproduce with this build; stop and compare against VERIFY_REFERENCE_FULL"
            save(st); print(st["done"]); return
    elif t["kind"] == "half":
        st["suspects"] = t["ids"] if reading == "FREE" else [a for a in st["suspects"] if a not in t["ids"]]
    else:
        st["done"] = ("CULPRIT: %s alone flips lfo1.mode to FREE" % t["ids"][0] if reading == "FREE" else
                      "NO SINGLE CULPRIT: %s alone reads ENVELOPE; the trigger needs a combination (bisection path in log)" % t["ids"][0])
        save(st); print(st["done"]); return
    next_test(st, w, base)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "status")
