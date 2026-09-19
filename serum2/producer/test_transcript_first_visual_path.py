"""Tests for the transcript-first visual evidence pipeline (VLP-1 correction).

Covers only the deterministic parts (no network, no Anthropic API call):
  - transcript_query_planner: transcript -> targeted before/after timestamps
  - diff_observed_states / infer_from_diffs: structured readings -> diff ->
    interpretation, with no model call and no value drift

Does NOT re-run any previously-verified candidate episode.
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_planner_finds_release_mention_and_brackets_it():
    from serum2.source.transcript_query_planner import (
        plan_visual_queries, TranscriptSegment,
    )

    segments = [
        TranscriptSegment(timestamp_sec=10.0, text="Let's start with the oscillator."),
        TranscriptSegment(
            timestamp_sec=34.0,
            text="I like to make the release time like this because it's more smooth.",
        ),
        TranscriptSegment(timestamp_sec=60.0, text="Now let's move to the filter."),
    ]
    plan = plan_visual_queries(segments, before_offset_sec=4.0, after_offset_sec=4.0,
                                extra_after_offset_sec=10.0)

    assert plan.concept_hint == "note-release"
    assert plan.target_name_hint == "Env1.Release"
    assert plan.trigger_timestamp_sec == 34.0
    assert len(plan.targets) == 3
    roles = [t.role for t in plan.targets]
    assert roles == ["before", "after", "after"]
    ts = plan.timestamps()
    assert ts[0] == 30.0   # before
    assert ts[1] == 38.0   # after
    assert ts[2] == 44.0   # settled-value after
    print("[PASS] test_planner_finds_release_mention_and_brackets_it")


def test_planner_blocks_honestly_when_no_known_target_mentioned():
    """No known parameter mentioned -> empty plan, not a guessed target."""
    from serum2.source.transcript_query_planner import (
        plan_visual_queries, TranscriptSegment,
    )

    segments = [
        TranscriptSegment(timestamp_sec=0.0, text="Welcome back to the channel."),
        TranscriptSegment(timestamp_sec=5.0, text="Today we're making a dubstep growl."),
    ]
    plan = plan_visual_queries(segments)
    assert plan.targets == []
    assert plan.concept_hint is None
    print("[PASS] test_planner_blocks_honestly_when_no_known_target_mentioned")


def test_diff_pairs_earliest_and_latest_reading_per_target():
    from serum2.source.visual_evidence import VisualEvidenceBundle, ObservedCanonicalState
    from serum2.producer.visual_reasoner import diff_observed_states

    bundle = VisualEvidenceBundle(source_url="u", source_id="s", video_id="v")
    bundle.observed_canonical_states = [
        ObservedCanonicalState(target="Env1.Release", value="15 ms",
                                frame_id="f34", timestamp_sec=34.0, frame_hash="aaa"),
        ObservedCanonicalState(target="Env1.Release", value="220 ms",
                                frame_id="f38", timestamp_sec=38.0, frame_hash="bbb"),
        ObservedCanonicalState(target="Env1.Release", value="220 ms",
                                frame_id="f44", timestamp_sec=44.0, frame_hash="ccc"),
    ]
    diffs = diff_observed_states(bundle)
    assert len(diffs) == 1
    d = diffs[0]
    assert d.target == "Env1.Release"
    assert d.before.value == "15 ms"
    assert d.before.timestamp_sec == 34.0
    assert d.after.value == "220 ms"
    assert d.after.timestamp_sec == 44.0   # latest, not the middle reading
    assert d.changed is True
    print("[PASS] test_diff_pairs_earliest_and_latest_reading_per_target")


def test_infer_from_diffs_derives_direction_without_a_model_call():
    from serum2.source.visual_evidence import VisualEvidenceBundle, ObservedCanonicalState
    from serum2.producer.visual_reasoner import diff_observed_states, infer_from_diffs

    bundle = VisualEvidenceBundle(source_url="u", source_id="s", video_id="v")
    bundle.observed_canonical_states = [
        ObservedCanonicalState(target="Env1.Release", value="15 ms",
                                frame_id="f34", timestamp_sec=34.0, frame_hash="aaa",
                                confidence=0.9),
        ObservedCanonicalState(target="Env1.Release", value="220 ms",
                                frame_id="f38", timestamp_sec=38.0, frame_hash="bbb",
                                confidence=0.85),
    ]
    diffs = diff_observed_states(bundle)
    infer_from_diffs(bundle, diffs)

    assert len(bundle.interpretations) == 1
    interp = bundle.interpretations[0]
    assert interp.production_concept == "note-release"
    assert interp.semantic_direction == "longer"
    # The exact value must trace back to the diff's after.value, never a
    # fresh guess — this is the whole point of deterministic inference.
    assert "220 ms" in interp.production_action
    assert "f34" in interp.supporting_frame_ids and "f38" in interp.supporting_frame_ids
    assert interp.confidence == 0.85  # min(before, after)
    print("[PASS] test_infer_from_diffs_derives_direction_without_a_model_call")


def test_infer_from_diffs_skips_unchanged_diff():
    from serum2.source.visual_evidence import VisualEvidenceBundle, ObservedCanonicalState
    from serum2.producer.visual_reasoner import diff_observed_states, infer_from_diffs

    bundle = VisualEvidenceBundle(source_url="u", source_id="s", video_id="v")
    bundle.observed_canonical_states = [
        ObservedCanonicalState(target="Env1.Release", value="220 ms",
                                frame_id="f38", timestamp_sec=38.0, frame_hash="bbb"),
        ObservedCanonicalState(target="Env1.Release", value="220 ms",
                                frame_id="f44", timestamp_sec=44.0, frame_hash="ccc"),
    ]
    diffs = diff_observed_states(bundle)
    assert diffs[0].changed is False
    infer_from_diffs(bundle, diffs)
    assert bundle.interpretations == []
    print("[PASS] test_infer_from_diffs_skips_unchanged_diff")


def test_bundle_round_trip_preserves_new_fields():
    import json, tempfile, os
    from serum2.source.visual_evidence import (
        VisualEvidenceBundle, ObservedCanonicalState, CanonicalStateDiff,
    )

    bundle = VisualEvidenceBundle(source_url="u", source_id="s", video_id="v")
    before = ObservedCanonicalState(target="Env1.Release", value="15 ms",
                                     frame_id="f34", timestamp_sec=34.0, frame_hash="aaa")
    after = ObservedCanonicalState(target="Env1.Release", value="220 ms",
                                    frame_id="f38", timestamp_sec=38.0, frame_hash="bbb")
    bundle.observed_canonical_states = [before, after]
    bundle.canonical_diffs = [CanonicalStateDiff(
        target="Env1.Release", before=before, after=after, changed=True,
    )]
    bundle.query_plan = {"concept_hint": "note-release", "targets": []}
    bundle.unknown = ["exact UI gesture used to change the value"]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(bundle.to_dict()))
        tmp_path = f.name
    try:
        loaded = VisualEvidenceBundle.load(tmp_path)
        assert len(loaded.observed_canonical_states) == 2
        assert loaded.observed_canonical_states[1].value == "220 ms"
        assert len(loaded.canonical_diffs) == 1
        assert loaded.canonical_diffs[0].changed is True
        assert loaded.query_plan["concept_hint"] == "note-release"
        assert loaded.unknown == ["exact UI gesture used to change the value"]
    finally:
        os.unlink(tmp_path)
    print("[PASS] test_bundle_round_trip_preserves_new_fields")


if __name__ == "__main__":
    test_planner_finds_release_mention_and_brackets_it()
    test_planner_blocks_honestly_when_no_known_target_mentioned()
    test_diff_pairs_earliest_and_latest_reading_per_target()
    test_infer_from_diffs_derives_direction_without_a_model_call()
    test_infer_from_diffs_skips_unchanged_diff()
    test_bundle_round_trip_preserves_new_fields()
    print("\nAll transcript-first visual path tests passed.")
