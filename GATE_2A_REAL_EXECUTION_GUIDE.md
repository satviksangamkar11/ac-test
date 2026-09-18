# Gate 2A Real Execution Guide

## Current State

**Gate 2A Architecture**: ✅ Complete and regression-tested
**Gate 2A Provenance**: ✅ Fully specified, linked to Golden Fixture (a5bbbfb)
**Gate 2A Proof**: ⏳ **PENDING_MANUAL_VERIFICATION** — requires real Ableton + Serum

## What Gate 2A Proves

Single episode `ep_prod_001`:
- Frozen Golden Production-Slice Fixture (immutable)
- Lead Bright.SerumPreset (SHA-256: `472618eb46084ce78794b5f36431c928cac95d134ac8c2d131da367b0c18c106`)
- Serum 2.0.21 VST3 plugin in Ableton
- 4-note MIDI phrase (C-D-E-F / pitches 60-62-64-65)
- Arranged to 16 bars @ 120 BPM
- Renders to WAV (32 seconds)

## Execution Steps

Run this in your Claude Code desktop environment (you have UI + Ableton MCP access):

```bash
cd "D:\ableton claude final best"
python serum2/orchestration/gate_2a_real_execution.py
```

The script will guide you through 7 steps:

### Step 1: UI Verification
- Open Ableton Live
- Locate track "Serum Lead" (index 0)
- Click Serum VST3 plugin
- **VERIFY in Serum UI**:
  - Preset name shows "Lead Bright"
  - Serum version is 2.0.21
  - No errors
- Type `CONFIRMED` to continue

### Step 2: Ableton MCP Orchestration
The script lists 6 MCP operations to execute:

```
1. create_midi_track(track_name="Serum Lead")
2. load_instrument_or_effect(instrument="Serum", device_index=0)
3. set_tempo(tempo_bpm=120)
4. create_clip(clip_type="MIDI", clip_length=4)
5. add_notes_to_clip(notes=[60,62,64,65])
6. duplicate_to_arrangement(clip_index=0, destination_positions=[0,4,8,12])
```

Execute these via Ableton MCP API (or manually replicate in UI).
Type `DONE` when complete.

### Step 3: Readback Verification
**HARD STOP CHECK** — Verify Ableton state before rendering:

```
[ ] Track 0 exists: "Serum Lead"
[ ] Serum VST3 loaded on Track 0
[ ] Serum shows "Lead Bright" preset
[ ] MIDI clip exists (4 bars)
[ ] MIDI notes: C3(60), D3(62), E3(64), F3(65)
[ ] Arrangement: 4 copies of clip (bars 0-4, 4-8, 8-12, 12-16 = 16 bars total)
[ ] Tempo: 120 BPM
```

**If ANY check fails**: STOP. Fix the actual state in Ableton.
Do NOT update the evidence record to hide mismatches.

Type `VERIFIED` to proceed.

### Step 4: Render
Execute the render via Ableton MCP `record_section()`:

```
record_section(
  start_time=0,
  duration=32 sec,  # 16 bars @ 120 BPM
  output_path=D:\ableton claude final best\serum2\orchestration\gate_2a_ep_prod_001_render.wav
)
```

Or manually export audio from the arrangement (16 bars, 44.1 kHz).

Type `RENDERED` when complete.

### Step 5: Artifact Verification
Script automatically verifies:
- WAV file exists
- File size > 1 KB (not empty)
- Readable as WAV
- Duration ≈ 32 seconds (±2 sec tolerance)
- Sample rate = 44100 Hz

**HARD STOP** if any check fails.

### Step 6: Update Evidence
Once all verifications pass, script updates evidence record:

```json
{
  "outcome": "PASS",
  "manual_verification": {
    "serum_ui_verified": true,
    "serum_preset_confirmed": "Lead Bright",
    "ableton_mcp_executed": true,
    "midi_readback_confirmed": true,
    "arrangement_readback_confirmed": true,
    "render_confirmed": true,
    "render_artifact_path": "...",
    "render_artifact_sha256": "...",
    "verification_timestamp": "..."
  }
}
```

### Step 7: Final Regression
Confirms:
- Golden fixture SHA-256 unchanged
- Outcome = PASS
- Render artifact recorded
- All 16 provenance fields present

## Hard Stop Conditions

The script **STOPS IMMEDIATELY** if:

```
❌ Serum preset is NOT "Lead Bright"
❌ Preset SHA-256 does NOT match 472618eb46084ce78794b5f36431c928cac95d134ac8c2d131da367b0c18c106
❌ Serum version is NOT 2.0.21
❌ MIDI notes are NOT exactly: 60, 62, 64, 65
❌ Arrangement is NOT 16 bars (4x4-bar clips)
❌ Tempo is NOT 120 BPM
❌ Ableton MCP operations are simulated (not real)
❌ Render WAV file is missing or unreadable
❌ Render duration is not ~32 seconds
```

**If any hard stop triggers:**
1. The script will print `[STOP] Gate 2A hard stop: <reason>`
2. Do NOT edit the evidence record to hide the mismatch
3. Fix the actual state in Ableton
4. Re-run the script

## Evidence Artifacts

After successful execution:

```
D:\ableton claude final best\serum2\orchestration\
├── gate_2a_ep_prod_001_final.json          # Updated evidence (outcome=PASS)
├── gate_2a_ep_prod_001_render.wav          # Render output (32 sec WAV)
└── gate_2a_execution.log                   # Execution log
```

## Next Steps

After Gate 2A PASS:
1. ✅ Golden Fixture (a5bbbfb) — immutable, proven
2. ✅ Gate 2A — Ableton integration, single 16-bar render proven
3. ⏳ Review Gate 2A evidence
4. ⏳ Decide: Is Ableton path sufficiently proven for full 908/396 production loop?

**DO NOT** start 908/396 scaling immediately after this render.
The architecture must be reviewed first.

## Key Constraints

- **Do not modify** the Golden Fixture or Serum preset
- **Do not touch** Serum parameters (no automation, no parameter edits)
- **Do not simulate** Ableton MCP calls (must be real)
- **Do not mask** state mismatches with evidence record edits
- **Single episode only**: ep_prod_001, one 16-bar render

## Questions?

If the script stops or you need clarification:
1. Check the hard stop condition message
2. Fix the actual Ableton state
3. Re-run the script

The evidence will only update to PASS when all verifications succeed.
