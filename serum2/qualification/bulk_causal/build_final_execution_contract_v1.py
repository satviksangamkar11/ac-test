"""Generate final_execution_contract_v1.json — the 330-row machine-readable table the producer uses at runtime.

Each row covers one PRODUCT atlas_id and carries:
  atlas_id, allowed_operation, raw_body_path, valid_domain, context_requirements,
  execution_outcome, verification_method, known_exception, exception_detail, epoch_sha256

Sources (read-only, never modified):
  parameter_characterization/serum_mcp_mutable_surface.json         (330 candidates)
  parameter_characterization/binding_evidence_mcp_exec_v1/*.json    (promoted evidence per control)
  serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_all_v2_results.jsonl

Classification is derived from actual v2 outcomes — the executable count is never hard-coded:
  HOST_CONFIRMED / CONFIRMED / RAW_ONLY  -> executable
  CONFORMANCE_EXCEPTION                  -> documented exception
  NOOP_SUSPECT / FAILED                  -> open (must not be silently folded into exceptions)

Usage:
  python build_final_execution_contract_v1.py [--results PATH]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
EV_DIR = os.path.join(REPO, "parameter_characterization", "binding_evidence_mcp_exec_v1")
SURFACE_PATH = os.path.join(REPO, "parameter_characterization", "serum_mcp_mutable_surface.json")
DEFAULT_RESULTS = os.path.join(
    HERE, "giant_verify_out", "bulk_ui_verification", "mcp_exec_all_v2_results.jsonl"
)
OUT_PATH = os.path.join(ED, "final_execution_contract_v1.json")

PROMOTABLE = {"MCP_EXEC_HOST_CONFIRMED", "MCP_EXEC_CONFIRMED", "MCP_EXEC_RAW_ONLY"}
EXCEPTION_OUTCOME = "MCP_EXEC_CONFORMANCE_EXCEPTION"


def _raw_body_path(evidence):
    """Extract the primary body path from the evidence's body_diff_filtered list."""
    diffs = evidence.get("body_diff_filtered") or []
    if not diffs:
        return None
    return diffs[0].get("path")


def _valid_domain(evidence, surface_entry):
    """Build the valid_domain dict from evidence + surface manifest."""
    control_type = surface_entry.get("control_type")
    if control_type in ("continuous", "knob", "stepper", "draggable_value", "signed", "log"):
        lo = surface_entry.get("min")
        hi = surface_entry.get("max")
        if lo is not None or hi is not None:
            return {"kind": "continuous", "min": lo, "max": hi}
        return {"kind": "continuous"}
    if control_type == "enum" or surface_entry.get("enum_values"):
        return {"kind": "enum", "values": surface_entry.get("enum_values") or []}
    if control_type == "boolean":
        return {"kind": "boolean"}
    return {"kind": control_type or "unknown"}


