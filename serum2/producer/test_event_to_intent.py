"""Tests for event_to_intent.py -- Phase F.

End-to-end: a ProductionEvent built from real observed data (the actual
mU6/k6 episodes' values) produces candidates that resolve/admit through the
REAL, unmodified Producer Brain -- not a mock. Proves the whole Phase A-F
chain composes: UIStateSnapshot diff -> ProductionEvent -> candidates ->
real resolution -> real admission.
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_scalar_change_produces_a_candidate_that_admits():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual
    from serum2.producer.event_to_intent import production_event_to_requests
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest

    diff = {"changed_controls": [{"control_id": "env1.release", "before": "15 ms", "after": "36 ms"}],
            "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual("evt", 18.0, 40.0, ["f1", "f2"], diff,
                                        transcript_excerpt="the release", transcript_timestamp_sec=22.0)
    candidates = production_event_to_requests(event)
    assert len(candidates) == 1
    assert "36 ms" in candidates[0]["request_kwargs"]["user_intent"]

    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(**candidates[0]["request_kwargs"]))
    assert result.resolved_concept == "note-release"
    assert result.execution_status == "SERUM_PRESET_PLAN_READY"
    print("[PASS] test_scalar_change_produces_a_candidate_that_admits")


def test_unmentioned_change_still_produces_its_own_candidate():
    """The core motivating case: transcript names release, but attack also
    changed -- both must become independent candidates, not just the named one."""
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual
    from serum2.producer.event_to_intent import production_event_to_requests

    diff = {"changed_controls": [
        {"control_id": "env1.release", "before": "15 ms", "after": "36 ms"},
        {"control_id": "env1.attack", "before": "1.0 ms", "after": "4.0 ms"},
    ], "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual("evt", 18.0, 40.0, ["f1", "f2"], diff,
                                        transcript_excerpt="take a bit off the release", transcript_timestamp_sec=22.0)
    candidates = production_event_to_requests(event)
    control_ids = {c["source_control_id"] for c in candidates}
    assert control_ids == {"env1.release", "env1.attack"}, (
        "attack must produce a candidate even though only release was named in the transcript"
    )
    print("[PASS] test_unmentioned_change_still_produces_its_own_candidate")


def test_route_change_produces_add_modulation_route_candidate_that_admits():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual
    from serum2.producer.event_to_intent import production_event_to_requests
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest

    diff = {"changed_controls": [], "added_routes": [{"source": "lfo0", "destination": "filter0.cutoff"}], "removed_routes": []}
    event = fuse_transcript_and_visual("evt", 409, 423, ["f3"], diff,
                                        transcript_excerpt="drag LFO onto cutoff", transcript_timestamp_sec=413)
    candidates = production_event_to_requests(event)
    assert len(candidates) == 1
    assert candidates[0]["request_kwargs"]["operation"] == "ADD_MODULATION_ROUTE"

    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(**candidates[0]["request_kwargs"]))
    assert result.execution_status == "MODULATION_ROUTE_PLAN_READY"
    print("[PASS] test_route_change_produces_add_modulation_route_candidate_that_admits")


def test_unrecognized_control_produces_no_candidate_not_a_guess():
    from serum2.producer.evidence_fusion import fuse_transcript_and_visual
    from serum2.producer.event_to_intent import production_event_to_requests

    diff = {"changed_controls": [{"control_id": "unison2.detune_amount", "before": "5%", "after": "20%"}],
            "added_routes": [], "removed_routes": []}
    event = fuse_transcript_and_visual("evt", 0, 5, ["f1"], diff, transcript_excerpt=None)
    candidates = production_event_to_requests(event)
    assert candidates == [], "no known vocabulary for this control -- must not guess a concept"
    print("[PASS] test_unrecognized_control_produces_no_candidate_not_a_guess")


if __name__ == "__main__":
    test_scalar_change_produces_a_candidate_that_admits()
    test_unmentioned_change_still_produces_its_own_candidate()
    test_route_change_produces_add_modulation_route_candidate_that_admits()
    test_unrecognized_control_produces_no_candidate_not_a_guess()
    print("\nAll event-to-intent tests passed.")
