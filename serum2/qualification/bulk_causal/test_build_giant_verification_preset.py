"""The corrected bulk DIRECT-UI verification stage: ONE giant preset covering all applicable sections/controls,
plus one small secondary preset for the single genuine structural conflict (oscillator mode). Every one of the 330
MCP candidates gets exactly one terminal status; nothing is silently excluded, and no two candidates may disagree
on the same underlying path (aliases with equal targets are fine, disagreement is a PATH_CONFLICT)."""
import json
from pathlib import Path

import pytest

ED = Path(__file__).resolve().parents[3] / "parameter_characterization" / "bulk_causal_evidence"
HERE = Path(__file__).resolve().parent
PLAN = HERE / "giant_verify_out" / "giant_verification_plan.json"
STATUS_VOCAB = {"APPLIED_TO_GIANT_PRESET", "APPLIED_TO_SECONDARY_PRESET", "NO_USABLE_TARGET_VALUE", "PATH_CONFLICT", "NOT_DERIVED"}

pytestmark = pytest.mark.skipif(not PLAN.exists(), reason="giant verification preset not built")


@pytest.fixture(scope="module")
def plan():
    return json.loads(PLAN.read_text())


def test_all_330_mcp_candidates_accounted_for_exactly_once(plan):
    acct = json.loads((ED / "campaign_accounting_v1.json").read_text())
    ids = [c["atlas_id"] for c in plan["candidates"]]
    assert len(ids) == len(set(ids)) == acct["total_candidates"] == 330
    assert {c["status"] for c in plan["candidates"]} <= STATUS_VOCAB
    for c in plan["candidates"]:
        assert c.get("reason") or c["status"] == "APPLIED_TO_GIANT_PRESET"   # every non-applied status states why


def test_giant_preset_dominates_coverage_over_the_old_15_context_split(plan):
    """The whole point of this correction: one preset should cover far more candidates at once than any single
    context did in the earlier (wrong) 15-preset design, where INIT alone -- the largest context -- covered 205."""
    assert plan["status_counts"]["APPLIED_TO_GIANT_PRESET"] > 205


def test_no_unresolved_path_disagreement(plan):
    assert plan["status_counts"].get("PATH_CONFLICT", 0) == 0 or all(
        c.get("reason") for c in plan["candidates"] if c["status"] == "PATH_CONFLICT")


def test_secondary_preset_is_exactly_the_stated_structural_conflict(plan):
    secondary_ids = {c["atlas_id"] for c in plan["candidates"] if c["status"] == "APPLIED_TO_SECONDARY_PRESET"}
    assert secondary_ids == {"oscA.warp_amount2", "oscB.warp_amount2", "oscC.warp_amount2"}
    for c in plan["candidates"]:
        if c["status"] == "APPLIED_TO_SECONDARY_PRESET":
            assert "OSC_SAMPLE" in c["reason"] and "Warp2" in c["reason"]


def test_enum_and_text_candidates_are_included_not_gated_on_prior_gui_proof(plan):
    """This stage's whole point is to let the GUI prove/disprove a raw value -- unlike the earlier per-context
    draft, enum/text candidates must appear as APPLIED, tagged gui_proven=False, never silently skipped."""
    applied = [c for c in plan["candidates"] if c["status"] == "APPLIED_TO_GIANT_PRESET"]
    enum_applied = [c for c in applied if c.get("declared_domain", {}).get("kind") in ("enum", "enum_str", "text")]
    assert enum_applied, "no enum/text candidates were applied -- regression to the old gating behavior"
    assert all(c["gui_proven"] is False for c in enum_applied)


def test_giant_preset_file_matches_the_plan_on_fresh_readback():
    import sys
    sys.path.insert(0, str(HERE))
    import preset_build  # noqa: F401  (sets up the vendor serum-mcp path as a side effect)
    from serum_mcp.preset.packer import unpack_file
    from bulk_engine import body_get
    plan = json.loads(PLAN.read_text())
    giant = unpack_file(str(HERE / "giant_verify_out" / plan["giant_preset"])).data
    secondary = unpack_file(str(HERE / "giant_verify_out" / plan["secondary_preset"])).data
    for c in plan["candidates"]:
        if c["status"] not in ("APPLIED_TO_GIANT_PRESET", "APPLIED_TO_SECONDARY_PRESET"):
            continue
        body = giant if c["status"] == "APPLIED_TO_GIANT_PRESET" else secondary
        got = body_get(body, c["raw_path"])
        tv = c["target_value"]
        assert got == tv or (isinstance(got, float) and isinstance(tv, float) and abs(got - tv) < 1e-9), (c["atlas_id"], tv, got)
