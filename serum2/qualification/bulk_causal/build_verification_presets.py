"""Bulk DIRECT-UI verification, stage 2: build ONE composite verification preset PER CONTEXT (not one per parameter,
not one per mutation), containing every candidate's known target value applied SIMULTANEOUSLY. This is a different
bulk stage from B.1/B.2's causal qualification (sequential mutate -> observe -> restore, one row per value): here the
state is already qualified, and the goal is to load a FINISHED state once and read many controls off one screen.

    python build_verification_presets.py <campaign_run_gui.json> <manifest.json> <out_dir>

For each context: start from build_context_body(ctx) (the same canonical context body the causal engine used), then
apply EVERY candidate's target value in that context at once (no restore between candidates -- there is nothing to
restore, this is a single finished state). Writes contexts/VERIFY_<context>.SerumPreset plus verification_plan.json:
{atlas_id -> {context, kparam, raw_path, target_value, declared_domain, expected: written/normalized}}. A human or a
screen-reader then loads each preset ONCE and reads however many controls that context's UI page shows.

Target value selection (per candidate, from the GUI campaign's own evidence, never invented):
  - must be a value Serum actually retained (state_value is not None, matches "written")
  - prefer a non-probe, non-default value close to mid-range (mirrors unify.pick_pair's numeric choice, without
    requiring Atlas identity -- this stage doesn't need promotion, only a visually distinguishable target)
  - bool: 1.0 if retained, else 0.0
  - enum/text: skipped here (no GUI-proven labels at this stage) -- explicitly listed as excluded, not guessed

Candidates with NO retained value (STATE_NOT_OBSERVED) or that never derived (NOT_DERIVED) are explicitly excluded
and listed, never silently dropped and never given an invented target.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set, resolve_path  # noqa: E402
from preset_build import build_context_body, pack_file  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402


def pick_target(rec):
    """Return (target_value, why_excluded). why_excluded is None iff target_value is usable."""
    g = rec["range"]
    kind = rec["declared"]["kind"]
    base = g["discovered_default"] if g["discovered_default"] is not None else rec["declared"].get("default")
    kept = [v for v in rec["values"] if not v["probe"] and v["state_value"] is not None]
    if not kept:
        return None, "no retained value in this run (STATE_NOT_OBSERVED)"
    if kind == "bool":
        m = next((v for v in kept if v["state_value"] in (0.0, 1.0) and v["state_value"] != base), None)
        return (m["state_value"], None) if m else (None, "no retained 0/1 value differing from default")
    if kind in ("enum", "enum_str", "text"):
        return None, "enum/text needs GUI-proven labels; not resolved at this evidence stage"
    numeric = [v for v in kept if isinstance(v["state_value"], (int, float)) and not isinstance(v["state_value"], bool)
               and (base is None or abs(v["state_value"] - base) > 1e-9)]
    if not numeric:
        return None, "no retained numeric value differing from default"
    lo, hi = g["reachable_min"], g["reachable_max"]
    mid = (lo + hi) / 2 if lo is not None and hi is not None else numeric[0]["state_value"]
    v = min(numeric, key=lambda r: abs(r["state_value"] - mid))
    return v["state_value"], None


def main(run_path, manifest_path, out_dir):
    run = json.loads(open(run_path).read())
    manifest = json.loads(open(manifest_path).read())
    recs = {r["atlas_id"]: r for r in run["records"]}
    os.makedirs(out_dir, exist_ok=True)

    by_context = {}
    for p in manifest["parameters"]:
        by_context.setdefault(p["context"], []).append(p)

    plan = {"source_run": os.path.abspath(run_path), "source_manifest": os.path.abspath(manifest_path), "contexts": {}}
    for name, params in by_context.items():
        ctx = manifest["contexts"][name]
        body, meta = build_context_body(ctx)
        applied, excluded = [], []
        seen_paths = {}   # tuple(path) -> (target_value, first atlas_id) -- catches TRUE conflicts, allows identity aliases
        for p in params:
            aid = p["atlas_id"]
            rec = recs.get(aid)
            if rec is None:
                excluded.append({"atlas_id": aid, "reason": "absent from run evidence (NOT_DERIVED or SERUM_CRASH)"})
                continue
            target, why = pick_target(rec)
            if why:
                excluded.append({"atlas_id": aid, "reason": why})
                continue
            path = resolve_path(p["mutation"])
            pk = tuple(path)
            if pk in seen_paths:
                prev_target, prev_aid = seen_paths[pk]
                if not (prev_target == target or (isinstance(prev_target, float) and isinstance(target, float) and abs(prev_target - target) < 1e-9)):
                    # two DIFFERENT atlas_ids disagree on the target for the SAME underlying path: a real identity/atlas
                    # conflict, not something this evidence-only stage may silently resolve either way
                    excluded.append({"atlas_id": aid, "reason": "path collision with %s at %s: targets disagree (%r vs %r) -- "
                                     "likely a duplicate/aliased Atlas identity needing separate resolution" % (prev_aid, path, target, prev_target)})
                    continue
                # same path, same target: a harmless duplicate identity for the same physical control (e.g.
                # "filter1.enabled" / "mixer.filter1.enable") -- both are verifiable from the one shared reading
            else:
                body_set(body, path, target)
                seen_paths[pk] = (target, aid)
            applied.append({"atlas_id": aid, "kparam": path[-1], "raw_path": path, "target_value": target,
                            "alias_of": seen_paths[pk][1] if seen_paths[pk][1] != aid else None,
                            "declared_domain": rec["declared"], "reachable_range": {"min": rec["range"]["reachable_min"],
                                                                                    "max": rec["range"]["reachable_max"]}})
        # verify: every applied target actually landed at its own path (no unresolved cross-candidate collision)
        for a in applied:
            got = body_get(body, a["raw_path"])
            assert got == a["target_value"] or (isinstance(got, float) and isinstance(a["target_value"], float) and abs(got - a["target_value"]) < 1e-9), \
                "collision building %s: %s wrote %r but body has %r" % (name, a["atlas_id"], a["target_value"], got)
        preset_path = os.path.join(out_dir, "VERIFY_%s.SerumPreset" % name)
        pack_file(SerumPreset(metadata=dict(meta, presetName="VERIFY_%s" % name), data=copy.deepcopy(body)), preset_path)
        plan["contexts"][name] = {"preset": os.path.relpath(preset_path, out_dir), "applied_count": len(applied),
                                  "excluded_count": len(excluded), "applied": applied, "excluded": excluded}
        print("%-14s applied=%3d excluded=%3d -> %s" % (name, len(applied), len(excluded), preset_path))

    total_applied = sum(c["applied_count"] for c in plan["contexts"].values())
    total_excluded = sum(c["excluded_count"] for c in plan["contexts"].values())
    plan["summary"] = {"total_candidates_in_manifest": len(manifest["parameters"]), "total_applied": total_applied, "total_excluded": total_excluded}
    json.dump(plan, open(os.path.join(out_dir, "verification_plan.json"), "w"), indent=1)
    print("\ntotal: %d applied, %d excluded, %d contexts -> %d composite presets" % (total_applied, total_excluded, len(by_context), len(by_context)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
