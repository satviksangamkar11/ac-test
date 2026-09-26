"""The one command: YouTube URL -> real Reference Knowledge -> real capability admission -> real compiled preset ->
real bridge load into real, running Serum -> real forensic report.

    python run_full_pipeline.py <youtube_url> [--name NAME] [--work-dir DIR]

Run from the repo root (fetch_transcript resolves its own output relative to CWD).

This is not a cron-job-able unattended script, and is not presented as one: it runs straight through until it needs
a Stage-A visual census or the live-Ableton bridge, at which point it stops with the EXACT next command to run --
never a fabricated placeholder standing in for either. Re-running the same command after the census is filled in
resumes from where it stopped (see reference_engine.run_stage1_acquire_and_prep's idempotency).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:   # youtube_to_serum has no __init__.py; import it the same unqualified way everywhere
    sys.path.insert(0, _HERE)

from reference_engine import (  # noqa: E402
    NeedsStageACensus, build_forensic_report, run_stage1_acquire_and_prep, run_stage2_reproduce,
)
from serum2.ableton.serum_track_loader import BridgeUnavailable, build_ui_readback_request, load_and_verify  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("youtube_url")
    ap.add_argument("--name", default=None, help="reproduction run name; defaults to the video id")
    ap.add_argument("--work-dir", default=None, help="defaults to youtube_to_serum/runs/<video_id>")
    ap.add_argument("--skip-bridge", action="store_true",
                    help="stop after compiling the preset; do not attempt the live-Ableton load")
    a = ap.parse_args()

    from serum2.source.youtube_url import extract_youtube_video_id
    video_id = extract_youtube_video_id(a.youtube_url)
    work_dir = Path(a.work_dir) if a.work_dir else ROOT / "youtube_to_serum" / "runs" / video_id
    name = a.name or ("ytrecon_%s" % video_id)

    print("[stage 1/3] acquisition + Stage-A prep ...")
    try:
        stage1 = run_stage1_acquire_and_prep(a.youtube_url, work_dir)
    except NeedsStageACensus as e:
        print("\n%s\n" % e)
        sys.exit(2)
    print("  %d frames prepared, census already filled -> proceeding" % stage1["n_frames"])

    print("[stage 2/3] ledger -> admission -> compile -> file readback ...")
    stage2 = run_stage2_reproduce(stage1["stage_a_skeleton_path"], video_id, a.youtube_url, name)
    run = stage2["run"]
    print("  preset: %s" % run.preset["path"])
    print("  verification_level=%s coverage_status=%s reference_verified=%s"
         % (run.verification_level, run.coverage_status, run.reference_verified))

    report_path = build_forensic_report(stage2, a.youtube_url, work_dir / "forensic_report.docx")
    print("  forensic report: %s" % report_path)

    if a.skip_bridge:
        print("\n--skip-bridge set: stopping before the live-Ableton load.")
        return

    print("[stage 3/3] bridge: load into real Serum ...")
    try:
        bridge_result = load_and_verify(run.preset["path"], track_name=name)
        print("  bridge result: %s" % json.dumps(bridge_result))
        watched = sorted({r.control_id for r in run.rows if r.terminal == "OPERATION_DERIVED"})
        readback_request = build_ui_readback_request(watched)
        req_path = work_dir / "ui_readback_request.json"
        req_path.write_text(json.dumps(readback_request, indent=1))
        print("\n  Loaded into real Serum. To complete verification, fill in the ACTUAL values you see for each "
             "control in %s, then re-run stage 2 passing that file as ui_readback." % req_path)
    except BridgeUnavailable as e:
        print("\n%s\n" % e)
        print("Preset is compiled and ready at: %s" % run.preset["path"])
        print("Run this exact command on that machine to finish: "
             "python youtube_to_serum/run_full_pipeline.py %r --name %r" % (a.youtube_url, name))
        sys.exit(3)


if __name__ == "__main__":
    main()
