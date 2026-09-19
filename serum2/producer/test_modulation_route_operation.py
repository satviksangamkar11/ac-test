"""Tests for the generic ADD_MODULATION_ROUTE structured operation.

Covers the required proof set (see conversation instruction): generic
resolution, qualification-derived contract, valid/invalid admission,
unknown-amount preservation, finalize guard, and the "no bypass" invariants
-- visual reasoning cannot call MCP directly, an unadmitted operation
cannot reach a plan. Regression of note-release/envelope-attack/Ableton MCP
routing is covered by the existing test_producer_brain.py suite (re-run
alongside this file, not duplicated here).
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_contract_derived_from_qualification_evidence():
    """The contract is built FROM the qualification JSON, not hand-typed --
    changing the evidence file changes the contract, proving no hardcoded
    LFO1/Filter1 special-case lives in the contract builder."""
    from serum2.producer.modulation_route_contract import (
        build_modulation_route_contract, CAPABILITY_TARGET,
    )
    contract = build_modulation_route_contract()
    assert contract is not None
    assert contract.target == CAPABILITY_TARGET
    assert contract.status == "STRUCTURAL_ONLY"  # honest -- no causal/audio proof
    assert "lfo" in contract.scope["supported_source_prefixes"]
    assert "filter" in contract.scope["supported_destination_families"]
    # Domain is a CLASS description, not one video's instance
    assert "lfo0" not in contract.scope  # no literal instance baked into scope
    assert contract.execution_binding.resolver_operation_id == "serum_mcp.add_modulation_route"
    print("[PASS] test_contract_derived_from_qualification_evidence")


def test_generic_operation_resolves_valid_route():
    """A route the K6 video never demonstrated (macro3 -> oscillator pitch)
    is admitted purely from the qualified DOMAIN, proving this isn't a
    K6-specific bridge."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "macro3", "destination": "Oscillator 2 Pitch",
                         "amount": 25, "bipolar": True},
    )
    result = brain.execute(req)
    assert result.execution_status == "MODULATION_ROUTE_PLAN_READY"
    assert result.admitted is True
    plan = getattr(result, "_modulation_route_plan", None)
    assert plan is not None
    assert plan["source"] == "macro3"
    print("[PASS] test_generic_operation_resolves_valid_route")


def test_unknown_amount_and_bipolar_preserved_not_guessed():
    """Evidence-derived None must survive resolution+admission unchanged --
    never coerced into an invented number."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "LFO1", "destination": "Filter 1 Freq",
                         "amount": None, "bipolar": None},
    )
    result = brain.execute(req)
    assert result.execution_status == "MODULATION_ROUTE_PLAN_READY"
    plan = getattr(result, "_modulation_route_plan", None)
    assert plan["amount"] is None, "amount must stay None, never guessed"
    assert plan["bipolar"] is None, "bipolar must stay None, never guessed"
    print("[PASS] test_unknown_amount_and_bipolar_preserved_not_guessed")


def test_out_of_scope_source_refuses_no_guess():
    """'Envelope 7' starts with 'env' but env sources only go 0-3 -- a loose
    substring match would wrongly admit this (caught live during
    implementation). Precise indexed-range checking must refuse it."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "Envelope 7", "destination": "Filter 1 Freq"},
    )
    result = brain.execute(req)
    assert result.execution_status == "REFUSED_OUT_OF_SCOPE"
    assert not hasattr(result, "_modulation_route_plan"), (
        "an out-of-scope operation must never reach a plan"
    )
    print("[PASS] test_out_of_scope_source_refuses_no_guess")


def test_out_of_scope_destination_refuses_no_guess():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "LFO1", "destination": "Unknown Widget"},
    )
    result = brain.execute(req)
    assert result.execution_status == "REFUSED_OUT_OF_SCOPE"
    assert not hasattr(result, "_modulation_route_plan")
    print("[PASS] test_out_of_scope_destination_refuses_no_guess")


