"""The bridge: gets a real .SerumPreset into a real, running, Ableton-hosted Serum 2.0.23, and prepares the shape
a Direct-UI readback needs.

This is a THIN wrapper around the qualified 20/20 loader in `ableton_mcp_extended/` (cherry-picked verbatim from
`feature/serum-track-loader`, unmodified) -- it does not reimplement any of the OLE drag/drop mechanics. Those only
work on Windows, with Ableton Live running an AbletonMCP-compatible Remote Script on localhost:9877, and Serum 2.0.23
already loaded into a track. On any other machine (including this cloud container) `load_and_verify` fails closed
with BridgeUnavailable and an exact remedy -- it never returns a fake LOADED_VISUAL/VERIFIED result.

    from serum2.ableton.serum_track_loader import load_and_verify
    result = load_and_verify("/path/to/generated.SerumPreset")
    # result["status"] in ("LOADED_VISUAL", "FAILED", "BRIDGE_UNAVAILABLE")

`load_and_verify` proves the drop was accepted and the preset-name bar changed (`LOADED_VISUAL`) -- exactly what
`create_serum_track` itself proves, no more. It does NOT produce a `DIRECT_UI` readback: no code here can look at
the loaded Serum's actual control values (that's real visual inspection, by a human or Claude Code looking at the
real GUI). `build_ui_readback_request` instead returns the exact watch-list `state_comparator.compare_ui` needs
filled in, so that inspection step is mechanical, not another hand-authored-differently-every-time JSON blob.
"""
from __future__ import annotations

import json
import platform
import socket
from typing import Any, Dict, List, Optional

PINNED_SERUM_SHA256 = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"  # Serum 2.0.23
DEFAULT_HOST, DEFAULT_PORT = "localhost", 9877


class BridgeUnavailable(RuntimeError):
    """The live-Ableton bridge cannot run here. Carries the exact remedy, never a fake result."""


def _check_platform() -> None:
    if platform.system() != "Windows":
        raise BridgeUnavailable(
            "The Ableton bridge only runs on Windows (real OLE drag/drop into a real Serum window). "
            "This is running on %r. Run this step on the Windows machine with Ableton Live + Serum 2.0.23, "
            "from a checkout that has serum2/ableton/ableton_mcp_extended/ and its AbletonMCP Remote Script "
            "(port %d) running." % (platform.system(), DEFAULT_PORT))


def _check_connection(host: str, port: int) -> None:
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return
    except OSError as e:
        raise BridgeUnavailable(
            "Could not reach an AbletonMCP Remote Script at %s:%d (%s). Start Ableton Live with the "
            "AbletonMCP Remote Script enabled (Preferences > Link/Tempo/MIDI > Control Surfaces), then retry."
            % (host, port, e))


def load_and_verify(preset_path: str, track_name: str = "", host: str = DEFAULT_HOST,
                     port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Loads `preset_path` into a new track's Serum 2 instance via the qualified native drag/drop loader.

    Fails closed (raises BridgeUnavailable) rather than returning any result at all when this isn't a machine
    that can actually do it. On a capable machine, delegates entirely to `create_serum_track` -- same code,
    same qualification, same failure modes (SERUM_VERSION_MISMATCH, DRAG_DROP_REJECTED, etc.)."""
    _check_platform()
    _check_connection(host, port)

    import sys
    import os
    mcp_dir = os.path.join(os.path.dirname(__file__), "ableton_mcp_extended")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    import server as ableton_mcp_server  # the cherry-picked, unmodified qualified server module

    raw = ableton_mcp_server.create_serum_track(ctx=None, preset_path=preset_path, name=track_name)
    result = json.loads(raw)
    return result


def build_ui_readback_request(watched_controls: List[str]) -> Dict[str, Any]:
    """The exact skeleton a real Direct-UI observation must fill in, matching what
    `serum2.execution.state_comparator.compare_ui` requires (`route: "DIRECT_UI"`, a `values` map). This function
    performs NO observation itself -- every value stays null until whoever is actually looking at the loaded
    Serum instance (this session, or the user) fills it in from what they see."""
    return {
        "route": "DIRECT_UI",
        "plugin": "Serum 2", "expected_version_sha256": PINNED_SERUM_SHA256,
        "instructions": "For each control below, read its ACTUAL displayed value in the real, loaded Serum "
                        "instance and fill it in. Do not infer, guess, or copy the expected/compiled value.",
        "values": {c: None for c in watched_controls},
    }


def bridge_status(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Non-raising status check, for a pipeline that wants to report the bridge's availability rather than fail."""
    try:
        _check_platform()
        _check_connection(host, port)
        return {"available": True}
    except BridgeUnavailable as e:
        return {"available": False, "reason": str(e)}
