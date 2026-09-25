"""Bisect native Serum crashes for one parameter: ONE written value per fresh Serum process (no cross-contamination).

    python lfo_crash_bisect.py [atlas_id ...]      (default lfo1.rate .. lfo6.rate)  ->  lfo_rate_crash_bisection_v1.json
    python lfo_crash_bisect.py --trial <atlas_id> <value>   (internal: one process, prints STAGE lines)

Per trial: baseline -> write the value -> state readback -> render -> restore. The parent records exit code + last stage reached.
Verdict per value: SAFE (exit 0, restored) / CRASHING (nonzero exit) / UNRESOLVED (exit 0 but restoration or readback failed).
Evidence only: nothing here touches the ledger, binding table, contracts or the compiler.
"""
import copy, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2] / "parameter_characterization" / "bulk_causal_evidence" / "lfo_rate_crash_bisection_v1.json"


def trial(aid, value):
    sys.path.insert(0, str(HERE))
    import serum_backend as sb
    from bulk_engine import body_get, body_set
    from preset_build import write_context_preset
    cfg = json.load(open(HERE / "manifest_campaign_v1.json"))
    p = next(x for x in cfg["parameters"] if x["atlas_id"] == aid)
    _, body, _ = write_context_preset("QUAL_BISECT", cfg["contexts"][p["context"]], str(HERE / "contexts"))
    path = p["mutation"]["path"]
    def stage(s, **kw):
        print("STAGE " + json.dumps({"stage": s, **kw}), flush=True)
    be = sb.SerumBackend(cfg)
    be.load(body); base = be.observe(); stage("baseline")
    m = copy.deepcopy(body); body_set(m, path, value)
    be.load(m); stage("loaded")
    st = be._state(); stage("state", readback=body_get(st, path))
    be._bands(); stage("rendered")
    be.load(body); after = be.observe()
    stage("restored", ok=body_get(after["state"], path[:-1]) == body_get(base["state"], path[:-1]))


def trial_seq(aid, values):
    """Same as trial() but many values in ONE process without restoring between them (finds order/accumulation crashes)."""
    sys.path.insert(0, str(HERE))
    import serum_backend as sb
    from bulk_engine import body_set
    from preset_build import write_context_preset
    cfg = json.load(open(HERE / "manifest_campaign_v1.json"))
    p = next(x for x in cfg["parameters"] if x["atlas_id"] == aid)
    _, body, _ = write_context_preset("QUAL_BISECT", cfg["contexts"][p["context"]], str(HERE / "contexts"))
    be = sb.SerumBackend(cfg); be.load(body); be.observe()
    for v in values:
        print("SEQ before", v, flush=True)
        m = copy.deepcopy(body); body_set(m, p["mutation"]["path"], v)
        be.load(m); be.observe(); print("SEQ ok", v, flush=True)


def main(ids):
    cfg = json.load(open(HERE / "manifest_campaign_v1.json"))
    sys.path.insert(0, str(HERE))
    from range_plan import plan
    results = {}
    for aid in ids:
        d = next(x for x in cfg["parameters"] if x["atlas_id"] == aid)["domain"]
        v = plan(d); vals = v["values"] + v["probes"]
        rows = []
        for val in vals:
            r = subprocess.run([sys.executable, __file__, "--trial", aid, repr(val)], cwd=str(HERE), capture_output=True, text=True, timeout=600)
            stages = [json.loads(l[6:]) for l in r.stdout.splitlines() if l.startswith("STAGE ")]
            last = stages[-1] if stages else {"stage": "none"}
            restored = last.get("stage") == "restored" and last.get("ok")
            verdict = "CRASHING" if r.returncode != 0 else ("SAFE" if restored else "UNRESOLVED")
            rows.append({"parameter": aid, "value": val, "process_exit_code": r.returncode & 0xFFFFFFFF, "survived": r.returncode == 0,
                         "last_stage": last["stage"], "state_readback": next((s.get("readback") for s in stages if s["stage"] == "state"), None),
                         "restored": bool(restored), "verdict": verdict})
            print(aid, val, verdict, hex(r.returncode & 0xFFFFFFFF), last["stage"], flush=True)
        results[aid] = rows
        OUT.write_text(json.dumps({"kind": "lfo_rate_crash_bisection_v1", "note": "one value per fresh Serum process; per-value verdicts, not per-parameter",
                                   "results": results}, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--seq"]:
        trial_seq(sys.argv[2], [float(x) for x in sys.argv[3:]])
    elif sys.argv[1:2] == ["--trial"]:
        trial(sys.argv[2], float(sys.argv[3]))
    else:
        main(sys.argv[1:] or ["lfo%d.rate" % i for i in range(1, 7)])
