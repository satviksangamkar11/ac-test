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

## Qualification result (2026-09-26): SERUM_NATIVE_PRESET_LOAD = QUALIFIED
- `qual20.py` ran the unchanged `create_serum_track` 20 consecutive times, cycling the 4 presets in one Live/Serum session.
- `evidence/qual20_results.json`: 20/20 LOADED_VISUAL, 0 failures, 0 rollback/cleanup leaks, 0 wrong Serum version,
  drop effect 7 every run, preset-name bar changed 5.3-6.3 % (threshold 2 %), track renamed to the preset every run.
- `evidence/qual20_attempt1_interrupted_by_live_restart.json`: first attempt, 15/15 then run 16 broke because Ableton was
  restarted mid-run. It exposed a rollback that deleted by track INDEX (could hit a user track after a restart); fixed to
  delete by the nonce NAME, and the rollback result is now in the returned JSON. The 20/20 run used the fixed code.
- Smoke test through the real MCP server then found the tool's `serum_loader` import failed when server.py runs as a
  script (the campaign imported it as a package, so could not see this). Fixed with a fallback import; after that the
  real tool returned LOADED_VISUAL, renamed the track, and a missing file returned FAILED: PRESET_FILE_INVALID with no side effects.

## Limits
- Qualification = native drag/drop loading only. State verification is NOT included. Parameter reproduction is NOT included.
- No readback of Serum parameter state. Status is `LOADED_VISUAL` (drop accepted + preset-name bar changed), never "verified".
- `qual20.py` takes the presets, run count and output path as arguments (nothing built in). The run recorded here was:
  `qual20.py --out qual20_results.json --runs 20 "Prague Lead - Phase 5.SerumPreset" probe_noise_pink.SerumPreset probe_lfo4_retrig.SerumPreset probe_noise_white.SerumPreset`
- The other scripts are one-off experiment tools; `ole_drop.py`/`capture.py`/`serum_tree.py` take the nonce/file on the command line.
