"""B1 integration: B1 is on the canonical ProducerBrain.execute() path, consumes TargetResolver's result,
owns no target/contract table, and has no execution authority. Legacy behaviour is labelled, not mixed in."""
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest, _direction_from_words
from serum2.producer import target_resolution as tr

SRC = Path(__file__).parent


def _run(intent, semantic_target=None):
    return ProducerBrain().execute(ProducerRequest(user_intent=intent, semantic_target=semantic_target,
                                                   mode="EXECUTE", visual_mode="NEVER"))


def _plan(r):
    return getattr(r, "_serum_preset_plan", None) or {}


def test_canonical_path_runs_b1_and_hands_the_resolved_capability_downstream():
    r = _run("make Env1.Decay shorter", "Env1.Decay")
    b1 = r.b1_intent
    assert r.resolution_mode == "B1_CANONICAL" and b1["b1_used"] is True
    assert b1["canonical_target"] == "env1.decay" and b1["capability_key"] == "envelope_field_decay"
    assert b1["representation"]["provenance"] == "contract"
    assert b1["operation"]["operation"] == "decrease" and r.semantic_direction == "shorter"
    assert _plan(r)["contract_id"] == "envelope_field_decay" and r.admitted is True
    assert "release" not in " ".join(b1["derivation_trace"]).lower()          # Decay never becomes Release


@pytest.mark.parametrize("intent,cap", [("shorter Env1.Decay to 627 ms", "envelope_field_decay"),
                                        ("lower Env1.Sustain to -13.8 dB", "envelope_field_sustain")])
def test_numeric_value_is_read_from_the_value_not_from_the_identifier(intent, cap):
    op = _run(intent).b1_intent["operation"]
    assert op["operation"] == "numeric_set" and op["direction"] == "decrease"
    assert op["target_value"] in (627, -13.8) and op["target_value"] != 1          # 'Env1' digit is not a value


def test_enum_contract_interprets_as_select_not_as_the_number_in_the_label():
    r = _run("set Filter1.Type to Band 24")
    assert r.b1_intent["operation"]["operation"] == "enum_select" and r.admitted is True


def test_other_envelope_slots_keep_their_own_capability_and_never_borrow_env1s():
    r = _run("shorter Env2.Decay to 100 ms")
    b1 = r.b1_intent
    assert r.resolution_mode == "B1_CANONICAL"                                       # B1 ran on the resolved target ...
    assert b1["capability_key"] == "envelope2_field_decay"                           # ... using ITS capability key
    assert b1["representation"]["provenance"] == "legacy_semantic_target"            # no CAUSAL_VERIFIED contract for it
    assert r.refusal["code"] == tr.REFUSED_NO_CAPABILITY and not r.admitted          # refused downstream, not substituted
    assert _plan(r).get("contract_id") is None


def test_legacy_natural_language_path_is_labelled_and_does_not_use_b1():
    r = _run("Make the note sustain longer")
    assert r.resolved_concept == "note-release"                                     # legacy behaviour preserved
    assert r.resolution_mode == "LEGACY"
    assert r.b1_intent == {"resolution_mode": "LEGACY", "brain_source": "_INTENT_TO_CONCEPT", "b1_used": False}


def test_refusals_are_labelled_refused_and_b1_is_not_used():
    for intent in ("shorter Env1.Bogus", "make it shorter"):
        r = _run(intent, "cutoff" if "make" in intent else None)
        assert r.resolution_mode in ("REFUSED", "LEGACY") and r.b1_intent["b1_used"] is False


@pytest.mark.parametrize("text", ["shorter Env1.Decay", "longer Env1.Attack to 1.5 ms", "lower Env1.Sustain to -3 dB",
                                  "more Env1.Release"])
def test_b1_direction_does_not_drift_from_the_established_direction_adapter(text):
    r = _run(text)
    assert r.semantic_direction == _direction_from_words(text).value


def test_b1_has_no_hand_written_target_or_contract_tables_and_no_authority():
    for name in ("concept_representation.py", "operation_spec.py", "request_context.py", "universal_intent.py"):
        src = (SRC / name).read_text(encoding="utf-8")
        for forbidden in ("contract_hints", "conservative_numeric", "known_enums", "envelope_field_", "filter_field_",
                          "lfo_field_", "AdmissionHandoff", "ContractGovernedExecutor", "_execute_mcp", "mcp__"):
            assert forbidden not in src, (name, forbidden)
