"""Mechanical prep for the one legitimate manual step in the pipeline: Claude Code's direct visual inspection of
the captured video frames (the Stage-A boundary, docs/VLP1_Fully_Revised_Architecture.md section 10).

This module does NOT perform vision or interpretation. It only:
  1. normalizes the raw captured transcript (yt-dlp's json3 format) into the shape
     `.claude/skills/analyze-youtube-transcript` expects, so that skill can produce a visual-inspection cue plan
     without anyone hand-copying fields between formats each run;
  2. builds a frame manifest from the captured frames directory (plus an optional dense-window manifest, if the
     video was densified around changing regions);
  3. emits an EMPTY, schema-valid Stage-A observation skeleton -- one entry per frame, every observation list
     empty -- for a visual census to fill in. The skeleton's shape matches
     tests/fixtures/reference_reproduction/stage_a_observation.json exactly, so the same `state_ledger.build_all`
     that already consumes that fixture consumes a filled-in skeleton with no format drift.

Nothing here invents a control, a value, or a cue. An empty skeleton is not a claim that nothing is visible; it is
the frame accounting Claude Code's census fills in, one frame at a time.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_transcript(json3_path: str, video_id: str, source_url: str) -> Dict[str, Any]:
    """yt-dlp json3 (`events` of `segs`) -> the normalized shape `analyze-youtube-transcript` consumes."""
    raw = json.loads(Path(json3_path).read_text(encoding="utf-8"))
    segments = []
    for i, ev in enumerate(raw.get("events", [])):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 0)
        segments.append({
            "segment_id": "seg-%04d" % i, "text": text,
            "start_time_sec": start_ms / 1000.0, "duration": dur_ms / 1000.0,
        })
    transcript_sha256 = hashlib.sha256(Path(json3_path).read_bytes()).hexdigest()
    return {
        "source_id": "yt_%s" % video_id, "video_id": video_id, "source_url": source_url,
        "language": "en", "transcript_sha256": transcript_sha256, "transcript": segments,
    }


def normalize_fetch_transcript_output(transcript_json_path: str) -> Dict[str, Any]:
    """`serum2.source.fetch_youtube.fetch_transcript` writes its OWN already-mostly-normalized JSON
    (source_id/source_url/video_id/segments, segments already shaped {text, start_time_sec, duration}) -- a
    DIFFERENT file, format and location than yt-dlp's raw json3 (which `normalize_transcript` above handles, for
    a manually-captured video). This only renames/re-keys fields into the exact shape
    `analyze-youtube-transcript` expects; no segment is dropped, reordered, or re-timed."""
    raw = json.loads(Path(transcript_json_path).read_text(encoding="utf-8"))
    segments = [
        {"segment_id": "seg-%04d" % i, "text": s.get("text", ""),
         "start_time_sec": s.get("start_time_sec", s.get("start", 0.0)),
         "duration": s.get("duration", 0.0)}
        for i, s in enumerate(raw.get("segments", []))
    ]
    return {
        "source_id": raw["source_id"], "video_id": raw["video_id"], "source_url": raw["source_url"],
        "language": raw.get("language_code") or raw.get("language") or "en",
        "transcript_sha256": hashlib.sha256(Path(transcript_json_path).read_bytes()).hexdigest(),
        "transcript": segments,
    }


# Old video_capture naming: f_00001.jpg (1-based index, fps-derived timestamp)
_FRAME_RE = re.compile(r"f_(\d+)\.jpg$")
# acquire_visual_evidence naming: frame_<source_id>_<ms>.jpg (millisecond timestamp)
# source_id itself contains underscores (e.g. yt_6351960979de), so match greedily up to the final _<digits>.jpg
_FRAME_RE_AV = re.compile(r"frame_.+_(\d+)\.jpg$")


def build_frame_manifest(frames_dir: str, fps: float = 1.0, dense_windows_json: Optional[str] = None) -> List[Dict[str, Any]]:
    """One entry per captured frame: {frame_id, timestamp_sec, path}. Sparse (1 fps) frames plus any dense-window
    frames are both included, each keyed by its own real path and timestamp -- nothing is deduplicated or dropped
    silently; a frame that exists in both the sparse and a dense window appears twice, at its own two paths, because
    they are two different images taken at two different resolutions/rates."""
    manifest = []
    fdir = Path(frames_dir)
    # Old video_capture naming: f_00001.jpg
    for p in sorted(fdir.glob("f_*.jpg")):
        m = _FRAME_RE.search(p.name)
        if not m:
            continue
        idx = int(m.group(1))
        ts = (idx - 1) / fps
        manifest.append({"frame_id": "frame_%05d" % idx, "timestamp_sec": ts, "path": str(p), "source": "sparse"})
    # acquire_visual_evidence naming: frame_<source_id>_<ms>.jpg
    for p in sorted(fdir.glob("frame_*.jpg")):
        m = _FRAME_RE_AV.search(p.name)
        if not m:
            continue
        ts = int(m.group(1)) / 1000.0
        frame_id = p.stem  # already unique: frame_yt_<sid>_<ms>
        manifest.append({"frame_id": frame_id, "timestamp_sec": ts, "path": str(p), "source": "sparse"})
    if dense_windows_json and Path(dense_windows_json).exists():
        windows = json.loads(Path(dense_windows_json).read_text())
        dense_fps = windows.get("dense_fps", 10)
        dense_root = Path(dense_windows_json).parent   # .../dense/windows.json -> .../dense
        for w in windows.get("windows", []):
            # "dir" was recorded on the machine that ran the densifier (often Windows: backslash separators).
            # Re-resolve to THIS machine's real dense/<window-name> directory instead of trusting the raw string --
            # a silent path-separator mismatch would otherwise drop every dense frame with no error at all.
            window_name = re.split(r"[\\/]", w["dir"])[-1]
            wdir = dense_root / window_name
            for p in sorted(wdir.glob("f_*.jpg")) if wdir.is_dir() else []:
                m = _FRAME_RE.search(p.name)
                if not m:
                    continue
                idx = int(m.group(1))
                ts = w["start"] + (idx - 1) / dense_fps
                manifest.append({"frame_id": "dense_%s_%05d" % (window_name, idx), "timestamp_sec": ts,
                                  "path": str(p), "source": "dense"})
    return manifest


def empty_stage_a_skeleton(frame_manifest: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Schema-identical to tests/fixtures/reference_reproduction/stage_a_observation.json, with every frame present
    and every observation list empty -- the census fills these in, never removes a frame entry."""
    return {
        "stage_a_provenance": {
            "observer": "claude_code", "observation_mode": "direct_visual_inspection", "model_api_used": False,
        },
        "frames": [
            {
                "frame_id": f["frame_id"], "timestamp_sec": f["timestamp_sec"],
                "serum_visible": None,   # census must set true/false explicitly -- never left implying "no"
                "visible_panel": None,
                "controls": [], "mod_routes": [], "observations": [], "unknown": [],
                "_source_path": f["path"],   # census provenance only; state_ledger.build_all ignores unknown keys
            }
            for f in frame_manifest
        ],
    }


