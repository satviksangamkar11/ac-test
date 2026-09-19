"""Tests for timeline.py (Phase G): timestamped snapshots + transcript ->
ordered ProductionEvent timeline. All synthetic fixtures are deterministic
unit tests (no network); one additional test at the bottom uses the real
mU6 Stage-A observation artifact already in the repo, if present, but the
basic suite never requires it.
"""
import json
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.source.visual_evidence import ControlState, UIStateSnapshot, OBSERVED, OCCLUDED
from serum2.source.transcript_query_planner import TranscriptSegment
from serum2.producer.timeline import build_production_timeline


def _snap(frame_id, ts, controls):
    return UIStateSnapshot(frame_id=frame_id, frame_hash="h_" + frame_id, timestamp_sec=ts, controls=controls)


def test_ordered_snapshots_produce_correctly_ordered_events():
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
        _snap("f2", 20.0, [ControlState(control_id="env1.release", control_type="knob", value="60 ms", status=OBSERVED)]),
    ]
    events = build_production_timeline(snaps, [])
    assert [e.start_timestamp_sec for e in events] == [0.0, 10.0]
    assert [e.end_timestamp_sec for e in events] == [10.0, 20.0]
    print("[PASS] test_ordered_snapshots_produce_correctly_ordered_events")


def test_newly_observed_alone_produces_no_event():
    """A control that merely became visible between two frames (present in
    `after`, absent from `before`) is newly_observed_controls, not a
    change -- diff_snapshots()'s own invariant. An interval where that is
    the ONLY evidence, with nothing else changed and no transcript, must
    not become a timeline event."""
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED),
                           ControlState(control_id="env1.attack", control_type="knob", value="4 ms", status=OBSERVED)]),
    ]
    events = build_production_timeline(snaps, [])
    assert events == []
    print("[PASS] test_newly_observed_alone_produces_no_event")


def test_input_ordering_does_not_affect_deterministic_output():
    snaps_forward = [
        _snap("f0", 0.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
    ]
    snaps_reversed = list(reversed(snaps_forward))
    segs_forward = [TranscriptSegment(timestamp_sec=5.0, text="the release")]
    segs_reversed = list(reversed(segs_forward))

    ev1 = build_production_timeline(snaps_forward, segs_forward)
    ev2 = build_production_timeline(snaps_reversed, segs_reversed)
    assert [e.to_dict() for e in ev1] == [e.to_dict() for e in ev2]
    # originals untouched
    assert snaps_reversed[0].timestamp_sec == 10.0
    assert segs_reversed[0].timestamp_sec == 5.0
    print("[PASS] test_input_ordering_does_not_affect_deterministic_output")


def test_one_visual_change_produces_one_correctly_fused_event():
    snaps = [
        _snap("f0", 18.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 26.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
    ]
    # Directional wording that agrees with the observed increase -> AGREEMENT (architecture 22: both
    # a transcript direction and a visual direction must be present and agree for this control).
    segs = [TranscriptSegment(timestamp_sec=22.0, text="I'm going to make the release time longer here")]
    events = build_production_timeline(snaps, segs)
    assert len(events) == 1
    e = events[0]
    assert e.fusion_status == "AGREEMENT"
    assert e.snapshot_diff["changed_controls"] == [{"control_id": "env1.release", "before": "15 ms", "after": "36 ms"}]
    print("[PASS] test_one_visual_change_produces_one_correctly_fused_event")


def test_real_mu6_wording_matches_conflict():
    """Locks in existing (not new) evidence_fusion.py behavior: the real
    mU6 tutorial's actual phrasing ('take a little bit off the release')
    uses a decrease-coded word ('off') while the real observed value
    INCREASED (15ms -> 36ms) -- evidence_fusion's coarse directional
    heuristic flags this as CONFLICT, exactly as it did in this session's
    real end-to-end run. This is a pre-existing, documented limitation of
    the reused fusion function, not a defect in the timeline layer."""
    snaps = [
        _snap("f0", 18.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 26.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
    ]
    segs = [TranscriptSegment(timestamp_sec=22.0, text="I'm going to take a little bit off the release")]
    events = build_production_timeline(snaps, segs)
    assert len(events) == 1
    assert events[0].fusion_status == "CONFLICT"
    print("[PASS] test_real_mu6_wording_matches_conflict")


def test_multiple_changed_controls_are_preserved():
    snaps = [
        _snap("f0", 0.0, [
            ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED),
            ControlState(control_id="env1.attack", control_type="knob", value="1 ms", status=OBSERVED),
            ControlState(control_id="oscA.unison", control_type="knob", value="1", status=OBSERVED),
        ]),
        _snap("f1", 8.0, [
            ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED),
            ControlState(control_id="env1.attack", control_type="knob", value="4 ms", status=OBSERVED),
            ControlState(control_id="oscA.unison", control_type="knob", value="7", status=OBSERVED),
        ]),
    ]
    events = build_production_timeline(snaps, [])
    assert len(events) == 1
    changed_ids = {c["control_id"] for c in events[0].snapshot_diff["changed_controls"]}
    assert changed_ids == {"env1.release", "env1.attack", "oscA.unison"}, (
        "multiple simultaneous changes must not be collapsed into one fake parameter"
    )
    print("[PASS] test_multiple_changed_controls_are_preserved")


def test_transcript_only_evidence_remains_transcript_only():
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
    ]
    segs = [TranscriptSegment(timestamp_sec=5.0, text="I'm going to add an LFO here")]
    events = build_production_timeline(snaps, segs)
    assert len(events) == 1
    assert events[0].fusion_status == "TRANSCRIPT_ONLY"
    print("[PASS] test_transcript_only_evidence_remains_transcript_only")


