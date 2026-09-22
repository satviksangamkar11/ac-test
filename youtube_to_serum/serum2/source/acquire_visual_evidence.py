"""Frame acquisition for visual evidence.

Uses yt-dlp to download storyboard (mhtml) and ffmpeg to extract frames.
All frames are hashed for provenance.

Security:
- Source URL is validated against a simple pattern before use
- No untrusted data is interpolated into shell commands; all yt-dlp/ffmpeg
  args are passed as list items, never via shell=True
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from serum2.source.visual_evidence import (
    VisualEvidenceBundle, VisualFrameArtifact, TranscriptSufficiency,
)
from serum2.source.youtube_url import extract_youtube_video_id

# Where frames are stored (relative to repo root)
_FRAMES_DIR = Path(__file__).parent.parent / "data" / "visual_frames"

# VLP-1 timestamp strategy: every 45 seconds, up to 8 frames
_DEFAULT_SAMPLE_INTERVAL_SEC = 45.0
_DEFAULT_MAX_FRAMES = 8


def _validate_youtube_url(url: str) -> Tuple[str, str]:
    """Validate URL and extract video_id. Returns (url, video_id).
    Raises ValueError on invalid input."""
    return url, extract_youtube_video_id(url)


def _find_ffmpeg() -> Optional[str]:
    """Return path to ffmpeg binary or None."""
    return shutil.which("ffmpeg")


def _source_id(url: str) -> str:
    return "yt_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


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
    """Return real, ffprobe-verified {width, height, codec, fps, duration_sec}.
    Never trust yt-dlp's format metadata alone — this re-derives from the
    actual downloaded bytes."""
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


# Resolution cascade: try each ceiling in order, take the best real stream
# at or below it (video-only preferred; falls back to muxed).
_RESOLUTION_CASCADE = [1080, 720, 480, 360]


def _download_best_video(
    url: str, out_dir: Path, video_id: str,
) -> Tuple[Optional[Path], dict]:
    """Download the highest-resolution real video stream available, trying
    the resolution cascade in order. Returns (path_or_None, provenance dict).

    provenance always contains: requested_resolution, selected_resolution,
    fallback_reason, format_id, yt_dlp_version. selected_resolution/format_id
    are None if every cascade step failed.
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
    for ceiling in _RESOLUTION_CASCADE:
        out_tmpl = str(out_dir / "video.%(ext)s")
        # Prefer video-only (audio not needed for frame extraction), then
        # muxed, at or below this ceiling, maximizing quality.
        fmt_selector = (
            f"bestvideo[height<={ceiling}]/best[height<={ceiling}]"
        )
        cmd = [
            yt_dlp,
            "--format", fmt_selector,
            "--no-playlist",
            "--output", out_tmpl,
            "--print", "after_move:filepath",
            "--quiet",
            "--no-progress",
            "--",
            url,
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=240, check=False
            )
        except subprocess.TimeoutExpired:
            attempted_reasons.append("height<=%d: timed out" % ceiling)
            continue
        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip().splitlines()
            reason = stderr_tail[-1] if stderr_tail else "yt-dlp exited %d" % proc.returncode
            attempted_reasons.append("height<=%d: %s" % (ceiling, reason))
            for p in out_dir.glob("video.*"):
                p.unlink(missing_ok=True)
            continue

        downloaded = None
        for p in out_dir.glob("video.*"):
            if p.suffix.lower() in (".mp4", ".webm", ".mkv", ".avi", ".ts"):
                downloaded = p
                break
        if downloaded is None:
            attempted_reasons.append("height<=%d: no output file produced" % ceiling)
            continue

        # Validate real dimensions — never trust format metadata alone.
        info = _ffprobe_video_info(downloaded)
        if info is None or not info.get("width") or not info.get("height"):
            attempted_reasons.append(
                "height<=%d: downloaded but ffprobe could not verify dimensions" % ceiling
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
            provenance["fallback_reason"] = (
                "1080p unavailable; used <=%dp real stream. Prior attempts: %s"
                % (ceiling, "; ".join(attempted_reasons)) if attempted_reasons else
                "Selected the first working cascade step (<=%dp)." % ceiling
            )
        return downloaded, provenance

    provenance["fallback_reason"] = (
        "All real-video cascade steps failed: " + "; ".join(attempted_reasons)
        if attempted_reasons else "No cascade step attempted"
    )
    return None, provenance


def _get_video_duration(video_path: Path, ffmpeg: str) -> Optional[float]:
    """Return video duration in seconds using ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # Try next to ffmpeg
        ffprobe = str(Path(ffmpeg).parent / "ffprobe")
        if not Path(ffprobe).exists():
            return None
    cmd = [
        ffprobe, "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(proc.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return None


def _extract_frame(
    video_path: Path,
    timestamp_sec: float,
    out_path: Path,
    ffmpeg: str,
) -> bool:
    """Extract one frame at timestamp_sec from video_path to out_path (JPEG)."""
    cmd = [
        ffmpeg,
        "-ss", "%.3f" % timestamp_sec,  # seek first (fast seek)
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "3",            # JPEG quality
        "-y",                   # overwrite
        str(out_path),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=30, check=False
        )
        return proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Storyboard acquisition — used when the video stream is unavailable
# ---------------------------------------------------------------------------

def _get_storyboard_format_id(video_id: str) -> Optional[str]:
    """Find best storyboard format ID by inspecting yt-dlp formats."""
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return None
    cmd = [yt_dlp, "--dump-json", "--no-download",
           f"https://www.youtube.com/watch?v={video_id}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        if proc.returncode != 0:
            return None
        data = None
        for line in reversed(proc.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                try:
                    data = json.loads(line)
                    break
                except Exception:
                    continue
        if not data:
            return None
        formats = data.get("formats", [])
        sbs = sorted(
            [f for f in formats if "storyboard" in f.get("format_note", "").lower()],
            key=lambda x: x.get("width", 0) * x.get("height", 0),
            reverse=True,
        )
        if not sbs:
            return None
        # Prefer sb0 — highest per-frame resolution (320x180), needed to
        # read Serum UI controls; sb1/sb2/sb3 trade resolution for more
        # frames per sheet but are too small (down to 48x27) to be useful.
        format_ids = [f["format_id"] for f in sbs]
        for fid in ("sb0", "sb1", "sb2", "sb3"):
            if fid in format_ids:
                return fid
        return sbs[0]["format_id"]
    except Exception:
        return None


def _get_storyboard_grid(video_id: str, format_id: str) -> Tuple[int, int]:
    """Return (cols, rows) for a storyboard format from yt-dlp JSON."""
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return 3, 3
    try:
        proc = subprocess.run(
            [yt_dlp, "--dump-json", "--no-download",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=60, check=False
        )
        for line in reversed(proc.stdout.strip().split('\n')):
            if line.strip().startswith('{'):
                try:
                    data = json.loads(line)
                    for f in data.get("formats", []):
                        if f.get("format_id") == format_id:
                            return f.get("columns", 3), f.get("rows", 3)
                    break
                except Exception:
                    continue
    except Exception:
        pass
    return 3, 3


def _parse_mhtml_storyboard(
    mhtml_path: Path,
    tmp_dir: Path,
) -> Tuple[List[Tuple[Path, float, float]], Optional[str]]:
    """Parse mhtml storyboard. Returns list of (jpeg_path, start_sec, end_sec)."""
    import email

    try:
        # Must read as bytes — mhtml embeds raw binary JPEG data, and
        # decoding as text would corrupt it (replacement chars for
        # every non-UTF-8 byte).
        data = mhtml_path.read_bytes()
        msg = email.message_from_bytes(data)
        parts = list(msg.walk())

        # Parse timing from HTML part
        slide_timings: List[Tuple[float, float]] = []
        for p in parts:
            if p.get_content_type() == "text/html":
                html = (p.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
                for m in re.finditer(
                    r"Slide #\d+: (\d+):(\d+):(\d+),(\d+)\s*[–-]\s*(\d+):(\d+):(\d+),(\d+)",
                    html,
                ):
                    h1, m1, s1, ms1 = (
                        int(m.group(1)), int(m.group(2)),
                        int(m.group(3)), int(m.group(4)),
                    )
                    h2, m2, s2, ms2 = (
                        int(m.group(5)), int(m.group(6)),
                        int(m.group(7)), int(m.group(8)),
                    )
                    start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
                    end   = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
                    slide_timings.append((start, end))
                break

        # Extract JPEG sprite sheets
        jpeg_parts = [p for p in parts if p.get_content_type() == "image/jpeg"]
        if not jpeg_parts:
            return [], "No JPEG parts in mhtml"

        results: List[Tuple[Path, float, float]] = []
        for i, jp in enumerate(jpeg_parts):
            raw = jp.get_payload(decode=True)
            if not raw:
                continue
            jp_path = tmp_dir / f"sprite_{i:03d}.jpg"
            jp_path.write_bytes(raw)
            start = slide_timings[i][0] if i < len(slide_timings) else 0.0
            end   = slide_timings[i][1] if i < len(slide_timings) else start + 60.0
            results.append((jp_path, start, end))

        return results, None if results else "No JPEG data in mhtml"
    except Exception as exc:
        return [], f"mhtml parse failed: {exc}"


def _sprite_frame_dimensions(sprite_path: Path, cols: int, rows: int) -> Tuple[int, int]:
    """Get per-frame pixel dimensions from a sprite sheet.

    PIL is tried first: ffprobe's "-show_streams" reports a still JPEG
    under codec_type "video" inconsistently (0x0 in practice here), so
    PIL is the reliable path for a plain JPEG sprite sheet.
    """
    try:
        from PIL import Image
        img = Image.open(sprite_path)
        w, h = img.size
        if w > 0 and h > 0:
            return w // cols, h // rows
    except Exception:
        pass

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            proc = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_streams", str(sprite_path)],
                capture_output=True, text=True, timeout=10
            )
            data = json.loads(proc.stdout)
            for stream in data.get("streams", []):
                w = stream.get("width", 0)
                h = stream.get("height", 0)
                if w and h:
                    return w // cols, h // rows
        except Exception:
            pass

    return 160, 90


def _extract_frame_from_sprite(
    sprite_path: Path,
    frame_index: int,
    cols: int,
    rows: int,
    frame_width: int,
    frame_height: int,
    out_path: Path,
    ffmpeg: str,
) -> bool:
    """Extract one frame from a sprite sheet."""
    col = frame_index % cols
    row = frame_index // cols
    x = col * frame_width
    y = row * frame_height
    cmd = [
        ffmpeg,
        "-i", str(sprite_path),
        "-vf", f"crop={frame_width}:{frame_height}:{x}:{y}",
        "-q:v", "3",
        "-y",
        str(out_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
        return proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def _acquire_from_storyboard(
    url: str,
    video_id: str,
    sid: str,
    frames_dir: Path,
    max_frames: int,
    sample_interval_sec: float,
) -> Tuple[List[VisualFrameArtifact], Optional[str]]:
    """Acquire frames from YouTube storyboard via yt-dlp mhtml download."""
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        return [], "yt-dlp not found"

    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return [], "ffmpeg not found"

    fmt_id = _get_storyboard_format_id(video_id)
    if not fmt_id:
        return [], "No storyboard format available"

    cols, rows = _get_storyboard_grid(video_id, fmt_id)
    frames_per_sprite = cols * rows

    with tempfile.TemporaryDirectory(prefix="vlp1_storyboard_") as tmp:
        tmp_dir = Path(tmp)
        mhtml_path = tmp_dir / "storyboard.mhtml"

        # Download storyboard as mhtml
        cmd = [
            yt_dlp,
            "--format", fmt_id,
            "--no-playlist",
            "--output", str(mhtml_path),
            "--quiet",
            "--no-progress",
            "--",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=120, check=False)
            if proc.returncode != 0:
                return [], f"yt-dlp storyboard download failed (exit {proc.returncode})"
        except subprocess.TimeoutExpired:
            return [], "yt-dlp storyboard download timed out"

        if not mhtml_path.exists():
            return [], "Storyboard mhtml not found after download"

        # Parse mhtml to extract sprite sheets with timing
        sprites, err = _parse_mhtml_storyboard(mhtml_path, tmp_dir)
        if not sprites:
            return [], err or "No sprites in storyboard"

        frames: List[VisualFrameArtifact] = []
        total_duration = sprites[-1][2] - sprites[0][1]

        for sprite_path, start_sec, end_sec in sprites:
            if len(frames) >= max_frames:
                break

            duration = end_sec - start_sec
            if duration <= 0:
                continue

            sec_per_frame = duration / frames_per_sprite
            frame_w, frame_h = _sprite_frame_dimensions(sprite_path, cols, rows)

            # How many frames to take from this sprite sheet
            frac = duration / max(total_duration, 1.0)
            n_take = max(1, round(max_frames * frac))
            n_take = min(n_take, frames_per_sprite, max_frames - len(frames))
            step = max(1, frames_per_sprite // n_take)

            for idx in range(0, frames_per_sprite, step):
                if len(frames) >= max_frames:
                    break
                timestamp_sec = start_sec + idx * sec_per_frame
                frame_id = "frame_%s_%08d" % (sid, int(timestamp_sec * 1000))
                out_path = frames_dir / ("%s.jpg" % frame_id)

                ok = _extract_frame_from_sprite(
                    sprite_path, idx, cols, rows, frame_w, frame_h, out_path, ffmpeg
                )
                if ok:
                    ahash = _sha256_file(out_path)
                    frames.append(VisualFrameArtifact(
                        frame_id=frame_id,
                        source_url=url,
                        source_id=sid,
                        video_id=video_id,
                        timestamp_sec=timestamp_sec,
                        artifact_path=str(out_path.relative_to(
                            Path(__file__).parent.parent.parent
                        )).replace("\\", "/"),
                        artifact_hash=ahash,
                    ))

    return frames, None if frames else "No frames extracted from storyboard"


def acquire_visual_evidence(
    source_url: str,
    transcript_sufficiency: Optional[TranscriptSufficiency] = None,
    max_frames: int = _DEFAULT_MAX_FRAMES,
    sample_interval_sec: float = _DEFAULT_SAMPLE_INTERVAL_SEC,
    force: bool = False,
) -> VisualEvidenceBundle:
    """Acquire visual evidence for a YouTube source.

    Attempts video stream first; falls back to storyboard extraction if
    the video stream is unavailable.

    Returns:
        VisualEvidenceBundle with frames populated (no observations yet).
    """
    url, video_id = _validate_youtube_url(source_url)
    sid = _source_id(url)

    bundle = VisualEvidenceBundle(
        source_url=url,
        source_id=sid,
        video_id=video_id,
        transcript_sufficiency=transcript_sufficiency,
    )

    # Check if frames already exist (idempotent)
    frames_dir = _FRAMES_DIR / sid
    manifest_path = frames_dir / "manifest.json"
    if manifest_path.exists() and not force:
        _load_existing_frames(bundle, manifest_path)
        return bundle

    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        bundle.acquisition_error = "ffmpeg not found on PATH"
        return bundle

    frames_dir.mkdir(parents=True, exist_ok=True)

    # Primary path: real video, highest resolution available up to 1080p.
    with tempfile.TemporaryDirectory(prefix="vlp1_video_") as tmp:
        tmp_dir = Path(tmp)
        video_path, video_provenance = _download_best_video(url, tmp_dir, video_id)

        if video_path is not None:
            duration = video_provenance.get("duration_sec") or _get_video_duration(video_path, ffmpeg)
            effective_duration = duration if duration else 300.0
            frame_w = video_provenance.get("width")
            frame_h = video_provenance.get("height")
            src_sha = video_provenance.get("source_video_sha256")

            timestamps = []
            t = sample_interval_sec
            while t < effective_duration and len(timestamps) < max_frames:
                timestamps.append(t)
                t += sample_interval_sec

            if timestamps and timestamps[0] > 30.0:
                timestamps = [30.0] + timestamps[:max_frames - 1]
            if not timestamps:
                timestamps = [30.0]

            manifest_frames = []
            for ts in timestamps:
                frame_id = "frame_%s_%08d" % (sid, int(ts * 1000))
                out_path = frames_dir / ("%s.jpg" % frame_id)
                if out_path.exists() and not force:
                    ahash = _sha256_file(out_path)
                else:
                    ok = _extract_frame(video_path, ts, out_path, ffmpeg)
                    if not ok:
                        continue
                    ahash = _sha256_file(out_path)

                artifact = VisualFrameArtifact(
                    frame_id=frame_id,
                    source_url=url,
                    source_id=sid,
                    video_id=video_id,
                    timestamp_sec=ts,
                    artifact_path=str(out_path.relative_to(
                        Path(__file__).parent.parent.parent
                    )).replace("\\", "/"),
                    artifact_hash=ahash,
                    width=frame_w,
                    height=frame_h,
                    source_video_sha256=src_sha,
                )
                bundle.frames.append(artifact)
                manifest_frames.append(artifact.to_dict())

            if bundle.frames:
                bundle.source_video_info = video_provenance
                manifest_path.write_text(json.dumps({
                    "frames": manifest_frames,
                    "source_video_info": video_provenance,
                }, indent=2))
                return bundle  # success via real video stream
            else:
                video_provenance["fallback_reason"] = (
                    (video_provenance.get("fallback_reason") or "") +
                    " | video downloaded but no frames could be extracted"
                ).strip(" |")

    # Real video genuinely unavailable — fall back to storyboard (last resort).
    sb_frames, sb_error = _acquire_from_storyboard(
        url, video_id, sid, frames_dir, max_frames, sample_interval_sec
    )

    if sb_frames:
        bundle.frames = sb_frames
        bundle.source_video_info = None  # storyboard path — no real video provenance
        manifest_path.write_text(json.dumps({
            "frames": [f.to_dict() for f in sb_frames],
            "source_video_info": None,
        }, indent=2))
        return bundle

    bundle.acquisition_error = sb_error or "Both real-video and storyboard acquisition failed"
    return bundle


def acquire_frames_at_timestamps(
    source_url: str,
    timestamps: List[float],
    force: bool = False,
) -> VisualEvidenceBundle:
    """Acquire frames at EXACT caller-given timestamps — the transcript-first
    counterpart to acquire_visual_evidence()'s blind fixed-cadence sampling.

    Used when a transcript_query_planner.VisualQueryPlan has already
    identified WHICH moments matter; this function only fetches those, at
    the highest resolution available, with the same real hash/provenance
    guarantees as the cadence-based path. It never falls back to storyboard
    sampling on its own — storyboard frames are too low-resolution (down to
    320x180 or smaller) to reliably read a knob's displayed number, which is
    the whole point of a targeted query. Callers that need a storyboard
    fallback should do so explicitly and say so in the resulting record.

    Returns a VisualEvidenceBundle with bundle.frames populated in the same
    order as `timestamps` (one frame per timestamp; a timestamp that fails
    to extract is simply omitted, not silently replaced by a nearby one).
    """
    url, video_id = _validate_youtube_url(source_url)
    sid = _source_id(url)

    bundle = VisualEvidenceBundle(source_url=url, source_id=sid, video_id=video_id)

    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        bundle.acquisition_error = "ffmpeg not found on PATH"
        return bundle

    frames_dir = _FRAMES_DIR / sid
    frames_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vlp1_targeted_") as tmp:
        tmp_dir = Path(tmp)
        video_path, video_provenance = _download_best_video(url, tmp_dir, video_id)

        if video_path is None:
            bundle.acquisition_error = (
                "Real video stream unavailable for targeted acquisition "
                "(storyboard fallback deliberately not used — resolution "
                "too low to read exact UI values). fallback_reason=%r"
                % video_provenance.get("fallback_reason")
            )
            return bundle

        frame_w = video_provenance.get("width")
        frame_h = video_provenance.get("height")
        src_sha = video_provenance.get("source_video_sha256")

        manifest_frames = []
        for ts in timestamps:
            frame_id = "frame_%s_%08d" % (sid, int(ts * 1000))
            out_path = frames_dir / ("%s.jpg" % frame_id)
            if out_path.exists() and not force:
                ahash = _sha256_file(out_path)
            else:
                ok = _extract_frame(video_path, ts, out_path, ffmpeg)
                if not ok:
                    continue
                ahash = _sha256_file(out_path)

            artifact = VisualFrameArtifact(
                frame_id=frame_id,
                source_url=url,
                source_id=sid,
                video_id=video_id,
                timestamp_sec=ts,
                artifact_path=str(out_path.relative_to(
                    Path(__file__).parent.parent.parent
                )).replace("\\", "/"),
                artifact_hash=ahash,
                width=frame_w,
                height=frame_h,
                source_video_sha256=src_sha,
            )
            bundle.frames.append(artifact)
            manifest_frames.append(artifact.to_dict())

        if bundle.frames:
            bundle.source_video_info = video_provenance
            manifest_path = frames_dir / "manifest.json"
            existing = []
            if manifest_path.exists():
                try:
                    existing = json.loads(manifest_path.read_text()).get("frames", [])
                except Exception:
                    existing = []
            existing_ids = {f["frame_id"] for f in existing}
            merged = existing + [f for f in manifest_frames if f["frame_id"] not in existing_ids]
            manifest_path.write_text(json.dumps({
                "frames": merged,
                "source_video_info": video_provenance,
            }, indent=2))
        else:
            bundle.acquisition_error = (
                "Video downloaded but no frame could be extracted at any "
                "requested timestamp"
            )

    return bundle


def _load_existing_frames(bundle: VisualEvidenceBundle, manifest_path: Path) -> None:
    """Populate bundle.frames (and source_video_info, if present) from a
    persisted manifest. Accepts both the current {frames, source_video_info}
    format and the legacy bare-list format."""
    data = json.loads(manifest_path.read_text())
    if isinstance(data, dict):
        frame_items = data.get("frames", [])
        bundle.source_video_info = data.get("source_video_info")
    else:
        frame_items = data  # legacy: bare list of frame dicts
    for item in frame_items:
        frame_path = Path(__file__).parent.parent.parent / item["artifact_path"]
        if not frame_path.exists():
            continue
        bundle.frames.append(VisualFrameArtifact(**item))
