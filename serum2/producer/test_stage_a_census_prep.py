"""stage_a_census_prep is pure mechanical prep: no vision, no invented values. Fixtures are small and synthetic."""
import json

from serum2.producer.stage_a_census_prep import (
    build_frame_manifest, empty_stage_a_skeleton, normalize_fetch_transcript_output, normalize_transcript, prep,
)


def _json3(tmp_path, events):
    p = tmp_path / "t.json3"
    p.write_text(json.dumps({"events": events}))
    return str(p)


def test_normalize_transcript_extracts_text_and_seconds(tmp_path):
    events = [
        {"tStartMs": 0, "dDurationMs": 2000, "segs": [{"utf8": "hello"}]},
        {"tStartMs": 750},                                     # a bare newline-only event: no segs, must be skipped
        {"tStartMs": 2000, "dDurationMs": 1500, "segs": [{"utf8": "wor"}, {"utf8": "ld"}]},
    ]
    t = normalize_transcript(_json3(tmp_path, events), "abc123", "https://youtube.com/watch?v=abc123")
    assert t["video_id"] == "abc123" and t["source_id"] == "yt_abc123"
    assert len(t["transcript"]) == 2
    assert t["transcript"][0] == {"segment_id": "seg-0000", "text": "hello", "start_time_sec": 0.0, "duration": 2.0}
    assert t["transcript"][1]["text"] == "world" and t["transcript"][1]["start_time_sec"] == 2.0


def test_normalize_transcript_skips_blank_and_whitespace_only_segments(tmp_path):
    events = [{"tStartMs": 0, "dDurationMs": 100, "segs": [{"utf8": "\n"}]},
              {"tStartMs": 100, "dDurationMs": 100, "segs": [{"utf8": "  "}]}]
    t = normalize_transcript(_json3(tmp_path, events), "x", "https://y")
    assert t["transcript"] == []


def test_build_frame_manifest_from_sparse_frames_only(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    for i in (1, 2, 30):
        (frames / ("f_%05d.jpg" % i)).write_bytes(b"\xff\xd8")
    m = build_frame_manifest(str(frames), fps=1.0)
    assert [f["timestamp_sec"] for f in m] == [0.0, 1.0, 29.0]
    assert all(f["source"] == "sparse" for f in m)


def test_build_frame_manifest_resolves_dense_windows_across_path_separators(tmp_path):
    """Regression: windows.json is often written on Windows (backslash-separated `dir`). On a different machine,
    trusting that raw string silently drops every dense frame with no error. Frames must resolve by directory NAME
    against the real dense/ root, whatever separator the recorded string used."""
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames / "f_00001.jpg").write_bytes(b"\xff\xd8")
    dense = tmp_path / "dense" / "0000"
    dense.mkdir(parents=True)
    for i in (1, 2):
        (dense / ("f_%05d.jpg" % i)).write_bytes(b"\xff\xd8")
    windows_json = tmp_path / "dense" / "windows.json"
    windows_json.write_text(json.dumps({
        "dense_fps": 10,
        "windows": [{"start": 5.0, "end": 5.2, "dir": r"C:\some\other\machine\dense\0000", "frames": 2}],
    }))
    m = build_frame_manifest(str(frames), fps=1.0, dense_windows_json=str(windows_json))
    dense_entries = [f for f in m if f["source"] == "dense"]
    assert len(dense_entries) == 2, "dense frames were dropped by the path-separator mismatch"
    assert dense_entries[0]["timestamp_sec"] == 5.0
    assert dense_entries[1]["timestamp_sec"] == 5.1


def test_build_frame_manifest_missing_dense_dir_is_silent_not_a_crash(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    windows_json = tmp_path / "windows.json"
    windows_json.write_text(json.dumps({"dense_fps": 10, "windows": [{"start": 0, "end": 1, "dir": "nope", "frames": 0}]}))
    m = build_frame_manifest(str(frames), fps=1.0, dense_windows_json=str(windows_json))
    assert m == []


def test_empty_skeleton_has_one_entry_per_frame_all_empty():
    manifest = [{"frame_id": "f1", "timestamp_sec": 0.0, "path": "/a.jpg"},
                {"frame_id": "f2", "timestamp_sec": 1.0, "path": "/b.jpg"}]
    s = empty_stage_a_skeleton(manifest)
    assert s["stage_a_provenance"] == {"observer": "claude_code", "observation_mode": "direct_visual_inspection",
                                       "model_api_used": False}
    assert len(s["frames"]) == 2
    for f in s["frames"]:
        assert f["serum_visible"] is None
        assert f["controls"] == [] and f["mod_routes"] == [] and f["observations"] == [] and f["unknown"] == []


def test_skeleton_matches_the_real_fixture_shape():
    """No key in the skeleton (besides the provenance-only _source_path) may be absent from the shape
    state_ledger.build_all already consumes."""
    fixture = json.loads(open("tests/fixtures/reference_reproduction/stage_a_observation.json").read())
    skeleton = empty_stage_a_skeleton([{"frame_id": "f1", "timestamp_sec": 0.0, "path": "/a.jpg"}])
    assert set(skeleton["stage_a_provenance"]) == set(fixture["stage_a_provenance"])
    fixture_frame_keys = set(fixture["frames"][0])
    skeleton_frame_keys = set(skeleton["frames"][0]) - {"_source_path"}
    assert skeleton_frame_keys == fixture_frame_keys


def test_normalize_fetch_transcript_output_reshapes_the_real_pipeline_format(tmp_path):
    """serum2.source.fetch_youtube.fetch_transcript's actual saved shape -- a different file/format/location than
    the raw json3 the other normalizer handles."""
    p = tmp_path / "yt_abc123.json"
    p.write_text(json.dumps({
        "source_id": "yt_abc123", "video_id": "abc123", "source_url": "https://y/abc123",
        "language": "English", "language_code": "en",
        "segments": [{"text": "hello", "start_time_sec": 0.0, "duration": 2.0},
                    {"text": "world", "start_time_sec": 2.0, "duration": 1.5}],
    }))
    t = normalize_fetch_transcript_output(str(p))
    assert t["source_id"] == "yt_abc123" and t["video_id"] == "abc123" and t["language"] == "en"
    assert len(t["transcript"]) == 2
    assert t["transcript"][0] == {"segment_id": "seg-0000", "text": "hello", "start_time_sec": 0.0, "duration": 2.0}


def test_prep_accepts_fetch_transcript_kind(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames / "f_00001.jpg").write_bytes(b"\xff\xd8")
    tp = tmp_path / "yt_x.json"
    tp.write_text(json.dumps({"source_id": "yt_x", "video_id": "x", "source_url": "https://y/x",
                              "language_code": "en", "segments": []}))
    result = prep(str(frames), str(tp), "x", "https://y/x", str(tmp_path / "out"), transcript_kind="fetch_transcript")
    assert json.loads(open(result["normalized_transcript_path"]).read())["video_id"] == "x"


def test_prep_writes_both_files_and_reports_frame_count(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames / "f_00001.jpg").write_bytes(b"\xff\xd8")
    transcript = _json3(tmp_path, [{"tStartMs": 0, "dDurationMs": 500, "segs": [{"utf8": "hi"}]}])
    out = tmp_path / "out"
    result = prep(str(frames), transcript, "vid1", "https://y/vid1", str(out))
    assert result["n_frames"] == 1
    assert json.loads(open(result["normalized_transcript_path"]).read())["video_id"] == "vid1"
    assert len(json.loads(open(result["stage_a_skeleton_path"]).read())["frames"]) == 1