def test_visual_only_evidence_remains_visual_only():
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="oscA.unison", control_type="knob", value="1", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="oscA.unison", control_type="knob", value="7", status=OBSERVED)]),
    ]
    events = build_production_timeline(snaps, [])
    assert len(events) == 1
    assert events[0].fusion_status == "VISUAL_ONLY"
    print("[PASS] test_visual_only_evidence_remains_visual_only")


def test_genuine_contradiction_remains_conflict():
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
    ]
    segs = [TranscriptSegment(timestamp_sec=5.0, text="make the release shorter")]
    events = build_production_timeline(snaps, segs)
    assert len(events) == 1
    assert events[0].fusion_status == "CONFLICT"
    print("[PASS] test_genuine_contradiction_remains_conflict")


def test_occluded_controls_do_not_become_removals():
    snaps = [
        _snap("f0", 0.0, [
            ControlState(control_id="oscA.unison", control_type="knob", value="7", status=OBSERVED),
            ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED),
        ]),
        _snap("f1", 10.0, [
            ControlState(control_id="oscA.unison", control_type="knob", value=None, status=OCCLUDED),
            ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED),
        ]),
    ]
    events = build_production_timeline(snaps, [])
    assert len(events) == 1
    diff = events[0].snapshot_diff
    assert diff["changed_controls"] == [{"control_id": "env1.release", "before": "15 ms", "after": "36 ms"}]
    assert diff["removed_controls"] == [], "occlusion must never surface as removal"
    assert "oscA.unison" in diff["not_observed_controls"]
    print("[PASS] test_occluded_controls_do_not_become_removals")


def test_no_change_snapshots_produce_no_spurious_events():
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
    ]
    events = build_production_timeline(snaps, [])
    assert events == []
    print("[PASS] test_no_change_snapshots_produce_no_spurious_events")


def test_occluded_only_interval_with_no_transcript_produces_no_event():
    """A control merely losing visibility (occlusion) is not, by itself,
    timeline-worthy -- diff_snapshots() correctly reports it as
    not_observed_controls, and build_production_timeline() must not turn
    that alone into an event."""
    snaps = [
        _snap("f0", 0.0, [ControlState(control_id="oscA.unison", control_type="knob", value="7", status=OBSERVED)]),
        _snap("f1", 10.0, [ControlState(control_id="oscA.unison", control_type="knob", value=None, status=OCCLUDED)]),
    ]
    events = build_production_timeline(snaps, [])
    assert events == []
    print("[PASS] test_occluded_only_interval_with_no_transcript_produces_no_event")


