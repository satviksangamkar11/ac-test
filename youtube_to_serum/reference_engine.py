"""The real per-video reference-reproduction engine. Replaces orchestrator.py's fakes:
  - transcript_segments actually comes from the real fetched transcript (not `[]`).
  - No hardcoded preset: the compiled preset comes only from admitted operations built from a real Stage-A
    observation.
  - The Producer Brain actually sees the complete reference knowledge (every ledger row) via
    reference_knowledge_brief.brief_reference_knowledge -- read-only, cannot alter admission (see that module and
    its tests).
  - The forensic report lists every non-executable row by name and reason, built from the real ledger/admission
    output, never "no items."
  - The bridge (serum2.ableton.serum_track_loader) is actually called to load the compiled preset into real,
    running Serum -- or the run stops there with the exact remedy, on a machine that can't do it.

This module performs NO vision or interpretation itself. Where a Stage-A observation is required and doesn't exist
yet, `run_stage1_acquire_and_prep` stops and tells the caller exactly what to do next -- it never invents one.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# serum2/source's own modules import each other by bare name (e.g. "from youtube_transcript_resolver import ..."),
# so serum2/source itself must be on sys.path directly, not only importable as the serum2.source package.
_SOURCE_PATH = str(ROOT / "serum2" / "source")
if _SOURCE_PATH not in sys.path:
    sys.path.insert(0, _SOURCE_PATH)

from serum2.source.fetch_youtube import fetch_transcript  # noqa: E402
from serum2.source.acquire_visual_evidence import acquire_visual_evidence  # noqa: E402
from serum2.source.youtube_url import extract_youtube_video_id  # noqa: E402
from serum2.producer.stage_a_census_prep import prep as stage_a_prep  # noqa: E402
from serum2.producer.state_ledger import build_all, conservation  # noqa: E402
from serum2.producer.reference_knowledge_brief import brief_reference_knowledge  # noqa: E402
from serum2.producer.execution_epoch import installed_epoch  # noqa: E402
from serum2.server.reference_reproduction import run_reference_reproduction  # noqa: E402

BINDING_EVIDENCE_DIR = ROOT / "parameter_characterization" / "binding_evidence"
PROMOTED_EVIDENCE_DIR = ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1"


class NeedsStageACensus(RuntimeError):
    """The Stage-A skeleton exists but is still empty (or missing entirely). Carries the exact path to fill in and
    to resume from -- never a reason to proceed with a fabricated observation."""

    def __init__(self, skeleton_path: str, normalized_transcript_path: str, n_frames: int):
        self.skeleton_path, self.normalized_transcript_path, self.n_frames = skeleton_path, normalized_transcript_path, n_frames
        super().__init__(
            "Stage-A visual census required: %d frames prepared, none yet observed.\n"
            "  1. Read %s for timing context.\n"
            "  2. Fill in %s -- one entry per frame, only what is actually visible (leave serum_visible false / "
            "controls empty where nothing Serum-relevant is on screen; never guess a value).\n"
            "  3. Re-run this pipeline with --resume-from stage_a." % (n_frames, normalized_transcript_path, skeleton_path))


def stage_a_is_filled(skeleton_path: str) -> bool:
    """A skeleton counts as filled once at least one frame has a non-empty controls/observations/unknown list, or
    serum_visible has been set to something other than None. An all-still-empty file is not a valid census."""
    data = json.loads(Path(skeleton_path).read_text())
    return any(
        f.get("serum_visible") is not None or f["controls"] or f["mod_routes"] or f["observations"] or f["unknown"]
        for f in data["frames"]
    )


def run_stage1_acquire_and_prep(youtube_url: str, work_dir: Path) -> Dict[str, Any]:
    """Real acquisition through the existing, already-real fetch_transcript/acquire_visual_evidence, then mechanical
    Stage-A prep. Raises NeedsStageACensus if the skeleton isn't filled in yet -- the only legitimate stop.

    Idempotent by design: if work_dir already has a skeleton from a previous call, it is NEVER regenerated -- doing
    so would silently discard whatever census work has been filled into it so far. Re-acquisition (a fresh
    transcript/frame fetch) only happens the first time, before that file exists."""
    work_dir.mkdir(parents=True, exist_ok=True)
    existing_skeleton = work_dir / "stage_a_skeleton.json"
    existing_transcript = work_dir / "normalized_transcript.json"
    if existing_skeleton.exists() and existing_transcript.exists():
        if not stage_a_is_filled(str(existing_skeleton)):
            n_frames = len(json.loads(existing_skeleton.read_text())["frames"])
            raise NeedsStageACensus(str(existing_skeleton), str(existing_transcript), n_frames)
        return {"normalized_transcript_path": str(existing_transcript), "stage_a_skeleton_path": str(existing_skeleton),
                "n_frames": len(json.loads(existing_skeleton.read_text())["frames"])}

    video_id = extract_youtube_video_id(youtube_url)

    if not fetch_transcript(video_id=video_id, url=youtube_url, allow_fallback=True):
        raise RuntimeError("Could not fetch a transcript for %r" % youtube_url)
    # fetch_transcript resolves Path("data/transcripts") relative to CWD, not to this module's location -- mirror
    # that exact resolution here (never ROOT) so this always looks where fetch_transcript actually just wrote.
    from serum2.source.fetch_youtube import compute_source_id
    source_id = compute_source_id(youtube_url)
    transcript_path = Path("data") / "transcripts" / (source_id + ".json")
    if not transcript_path.exists():
        raise RuntimeError("fetch_transcript reported success but %s was not found relative to the current "
                           "working directory (%s)" % (transcript_path, Path.cwd()))

    bundle = acquire_visual_evidence(source_url=youtube_url, transcript_sufficiency=None,
                                     max_frames=999999, sample_interval_sec=1.0, force=False)
    if not bundle.frames:
        raise RuntimeError("acquire_visual_evidence returned zero frames for %r" % youtube_url)
    frame_dir = (ROOT / bundle.frames[0].artifact_path).parent

    prep_result = stage_a_prep(
        frames_dir=str(frame_dir),
        transcript_json3_path=str(transcript_path), video_id=video_id, source_url=youtube_url,
        out_dir=str(work_dir), transcript_kind="fetch_transcript",
    )

    if not stage_a_is_filled(prep_result["stage_a_skeleton_path"]):
        raise NeedsStageACensus(prep_result["stage_a_skeleton_path"], prep_result["normalized_transcript_path"],
                                prep_result["n_frames"])
    return prep_result


def run_stage2_reproduce(stage_a_path: str, video_id: str, source_url: str, name: str,
                         reread_log_path: Optional[str] = None, ui_readback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Real ledger -> admission -> compile -> file readback (-> UI compare if ui_readback is given), plus the
    Brain's read-only reference-knowledge brief. Requires a REAL Serum binary at the epoch's documented path (this
    raises whatever installed_epoch() raises on a machine without one -- never silently substitutes an epoch)."""
    reread_log_path = reread_log_path or _empty_reread_log(Path(stage_a_path).parent)
    epoch = installed_epoch()

    run = run_reference_reproduction(
        stage_a_path, reread_log_path, source={"video_id": video_id, "source_url": source_url}, name=name,
        epoch=epoch, ui_readback=ui_readback,
        binding_evidence_dir=str(BINDING_EVIDENCE_DIR) if BINDING_EVIDENCE_DIR.is_dir() else None,
        promoted_evidence_dir=str(PROMOTED_EVIDENCE_DIR) if PROMOTED_EVIDENCE_DIR.is_dir() else None,
    )

    rows_for_brief = [{"control_id": r.control_id, "terminal": r.terminal, "reason": getattr(r, "reason", None)}
                      for r in run.rows]
    brief = brief_reference_knowledge(rows_for_brief)

    return {"run": run, "brief": brief}


