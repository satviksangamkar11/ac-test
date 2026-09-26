"""Real orchestrator: thin wrapper around reference_engine.py's real pipeline.

Previously this module faked four things: transcript_segments was set to `[]` and never filled from the real
fetched transcript; every frame got an empty stub with a dead `# TODO: Replace with actual VLM inference`; the
Producer Brain's execute_producer_request() result was computed and thrown away; and the preset written was a
fixed, hardcoded oscillator regardless of the video's actual content. It also never touched Ableton/Serum.

None of that remains. This function now delegates entirely to reference_engine.py (Stage-A prep, ledger, admission,
compilation, the Brain's read-only reference-knowledge brief, the real forensic report) and
serum2/ableton/serum_track_loader.py (the bridge into real, running Serum). Where the real pipeline needs a Stage-A
visual census or a live-Ableton bridge that this machine can't provide, this function returns that fact plainly --
it never substitutes a placeholder for either.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference_engine import (  # noqa: E402
    NeedsStageACensus, build_forensic_report, run_stage1_acquire_and_prep, run_stage2_reproduce,
)
from serum2.ableton.serum_track_loader import BridgeUnavailable, build_ui_readback_request, load_and_verify  # noqa: E402
from serum2.source.youtube_url import extract_youtube_video_id  # noqa: E402


def orchestrate_youtube_to_serum(youtube_url: str, output_dir: Path) -> dict:
    """Real end-to-end orchestration. Returns a dict describing exactly what happened -- including, honestly,
    when it stopped at a checkpoint rather than proceeding with a fabricated result."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = extract_youtube_video_id(youtube_url)
    name = "ytrecon_%s" % video_id

    print("[1/4] Acquisition + Stage-A prep...")
    try:
        stage1 = run_stage1_acquire_and_prep(youtube_url, output_dir)
    except NeedsStageACensus as e:
        print(str(e))
        return {"status": "STAGE_A_REQUIRED", "stage_a_skeleton_path": e.skeleton_path,
                "normalized_transcript_path": e.normalized_transcript_path, "n_frames": e.n_frames,
                "preset_path": None, "report_path": None}
    print("  %d frames prepared; census filled -> proceeding" % stage1["n_frames"])

    print("[2/4] Ledger -> admission -> compile -> file readback (+ Brain reference-knowledge brief)...")
    stage2 = run_stage2_reproduce(stage1["stage_a_skeleton_path"], video_id, youtube_url, name)
    run = stage2["run"]
    print("  preset: %s" % run.preset["path"])
    print("  verification_level=%s coverage_status=%s reference_verified=%s"
         % (run.verification_level, run.coverage_status, run.reference_verified))

    print("[3/4] Building forensic report from the real ledger/admission output...")
    report_path = build_forensic_report(stage2, youtube_url, output_dir / "forensic_report.docx")
    print("  report: %s" % report_path)

    print("[4/4] Bridge: loading the compiled preset into real, running Serum...")
    bridge_status, bridge_reason = "SKIPPED", None
    try:
        bridge_result = load_and_verify(run.preset["path"], track_name=name)
        bridge_status = bridge_result.get("status", "UNKNOWN")
    except BridgeUnavailable as e:
        bridge_status, bridge_reason = "BRIDGE_UNAVAILABLE", str(e)
        print(str(e))

    return {
        "status": "COMPLETE", "preset_path": run.preset["path"], "report_path": report_path,
        "video_path": None, "transcript_path": stage1["normalized_transcript_path"],
        "verification_level": run.verification_level, "coverage_status": run.coverage_status,
        "reference_verified": run.reference_verified, "bridge_status": bridge_status, "bridge_reason": bridge_reason,
    }
