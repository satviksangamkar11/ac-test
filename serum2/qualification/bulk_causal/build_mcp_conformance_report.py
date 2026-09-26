"""Phase 3D: turn the harness results JSONL into the final MCP execution record + a readable report.

    python build_mcp_conformance_report.py <results.jsonl> [--label all|sample]

Writes parameter_characterization/bulk_causal_evidence/mcp_execution_results_<label>_v1.json and
giant_verify_out/bulk_ui_verification/MCP_CONFORMANCE_REPORT_<label>.md. Every row keeps its raw observations; the
report lists every row that needs a human look (FAILED, NOOP_SUSPECT, CONFIRMED with an unchanged named host, bucket-D
observations next to their oracle, and host parameters a scan found that the crosswalk did not know about).
"""
import argparse
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
ORDER = ["MCP_EXEC_HOST_CONFIRMED", "MCP_EXEC_CONFIRMED", "MCP_EXEC_RAW_ONLY", "MCP_EXEC_CONFORMANCE_EXCEPTION",
         "MCP_EXEC_NOOP_SUSPECT", "MCP_EXEC_FAILED"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--label", default="all")
    a = ap.parse_args()
    rows = {}
    for l in open(a.results):
        if l.strip():
            r = json.loads(l)
            rows[r["atlas_id"]] = r     # last line wins, so a --resume or --ids re-run replaces the earlier result
    contract = {r["atlas_id"] for r in json.load(open(os.path.join(ED, "mcp_execution_contract_v1.json")))["rows"]}
    missing = sorted(contract - set(rows)) if a.label == "all" else []
    counts = Counter(r["outcome"] for r in rows.values())

    json.dump({"version": 1, "label": a.label, "source": os.path.basename(a.results), "n_rows": len(rows),
               "missing_from_contract": missing, "outcome_counts": {k: counts.get(k, 0) for k in ORDER},
               "rows": [rows[k] for k in sorted(rows)]},
              open(os.path.join(ED, "mcp_execution_results_%s_v1.json" % a.label), "w"), indent=1, default=repr)

    L = ["# MCP conformance report (%s)" % a.label, "", "Source: `%s`. Rows: %d%s." % (
        os.path.basename(a.results), len(rows), (", missing from the contract: %d" % len(missing)) if missing else ""), "",
        "| outcome | rows |", "|---|---|"] + ["| %s | %d |" % (k, counts.get(k, 0)) for k in ORDER]

    def section(title, pred, fmt):
        hits = [r for k, r in sorted(rows.items()) if pred(r)]
        if hits:
            L.extend(["", "## %s (%d)" % (title, len(hits)), ""] + [fmt(r) for r in hits])

    leaves = lambda r: "; ".join("%s: wrote %r, Serum before %r, after %r" % ("/".join(map(str, l["path"][-2:])), l["written"], l["pre"], l["post"])
                                 for l in r.get("q3_leaves", []))
    section("FAILED -- needs a fix", lambda r: r["outcome"] == "MCP_EXEC_FAILED",
            lambda r: "- `%s`: %s. %s" % (r["atlas_id"], r.get("error", ""), leaves(r)))
    section("NOOP_SUSPECT -- test value likely equals Serum's hidden default; move it and re-run with --ids",
            lambda r: r["outcome"] == "MCP_EXEC_NOOP_SUSPECT", lambda r: "- `%s`: %s" % (r["atlas_id"], leaves(r)))
    section("CONFIRMED but the named host parameter did not change -- crosswalk identity to re-check",
            lambda r: r["outcome"] == "MCP_EXEC_CONFIRMED",
            lambda r: "- `%s`: named %r stayed %r; other hosts that changed: %s" % (
                r["atlas_id"], r["q4"]["named"], r["q4"]["named_post"], r["q4"]["changed_hosts"][:5]))
    section("Bucket D -- observed vs oracle", lambda r: r["outcome"] == "MCP_EXEC_CONFORMANCE_EXCEPTION",
            lambda r: "- `%s`: %s | named %r: %r -> %r | hosts changed: %s | oracle: %s" % (
                r["atlas_id"], leaves(r), r["q4"]["named"], r["q4"]["named_pre"], r["q4"]["named_post"],
                r["q4"]["changed_hosts"][:5], r["q4"].get("oracle", "")))
    section("New host identities found by scan -- feed back into the crosswalk",
            lambda r: r.get("new_host_identity_candidates"),
            lambda r: "- `%s`: %s" % (r["atlas_id"], r["new_host_identity_candidates"]))
    open(os.path.join(BUV, "MCP_CONFORMANCE_REPORT_%s.md" % a.label), "w").write("\n".join(L) + "\n")
    print(json.dumps({k: counts.get(k, 0) for k in ORDER}), "missing:", len(missing))


if __name__ == "__main__":
    main()
