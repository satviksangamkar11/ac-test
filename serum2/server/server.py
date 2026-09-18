"""Producer Server — single MCP server.

External interface (4 tools):
  produce_from_youtube(url)
  advance_production(run_id, stage, evidence)
  get_production_status(run_id)
  list_productions()

Internal: delegates to production_pipeline.py which orchestrates all modules.

Run: python serum2/server/server.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mcp.server.fastmcp import FastMCP
from serum2.server.production_pipeline import (
    advance_production as _advance,
    get_status as _status,
    produce_from_youtube as _produce,
)
from serum2.server.state_machine import ProductionRun

mcp = FastMCP("producer-server")


@mcp.tool()
def produce_from_youtube(url: str) -> dict:
    """Start a production from a YouTube URL.

    Runs auto stages: transcript → knowledge → intent → admission.
    Returns next_action with instructions to call mcp__serum-mcp__generate_preset.
    Idempotent: same URL returns the existing run if not terminal.
    """
    run = _produce(url)
    return {
        "run_id": run.run_id,
        "state": run.state,
        "source_id": run.source_id,
        "knowledge_records": run.knowledge_record_count,
        "intent": run.intent,
        "error": run.error,
        "next_action": run.next_action,
    }


@mcp.tool()
def advance_production(run_id: str, stage: str, evidence: dict) -> dict:
    """Advance a production run past an agent-driven stage.

    Called after Claude executes a Serum/Ableton/render step and captures evidence.

    stage:
      PRESET_GENERATED    evidence: {preset_path, preset_sha256}
      SERUM_UI_CONFIGURED evidence: {screenshot_path, preset_name_confirmed, serum_version}
      SERUM_VERIFIED      evidence: {verified: true, screenshot_path}
      ABLETON_CONFIGURED  evidence: {track_index, tempo_bpm, clip_info, arrangement_clips}
      RENDERED            evidence: {render_path, file_size_bytes, duration_sec}
    """
    run = _advance(run_id, stage, evidence)
    return {
        "run_id": run.run_id,
        "state": run.state,
        "next_action": run.next_action,
        "episode_id": run.episode_id,
        "error": run.error,
    }


@mcp.tool()
def get_production_status(run_id: str) -> dict:
    """Get the current state and next_action for a production run."""
    return _status(run_id)


@mcp.tool()
def list_productions() -> list:
    """List recent production runs (newest first, max 20)."""
    return [
        {
            "run_id": r.run_id,
            "state": r.state,
            "youtube_url": r.youtube_url,
            "episode_id": r.episode_id,
            "created_at": r.created_at,
            "error": r.error,
        }
        for r in ProductionRun.load_all()[:20]
    ]


if __name__ == "__main__":
    mcp.run()
