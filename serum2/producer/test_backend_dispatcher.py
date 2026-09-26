"""Tests for backend_dispatcher.py -- Phase E.

Proves the dispatch invariant against REAL ProducerBrain results: a Serum
operation's admitted plan is always attributed to SERUM_MCP, a DAW/session
operation's to ABLETON_MCP, and a refused operation to NONE -- using the
actual producer_brain.py execute() output, not a mock.
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_serum_concept_dispatches_to_serum_mcp():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.backend_dispatcher import dispatched_backend, SERUM
    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(user_intent="make the note sustain longer"))
    assert result.execution_status == "ADVISORY_ONLY"
    assert dispatched_backend(result) == SERUM
    print("[PASS] test_serum_concept_dispatches_to_serum_mcp")


def test_modulation_route_dispatches_to_serum_mcp():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.backend_dispatcher import dispatched_backend, SERUM
    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "LFO1", "destination": "Filter 1 Freq"},
    ))
    assert result.execution_status == "MODULATION_ROUTE_PLAN_READY"
    assert dispatched_backend(result) == SERUM
    print("[PASS] test_modulation_route_dispatches_to_serum_mcp")


def test_filter_cutoff_dispatches_to_ableton_mcp():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.backend_dispatcher import dispatched_backend, ABLETON
    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(user_intent="make the filter cutoff higher"))
    assert result.execution_status in ("ADVISORY_ONLY", "MCP_PLAN_READY")
    assert dispatched_backend(result) == ABLETON
    print("[PASS] test_filter_cutoff_dispatches_to_ableton_mcp")


def test_refused_operation_dispatches_to_none():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.backend_dispatcher import dispatched_backend, NONE
    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "unknown_thing", "destination": "unknown_widget"},
    ))
    assert result.execution_status == "REFUSED_OUT_OF_SCOPE"
    assert dispatched_backend(result) == NONE
    print("[PASS] test_refused_operation_dispatches_to_none")


if __name__ == "__main__":
    test_serum_concept_dispatches_to_serum_mcp()
    test_modulation_route_dispatches_to_serum_mcp()
    test_filter_cutoff_dispatches_to_ableton_mcp()
    test_refused_operation_dispatches_to_none()
    print("\nAll backend dispatcher tests passed.")
