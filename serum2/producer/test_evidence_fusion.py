"""Tests for evidence_fusion.py -- Phase B (transcript + visual fusion).

Covers the exact real cases surfaced this session: the mU6 release/attack/
filter event (transcript wording vs observed value direction genuinely
conflicts -- must stay CONFLICT, never silently resolved), the k6 LFO route
event (transcript topically matches a ROUTE change, not a control value --
AGREEMENT), a topically-disjoint case, and a transcript-only case.
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_wording_value_conflict_preserved_not_resolved():
    """'take a bit off' (decrease-coded) + observed values increasing must
    stay CONFLICT -- the frozen plan's own worked example."""
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, CONFLICT
    diff = {
        "changed_controls": [
            {"control_id": "env1.release", "before": "15 ms", "after": "36 ms"},
            {"control_id": "env1.attack", "before": "1.0 ms", "after": "4.0 ms"},
            {"control_id": "filter1.type", "before": "Lowpass", "after": "Band 24"},
        ],
        "added_routes": [], "removed_routes": [],
    }
    event = fuse_transcript_and_visual(
        "evt_1", 18.0, 40.0, ["f1", "f2"], diff,
        transcript_excerpt="take a little bit off the attack and the release",
        transcript_timestamp_sec=22.0,
    )
    assert event.fusion_status == CONFLICT
    assert len(event.observed) == 3, "all three real changes preserved, not just the transcript-named ones"
    assert "filter1.type" in str(event.unknown), "the unmentioned filter change must still be recorded"
    print("[PASS] test_wording_value_conflict_preserved_not_resolved")


def test_route_change_matches_transcript_agreement():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, AGREEMENT
    diff = {"changed_controls": [], "added_routes": [{"source": "lfo0", "destination": "filter0.cutoff"}], "removed_routes": []}
    event = fuse_transcript_and_visual(
        "evt_2", 409, 423, ["f3"], diff,
        transcript_excerpt="drag the LFO one onto the cutoff to introduce more movement",
        transcript_timestamp_sec=413,
    )
    assert event.fusion_status == AGREEMENT
    assert "lfo0" in event.observed[0]
    print("[PASS] test_route_change_matches_transcript_agreement")


def test_topically_disjoint_evidence_is_conflict_not_guessed():
    """Real change exists, real transcript exists, but they're about
    different things -- must not silently pick one."""
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, CONFLICT
    diff = {"changed_controls": [{"control_id": "env1.release", "before": "15", "after": "220"}], "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual(
        "evt_3", 0, 5, ["f4"], diff,
        transcript_excerpt="the filter sounds different now", transcript_timestamp_sec=2,
    )
    assert event.fusion_status == CONFLICT
    print("[PASS] test_topically_disjoint_evidence_is_conflict_not_guessed")


def test_transcript_only_no_ui_change():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, TRANSCRIPT_ONLY
    diff = {"changed_controls": [], "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual(
        "evt_4", 0, 5, ["f5"], diff,
        transcript_excerpt="now lets move to the effect section", transcript_timestamp_sec=2,
    )
    assert event.fusion_status == TRANSCRIPT_ONLY
    assert event.unknown  # records that the described action had no observed UI counterpart
    print("[PASS] test_transcript_only_no_ui_change")


def test_visual_only_no_transcript():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, VISUAL_ONLY
    diff = {"changed_controls": [{"control_id": "env1.release", "before": "15", "after": "220"}], "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual("evt_5", 0, 5, ["f6"], diff, transcript_excerpt=None)
    assert event.fusion_status == VISUAL_ONLY
    print("[PASS] test_visual_only_no_transcript")


def test_no_evidence_at_all_is_unknown():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, UNKNOWN
    diff = {"changed_controls": [], "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual("evt_6", 0, 5, [], diff, transcript_excerpt=None)
    assert event.fusion_status == UNKNOWN
    print("[PASS] test_no_evidence_at_all_is_unknown")


def test_snapshot_diff_is_deterministic():
    """diff_snapshots is pure Python, no model call -- proven by calling it
    twice on identical input and checking bit-identical output."""
    from serum2.source.visual_evidence import UIStateSnapshot, ControlState, diff_snapshots
    before = UIStateSnapshot(
        frame_id="fA", frame_hash="hA", timestamp_sec=1.0,
        controls=[ControlState(control_id="env1.release", control_type="knob", value="15 ms", frame_id="fA")],
    )
    after = UIStateSnapshot(
        frame_id="fB", frame_hash="hB", timestamp_sec=2.0,
        controls=[
            ControlState(control_id="env1.release", control_type="knob", value="36 ms", frame_id="fB"),
            ControlState(control_id="filter1.type", control_type="dropdown", value="Band 24", frame_id="fB"),
        ],
    )
    d1 = diff_snapshots(before, after)
    d2 = diff_snapshots(before, after)
    assert d1 == d2
    assert d1["changed_controls"] == [{"control_id": "env1.release", "before": "15 ms", "after": "36 ms"}]
    assert d1["newly_observed_controls"] == ["filter1.type"]
    print("[PASS] test_snapshot_diff_is_deterministic")


if __name__ == "__main__":
    test_wording_value_conflict_preserved_not_resolved()
    test_route_change_matches_transcript_agreement()
    test_topically_disjoint_evidence_is_conflict_not_guessed()
    test_transcript_only_no_ui_change()
    test_visual_only_no_transcript()
    test_no_evidence_at_all_is_unknown()
    test_snapshot_diff_is_deterministic()
    print("\nAll evidence fusion tests passed.")
