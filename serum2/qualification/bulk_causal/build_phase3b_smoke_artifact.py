"""Phase 3B smoke-test artifact: the 9 representative MCP execution tests, derived from mcp_execution_contract_v1.json
(read-only) and run_mcp_execution_harness.py's real flow. Nothing is hand-typed per control; only the per-mode rules are.

    python build_phase3b_smoke_artifact.py -> parameter_characterization/bulk_causal_evidence/mcp_smoke_phase3b_v1.json
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")

TESTS = [("A", "NAMED", ["env1.attack", "global.bend_range_down"]),
         ("B", "FULL_SCAN", ["arp.pattern.rate", "fx.bode.blur", "lfo1.dotted"]),
         ("B", "NAMED_THEN_FULL_SCAN", ["lfo1.rate_10x"]),
         ("D", "ORACLE", ["arp.transpose.range", "fx.compressor.attack", "macro1.name"])]

FLOW = ["load(baseline body) -> state()+hosts() = pre_state/pre_hosts",
        "load(edited body)   -> state()+hosts() = post_state/post_hosts",
        "load(baseline body) again -> state() = restored_state (Q6 restoration check)"]

PASS = {
    "NAMED": "outcome MCP_EXEC_HOST_CONFIRMED: expected leaf persisted (post == written), the named host parameter's text changed "
             "pre -> post, restoration_verified true, serum_sha256 stamped",
    "FULL_SCAN": "outcome MCP_EXEC_RAW_ONLY or MCP_EXEC_HOST_CONFIRMED: expected leaf persisted, restoration_verified true. Any changed host "
                 "text is recorded as a new identity candidate, not a pass/fail signal",
    "NAMED_THEN_FULL_SCAN": "as FULL_SCAN, but the named host parameter is checked first and the 412-parameter scan runs only if it did not change",
    "ORACLE": "outcome MCP_EXEC_CONFORMANCE_EXCEPTION with the observation recorded against the oracle, leaf persisted (or absent as the oracle "
              "states), restoration_verified true",
}
BLOCKING = "MCP_EXEC_FAILED (build/load error, or the written leaf came back different) or MCP_EXEC_NOOP_SUSPECT (post_state unchanged) blocks the 330 sweep"


def mcp_operation(e):
    if e["kind"] == "field":
        return {"summary": "spec.%s[%d].%s = %r" % (e["list"], e["index"], e["field"], e["value"]),
                "built_with": "serum_mcp.preset.mapping.apply_spec on the campaign companion spec (client_bodies)"}
    if e["kind"] == "singleton_field":
        return {"summary": "spec.%s.%s = %r" % (e["attr"], e["field"], e["value"]),
                "built_with": "serum_mcp.preset.mapping.apply_spec on the campaign companion spec (client_bodies)"}
    return {"summary": "spec.fx_chain = [FxUnitSpec(type=%s, params={%s: %r}, wet=100.0)]" % (e["fx_type"], e["param"], e["value"]),
            "built_with": "FxUnitSpec.model_validate + apply_spec on SPEC0 (client_bodies, fx branch)"}


def main():
    rows = {r["atlas_id"]: r for r in json.load(open(os.path.join(ED, "mcp_execution_contract_v1.json")))["rows"]}
    prior = {}
    p = os.path.join(BUV, "mcp_exec_all_v2_results.jsonl")
    if os.path.exists(p):
        prior = {json.loads(l)["atlas_id"]: json.loads(l)["outcome"] for l in open(p) if l.strip()}
    tests = []
    for bucket, mode, ids in TESTS:
        for aid in ids:
            r = rows[aid]
            assert r["bucket"] == bucket and r["q4_host_text_check"]["mode"] == mode, (aid, r["bucket"], r["q4_host_text_check"]["mode"])
            q4 = r["q4_host_text_check"]
            named = q4.get("host_parameter")
            readback = ["Q3: post_state leaf at expected_raw path equals the written value (absent or unchanged from pre_state = no-op suspect)",
                        "Q6: reloading the untouched baseline reproduces pre_state at that leaf"]
            if mode == "NAMED":
                readback.append("Q4: host parameter %r (index %s) text pre vs post" % (named, q4["host_index"]))
            elif mode == "NAMED_THEN_FULL_SCAN":
                readback.append("Q4: host parameter %r (index %s) first; if unchanged, all 412 host texts pre vs post" % (named, q4["host_index"]))
            elif mode == "FULL_SCAN":
                readback.append("Q4: all 412 host parameter texts pre vs post")
            else:
                oc = q4.get("oracle_check")
                readback.append("Q4/oracle: " + (json.dumps(oc) if oc else "observation recorded against the oracle, not machine-checked"))
            known = ("none declared; reference conclusion %s (%s). Not a failure: %s" % (r["q5_reference_conclusion"], r["q5_reference_reason"], "RAW_ONLY is the expected outcome"
                     if r["q5_reference_conclusion"] in ("UI_OBSERVABLE_BUT_UNREADABLE", "UI_UNOBSERVABLE") else "a host-text miss is recorded, not failed")
                     if bucket != "D" else "%s (reference conclusion %s: %s)" % (q4["expected"], r["q5_reference_conclusion"], r["q5_reference_reason"]))
            tests.append({
                "atlas_id": aid, "bucket": bucket, "q4_mode": mode,
                "mcp_operation": mcp_operation(r["mcp_edit"]), "mcp_edit_raw": r["mcp_edit"],
                "test_value": r["test_value"], "test_value_source": r["test_value_source"],
                "expected_raw": r["expected_raw"],
                "preset_to_create": {"baseline": "SMOKE_3B_%s__baseline" % aid.replace(".", "_"),
                                     "edited": "SMOKE_3B_%s__edited" % aid.replace(".", "_"),
                                     "note": "labels only: bodies are built in memory (client_bodies) and reach Serum through ONE transient "
                                             "transport file overwritten on every load; no preset file is saved"},
                "serum_loader_action": FLOW,
                "readback_required": readback,
                "pass_condition": PASS[mode],
                "fail_condition": BLOCKING,
                "known_exception_condition": known,
                "prior_observed_outcome_v2": prior.get(aid),
            })
    ids = ",".join(t["atlas_id"] for t in tests)
    out = {"artifact": "mcp_smoke_phase3b_v1", "n_tests": len(tests), "source_contract": "mcp_execution_contract_v1.json (read-only)",
           "backend": "run_mcp_execution_harness.LiveBackend: real Serum 2 VST3 in DawDreamer, sha256 stamped per row",
           "run": "python serum2/qualification/bulk_causal/run_mcp_execution_harness.py --ids %s --out "
                  "serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_smoke_3b_results.jsonl" % ids,
           "stop_rule": "do not start the 330 sweep if any A or B test returns MCP_EXEC_FAILED or MCP_EXEC_NOOP_SUSPECT, or any D test fails to return "
                        "MCP_EXEC_CONFORMANCE_EXCEPTION",
           "tests": tests}
    path = os.path.join(ED, "mcp_smoke_phase3b_v1.json")
    json.dump(out, open(path, "w"), indent=1)
    print(path)
    for t in tests:
        print("%-2s %-22s %-24s %s" % (t["bucket"], t["q4_mode"], t["atlas_id"], t["mcp_operation"]["summary"]))


if __name__ == "__main__":
    main()
