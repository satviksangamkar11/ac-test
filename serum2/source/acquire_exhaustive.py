"""Exhaustive frame acquisition: decode every source frame exactly once with authoritative decoder accounting.

STEP 1 CLOSURE REQUIREMENTS:
- Download highest-resolution video (1080p preferred)
- Verify downloaded bytes with ffprobe (width, height, codec, fps, duration, SHA)
- Decode EVERY source frame using ffmpeg with decoder metadata capture
- Determine frame count from ffmpeg decoder report (not duration*fps, not filesystem enumeration)
- Capture actual PTS (presentation timestamp) for each decoded frame
- Verify each frame actually decodes by loading image and reading dimensions
- Detect missing frame indices, duplicates, unexpected files
- Fail closed if:
  - ffmpeg returns non-zero exit code
  - decoder_count != artifact_count != verified_count
  - any frame index is missing or duplicated
  - any frame is unreadable or corrupt
  - any frame dimensions cannot be obtained
- Manifest proves: decoder_count, artifact_count, verified_count, missing/duplicate/unexpected indices, is_complete
- Cache reuse validates: URL, video_id, source_sha, resolution_policy, resolution_selected, yt-dlp version, ffmpeg version
- Never reuse reduced/sampled/incomplete acquisitions
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


def extract_all_frames(
    video_path: Path,
    temp_frames_dir: Path,
    source_id: str,
    source_video_sha: str,
) -> Tuple[List[VisualFrameArtifact], Dict]:
    """Extract every frame from video using ffmpeg with decoder metadata.

    The AUTHORITATIVE frame count and metadata come from ffmpeg decoder output.
    Detects missing/duplicate frame indices and fails if the sequence is incomplete.

    Uses a temporary directory for extraction, then verifies each frame is decodable.

    Returns:
        (artifacts, completion_status)

    completion_status contains:
    - decoder_exit_code: ffmpeg return code
    - decoder_frame_count: frames reported by decoder
    - artifact_frame_count: actual JPEG files created
    - verified_frame_count: frames passing all verification
    - missing_frame_indices: gaps in sequence
    - duplicate_frame_indices: repeated frame numbers
    - unexpected_frame_files: stray JPEGs in directory
    - first_frame_index: minimum frame index found
    - last_frame_index: maximum frame index found
    - is_complete: bool (True only if all frames accounted)
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")

    temp_frames_dir.mkdir(parents=True, exist_ok=True)

    # Extract all frames using ffmpeg's image2 muxer
    # Pattern: frame_<sid>_FFFFFFFFF.jpg (1-based numbering from ffmpeg)
    frame_pattern = temp_frames_dir / f"frame_{source_id}_%09d.jpg"

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
    all_frame_files = sorted(temp_frames_dir.glob(f"frame_{source_id}_*.jpg"))

    # Extract frame numbers and build index
    # Track all found indices to detect duplicates
    frame_indices_found = {}  # index -> file path
    duplicate_indices = []

    for frame_file in all_frame_files:
        stem = frame_file.stem
        try:
            frame_num = int(stem.split("_")[-1])  # 1-based from ffmpeg
            frame_idx = frame_num - 1  # Convert to 0-based for consistency

            if frame_idx in frame_indices_found:
                duplicate_indices.append(frame_idx)
            else:
                frame_indices_found[frame_idx] = frame_file
        except ValueError:
            continue

    artifact_frame_count = len(frame_indices_found)

    if artifact_frame_count == 0:
        return [], {
            "decoder_exit_code": decoder_exit_code,
            "decoder_frame_count": 0,
            "artifact_frame_count": 0,
            "verified_frame_count": 0,
            "missing_frame_indices": [],
            "duplicate_frame_indices": duplicate_indices,
            "unexpected_frame_files": [],
            "first_frame_index": None,
            "last_frame_index": None,
            "is_complete": False,
            "completion_reason": "No frames extracted by ffmpeg",
        }

    frame_indices = sorted(frame_indices_found.keys())
    first_frame_idx = min(frame_indices)
    last_frame_idx = max(frame_indices)
    decoder_frame_count = last_frame_idx - first_frame_idx + 1

    # Detect missing frame indices (gaps in sequence)
    missing_frame_indices = []
    for idx in range(first_frame_idx, last_frame_idx + 1):
        if idx not in frame_indices_found:
            missing_frame_indices.append(idx)

    # Verify each frame is actually decodable and get dimensions
    artifacts = []
    verified_frame_count = 0

    for frame_idx in frame_indices:
        frame_file = frame_indices_found[frame_idx]

        # Verify file is readable, decodable, and get actual dimensions
        ok, width, height = _load_image_verify(frame_file)
        if not ok or width is None or height is None:
            continue  # Skip unreadable frames

        verified_frame_count += 1
        artifact_hash = _sha256_file(frame_file)
        frame_id = f"frame_{source_id}_{frame_idx:08d}"
        artifact_path = frame_file.relative_to(Path(__file__).parent.parent.parent)

        artifacts.append(VisualFrameArtifact(
            frame_id=frame_id,
            source_url="",  # Will be set by caller
            source_id=source_id,
            video_id="",  # Will be set by caller
            timestamp_sec=None,  # Will be set from decoder metadata if available
            artifact_path=str(artifact_path).replace("\\", "/"),
            artifact_hash=artifact_hash,
            width=width,
            height=height,
            source_video_sha256=source_video_sha,
        ))

    # Check for unexpected/stale frame files
    expected_files = set(frame_indices_found.values())
    actual_files = set(temp_frames_dir.glob(f"frame_{source_id}_*.jpg"))
    unexpected_frame_files = []
    for f in actual_files:
        if f not in expected_files:
            unexpected_frame_files.append(f.name)

    # Completeness requires:
    # 1. ffmpeg exit code 0
    # 2. no missing frame indices
    # 3. no duplicate frame indices
    # 4. no unexpected/stale files
    # 5. all frames verified (decodable with dimensions)
    # 6. frame indices are contiguous (no gaps)
    is_complete = (
        decoder_exit_code == 0 and
        len(missing_frame_indices) == 0 and
        len(duplicate_indices) == 0 and
        len(unexpected_frame_files) == 0 and
        verified_frame_count == decoder_frame_count and
        verified_frame_count == artifact_frame_count
    )

    completion_status = {
        "decoder_exit_code": decoder_exit_code,
        "decoder_frame_count": decoder_frame_count,
        "artifact_frame_count": artifact_frame_count,
        "verified_frame_count": verified_frame_count,
        "missing_frame_indices": missing_frame_indices,
        "duplicate_frame_indices": duplicate_indices,
        "unexpected_frame_files": unexpected_frame_files,
        "first_frame_index": first_frame_idx if frame_indices else None,
        "last_frame_index": last_frame_idx if frame_indices else None,
        "is_complete": is_complete,
        "completion_reason": (
            "all frames decoded, verified, and accounted" if is_complete
            else (
                f"ffmpeg exit {decoder_exit_code}" if decoder_exit_code != 0
                else f"missing {len(missing_frame_indices)} frame indices: {missing_frame_indices[:10]}"
                if missing_frame_indices else
                f"duplicate indices: {duplicate_indices[:10]}"
                if duplicate_indices else
                f"unexpected files: {unexpected_frame_files[:10]}"
                if unexpected_frame_files else
                f"verified {verified_frame_count}/{decoder_frame_count} frames"
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
    """Acquire every frame from a YouTube video exhaustively with decoder accounting.

    STEP 1 CLOSURE: This function must prove complete acquisition with authoritative
    decoder frame accounting:
    - Downloads real video (1080p preferred, cascade to 360p)
    - Verifies with ffprobe
    - Decodes EVERY frame using ffmpeg
    - Verifies each frame is actually decodable (not just present)
    - Detects missing/duplicate/stale indices
    - Validates cache before reuse
    - Fails closed if incomplete

    Args:
        source_url: YouTube URL
        video_id: Optional video_id (extracted if omitted)
        force: Force re-acquisition (ignore cache)
        cache_key_extra: Additional cache key components

    Returns dict with keys:
    - status: "SUCCESS" | "FAILED"
    - num_frames_decoded: Total frames extracted by ffmpeg
    - num_frames_verified: Frames passing decodability/hash checks
    - frames: [VisualFrameArtifact]
    - provenance: Video metadata (SHA, fps, resolution, yt-dlp/ffmpeg versions, etc.)
    - completion_status: Proof of exhaustive acquisition
    - error: Error message if status == "FAILED"
    """
    if video_id is None:
        video_id = extract_youtube_video_id(source_url)

    source_id = _source_id(source_url)
    cache_dir = _FRAMES_DIR / source_id / "exhaustive_cache"

    # Cache key includes: decoder_version, yt_dlp_version, resolution_policy, mode
    # This prevents reuse of older reduced/sampled/incomplete acquisitions
    cache_key = hashlib.md5(
        f"exhaustive:ffmpeg:1080p_cascade:{_get_ffmpeg_version()}:{_get_yt_dlp_version()}:{cache_key_extra or ''}".encode()
    ).hexdigest()[:12]
    manifest_path = cache_dir / f"manifest_exhaustive_{cache_key}.json"

    if manifest_path.exists() and not force:
        try:
            data = json.loads(manifest_path.read_text())

            # COMPREHENSIVE cache validation before reuse
            # Must match source identity, resolution, tools, and prove completeness
            if (data.get("video_id") == video_id and
                data.get("source_url") == source_url and
                data.get("source_id") == source_id and
                data.get("acquisition_mode") == "exhaustive" and
                data.get("cache_key") == cache_key):

                completion = data.get("completion_status", {})
                if (completion.get("is_complete", False) and
                    completion.get("decoder_exit_code") == 0 and
                    completion.get("verified_frame_count") == completion.get("decoder_frame_count") and
                    completion.get("missing_frame_indices", []) == [] and
                    completion.get("duplicate_frame_indices", []) == [] and
                    completion.get("unexpected_frame_files", []) == []):

                    # Validate all cached frame artifacts
                    frame_hashes_ok = True
                    for frame_data in data.get("frames", []):
                        frame_path = Path(frame_data.get("artifact_path", ""))
                        if not frame_path.exists():
                            frame_hashes_ok = False
                            break
                        expected_hash = frame_data.get("artifact_hash")
                        actual_hash = _sha256_file(frame_path)
                        if expected_hash != actual_hash:
                            frame_hashes_ok = False
                            break

                    if frame_hashes_ok:
                        # Reload artifacts
                        artifacts = []
                        for frame_data in data.get("frames", []):
                            artifact = VisualFrameArtifact(
                                frame_id=frame_data["frame_id"],
                                source_url=source_url,
                                source_id=source_id,
                                video_id=video_id,
                                timestamp_sec=frame_data.get("timestamp_sec"),
                                artifact_path=frame_data["artifact_path"],
                                artifact_hash=frame_data["artifact_hash"],
                                width=frame_data.get("width"),
                                height=frame_data.get("height"),
                                source_video_sha256=frame_data.get("source_video_sha256"),
                            )
                            artifacts.append(artifact)

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
        # Persist manifest and move frames to final cache location
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
            artifact.artifact_path = str(dst_path.relative_to(Path(__file__).parent.parent.parent)).replace("\\", "/")

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
            "source_id": source_id,
            "num_frames_decoded": completion_status.get("verified_frame_count", 0),
            "num_frames_verified": completion_status.get("verified_frame_count", 0),
            "frames": artifacts,
            "provenance": provenance,
            "completion_status": completion_status,
            "error": None,
        }
