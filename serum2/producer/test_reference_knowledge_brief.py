"""The Brain's read-only reference-knowledge brief must never touch execution/admission, and must annotate
every row -- including non-DERIVED ones -- without inventing anything for rows with no corpus coverage."""
import pytest

from serum2.producer.producer_brain import ProducerBrain
from serum2.producer.reference_knowledge_brief import brief_reference_knowledge, brief_row


def test_briefs_every_row_in_order_none_dropped():
    rows = [
        {"control_id": "env1.attack", "terminal": "OPERATION_DERIVED"},
        {"control_id": "some.unknown.control", "terminal": "UNRESOLVED", "reason": "no Atlas identity"},
        {"control_id": "oscA.wavetable", "terminal": "UNREADABLE_RE_READ_REQUIRED", "reason": "obscured in frame"},
    ]
    briefs = brief_reference_knowledge(rows)
    assert len(briefs) == 3
    assert [b["target"] for b in briefs] == ["env1.attack", "some.unknown.control", "oscA.wavetable"]
    assert briefs[1]["terminal"] == "UNRESOLVED" and briefs[1]["reason"] == "no Atlas identity"


def test_never_calls_execute_or_admission(monkeypatch):
    """A brain whose .execute()/._resolve_and_admit() would raise if called at all -- brief_row must never reach
    them, proving this stays a pure retrieval call with no authority path."""
    brain = ProducerBrain()

    def boom(*a, **kw):
        raise AssertionError("brief_row must never call an execution/admission method")
    monkeypatch.setattr(brain, "execute", boom)
    if hasattr(brain, "_resolve_and_admit"):
        monkeypatch.setattr(brain, "_resolve_and_admit", boom)
    if hasattr(brain, "_run_mcp_path"):
        monkeypatch.setattr(brain, "_run_mcp_path", boom)

    result = brief_row(brain, {"control_id": "env1.attack", "terminal": "OPERATION_DERIVED"})
    assert result["target"] == "env1.attack"   # completed normally; none of the patched methods were touched


def test_target_with_zero_corpus_coverage_gets_zero_items_not_fabricated():
    brain = ProducerBrain()
    result = brief_row(brain, {"control_id": "definitely.not.a.real.corpus.term.xyz123", "terminal": "OPERATION_DERIVED"})
    assert result["brain_knowledge_item_count"] == 0


def test_brief_reuses_the_same_documented_advisory_only_retrieval_method(monkeypatch):
    calls = []
    brain = ProducerBrain()
    real = brain._retrieve_knowledge

    def spy(intent_text, concept, **kw):
        calls.append((intent_text, concept))
        return real(intent_text, concept, **kw)
    monkeypatch.setattr(brain, "_retrieve_knowledge", spy)
    brief_row(brain, {"control_id": "fx.reverb.type", "terminal": "OPERATION_DERIVED"})
    assert calls == [("fx.reverb.type", None)]
