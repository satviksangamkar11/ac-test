"""TRUE context-based bulk verification: one canonical preset per context, many parameters swept inside it.

    python bulk_worker.py <bulk_manifest.json> <evidence_out.json>

Manifest: {"contexts": {name: {"preset_name", "fx": [{type, params}], "spec_patch"}}, "parameters": [{atlas_id, context,
mutation: {kind, ...}, domain: {kind, min, max, ...}}], render_sec, note, bands, session_size, min_noise_floor_db}.
The per-parameter value vector + probes come from range_plan (generic). Evidence is one record per PARAMETER (values,
raw retained value, audio deltas, host changes, file round-trip, restoration, reachable range, clamps, default behaviour).
Runs in its OWN process (imports the older repo's serum2 via serum_backend). Writes exactly one persistent preset per context
(into ./contexts/) and never touches any authority artifact (bindings, surface, registry, contracts). The legacy per-test
worker.py is untouched, so every v1/v2 historical evidence file stays reproducible.
"""
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serum_backend as sb  # noqa: E402  (imports the old repo's serum2; keep this file out of this repo's normal imports)
from bulk_engine import ENGINE_CONTRACT_VERSION, run_context  # noqa: E402
from preset_build import write_context_preset  # noqa: E402

PINNED_SHA = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(manifest, out, progress=None):
    cfg = json.load(open(manifest))
    done_ids, prev = set(), []
    if progress and os.path.exists(progress):    # resume: skip what a previous (possibly crashed) worker already recorded
        for line in open(progress).read().splitlines():
            if line.strip():
                j = json.loads(line)
                if j["t"] in ("record", "crash"):
                    done_ids.add(j["id"])
                    prev.append(j)
    log = open(progress, "a") if progress else None
    def on_start(p):
        if log:
            log.write(json.dumps({"t": "start", "id": p["atlas_id"]}) + chr(10))
            log.flush()
    def on_record(rec):
        if log:
            log.write(json.dumps({"t": "record", "id": rec["atlas_id"], "rec": rec}) + chr(10))
            log.flush()
    got = sha(sb.epoch.SERUM_BINARY)
    if got != PINNED_SHA:
        raise SystemExit("Serum binary is %s, expected the pinned 2.0.23 build" % got)
    ctx_dir = os.path.join(HERE, "contexts")
    counters, records, presets = {}, [], []
    for name, ctx in cfg["contexts"].items():
        params_all = [p for p in cfg["parameters"] if p["context"] == name]
        params = [p for p in params_all if p["atlas_id"] not in done_ids]
        path, body, meta = write_context_preset(ctx.get("preset_name", name), ctx, ctx_dir)   # the ONE persistent preset
        presets.append({"context": name, "path": os.path.relpath(path, HERE), "sha256": sha(path), "parameters": len(params_all)})
        recs = run_context(name, body, params, lambda: sb.SerumBackend(cfg), cfg, counters, meta=meta, on_start=on_start, on_record=on_record) if params else []
        for r in recs:
            print("%-30s %-14s restore=%s reach=[%s,%s]" % (r["atlas_id"], r["candidate"]["kparam"], r["restoration"]["ok"],
                                                             r["range"]["reachable_min"], r["range"]["reachable_max"]))
        records += recs
    if progress:      # final assembly from the progress file (records from every worker generation + crash markers)
        allrec, crashes = {}, []
        for line in open(progress).read().splitlines():
            if line.strip():
                j = json.loads(line)
                if j["t"] == "record":
                    allrec[j["id"]] = j["rec"]
                elif j["t"] == "crash":
                    crashes.append({"atlas_id": j["id"], "status": "SERUM_CRASH", "note": j.get("note")})
        records = [allrec[p["atlas_id"]] for p in cfg["parameters"] if p["atlas_id"] in allrec]
    values = sum(len(r["values"]) for r in records)
    json.dump({"harness": {"engine_contract_version": ENGINE_CONTRACT_VERSION, "product_version": "2.0.23", "state_version": 9.0, "architecture": "context-based bulk: parameter-by-parameter RAW mutation inside one qualification context",
                           "backend": "real Serum 2.0.23 VST3 in DawDreamer (headless): state readback + rendered band energy + host texts; not GUI",
                           "serum_sha256": got, "manifest": os.path.abspath(manifest), "manifest_sha256": sha(manifest),
                           "context_presets": presets, "persistent_presets_written": len(presets), "parameters": len(records),
                           "values_observed": values, "state_loads": counters.get("state_loads", 0), "sessions": counters.get("sessions", 0),
                           "context_loads": counters.get("context_loads"), "baseline_reloads": counters.get("baseline_reloads"),
                           "transient_transport_files": "one per Serum session, overwritten on every load (not a preset)",
                           "authorizes_nothing": True, "serum_crashes": crashes if progress else [], "generated": datetime.datetime.now(datetime.timezone.utc).isoformat()},
               "records": records}, open(out, "w"), indent=1)
    print("%d parameters, %d values, %d state loads, %d persistent preset(s)" % (len(records), values, counters.get("state_loads", 0), len(presets)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[sys.argv.index("--progress") + 1] if "--progress" in sys.argv else None)
