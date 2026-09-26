"""
densify_windows.py — extract 10-fps windows around frames where the Serum UI is changing.

Strategy:
  1. Crop each 1-fps frame to the Serum panel region (right half of screen, roughly).
  2. Compute pixel diff between consecutive cropped frames.
  3. Any frame whose diff exceeds THRESHOLD starts a window [t-0.5s, t+4.5s].
  4. Adjacent/overlapping windows are merged.
  5. Each merged window is re-extracted from the source video at 10 fps.

Output:
  serum2/video_capture/v1/dense/<window_idx>/f_%05d.jpg  — 10-fps frames
  serum2/video_capture/v1/dense/windows.json             — window metadata

Usage:
  python serum2/video_capture/densify_windows.py
"""

import json, os, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent.parent
FRAMES_DIR = REPO / "serum2/video_capture/v1/frames"
VIDEO     = REPO / "serum2/video_capture/v1/video.mp4"
OUT_DIR   = REPO / "serum2/video_capture/v1/dense"

# Serum panel region: right ~60% of screen, full height.
# 1920x1024 source; Serum typically occupies the right portion when Ableton is open.
# Using a generous crop — the analysis doesn't need to be exact.
CROP_X, CROP_Y = 700, 0
CROP_W, CROP_H = 1220, 1024

THRESHOLD   = 0.015   # mean abs diff per pixel (0-1 scale) to count as "active"
PAD_BEFORE  = 0.5     # seconds before active frame to include in window
PAD_AFTER   = 4.5     # seconds after active frame to include in window
DENSE_FPS   = 10


def load_crop(path):
    img = Image.open(path).crop((CROP_X, CROP_Y, CROP_X + CROP_W, CROP_Y + CROP_H))
    return np.array(img, dtype=np.float32) / 255.0


def active_seconds(frames_dir: Path) -> list[int]:
    """Return list of 0-based second indices where the Serum region changed noticeably."""
    jpgs = sorted(frames_dir.glob("f_*.jpg"))
    if len(jpgs) < 2:
        return []
    active = []
    prev = load_crop(jpgs[0])
    for i, jp in enumerate(jpgs[1:], 1):
        cur = load_crop(jp)
        diff = float(np.mean(np.abs(cur - prev)))
        if diff > THRESHOLD:
            active.append(i)
        prev = cur
    return active


def merge_windows(active: list[int], duration: float) -> list[dict]:
    """Merge active seconds into contiguous windows with padding."""
    if not active:
        return []
    windows = []
    start = max(0.0, active[0] - PAD_BEFORE)
    end   = min(duration, active[0] + PAD_AFTER)
    for s in active[1:]:
        ws = max(0.0, s - PAD_BEFORE)
        we = min(duration, s + PAD_AFTER)
        if ws <= end:          # overlapping — extend
            end = max(end, we)
        else:
            windows.append({"start": start, "end": end})
            start, end = ws, we
    windows.append({"start": start, "end": end})
    return windows


def extract_window(video: Path, start: float, end: float, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = end - start
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(video),
        "-t", str(duration),
        "-vf", f"fps={DENSE_FPS}",
        "-q:v", "2",
        str(out_dir / "f_%05d.jpg"),
    ], check=True, capture_output=True)


def main():
    info_path = REPO / "serum2/video_capture/v1/video_info.json"
    duration = json.loads(info_path.read_text())["duration"]

    print("scanning 1-fps frames for Serum activity…")
    active = active_seconds(FRAMES_DIR)
    print(f"  {len(active)} active seconds out of {duration}")

    windows = merge_windows(active, duration)
    print(f"  {len(windows)} merged windows")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for i, w in enumerate(windows):
        out = OUT_DIR / f"{i:04d}"
        print(f"  window {i}: {w['start']:.1f}-{w['end']:.1f}s -> {out}")
        extract_window(VIDEO, w["start"], w["end"], out)
        w["dir"] = str(out.relative_to(REPO))
        frames_extracted = len(list(out.glob("*.jpg")))
        w["frames"] = frames_extracted
        print(f"    {frames_extracted} frames")

    meta = {
        "video": "serum2/video_capture/v1/video.mp4",
        "vst3_sha256": "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3",
        "crop": {"x": CROP_X, "y": CROP_Y, "w": CROP_W, "h": CROP_H},
        "threshold": THRESHOLD,
        "dense_fps": DENSE_FPS,
        "windows": windows,
    }
    out_json = OUT_DIR / "windows.json"
    out_json.write_text(json.dumps(meta, indent=2))
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
