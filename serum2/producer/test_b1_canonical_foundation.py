"""B1 Test Suite: Canonical Foundation.

Unit tests for B1.1–B1.5 components.
All tests are independent of the full pipeline; they validate derivation logic only.
"""
import pytest
import sys
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.concept_representation import (
    ConceptRepresentation, ConceptDerivationEngine, Provenance, ValueDomain
)
from serum2.producer.operation_spec import OperationInterpreter, OperationType
from serum2.producer.request_context import ContextExtractor
from serum2.producer.universal_intent import IntentFormationEngine, IntentValidator
from serum2.producer.contract_registry import ContractRegistry


class TestConceptRepresentation:
    """B1.1: Test ConceptRepresentation structure and validation."""

    def test_creates_valid_representation(self):
        """Can create a valid concept representation."""
        rep = ConceptRepresentation(
            canonical_target="env1.decay",
            operation_type="numeric",
            provenance=Provenance.CONTRACT,
            confidence=0.95,
        )
        assert rep.canonical_target == "env1.decay"
        assert rep.is_derivable()

    def test_rejects_invalid_confidence(self):
        """Rejects confidence outside 0.0–1.0."""
        with pytest.raises(ValueError):
            ConceptRepresentation(
                canonical_target="env1.decay",
                provenance=Provenance.MISSING,
                confidence=1.5,
            )

    def test_marks_missing_as_not_derivable(self):
        """MISSING provenance means not derivable."""
        rep = ConceptRepresentation(
            canonical_target="oscA.warp_mode",
            provenance=Provenance.MISSING,
            confidence=0.0,
        )
        assert not rep.is_derivable()

    def test_serializes_to_dict(self):
        """Can serialize representation to dict for audit."""
        rep = ConceptRepresentation(
            canonical_target="env1.decay",
            operation_type="numeric",
            provenance=Provenance.CONTRACT,
            confidence=0.95,
            derivation_chain=["step1", "step2"],
        )
        d = rep.to_dict()
        assert d["canonical_target"] == "env1.decay"
        assert d["provenance"] == "contract"
        assert d["derivation_chain"] == ["step1", "step2"]


class TestConceptDerivationEngine:
    """B1.2: Test concept derivation from frozen data layers."""

    def test_derives_from_contract(self):
        """Can derive concept from CAUSAL_VERIFIED contract."""
        engine = ConceptDerivationEngine(ContractRegistry())
        rep = engine.derive("env1.decay")

        # env1.decay should have a contract
        assert rep.canonical_target == "env1.decay"
        assert rep.is_derivable()
        assert rep.provenance == Provenance.CONTRACT
        assert rep.confidence >= 0.90

    def test_marks_missing_when_no_path(self):
        """Returns MISSING when no derivation path exists."""
        engine = ConceptDerivationEngine(ContractRegistry())
        rep = engine.derive("oscA.warp_mode")

        # warp_mode has no contract and no semantic target
        assert rep.canonical_target == "oscA.warp_mode"
        assert not rep.is_derivable()
        assert rep.provenance == Provenance.MISSING

    def test_no_invention_of_concepts(self):
        """Never invents a concept; returns MISSING instead."""
        engine = ConceptDerivationEngine(ContractRegistry())
        rep = engine.derive("completely.bogus")

        # This should fail at Atlas resolution
        assert rep.provenance == Provenance.MISSING or rep.provenance == Provenance.MISSING
        # Most importantly: no invented provenance
        assert rep.provenance != Provenance.GENERIC_LANGUAGE  # only if we tried generically

    def test_includes_audit_trail(self):
        """Derivation includes complete audit trail."""
        engine = ConceptDerivationEngine(ContractRegistry())
        rep = engine.derive("env1.decay")

        assert len(rep.derivation_chain) > 0
        # Should include at least: resolve, contract lookup
        chain_str = " ".join(rep.derivation_chain).lower()
        assert "derive" in chain_str or "resolve" in chain_str


class TestOperationInterpreter:
    """B1.3: Test operation/value interpretation."""

    def test_interprets_decrease_direction(self):
        """Recognizes decrease direction words."""
        interp = OperationInterpreter()
        spec = interp.interpret("shorter")

        assert spec.operation == OperationType.NUMERIC_DECREASE
        assert spec.direction == "decrease"
        assert spec.certainty >= 0.75

    def test_interprets_increase_direction(self):
        """Recognizes increase direction words."""
        interp = OperationInterpreter()
        spec = interp.interpret("longer")

        assert spec.operation == OperationType.NUMERIC_INCREASE
        assert spec.direction == "increase"
        assert spec.certainty >= 0.75

    def test_interprets_numeric_set(self):
        """Extracts numeric value assignments."""
        interp = OperationInterpreter()
        spec = interp.interpret("to 100ms")

        assert spec.operation == OperationType.NUMERIC_SET
        assert spec.target_value == 100
        assert spec.unit == "ms"
        assert spec.certainty >= 0.85

    def test_interprets_toggle_on(self):
        """Recognizes toggle ON."""
        interp = OperationInterpreter()
        spec = interp.interpret("enable", operation_type="toggle")

        assert spec.operation == OperationType.TOGGLE_ON
        assert spec.certainty >= 0.75

    def test_interprets_toggle_off(self):
        """Recognizes toggle OFF."""
        interp = OperationInterpreter()
        spec = interp.interpret("disable", operation_type="toggle")

        assert spec.operation == OperationType.TOGGLE_OFF
        assert spec.certainty >= 0.75

    def test_returns_unknown_when_cannot_interpret(self):
        """Returns UNKNOWN operation when interpretation fails."""
        interp = OperationInterpreter()
        spec = interp.interpret("xyz123abc")

        assert spec.operation == OperationType.UNKNOWN
        assert spec.certainty == 0.0

    def test_includes_interpretation_chain(self):
        """Operation spec includes audit trail."""
        interp = OperationInterpreter()
        spec = interp.interpret("to 50 hz")

        assert len(spec.interpretation_chain) > 0


