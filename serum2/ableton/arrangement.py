"""Create a 16-bar MIDI clip in Ableton's Arrangement view using real MCP bridge.

This module implements the canonical ARRANGE stage: creating a real arrangement clip
on the Serum track, covering 16 bars. On Windows with Ableton MCP available, it performs
the actual operation. On other machines, it fails closed with BridgeUnavailable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from serum2.ableton.serum_track_loader import BridgeUnavailable


def create_16bar_arrangement(track_id: str = "", run_dir: str = "") -> Dict[str, Any]:
    """Create a 16-bar MIDI clip in the arrangement view on the Serum track.

    Args:
        track_id: Track identifier (run_id_native or similar). Not directly used
                  because we need the actual track_index. If provided, used for logging.
        run_dir: Run directory for storing arrangement artifacts.

    Returns:
        A dict with:
        - status: "CREATED_REAL_ARRANGEMENT" or "SKIPPED" (if bridge unavailable)
        - arrangement_path: path to saved arrangement.json (even if not actually created)
        - track_index: the 1-based track index where clip was created
        - clip_details: dict with clip metadata

    Raises:
        BridgeUnavailable: If the Ableton bridge is not available (non-Windows or no MCP).
        ValueError: If the arrangement could not be created for a different reason.
    """
    from serum2.ableton.serum_track_loader import bridge_status

    # Check if bridge is available (will raise BridgeUnavailable if not)
    status = bridge_status()
    if not status.get("available"):
        raise BridgeUnavailable(
            f"Ableton bridge not available: {status.get('reason', 'unknown reason')}. "
            "Run on Windows with Ableton Live 11.3+ and Serum 2.0.23 open."
        )

    # Now we know we're on Windows with the bridge available
    import sys
    import os
    mcp_dir = os.path.join(os.path.dirname(__file__), "ableton_mcp_extended")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)

    try:
        import server as ableton_mcp_server
    except ImportError as e:
        raise BridgeUnavailable(f"Could not import AbletonMCP server: {e}")

    # Get the last track (the one we just created the Serum instance on)
    # This is the track where load_and_verify created a MIDI track with Serum
    try:
        ableton = ableton_mcp_server.get_ableton_connection()
        session_info = ableton.send_command("get_session_info")
        track_count = session_info.get("track_count", 0)

        if track_count < 1:
            raise ValueError("No tracks in Ableton session")

        # The last track is the one we just created (with the Serum instance)
        track_index = track_count  # 1-based

        # Create a 16-bar MIDI clip in the arrangement view
        # In 4/4 time, 16 bars = 64 beats
        # Arrangement clips use beat positions (0-based)
        # Start at bar 1 = beat 0, end at bar 17 = beat 64
        result = ableton.send_command("create_arrangement_clip", {
            "track_index": track_index - 1,  # Convert to 0-based for the command
            "position": 0.0,  # Start at beat 0 (bar 1)
            "length": 64.0,   # 16 bars in 4/4 = 64 beats
        })

        clip_details = {
            "track_index": track_index,
            "start_beat": 0.0,
            "start_bar": 1,
            "length_beats": 64.0,
            "length_bars": 16,
            "time_signature": "4/4",
            "overlapped_clips": result.get("overlapped_clips", []),
        }

        # Save arrangement metadata to JSON
        arrangement_data = {
            "status": "CREATED_REAL_ARRANGEMENT",
            "track_id": track_id,
            "track_index": track_index,
            "clip_details": clip_details,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        run_dir_path = Path(run_dir)
        arrangement_path = run_dir_path / "arrangement.json"
        with open(arrangement_path, "w") as f:
            json.dump(arrangement_data, f, indent=2)

        return {
            "status": "CREATED_REAL_ARRANGEMENT",
            "arrangement_path": str(arrangement_path),
            "track_index": track_index,
            "clip_details": clip_details,
        }

    except Exception as e:
        # Any error in the MCP interaction should still raise BridgeUnavailable
        # because it indicates the bridge is not properly set up
        raise BridgeUnavailable(
            f"Failed to create arrangement on Ableton: {e}. "
            "Ensure Ableton Live is running with the AbletonMCP Remote Script enabled."
        )
