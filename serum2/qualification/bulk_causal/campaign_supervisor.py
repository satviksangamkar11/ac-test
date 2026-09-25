"""Crash-safe driver for a big bulk run. Serum/DawDreamer can die natively (no Python traceback), so progress is written to a JSONL
file as it happens and the worker is restarted until every parameter has either a record or an explicit SERUM_CRASH marker.

    python campaign_supervisor.py <bulk_manifest.json> <final_evidence.json> <progress.jsonl>

A parameter that was STARTED but never recorded when the worker died is the crash cause: it is marked SERUM_CRASH (evidence, not
silence) and skipped on the next restart. Nothing else about the engine changes; contexts and mutations are exactly the worker's.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def progress_state(path):
    started, done, crashed, order = [], set(), set(), []
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            j = json.loads(line)
            if j["t"] == "start":
                started.append(j["id"])
            elif j["t"] in ("record", "crash"):
                done.add(j["id"])
                if j["t"] == "crash":
                    crashed.add(j["id"])
    return started, done, crashed


def main(manifest, final, progress, max_restarts=80):
    manifest, final, progress = (str(Path(x).resolve()) for x in (manifest, final, progress))   # the worker runs with cwd=HERE
    cfg = json.loads(Path(manifest).read_text())
    ids = [p["atlas_id"] for p in cfg["parameters"]]
    for attempt in range(max_restarts):
        started, done, crashed = progress_state(progress)
        # a param that was started but never finished when the previous worker died is the crash cause
        open_ = [s for s in started if s not in done]
        if open_:
            with open(progress, "a") as f:
                f.write(json.dumps({"t": "crash", "id": open_[-1], "note": "worker process died while this parameter was running"}) + "\n")
            print("marked SERUM_CRASH:", open_[-1], flush=True)
            continue
        if all(i in done for i in ids):
            break
        print("attempt %d: %d/%d done" % (attempt, len(done), len(ids)), flush=True)
        r = subprocess.run([sys.executable, str(HERE / "bulk_worker.py"), manifest, final, "--progress", progress], cwd=str(HERE))
        print("worker exit code", r.returncode, flush=True)
    started, done, crashed = progress_state(progress)
    print("finished: %d/%d params accounted, %d marked SERUM_CRASH" % (len(done), len(ids), len(crashed)), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
