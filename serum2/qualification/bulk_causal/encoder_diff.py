"""Offline encoder diff: does the causal engine's RAW write equal what serum-mcp's own apply_spec encoder writes?

    python encoder_diff.py [giant_verification_plan.json] [manifest.json] [out.json]

No Serum, no GUI. For every candidate the giant plan gave a target value (APPLIED_TO_GIANT_PRESET / _SECONDARY_PRESET):

    raw body     = apply_spec(context spec)  then  body_set(raw_path, target)     <- what bulk_engine / the giant preset wrote
    encoded body = apply_spec(context spec with the bound PresetSpec field / FX param = target)   <- what generation writes

and every differing leaf between the two bodies is reported (not just the candidate's own path: the encoder may write
elsewhere, or several leaves). Enum candidates map the raw target back to its spec word through the manifest's
vocabulary_map. Verdicts:
  IDENTICAL          encoder and raw write produce the same body -> the raw write is not an encoder bug for this control
  ENCODER_DIFFERS    bodies differ -> raw write skipped a transform the encoder applies (the compressor/sustain class)
  ENCODER_REJECTED   apply_spec refused the target value -> the target itself is outside the encoder's input domain
  NOT_COMPARABLE     no target, or no way back to a spec input (reason given)
Every plan candidate gets exactly one verdict. IDENTICAL does NOT prove GUI truth (Serum's loader may still disagree);
it only rules out the encoder-bypass cause.
"""
import copy
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set, resolve_path  # noqa: E402
from campaign_derive import BT, base_spec, companion_spec, leaves, with_field  # noqa: E402
from preset_build import BASE, SPEC0  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402


def _fx_body(fx_type, params):
    return apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=fx_type, params=params, wet=100.0)]}))


def _spec_input(param, target):
    """Raw target -> the value to hand the PresetSpec field. Numeric/bool: the same number (the derivation's assumption).
    Enum/text: invert vocabulary_map (raw -> spec word); leaf_set targets are already spec words."""
    m = param["mutation"]
    if m["kind"] == "leaf_set":
        return target, None
    vm = param.get("vocabulary_map")
    if vm is None:
        return target, None
    words = [w for w, raw in vm.items() if raw == target]
    if not words:
        return None, "raw target %r not in vocabulary_map %s" % (target, sorted(map(str, vm.values())))
    return words[0], None


def compare(param, ctrl, target):
    path = resolve_path(param["mutation"])
    if ctrl["kind"] == "fx":
        raw = _fx_body(ctrl["fx_type"], {})
        body_set(raw, path, target)
        try:
            enc = _fx_body(ctrl["fx_type"], {ctrl["param"]: target})
        except Exception as e:
            return {"verdict": "ENCODER_REJECTED", "error": "%s: %s" % (type(e).__name__, str(e)[:200])}
    else:
        spec_base = companion_spec(ctrl)[0] or base_spec()
        raw = apply_spec(BASE.data, spec_base)
        m = param["mutation"]
        if m["kind"] == "leaf_set":
            if target not in m["table"]:   # the plan may hold the PRIMARY leaf's retained value, not the word: map it back
                words = [w for w, lv in m["table"].items() if any(lp == m["primary"] and v == target for lp, v in lv)]
                if not words and body_get(raw, m["primary"]) == target:   # target == the base value: the word that writes nothing
                    words = [w for w, lv in m["table"].items() if not lv]
                if not words:
                    return {"verdict": "NOT_COMPARABLE", "reason": "leaf_set target %r matches no word's primary leaf" % (target,)}
                target = words[0]
            for lp, lv in m["table"][target]:
                body_set(raw, lp, lv)
        else:
            body_set(raw, path, target)
        spec_value, why = _spec_input(param, target)
        if why:
            return {"verdict": "NOT_COMPARABLE", "reason": why}
        try:
            enc = apply_spec(BASE.data, with_field(spec_base, ctrl, spec_value))
        except Exception as e:
            return {"verdict": "ENCODER_REJECTED", "spec_input": spec_value, "error": "%s: %s" % (type(e).__name__, str(e)[:200])}
    d = leaves(raw, enc)
    out = {"raw_leaf": body_get(raw, path), "encoded_leaf": body_get(enc, path)}
    if not d:
        out["verdict"] = "IDENTICAL"
    else:
        out["verdict"] = "ENCODER_DIFFERS"
        out["diffs"] = [{"path": p, "raw": a, "encoded": b} for p, a, b in sorted(d, key=lambda x: json.dumps(x[0], default=str))][:12]
        out["n_diff_leaves"] = len(d)
        out["own_path_differs"] = any(p == path for p, _a, _b in d)
    return out


def main(plan_path, manifest_path, out_path):
    plan = json.load(open(plan_path))
    manifest = {p["atlas_id"]: p for p in json.load(open(manifest_path))["parameters"]}
    bt = json.load(open(BT))["controls"]
    rows = []
    for c in plan["candidates"]:
        aid = c["atlas_id"]
        row = {"atlas_id": aid, "plan_status": c["status"], "target_value": c.get("target_value")}
        param, ctrl = manifest.get(aid), bt.get(aid)
        if c["status"] not in ("APPLIED_TO_GIANT_PRESET", "APPLIED_TO_SECONDARY_PRESET"):
            row.update({"verdict": "NOT_COMPARABLE", "reason": "no target value (%s)" % c["status"]})
        elif param is None or ctrl is None:
            row.update({"verdict": "NOT_COMPARABLE", "reason": "no manifest entry / binding"})
        else:
            row.update({"mechanism": param["mechanism"], "domain": param["domain"]})
            row.update(compare(param, ctrl, copy.deepcopy(c["target_value"])))
        rows.append(row)
    counts = Counter(r["verdict"] for r in rows)
    assert sum(counts.values()) == len(plan["candidates"])
    json.dump({"source_plan": os.path.relpath(plan_path, HERE), "source_manifest": os.path.relpath(manifest_path, HERE),
               "verdict_counts": dict(counts), "candidates": rows}, open(out_path, "w"), indent=1, default=repr)
    print(json.dumps(dict(counts), indent=1))
    for r in rows:
        if r["verdict"] in ("ENCODER_DIFFERS", "ENCODER_REJECTED"):
            print("%-17s %-34s target=%r raw=%r enc=%r %s" % (r["verdict"], r["atlas_id"], r["target_value"], r.get("raw_leaf"),
                                                            r.get("encoded_leaf"), r.get("error", "")[:80]))


if __name__ == "__main__":
    a = sys.argv[1:] + [None] * 3
    main(a[0] or os.path.join(HERE, "giant_verify_out", "giant_verification_plan.json"),
         a[1] or os.path.join(HERE, "manifest_campaign_v1.json"),
         a[2] or os.path.join(HERE, "giant_verify_out", "encoder_diff.json"))