def _exception_detail(sweep_row):
    """Extract a brief exception detail string from the harness result row."""
    parts = []
    if sweep_row.get("q5_reference"):
        parts.append("reference: %s" % sweep_row["q5_reference"])
    leaves = sweep_row.get("q3_leaves") or []
    if leaves:
        persisted = [l for l in leaves if l.get("persisted")]
        not_persisted = [l for l in leaves if not l.get("persisted")]
        if not_persisted:
            paths = [".".join(str(p) for p in l.get("path", [])) for l in not_persisted]
            parts.append("leaves_not_persisted: [%s]" % ", ".join(paths))
        if persisted and not_persisted:
            parts.append("partial_persistence")
    q4 = sweep_row.get("q4")
    if q4 is not None and not q4:
        parts.append("host_param_unchanged")
    return "; ".join(parts) if parts else "conformance_exception"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=DEFAULT_RESULTS,
                    help="path to mcp_exec_all_v2_results.jsonl (default: %(default)s)")
    a = ap.parse_args()

    surface = json.load(open(SURFACE_PATH))
    candidates = surface["mcp_mutable_candidates"]  # dict: atlas_id -> entry
    assert len(candidates) == 330, "expected 330 candidates, got %d" % len(candidates)

    # Load sweep results (keyed by atlas_id)
    sweep_rows = {}
    for line in open(a.results):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        sweep_rows[r["atlas_id"]] = r
    assert len(sweep_rows) == 330, "expected 330 sweep rows, got %d" % len(sweep_rows)

    # Load evidence files (keyed by atlas_id)
    evidence = {}
    for fname in os.listdir(EV_DIR):
        if not fname.endswith(".json"):
            continue
        atlas_id = fname[:-5]
        evidence[atlas_id] = json.load(open(os.path.join(EV_DIR, fname)))

    controls = []
    for atlas_id in sorted(candidates.keys()):
        surf = candidates[atlas_id]
        sweep = sweep_rows.get(atlas_id)
        ev = evidence.get(atlas_id)
        outcome = sweep["outcome"] if sweep else "MISSING"

        if outcome in PROMOTABLE:
            verification_method = outcome
            known_exception = False
            exception_detail = None
        elif outcome == EXCEPTION_OUTCOME:
            verification_method = outcome
            known_exception = True
            exception_detail = _exception_detail(sweep) if sweep else "conformance_exception"
        else:
            # NOOP_SUSPECT, FAILED, or MISSING — explicitly open
            verification_method = outcome
            known_exception = False
            exception_detail = None

        epoch_sha = sweep["serum_sha256"] if sweep and sweep.get("serum_sha256") else None

        row = {
            "atlas_id": atlas_id,
            "allowed_operation": ev["source_outcome"] if ev else None,
            "raw_body_path": _raw_body_path(ev) if ev else None,
            "valid_domain": _valid_domain(ev, surf) if ev else None,
            "context_requirements": surf.get("conditional_context") or None,
            "execution_outcome": outcome,
            "verification_method": verification_method,
            "known_exception": known_exception,
            "exception_detail": exception_detail,
            "epoch_sha256": epoch_sha,
        }
        # Derive allowed_operation from Atlas control_type — same mapping evidence_promotion.py uses.
        if ev:
            ct = surf.get("control_type")
            _CT_TO_OP = {
                "continuous": "mutate_numeric_value",
                "knob": "mutate_numeric_value",
                "stepper": "mutate_numeric_value",
                "draggable_value": "mutate_numeric_value",
                "signed": "mutate_numeric_value",
                "log": "mutate_numeric_value",
                "enum": "mutate_enum_value",
                "dropdown": "mutate_enum_value",
                "nested_dropdown": "mutate_enum_value",
                "boolean": "mutate_boolean_value",
                "toggle": "mutate_boolean_value",
                "checkbox": "mutate_boolean_value",
            }
            if ct in _CT_TO_OP:
                row["allowed_operation"] = _CT_TO_OP[ct]
        controls.append(row)

    # Verification
    assert len(controls) == 330, "expected 330 rows, got %d" % len(controls)
    ids = [c["atlas_id"] for c in controls]
    assert len(set(ids)) == 330, "duplicate atlas_id detected"

    executable = [c for c in controls if c["execution_outcome"] in PROMOTABLE]
    exceptions = [c for c in controls if c["execution_outcome"] == EXCEPTION_OUTCOME]
    open_items = [c for c in controls if c["execution_outcome"] not in PROMOTABLE and
                  c["execution_outcome"] != EXCEPTION_OUTCOME]

    summary = {
        "n_total": len(controls),
        "n_executable": len(executable),
        "n_exceptions": len(exceptions),
        "n_open": len(open_items),
        "open_atlas_ids": [c["atlas_id"] for c in open_items],
        "epoch_sha256": "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3",
        "source_results": os.path.basename(a.results),
        "source_evidence_dir": "parameter_characterization/binding_evidence_mcp_exec_v1",
    }

    contract = {"summary": summary, "controls": controls}
    json.dump(contract, open(OUT_PATH, "w"), indent=1)

    print(json.dumps({
        "n_total": summary["n_total"],
        "n_executable": summary["n_executable"],
        "n_exceptions": summary["n_exceptions"],
        "n_open": summary["n_open"],
        "open_atlas_ids": summary["open_atlas_ids"],
    }, indent=1))
    print("written:", OUT_PATH)


if __name__ == "__main__":
    main()
