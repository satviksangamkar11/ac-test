"""Exhaustive frame acquisition: decode every source frame exactly once.

This module replaces the sampling-based approach with deterministic, exhaustive
single-pass frame extraction. Every source frame is decoded and tracked.
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

    Returns (video_path, provenance_dict).
    Provenance includes: source_video_sha256, width, height, fps, duration_sec,
    container, codec, requested_resolution, selected_resolution, fallback_reason.
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
    duration_sec: float,
    source_video_sha: str,
) -> Tuple[List[VisualFrameArtifact], List[Dict]]:
    """Extract every frame from video using ffmpeg.

    Returns:
        (list of successfully extracted VisualFrameArtifact, list of failed frame records)
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")

    frames_dir.mkdir(parents=True, exist_ok=True)

    # Calculate total frames
    total_frames = int(duration_sec * fps) if fps and duration_sec else 0
    if total_frames <= 0:
        raise ValueError(f"Cannot determine frame count: fps={fps}, duration={duration_sec}")

    # Extract all frames using ffmpeg
    # Use %d for frame numbering (1-based by default)
    frame_pattern = frames_dir / f"frame_{source_id}_%09d.jpg"

    cmd = [
        ffmpeg,
        "-i", str(video_path),
        "-q:v", "3",  # JPEG quality
        "-y",  # overwrite
        str(frame_pattern),
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600, check=False
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffmpeg extraction timed out for {video_path}")

    # Collect extracted frames
    artifacts = []
    failed_frames = []

    for frame_file in sorted(frames_dir.glob(f"frame_{source_id}_*.jpg")):
        # Extract frame number from filename
        stem = frame_file.stem
        try:
            frame_num = int(stem.split("_")[-1])  # 1-based from ffmpeg
        except ValueError:
            continue

        frame_idx = frame_num - 1  # Convert to 0-based
        timestamp_sec = frame_idx / fps if fps else 0.0

        # Verify frame exists and is readable
        if not frame_file.exists() or frame_file.stat().st_size == 0:
            failed_frames.append({
                "frame_index": frame_idx,
                "frame_number": frame_num,
                "timestamp_sec": timestamp_sec,
                "status": "UNREADABLE",
                "reason": "File empty or missing",
            })
            continue

        try:
            artifact_hash = _sha256_file(frame_file)
        except Exception as e:
            failed_frames.append({
                "frame_index": frame_idx,
                "frame_number": frame_num,
                "timestamp_sec": timestamp_sec,
                "status": "UNREADABLE",
                "reason": f"Hash computation failed: {e}",
            })
            continue

        frame_id = f"frame_{source_id}_{frame_idx:08d}"
        artifact_path = frame_file.relative_to(Path(__file__).parent.parent.parent)

        artifacts.append(VisualFrameArtifact(
            frame_id=frame_id,
            source_url="",  # Will be set by caller
            source_id=source_id,
            video_id="",  # Will be set by caller
            timestamp_sec=timestamp_sec,
            artifact_path=str(artifact_path).replace("\\", "/"),
            artifact_hash=artifact_hash,
            width=None,  # Could be set via ffprobe if needed
            height=None,
            source_video_sha256=source_video_sha,
        ))

    return artifacts, failed_frames


def acquire_exhaustive(source_url: str, video_id: str = None, force: bool = False) -> Dict:
    """Acquire every frame from a YouTube video exhaustively.

    Returns:
        {
            "status": "SUCCESS" | "FAILED",
            "num_frames_decoded": int,
            "num_frames_failed": int,
            "frames": [VisualFrameArtifact],
            "failed_frames": [dict],
            "provenance": {video metadata},
            "error": Optional[str],
        }
    """
    if video_id is None:
        video_id = extract_youtube_video_id(source_url)

    source_id = _source_id(source_url)
    frames_dir = _FRAMES_DIR / source_id / "exhaustive"

    # Check for existing extraction (skip if exists and not forced)
    manifest_path = frames_dir / "manifest_exhaustive.json"
    if manifest_path.exists() and not force:
        try:
            data = json.loads(manifest_path.read_text())
            # Reload artifacts from disk
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
                "num_frames_decoded": len(artifacts),
                "num_frames_failed": len(data.get("failed_frames", [])),
                "frames": artifacts,
                "failed_frames": data.get("failed_frames", []),
                "provenance": data.get("provenance", {}),
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
                "num_frames_failed": 0,
                "frames": [],
                "failed_frames": [],
                "provenance": provenance,
                "error": f"Video download failed: {provenance.get('fallback_reason')}",
            }

        # Verify video with ffprobe
        info = _ffprobe_video_info(video_path)
        if not info:
            return {
                "status": "FAILED",
                "num_frames_decoded": 0,
                "num_frames_failed": 0,
                "frames": [],
                "failed_frames": [],
                "provenance": provenance,
                "error": "ffprobe could not verify downloaded video",
            }

        provenance.update(info)

        # Extract all frames
        try:
            artifacts, failed_frames = extract_all_frames(
                video_path,
                frames_dir,
                source_id,
                info.get("fps", 30),
                info.get("duration_sec", 0),
                provenance.get("source_video_sha256", ""),
            )
        except Exception as e:
            return {
                "status": "FAILED",
                "num_frames_decoded": 0,
                "num_frames_failed": 0,
                "frames": [],
                "failed_frames": [],
                "provenance": provenance,
                "error": f"Frame extraction failed: {e}",
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
            "num_frames_decoded": len(artifacts),
            "num_frames_failed": len(failed_frames),
            "frames": [a.to_dict() for a in artifacts],
            "failed_frames": failed_frames,
            "provenance": provenance,
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        return {
            "status": "SUCCESS" if artifacts else "FAILED",
            "num_frames_decoded": len(artifacts),
            "num_frames_failed": len(failed_frames),
            "frames": artifacts,
            "failed_frames": failed_frames,
            "provenance": provenance,
            "error": None if artifacts else "No frames extracted",
            "from_cache": False,
        }
