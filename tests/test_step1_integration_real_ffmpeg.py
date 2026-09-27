from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from serum2.source.acquire_exhaustive import extract_all_frames


FFMPEG = shutil.which("ffmpeg")

pytestmark = pytest.mark.skipif(
    FFMPEG is None,
    reason="ffmpeg executable not installed on this machine",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


@pytest.fixture
def tiny_video(tmp_path: Path) -> Path:
    """
    Create a real deterministic video using the actual ffmpeg executable.

    2 seconds × 5 fps = approximately 10 frames.
    """

    output = tmp_path / "step1_tiny.mp4"

    command = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "error",

        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=5:duration=2",

        "-pix_fmt",
        "yuv420p",

        "-an",

        "-y",
        str(output),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, (
        "ffmpeg failed to create deterministic test video:\n"
        + result.stderr
    )

    assert output.exists()
    assert output.stat().st_size > 0

    return output


def get_frame_index(artifact) -> int:
    """
    VisualFrameArtifact does not contain a frame_index attribute.

    Production frame_id format:

        frame_<source_id>_<8-digit-frame-index>
    """

    return int(
        artifact.frame_id.rsplit("_", 1)[-1]
    )


class TestRealFFmpegStep1:

    def test_real_ffmpeg_complete_exhaustion(
        self,
        tiny_video: Path,
        tmp_path: Path,
    ) -> None:
        """
        Execute the REAL ffmpeg executable against a REAL video.

        This tests extract_all_frames(), which is the actual decoder boundary.

        Required proof:

            decoder_count
                ==
            artifact_count
                ==
            verified_count
        """

        source_sha = sha256_file(tiny_video)

        # IMPORTANT:
        # This directory MUST NOT exist yet.
        extraction_dir = tmp_path / "fresh_extraction"

        artifacts, completion = extract_all_frames(
            video_path=tiny_video,
            temp_frames_dir=extraction_dir,
            source_id="integration",
            source_video_sha=source_sha,
        )

        assert completion["decoder_exit_code"] == 0

        decoder_count = completion["decoder_frame_count"]
        artifact_count = completion["artifact_frame_count"]
        verified_count = completion["verified_frame_count"]

        assert decoder_count > 0

        assert decoder_count == artifact_count
        assert artifact_count == verified_count
        assert len(artifacts) == decoder_count

        assert completion["missing_frame_indices"] == []
        assert completion["duplicate_frame_indices"] == []
        assert completion["unexpected_frame_files"] == []

        assert completion["decoder_pts_complete"] is True
        assert completion["decoder_artifact_index_match"] is True
        assert completion["decoder_artifact_dimension_match"] is True
        assert completion["is_complete"] is True

        indices = sorted(
            get_frame_index(a)
            for a in artifacts
        )

        assert indices == list(
            range(decoder_count)
        )

        from PIL import Image

        for artifact in artifacts:
            assert artifact.timestamp_sec is not None
            assert artifact.width is not None
            assert artifact.height is not None

            assert artifact.width > 0
            assert artifact.height > 0

            assert artifact.artifact_hash
            assert len(artifact.artifact_hash) == 64

            artifact_path = Path(
                artifact.artifact_path
            )

            assert artifact_path.exists()
            assert artifact_path.stat().st_size > 0

            # Actual image decode.
            with Image.open(artifact_path) as image:
                image.load()

                assert image.width == artifact.width
                assert image.height == artifact.height


    def test_real_ffmpeg_has_decoder_pts_for_every_frame(
        self,
        tiny_video: Path,
        tmp_path: Path,
    ) -> None:
        """
        Every successful decoder frame must have actual PTS.

        The production implementation obtains timestamp_sec from:

            ffmpeg showinfo -> DecoderFrame.pts_time

        The test itself does NOT calculate PTS.
        """

        source_sha = sha256_file(tiny_video)

        extraction_dir = tmp_path / "pts_extraction"

        artifacts, completion = extract_all_frames(
            video_path=tiny_video,
            temp_frames_dir=extraction_dir,
            source_id="pts",
            source_video_sha=source_sha,
        )

        assert completion["is_complete"] is True
        assert completion["decoder_pts_complete"] is True

        assert len(artifacts) == completion["decoder_frame_count"]

        for artifact in artifacts:
            assert artifact.timestamp_sec is not None
            assert isinstance(
                artifact.timestamp_sec,
                (int, float),
            )


    def test_real_ffmpeg_dimensions_match_artifacts(
        self,
        tiny_video: Path,
        tmp_path: Path,
    ) -> None:
        """
        Decoder dimensions must match the actual decoded JPEG dimensions.
        """

        source_sha = sha256_file(tiny_video)

        extraction_dir = tmp_path / "dimension_extraction"

        artifacts, completion = extract_all_frames(
            video_path=tiny_video,
            temp_frames_dir=extraction_dir,
            source_id="dimensions",
            source_video_sha=source_sha,
        )

        assert completion["is_complete"] is True

        from PIL import Image

        for artifact in artifacts:
            artifact_path = Path(
                artifact.artifact_path
            )

            with Image.open(artifact_path) as image:
                image.load()

                assert image.width == artifact.width
                assert image.height == artifact.height
