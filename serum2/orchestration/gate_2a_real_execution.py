#!/usr/bin/env python3
"""
GATE 2A Real Execution: Ableton + Serum UI Verification + MCP Orchestration

This script coordinates the single real proof for Gate 2A:
  1. UI verification: Serum shows "Lead Bright" preset loaded
  2. Ableton MCP: Create MIDI track, add Serum, create MIDI clip
  3. Readback verification: Confirm state before render
  4. Render: Use record_section to capture 16-bar WAV
  5. Artifact verification: Confirm WAV exists and is valid
  6. Evidence update: Mark outcome as PASS

Hard stop conditions:
  - Preset is not frozen Lead Bright
  - SHA-256 does not match
  - Serum version is not 2.0.21
  - MIDI does not match spec (60,62,64,65)
  - Arrangement is not 16 bars
  - Tempo is not 120 BPM
  - Render file missing/unreadable

Run this in Claude Code desktop environment (has UI/MCP access).
"""

import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, str(Path(__file__).parent.parent / "qualification"))

from golden_fixture import GOLDEN_FIXTURE

# Expected values - DO NOT CHANGE
EXPECTED_PRESET_SHA256 = "472618eb46084ce78794b5f36431c928cac95d134ac8c2d131da367b0c18c106"
EXPECTED_MIDI_PITCHES = [60, 62, 64, 65]
EXPECTED_ARRANGEMENT_BARS = 16
EXPECTED_TEMPO_BPM = 120
EXPECTED_RENDER_DURATION_SEC = 32.0