def prep(frames_dir: str, transcript_json3_path: str, video_id: str, source_url: str,
         out_dir: str, fps: float = 1.0, dense_windows_json: Optional[str] = None,
         transcript_kind: str = "json3") -> Dict[str, str]:
    """Writes normalized_transcript.json and stage_a_skeleton.json into out_dir; returns their paths plus the
    frame count, so a caller can print the exact next action (run the cue-plan skill, then fill the skeleton).
    transcript_kind: "json3" (yt-dlp raw captions, e.g. a manually captured video) or "fetch_transcript"
    (serum2.source.fetch_youtube's own already-mostly-normalized output)."""
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    if transcript_kind == "fetch_transcript":
        transcript = normalize_fetch_transcript_output(transcript_json3_path)
    else:
        transcript = normalize_transcript(transcript_json3_path, video_id, source_url)
    manifest = build_frame_manifest(frames_dir, fps=fps, dense_windows_json=dense_windows_json)
    skeleton = empty_stage_a_skeleton(manifest)
    t_path, s_path = outp / "normalized_transcript.json", outp / "stage_a_skeleton.json"
    t_path.write_text(json.dumps(transcript, indent=1))
    s_path.write_text(json.dumps(skeleton, indent=1))
    return {"normalized_transcript_path": str(t_path), "stage_a_skeleton_path": str(s_path),
            "n_frames": len(manifest)}
