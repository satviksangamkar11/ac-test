# Superseded: Phase 4B.1 Architecture Designs

These reports document the attempt to build a custom VST3 state bridge between DawDreamer and Ableton-hosted Serum.

## Why superseded

**Decision:** Use `serum-mcp` as the Serum authoring actuator instead.

The VST3 state-bridge approach required implementing a missing Ableton MCP tool (`load_plugin_state()`), which was outside the scope.

The new architecture:
1. `serum-mcp` generates .SerumPreset files
2. Human manually loads preset once into Serum in Ableton
3. Ableton MCP handles MIDI, arrangement, transport, render
4. DawDreamer remains the validation oracle

This is simpler and doesn't require bridging infrastructure.

## Files in this folder

- `PHASE_4B1_CONTROL_GATE_REPORT.md` — Gate test: can Serum parameters be mutated through Ableton MCP?
  - Finding: NO. Only "Device On" wrapper exposed.
  - Blocked VST3 state bridge.

- `PHASE_4B1B_FORENSIC_FINDINGS.md` — Deep analysis of existing V8/VC2! infrastructure.
  - Finding: Infrastructure is complete but isolated from Ableton.
  - No mechanism to deliver state blob into running Serum instance.

## What was learned

The V8/VC2! state machinery (bridge.py, codec.py, vst3_state.py) is correctly built and can convert between .SerumPreset and VST3 state formats. This infrastructure is NOT wasted—it now serves validation instead of delivery.

## Current path

See parent directory for active Phase 4B.2 work.
