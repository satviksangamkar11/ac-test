"""VLP-1 candidate: mU6PB--pf9w (acid bass, 2-min tutorial) -- VerifiedEpisode.

Full universal pipeline, no shortcuts:
  real transcript -> transcript_query_planner (found 'release' at t=22s,
  same word-split-safe matcher fixed during the k6 run) -> targeted frame
  acquisition (real yt-dlp download, real hashes) -> native-vision
  observation (ANTHROPIC_API_KEY still 401, same established fallback) ->
  deterministic diff (15ms -> 36ms, direction=longer) -> Producer Brain
  (resolved_concept=note-release, target=Env1.Release) -> real Resolution
  -> real Admission (ADMITTED, envelope_field_release, FRESH_4Q_VERIFIED) ->
  serum-mcp generate_preset -> real Serum 2 UI load (Serum's own preset
  browser) -> real MATRIX/ENV panel readback (REL=36ms, exact match) ->
  finalize_serum_preset_execution -> EXECUTED/ACCEPTED.

Honest gap: the planner's default before/after offsets (+4s/+10s) did not
bracket the actual edit -- ENV1 wasn't visible in-frame at those exact
timestamps because the video's window layout changed. Extended to t=40s
by hand to find a frame where ENV1 was actually visible; this is a real
limitation of fixed-offset targeting worth fixing generically (video
window/panel layout is not guaranteed stable across a tutorial), not
specific to this video.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(ROOT))

from serum2.server.experience_record import ProductionExperienceRecord, save as save_experience

bundle = json.loads(
    (ROOT / "serum2/data/visual_frames/yt_89a28028e125/bundle_env1_release.json").read_text()
)
brain_result = json.loads(
    (ROOT / "serum2/data/visual_frames/yt_89a28028e125/brain_result.json").read_text()
)

now = datetime.now(timezone.utc).isoformat()
exp_id = "vlp1_mu6_env1release_%s" % datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

serum_ui_actions = [
    {
        "action": "load_and_configure", "stage": "executed",
        "evidence": {
            "mechanism": "Serum 2's own in-plugin preset browser (User folder)",
            "track_index": 0, "device_index": 0,
        },
        "recorded_at": now,
    },
    {
        "action": "verify", "stage": "verified",
        "evidence": {
            "method": "computer-use screenshot of the real Serum 2 ENV1 panel",
            "title_bar": "VLP1-Mu6-Env1Release36ms",
            "env1_readback": {"ATK": "4.0 ms", "HOLD": "0.0 ms", "DEC": "1.00 s", "SUS": "0.0 dB", "REL": "36 ms"},
        },
        "controls_matched": True,
        "mutation_applied": "Env1.Release: default (15 ms) -> 36 ms",
        "recorded_at": now,
    },
]

exp = ProductionExperienceRecord(
    experience_id=exp_id,
    run_id=exp_id,
    source_id=bundle["source_id"],
    source_url=bundle["source_url"],
    producer_request={
        "user_intent": "longer Env1.Release to 36 ms",
        "mode": "EXECUTE", "visual_mode": "NEVER",
    },
    brain_decision=brain_result,
    serum_mcp_call={
        "tool": "generate_preset",
        "args_specified": {"spec": {"name": "VLP1-Mu6-Env1Release36ms",
                                     "envelopes": [{"attack": 0.004, "release": 0.036}]}},
        "stage": "verified",
        "preset_path": brain_result["serum_preset_execution"]["preset_path"],
        "preset_sha256": brain_result["serum_preset_execution"]["preset_sha256"],
        "recorded_at": now,
    },
    serum_ui_actions=serum_ui_actions,
    visual_evidence=bundle,
    transcript_sufficiency=bundle.get("transcript_sufficiency"),
    outcome={
        "status": "STATE_REPRODUCTION_VERIFIED",
        "state_reproduction": "VERIFIED",
        "render_measurement": "UNAVAILABLE_NO_TOOL",
        "reason": (
            "SOURCE observed (native vision, real frame hashes): Env1.Release "
            "15ms @18.0s -> 36ms @40.0s. Producer Brain resolved note-release -> "
            "Env1.Release -> envelope_field_release (FRESH_4Q_VERIFIED), ADMITTED. "
            "Real execution via serum-mcp generate_preset -> Serum's own "
            "in-plugin preset browser -> Track 0. REPRODUCED (real Serum 2 "
            "ENV1 panel readback): Env1.Release = 36 ms, exact match to the "
            "observed source value. Acoustic render/measurement unavailable "
            "(no bounce-to-file tool in the AbletonMCP toolset, same known gap "
            "as the earlier Env1.Release candidate)."
        ),
        "mutation_applied": True,
    },
    provenance={
        "visual_evidence.frames": "acquire_frames_at_timestamps (real yt-dlp download + ffmpeg extraction, real sha256)",
        "visual_evidence.observed_canonical_states": "active Claude Code chat session, native vision on the exact saved frame files (ANTHROPIC_API_KEY 401, confirmed live)",
        "visual_evidence.canonical_diffs / interpretations": "serum2.producer.visual_reasoner.diff_observed_states / infer_from_diffs (deterministic, no model call)",
        "brain_decision": "serum2.producer.producer_brain.execute_producer_request (unmodified authority chain)",
        "serum_mcp_call": "mcp__serum-mcp__generate_preset, called directly by the orchestrating session",
        "serum_ui_actions": "mcp__computer-use__* tools against the real Serum 2 plugin window",
    },
)

exp_path = save_experience(exp)
print("Episode saved:", exp_path)
print("experience_id:", exp_id)
