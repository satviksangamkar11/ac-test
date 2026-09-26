"""reference_engine's Stage 1 wiring, proven against the real captured 'Pluck To Lead in Serum 2' frame data
(serum2/video_capture/v1/) that this session's local agent already downloaded. Only the two network-dependent calls
(fetch_transcript, acquire_visual_evidence) are mocked -- everything downstream of them (source_id computation,
transcript path resolution, frame directory resolution, the NeedsStageACensus stop) is real."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
REAL_VIDEO_DIR = ROOT / "serum2" / "video_capture" / "v1"
YOUTUBE_URL = "https://www.youtube.com/watch?v=h4biGNiYJTQ"

pytestmark = pytest.mark.skipif(not REAL_VIDEO_DIR.is_dir(), reason="captured video fixture not present")

sys.path.insert(0, str(ROOT / "youtube_to_serum"))
import reference_engine as eng  # noqa: E402


def _fake_frame_bundle():
    frames = sorted((REAL_VIDEO_DIR / "frames").glob("f_*.jpg"))[:5]   # small slice: this test checks wiring, not scale
    return SimpleNamespace(frames=[
        SimpleNamespace(artifact_path=str(p.relative_to(ROOT)), frame_id=p.stem, timestamp_sec=i)
        for i, p in enumerate(frames)
    ])


def test_stage1_raises_needs_census_with_real_frame_and_transcript_data(tmp_path, monkeypatch):
    from serum2.source.fetch_youtube import compute_source_id
    source_id = compute_source_id(YOUTUBE_URL)
    transcripts_dir = tmp_path / "data" / "transcripts"
    transcripts_dir.mkdir(parents=True)
    # A fetch_transcript-shaped file built from the real captured json3 transcript's first few segments.
    raw = json.loads((REAL_VIDEO_DIR / "transcript.en.json3").read_text())
    segs = []
    for ev in raw["events"][:6]:
        if ev.get("segs"):
            text = "".join(s.get("utf8", "") for s in ev["segs"]).strip()
            if text and text != "\n":
                segs.append({"text": text, "start_time_sec": ev["tStartMs"] / 1000.0, "duration": ev.get("dDurationMs", 0) / 1000.0})
    (transcripts_dir / (source_id + ".json")).write_text(json.dumps({
        "source_id": source_id, "video_id": "h4biGNiYJTQ", "source_url": YOUTUBE_URL,
        "language_code": "en", "segments": segs,
    }))

    monkeypatch.setattr(eng, "fetch_transcript", lambda **kw: True)
    monkeypatch.setattr(eng, "acquire_visual_evidence", lambda **kw: _fake_frame_bundle())
    monkeypatch.chdir(tmp_path)   # fetch_transcript (and this engine, matching it) resolve data/transcripts via CWD

    with pytest.raises(eng.NeedsStageACensus) as exc:
        eng.run_stage1_acquire_and_prep(YOUTUBE_URL, tmp_path / "work")

    # build_frame_manifest globs the whole real frames/ directory the bundle points at, not just the frame objects
    # the (mocked) bundle happened to list -- that's correct: the directory is the actual source of truth.
    real_frame_count = len(list((REAL_VIDEO_DIR / "frames").glob("f_*.jpg")))
    assert exc.value.n_frames == real_frame_count
    skeleton = json.loads(Path(exc.value.skeleton_path).read_text())
    assert len(skeleton["frames"]) == real_frame_count
    transcript = json.loads(Path(exc.value.normalized_transcript_path).read_text())
    assert transcript["video_id"] == "h4biGNiYJTQ"
    assert len(transcript["transcript"]) == len(segs)
    assert "What's up" in transcript["transcript"][0]["text"]


def test_stage1_proceeds_past_census_once_the_skeleton_is_filled(tmp_path, monkeypatch):
    from serum2.source.fetch_youtube import compute_source_id
    source_id = compute_source_id(YOUTUBE_URL)
    transcripts_dir = tmp_path / "data" / "transcripts"
    transcripts_dir.mkdir(parents=True)
    (transcripts_dir / (source_id + ".json")).write_text(json.dumps({
        "source_id": source_id, "video_id": "h4biGNiYJTQ", "source_url": YOUTUBE_URL,
        "language_code": "en", "segments": [],
    }))
    monkeypatch.setattr(eng, "fetch_transcript", lambda **kw: True)
    monkeypatch.setattr(eng, "acquire_visual_evidence", lambda **kw: _fake_frame_bundle())
    monkeypatch.chdir(tmp_path)

    try:
        eng.run_stage1_acquire_and_prep(YOUTUBE_URL, tmp_path / "work")
        assert False, "expected NeedsStageACensus on the first pass"
    except eng.NeedsStageACensus as first:
        skeleton_path = first.skeleton_path

    data = json.loads(Path(skeleton_path).read_text())
    data["frames"][0]["serum_visible"] = True
    data["frames"][0]["controls"] = [{"control_id": "oscA.enabled", "control_type": "toggle", "label": "A",
                                      "value": "on", "unit": None, "status": "OBSERVED",
                                      "screen_region": "osc panel", "confidence": 0.9}]
    Path(skeleton_path).write_text(json.dumps(data))

    result = eng.run_stage1_acquire_and_prep(YOUTUBE_URL, tmp_path / "work")
    assert result["stage_a_skeleton_path"] == skeleton_path
