"""Composite verification presets: every context's applied candidates land at their own path with no collision,
and every manifest candidate is accounted for as either applied or explicitly excluded (never silently dropped)."""
import json
from pathlib import Path

import pytest

ED = Path(__file__).resolve().parents[3] / "parameter_characterization" / "bulk_causal_evidence"
HERE = Path(__file__).resolve().parent
PLAN = HERE / "verify_out" / "verification_plan.json"
MANIFEST = HERE / "manifest_campaign_v1.json"

pytestmark = pytest.mark.skipif(not PLAN.exists(), reason="verification presets not built")


@pytest.fixture(scope="module")
def plan():
    return json.loads(PLAN.read_text())


def test_every_manifest_candidate_is_applied_or_explicitly_excluded(plan):
    manifest = json.loads(MANIFEST.read_text())
    all_ids = {p["atlas_id"] for p in manifest["parameters"]}
    applied_ids, excluded_ids = set(), set()
    for c in plan["contexts"].values():
        applied_ids |= {a["atlas_id"] for a in c["applied"]}
        excluded_ids |= {e["atlas_id"] for e in c["excluded"]}
        for e in c["excluded"]:
            assert e["reason"]           # every exclusion states why -- never a silent drop
    assert applied_ids | excluded_ids == all_ids
    assert not (applied_ids & excluded_ids)
    assert plan["summary"]["total_applied"] == len(applied_ids)
    assert plan["summary"]["total_excluded"] == len(excluded_ids)


def test_no_two_candidates_in_one_context_disagree_on_the_same_path(plan):
    """Two atlas_ids CAN share a raw path (duplicate/aliased Atlas identities for one physical control) as long as
    they agree on the target value -- that's still one verifiable reading. Disagreement must never be silently
    resolved; the builder excludes the later one with a stated reason instead."""
    for name, c in plan["contexts"].items():
        by_path = {}
        for a in c["applied"]:
            pk = tuple(a["raw_path"])
            if pk in by_path:
                prev = by_path[pk]
                assert prev == a["target_value"] or (isinstance(prev, float) and isinstance(a["target_value"], float) and abs(prev - a["target_value"]) < 1e-9), \
                    "context %s: unresolved disagreement at %s" % (name, pk)
            by_path[pk] = a["target_value"]


def test_composite_presets_exist_on_disk(plan):
    for name, c in plan["contexts"].items():
        assert (HERE / "verify_out" / c["preset"]).exists(), c["preset"]


def test_no_target_value_was_invented_for_enum_or_text_candidates(plan):
    """pick_target() must refuse enum/text candidates (no GUI-proven labels at this evidence stage) rather than
    writing a raw number that would display as nonsense in the UI."""
    for c in plan["contexts"].values():
        for a in c["applied"]:
            assert a["declared_domain"]["kind"] not in ("enum", "enum_str", "text")
