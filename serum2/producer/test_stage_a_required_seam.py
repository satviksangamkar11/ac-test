"""Proves the Brain's transcript-first visual path never falls back to
VisualReasoner's legacy Anthropic SDK path. Without stage_a_observation it
must stop honestly at STAGE_A_REQUIRED (frames acquired, vision not yet
performed); with a real Claude-Code-produced observation dict supplied, it
must proceed through diff/infer using ingest_stage_a_observation() only.

Uses the real frame already acquired this session (yt_89a28028e125) and the
real observation JSON already written by direct visual inspection -- not a
synthetic fixture -- so this exercises the actual seam end to end.
"""
import json
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


_TRANSCRIPT_SEGMENTS = [
    {"timestamp_sec": 22.0, "text": "I'm going to take a little bit off the attack and the release"},
]


def test_transcript_first_visual_path_stops_at_stage_a_required_without_observation():
    """Exercises the exact private method the Brain's execute() calls for
    the transcript-first visual path -- avoids the unrelated, pre-existing
    source_url subprocess-ingestion gap (see [[project_producer_server]]
    memory: passing source_url through the full execute() path calls a
    missing phase1_ingest.py subprocess) so this test isolates only the
    Stage-A seam this change actually touched."""
    from serum2.producer.producer_brain import ProducerBrain

    brain = ProducerBrain()
    bundle = brain._acquire_and_reason_visual_transcript_first(
        source_url="https://www.youtube.com/watch?v=mU6PB--pf9w",
        transcript_segments=_TRANSCRIPT_SEGMENTS,
        transcript_sufficiency=None,
        stage_a_observation=None,
    )
    assert bundle.reasoning_error is not None
    assert bundle.reasoning_error.startswith("STAGE_A_REQUIRED"), bundle.reasoning_error
    assert bundle.frames, "frames must already be acquired before stopping for Stage A"
    assert bundle.ui_state_snapshots == [], "no vision must have run yet"
    print("[PASS] test_transcript_first_visual_path_stops_at_stage_a_required_without_observation")


def test_transcript_first_visual_path_proceeds_with_real_stage_a_observation():
    from serum2.producer.producer_brain import ProducerBrain

    obs_path = Path(ROOT) / "serum2" / "data" / "visual_frames" / "yt_89a28028e125" / "stage_a_observation_00018000.json"
    stage_a_observation = json.loads(obs_path.read_text())

    brain = ProducerBrain()
    bundle = brain._acquire_and_reason_visual_transcript_first(
        source_url="https://www.youtube.com/watch?v=mU6PB--pf9w",
        transcript_segments=_TRANSCRIPT_SEGMENTS,
        transcript_sufficiency=None,
        stage_a_observation=stage_a_observation,
    )
    assert bundle.reasoning_error is None, bundle.reasoning_error
    assert len(bundle.ui_state_snapshots) == 1
    assert len(bundle.ui_state_snapshots[0].controls) == 24
    assert bundle.stage_a_provenance == {
        "observer": "claude_code", "observation_mode": "direct_visual_inspection",
        "model_api_used": False,
    }
    print("[PASS] test_transcript_first_visual_path_proceeds_with_real_stage_a_observation")


if __name__ == "__main__":
    test_transcript_first_visual_path_stops_at_stage_a_required_without_observation()
    test_transcript_first_visual_path_proceeds_with_real_stage_a_observation()
    print("\nAll Stage-A seam tests passed.")
