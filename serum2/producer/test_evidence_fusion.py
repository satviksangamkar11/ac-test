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


def test_topically_disjoint_evidence_is_visual_only_not_conflict():
    """Architecture 22: a real change and a real transcript that are about different things are NOT a
    contradiction. The UI change has no transcript coverage -> VISUAL_ONLY; nothing is guessed."""
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual, VISUAL_ONLY
    diff = {"changed_controls": [{"control_id": "env1.release", "before": "15", "after": "220"}], "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual(
        "evt_3", 0, 5, ["f4"], diff,
        transcript_excerpt="the filter sounds different now", transcript_timestamp_sec=2,
    )
    assert event.fusion_status == VISUAL_ONLY
    assert event.snapshot_diff["control_fusion"]["env1.release"]["mentioned"] is False
    print("[PASS] test_topically_disjoint_evidence_is_visual_only_not_conflict")


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


# ---- architecture section 22: direction is evaluated PER CONTROL ---------------------------------
def _fuse(changes, text):
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual
    diff = {"changed_controls": [{"control_id": c, "before": b, "after": a} for c, b, a in changes],
            "added_routes": [], "removed_routes": []}
    return fuse_transcript_and_visual("evt", 0, 10, ["f0", "f1"], diff, transcript_excerpt=text, transcript_timestamp_sec=1)


def test_controls_moving_in_different_directions_do_not_conflict_with_each_other():
    """One window says 'down' for one control and 'more' for another; each matches its own change."""
    e = _fuse([("env1.sustain", "0.0 dB", "-13.8 dB"), ("env1.release", "15 ms", "120 ms")],
              "the sustain a bit down and then a bit more release")
    cf = e.snapshot_diff["control_fusion"]
    assert cf["env1.sustain"]["classification"] == "AGREEMENT" and cf["env1.sustain"]["transcript"] == "decrease"
    assert cf["env1.release"]["classification"] == "AGREEMENT" and cf["env1.release"]["transcript"] == "increase"
    assert e.fusion_status == "AGREEMENT"


def test_unrelated_direction_words_in_the_window_are_not_a_contradiction():
    """'down' is about something else (far from any changed control's mention); the release change is untouched."""
    e = _fuse([("env1.release", "15 ms", "120 ms")],
              "we are going down the list of settings now and then look at the release later on")
    assert e.snapshot_diff["control_fusion"]["env1.release"]["transcript"] is None
    assert e.fusion_status == "UNKNOWN"            # covered, but direction not evaluable -> never CONFLICT


def test_genuine_contradiction_for_the_specific_control_is_conflict():
    e = _fuse([("env1.release", "15 ms", "120 ms"), ("env1.attack", "1.0 ms", "1.5 ms")],
              "a bit shorter release and a bit more attack")
    cf = e.snapshot_diff["control_fusion"]
    assert cf["env1.release"]["classification"] == "CONFLICT"          # said shorter, value went up
    assert cf["env1.attack"]["classification"] == "AGREEMENT"          # said more, value went up
    assert e.fusion_status == "CONFLICT"


def test_neutral_language_is_unknown_not_agreement_or_conflict():
    e = _fuse([("env1.release", "15 ms", "120 ms")], "let's adjust the release time here")
    assert e.snapshot_diff["control_fusion"]["env1.release"]["mentioned"] is True
    assert e.fusion_status == "UNKNOWN"


def test_direction_word_between_two_controls_is_ambiguous_and_assigned_to_neither():
    e = _fuse([("env1.attack", "1.0 ms", "1.5 ms"), ("env1.release", "15 ms", "120 ms")], "attack more release")
    assert e.snapshot_diff["control_fusion"]["env1.attack"]["transcript"] is None
    assert e.snapshot_diff["control_fusion"]["env1.release"]["transcript"] is None


def test_units_are_compared_in_a_common_base():
    e = _fuse([("env1.decay", "1.00 s", "627 ms")], "the decay a little bit smaller")
    d = e.snapshot_diff["control_fusion"]["env1.decay"]
    assert d["visual"] == "decrease" and d["transcript"] == "decrease" and e.fusion_status == "AGREEMENT"


