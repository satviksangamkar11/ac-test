"""Exhaustive frame acquisition: decode every source frame exactly once with authoritative decoder accounting.

STEP 1 CLOSURE: Complete frame manifest with decoder-side accounting.

YouTube URL
   → verified downloaded source video
   → SAME ffmpeg decode process with showinfo metadata
   → decoder showinfo ledger (authoritative frame sequence)
   → independent artifact ledger (JPEG files)
   → exact decoder/artifact one-to-one reconciliation
   → complete immutable manifest
   → validated cache reuse only

The decoder ledger (from ffmpeg showinfo) is independent from the artifact ledger (JPEG files).
Both must be present, contiguous, and match exactly — or acquisition fails closed.

Explicitly forbidden:
  - duration * fps
  - max JPEG index + 1
  - counting filenames as decoder count
  - synthetic timestamp = frame_index / fps
  - timestamp_sec=None for successful frames
  - trusting JPEG existence as readability
  - old cache reuse based only on video_id
  - stale directory contamination
  - partial promotion
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from serum2.source.visual_evidence import VisualFrameArtifact
from serum2.source.youtube_url import extract_youtube_video_id

_FRAMES_DIR = Path(__file__).parent.parent / "data" / "visual_frames"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _source_id(url: str) -> str:
    return "yt_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _get_ffmpeg_version() -> Optional[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        proc = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=10)
        first_line = (proc.stdout or "").split("\n")[0]
        return first_line.strip() or None
    except Exception:
        return None


def _get_yt_dlp_version() -> Optional[str]:
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return None
    try:
        proc = subprocess.run([yt_dlp, "--version"], capture_output=True, text=True, timeout=15)
        return proc.stdout.strip() or None
    except Exception:
        return None


def _load_image_verify(path: Path) -> Tuple[bool, Optional[int], Optional[int]]:
    """Load image and verify it's decodable. Returns (success, width, height)."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.load()
            w, h = img.size
            return True, w, h
    except Exception:
        return False, None, None


