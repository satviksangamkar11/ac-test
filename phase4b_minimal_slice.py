"""
STEP 2: Minimal real Ableton slice
- 16-bar session (64 beats)
- One MIDI track
- Serum loaded
- One 4-beat MIDI note (C3, velocity 80)
- Readback confirmation
"""

import json

def minimal_slice_spec():
    """Returns the minimal slice configuration."""
    return {
        "session": {
            "tempo": 120,
            "signature": "4/4",
            "duration_bars": 16,
            "duration_beats": 64,
        },
        "track": {
            "index": 0,
            "type": "MIDI",
            "name": "Serum Track",
        },
        "device": {
            "type": "Serum",
            "index": 0,
        },
        "clip": {
            "track_index": 0,
            "clip_index": 0,
            "length_beats": 4.0,
            "notes": [
                {
                    "pitch": 60,
                    "start_time": 0.0,
                    "duration": 4.0,
                    "velocity": 80,
                }
            ],
        },
        "actions": [
            "create_midi_track at index 0",
            "load Serum to device_index 0 on track 0",
            "create_clip at track 0, clip_index 0, length 4.0 beats",
            "add_notes_to_clip with C3 4-beat note",
            "confirm readback: track info, device parameters, clip notes",
        ],
    }

if __name__ == "__main__":
    spec = minimal_slice_spec()
    print(json.dumps(spec, indent=2))