def test_toggle_direction_and_uncomparable_values():
    from serum2.producer.evidence_fusion import _visual_direction
    assert _visual_direction("off", "on") == "increase" and _visual_direction("on", "off") == "decrease"
    assert _visual_direction("Band 24", "MG Low 18") is None and _visual_direction("1", "1 ms") is None


def test_visual_only_and_transcript_only_and_unknown_are_preserved():
    assert _fuse([("env1.release", "15 ms", "120 ms")], None).fusion_status == "VISUAL_ONLY"
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual
    e = fuse_transcript_and_visual("e", 0, 1, [], {"changed_controls": [], "added_routes": [], "removed_routes": []},
                                   transcript_excerpt="more release", transcript_timestamp_sec=0)
    assert e.fusion_status == "TRANSCRIPT_ONLY"
    assert fuse_transcript_and_visual("e", 0, 1, [], {"changed_controls": []}).fusion_status == "UNKNOWN"


def test_no_tutorial_specific_language_in_fusion_source():
    from pathlib import Path
    src = (Path(__file__).parent / "evidence_fusion.py").read_text(encoding="utf-8").lower()
    for forbidden in ("td22", "mu6", "acid", "gotas", "j106", "amelie"):
        assert forbidden not in src, forbidden


def test_direction_word_does_not_cross_a_clause_boundary():
    e = _fuse([("env1.release", "15 ms", "120 ms"), ("env1.decay", "1.00 s", "627 ms")],
              "the release a little bit longer and the decay a little bit smaller")
    cf = e.snapshot_diff["control_fusion"]
    assert cf["env1.release"]["transcript"] == "increase" and cf["env1.decay"]["transcript"] == "decrease"
    assert e.fusion_status == "AGREEMENT"


def test_a_neighbouring_control_competes_for_the_direction_word():
    """'down' belongs to the closer control (blend), not to the changed unison count."""
    e = _fuse([("oscB.unison", 1, 3)], "make it three voices blend a bit down")
    d = e.snapshot_diff["control_fusion"]["oscB.unison"]
    assert d["mentioned"] is True and d["transcript"] is None and e.fusion_status == "UNKNOWN"


def test_named_slot_excludes_a_different_slots_control():
    """The excerpt talks about envelope one; a change to env2.decay is not covered by it."""
    e = _fuse([("env2.decay", "1.00 s", "205 ms")], "envelope one the decay a little bit smaller")
    d = e.snapshot_diff["control_fusion"]["env2.decay"]
    assert d["mentioned"] is False and e.fusion_status == "VISUAL_ONLY"
    e1 = _fuse([("env1.decay", "1.00 s", "627 ms")], "envelope one the decay a little bit smaller")
    assert e1.snapshot_diff["control_fusion"]["env1.decay"]["classification"] == "AGREEMENT"


def test_bracketed_captions_are_not_speech():
    from serum2.producer.evidence_fusion import _tokens
    assert _tokens("the decay [music] a bit smaller") == ["the", "decay", "a", "bit", "smaller"]


def test_every_conflict_has_a_per_control_contradiction():
    """Audit rule: an event may be CONFLICT only if some control shows both directions, opposite."""
    e = _fuse([("env1.release", "15 ms", "120 ms"), ("env1.attack", "1.0 ms", "1.5 ms")], "a bit shorter release and a bit more attack")
    assert e.fusion_status == "CONFLICT"
    bad = [c for c, d in e.snapshot_diff["control_fusion"].items() if d["classification"] == "CONFLICT"]
    assert bad and all(e.snapshot_diff["control_fusion"][c]["visual"] != e.snapshot_diff["control_fusion"][c]["transcript"]
                       and None not in (e.snapshot_diff["control_fusion"][c]["visual"], e.snapshot_diff["control_fusion"][c]["transcript"])
                       for c in bad)
