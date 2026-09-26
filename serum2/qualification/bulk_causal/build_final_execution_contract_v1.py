"""Build the final producer-facing MCP execution contract (v1) purely from committed evidence.

Inputs (read-only, never modified):
  - giant_verify_out/bulk_ui_verification/mcp_exec_all_v3_results.jsonl  (LIVE execution authority)
  - giant_verify_out/bulk_ui_verification/mcp_exec_all_v2_results.jsonl  (v3-vs-v2 comparison only)
  - parameter_characterization/bulk_causal_evidence/mcp_execution_contract_v1.json  (MCP op + expected raw)
  - parameter_characterization/bulk_causal_evidence/serum_full_control_map_v8.json  (identity + reference)

Outputs:
  - parameter_characterization/bulk_causal_evidence/final_execution_contract_v1.json
  - parameter_characterization/bulk_causal_evidence/FINAL_EXECUTION_CONTRACT_REPORT_v1.md

The live v3 `outcome` is copied verbatim; nothing is re-derived or upgraded. Host identity is reported only when the
live run observed a named host parameter change; a raw path alone never implies a host parameter.
"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ED = REPO / "parameter_characterization" / "bulk_causal_evidence"
LIVE_DIR = HERE / "giant_verify_out" / "bulk_ui_verification"
V3 = LIVE_DIR / "mcp_exec_all_v3_results.jsonl"
V2 = LIVE_DIR / "mcp_exec_all_v2_results.jsonl"
CONTRACT = ED / "mcp_execution_contract_v1.json"
HOST_DUMP = HERE / "giant_verify_out" / "reference_parameter_text.json"
MAP_V8 = ED / "serum_full_control_map_v8.json"
LIVE_META = ED / "finish_line_b_live_serum_evidence_v1.json"
OUT_JSON = ED / "final_execution_contract_v1.json"
OUT_MD = ED / "FINAL_EXECUTION_CONTRACT_REPORT_v1.md"

SERUM_VERSION = "2.0.23"
SERUM_SHA256 = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"
HOST, RAW, EXC = "MCP_EXEC_HOST_CONFIRMED", "MCP_EXEC_RAW_ONLY", "MCP_EXEC_CONFORMANCE_EXCEPTION"
FAILED, NOOP = "MCP_EXEC_FAILED", "MCP_EXEC_NOOP_SUSPECT"
EXPECTED = {"total": 330, HOST: 183, RAW: 127, EXC: 20}

CLASSIFICATION_RULES = {
    HOST: "live MCP execution succeeded and the expected named host parameter behavior was confirmed "
          "(a named VST3 host parameter's text changed in the live run)",
    RAW: "live MCP execution succeeded and the raw state persisted and restored correctly, but no reliable named "
         "host confirmation exists; the control is executed as a raw-field edit, NOT as a native host parameter",
    EXC: "execution occurred but a known, documented Serum/schema/UI divergence remains; never counted as success",
    "policy": [
        "final_classification is the LIVE v3 `outcome`, copied verbatim; it is never reinterpreted or upgraded",
        "an exception is never converted into success",
        "host identity is reported only from the live run's observed named host change, never from a raw path",
        "not all 330 controls are native VST3 host parameters; only HOST_CONFIRMED rows carry live host identity",
    ],
}
PATHS = {
    "live_v3": "serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_all_v3_results.jsonl",
    "live_v2": "serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_all_v2_results.jsonl",
    "contract": "parameter_characterization/bulk_causal_evidence/mcp_execution_contract_v1.json",
    "map_v8": "parameter_characterization/bulk_causal_evidence/serum_full_control_map_v8.json",
    "host_dump": "serum2/qualification/bulk_causal/giant_verify_out/reference_parameter_text.json",
}


def load_jsonl(p):
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def index_unique(rows, what):
    out = {}
    for r in rows:
        assert r["atlas_id"] not in out, f"duplicate atlas_id {r['atlas_id']} in {what}"
        out[r["atlas_id"]] = r
    return out


def live_host(live, v8c, dump):
    """Host identity as observed live. Index comes from map v8 only when the names agree."""
    q4 = live.get("q4") or {}
    name = None
    if q4.get("named_changed") and q4.get("named"):
        name = q4["named"]
    elif live["outcome"] == HOST and len(q4.get("changed_hosts") or []) == 1:
        name = q4["changed_hosts"][0]
    hp = (v8c.get("serum_native_identity") or {}).get("host_parameter") or {}
    index, index_source = None, None
    if name is not None and hp.get("name") == name:
        index, index_source = hp.get("index"), "map_v8.serum_native_identity"
    elif name is not None and name in dump:
        index, index_source = dump[name]["index"], "reference_parameter_text.json (name-keyed host dump)"
    return {
        "host_parameter_present": name is not None or (live["outcome"] == HOST and bool(q4.get("changed_hosts"))),
        "host_parameter_name": name,
        "host_parameter_index": index,
        "host_parameter_index_source": index_source,
        "host_text_pre": q4.get("named_pre") if name == q4.get("named") else None,
        "host_text_post": q4.get("named_post") if name == q4.get("named") else None,
        "changed_hosts_observed": q4.get("changed_hosts") or [],
        "host_identity_note": None if name is not None or not q4.get("changed_hosts") else
        "live run changed several host parameters; no single named host identity is asserted",
    }


def exception_details(live, v8c):
    if live["outcome"] != EXC:
        return None
    q4 = live.get("q4") or {}
    return {
        "reference_conclusion": v8c["final_conclusion"],
        "reference_reason": v8c.get("final_reason"),
        "live_oracle": q4.get("oracle"),
        "oracle_match": live.get("oracle_match"),
        "oracle_observed": live.get("oracle_observed"),
        "leaves_not_persisted": [l["path"] for l in live["q3_leaves"] if not l.get("persisted")],
        "policy": "known documented divergence; do not treat as success and do not reopen",
    }


def build():
    v3 = load_jsonl(V3)
    v2 = load_jsonl(V2)
    live = index_unique(v3, "v3")
    live2 = index_unique(v2, "v2")
    contract = index_unique(json.loads(CONTRACT.read_text())["rows"], "contract")
    v8 = index_unique(json.loads(MAP_V8.read_text())["controls"], "map_v8")
    dump = json.loads(HOST_DUMP.read_text())["reference"]
    ids = set(live)
    assert len(v3) == EXPECTED["total"] and len(ids) == EXPECTED["total"], "v3 must hold 330 unique rows"
    assert ids == set(contract) == set(v8) == set(live2), "atlas_id sets differ across sources"

    rows = []
    for aid in sorted(ids):
        L, C, M = live[aid], contract[aid], v8[aid]
        assert L["serum_sha256"] == SERUM_SHA256, aid
        assert L["test_value"] == C["test_value"], f"test_value mismatch {aid}"
        assert [l["path"] for l in L["q3_leaves"]] == [e["path"] for e in C["expected_raw"]], f"raw path mismatch {aid}"
        assert L["q5_reference"] == C["q5_reference_conclusion"] == M["final_conclusion"], f"reference mismatch {aid}"
        assert C["mcp_edit"]["kind"] == M["semantic_field"]["kind"], f"kind mismatch {aid}"
        edit = C["mcp_edit"]
        rows.append({
            "atlas_id": aid,
            "semantic_identity": M["semantic_field"],
            "mutation_mechanism": M.get("mutation_mechanism"),
            "context_requirements": M.get("context_requirements"),
            "declared_domain": M.get("declared_domain"),
            "mcp_operation": {"kind": edit["kind"], "field": edit.get("field"), "attr": edit.get("attr"),
                              "edit": edit},
            "test_value": C["test_value"],
            "expected_raw": C["expected_raw"],
            "live_execution": {
                "outcome": L["outcome"],
                "q1_addressable": L["q1_addressable"],
                "q2_raw_written": L["q2_raw_written"],
                "leaves": L["q3_leaves"],
                "q4": L["q4"],
            },
            "execution_kind": "NATIVE_HOST_PARAMETER_CONFIRMED" if L["outcome"] == HOST else "RAW_FIELD",
            **{k: v for k, v in live_host(L, M, dump).items()},
            "host_verification_mode": L["q4_mode"],
            "restoration_verified": L["restoration_verified"],
            "serum_version": SERUM_VERSION,
            "serum_binary_sha256": L["serum_sha256"],
            "reference_conclusion": M["final_conclusion"],
            "reference_reason": M.get("final_reason"),
            "final_execution_classification": L["outcome"],
            "exception": exception_details(L, M),
            "v3_identical_to_v2": L == live2[aid],
            "bucket": L["bucket"],
            "source_evidence": {
                "live_execution": f"{PATHS['live_v3']}#atlas_id={aid}",
                "live_execution_prior": f"{PATHS['live_v2']}#atlas_id={aid}",
                "contract": f"{PATHS['contract']}#rows[atlas_id={aid}]",
                "control_map": f"{PATHS['map_v8']}#controls[atlas_id={aid}]",
            },
        })
    counts = collections.Counter(r["final_execution_classification"] for r in rows)
    summary = {
        "total_controls": len(rows),
        "conforming_executable": counts[HOST] + counts[RAW],
        HOST: counts[HOST], RAW: counts[RAW], EXC: counts[EXC],
        FAILED: counts[FAILED], NOOP: counts[NOOP],
        "restoration_verified": sum(r["restoration_verified"] for r in rows),
        "v3_vs_v2_identical": all(r["v3_identical_to_v2"] for r in rows),
        "host_confirmed_with_single_named_identity": sum(r["final_execution_classification"] == HOST and r["host_parameter_name"] is not None for r in rows),
        "host_confirmed_multi_host_side_effect": sorted(r["atlas_id"] for r in rows if r["final_execution_classification"] == HOST and r["host_parameter_name"] is None),
    }
    lookup = {r["atlas_id"]: {
        "op": {k: v for k, v in r["mcp_operation"]["edit"].items() if k != "value"},
        "raw": [[".".join(map(str, e["path"])), e["value"]] for e in r["expected_raw"]],
        "verify": r["host_verification_mode"] + (f" -> {r['host_parameter_name']}" if r["host_parameter_name"] else ""),
        "class": r["final_execution_classification"],
        "exception_policy": "KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS" if r["exception"] else "NONE",
    } for r in rows}
    doc = {
        "version": 1,
        "final": True,
        "authority": "live v3 sweep outcome, copied verbatim",
        "serum_version": SERUM_VERSION,
        "serum_binary_sha256": SERUM_SHA256,
        "sources": PATHS,
        "classification_rules": CLASSIFICATION_RULES,
        "summary": summary,
        "exceptions": sorted(r["atlas_id"] for r in rows if r["exception"]),
        "producer_lookup": lookup,
        "rows": rows,
    }
    validate(doc)
    return doc


def validate(doc):
    s, rows = doc["summary"], doc["rows"]
    ids = [r["atlas_id"] for r in rows]
    assert len(ids) == len(set(ids)) == EXPECTED["total"]
    for k in (HOST, RAW, EXC):
        assert s[k] == EXPECTED[k], (k, s[k])
    assert s["conforming_executable"] == 310
    assert s[FAILED] == 0 and s[NOOP] == 0
    assert s["restoration_verified"] == EXPECTED["total"]
    assert s["v3_vs_v2_identical"]
    assert len(doc["exceptions"]) == 20
    for r in rows:
        assert r["live_execution"]["outcome"] == r["final_execution_classification"]
        if r["final_execution_classification"] != HOST:
            assert r["execution_kind"] == "RAW_FIELD"
        if r["final_execution_classification"] == RAW:
            assert not r["host_parameter_present"], r["atlas_id"]
        if r["final_execution_classification"] == HOST:
            assert r["host_parameter_present"] and r["changed_hosts_observed"], r["atlas_id"]


def fmt(v):
    return json.dumps(v, separators=(",", ":"))


def report(doc):
    s = doc["summary"]
    by = {r["atlas_id"]: r for r in doc["rows"]}
    out = [
        "# Final MCP Execution Contract v1 — Report", "",
        "Built entirely from committed evidence; no Serum rerun, no GUI exploration, no new controls.",
        "Live v3 sweep outcome is the execution authority and is copied verbatim.", "",
        f"- Serum version: `{doc['serum_version']}`",
        f"- Serum binary SHA256: `{doc['serum_binary_sha256']}`",
        "- Contract: `final_execution_contract_v1.json`", "",
        "## Counts", "", "| metric | value |", "|---|---|",
        f"| total controls | {s['total_controls']} |",
        f"| conforming / executable | {s['conforming_executable']} |",
        f"| conformance exceptions | {s[EXC]} |",
        f"| host-confirmed | {s[HOST]} |",
        f"| raw-only | {s[RAW]} |",
        f"| execution failures | {s[FAILED]} |",
        f"| noop suspects | {s[NOOP]} |",
        f"| restoration verified | {s['restoration_verified']}/{s['total_controls']} |",
        f"| v3 vs v2 | {'identical' if s['v3_vs_v2_identical'] else 'DIFFERENT'} |", "",
        "Only the 183 host-confirmed rows carry live VST3 host-parameter evidence. The 127 raw-only rows "
        "(and the 20 exceptions) execute as raw-field edits; the 330 controls are **not** all native host parameters.", "",
        f"Of the 183 host-confirmed rows, {s['host_confirmed_with_single_named_identity']} have a single named host "
        f"parameter; {', '.join('`%s`' % a for a in s['host_confirmed_multi_host_side_effect'])} is host-confirmed by the "
        "live run but changed several host parameters, so no single host identity is asserted for it.", "",
        "## Classification rules", "",
        f"- `{HOST}` — {CLASSIFICATION_RULES[HOST]}",
        f"- `{RAW}` — {CLASSIFICATION_RULES[RAW]}",
        f"- `{EXC}` — {CLASSIFICATION_RULES[EXC]}",
        *[f"- {p}" for p in CLASSIFICATION_RULES["policy"]], "",
        "## The 20 conformance exceptions", "",
        "| atlas_id | reference conclusion | reason / live oracle |", "|---|---|---|",
    ]
    for aid in doc["exceptions"]:
        e = by[aid]["exception"]
        why = (e["live_oracle"] or e["reference_reason"] or "").replace("|", "\\|")
        out.append(f"| `{aid}` | {e['reference_conclusion']} | {why} |")
    out += ["", "## Producer lookup", "",
            "`atlas_id -> MCP operation -> expected raw path=value -> verification -> exception policy`. "
            "The same index is in the JSON under `producer_lookup`.", "",
            "| atlas_id | MCP operation | expected raw | verification | class | exception policy |",
            "|---|---|---|---|---|---|"]
    for aid, L in doc["producer_lookup"].items():
        raw = "<br>".join(f"`{p}`={fmt(v)}" for p, v in L["raw"])
        out.append(f"| `{aid}` | `{fmt(L['op'])}` | {raw} | {L['verify']} | {L['class'].replace('MCP_EXEC_', '')} "
                   f"| {L['exception_policy']} |")
    out += ["", "## Validation", "",
            "Enforced by the builder and by `test_final_execution_contract_v1.py`: 330 unique atlas_ids identical "
            "across v3, v2, contract v1 and map v8; counts 183/127/20; 0 failures; 0 noop suspects; 330/330 "
            "restoration verified; every row's test value, raw paths and reference conclusion cross-checked against "
            "contract v1 and map v8; v3 == v2 per row; raw-only rows carry no host identity.", ""]
    return "\n".join(out)


def main():
    doc = build()
    OUT_JSON.write_text(json.dumps(doc, indent=1) + "\n")
    OUT_MD.write_text(report(doc))
    print(json.dumps(doc["summary"], indent=1))


if __name__ == "__main__":
    main()
