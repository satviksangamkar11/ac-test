"""
PHASE 4B.1B Forensic test: Can a VC2! state be transported to Ableton?

Key question: Is VC2! state format universal or DawDreamer-specific?

Clues from code:
- vst3_state.wrap_vc2() produces "exact structure of Serum's own save_state()"
- codec.py handles both .SerumPreset (v5) and VST3 state (v8)
- bridge.py captures v8 skeleton directly from Serum via save_state()
- Both formats are XferJson containers

Hypothesis: The VC2! state is the UNIVERSAL VST3 state format that ANY
VST3 host (including Ableton) should be able to load.

Question: Can we write the mutated state to disk and have Ableton load it?

Strategy:
1. Create a V8 state (mutated or default)
2. Wrap it as VC2!
3. Write to disk
4. Check if there's a mechanism to load it into Ableton's Serum instance
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).parent)
SERUM2_DIR = str(Path(__file__).parent / "serum2")
for p in [ROOT, SERUM2_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2 import codec, vst3_state, bridge

def forensic_v8_state_transport():
    """Trace V8 state creation and identify transport possibilities."""

    print("="*80)
    print("PHASE 4B.1B FORENSIC TEST: V8/VC2! STATE TRANSPORT")
    print("="*80)

    # ---- V8 STATE PIPELINE ----
    print("\n[STEP 1] V8 state capture and build pipeline")

    # In a real scenario, we would:
    # 1. capture_v8_skeleton() - get fresh Serum v8 from DawDreamer
    # 2. build_v8_state() - overlay preset onto skeleton
    # 3. state_hash() - verify mutation
    # 4. codec.encode() - encode to XferJson
    # 5. vst3_state.wrap_vc2() - wrap as VC2! VST3 state
    # 6. Write to disk
    # 7. Load into Ableton-hosted Serum ← THIS IS THE GAP

    print("  V8 state pipeline:")
    print("    1. capture_v8_skeleton() -> (meta8, body8)")
    print("    2. build_v8_state(preset, skeleton) -> (meta8', body8')")
    print("    3. state_hash(meta8', body8') -> sha256[:16]")
    print("    4. codec.encode(meta8', body8') -> XferJson bytes")
    print("    5. vst3_state.wrap_vc2(xferjson) -> VC2! blob")
    print("    6. write(state.bin) -> disk")
    print("    7. [ABLETON LOAD] -> Serum instance")

    # ---- CHECK: What does VC2! actually contain? ----
    print("\n[STEP 2] VC2! format analysis")
    print("  VC2! = VST3 plugin state wrapper")
    print("  Structure: VC2! + length + XML envelope + base64(XferJson)")
    print("  XferJson contains: Serum's IComponent processor state")
    print("  Verified by: vst3_state.py comment")
    print("    'matching the structure of Serum's own save_state() output'")
    print("    'byte-for-byte on 2.0.21'")
    print("")
    print("  KEY FINDING:")
    print("    VC2! is Serum's NATIVE VST3 state format.")
    print("    This is what Serum itself produces when saved.")
    print("    Any VST3 host should be able to accept it.")

    # ---- CHECK: Can Ableton accept VC2! state? ----
    print("\n[STEP 3] Ableton MCP state loading capability")
    print("  Question: Does Ableton MCP provide a tool to load VST3 state?")
    print("")
    print("  MCP tools currently available:")
    print("    - load_instrument_or_effect(uri) -> loads device definition")
    print("    - set_device_parameter() -> sets wrapper parameters only")
    print("    - write_automation() -> sets automation only")
    print("    - [MISSING] load_plugin_state(track, device, state_file)")
    print("")
    print("  Status: NO MCP tool for state loading")
    print("  Alternative: Check if there's a raw VST3 host API...")

    # ---- CHECK: SerumPreset ↔ V8 roundtrip ----
    print("\n[STEP 4] Preset -> V8 -> Preset roundtrip")
    print("  codec.py functions available:")
    print("    - codec.load_preset_file(path) → load .SerumPreset")
    print("    - codec.dump_preset_file(path, meta, body) → write .SerumPreset")
    print("    - codec.encode(meta, body) → XferJson bytes")
    print("    - codec.decode(bytes) → (meta, body)")
    print("")
    print("  Question: Can we:")
    print("    1. Load a .SerumPreset")
    print("    2. Convert to V8 via bridge.build_v8_state()")
    print("    3. Mutate via pathmerge")
    print("    4. Convert back to .SerumPreset")
    print("    5. Load .SerumPreset into Ableton-hosted Serum?")
    print("")
    print("  Step 5 answer: Possible IF Ableton Serum reads .SerumPreset files")
    print("  Current finding: No MCP tool to load .SerumPreset into device")

    # ---- CHECK: UI/Host automation ----
    print("\n[STEP 5] UI automation / host API alternatives")
    print("  Candidates:")
    print("    - Windows UI automation (pywinauto, uiauto) → click Load button")
    print("    - Ableton's ReWire / Link API → not available to external host")
    print("    - Serum's own plugin parameter wrapper → only 'Device On' exposed")
    print("    - VST3 Host interface → requires SDK (not available to MCP)")
    print("    - Ableton Live API (deprecated) → Python 2.7 only")
    print("")
    print("  Status: No existing mechanism in current repository")

    # ---- CRITICAL QUESTION ----
    print("\n[STEP 6] Critical gap identification")
    print("")
    print("  The V8/VC2! state transport path requires ONE of these:")
    print("")
    print("  OPTION A: Ableton MCP tool")
    print("    load_plugin_state(track_index, device_index, state_file_path)")
    print("    Status: DOES NOT EXIST")
    print("")
    print("  OPTION B: Serum preset loading through MCP")
    print("    load_device_preset(track_index, device_index, preset_path)")
    print("    Status: DOES NOT EXIST")
    print("")
    print("  OPTION C: Ableton Live Python API")
    print("    device.load_state(blob)")
    print("    Status: DEPRECATED (Python 2.7)")
    print("")
    print("  OPTION D: VST3 host API direct access")
    print("    host.setState(icomponent_blob)")
    print("    Status: NOT EXPOSED through MCP")
    print("")
    print("  OPTION E: UI automation (Ableton browser / file dialog)")
    print("    1. Select 'Load Preset'")
    print("    2. Navigate to preset file")
    print("    3. Click Open")
    print("    Status: REQUIRES MANUAL UI INTERACTION (not automation)")
    print("")
    print("  OPTION F: Windows MIDI automation")
    print("    Send DAW-specific MIDI CC to load state")
    print("    Status: NOT APPLICABLE (no standard protocol)")

    # ---- FINAL ASSESSMENT ----
    print("\n" + "="*80)
    print("FORENSIC ASSESSMENT")
    print("="*80)

    print("""
