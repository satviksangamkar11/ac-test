#!/usr/bin/env python3
"""
Regression Test: Gate 2A Provenance Integrity

Validates that Gate 2A evidence record:
  - Links to correct Golden Fixture (a5bbbfb)
  - Verifies preset SHA-256 matches
  - All MCP operations documented
  - Render path and outcome recorded
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, str(Path(__file__).parent.parent / "qualification"))

from golden_fixture import GOLDEN_FIXTURE


def test_gate_2a_provenance_integrity():
    """Test: Gate 2A evidence links to frozen Golden Fixture."""

    print("=" * 80)
    print("TEST: Gate 2A Provenance Integrity")
    print("=" * 80)

    # Load Gate 2A evidence
    print("\n[Step 1] Load Gate 2A evidence record")

    evidence_path = Path(PROJECT_ROOT) / "serum2" / "orchestration" / "gate_2a_ep_prod_001_final.json"

    if not evidence_path.exists():
        print(f"[FAIL] Evidence record not found: {evidence_path}")
        return False

    with open(evidence_path, "r") as f:
        evidence = json.load(f)

    print(f"[OK] Evidence loaded: {evidence_path}")

    # Test 1: Episode ID matches
    print("\n[Test 1] Episode ID matches Golden Fixture")

    if evidence["episode_id"] != GOLDEN_FIXTURE.episode_id:
        print(f"[FAIL] Episode ID mismatch: {evidence['episode_id']} != {GOLDEN_FIXTURE.episode_id}")
        return False

    print(f"[OK] Episode: {evidence['episode_id']}")

    # Test 2: Preset SHA-256 matches
    print("\n[Test 2] Preset SHA-256 matches Golden Fixture")

    golden_sha = GOLDEN_FIXTURE.preset_sha256
    if evidence["golden_fixture_preset_sha256"] != golden_sha:
        print(f"[FAIL] Preset SHA-256 mismatch")
        print(f"  Expected: {golden_sha}")
        print(f"  Got:      {evidence['golden_fixture_preset_sha256']}")
        return False

    print(f"[OK] Preset SHA-256: {golden_sha[:16]}...")

    # Test 3: Golden Fixture commit linked
    print("\n[Test 3] Golden Fixture commit linked")

    expected_commit = "a5bbbfb"
    if evidence["golden_fixture_commit"] != expected_commit:
        print(f"[FAIL] Commit hash mismatch: {evidence['golden_fixture_commit']} != {expected_commit}")
        return False

    print(f"[OK] Golden Fixture commit: {evidence['golden_fixture_commit']}")

    # Test 4: Required evidence fields present
    print("\n[Test 4] Required Gate 2A evidence fields present")

    required_fields = [
        "gate_id",
        "episode_id",
        "timestamp",
        "golden_fixture_commit",
        "golden_fixture_preset_sha256",
        "serum_preset_filename",
        "serum_preset_sha256_verified",
        "serum_vst3_loaded_in_track",
        "ableton_mcp_calls",
        "midi_notes_created",
        "arrangement_duration_bars",
        "arrangement_tempo_bpm",
        "render_path",
        "render_sample_rate",
        "render_duration_bars",
        "outcome",
    ]

    for field in required_fields:
        if field not in evidence:
            print(f"[FAIL] Missing required field: {field}")
            return False

    print(f"[OK] All {len(required_fields)} required fields present")

    # Test 5: Arrangement metadata correct
    print("\n[Test 5] Arrangement metadata correct")

    if evidence["arrangement_duration_bars"] != 16:
        print(f"[FAIL] Expected 16 bars, got {evidence['arrangement_duration_bars']}")
        return False

    if evidence["arrangement_tempo_bpm"] != 120:
        print(f"[FAIL] Expected 120 BPM, got {evidence['arrangement_tempo_bpm']}")
        return False

    if evidence["render_duration_bars"] != 16:
        print(f"[FAIL] Render duration should be 16 bars, got {evidence['render_duration_bars']}")
        return False

    print(f"[OK] Arrangement: {evidence['arrangement_duration_bars']} bars @ {evidence['arrangement_tempo_bpm']} BPM")

    # Test 6: MIDI configuration valid
    print("\n[Test 6] MIDI configuration valid")

    if evidence["midi_notes_created"] < 1:
        print(f"[FAIL] No MIDI notes created")
        return False

    if len(evidence["midi_note_pitches"]) != evidence["midi_notes_created"]:
        print(f"[FAIL] MIDI note count mismatch")
        return False

    print(f"[OK] MIDI notes: {evidence['midi_notes_created']} (pitches: {evidence['midi_note_pitches']})")

    # Test 7: Ableton MCP operations documented
    print("\n[Test 7] Ableton MCP operations documented")

    mcp_ops = evidence["ableton_mcp_calls"]
    expected_ops = [
        "create_midi_track",
        "load_instrument_or_effect",
        "create_clip",
        "add_notes_to_clip",
        "duplicate_to_arrangement",
        "set_tempo",
        "record_section",
    ]

    for op in expected_ops:
        if not any(op in call for call in mcp_ops):
            print(f"[FAIL] Missing MCP operation: {op}")
            return False

    print(f"[OK] All {len(expected_ops)} MCP operations documented")

    # Test 8: Outcome status recorded
    print("\n[Test 8] Outcome status recorded")

    outcome = evidence["outcome"]
    if outcome not in ["PENDING_MANUAL_VERIFICATION", "PASS", "FAIL"]:
        print(f"[FAIL] Invalid outcome: {outcome}")
        return False

    print(f"[OK] Outcome: {outcome}")

    return True


def main():
    """Run Gate 2A regression test."""

    success = test_gate_2a_provenance_integrity()

    print("\n" + "=" * 80)

    if success:
        print("[OK] GATE 2A REGRESSION TEST PASSED")
        print("\nProvenance integrity verified:")
        print("  - Golden Fixture commit linked (a5bbbfb)")
        print("  - Preset SHA-256 verified")
        print("  - Ableton MCP operations documented")
        print("  - Arrangement metadata correct (16 bars @ 120 BPM)")
        print("  - MIDI configuration valid")
        print("\nReady for manual Ableton verification and render.")
        print("=" * 80)
        return 0
    else:
        print("[FAIL] GATE 2A REGRESSION TEST FAILED")
        print("Provenance integrity check failed.")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
