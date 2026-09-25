"""Closure ledger v3: closure_ledger_v2.json unchanged, plus an ADDITIVE direct_ui_evidence tier from the screen scan
(parameter_characterization/bulk_causal_evidence/direct_ui_evidence_v2.json).

    python -m serum2.qualification.bulk_causal.closure_ledger_v3 [out.json]   (default: closure_ledger_v3.json in ED)

Built ON TOP OF the committed closure_ledger_v2.json, not by re-running closure_ledger.build(): build()'s promotion
dry-run resolves the installed Serum epoch, which exists only on the Serum machine, so a rebuild elsewhere would
silently turn CLOSED into PROMOTION_BLOCKED. Layering keeps every v2 field identical on any machine.

Separation rules (enforced here and in test_closure_ledger_v3.py):
  * direct_ui_evidence is read ONLY from direct_ui_evidence_v2.json (screen-level observation of Serum's own window).
  * host_text_evidence is carried verbatim from closure_ledger_v2.json (VST3 host text, host_text_fallback).
  * Neither tier reads the other, and neither changes `status`, `ui_semantics` or promotion fields, which are carried
    verbatim from v2. Promotion from DIRECT_UI evidence is a later, separately reviewed step (authority, admission,
    binding and state-machine code are untouched).

direct_ui_evidence.status, per candidate:
  UI_CONFIRMED                  MATCH / NORMALIZED_MATCH on screen
  UI_PLAUSIBLE                  PLAUSIBLE_MATCH (e.g. integer-quantized display, not hover-confirmed)
  UI_MISMATCH                   screen value differs from the written target
  UI_CONTEXT_CONFLICT           target disabled by another co-applied target (lfo mode=Envelope with shape=S&H)
  UI_VOCABULARY_MISMATCH        Serum's menu does not contain the schema's vocabulary
  UI_VOCABULARY_DISCOVERED      display vocabulary enumerated for a control that had none (raw values may be unknown)
  UI_NOT_OBSERVABLE_IN_CONTEXT  control not shown in this preset's structural context (not a failure)
  UI_CURVE_UNVERIFIED           a value is shown but its relation to the raw value is not established
  UI_OBSERVED_NO_TARGET         shown on screen but the plan had no target to compare
  UI_NOT_SCANNED                no DIRECT_UI observation yet
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from closure_ledger import ED  # noqa: E402

DIRECT_UI_FILE = "direct_ui_evidence_v2.json"
V2_FILE = "closure_ledger_v2.json"
# observations recorded under a non-atlas name before atlas ids were used consistently
ALIASES = {"noise.type": "oscNoise.noise_type"}
VERDICT_TO_STATUS = {"MATCH": "UI_CONFIRMED", "NORMALIZED_MATCH": "UI_CONFIRMED", "PLAUSIBLE_MATCH": "UI_PLAUSIBLE",
                     "MISMATCH": "UI_MISMATCH", "CONTEXT_CONFLICT": "UI_CONTEXT_CONFLICT",
                     "VOCABULARY_MISMATCH": "UI_VOCABULARY_MISMATCH", "VOCABULARY_DISCOVERED": "UI_VOCABULARY_DISCOVERED",
                     "NOT_OBSERVABLE_IN_CONTEXT": "UI_NOT_OBSERVABLE_IN_CONTEXT", "CURVE_UNVERIFIED": "UI_CURVE_UNVERIFIED",
                     "OBSERVED_NOT_IN_PLAN": "UI_OBSERVED_NO_TARGET"}
CARRY = ("expected_target", "screen_displayed", "verdict", "method", "note", "conflicts_with", "conflicting_target",
         "isolation_evidence", "display_vocabulary", "serum_vocabulary", "schema_vocabulary", "context", "source")


def direct_ui_evidence(obs):
    if obs is None:
        return {"status": "UI_NOT_SCANNED", "is_direct_ui_verified": False}
    out = {"status": VERDICT_TO_STATUS[obs["verdict"]], "is_direct_ui_verified": obs["verdict"] in ("MATCH", "NORMALIZED_MATCH"),
           "observation_method": "direct_ui_screen_scan"}
    out.update({k: obs[k] for k in CARRY if k in obs})
    if obs.get("superseded"):
        out["superseded_readings"] = len(obs["superseded"])
    return out


def main(out_path):
    v2 = json.loads((ED / V2_FILE).read_text())
    ui = json.loads((ED / DIRECT_UI_FILE).read_text())
    ui_by = {}
    for o in ui["observations"]:
        a = ALIASES.get(o["atlas_id"], o["atlas_id"])
        assert a not in ui_by, "duplicate DIRECT_UI observation for %s" % a
        ui_by[a] = o

    led = copy.deepcopy(v2["candidates"])
    ids = {e["atlas_id"] for e in led}
    counts = {}
    for e in led:
        assert "direct_ui_evidence" not in e
        e["direct_ui_evidence"] = direct_ui_evidence(ui_by.get(e["atlas_id"]))
        counts[e["direct_ui_evidence"]["status"]] = counts.get(e["direct_ui_evidence"]["status"], 0) + 1
    assert sum(counts.values()) == v2["total_candidates"] == len(led) == len(ids)
    unmatched = sorted(a for a in ui_by if a not in ids)   # page-level observations (e.g. MATRIX_PAGE), not candidates

    json.dump({"total_candidates": v2["total_candidates"], "status_counts": v2["status_counts"],
               "host_text_evidence_counts": v2["host_text_evidence_counts"], "direct_ui_evidence_counts": counts,
               "direct_ui_non_candidate_observations": unmatched, "authorizes_nothing": True,
               "status_changed_by_direct_ui": False, "direct_ui_verification_performed": True,
               "evidence": dict(v2["evidence"], base_ledger=V2_FILE, direct_ui=DIRECT_UI_FILE, direct_ui_aliases=ALIASES),
               "candidates": led}, open(out_path, "w"), indent=1)
    print("status_counts (from v2):", json.dumps(v2["status_counts"]))
    print("direct_ui_evidence_counts:", json.dumps(counts))
    if unmatched:
        print("non-candidate DIRECT_UI observations:", unmatched)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ED / "closure_ledger_v3.json"))