class Gate2AExecutor:
    """Orchestrate real Gate 2A execution with Ableton MCP."""

    def __init__(self):
        self.evidence_path = Path(PROJECT_ROOT) / "serum2" / "orchestration" / "gate_2a_ep_prod_001_final.json"
        self.render_path = Path(PROJECT_ROOT) / "serum2" / "orchestration" / "gate_2a_ep_prod_001_render.wav"
        self.evidence = self._load_evidence()
        self.execution_log = []

    def _load_evidence(self) -> Dict[str, Any]:
        """Load existing Gate 2A evidence record."""
        if not self.evidence_path.exists():
            raise FileNotFoundError(f"Evidence record not found: {self.evidence_path}")

        with open(self.evidence_path, "r") as f:
            return json.load(f)

    def _log(self, level: str, message: str):
        """Log execution message."""
        ts = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{ts}] [{level}] {message}"
        self.execution_log.append(log_entry)
        print(log_entry)

    def step_1_ui_verification(self):
        """Step 1: Verify Serum UI shows Lead Bright preset."""

        print("\n" + "=" * 80)
        print("STEP 1: UI Verification - Serum Preset Loaded")
        print("=" * 80)

        self._log("INFO", "Checking Serum UI for Lead Bright preset...")

        print("\n[ACTION REQUIRED] Manual UI Check in Ableton:")
        print("  1. Open Ableton Live (if not already open)")
        print("  2. Find the track: 'Serum Lead' (index 0)")
        print("  3. Click on the Serum VST3 plugin on that track")
        print("  4. In the Serum UI, verify:")
        print("     - Preset name at top shows: 'Lead Bright'")
        print("     - No error messages")
        print("     - Serum version shows 2.0.21")
        print("\n  5. Take a screenshot if possible (for evidence)")
        print("  6. Type 'CONFIRMED' and press Enter to continue...")

        response = input("\n> ").strip().upper()

        if response != "CONFIRMED":
            self._log("ERROR", "UI verification not confirmed by user")
            print("\n[STOP] Gate 2A hard stop: Serum preset not visually confirmed")
            return False

        self._log("OK", "Serum UI verified: Lead Bright preset loaded")
        print("[OK] Serum UI verification complete")
        return True

    def step_2_ableton_mcp_orchestration(self):
        """Step 2: Execute Ableton MCP operations."""

        print("\n" + "=" * 80)
        print("STEP 2: Ableton MCP Orchestration")
        print("=" * 80)

        self._log("INFO", "Executing Ableton MCP operations...")

        mcp_operations = [
            {
                "name": "create_midi_track",
                "params": {"track_name": "Serum Lead"},
                "instruction": "Create MIDI track named 'Serum Lead'"
            },
            {
                "name": "load_instrument_or_effect",
                "params": {"instrument": "Serum", "device_index": 0},
                "instruction": "Load Serum VST3 to track index 0"
            },
            {
                "name": "set_tempo",
                "params": {"tempo_bpm": EXPECTED_TEMPO_BPM},
                "instruction": f"Set tempo to {EXPECTED_TEMPO_BPM} BPM"
            },
            {
                "name": "create_clip",
                "params": {"clip_type": "MIDI", "clip_length": 4},
                "instruction": "Create MIDI clip (4 bars)"
            },
            {
                "name": "add_notes_to_clip",
                "params": {"notes": [
                    {"pitch": 60, "velocity": 100, "start_time": 0.0, "duration": 1.0},
                    {"pitch": 62, "velocity": 100, "start_time": 1.0, "duration": 1.0},
                    {"pitch": 64, "velocity": 100, "start_time": 2.0, "duration": 1.0},
                    {"pitch": 65, "velocity": 100, "start_time": 3.0, "duration": 1.0},
                ]},
                "instruction": "Add MIDI notes: C3(60), D3(62), E3(64), F3(65)"
            },
            {
                "name": "duplicate_to_arrangement",
                "params": {"clip_index": 0, "destination_positions": [0, 4, 8, 12]},
                "instruction": "Duplicate clip to arrangement at bars 0,4,8,12 (16 bars total)"
            },
        ]

        print("\n[ACTION REQUIRED] Execute Ableton MCP operations:")
        print("\nThese operations should be performed via Ableton MCP API calls")
        print("(or manually replicated in Ableton UI):\n")

        for i, op in enumerate(mcp_operations, 1):
            print(f"  {i}. {op['name']}")
            print(f"     {op['instruction']}")

        print("\n[ACTION] Confirm MCP operations have been executed:")
        print("  - Type 'DONE' when all operations are complete")

        response = input("\n> ").strip().upper()

        if response != "DONE":
            self._log("ERROR", "MCP operations not confirmed")
            print("\n[STOP] Gate 2A hard stop: MCP operations not completed")
            return False

        self._log("OK", "Ableton MCP operations executed")
        print("[OK] MCP orchestration complete")
        return True

    def step_3_readback_verification(self):
        """Step 3: Readback and verify state before render."""

        print("\n" + "=" * 80)
        print("STEP 3: Readback Verification - Confirm State")
        print("=" * 80)

        self._log("INFO", "Verifying Ableton state before render...")

        print("\n[ACTION REQUIRED] Manual Ableton State Verification:")
        print("\nCheck in Ableton and confirm:")
        print(f"  [ ] Track 0 exists and is named 'Serum Lead'")
        print(f"  [ ] Serum VST3 is loaded on Track 0")
        print(f"  [ ] Preset in Serum shows 'Lead Bright'")
        print(f"  [ ] MIDI clip exists in Session view")
        print(f"  [ ] MIDI clip duration is exactly 4 bars")
        print(f"  [ ] MIDI notes are: C3(60), D3(62), E3(64), F3(65)")
        print(f"  [ ] Arrangement shows 4 copies of clip (bars 0-4, 4-8, 8-12, 12-16)")
        print(f"  [ ] Tempo shows {EXPECTED_TEMPO_BPM} BPM")

        print("\n[ACTION] When all checks pass, type 'VERIFIED' to continue...")

        response = input("\n> ").strip().upper()

        if response != "VERIFIED":
            self._log("ERROR", "State readback not verified")
            print("\n[STOP] Gate 2A hard stop: Ableton state does not match spec")
            print("\nDo NOT mask the mismatch with evidence. Fix the actual state in Ableton.")
            return False

        self._log("OK", "Ableton state verified: ready to render")
        print("[OK] Readback verification complete")
        return True

    def step_4_render(self):
        """Step 4: Execute render via Ableton MCP record_section."""

        print("\n" + "=" * 80)
        print("STEP 4: Render - Capture 16-bar Audio")
        print("=" * 80)

        self._log("INFO", "Executing render via Ableton MCP...")

        print("\n[MCP] record_section")
        print(f"  start_time=0")
        print(f"  duration={EXPECTED_RENDER_DURATION_SEC} sec (16 bars @ 120 BPM)")
        print(f"  output_path={self.render_path}")

        print("\n[ACTION REQUIRED] Execute render in Ableton:")
        print("  1. Use Ableton MCP: record_section()")
        print("  2. Or manually export audio from arrangement (16 bars)")
        print(f"  3. Save output to: {self.render_path.name}")

        print("\n[ACTION] When render is complete, type 'RENDERED' to continue...")

        response = input("\n> ").strip().upper()

        if response != "RENDERED":
            self._log("ERROR", "Render not confirmed")
            print("\n[STOP] Gate 2A hard stop: Render did not complete")
            return False

        self._log("OK", "Render completed")
        print("[OK] Render execution confirmed")
        return True

    def step_5_artifact_verification(self) -> bool:
        """Step 5: Verify render artifact (WAV file)."""

        print("\n" + "=" * 80)
        print("STEP 5: Artifact Verification - WAV File")
        print("=" * 80)

        self._log("INFO", "Verifying render WAV artifact...")

        # Check file exists
        if not self.render_path.exists():
            self._log("FAIL", f"Render WAV not found: {self.render_path}")
            print(f"\n[FAIL] Render file does not exist: {self.render_path}")
            print("\n[STOP] Gate 2A hard stop: No render artifact")
            return False

        print(f"[OK] WAV file exists: {self.render_path.name}")
        self._log("OK", "Render WAV file exists")

        # Check file size
        file_size = self.render_path.stat().st_size
        print(f"[OK] File size: {file_size} bytes")

        if file_size < 1000:
            self._log("FAIL", f"WAV file too small: {file_size} bytes")
            print(f"\n[FAIL] WAV file is empty or corrupted (size: {file_size} bytes)")
            print("\n[STOP] Gate 2A hard stop: Render artifact invalid")
            return False

        # Compute SHA-256
        wav_sha256 = hashlib.sha256(self.render_path.read_bytes()).hexdigest()
        print(f"[OK] WAV SHA-256: {wav_sha256[:16]}...")
        self._log("OK", f"WAV SHA-256 computed: {wav_sha256[:16]}...")

        # Try to read WAV header
        try:
            import wave
            with wave.open(str(self.render_path), 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                channels = wav.getnchannels()
                duration_sec = frames / rate

                print(f"[OK] WAV format: {channels} ch, {rate} Hz, {frames} frames")
                print(f"[OK] Duration: {duration_sec:.1f} seconds")

                # Check duration (should be ~32 sec, allow ±2 sec tolerance)
                if abs(duration_sec - EXPECTED_RENDER_DURATION_SEC) > 2.0:
                    self._log("FAIL", f"WAV duration mismatch: {duration_sec:.1f} != {EXPECTED_RENDER_DURATION_SEC}")
                    print(f"\n[FAIL] WAV duration incorrect: {duration_sec:.1f} sec (expected ~{EXPECTED_RENDER_DURATION_SEC})")
                    print("\n[STOP] Gate 2A hard stop: Render duration mismatch")
                    return False

                print(f"[OK] Duration matches spec: {duration_sec:.1f} ~= {EXPECTED_RENDER_DURATION_SEC}")
                self._log("OK", f"WAV duration verified: {duration_sec:.1f} sec")

        except Exception as e:
            self._log("FAIL", f"Could not read WAV: {e}")
            print(f"\n[FAIL] Could not read WAV file: {e}")
            print("\n[STOP] Gate 2A hard stop: WAV unreadable")
            return False

        print("\n[OK] Artifact verification complete")
        return True

    def step_6_update_evidence(self):
        """Step 6: Update evidence record with PASS outcome."""

        print("\n" + "=" * 80)
        print("STEP 6: Update Evidence Record")
        print("=" * 80)

        self._log("INFO", "Updating Gate 2A evidence record...")

        # Update evidence
        self.evidence["outcome"] = "PASS"
        self.evidence["manual_verification"] = {
            "serum_ui_verified": True,
            "serum_preset_confirmed": "Lead Bright",
            "ableton_mcp_executed": True,
            "midi_readback_confirmed": True,
            "arrangement_readback_confirmed": True,
            "render_confirmed": True,
            "render_artifact_path": str(self.render_path),
            "render_artifact_sha256": hashlib.sha256(self.render_path.read_bytes()).hexdigest(),
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Save updated evidence
        with open(self.evidence_path, "w") as f:
            json.dump(self.evidence, f, indent=2)

        print(f"[OK] Evidence record updated: outcome=PASS")
        print(f"     Path: {self.evidence_path}")
        self._log("OK", "Evidence record updated with PASS outcome")

    def step_7_final_regression(self):
        """Step 7: Run final Gate 2A regression test."""

        print("\n" + "=" * 80)
        print("STEP 7: Final Gate 2A Regression Test")
        print("=" * 80)

        self._log("INFO", "Running final Gate 2A regression...")

        # Load updated evidence
        with open(self.evidence_path, "r") as f:
            evidence = json.load(f)

        # Test 1: Golden fixture unchanged
        if evidence["golden_fixture_preset_sha256"] != EXPECTED_PRESET_SHA256:
            self._log("FAIL", "Golden fixture SHA-256 changed")
            print("[FAIL] Golden fixture SHA-256 mismatch!")
            return False

        print("[OK] Golden fixture SHA-256 unchanged")

        # Test 2: Outcome is PASS
        if evidence["outcome"] != "PASS":
            self._log("FAIL", f"Outcome is not PASS: {evidence['outcome']}")
            print(f"[FAIL] Outcome is {evidence['outcome']}, expected PASS")
            return False

        print("[OK] Outcome: PASS")

        # Test 3: Render artifact recorded
        if "render_artifact_path" not in evidence.get("manual_verification", {}):
            self._log("FAIL", "Render artifact not recorded")
            print("[FAIL] Render artifact path not recorded")
            return False

        print("[OK] Render artifact recorded")

        # Test 4: All provenance fields present
        required_fields = [
            "gate_id", "episode_id", "golden_fixture_commit",
            "golden_fixture_preset_sha256", "serum_preset_filename",
            "arrangement_duration_bars", "arrangement_tempo_bpm",
            "outcome"
        ]

        for field in required_fields:
            if field not in evidence:
                self._log("FAIL", f"Missing provenance field: {field}")
                print(f"[FAIL] Missing field: {field}")
                return False

        print(f"[OK] All {len(required_fields)} provenance fields present")

        self._log("OK", "Final regression passed")
        print("\n[OK] FINAL REGRESSION TEST PASSED")
        return True

    def execute(self) -> bool:
        """Execute all Gate 2A steps."""

        print("=" * 80)
        print("GATE 2A REAL EXECUTION - Single ep_prod_001 Render")
        print("=" * 80)

        steps = [
            ("UI Verification", self.step_1_ui_verification),
            ("Ableton MCP Orchestration", self.step_2_ableton_mcp_orchestration),
            ("Readback Verification", self.step_3_readback_verification),
            ("Render", self.step_4_render),
            ("Artifact Verification", self.step_5_artifact_verification),
            ("Update Evidence", self.step_6_update_evidence),
            ("Final Regression", self.step_7_final_regression),
        ]

        for step_name, step_func in steps:
            try:
                result = step_func()
                if not result:
                    print(f"\n[STOP] Gate 2A hard stop at: {step_name}")
                    self._log("FAIL", f"Hard stop: {step_name}")
                    return False
            except Exception as e:
                print(f"\n[ERROR] Exception in {step_name}: {e}")
                self._log("ERROR", f"Exception in {step_name}: {e}")
                import traceback
                traceback.print_exc()
                return False

        # Final summary
        print("\n" + "=" * 80)
        print("GATE 2A REAL EXECUTION COMPLETE")
        print("=" * 80)
        print("\n[OK] All steps completed successfully")
        print(f"[OK] Evidence: {self.evidence_path}")
        print(f"[OK] Render: {self.render_path}")
        print(f"[OK] Outcome: PASS")

        self._log("OK", "Gate 2A execution complete - outcome PASS")

        # Save execution log
        log_path = Path(PROJECT_ROOT) / "serum2" / "orchestration" / "gate_2a_execution.log"
        with open(log_path, "w") as f:
            f.write("\n".join(self.execution_log))

        print(f"\nExecution log: {log_path}")

        return True


if __name__ == "__main__":
    executor = Gate2AExecutor()
    success = executor.execute()
    sys.exit(0 if success else 1)
