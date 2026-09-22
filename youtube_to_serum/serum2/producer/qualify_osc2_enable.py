"""Qualification experiment for OSC2.Enable (Phase 3B.3).

Answers: "Can serum-mcp's file-based PresetSpec interface construct/
persist/reload a mutation of Osc B's enabled state as a CLASS of
operation?" This is STRUCTURAL evidence only -- no live Serum 2.0.21
plugin instance was involved and no audio was rendered or measured
(same honesty boundary as qualify_modulation_route.py's Instance B).

This script does not call serum-mcp itself, since this process cannot
invoke MCP tools directly. It packages ALREADY-OBTAINED real tool
results (generate_preset / describe_preset / edit_preset, called this
session) into the qualification evidence artifact.

Two representations of the SAME semantic target are recorded, kept
deliberately distinct (see docs/BINDING_DISCOVERY_FROZEN_5.md):

  REFERENCE / PLUGIN SURFACE evidence (already held, from
  SERUM2_SEMANTIC_INVENTORY_FINAL.json, MIXER.OSC_B.ENABLE):
      OSC2.Enable <-> VST3 host parameter "B Enable"

  PRESET / EXECUTION SURFACE evidence (this script):
      OSC2.Enable <-> PresetSpec.oscillators[1].enabled

The 8-step acceptance cycle (see docs/BINDING_DISCOVERY_FROZEN_5.md
Phase 3B.3 section) was run against a dedicated fixture preset:

  1. generate_preset  -> baseline fixture, oscillators=[{enabled:true},
                          {enabled:true}]
  2. describe_preset  -> baseline read: "Osc B: ON"
  3. edit_preset      -> oscillators=[{}, {enabled:false}]
  4. describe_preset  -> after-mutation read: "Osc B: off" (Osc A
                          unaffected -- mutation correctly scoped)
  5. sha256(file)     -> persisted on-disk bytes
                          C4A872A13F25F85C2C4D522B27A88E0FE98DF0028EDFBBF84E97EB6C08BFC7BB
  6. describe_preset  -> independent reload read: "Osc B: off" (matches
                          step 4 -- mutation survived a fresh file read)

Result: STRUCTURAL_VERIFIED (file-level). Live-Serum/CAUSAL verification
is a separate later stage (load this fixture into real Serum 2.0.21 via
Ableton and directly observe OSC B's enable state), not performed here.

Run: python -m serum2.producer.qualify_osc2_enable
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_QUALIFICATION_DIR = Path(__file__).parent.parent / "qualification"
_OUT_PATH = _QUALIFICATION_DIR / "osc2_enable_qualification.json"

_FIXTURE_PATH = (
    Path.home() / "Documents" / "Xfer" / "Serum 2 Presets" / "Presets" / "User"
    / "VLP1-Phase3B-OSC2Enable-Test.SerumPreset"
)


def build_qualification_evidence() -> dict:
    now = datetime.now(timezone.utc).isoformat()

    return {
        "semantic_target": "OSC2.Enable",
        "capability_key": "oscillator_field_OSC2-ENABLE",
        "qualified_at": now,
        "backend": "serum-mcp",
        "fixture_preset_path": str(_FIXTURE_PATH),
        "fixture_preset_sha256_after_mutation": (
            "C4A872A13F25F85C2C4D522B27A88E0FE98DF0028EDFBBF84E97EB6C08BFC7BB"
        ),
        "evidence_layers": {
            "reference_plugin_surface": {
                "route_type": "VST3_HOST_PARAMETER",
                "binding": "B Enable",
                "source": "SERUM2_SEMANTIC_INVENTORY_FINAL.json (MIXER.OSC_B.ENABLE)",
                "note": (
                    "Plugin-surface evidence only. serum-mcp cannot address "
                    "this control by VST3 parameter name -- it never loads "
                    "the Serum plugin or a DAW. Kept as a separate binding, "
                    "not collapsed into the preset-structural evidence below."
                ),
            },
            "preset_execution_surface": {
                "route_type": "SERUM_PRESET_STRUCTURAL_BINDING",
                "field_path": "oscillators[1].enabled",
                "source": "serum-mcp PresetSpec.OscillatorSpec.enabled",
                "operation_family": "TOGGLE",
            },
        },
        "acceptance_cycle": [
            {"step": 1, "action": "generate_preset", "result": "baseline fixture written, Osc B enabled=True"},
            {"step": 2, "action": "describe_preset (baseline read)", "result": "Osc B: ON"},
            {"step": 3, "action": "edit_preset (mutate oscillators[1].enabled=False)", "result": "applied"},
            {"step": 4, "action": "describe_preset (after-mutation read)", "result": "Osc B: off (Osc A unaffected)"},
            {"step": 5, "action": "state_changed check", "result": True, "before": "ON", "after": "off"},
            {"step": 6, "action": "persist (sha256 of on-disk file)", "result": "C4A872A13F25F85C2C4D522B27A88E0FE98DF0028EDFBBF84E97EB6C08BFC7BB"},
            {"step": 7, "action": "reload (independent describe_preset call)", "result": "Osc B: off"},
            {"step": 8, "action": "persistence_verified check", "result": True},
        ],
        "status": "STRUCTURAL_VERIFIED",
        "tier": "FILE_VERIFIED_ONLY",
        "notes": (
            "File-level structural qualification only. No live Serum 2.0.21 "
            "plugin instance was loaded and no audio was rendered/measured. "
            "This is NOT CAUSAL_VERIFIED -- a separate live-Serum verification "
            "stage (load fixture into Ableton -> real Serum 2.0.21 -> direct "
            "UI/readback observation) is required before any causal or "
            "audio-domain claim can be made for this capability."
        ),
    }


if __name__ == "__main__":
    _QUALIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    evidence = build_qualification_evidence()
    _OUT_PATH.write_text(json.dumps(evidence, indent=2))
    print("Qualification evidence written to", _OUT_PATH)
