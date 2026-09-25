# Serum track loader: qualification experiments (2026-09-25/26)

Scratch scripts and evidence from qualifying "load a .SerumPreset into Serum 2.0.23 inside Ableton Live 12 via Serum's native
drag/drop". The production code is `../ableton-mcp-extended/MCP_Server/serum_loader.py` (+ `create_serum_track` in `server.py`).
These are experiments, not a test suite. Nothing here is a verified-correctness claim: the only success signal is visual.

## Scripts
- `ableton_windows.py` : list visible top-level windows of the Ableton process (class, title, rect). G1 window identification.
- `live_cmd.py`        : send one raw command to the AbletonMCP Remote Script on localhost:9877 (showed a fresh Serum exposes only "Device On").
- `serum_tree.py`      : dump the Serum window's child tree; one VSTGUI child registers an OLE drop target (so WM_DROPFILES is the wrong mechanism).
- `capture.py`         : PrintWindow capture of the Serum editor (works while occluded).
- `ole_drop.py`        : the drop experiment. Final version starts the drag from a window owned by this process (see below).

## Evidence
- `evidence/before.png`  : Serum editor on a fresh track, preset `- Init -`.
- `evidence/after.png`, `after2.png` : drop attempts that FAILED (still `- Init -`), from earlier versions of `ole_drop.py`.
- `evidence/after3.png`  : after the working drop, header reads `Prague Lead - Phase 5`, artist `serum-mcp`, Osc B/C on, filter MG Ladder.
- `evidence/drop.log`, `drop2.log`, `drop3.log` : failing runs (no QueryContinueDrag callbacks; DoDragDrop blocked).
- `evidence/drop4.log`   : working run (40 QueryContinueDrag calls, DoDragDrop -> effect 7).

## What the experiments established (Live 12 Suite, Serum 2.0.23, sha256 9293eb90...)
1. Loading Serum from the browser onto a new track auto-opens the editor only if Live's main window is not minimized.
   Window: class `Vst3PlugWindow`, title `Serum 2/<track name>`.
2. `DoDragDrop` only runs its loop when the mouse press begins on a window owned by the calling process. Pressing on the
   taskbar or another app's window (attempts 1-3) blocks forever with zero callbacks.
3. With a process-owned 60x60 source window, real mouse_event press/move/release onto the preset-name bar loads the preset.

## Limits
- Only 4 presets run end-to-end; the 20-consecutive-run qualification was NOT done.
- No readback of Serum parameter state. Status is `LOADED_VISUAL` (drop accepted + preset-name bar changed), never "verified".
- Scripts hardcode the scratch paths/nonces used in the session.
