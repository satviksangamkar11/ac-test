"""Mandatory regression test: observe_frames() must not scope its census to
what the transcript mentioned.

Scenario: the narrator says only "Change the release." while the frame
visibly contains several other legible controls (attack, decay, sustain,
an oscillator's unison/detune/wavetable, and an LFO's shape/rate). The
model response used here is a canned stand-in for a real API call (no
network/API key needed for this test -- _call_model is monkeypatched),
shaped exactly like a real full-census response. The test fails if any
unmentioned control is missing from bundle.ui_state_snapshots -- that is
the one thing this test exists to catch: the transcript silently becoming
the enumeration scope again.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


_CANNED_FULL_CENSUS_RESPONSE = {
    "stage_a_provenance": {
        "observer": "claude_code",
        "observation_mode": "direct_visual_inspection",
        "model_api_used": False,
    },
    "frames": [
        {
            "frame_id": "frame_test_00018000",
            "timestamp_sec": 18.0,
            "serum_visible": True,
            "visible_panel": "OSC+ENV1+LFO3",
            "controls": [
                {"control_id": "env1.release", "control_type": "knob", "label": "REL", "value": "15 ms", "unit": "ms", "status": "OBSERVED", "screen_region": "ENV1 panel", "confidence": 0.95},
                {"control_id": "env1.attack", "control_type": "knob", "label": "ATK", "value": "1.0 ms", "unit": "ms", "status": "OBSERVED", "screen_region": "ENV1 panel", "confidence": 0.9},
                {"control_id": "env1.decay", "control_type": "knob", "label": "DEC", "value": "1.00 s", "unit": "s", "status": "OBSERVED", "screen_region": "ENV1 panel", "confidence": 0.9},
                {"control_id": "env1.sustain", "control_type": "knob", "label": "SUS", "value": "-inf dB", "unit": "dB", "status": "OBSERVED", "screen_region": "ENV1 panel", "confidence": 0.85},
                {"control_id": "oscA.unison", "control_type": "knob", "label": "UNISON", "value": "1", "unit": None, "status": "OBSERVED", "screen_region": "OSC A row", "confidence": 0.9},
                {"control_id": "oscA.detune", "control_type": "knob", "label": "DETUNE", "value": None, "unit": None, "status": "OBSERVED", "screen_region": "OSC A row", "confidence": 0.4},
                {"control_id": "oscA.wavetable", "control_type": "dropdown", "label": "wavetable", "value": "Basic Shapes", "unit": None, "status": "OBSERVED", "screen_region": "OSC A header", "confidence": 0.8},
                {"control_id": "lfo3.shape", "control_type": "other", "label": "curve", "value": "triangle", "unit": None, "status": "OBSERVED", "screen_region": "LFO3 panel", "confidence": 0.7},
                {"control_id": "lfo3.rate", "control_type": "other", "label": "RATE", "value": "1/4", "unit": None, "status": "OBSERVED", "screen_region": "LFO3 panel", "confidence": 0.7},
            ],
            "mod_routes": [],
            "target_reading": {"target": "Env1.Release", "value": "15 ms", "confidence": 0.95},
            "unknown": [],
        },
    ]
}


def test_observe_frames_captures_controls_the_transcript_never_named():
    from serum2.producer.visual_reasoner import VisualReasoner
    from serum2.source.visual_evidence import VisualEvidenceBundle, VisualFrameArtifact

    bundle = VisualEvidenceBundle(
        source_url="https://www.youtube.com/watch?v=test", source_id="yt_test", video_id="test",
    )
    bundle.frames = [VisualFrameArtifact(
        frame_id="frame_test_00018000", source_url=bundle.source_url, source_id=bundle.source_id,
        video_id=bundle.video_id, timestamp_sec=18.0,
        artifact_path=__file__,  # any existing file -- only used for an existence check
        artifact_hash="deadbeef",
    )]

    reasoner = VisualReasoner(api_key="test-key-not-used")
    # Only _call_model is faked -- everything else (prompt building, JSON
    # parsing, UIStateSnapshot construction) runs for real, same as a live
    # API call would exercise.
    reasoner._call_model = lambda system_prompt, content: (
        SimpleNamespace(
            content=[SimpleNamespace(text=json.dumps(_CANNED_FULL_CENSUS_RESPONSE))],
            model="claude-haiku-4-5-20251001", id="test-req", usage=None,
        ),
        None,
    )

    # The narrator, per the scenario, said only "Change the release." --
    # target_hint reflects that: it must NOT narrow the resulting census.
    result = reasoner.observe_frames(bundle, target_hint="Env1.Release")

    assert result.reasoning_error is None, result.reasoning_error
    assert result.stage_a_provenance == {
        "observer": "claude_code", "observation_mode": "direct_visual_inspection",
        "model_api_used": False,
    }, "provenance must be captured verbatim onto the bundle -- machine-checkable, not just claimed"
    assert len(result.ui_state_snapshots) == 1
    snapshot = result.ui_state_snapshots[0]
    captured_ids = {c.control_id for c in snapshot.controls}

    required = {
        "env1.release", "env1.attack", "env1.decay", "env1.sustain",
        "oscA.unison", "oscA.detune", "oscA.wavetable",
        "lfo3.shape", "lfo3.rate",
    }
    missing = required - captured_ids
    assert not missing, (
        "observe_frames() dropped controls the transcript never mentioned "
        "(scope must be the whole visible UI, not the transcript): %s" % missing
    )

    # The narrator-named control's value must still be exactly what was
    # observed, unchanged by the census broadening.
    release = next(c for c in snapshot.controls if c.control_id == "env1.release")
    assert release.value == "15 ms"

    # A knob visible but numerically illegible (oscA.detune) must stay
    # value=None, never a guessed number, while still being present.
    detune = next(c for c in snapshot.controls if c.control_id == "oscA.detune")
    assert detune.value is None
    assert detune.status == "OBSERVED"  # visible, just not numerically legible

    print("[PASS] test_observe_frames_captures_controls_the_transcript_never_named")


if __name__ == "__main__":
    test_observe_frames_captures_controls_the_transcript_never_named()
    print("\nAll full-census regression tests passed.")
