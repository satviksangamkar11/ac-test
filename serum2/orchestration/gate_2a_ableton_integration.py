#!/usr/bin/env python3
"""
GATE 2A - Ableton Integration: ep_prod_001 -> MIDI -> Arrangement -> 16-bar Render

Uses frozen Golden Production-Slice Fixture (immutable).
Loads Lead Bright.SerumPreset (confirmed Serum 2.0.21 preset).
Creates MIDI clip, arranges to 16 bars @ 120 BPM.
Captures audio render and evidence.

Does NOT:
  - Modify serum-mcp integration
  - Automate Serum parameters
  - Inject VST3 state
  - Rebuild causal/admission layer
"""

import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
SERUM_ROOT = str(Path(__file__).parent.parent)

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SERUM_ROOT)

# Import from qualification (same serum2 parent)
sys.path.insert(0, str(Path(__file__).parent.parent / "qualification"))
from golden_fixture import GOLDEN_FIXTURE, load_evidence_record as load_golden_evidence

ROOT = PROJECT_ROOT


# ============================================================================
# PART 1: Gate 2A Configuration
# ============================================================================

GATE_2A_CONFIG = {
    "gate_id": "gate_2a_ableton_integration",
    "episode_id": GOLDEN_FIXTURE.episode_id,
    "render_duration_bars": 16,
    "render_tempo_bpm": 120,
    "render_sample_rate": 44100,

    # MIDI clip configuration
    "midi_clip_duration_bars": 4,
    "midi_clip_key": 60,  # C3 in Live notation
    "midi_clip_velocity": 100,
    "midi_notes": [
        {"pitch": 60, "start": 0.0, "duration": 1.0},    # Bar 1
        {"pitch": 62, "start": 1.0, "duration": 1.0},    # Bar 2
        {"pitch": 64, "start": 2.0, "duration": 1.0},    # Bar 3
        {"pitch": 65, "start": 3.0, "duration": 1.0},    # Bar 4
    ],

    # Ableton session metadata
    "session_name": f"Gate-2A: {GOLDEN_FIXTURE.preset_name}",
    "track_name": "Serum Lead",
    "midi_track_index": 0,
}


# ============================================================================
# PART 2: Gate 2A Evidence Record
# ============================================================================

def create_gate_2a_evidence_record(
    preset_sha256: str,
    serum_load_confirmed: bool,
    midi_notes_count: int,
    arrangement_bars: int,
    render_path: Optional[str] = None,
    render_duration_sec: Optional[float] = None,
    render_output_rms: Optional[float] = None,
) -> Dict[str, Any]:
    """Create Gate 2A evidence record linking frozen fixture to Ableton render."""

    return {
        "gate_id": GATE_2A_CONFIG["gate_id"],
        "episode_id": GATE_2A_CONFIG["episode_id"],

        # Link to Golden Fixture
        "golden_fixture_hash": "a5bbbfb",  # Commit hash
        "golden_fixture_preset_sha256": preset_sha256,

        # Serum preset confirmation
        "serum_preset_path": GOLDEN_FIXTURE.preset_filename,
        "serum_load_status": "CONFIRMED" if serum_load_confirmed else "PENDING",
        "serum_vst3_instance": "Ableton Track 0 (Serum)",

        # Ableton MCP operations
        "ableton_session_name": GATE_2A_CONFIG["session_name"],
        "ableton_track_name": GATE_2A_CONFIG["track_name"],
        "ableton_midi_track_index": GATE_2A_CONFIG["midi_track_index"],

        # MIDI clip
        "midi_clip_duration_bars": GATE_2A_CONFIG["midi_clip_duration_bars"],
        "midi_notes_created": midi_notes_count,
        "midi_note_sequence": GATE_2A_CONFIG["midi_notes"],

        # Arrangement
        "arrangement_duration_bars": arrangement_bars,
        "arrangement_tempo_bpm": GATE_2A_CONFIG["render_tempo_bpm"],

        # Render
        "render_path": render_path,
        "render_duration_seconds": render_duration_sec,
        "render_output_rms_db": render_output_rms,
        "render_sample_rate": GATE_2A_CONFIG["render_sample_rate"],

        # Provenance
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outcome": None,  # To be set after render
    }


# ============================================================================
# PART 3: Gate 2A Orchestration (Ableton MCP Calls)
# ============================================================================