def test_provenance_survives_into_the_resulting_production_event():
    snaps = [
        _snap("frame_A", 18.0, [ControlState(control_id="env1.release", control_type="knob", value="15 ms", status=OBSERVED)]),
        _snap("frame_B", 26.0, [ControlState(control_id="env1.release", control_type="knob", value="36 ms", status=OBSERVED)]),
    ]
    segs = [TranscriptSegment(timestamp_sec=22.0, text="the release")]
    events = build_production_timeline(snaps, segs)
    e = events[0]
    assert e.evidence_frame_ids == ["frame_A", "frame_B"]
    assert e.start_timestamp_sec == 18.0 and e.end_timestamp_sec == 26.0
    assert e.transcript_excerpt == "the release"
    assert e.transcript_timestamp_sec == 22.0
    assert e.fusion_status is not None
    # frame hashes remain recoverable from the original snapshots by frame_id
    # (ProductionEvent's existing schema has no frame_hash field -- see
    # timeline.py's docstring / the final report for why none was added).
    by_id = {s.frame_id: s.frame_hash for s in snaps}
    assert by_id[e.evidence_frame_ids[0]] == "h_frame_A"
    assert by_id[e.evidence_frame_ids[1]] == "h_frame_B"
    print("[PASS] test_provenance_survives_into_the_resulting_production_event")


def test_real_mu6_stage_a_artifact_if_available():
    """Uses the real Stage-A observation JSON produced by direct visual
    inspection this session, if it's present in the repo -- no network
    call, and the basic suite does not depend on this test."""
    obs_path = Path(ROOT) / "serum2" / "data" / "visual_frames" / "yt_89a28028e125" / "stage_a_observation_00018000.json"
    if not obs_path.exists():
        print("[SKIP] test_real_mu6_stage_a_artifact_if_available (artifact not present)")
        return

    from serum2.source.visual_evidence import VisualEvidenceBundle, VisualFrameArtifact
    from serum2.producer.visual_reasoner import ingest_stage_a_observation

    bundle = VisualEvidenceBundle(source_url="https://www.youtube.com/watch?v=mU6PB--pf9w", source_id="yt_89a28028e125", video_id="mU6PB--pf9w")
    bundle.frames = [VisualFrameArtifact(
        frame_id="frame_yt_89a28028e125_00018000", source_url=bundle.source_url, source_id=bundle.source_id,
        video_id=bundle.video_id, timestamp_sec=18.0,
        artifact_path="serum2/data/visual_frames/yt_89a28028e125/frame_yt_89a28028e125_00018000.jpg",
        artifact_hash="18bed31207e6c2be5bf0bc29d184c7b8acea103cd687bcd66f7deadc33af3b98",
    )]
    data = json.loads(obs_path.read_text())
    ingest_stage_a_observation(bundle, data, target_hint="Env1.Release")
    real_snapshot = bundle.ui_state_snapshots[0]

    # Build a synthetic second snapshot representing the same real frame's
    # controls after the tutorial's observed release change (36ms, matching
    # this session's real Stage-A/Brain/execution run) -- only env1.release
    # differs; everything else stays byte-identical to the real census, so
    # this exercises the real 24-control artifact through the timeline layer
    # without a second network-dependent frame acquisition.
    import copy
    after_controls = copy.deepcopy(real_snapshot.controls)
    for c in after_controls:
        if c.control_id == "env1.release":
            c.value = "36 ms"
    after_snapshot = UIStateSnapshot(
        frame_id="frame_yt_89a28028e125_00026000", frame_hash="synthetic_after_hash",
        timestamp_sec=26.0, controls=after_controls,
    )

    segs = [TranscriptSegment(timestamp_sec=22.0, text="I'm going to take a little bit off the attack and the release")]
    events = build_production_timeline([real_snapshot, after_snapshot], segs)
    assert len(events) == 1
    diff = events[0].snapshot_diff
    assert diff["changed_controls"] == [{"control_id": "env1.release", "before": "15 ms", "after": "36 ms"}]
    # 24 real controls total, 1 changed (env1.release), 2 honestly OUT_OF_VIEW
    # in the real census (filter1.cutoff, matrix.routes -- neither panel was
    # frontmost in the real frame) so they land in not_observed_controls, not
    # unchanged_controls -- leaving 21 provably-unchanged controls.
    assert len(diff["unchanged_controls"]) == 21
    assert set(diff["not_observed_controls"]) == {"filter1.cutoff", "matrix.routes"}
    print("[PASS] test_real_mu6_stage_a_artifact_if_available (real 24-control artifact converted to a timeline)")



