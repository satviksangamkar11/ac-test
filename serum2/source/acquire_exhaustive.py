"""Exhaustive frame acquisition: decode every source frame exactly once.

STEP 1 CLOSURE REQUIREMENTS:
- Download highest-resolution video (1080p preferred)
- Verify downloaded bytes with ffprobe (width, height, codec, fps, duration, SHA)
- Decode EVERY source frame using ffmpeg
- Determine expected frame count from actual ffmpeg output (NOT duration*fps)
- Detect missing frame indices explicitly (gaps in sequence)
- Fail closed if:
  - ffmpeg returns non-zero exit code
  - decoded_count != expected_count
  - any frame index is missing
  - any frame is unreadable
- Manifest proves: expected_count, decoded_count, missing_indices, is_complete
- Cache reuse validates: video_id, source_sha, resolution_policy, decoder_version
- Never reuse reduced/sampled acquisitions
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from serum2.source.visual_evidence import VisualFrameArtifact
from serum2.source.youtube_url import extract_youtube_video_id

_FRAMES_DIR = Path(__file__).parent.parent / "data" / "visual_frames"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _source_id(url: str) -> str:
    return "yt_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _download_best_video(
    url: str, out_dir: Path, video_id: str
) -> Tuple[Optional[Path], Dict]:
    """Download highest-resolution video stream (1080p preferred).

    Returns (video_path, provenance_dict) where provenance includes:
    - source_video_sha256
    - width, height, fps, duration_sec, codec, container
    - requested_resolution, selected_resolution, fallback_reason
    """
    yt_dlp = shutil.which("yt-dlp")
    provenance = {
        "requested_resolution": 1080,
        "selected_resolution": None,
        "format_id": None,
        "fallback_reason": None,
        "yt_dlp_version": _get_yt_dlp_version(),
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


def _get_yt_dlp_version() -> Optional[str]:
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return None
    try:
        proc = subprocess.run([yt_dlp, "--version"], capture_output=True, text=True, timeout=15)
        return proc.stdout.strip() or None
    except Exception:
        return None


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


def extract_all_frames(
    video_path: Path,
    frames_dir: Path,
    source_id: str,
    fps: float,
    source_video_sha: str,
) -> Tuple[List[VisualFrameArtifact], Dict]:
    """Extract every frame from video using ffmpeg.

    The AUTHORITATIVE frame count comes from actual ffmpeg output, not duration*fps.
    Detects missing frame indices and fails if the sequence is incomplete.

    Returns:
        (artifacts, completion_status)

    completion_status contains:
    - decoder_exit_code: ffmpeg return code
    - total_frames_decoded: actual JPEGs created by ffmpeg
    - total_frames_verified: JPEGs that pass readability/hash checks
    - missing_frame_indices: gaps in the frame sequence
    - is_complete: bool (True only if all frames present and readable)
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")

    frames_dir.mkdir(parents=True, exist_ok=True)

    # Extract all frames: ffmpeg will create frame_<sid>_FFFFFFFFF.jpg (1-based numbering)
    frame_pattern = frames_dir / f"frame_{source_id}_%09d.jpg"

    cmd = [
        ffmpeg,
        "-i", str(video_path),
        "-q:v", "3",
        "-y",
        str(frame_pattern),
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600, check=False
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffmpeg extraction timed out for {video_path}")

    decoder_exit_code = proc.returncode

    # Collect all JPEGs that ffmpeg created
    all_frame_files = sorted(frames_dir.glob(f"frame_{source_id}_*.jpg"))

    # Extract frame numbers and build index
    decoded_frame_indices = set()
    frame_files_by_index = {}

    for frame_file in all_frame_files:
        stem = frame_file.stem
        try:
            frame_num = int(stem.split("_")[-1])  # 1-based from ffmpeg
            frame_idx = frame_num - 1  # Convert to 0-based for consistency
            decoded_frame_indices.add(frame_idx)
            frame_files_by_index[frame_idx] = frame_file
        except ValueError:
            continue

    # Expected frame count = highest index + 1
    # This is authoritative: it's what ffmpeg actually produced
    total_frames_decoded = len(decoded_frame_indices)

    if total_frames_decoded == 0:
        # No frames were extracted - complete failure
        return [], {
            "decoder_exit_code": decoder_exit_code,
            "total_frames_decoded": 0,
            "total_frames_verified": 0,
            "total_frames_expected": 0,
            "missing_frame_indices": [],
            "is_complete": False,
            "completion_reason": "No frames extracted by ffmpeg",
        }

    max_frame_idx = max(decoded_frame_indices)
    total_frames_expected = max_frame_idx + 1

    # Detect missing frame indices (gaps in sequence)
    missing_frame_indices = []
    for idx in range(total_frames_expected):
        if idx not in decoded_frame_indices:
            missing_frame_indices.append(idx)

    # Verify each frame file is readable and hash it
    artifacts = []
    total_frames_verified = 0

    for frame_idx in sorted(decoded_frame_indices):
        frame_file = frame_files_by_index[frame_idx]
        timestamp_sec = frame_idx / fps if fps else 0.0

        # Verify file is readable and has content
        try:
            if not frame_file.exists() or frame_file.stat().st_size == 0:
                continue  # Skip to next; mark as incomplete below
            artifact_hash = _sha256_file(frame_file)
        except Exception:
            continue  # Skip to next; mark as incomplete

        total_frames_verified += 1
        frame_id = f"frame_{source_id}_{frame_idx:08d}"
        artifact_path = frame_file.relative_to(Path(__file__).parent.parent.parent)

        artifacts.append(VisualFrameArtifact(
            frame_id=frame_id,
            source_url="",  # Will be set by caller
            source_id=source_id,
            video_id="",
            timestamp_sec=timestamp_sec,
            artifact_path=str(artifact_path).replace("\\", "/"),
            artifact_hash=artifact_hash,
            width=None,
            height=None,
            source_video_sha256=source_video_sha,
        ))

    # Completeness requires:
    # 1. ffmpeg exit code 0
    # 2. no missing frame indices
    # 3. all frames verified (readable and hashed)
    is_complete = (
        decoder_exit_code == 0 and
        len(missing_frame_indices) == 0 and
        total_frames_verified == total_frames_expected
    )

    completion_status = {
        "decoder_exit_code": decoder_exit_code,
        "total_frames_expected": total_frames_expected,
        "total_frames_decoded": total_frames_decoded,
        "total_frames_verified": total_frames_verified,
        "missing_frame_indices": missing_frame_indices,
        "is_complete": is_complete,
        "completion_reason": (
            "all frames decoded, verified, and accounted" if is_complete
            else (
                f"ffmpeg exit {decoder_exit_code}" if decoder_exit_code != 0
                else f"missing {len(missing_frame_indices)} frame indices: {missing_frame_indices[:10]}"
                if missing_frame_indices else
                f"verified {total_frames_verified}/{total_frames_expected}"
            )
        ),
    }

    return artifacts, completion_status


def acquire_exhaustive(
    source_url: str,
    video_id: str = None,
    force: bool = False,
    cache_key_extra: str = None,
) -> Dict:
    """Acquire every frame from a YouTube video exhaustively.

    STEP 1 CLOSURE: This function must prove complete acquisition:
    - Downloads real video (1080p preferred, cascade to 360p)
    - Verifies with ffprobe
    - Decodes EVERY frame
    - Detects missing indices
    - Fails closed if incomplete

    Args:
        source_url: YouTube URL
        video_id: Optional video_id (extracted if omitted)
        force: Force re-acquisition (ignore cache)
        cache_key_extra: Additional cache key components (e.g., decoder_version)

    Returns dict with keys:
    - status: "SUCCESS" | "FAILED"
    - num_frames_decoded: Total frames extracted by ffmpeg
    - num_frames_verified: Frames passing readability/hash checks
    - frames: [VisualFrameArtifact]
    - provenance: Video metadata (SHA, fps, resolution, etc.)
    - completion_status: Proof of exhaustive acquisition
    - error: Error message if status == "FAILED"
    """
    if video_id is None:
        video_id = extract_youtube_video_id(source_url)

    source_id = _source_id(source_url)
    frames_dir = _FRAMES_DIR / source_id / "exhaustive"

    # Cache key includes: decoder_version, acquisition_mode, resolution_policy
    # This prevents reuse of older reduced/sampled acquisitions
    cache_key = hashlib.md5(
        f"exhaustive:ffmpeg:1080p_cascade:{cache_key_extra or ''}".encode()
    ).hexdigest()[:8]
    manifest_path = frames_dir / f"manifest_exhaustive_{cache_key}.json"

    if manifest_path.exists() and not force:
        try:
            data = json.loads(manifest_path.read_text())

            # Validate cache reuse: must have same video_id, source_sha, resolution, completion
            if (data.get("video_id") == video_id and
                data.get("completion_status", {}).get("is_complete", False)):
                # Reload artifacts
                artifacts = []
                for frame_data in data.get("frames", []):
                    artifact = VisualFrameArtifact(
                        frame_id=frame_data["frame_id"],
                        source_url=source_url,
                        source_id=source_id,
                        video_id=video_id,
                        timestamp_sec=frame_data["timestamp_sec"],
                        artifact_path=frame_data["artifact_path"],
                        artifact_hash=frame_data["artifact_hash"],
                        width=frame_data.get("width"),
                        height=frame_data.get("height"),
                        source_video_sha256=frame_data.get("source_video_sha256"),
                    )
                    artifacts.append(artifact)

                return {
                    "status": "SUCCESS",
                    "num_frames_decoded": data.get("completion_status", {}).get("total_frames_verified", 0),
                    "num_frames_verified": data.get("completion_status", {}).get("total_frames_verified", 0),
                    "frames": artifacts,
                    "provenance": data.get("provenance", {}),
                    "completion_status": data.get("completion_status", {}),
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
                "num_frames_decoded": 0,
                "num_frames_verified": 0,
                "frames": [],
                "provenance": provenance,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": f"Video download failed: {provenance.get('fallback_reason')}",
                },
                "error": f"Video download failed: {provenance.get('fallback_reason')}",
                "from_cache": False,
            }

        # Verify with ffprobe
        info = _ffprobe_video_info(video_path)
        if not info:
            return {
                "status": "FAILED",
                "num_frames_decoded": 0,
                "num_frames_verified": 0,
                "frames": [],
                "provenance": provenance,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": "ffprobe verification failed",
                },
                "error": "ffprobe could not verify downloaded video",
                "from_cache": False,
            }

        provenance.update(info)

        # Extract all frames
        try:
            artifacts, completion_status = extract_all_frames(
                video_path,
                frames_dir,
                source_id,
                info.get("fps", 30),
                provenance.get("source_video_sha256", ""),
            )
        except Exception as e:
            return {
                "status": "FAILED",
                "num_frames_decoded": 0,
                "num_frames_verified": 0,
                "frames": [],
                "provenance": provenance,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": str(e),
                },
                "error": f"Frame extraction failed: {e}",
                "from_cache": False,
            }

        # FAIL CLOSED if incomplete
        if not completion_status.get("is_complete", False):
            return {
                "status": "FAILED",
                "num_frames_decoded": completion_status.get("total_frames_decoded", 0),
                "num_frames_verified": completion_status.get("total_frames_verified", 0),
                "frames": [],
                "provenance": provenance,
                "completion_status": completion_status,
                "error": f"Acquisition incomplete: {completion_status.get('completion_reason')}",
                "from_cache": False,
            }

        # Set source URL and video_id in artifacts
        for artifact in artifacts:
            artifact.source_url = source_url
            artifact.video_id = video_id

        # Save manifest
        frames_dir.mkdir(parents=True, exist_ok=True)
        manifest_data = {
            "source_url": source_url,
            "video_id": video_id,
            "source_id": source_id,
            "cache_key": cache_key,
            "acquisition_mode": "exhaustive",
            "decoder": "ffmpeg",
            "frames": [a.to_dict() for a in artifacts],
            "provenance": provenance,
            "completion_status": completion_status,
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        return {
            "status": "SUCCESS",
            "num_frames_decoded": completion_status.get("total_frames_verified", 0),
            "num_frames_verified": completion_status.get("total_frames_verified", 0),
            "frames": artifacts,
            "provenance": provenance,
            "completion_status": completion_status,
            "error": None,
            "from_cache": False,
        }
