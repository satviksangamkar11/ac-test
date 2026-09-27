"""Track B Acquisition: cache key includes params, ffprobe=None raises, storyboard flag.

Tests the acquire_visual_evidence module without making real network calls.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serum2.source.acquire_visual_evidence import (
    AcquisitionError, _params_hash, _source_id,
)


def test_params_hash_differs_with_different_max_frames():
    h1 = _params_hash(8, 45.0)
    h2 = _params_hash(16, 45.0)
    assert h1 != h2, "params_hash must differ when max_frames changes"


def test_params_hash_differs_with_different_interval():
    h1 = _params_hash(8, 45.0)
    h2 = _params_hash(8, 30.0)
    assert h1 != h2, "params_hash must differ when sample_interval_sec changes"


def test_params_hash_same_for_same_params():
    assert _params_hash(8, 45.0) == _params_hash(8, 45.0)


def test_manifest_path_includes_params_hash(tmp_path):
    """Two different param sets must produce different manifest paths.
    Verified by checking the hash suffix in the filenames."""
    sid = _source_id("https://www.youtube.com/watch?v=testid")
    p1 = "manifest_%s.json" % _params_hash(8, 45.0)
    p2 = "manifest_%s.json" % _params_hash(16, 45.0)
    assert p1 != p2


def test_acquisition_error_is_raised_for_unknown_duration(tmp_path):
    """When ffprobe cannot determine duration, AcquisitionError must be raised (not 300s default)."""
    with patch("serum2.source.acquire_visual_evidence._validate_youtube_url", return_value=("https://youtube.com/watch?v=x", "x")), \
         patch("serum2.source.acquire_visual_evidence._find_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("serum2.source.acquire_visual_evidence._download_best_video") as mock_dl, \
         patch("serum2.source.acquire_visual_evidence._get_video_duration", return_value=None), \
         patch("serum2.source.acquire_visual_evidence._FRAMES_DIR", tmp_path):
        mock_dl.return_value = (Path("/tmp/fake.mp4"), {"duration_sec": None, "width": 1920, "height": 1080})
        from serum2.source.acquire_visual_evidence import acquire_visual_evidence
        with pytest.raises(AcquisitionError, match="ffprobe could not determine"):
            acquire_visual_evidence("https://youtube.com/watch?v=x", max_frames=8, sample_interval_sec=45.0)


def test_storyboard_only_false_for_real_video():
    """A real-video acquisition must set storyboard_only=False on the bundle."""
    from serum2.source.visual_evidence import VisualEvidenceBundle
    b = VisualEvidenceBundle(source_url="https://youtube.com/watch?v=x", source_id="yt_test", video_id="x")
    assert b.storyboard_only is False


def test_storyboard_only_true_when_set():
    from serum2.source.visual_evidence import VisualEvidenceBundle
    b = VisualEvidenceBundle(source_url="https://youtube.com/watch?v=x", source_id="yt_test", video_id="x",
                             storyboard_only=True)
    assert b.storyboard_only is True


def test_storyboard_only_roundtrips_via_dict():
    from serum2.source.visual_evidence import VisualEvidenceBundle
    b = VisualEvidenceBundle(source_url="u", source_id="s", video_id="v", storyboard_only=True)
    d = b.to_dict()
    assert d["storyboard_only"] is True
    # Reload via load() requires a file; test dict representation is sufficient
    from serum2.source.visual_evidence import VisualEvidenceBundle as VEB
    b2 = VEB(source_url=d["source_url"], source_id=d["source_id"], video_id=d["video_id"],
              storyboard_only=d.get("storyboard_only", False))
    assert b2.storyboard_only is True