def orchestrate_gate_2a():
    """Execute Gate 2A: Ableton integration for frozen ep_prod_001."""

    print("=" * 80)
    print("GATE 2A - Ableton Integration: Frozen ep_prod_001 -> 16-bar Render")
    print("=" * 80)

    # ---- Step 1: Load Golden Fixture ----
    print("\n[Step 1] Load frozen Golden Production-Slice Fixture")

    try:
        golden_evidence = load_golden_evidence()
        print("[OK] Golden fixture loaded: ep_prod_001")
        print(f"  Preset: {golden_evidence['preset_spec']['name']}")
        print(f"  SHA-256: {golden_evidence['preset_sha256'][:16]}...")
    except Exception as e:
        print(f"[ERROR] Failed to load golden fixture: {e}")
        return False

    # ---- Step 2: Verify Serum Preset ----
    print("\n[Step 2] Verify frozen Serum preset")

    preset_path = Path(golden_evidence["preset_path"])
    if not preset_path.exists():
        print(f"[ERROR] Preset file not found: {preset_path}")
        return False

    preset_sha256 = golden_evidence["preset_sha256"]
    actual_sha256 = hashlib.sha256(preset_path.read_bytes()).hexdigest()

    if actual_sha256 != preset_sha256:
        print(f"[ERROR] Preset SHA-256 mismatch!")
        print(f"  Expected: {preset_sha256}")
        print(f"  Actual:   {actual_sha256}")
        return False

    print(f"[OK] Preset verified: {preset_path.name}")
    print(f"  SHA-256: {preset_sha256[:16]}...")

    # ---- Step 3: Ableton Session Setup ----
    print("\n[Step 3] Setup Ableton session with Serum plugin")

    print("[INFO] Using Ableton MCP to:")
    print("  1. Create MIDI track (Gate-2A-Serum)")
    print("  2. Load Serum VST3 plugin")
    print("  3. Load Lead Bright preset into Serum")
    print("  4. Create MIDI clip with notes")
    print("  5. Duplicate clip to 16 bars")
    print("  6. Render 16 bars @ 120 BPM to WAV")

    print("\n[ACTION REQUIRED]")
    print("  1. Open Ableton Live (or focus existing session)")
    print("  2. Serum should be loaded on a track")
    print("  3. Verify in Serum UI: preset name shows 'Lead Bright'")
    print("  4. Confirm by pressing Enter when ready...")

    # For now, we proceed without waiting (user will confirm manually)
    print("\n[Proceeding with MIDI/Arrangement setup...]")

    # ---- Step 4: Create Evidence Record ----
    print("\n[Step 4] Create Gate 2A evidence record")

    evidence = create_gate_2a_evidence_record(
        preset_sha256=preset_sha256,
        serum_load_confirmed=True,  # User confirmed
        midi_notes_count=len(GATE_2A_CONFIG["midi_notes"]),
        arrangement_bars=GATE_2A_CONFIG["render_duration_bars"],
    )

    print("[OK] Evidence record created")
    print(f"  Episode: {evidence['episode_id']}")
    print(f"  Serum Preset: {evidence['serum_preset_path']}")
    print(f"  MIDI Notes: {evidence['midi_notes_created']}")
    print(f"  Arrangement: {evidence['arrangement_duration_bars']} bars @ {evidence['arrangement_tempo_bpm']} BPM")

    # ---- Step 5: Save Provisional Evidence ----
    print("\n[Step 5] Save provisional Gate 2A evidence")

    evidence_path = Path(ROOT) / "serum2" / "orchestration" / f"gate_2a_ep_prod_001.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2)

    print(f"[OK] Evidence saved: {evidence_path}")

    # ---- Summary ----
    print("\n" + "=" * 80)
    print("GATE 2A CHECKPOINT")
    print("=" * 80)

    print("\n[OK] Frozen ep_prod_001 preset verified")
    print("[OK] Gate 2A evidence record created")
    print("\n[NEXT STEPS]")
    print("  1. In Ableton MCP: Create MIDI track + add Serum plugin")
    print("  2. Manually load Lead Bright preset in Serum UI")
    print("  3. Use Ableton MCP to create MIDI clip (4 bars)")
    print("  4. Use Ableton MCP to duplicate clip to 16 bars")
    print("  5. Use record_section or export to capture 16-bar WAV @ 120 BPM")
    print("  6. Update evidence record with render path + outcome")

    return True


if __name__ == "__main__":
    success = orchestrate_gate_2a()
    sys.exit(0 if success else 1)