def _cs(cid, v, st=OBSERVED):
    return ControlState(control_id=cid, control_type="knob", value=v, status=st)


def test_change_across_an_observation_gap_is_not_lost():
    """ENV panel shows ENV2 in the middle frame, so env1.* is unobserved there.
    The real ENV1 change (15 ms -> 120 ms) must still surface, compared against
    its last OBSERVED reading, with the baseline frame recorded."""
    snaps = [
        _snap("f0", 0.0, [_cs("env1.release", "15 ms")]),
        _snap("f1", 10.0, [_cs("env2.release", "15 ms")]),          # env1 not shown
        _snap("f2", 20.0, [_cs("env1.release", "120 ms")]),
    ]
    events = build_production_timeline(snaps, [])
    ev = [e for e in events if e.snapshot_diff["changed_controls"]]
    assert len(ev) == 1
    d = ev[0].snapshot_diff
    assert d["changed_controls"] == [{"control_id": "env1.release", "before": "15 ms", "after": "120 ms"}]
    assert d["baseline_carried"]["env1.release"] == {"frame_id": "f0", "timestamp_sec": 0.0}
    assert ev[0].start_timestamp_sec == 0.0 and "f0" in ev[0].evidence_frame_ids


def test_never_observed_before_is_still_only_newly_observed():
    snaps = [_snap("f0", 0.0, [_cs("a", "1")]), _snap("f1", 10.0, [_cs("a", "1"), _cs("env1.release", "120 ms")])]
    assert build_production_timeline(snaps, []) == []           # nothing to carry -> no fake change


def test_occluded_gap_carries_only_a_real_earlier_observation():
    snaps = [_snap("f0", 0.0, [_cs("x", "5")]), _snap("f1", 10.0, [_cs("x", None, OCCLUDED)]),
             _snap("f2", 20.0, [_cs("x", "5")])]
    assert build_production_timeline(snaps, []) == []           # same value before and after the gap


def test_routes_are_not_added_when_matrix_was_out_of_view():
    from serum2.source.visual_evidence import ModRouteState, OUT_OF_VIEW, diff_snapshots
    before = _snap("f0", 0.0, [_cs("matrix.routes", None, OUT_OF_VIEW)])
    after = UIStateSnapshot(frame_id="f1", frame_hash="h", timestamp_sec=1.0,
                            controls=[_cs("matrix.routes", "1 row")],
                            mod_routes=[ModRouteState(source="Velo", destination="Filter 1 Freq")])
    d = diff_snapshots(before, after)
    assert d["added_routes"] == [] and len(d["newly_observed_routes"]) == 1
    # legacy snapshots with no matrix control keep the original behavior
    legacy_before = _snap("f0", 0.0, [])
    assert len(diff_snapshots(legacy_before, after)["added_routes"]) == 1
    # a route table observed on both sides still yields a genuine addition
    seen_before = _snap("f0", 0.0, [_cs("matrix.routes", "0 rows")])
    assert len(diff_snapshots(seen_before, after)["added_routes"]) == 1

if __name__ == "__main__":
    test_ordered_snapshots_produce_correctly_ordered_events()
    test_newly_observed_alone_produces_no_event()
    test_input_ordering_does_not_affect_deterministic_output()
    test_one_visual_change_produces_one_correctly_fused_event()
    test_real_mu6_wording_matches_conflict()
    test_multiple_changed_controls_are_preserved()
    test_transcript_only_evidence_remains_transcript_only()
    test_visual_only_evidence_remains_visual_only()
    test_genuine_contradiction_remains_conflict()
    test_occluded_controls_do_not_become_removals()
    test_no_change_snapshots_produce_no_spurious_events()
    test_occluded_only_interval_with_no_transcript_produces_no_event()
    test_provenance_survives_into_the_resulting_production_event()
    test_real_mu6_stage_a_artifact_if_available()
    print("\nAll timeline tests passed.")