# Showinfo parsing
_SHOWINFO_RE = re.compile(
    r"""
    \bn:\s*(?P<frame_index>\d+)\b
    .*?\bpts_time:\s*(?P<pts_time>
        [+-]?
        (?:
            \d+(?:\.\d*)?
            |
            \.\d+
        )
        (?:[eE][+-]?\d+)?
    )\b
    .*?\bs:\s*(?P<width>\d+)x(?P<height>\d+)\b
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class DecoderFrame:
    frame_index: int
    pts_time: float
    width: int
    height: int


def _parse_showinfo_frames(stderr: str) -> List[DecoderFrame]:
    """
    Parse ffmpeg showinfo records.

    This is the authoritative decoder ledger.
    Never derive these values from output filenames.
    """
    frames: List[DecoderFrame] = []

    for match in _SHOWINFO_RE.finditer(stderr or ""):
        frames.append(
            DecoderFrame(
                frame_index=int(match.group("frame_index")),
                pts_time=float(match.group("pts_time")),
                width=int(match.group("width")),
                height=int(match.group("height")),
            )
        )

    return frames


def _decoder_index_errors(decoder_frames: List[DecoderFrame]) -> Tuple[List[int], List[int]]:
    """
    Return (missing_indices, duplicate_indices) from decoder metadata.
    """
    counts: Dict[int, int] = {}

    for frame in decoder_frames:
        counts[frame.frame_index] = counts.get(frame.frame_index, 0) + 1

    if not counts:
        return [], []

    first = min(counts)
    last = max(counts)

    expected = set(range(first, last + 1))
    actual = set(counts)

    missing = sorted(expected - actual)
    duplicates = sorted(
        index for index, count in counts.items() if count > 1
    )

    return missing, duplicates


def _artifact_index_from_name(path: Path, source_id: str) -> Optional[int]:
    """
    Parse the ffmpeg image2 filename.

    Filename numbering is ONLY used to identify the artifact.
    It is NEVER used as decoder accounting.
    """
    prefix = f"frame_{source_id}_"

    if not path.name.startswith(prefix):
        return None

    if path.suffix.lower() != ".jpg":
        return None

    suffix = path.name[len(prefix):-4]

    if not suffix.isdigit():
        return None

    # ffmpeg image2 numbering is 1-based.
    return int(suffix) - 1


def _enumerate_artifacts(
    frames_dir: Path,
    source_id: str,
) -> Tuple[Dict[int, Path], List[int], List[str]]:
    """
    Return:
      artifacts_by_index
      duplicate artifact indices
      unexpected files
    """
    artifacts_by_index: Dict[int, Path] = {}
    duplicate_indices: List[int] = []
    unexpected_files: List[str] = []

    for path in sorted(frames_dir.iterdir()):
        if not path.is_file():
            continue

        index = _artifact_index_from_name(path, source_id)

        if index is None:
            unexpected_files.append(path.name)
            continue

        if index in artifacts_by_index:
            duplicate_indices.append(index)
        else:
            artifacts_by_index[index] = path

    return (
        artifacts_by_index,
        sorted(set(duplicate_indices)),
        sorted(unexpected_files),
    )


def _verify_artifact(
    path: Path,
) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
    """
    Actually decode the JPEG with PIL.

    Returns:
        ok, width, height, sha256
    """
    ok, width, height = _load_image_verify(path)

    if not ok or width is None or height is None:
        return False, None, None, None

    try:
        digest = _sha256_file(path)
    except Exception:
        return False, None, None, None

    return True, width, height, digest


def _reconcile_decoder_and_artifacts(
    decoder_frames: List[DecoderFrame],
    artifacts_by_index: Dict[int, Path],
    duplicate_artifact_indices: List[int],
    unexpected_files: List[str],
    expected_source_video_sha: str,
    source_id: str,
) -> Tuple[List[VisualFrameArtifact], Dict]:
    """
    Reconcile TWO independent ledgers:

      A. decoder metadata emitted by ffmpeg showinfo
      B. artifact files written by ffmpeg

    Completion is possible only when they match exactly.
    """

    missing_decoder_indices, duplicate_decoder_indices = _decoder_index_errors(
        decoder_frames
    )

    decoder_indices = [frame.frame_index for frame in decoder_frames]

    if decoder_indices:
        first_decoder_index = min(decoder_indices)
        last_decoder_index = max(decoder_indices)
    else:
        first_decoder_index = None
        last_decoder_index = None

    decoder_frame_count = len(decoder_frames)
    artifact_frame_count = len(artifacts_by_index)

    artifact_indices = sorted(artifacts_by_index)

    if decoder_indices:
        expected_decoder_set = set(range(first_decoder_index, last_decoder_index + 1))
    else:
        expected_decoder_set = set()

    decoder_set = set(decoder_indices)
    artifact_set = set(artifact_indices)

    missing_frame_indices = sorted(
        expected_decoder_set - artifact_set
    )

    unexpected_artifact_indices = sorted(
        artifact_set - expected_decoder_set
    )

    decoder_pts_complete = all(
        frame.pts_time is not None
        for frame in decoder_frames
    )

    verified_frame_count = 0
    artifacts: List[VisualFrameArtifact] = []

    dimension_mismatches: List[int] = []
    unreadable_indices: List[int] = []
    hash_failures: List[int] = []

    # Do NOT trust artifact order.
    # Reconcile by index against the decoder ledger.
    for decoder_frame in decoder_frames:
        index = decoder_frame.frame_index
        path = artifacts_by_index.get(index)

        if path is None:
            continue

        ok, width, height, digest = _verify_artifact(path)

        if not ok:
            unreadable_indices.append(index)
            continue

        if (
            width != decoder_frame.width
            or height != decoder_frame.height
        ):
            dimension_mismatches.append(index)
            continue

        if not digest:
            hash_failures.append(index)
            continue

        verified_frame_count += 1

        frame_id = f"frame_{source_id}_{decoder_frame.frame_index:08d}"

        artifacts.append(
            VisualFrameArtifact(
                frame_id=frame_id,
                source_url="",
                source_id=source_id,
                video_id="",
                timestamp_sec=decoder_frame.pts_time,
                artifact_path=str(path),
                artifact_hash=digest,
                width=width,
                height=height,
                source_video_sha256=expected_source_video_sha,
            )
        )

    decoder_artifact_index_match = (
        decoder_set == artifact_set
        and not missing_frame_indices
        and not unexpected_artifact_indices
        and not duplicate_decoder_indices
        and not duplicate_artifact_indices
    )

    decoder_artifact_dimension_match = (
        not dimension_mismatches
        and verified_frame_count == decoder_frame_count
    )

    is_complete = (
        decoder_frame_count > 0
        and decoder_frame_count == artifact_frame_count
        and decoder_frame_count == verified_frame_count
        and not missing_decoder_indices
        and not duplicate_decoder_indices
        and not duplicate_artifact_indices
        and not missing_frame_indices
        and not unexpected_artifact_indices
        and not unexpected_files
        and decoder_pts_complete
        and decoder_artifact_index_match
        and decoder_artifact_dimension_match
        and not unreadable_indices
        and not hash_failures
    )

    if is_complete:
        reason = "all decoder frames reconciled to verified artifacts"
    elif not decoder_frames:
        reason = "ffmpeg emitted no decoder frame metadata"
    elif missing_decoder_indices:
        reason = f"decoder missing indices: {missing_decoder_indices[:20]}"
    elif duplicate_decoder_indices:
        reason = f"duplicate decoder indices: {duplicate_decoder_indices[:20]}"
    elif missing_frame_indices:
        reason = f"artifacts missing indices: {missing_frame_indices[:20]}"
    elif unexpected_artifact_indices:
        reason = (
            f"unexpected artifact indices: "
            f"{unexpected_artifact_indices[:20]}"
        )
    elif duplicate_artifact_indices:
        reason = (
            f"duplicate artifact indices: "
            f"{duplicate_artifact_indices[:20]}"
        )
    elif unexpected_files:
        reason = f"unexpected files: {unexpected_files[:20]}"
    elif not decoder_pts_complete:
        reason = "one or more decoder frames have no PTS"
    elif unreadable_indices:
        reason = f"unreadable artifacts: {unreadable_indices[:20]}"
    elif dimension_mismatches:
        reason = f"dimension mismatches: {dimension_mismatches[:20]}"
    elif hash_failures:
        reason = f"hash failures: {hash_failures[:20]}"
    elif decoder_frame_count != artifact_frame_count:
        reason = (
            f"decoder/artifact count mismatch: "
            f"{decoder_frame_count} != {artifact_frame_count}"
        )
    elif decoder_frame_count != verified_frame_count:
        reason = (
            f"decoder/verified count mismatch: "
            f"{decoder_frame_count} != {verified_frame_count}"
        )
    else:
        reason = "exhaustive reconciliation failed"

    completion_status = {
        "decoder_exit_code": None,
        "decoder_frame_count": decoder_frame_count,
        "artifact_frame_count": artifact_frame_count,
        "verified_frame_count": verified_frame_count,
        "missing_frame_indices": sorted(
            set(missing_decoder_indices + missing_frame_indices)
        ),
        "duplicate_frame_indices": sorted(
            set(
                duplicate_decoder_indices
                + duplicate_artifact_indices
            )
        ),
        "unexpected_frame_files": unexpected_files,
        "unexpected_artifact_indices": unexpected_artifact_indices,
        "first_frame_index": first_decoder_index,
        "last_frame_index": last_decoder_index,
        "decoder_pts_complete": decoder_pts_complete,
        "decoder_artifact_index_match": decoder_artifact_index_match,
        "decoder_artifact_dimension_match": decoder_artifact_dimension_match,
        "unreadable_frame_indices": unreadable_indices,
        "hash_failure_indices": hash_failures,
        "dimension_mismatch_indices": dimension_mismatches,
        "is_complete": is_complete,
        "completion_reason": reason,
    }

    return artifacts, completion_status


def extract_all_frames(
    video_path: Path,
    temp_frames_dir: Path,
    source_id: str,
    source_video_sha: str,
) -> Tuple[List[VisualFrameArtifact], Dict]:
    """
    Authoritative exhaustive decode.

    SAME ffmpeg invocation:
      - decodes every frame
      - emits showinfo metadata
      - writes one JPEG per decoded frame

    Decoder metadata is the authoritative frame ledger.
    Filesystem enumeration is an independent artifact ledger.
    """

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")

    # The caller provides a fresh directory.
    # Still refuse to operate on a dirty directory.
    temp_frames_dir.mkdir(parents=True, exist_ok=False)

    frame_pattern = temp_frames_dir / f"frame_{source_id}_%09d.jpg"

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "info",

        # Input
        "-i", str(video_path),

        # Decode every source frame.
        # Do NOT resample FPS.
        "-vf", "showinfo",

        # Prevent ffmpeg from inserting/dropping frames at the output.
        "-fps_mode", "passthrough",

        # JPEG output.
        "-q:v", "3",
        "-y",
        str(frame_pattern),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"ffmpeg extraction timed out for {video_path}"
        ) from exc

    decoder_exit_code = proc.returncode

    # CRITICAL:
    # The decoder ledger comes from ffmpeg stderr showinfo records.
    decoder_frames = _parse_showinfo_frames(proc.stderr or "")

    # Artifact ledger is independent.
    (
        artifacts_by_index,
        duplicate_artifact_indices,
        unexpected_files,
    ) = _enumerate_artifacts(
        temp_frames_dir,
        source_id,
    )

    (
        artifacts,
        completion_status,
    ) = _reconcile_decoder_and_artifacts(
        decoder_frames=decoder_frames,
        artifacts_by_index=artifacts_by_index,
        duplicate_artifact_indices=duplicate_artifact_indices,
        unexpected_files=unexpected_files,
        expected_source_video_sha=source_video_sha,
        source_id=source_id,
    )

    completion_status["decoder_exit_code"] = decoder_exit_code

    # ffmpeg failure ALWAYS fails closed.
    if decoder_exit_code != 0:
        completion_status["is_complete"] = False
        completion_status["completion_reason"] = (
            f"ffmpeg exited with code {decoder_exit_code}"
        )

    # A successful decoder exit with zero metadata also fails closed.
    if not decoder_frames:
        completion_status["is_complete"] = False
        completion_status["completion_reason"] = (
            "ffmpeg exited without decoder frame metadata"
        )

    # Important:
    # Never promote partial output.
    if not completion_status["is_complete"]:
        return [], completion_status

    # Attach final artifact metadata.
    for artifact in artifacts:
        artifact.source_id = source_id
        artifact.source_url = ""
        artifact.video_id = ""

    return artifacts, completion_status


def _validate_cached_manifest(
    data: dict,
    source_url: str,
    video_id: str,
    source_id: str,
    cache_key: str,
) -> bool:
    """
    Validate an existing exhaustive cache completely.

    Returning True means the cached manifest itself proves that the
    acquisition is complete and all cached artifacts are still valid.
    """

    if data.get("source_url") != source_url:
        return False

    if data.get("video_id") != video_id:
        return False

    if data.get("source_id") != source_id:
        return False

    if data.get("acquisition_mode") != "exhaustive":
        return False

    if data.get("cache_key") != cache_key:
        return False

    completion = data.get("completion_status") or {}

    if not completion.get("is_complete"):
        return False

    if completion.get("decoder_exit_code") != 0:
        return False

    decoder_count = completion.get("decoder_frame_count")
    artifact_count = completion.get("artifact_frame_count")
    verified_count = completion.get("verified_frame_count")

    if decoder_count is None:
        return False

    if decoder_count <= 0:
        return False

    if decoder_count != artifact_count:
        return False

    if decoder_count != verified_count:
        return False

    if completion.get("missing_frame_indices") != []:
        return False

    if completion.get("duplicate_frame_indices") != []:
        return False

    if completion.get("unexpected_frame_files") != []:
        return False

    if not completion.get("decoder_pts_complete"):
        return False

    if not completion.get("decoder_artifact_index_match"):
        return False

    if not completion.get("decoder_artifact_dimension_match"):
        return False

    provenance = data.get("provenance") or {}

    if not provenance.get("source_video_sha256"):
        return False

    if not provenance.get("selected_resolution"):
        return False

    if not provenance.get("ffmpeg_version"):
        return False

    if not provenance.get("yt_dlp_version"):
        return False

    frames = data.get("frames") or []

    if len(frames) != decoder_count:
        return False

    indices = []

    for frame_data in frames:
        frame_id = frame_data.get("frame_id")
        frame_index = frame_data.get("frame_index")

        if frame_index is None:
            # Backward-incompatible cache.
            return False

        if frame_id is None:
            return False

        if frame_data.get("presentation_timestamp_sec") is None:
            return False

        artifact_path = Path(
            frame_data.get("artifact_path", "")
        )

        if not artifact_path.exists():
            return False

        ok, width, height, digest = _verify_artifact(
            artifact_path
        )

        if not ok:
            return False

        if width != frame_data.get("width"):
            return False

        if height != frame_data.get("height"):
            return False

        if digest != frame_data.get("artifact_sha256"):
            return False

        if (
            frame_data.get("source_video_sha256")
            != provenance.get("source_video_sha256")
        ):
            return False

        indices.append(frame_index)

    if sorted(indices) != list(range(decoder_count)):
        return False

    if len(indices) != len(set(indices)):
        return False

    return True


def _download_best_video(
    url: str, out_dir: Path, video_id: str
) -> Tuple[Optional[Path], Dict]:
    """Download highest-resolution video stream (1080p preferred).

    Returns (video_path, provenance_dict) where provenance includes:
    - source_video_sha256
    - width, height, fps, duration_sec, codec, container
    - requested_resolution, selected_resolution, fallback_reason
    - yt_dlp_version, ffmpeg_version
    """
    yt_dlp = shutil.which("yt-dlp")
    provenance = {
        "requested_resolution": 1080,
        "selected_resolution": None,
        "format_id": None,
        "fallback_reason": None,
        "yt_dlp_version": _get_yt_dlp_version(),
        "ffmpeg_version": _get_ffmpeg_version(),
    }

    if not yt_dlp:
        provenance["fallback_reason"] = "yt-dlp not found on PATH"
        return None, provenance

    attempted_reasons = []
    cascade = [1080, 720, 480, 360]

    for ceiling in cascade:
        out_tmpl = str(out_dir / "video.%(ext)s")
        fmt_selector = f"bestvideo[height<={ceiling}]/best[height<={ceiling}]"

        cmd = [
            yt_dlp,
            "--format", fmt_selector,
            "--no-playlist",
            "--output", out_tmpl,
            "--print", "after_move:filepath",
            "--quiet",
            "--no-progress",
            "--js-runtimes", "node",
            "--",
            url,
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240, check=False)
        except subprocess.TimeoutExpired:
            attempted_reasons.append(f"height<={ceiling}: timed out")
            continue

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip().splitlines()
            reason = stderr_tail[-1] if stderr_tail else f"yt-dlp exited {proc.returncode}"
            attempted_reasons.append(f"height<={ceiling}: {reason}")
            for p in out_dir.glob("video.*"):
                p.unlink(missing_ok=True)
            continue

        downloaded = None
        for p in out_dir.glob("video.*"):
            if p.suffix.lower() in (".mp4", ".webm", ".mkv", ".avi", ".ts"):
                downloaded = p
                break

        if downloaded is None:
            attempted_reasons.append(f"height<={ceiling}: no output file produced")
            continue

        # Verify with ffprobe
        info = _ffprobe_video_info(downloaded)
        if info is None or not info.get("width") or not info.get("height"):
            attempted_reasons.append(
                f"height<={ceiling}: downloaded but ffprobe could not verify dimensions"
            )
            downloaded.unlink(missing_ok=True)
            continue

        provenance["selected_resolution"] = info["height"]
        provenance["width"] = info["width"]
        provenance["height"] = info["height"]
        provenance["fps"] = info.get("fps")
        provenance["codec"] = info.get("codec")
        provenance["container"] = downloaded.suffix.lstrip(".")
        provenance["duration_sec"] = info.get("duration_sec")
        provenance["source_video_sha256"] = _sha256_file(downloaded)

        if ceiling != 1080:
            prior = "; ".join(attempted_reasons) if attempted_reasons else "(none)"
            provenance["fallback_reason"] = (
                f"1080p unavailable; used <={ceiling}p. Prior attempts: {prior}"
            )

        return downloaded, provenance

    provenance["fallback_reason"] = (
        "All cascade steps failed: " + "; ".join(attempted_reasons)
        if attempted_reasons else "No cascade step attempted"
    )
    return None, provenance


def _ffprobe_video_info(path: Path) -> Optional[dict]:
    """Verify video with ffprobe. Returns {width, height, codec, fps, duration_sec}."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    cmd = [
        ffprobe, "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(proc.stdout)
    except Exception:
        return None

    info = {"duration_sec": None}
    fmt = data.get("format", {})
    if fmt.get("duration"):
        try:
            info["duration_sec"] = float(fmt["duration"])
        except (TypeError, ValueError):
            pass

    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            info["width"] = s.get("width")
            info["height"] = s.get("height")
            info["codec"] = s.get("codec_name")
            fps_raw = s.get("r_frame_rate", "")
            try:
                num, den = fps_raw.split("/")
                info["fps"] = round(float(num) / float(den), 3) if float(den) else None
            except Exception:
                info["fps"] = None
            if info["duration_sec"] is None and s.get("duration"):
                try:
                    info["duration_sec"] = float(s["duration"])
                except (TypeError, ValueError):
                    pass
            break

    return info if "width" in info else None


def acquire_exhaustive(
    source_url: str,
    video_id: str = None,
    force: bool = False,
    cache_key_extra: str = None,
) -> Dict:
    """Acquire every frame from a YouTube video exhaustively with decoder accounting.

    STEP 1 CLOSURE: This function must prove complete acquisition with authoritative
    decoder frame accounting via showinfo metadata.

    Args:
        source_url: YouTube URL
        video_id: Optional video_id (extracted if omitted)
        force: Force re-acquisition (ignore cache)
        cache_key_extra: Additional cache key components

    Returns dict with keys:
    - status: "SUCCESS" | "FAILED"
    - source_id: source identifier
    - num_frames_decoded: Total frames from decoder metadata
    - num_frames_verified: Frames passing decodability/hash checks
    - frames: [VisualFrameArtifact]
    - provenance: Video metadata
    - completion_status: Proof of exhaustive acquisition
    - error: Error message if status == "FAILED"
    """
    if video_id is None:
        video_id = extract_youtube_video_id(source_url)

    source_id = _source_id(source_url)
    cache_dir = _FRAMES_DIR / source_id / "exhaustive_cache"

    # Cache key includes: decoder_version, yt_dlp_version, resolution_policy, mode
    cache_key = hashlib.md5(
        f"exhaustive:ffmpeg:1080p_cascade:{_get_ffmpeg_version()}:{_get_yt_dlp_version()}:{cache_key_extra or ''}".encode()
    ).hexdigest()[:12]

    if not force:
        manifest_path = cache_dir / f"manifest_exhaustive_{cache_key}.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text())
                if _validate_cached_manifest(data, source_url, video_id, source_id, cache_key):
                    # Reload artifacts
                    artifacts = []
                    for frame_data in data.get("frames", []):
                        artifact = VisualFrameArtifact(
                            frame_id=frame_data["frame_id"],
                            source_url=source_url,
                            source_id=source_id,
                            video_id=video_id,
                            timestamp_sec=frame_data.get("presentation_timestamp_sec"),
                            artifact_path=frame_data["artifact_path"],
                            artifact_hash=frame_data.get("artifact_sha256"),
                            width=frame_data.get("width"),
                            height=frame_data.get("height"),
                            source_video_sha256=frame_data.get("source_video_sha256"),
                        )
                        artifacts.append(artifact)

                    completion = data.get("completion_status", {})
                    return {
                        "status": "SUCCESS",
                        "source_id": source_id,
                        "num_frames_decoded": completion.get("verified_frame_count", 0),
                        "num_frames_verified": completion.get("verified_frame_count", 0),
                        "frames": artifacts,
                        "provenance": data.get("provenance", {}),
                        "completion_status": completion,
                        "error": None,
                        "from_cache": True,
                    }
            except Exception:
                pass  # Fall through to re-acquire

    # Download video
    with tempfile.TemporaryDirectory(prefix="vlp1_exhaustive_") as tmp:
        tmp_dir = Path(tmp)
        video_path, provenance = _download_best_video(source_url, tmp_dir, video_id)

        if video_path is None:
            return {
                "status": "FAILED",
                "source_id": source_id,
                "num_frames_decoded": 0,
                "num_frames_verified": 0,
                "frames": [],
                "provenance": provenance,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": f"Video download failed: {provenance.get('fallback_reason')}",
                },
                "error": f"Video download failed: {provenance.get('fallback_reason')}",
            }

        # Verify with ffprobe
        info = _ffprobe_video_info(video_path)
        if not info:
            return {
                "status": "FAILED",
                "source_id": source_id,
                "num_frames_decoded": 0,
                "num_frames_verified": 0,
                "frames": [],
                "provenance": provenance,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": "ffprobe verification failed",
                },
                "error": "ffprobe could not verify downloaded video",
            }

        provenance.update(info)

        # Extract all frames in a temporary directory (isolated, no stale frame contamination)
        temp_extract_dir = tmp_dir / "frames_extracted"
        try:
            artifacts, completion_status = extract_all_frames(
                video_path,
                temp_extract_dir,
                source_id,
                provenance.get("source_video_sha256", ""),
            )
        except Exception as e:
            return {
                "status": "FAILED",
                "source_id": source_id,
                "num_frames_decoded": 0,
                "num_frames_verified": 0,
                "frames": [],
                "provenance": provenance,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": str(e),
                },
                "error": f"Frame extraction failed: {e}",
            }

        # FAIL CLOSED if incomplete
        if not completion_status.get("is_complete", False):
            return {
                "status": "FAILED",
                "source_id": source_id,
                "num_frames_decoded": completion_status.get("artifact_frame_count", 0),
                "num_frames_verified": completion_status.get("verified_frame_count", 0),
                "frames": [],
                "provenance": provenance,
                "completion_status": completion_status,
                "error": f"Acquisition incomplete: {completion_status.get('completion_reason')}",
            }

        # Set source URL and video_id in artifacts
        for artifact in artifacts:
            artifact.source_url = source_url
            artifact.video_id = video_id

        # PROMOTE to cache only after complete verification succeeds
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_frames_dir = cache_dir / f"frames_{cache_key}"

        # Move extracted frames to cache
        if cache_frames_dir.exists():
            shutil.rmtree(cache_frames_dir)
        cache_frames_dir.mkdir(parents=True, exist_ok=True)

        for artifact in artifacts:
            src_path = Path(artifact.artifact_path)
            dst_name = src_path.name
            dst_path = cache_frames_dir / dst_name
            shutil.copy2(src_path, dst_path)
            # Update artifact path to point to cached location
            artifact.artifact_path = str(dst_path)

        manifest_path = cache_dir / f"manifest_exhaustive_{cache_key}.json"

        # Re-verify hashes after promotion to cache
        manifest_data = {
            "source_url": source_url,
            "video_id": video_id,
            "source_id": source_id,
            "cache_key": cache_key,
            "acquisition_mode": "exhaustive",
            "decoder": "ffmpeg",
            "decoder_version": provenance.get("ffmpeg_version"),
            "frames": [
                {
                    "frame_id": f.frame_id,
                    "frame_index": int(f.frame_id.rsplit("_", 1)[-1]),
                    "presentation_timestamp_sec": f.timestamp_sec,
                    "artifact_path": f.artifact_path,
                    "artifact_sha256": f.artifact_hash,
                    "width": f.width,
                    "height": f.height,
                    "source_video_sha256": f.source_video_sha256,
                    "decode_status": "VERIFIED",
                }
                for f in artifacts
            ],
            "provenance": provenance,
            "completion_status": completion_status,
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        return {
            "status": "SUCCESS",
            "source_id": source_id,
            "num_frames_decoded": completion_status.get("verified_frame_count", 0),
            "num_frames_verified": completion_status.get("verified_frame_count", 0),
            "frames": artifacts,
            "provenance": provenance,
            "completion_status": completion_status,
            "error": None,
        }
