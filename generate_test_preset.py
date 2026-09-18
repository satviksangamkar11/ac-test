#!/usr/bin/env python3
"""Generate a minimal test preset via serum-mcp for Serum 2.0.21 compatibility."""

import json
import sys
from pathlib import Path

# Add serum-mcp to path
sys.path.insert(0, str(Path("D:/serum-mcp/src")))

from serum_mcp.generation.spec import PresetSpec, OscillatorSpec
from serum_mcp.tools.generate_preset import generate_preset

# Minimal saw lead: Osc A only, default filter, simple Env 1
spec = PresetSpec(
    name="Test Init Saw Lead",
    description="Basic init-style saw lead for Serum 2.0.21 compatibility test",
    oscillators=[
        OscillatorSpec(
            enabled=True,
            octave=0.0,
            volume=0.75,
            wavetable="default",
            unison=1.0,
        ),
        OscillatorSpec(enabled=False),
        OscillatorSpec(enabled=False),
        OscillatorSpec(enabled=False),  # Noise
        OscillatorSpec(enabled=False),  # Sub
    ],
    filters=[{"enabled": False}],  # No filter
)

try:
    result = generate_preset(spec=spec)
    print(f"✓ Preset generated successfully")
    print(f"  Path: {result}")
except Exception as e:
    print(f"✗ Failed to generate preset: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
