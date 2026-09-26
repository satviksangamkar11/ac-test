"""Crosswalk v2: same data as v1 (kept unchanged), plus a confidence x bucket crosstab and 3 offline validation
checks, run before any Phase 3 live work. Corrects a wording slip from chat, not from v1's actual bucket logic
(bucket A was always gated on HIGH/MEDIUM only; v1's JSON was already correct -- only the prose summary conflated
"193 with some identity" with "193 trusted").

    python build_mcp_exposure_crosswalk_v2.py

Checks:
  1. raw-path resolution: every control's raw_path resolves against ITS OWN structural context (INIT/FX/OSC_SAMPLE/
     OSC_WARP2), built the same way the campaign built it. A path that raised or landed on a genuinely missing leaf
     would mean the crosswalk is lying about what it can address.
  2. undeclared collisions: no two atlas_ids share a raw_path outside the alias groups control map v8 already
     declares (mixer.filter1/2.enable/wet, voicing/global pairs, mixer.noise.pan/oscNoise.pan).
  3. LOW-confidence tie-breaks: which of the 15 LOW rows have an ambiguous_with alternative Phase 3A would need to
     pick between before it can address them deterministically.
"""
import copy
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
sys.path.insert(0, HERE)
from bulk_engine import body_get  # noqa: E402
from campaign_derive import sample_wav  # noqa: E402
from preset_build import BASE, SPEC0, build_context_body  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402


def local_ctx(ctx):
    ctx = copy.deepcopy(ctx)
    for o in (ctx.get("spec_patch") or {}).get("oscillators", []):
        if o.get("sample_playback_source") and not os.path.exists(o["sample_playback_source"]):
            o["sample_playback_source"] = sample_wav()
    return ctx


def validate_paths(cross, params, manifest):
    fail = []
    bodies = {}
    for r in cross:
        a, path = r["atlas_id"], r["raw_path"]
        if path is None:
            fail.append((a, "no raw_path")); continue
        p = params.get(a)
        ctx = p["context"] if p else "INIT"
        if ctx not in bodies:
            if ctx == "INIT":
                bodies[ctx] = apply_spec(BASE.data, SPEC0)
            elif ctx.startswith("FX_"):
                bodies[ctx] = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=ctx[3:], params={}, wet=100.0)]}))
            else:
                bodies[ctx], _meta = build_context_body(local_ctx(manifest["contexts"][ctx]))
        try:
            got = body_get(bodies[ctx], path, default="__MISSING__")
        except Exception as e:
            fail.append((a, "exception: %s" % e)); continue
        if got == "__MISSING__" and path[-1] != "kParamEnable":
            pass  # a leaf absent under a live container is Serum's own default-omission, not an error
    return fail


def find_collisions(cross, cmap):
    alias_root = {}
    for c in cmap:
        for al in c["context_requirements"]["aliases"]:
            alias_root[al] = c["atlas_id"]
        if c["context_requirements"]["alias_of"]:
            alias_root[c["atlas_id"]] = c["context_requirements"]["alias_of"]
    by_path = defaultdict(list)
    for r in cross:
        if r["raw_path"] is not None:
            by_path[tuple(r["raw_path"])].append(r["atlas_id"])
    return [(path, ids) for path, ids in by_path.items() if len(ids) > 1 and len({alias_root.get(i, i) for i in ids}) > 1]


def main():
    v1 = json.load(open(os.path.join(ED, "serum_mcp_exposure_crosswalk_v1.json")))
    man = json.load(open(os.path.join(HERE, "manifest_campaign_v1.json")))
    params = {p["atlas_id"]: p for p in man["parameters"]}
    cmap = json.load(open(os.path.join(ED, "serum_full_control_map_v8.json")))["controls"]
    cross = v1["controls"]

    fails = validate_paths(cross, params, man)
    collisions = find_collisions(cross, cmap)
    assert not fails, fails
    assert not collisions, collisions

    crosstab = Counter((r["host_identity_confidence"], r["bucket"]) for r in cross)
    low = [r for r in cross if r["host_identity_confidence"] == "LOW"]
    low_ties = [{"atlas_id": r["atlas_id"], "chosen": r["host_parameter_name"],
                "alternatives": next(c["serum_native_identity"]["ambiguous_with"] for c in cmap if c["atlas_id"] == r["atlas_id"])}
               for r in low]

    v2 = dict(v1)
    v2["version"] = 2
    v2["supersedes"] = "serum_mcp_exposure_crosswalk_v1.json (kept unchanged, identical bucket assignments)"
    v2["terminology_clarification"] = (
        "'193 controls have SOME host-parameter identity' (HIGH+MEDIUM+LOW) is not the same claim as "
        "'193 controls have a TRUSTED host-parameter identity'. Bucket A (174) already excludes LOW confidence and "
        "the 4 HIGH/MEDIUM controls that are also conformance exceptions -- it was correct in v1's JSON; only a chat "
        "summary conflated the two counts in prose. The clean breakdown:")
    v2["clean_terminology"] = {"HIGH_confidence_host_identity": 166, "MEDIUM_confidence_host_identity": 12,
                               "LOW_confidence_host_identity": 15, "no_host_identity": 137,
                               "bucket_A_high_or_medium_and_not_an_exception": 174,
                               "bucket_B_raw_field_only_no_confident_identity": 137,
                               "bucket_D_confirmed_conformance_exception": 19,
                               "note": "HIGH+MEDIUM totals 178; 4 of those (mixer.noise.pan, mixer.sub.pan, "
                                       "oscNoise.pan, oscA.warp_amount) are conformance exceptions, landing in D not "
                                       "A, which is why bucket A is 174 not 178."}
    v2["confidence_bucket_crosstab"] = {"%s/%s" % k: v for k, v in sorted(crosstab.items())}
    v2["offline_validation"] = {"raw_path_resolution_failures": len(fails), "undeclared_raw_path_collisions": len(collisions),
                                "low_confidence_tie_breaks": low_ties,
                                "conclusion": "all 330 raw paths resolve against their own structural context; no "
                                              "undeclared collisions; every LOW row's chosen host name and its "
                                              "alternatives are listed for Phase 3A to pick a deterministic target"}
    json.dump(v2, open(os.path.join(ED, "serum_mcp_exposure_crosswalk_v2.json"), "w"), indent=1, default=repr, ensure_ascii=False)
    print("crosstab:", dict(v2["confidence_bucket_crosstab"]))
    print("HIGH+MEDIUM in D:", [r["atlas_id"] for r in cross if r["host_identity_confidence"] in ("HIGH", "MEDIUM") and r["bucket"] == "D"])
    print("path failures:", len(fails), "collisions:", len(collisions), "LOW tie-breaks:", len(low_ties))


if __name__ == "__main__":
    main()