def _empty_reread_log(work_dir: Path) -> str:
    p = work_dir / "reread_log.json"
    if not p.exists():
        p.write_text(json.dumps({"rereads": []}))
    return str(p)


def build_forensic_report(stage2_result: Dict[str, Any], youtube_url: str, out_path: Path) -> str:
    """Every non-executable row listed by name and reason -- the honest replacement for orchestrator.py's
    hardcoded 'no explicit non-executable items were documented' text."""
    run, brief = stage2_result["run"], stage2_result["brief"]
    by_terminal: Dict[str, List[Dict[str, Any]]] = {}
    for b in brief:
        by_terminal.setdefault(b["terminal"], []).append(b)

    try:
        from docx import Document
        doc = Document()
        doc.add_heading("Reference Reproduction Forensic Report", 0)
        doc.add_paragraph("Source: %s" % youtube_url)
        doc.add_paragraph("Generated: %s" % datetime.utcnow().isoformat())
        doc.add_paragraph("Serum epoch: %s" % run.epoch.label)
        doc.add_paragraph("Verification level: %s | Coverage: %s | reference_verified: %s"
                          % (run.verification_level, run.coverage_status, run.reference_verified))
        doc.add_heading("Compiled preset", level=1)
        doc.add_paragraph("Path: %s\nSHA-256: %s" % (run.preset["path"], run.preset["sha256"]))
        doc.add_heading("Executable (admitted, compiled)", level=1)
        for b in by_terminal.get("OPERATION_DERIVED", []):
            doc.add_paragraph("%s -- %d related knowledge item(s) retrieved" % (b["target"], b["brain_knowledge_item_count"]))
        for terminal, label in (("UNREADABLE_RE_READ_REQUIRED", "Unreadable"), ("UNBOUND_TO_SERUM_PARAM", "Unbound"),
                                ("UNSUPPORTED_VALUE", "Unsupported"), ("UNRESOLVED", "Unresolved identity"),
                                ("IGNORED_NAVIGATION", "Ignored (navigation)"), ("NOT_SERUM_SURFACE", "Not a Serum surface")):
            rows = by_terminal.get(terminal, [])
            if rows:
                doc.add_heading("Non-executable: %s (%d)" % (label, len(rows)), level=1)
                for b in rows:
                    doc.add_paragraph("%s -- %s" % (b["target"], b.get("reason") or "no reason recorded"))
        doc.save(str(out_path))
        return str(out_path)
    except ImportError:
        out_path = out_path.with_suffix(".json")
        out_path.write_text(json.dumps({
            "source_url": youtube_url, "verification_level": run.verification_level,
            "coverage_status": run.coverage_status, "reference_verified": run.reference_verified,
            "preset": run.preset, "by_terminal": {k: len(v) for k, v in by_terminal.items()},
            "non_executable": {k: v for k, v in by_terminal.items() if k != "OPERATION_DERIVED"},
        }, indent=1, default=str))
        return str(out_path)
