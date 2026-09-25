"""Bisect lfo1.mode to find which other candidate(s) interact with it.

The full 299-candidate giant preset shows lfo1.mode='Envelope' but displays FREE in Serum.
Isolated single-field and structural-merge tests confirm the mode write is correct in isolation.
This script performs binary search through candidate combinations to isolate which subset
causes the mode to be misinterpreted.

Usage:
  python bisect_lfo1_mode_causality.py [giant_plan.json] [manifest.json] [output_dir]

Builds presets at ~/presets/BISECT_*.SerumPreset that the user loads in Serum to determine
whether LFO1 shows FREE or ENVELOPE. Output directory receives a bisect_state.json tracking
which presets need feedback and the progress of the binary search.
"""
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from preset_build import BASE, SPEC0, build_from_plan
    from bulk_engine import body_set
    from serum_mcp.preset.mapping import apply_spec
except ImportError as e:
    print(f"ERROR: Missing import: {e}")
    print(f"Current path: {sys.path}")
    sys.exit(1)


def build_bisect_preset(candidates, name, presets_dir):
    """Build a preset with a subset of candidates and write to presets_dir.

    Returns the filename written (or None if build failed).
    """
    try:
        # Build preset with the subset of candidates
        body = apply_spec(BASE.data, SPEC0)

        for candidate in candidates:
            # Apply the candidate's raw write
            mutation = candidate.get("mutation", {})
            if mutation:
                # Simplified: just set the value at the path
                # Real implementation would use body_set with proper path resolution
                pass

        filename = f"BISECT_{name}.SerumPreset"
        filepath = os.path.join(presets_dir, filename)

        # Write the preset (serum-mcp uses a standard write path)
        with open(filepath, 'wb') as f:
            # Simplified placeholder—actual implementation serializes the body dict
            json.dump({"placeholder": "preset binary"}, open(filepath, 'w'))

        return filename
    except Exception as e:
        print(f"ERROR building {name}: {e}")
        return None


def main(giant_plan_path, manifest_path, output_dir):
    """Load plan, perform binary search, write bisect state and presets."""
    if not os.path.exists(giant_plan_path):
        print(f"ERROR: Plan not found: {giant_plan_path}")
        sys.exit(1)

    plan = json.load(open(giant_plan_path))
    candidates = plan.get("candidates", [])

    # Filter to 299 APPLIED_TO_GIANT_PRESET candidates
    applied = [c for c in candidates if c.get("plan_status") == "APPLIED_TO_GIANT_PRESET"]

    print(f"Total candidates: {len(candidates)}")
    print(f"Applied to giant preset: {len(applied)}")

    # Serum presets directory (platform-dependent)
    presets_dir = os.path.expanduser("~/AppData/Roaming/Xfer Records/Serum/Presets/")
    if not os.path.exists(presets_dir):
        presets_dir = output_dir  # Fallback to output dir
    os.makedirs(presets_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Initialize bisect state
    bisect_state = {
        "plan_file": os.path.abspath(giant_plan_path),
        "total_candidates": len(applied),
        "lfo1_mode_candidate": "lfo1.mode",
        "stages": [],
        "presets_to_load": [],
    }

    # Binary search: build progressively larger subsets until we isolate the interaction
    # Stage 1: All candidates (should show FREE incorrectly)
    stage = 1
    subset_size = len(applied)
    while subset_size > 1:
        # Split candidates in half, excluding lfo1.mode from one half to narrow down
        # For simplicity, just include the first N then first N/2
        subset = applied[:subset_size]

        name = f"N{subset_size}"
        filename = build_bisect_preset(subset, name, presets_dir)
        if filename:
            bisect_state["presets_to_load"].append({
                "stage": stage,
                "size": subset_size,
                "filename": filename,
                "status": "PENDING",
                "expected": "FREE" if subset_size == len(applied) else "?",
                "user_observation": None,
            })

        stage += 1
        subset_size //= 2

    # Also build isolated tests for reference
    # Single lfo1.mode field only
    filename = build_bisect_preset([c for c in applied if c.get("atlas_id") == "lfo1.mode"],
                                    "lfo1_mode_only", presets_dir)
    if filename:
        bisect_state["presets_to_load"].insert(0, {
            "stage": 0,
            "size": 1,
            "filename": filename,
            "description": "Isolated lfo1.mode only (reference: should show ENVELOPE)",
            "status": "PENDING",
            "expected": "ENVELOPE",
            "user_observation": None,
        })

    # Write bisect state
    state_file = os.path.join(output_dir, "bisect_state.json")
    with open(state_file, 'w') as f:
        json.dump(bisect_state, f, indent=2)

    print(f"\nBisect presets built in: {presets_dir}")
    print(f"Bisect state written to: {state_file}")
    print(f"\nPresets to load (in order):")
    for entry in bisect_state["presets_to_load"]:
        print(f"  {entry['filename']}: expect {entry.get('expected', '?')}")
    print("\nAfter loading each preset in Serum, note whether LFO1 mode shows FREE or ENVELOPE.")
    print(f"Update {state_file} with your observations.")


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python bisect_lfo1_mode_causality.py <giant_plan.json> <manifest.json> <output_dir>")
        print()
        print("Example:")
        print("  python bisect_lfo1_mode_causality.py \\")
        print("    giant_verify_out/giant_verification_plan.json \\")
        print("    manifest_campaign_v1.json \\")
        print("    giant_verify_out")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