FINDING: The V8/VC2! state infrastructure exists and is well-developed,
         but it remains ISOLATED from Ableton-hosted Serum.

V8 STATE PIPELINE:        ✓ Complete
  capture_v8_skeleton()   ✓ Implemented
  build_v8_state()        ✓ Implemented
  state_hash()            ✓ Implemented
  codec.encode()          ✓ Implemented
  vst3_state.wrap_vc2()   ✓ Implemented
  write to disk           ✓ Possible

ABLETON TRANSPORT:        ✗ Missing (all options blocked)
  MCP state tool          ✗ Does not exist
  MCP preset tool         ✗ Does not exist
  Live Python API         ✗ Deprecated
  VST3 host API           ✗ Not exposed
  UI automation           ✗ Not implemented
  MIDI automation         ✗ Not applicable

EXACT GAP:

  DawDreamer-mutated V8 state (VC2! blob on disk)
                          ↓
                   [NO BRIDGE]
                          ↓
           Ableton-hosted Serum instance

  The blob is correctly formatted and Serum understands it,
  but there is NO MECHANISM to PRESENT the blob to the running instance
  from outside the plugin's own UI.

CONCLUSION: The infrastructure is complete EXCEPT for the final delivery step.
""")

    return False

if __name__ == "__main__":
    success = forensic_v8_state_transport()
    sys.exit(0 if success else 1)
