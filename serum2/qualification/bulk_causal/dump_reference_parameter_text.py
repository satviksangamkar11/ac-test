"""Dump get_parameter_text for all parameters from VERIFY_REFERENCE_FULL.SerumPreset.

Usage:
  python dump_reference_parameter_text.py [preset_path] [output_json_path]

Loads the reference preset through serum_backend.py, calls get_parameter_text for every
parameter in the backend's parameter list, and writes a JSON file mapping atlas_id -> display_text.

Output format:
  {
    "preset_file": "/path/to/VERIFY_REFERENCE_FULL.SerumPreset",
    "parameters": {
      "atlas_id": "display_text_label",
      ...
    },
    "missing_parameters": ["atlas_id", ...]  // atlas IDs with no get_parameter_text result
  }
"""
import json
import sys
import os

# Adjust path as needed for serum_backend import
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

try:
    from serum_backend import SerumBackend
except ImportError:
    print("ERROR: serum_backend module not found. Ensure it is in the path.")
    print(f"Current path: {sys.path}")
    sys.exit(1)


def main(preset_path, output_path):
    """Load preset and dump parameter display text."""
    if not os.path.exists(preset_path):
        print(f"ERROR: Preset not found: {preset_path}")
        sys.exit(1)

    print(f"Loading {preset_path}...")
    backend = SerumBackend()
    backend.load(preset_path)

    # Get all available parameters
    all_params = backend.list_parameters()

    output = {
        "preset_file": os.path.abspath(preset_path),
        "parameters": {},
        "missing_parameters": [],
    }

    print(f"Found {len(all_params)} parameters, dumping display text...")

    for param_id in sorted(all_params.keys()):
        try:
            display_text = backend.get_parameter_text(param_id)
            if display_text is not None:
                output["parameters"][param_id] = display_text
            else:
                output["missing_parameters"].append(param_id)
        except Exception as e:
            print(f"  WARNING: {param_id} failed: {e}")
            output["missing_parameters"].append(param_id)

    print(f"Successfully retrieved text for {len(output['parameters'])} parameters.")
    print(f"Missing/failed: {len(output['missing_parameters'])}")

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Output written to {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python dump_reference_parameter_text.py <preset_path> <output_path>")
        print()
        print("Example:")
        print("  python dump_reference_parameter_text.py \\")
        print("    giant_verify_out/VERIFY_REFERENCE_FULL.SerumPreset \\")
        print("    giant_verify_out/reference_parameter_text.json")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