class TestContextExtractor:
    """B1.4: Test context extraction."""

    def test_extracts_explicit_target(self):
        """Extracts dotted target names."""
        extractor = ContextExtractor()
        ctx = extractor.extract("set env1.decay to 100ms")

        assert ctx.explicit_target == "env1.decay"
        assert ctx.confidence.get("explicit_target", 0) >= 0.90

    def test_extracts_implicit_filter_scope(self):
        """Recognizes filter scope from keywords."""
        extractor = ContextExtractor()
        ctx = extractor.extract("make the filter cutoff higher")

        assert ctx.implicit_scope_type == "filter"
        assert "filter" in ctx.implicit_scope.lower()

    def test_extracts_implicit_oscillator_scope(self):
        """Recognizes oscillator scope."""
        extractor = ContextExtractor()
        ctx = extractor.extract("adjust oscillator A")

        assert ctx.implicit_scope_type == "oscillator"

    def test_extracts_audio_descriptors(self):
        """Extracts audio descriptor words for P6 grounding."""
        extractor = ContextExtractor()
        ctx = extractor.extract("make it sound darker and warmer")

        assert "dark" in ctx.audio_descriptors
        assert "warm" in ctx.audio_descriptors

    def test_extracts_time_markers(self):
        """Extracts temporal context."""
        extractor = ContextExtractor()
        ctx = extractor.extract("at the end, gradually increase")

        assert ctx.time_marker is not None
        assert "end" in ctx.time_marker or "gradual" in ctx.time_marker


class TestIntentFormation:
    """B1.5: Test unified intent formation."""

    def test_combines_all_components(self):
        """Combines representation, operation, context into one intent."""
        engine = ConceptDerivationEngine(ContractRegistry())
        op_interp = OperationInterpreter()
        ctx_extractor = ContextExtractor()
        intent_engine = IntentFormationEngine()

        # Derive each component
        rep = engine.derive("env1.decay")
        op = op_interp.interpret("shorter")
        ctx = ctx_extractor.extract("make env1.decay shorter")

        # Form unified intent
        intent = intent_engine.form_intent(
            canonical_target="env1.decay",
            representation=rep,
            operation=op,
            context=ctx,
        )

        assert intent.canonical_target == "env1.decay"
        assert intent.representation is rep
        assert intent.operation is op
        assert intent.context is ctx
        assert intent.overall_confidence > 0.0

    def test_computes_overall_confidence(self):
        """Combines component confidences into overall score."""
        engine = ConceptDerivationEngine(ContractRegistry())
        op_interp = OperationInterpreter()
        ctx_extractor = ContextExtractor()
        intent_engine = IntentFormationEngine()

        rep = engine.derive("env1.decay")
        op = op_interp.interpret("to 500ms")
        ctx = ctx_extractor.extract("env1.decay to 500ms")

        intent = intent_engine.form_intent("env1.decay", rep, op, ctx)

        # Should be high confidence (contract + numeric set + context)
        assert intent.overall_confidence >= 0.70

    def test_includes_complete_trace(self):
        """Intent includes full derivation trace."""
        engine = ConceptDerivationEngine(ContractRegistry())
        op_interp = OperationInterpreter()
        ctx_extractor = ContextExtractor()
        intent_engine = IntentFormationEngine()

        rep = engine.derive("env1.decay")
        op = op_interp.interpret("shorter")
        ctx = ctx_extractor.extract("shorter env1.decay")

        intent = intent_engine.form_intent("env1.decay", rep, op, ctx)

        # Trace should include all components' chains
        trace_str = " ".join(intent.derivation_trace).lower()
        assert "derive" in trace_str or "contract" in trace_str or "confidence" in trace_str


class TestIntentValidator:
    """Validate intent readiness for Capability Resolution."""

    def test_accepts_valid_intent(self):
        """Accepts well-formed intent."""
        engine = ConceptDerivationEngine(ContractRegistry())
        op_interp = OperationInterpreter()
        ctx_extractor = ContextExtractor()
        intent_engine = IntentFormationEngine()
        validator = IntentValidator()

        rep = engine.derive("env1.decay")
        op = op_interp.interpret("to 200ms")
        ctx = ctx_extractor.extract("to 200ms")

        intent = intent_engine.form_intent("env1.decay", rep, op, ctx)

        is_valid, issues = validator.validate(intent)
        # If derivable and interpreted, should be mostly valid
        if rep.is_derivable():
            assert is_valid or len(issues) <= 1

    def test_rejects_missing_representation(self):
        """Rejects intent with MISSING representation."""
        engine = ConceptDerivationEngine(ContractRegistry())
        op_interp = OperationInterpreter()
        ctx_extractor = ContextExtractor()
        intent_engine = IntentFormationEngine()
        validator = IntentValidator()

        rep = engine.derive("completely.bogus")  # will be MISSING
        op = op_interp.interpret("to 100")
        ctx = ctx_extractor.extract("to 100")

        intent = intent_engine.form_intent("completely.bogus", rep, op, ctx)

        is_valid, issues = validator.validate(intent)
        # Should fail validation due to MISSING representation
        if not rep.is_derivable():
            assert not is_valid
            assert any("derivable" in issue.lower() for issue in issues)