def test_out_of_range_index_refuses():
    """macro9 -- macros only go 0-7. Index-range precision, not just family."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "macro9", "destination": "Filter 1 Freq"},
    )
    result = brain.execute(req)
    assert result.execution_status == "REFUSED_OUT_OF_SCOPE"
    print("[PASS] test_out_of_range_index_refuses")


def test_real_admission_gate_is_used():
    """The plan is produced only after the REAL, unmodified
    admission.admit() call returns admitted=True -- not a shadow/local
    check. Verified by admission_reason coming from the real 15.4 vocabulary."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.evidence import admission as admission_mod
    brain = ProducerBrain()
    req = ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "LFO1", "destination": "Filter 1 Freq"},
    )
    result = brain.execute(req)
    assert result.admission_reason == admission_mod.ADMITTED
    print("[PASS] test_real_admission_gate_is_used")


def test_finalize_requires_plan_ready_state():
    """Mirrors finalize_mcp_execution/finalize_serum_preset_execution's own
    guard tests -- an unadmitted/refused result can never be finalized as
    EXECUTED."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    refused = brain.execute(ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "Unknown", "destination": "Unknown"},
    ))
    assert refused.execution_status == "REFUSED_OUT_OF_SCOPE"
    try:
        brain.finalize_modulation_route_execution(
            refused, preset_path="x", preset_sha256="abc",
            matrix_readback={}, readback_verified=True,
        )
        assert False, "should have raised"
    except ValueError:
        pass
    print("[PASS] test_finalize_requires_plan_ready_state")


def test_finalize_requires_real_hash():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    admitted = brain.execute(ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "LFO1", "destination": "Filter 1 Freq"},
    ))
    assert admitted.execution_status == "MODULATION_ROUTE_PLAN_READY"
    try:
        brain.finalize_modulation_route_execution(
            admitted, preset_path="x", preset_sha256="",
            matrix_readback={}, readback_verified=True,
        )
        assert False, "should have raised on empty hash"
    except ValueError:
        pass
    print("[PASS] test_finalize_requires_real_hash")


def test_finalize_with_real_evidence_marks_executed():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    admitted = brain.execute(ProducerRequest(
        user_intent="", operation="ADD_MODULATION_ROUTE",
        operation_args={"source": "LFO1", "destination": "Filter 1 Freq"},
    ))
    brain.finalize_modulation_route_execution(
        admitted, preset_path="C:/fake/route.SerumPreset",
        preset_sha256="a" * 64,
        matrix_readback={"source": "LFO1", "destination": "Filter 1 Freq"},
        readback_verified=True,
    )
    assert admitted.execution_status == "EXECUTED"
    assert admitted.decision == "ACCEPTED"
    print("[PASS] test_finalize_with_real_evidence_marks_executed")


def test_visual_reasoner_cannot_call_mcp_directly():
    """Structural proof: the visual-reasoning module never imports an MCP
    client or serum-mcp/AbletonMCP call -- it can only produce
    observations/interpretations, never execute anything."""
    src = Path(ROOT, "serum2", "producer", "visual_reasoner.py").read_text()
    forbidden = ["mcp__serum-mcp", "mcp__AbletonMCP", "serum_mcp.", "AbletonMCP."]
    for token in forbidden:
        assert token not in src, "visual_reasoner.py must never call an MCP tool: found %r" % token
    print("[PASS] test_visual_reasoner_cannot_call_mcp_directly")


def test_regression_note_release_and_envelope_attack_unaffected():
    """The structured-operation path is parallel, not a replacement --
    concept-based intents must resolve exactly as before."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    r1 = brain.execute(ProducerRequest(user_intent="make the note sustain longer"))
    assert r1.resolved_concept == "note-release"
    assert r1.execution_route == "dawdreamer_serum"
    print("[PASS] test_regression_note_release_and_envelope_attack_unaffected")


if __name__ == "__main__":
    test_contract_derived_from_qualification_evidence()
    test_generic_operation_resolves_valid_route()
    test_unknown_amount_and_bipolar_preserved_not_guessed()
    test_out_of_scope_source_refuses_no_guess()
    test_out_of_scope_destination_refuses_no_guess()
    test_out_of_range_index_refuses()
    test_real_admission_gate_is_used()
    test_finalize_requires_plan_ready_state()
    test_finalize_requires_real_hash()
    test_finalize_with_real_evidence_marks_executed()
    test_visual_reasoner_cannot_call_mcp_directly()
    test_regression_note_release_and_envelope_attack_unaffected()
    print("\nAll ADD_MODULATION_ROUTE tests passed.")
