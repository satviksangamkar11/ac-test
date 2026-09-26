"""Phase 3A: the static MCP execution contract. One row per control: the real serum-mcp spec-field edit a client
would make (not a raw-path hack), a chosen test value, the expected raw outcome (Q1/Q2, computable offline because
encoder_diff.py already proved raw write == apply_spec for every comparable candidate), and the Q4 host-text check
strategy per bucket (agreed 2026-09-26, corrected after the local re-check of crosswalk v2). No Serum needed here;
Phase 3B is the first step that touches a live instance, using this file as its worklist.

    python build_mcp_execution_contract_v1.py

Per-row fields:
  atlas_id
  mcp_edit            {kind, ...} -- literally what to set on a PresetSpec/FxUnitSpec to exercise this control,
                      taken from serum_mcp_binding_table.json (the same bindings campaign_derive.py used)
  test_value          one concrete value in the declared domain (reuses the giant-preset target where the campaign
                      already validated one; else a fresh mid-domain pick)
  expected_raw        [(path, value), ...] apply_spec should produce -- Q1 (can MCP address it) + Q2 (does the raw
                      state land) collapse to "this diff succeeds and equals exactly this", checkable without Serum
  q3_reload_check     "the raw leaf must survive an unpack(pack(...)) round trip" -- Serum's own save/load is Phase
                      3B's job; this is the offline half of it (encoder_diff.py's roundtrip_ok, reused)
  q4_host_text_check  bucket-dependent (see build below): NAMED (check one parameter), FULL_SCAN (check all 412),
                      or ORACLE (a specific, already-known-divergent expected reading, for bucket D)
  q5_reference        the v8 final_conclusion/reason this test's live result should agree with
  bucket              A/B/D from the crosswalk

D-bucket oracles are the negative-test values already established across earlier evidence, not new guesses:
  fx.compressor.attack/ratio/release  -- schema domain is wrong; oracle checks the KNOWN corrected behavior
  mixer.noise.pan / .sub.pan / oscNoise.pan  -- off-by-one: display = round(raw) + 1 toward zero
  macro*.name  -- Serum shows "Macro N", never the written name
  global.fx_bus1/2_destination  -- vocabulary swapped (master shows DIRECT, direct shows BUS 1)
  arp.transpose.range  -- Serum's usable range stops at 8, not the declared 16
  global.use_ultra_on_render  -- expect NO persisted diff at all
  oscA.warp_amount  -- expect a monotonic but currently unmodeled display; no exact value asserted
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BT = os.path.join(REPO, "serum2", "reference", "serum_mcp_binding_table.json")
sys.path.insert(0, HERE)
from bulk_engine import _leaves_for, body_get, body_set, resolve_path  # noqa: E402
from campaign_derive import base_spec, companion_spec, diff_for, with_field  # noqa: E402
from preset_build import BASE, SPEC0, pack_unpack  # noqa: E402
from range_plan import close, plan as range_plan  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402

D_ORACLES = {
    "fx.compressor.attack": "DIVERGENT: displays raw ms with a numeric ratio, raw/100 ms only when ratio shows 'Limit' (control-map v8)",
    "fx.compressor.ratio": "DIVERGENT: raw==display for 1-8; 20 shows '32:1'; >=100 (and every value the campaign used, 210/430/31622) shows 'Limit'",
    "fx.compressor.release": "DIVERGENT: displays raw ms directly; the declared minimum 0.1 shows 1000 (schema minimum invalid)",
    "mixer.noise.pan": "DIVERGENT: display is written+1 toward zero (e.g. -20 -> '-19 L')",
    "mixer.sub.pan": "DIVERGENT: display is written+1 toward zero (e.g. -4 -> '-3 L')",
    "oscNoise.pan": "DIVERGENT: alias of mixer.noise.pan, same off-by-one",
    "global.fx_bus1_destination": "DIVERGENT: schema word 'master' (raw 1.0) displays DIRECT",
    "global.fx_bus2_destination": "DIVERGENT: schema word 'direct' (raw 2.0) displays BUS 1",
    "arp.transpose.range": "DIVERGENT: written 16 displayed as 8; Serum's usable range is narrower than declared",
    "global.use_ultra_on_render": "EXPECT NO DIFF: confirmed by direct toggle+save+diff test not persisted into any preset",
    "oscA.warp_amount": "EXPECT MONOTONIC, NO EXACT VALUE: Sync-mode display likely quantized, no smooth curve fits 8 points",
}
D_ORACLES.update({"macro%d.name" % i: "DIVERGENT: Serum shows 'Macro %d', never the written name" % i for i in range(1, 9)})


def spec_edit_and_diff(ctrl, atlas_id, value):
    """(mcp_edit dict, [(path, old, new), ...]) for one binding-table entry, reusing campaign_derive's own field
    setters so this is exactly the encoding path a real serum-mcp call takes."""
    if ctrl["kind"] == "fx":
        path = ["FXRack0", "FX", 0, ctrl["fx_type"], "plainParams", ctrl["param"]]
        b0 = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=ctrl["fx_type"], params={}, wet=100.0)]}))
        b1 = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=ctrl["fx_type"], params={ctrl["param"]: value}, wet=100.0)]}))
        edit = {"kind": "fx", "fx_type": ctrl["fx_type"], "param": ctrl["param"], "value": value}
        got = body_get(b1, path)
        return edit, [(path, body_get(b0, path), got)]
    spec_base, _ctx = companion_spec(ctrl)
    spec_base = spec_base or base_spec()
    d = diff_for(spec_base, ctrl, value)
    field_desc = {"list": ctrl["list"], "index": ctrl["index"]} if ctrl["kind"] == "field" else {"attr": ctrl["attr"]}
    edit = {"kind": ctrl["kind"], "field": ctrl["field"], "value": value, **field_desc}
    return edit, d


def pick_test_value(plan_row, domain, mutation, campaign_rec=None):
    if mutation["kind"] == "leaf_set":   # plan target_value is the raw table value, not the spec word apply_spec takes
        words = [w for w in domain["values"] if mutation["table"].get(w)]
        return (words[0] if words else domain["values"][0]), "first non-default vocabulary word"
    if plan_row and plan_row["status"] == "APPLIED_TO_GIANT_PRESET":
        return plan_row["target_value"], "reused giant-preset target (already GUI-cross-checked once)"
    if domain["kind"] in ("enum_str", "enum", "text"):
        return domain["values"][0] if domain["kind"] != "text" else "MCP_TEST", "first vocabulary word / literal"
    if domain["kind"] == "bool":
        return 1.0, "the non-default boolean state"
    if domain["kind"] == "open":
        stored = sorted({v["state_value"] for v in (campaign_rec or {}).get("values", [])
                         if isinstance(v.get("state_value"), (int, float)) and not isinstance(v["state_value"], bool)
                         and not v.get("load_error")})
        if stored:
            return stored[len(stored) // 2], "open domain: reused a value Serum itself stored in the campaign (no declared range to pick from otherwise)"
        return None, "open domain, and Serum never stored any written value for this key in the campaign either"
    v = range_plan(domain)["values"]
    return v[len(v) // 2], "midpoint of the declared domain"


def q4_strategy(row, cmap_row):
    if row["atlas_id"] in D_ORACLES:
        return {"mode": "ORACLE", "expected": D_ORACLES[row["atlas_id"]]}
    if row["host_identity_confidence"] in ("HIGH", "MEDIUM"):
        return {"mode": "NAMED", "host_parameter": row["host_parameter_name"], "host_index": row["host_parameter_index"],
               "expect": "this parameter's text changes from its pre-edit reading"}
    if row["host_identity_confidence"] == "LOW":
        return {"mode": "NAMED_THEN_FULL_SCAN", "host_parameter": row["host_parameter_name"], "host_index": row["host_parameter_index"],
               "expect": "check the named guess first; if it does NOT change, fall back to scanning all 412 host "
                         "parameters -- a hit there promotes this control's confidence, a miss confirms NONE-style scan below"}
    return {"mode": "FULL_SCAN", "expect": "scan all 412 host parameters' before/after text; none should change. Any "
                                          "change found is a NEW identity to feed back into the crosswalk, not a pass/fail signal"}


def main():
    bt = json.load(open(BT))["controls"]
    man = json.load(open(os.path.join(HERE, "manifest_campaign_v1.json")))
    params = {p["atlas_id"]: p for p in man["parameters"]}
    plan = {c["atlas_id"]: c for c in json.load(open(os.path.join(HERE, "giant_verify_out", "giant_verification_plan.json")))["candidates"]}
    cross = {r["atlas_id"]: r for r in json.load(open(os.path.join(ED, "serum_mcp_exposure_crosswalk_v2.json")))["controls"]}
    campaign_recs = {r["atlas_id"]: r for r in json.load(open(os.path.join(ED, "campaign_run_gui_v1.json")))["records"]}
    cmap = {c["atlas_id"]: c for c in json.load(open(os.path.join(ED, "serum_full_control_map_v8.json")))["controls"]}

    rows, skipped = [], []
    for aid, ctrl in sorted(bt.items()):
        row = cross[aid]
        p = params.get(aid)
        if p:
            domain, mutation = p["domain"], p["mutation"]
        elif ctrl["field"] == "voice_priority":
            domain, mutation = {"kind": "text", "values": None}, {"kind": "singleton_field"}
        else:   # arp.transpose.shape: use the 15-word vocabulary this repo already derived offline
            domain = {"kind": "enum_str", "values": [r["schema_word"] for r in
                      json.load(open(os.path.join(ED, "residual_arp_transpose_shape_v1.json")))["resolved"]]}
            mutation = {"kind": "singleton_field"}
        value, why = pick_test_value(plan.get(aid), domain, mutation, campaign_recs.get(aid))
        if value is None and domain["kind"] == "open":
            skipped.append({"atlas_id": aid, "reason": "open domain, no declared range to pick a test value from"})
            continue
        try:
            edit, diff = spec_edit_and_diff(ctrl, aid, value)
        except Exception as e:
            skipped.append({"atlas_id": aid, "reason": "apply_spec rejected the chosen test value: %s" % e})
            continue
        expected_raw = [{"path": d[0], "value": d[2]} for d in diff]
        # Q3 offline half: the roundtrip. Build the body with this edit applied and confirm pack/unpack preserves it.
        base_body = apply_spec(BASE.data, base_spec()) if ctrl["kind"] != "fx" else apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=ctrl["fx_type"], params={}, wet=100.0)]}))
        body = copy.deepcopy(base_body)
        for d in expected_raw:
            body_set(body, d["path"], d["value"])
        back = pack_unpack(BASE.metadata, body)
        roundtrip_ok = all(body_get(back, d["path"]) == d["value"] or (isinstance(d["value"], float) and abs(body_get(back, d["path"]) - d["value"]) < 1e-6) for d in expected_raw)

        rows.append({"atlas_id": aid, "mcp_edit": edit, "test_value": value, "test_value_source": why,
                    "expected_raw": expected_raw, "q3_roundtrip_offline_confirmed": roundtrip_ok,
                    "q4_host_text_check": q4_strategy(row, cmap[aid]),
                    "q5_reference_conclusion": cmap[aid]["final_conclusion"], "q5_reference_reason": cmap[aid]["final_reason"],
                    "bucket": row["bucket"]})

    assert all(r["q3_roundtrip_offline_confirmed"] for r in rows), [r["atlas_id"] for r in rows if not r["q3_roundtrip_offline_confirmed"]]
    out = {"version": 1, "total_bindings": len(bt), "contract_rows": len(rows), "skipped": skipped,
           "question_model": {"Q1": "can MCP address the control -- yes for every row here (that's why it's here)",
                              "Q2": "does MCP write the intended raw state -- expected_raw, computed via apply_spec, verified offline",
                              "Q3": "does Serum load/save that state -- q3_roundtrip_offline_confirmed is the offline half "
                                    "(pack/unpack); the LIVE half (real Serum save+reload) is Phase 3B's job",
                              "Q4": "does Serum expose it through host text -- q4_host_text_check, bucket-dependent",
                              "Q5": "does behavior agree with the contract -- q5_reference_conclusion/reason, from map v8"},
           "next_step": "Phase 3B: pick ~1 row per (bucket x q4 mode x mechanism) combination from this file, run it "
                        "against a live Serum instance, and confirm each row's expected_raw/q4 outcome actually happens "
                        "before running the other ~320 rows in bulk (Phase 3C).",
           "rows": rows}
    json.dump(out, open(os.path.join(ED, "mcp_execution_contract_v1.json"), "w"), indent=1, default=repr, ensure_ascii=False)
    print("contract rows:", len(rows), "skipped:", len(skipped))
    for s in skipped:
        print("  SKIP", s["atlas_id"], s["reason"])
    from collections import Counter
    print("by bucket:", dict(Counter(r["bucket"] for r in rows)))
    print("by q4 mode:", dict(Counter(r["q4_host_text_check"]["mode"] for r in rows)))


if __name__ == "__main__":
    main()
