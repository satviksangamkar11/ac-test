"""20-run qualification of create_serum_track (unchanged tool code). Stops on the first failure.
Per run: tool status == LOADED_VISUAL (drop accepted + preset-name bar changed), in-process Serum sha == pinned 2.0.23,
track renamed to the preset name, then that track is deleted and the track count must return to baseline.
Usage (from ableton-mcp-extended/):
  .venv/Scripts/python.exe qual20.py --out results.json [--runs 20] PRESET.SerumPreset [PRESET ...]
Presets are cycled in the order given. Nothing about the presets is built in: the caller or pipeline supplies them."""
import argparse
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())
from MCP_Server import serum_loader as sl  # noqa: E402
from MCP_Server import server  # noqa: E402

ap = argparse.ArgumentParser(description="Consecutive-run qualification of create_serum_track")
ap.add_argument("presets", nargs="+", help=".SerumPreset files, cycled in order")
ap.add_argument("--runs", type=int, default=20)
ap.add_argument("--out", required=True, help="results JSON path")
args = ap.parse_args()
PRESETS, RUNS, out_path = [os.path.abspath(p) for p in args.presets], args.runs, args.out
bad = [p for p in PRESETS if not (os.path.isfile(p) and p.lower().endswith(".serumpreset"))]
if bad:
    raise SystemExit("not .SerumPreset files: %s" % bad)
live = server.get_ableton_connection()
count = lambda: live.send_command("get_session_info")["track_count"]  # noqa: E731
baseline = count()
rec = {"started": datetime.datetime.now().isoformat(timespec="seconds"), "baseline_track_count": baseline,
       "criterion": "status LOADED_VISUAL (drop effect != 0 and preset-name bar changed >= 2%) + sha == pinned "
                    "2.0.23 + track renamed to preset + track deleted + track count back to baseline",
       "pinned_sha256": sl.PINNED_SHA256, "runs": []}


def save():
    json.dump(rec, open(out_path, "w"), indent=1)


for i in range(RUNS):
    preset = PRESETS[i % len(PRESETS)]
    t0 = time.time()
    r = json.loads(server.create_serum_track(None, preset))
    run = {"run": i + 1, "preset": os.path.basename(preset), "status": r["status"], "reason": r["reason"],
           "drop_effect": r.get("drop_effect"), "name_bar_changed": r.get("name_bar_changed"),
           "editor_pixels_changed": r.get("editor_pixels_changed"), "seconds": round(time.time() - t0, 1)}
    sha = list((r.get("serum_module_sha256") or {}).values())
    run["version_ok"] = bool(sha) and all(s == sl.PINNED_SHA256 for s in sha)
    problems = []
    if r["status"] != "LOADED_VISUAL":
        problems.append("status " + r["status"] + ": " + r["reason"])
    if not run["version_ok"]:
        problems.append("serum sha mismatch or missing")
    if r.get("track_index"):
        ti = r["track_index"]
        run["track_name"] = live.send_command("get_track_info", {"track_index": ti - 1})["name"]
        if run["track_name"] != os.path.splitext(run["preset"])[0]:
            problems.append("track name %r" % run["track_name"])
        run["cleanup"] = server.delete_track(None, ti)
        if not run["cleanup"].startswith("Deleted"):
            problems.append("cleanup failed: " + run["cleanup"])
    run["track_count_after"] = count()
    if run["track_count_after"] != baseline:
        problems.append("track count %d != baseline %d (rollback/cleanup leak)" % (run["track_count_after"], baseline))
    run["pass"] = not problems
    run["problems"] = problems
    rec["runs"].append(run)
    save()
    print("run %2d %-26s %-13s bar=%s %5.1fs %s" % (i + 1, run["preset"], r["status"], run["name_bar_changed"],
                                                     run["seconds"], "PASS" if run["pass"] else "FAIL " + "; ".join(problems)), flush=True)
    if problems:
        break

p = sum(x["pass"] for x in rec["runs"])
rec["summary"] = {"passed": p, "attempted": len(rec["runs"]), "required": RUNS, "qualified": p == RUNS,
                  "failures": len(rec["runs"]) - p,
                  "rollback_or_cleanup_failures": sum(any("count" in q or "cleanup" in q for q in x["problems"]) for x in rec["runs"]),
                  "wrong_serum_version": sum(not x["version_ok"] for x in rec["runs"])}
rec["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
save()
print(json.dumps(rec["summary"]))
