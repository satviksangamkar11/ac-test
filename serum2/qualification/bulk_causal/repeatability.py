"""Repeatability of a bulk run against a second run of the SAME manifest (pure).

    python repeatability.py <run1.json> <run2.json> [out.json]

Predefined contract (fixed BEFORE looking at any result):
    state / range fingerprint / restoration verdict / file round-trip  -> EXACT
    audio band energy per value (dB)                                   -> within AUDIO_TOL_DB
A measurement that only holds in one Serum session is not a measurement, so anything outside the contract is reported as a failure.
"""
import json
import sys

AUDIO_TOL_DB = 1.0


def compare(r1, r2, tol=AUDIO_TOL_DB):
    a = {(r["context"], r["candidate"]["kparam"], tuple(map(str, r["candidate"]["path"]))): r for r in r1["records"]}
    b = {(r["context"], r["candidate"]["kparam"], tuple(map(str, r["candidate"]["path"]))): r for r in r2["records"]}
    out = {"same_parameters": sorted(map(str, a)) == sorted(map(str, b)), "audio_tolerance_db": tol, "parameters": {}}
    for k in a.keys() & b.keys():
        x, y = a[k], b[k]
        fails = []
        if x["range"] != y["range"]:
            fails.append("range_fingerprint")
        if [(v["written"], v["state_value"], v["state_diff_keys"], v["file_roundtrip"]) for v in x["values"]] != \
           [(v["written"], v["state_value"], v["state_diff_keys"], v["file_roundtrip"]) for v in y["values"]]:
            fails.append("per_value_state")
        if x["restoration"]["ok"] != y["restoration"]["ok"] or not (x["restoration"]["ok"] and y["restoration"]["ok"]):
            fails.append("restoration")
        worst = max((abs(p - q) for u, v in zip(x["values"], y["values"]) for p, q in zip(u["band_db"], v["band_db"])), default=0.0)
        if worst > tol:
            fails.append("audio")
        out["parameters"][k[1]] = {"ok": not fails, "failed": fails, "max_audio_diff_db": round(worst, 3)}
    out["all_ok"] = out["same_parameters"] and all(p["ok"] for p in out["parameters"].values())
    out["max_audio_diff_db"] = max((p["max_audio_diff_db"] for p in out["parameters"].values()), default=0.0)
    return out


if __name__ == "__main__":
    res = compare(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
    if len(sys.argv) > 3:
        json.dump(res, open(sys.argv[3], "w"), indent=1)
    print("all_ok=%s  max_audio_diff=%.3f dB (tol %.1f)" % (res["all_ok"], res["max_audio_diff_db"], res["audio_tolerance_db"]))
    for k, v in res["parameters"].items():
        print("  %-16s %s %s" % (k, "OK " if v["ok"] else "FAIL", v["failed"] or v["max_audio_diff_db"]))
