#!/usr/bin/env python
"""YouTube → Serum 2.0.21 end-to-end product execution.

REAL pipeline:
  python main.py "<YOUTUBE_URL>"

Produces:
  - video.mp4 (downloaded)
  - .vtt transcript (extracted)
  - frames/ directory (EXHAUSTIVE frame extraction, not sparse)
  - stage_a_observation.json (from local model analysis)
  - result.SerumPreset (real Serum 2.0.21 preset)
  - report.docx (non-executable parameters documented)

No mocks. No placeholders. No print-only. Real execution.
"""

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator import orchestrate_youtube_to_serum


def main():
    parser = argparse.ArgumentParser(
        description="YouTube → Serum 2.0.21 preset reproduction"
    )
    parser.add_argument("youtube_url", help="YouTube video URL")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "output"),
        help="Output directory for artifacts"
    )
    args = parser.parse_args()

    print("Executing: YouTube -> Serum")
    print(f"URL: {args.youtube_url}")
    print(f"Output: {args.output_dir}\n")

    result = orchestrate_youtube_to_serum(
        youtube_url=args.youtube_url,
        output_dir=Path(args.output_dir)
    )

    # Print final deliverables
    print("\n" + "="*80)
    print("FINAL DELIVERABLES")
    print("="*80)
    if result.get("preset_path"):
        print(f"[OK] Serum Preset: {result['preset_path']}")
    if result.get("report_path"):
        print(f"[OK] Report (.docx): {result['report_path']}")
    if result.get("video_path"):
        print(f"[OK] Video: {result['video_path']}")
    if result.get("transcript_path"):
        print(f"[OK] Transcript: {result['transcript_path']}")
    print("="*80)


if __name__ == "__main__":
    main()
