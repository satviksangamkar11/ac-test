"""P7.1: Contextual policy foundation — comprehensive RED tests.

Verifies context is preference signal, never parameter mapping or authority.

Architecture:
  StructuredProductionContext
      ↓
  DeterministicContextPolicy
      ↓
  ContextPreference (advisory)
      ↓
  candidate preference adjustment
      ↓
  existing P4 ranking
      ↓
  Capability Resolution (unchanged)
      ↓
  Admission (unchanged)

Context CANNOT:
  - Create candidates
  - Replace target
  - Create capability
  - Bypass resolution/admission
  - Execute
"""

import pytest
from dataclasses import dataclass

from serum2.producer.structured_context import (
    StructuredProductionContext, DeterministicContextPolicy, ContextPreference
)


class TestP71ContextIndependence:
    """Context is representable independently of parameters."""

    def test_context_has_only_semantic_dimensions(self):
        """StructuredProductionContext has no parameter value fields."""
        ctx = StructuredProductionContext(role="bass", genre="house")
        fields = {f for f in ctx.__dataclass_fields__ if not f.startswith("_")}

        # Forbidden fields (would indicate parameter mapping)
        forbidden = {
            "cutoff", "resonance", "attack", "release", "decay", "sustain",
            "filter_type", "oscs", "detune", "unison", "oscillator",
            "reverb", "delay", "compression", "eq", "routing", "enable"
        }
        actual = fields & forbidden
        assert not actual, f"Context has parameter fields: {actual}"

    def test_context_is_frozen_immutable(self):
        """StructuredProductionContext is frozen."""
        ctx = StructuredProductionContext(role="bass")
        with pytest.raises((AttributeError, TypeError)):
            ctx.role = "melody"


class TestP71UnknownStaysUnknown:
    """Missing context remains explicit (None, confidence=0.0)."""

    def test_empty_context_is_all_none(self):
        """Empty context has all None values."""
        ctx = StructuredProductionContext()
        assert ctx.role is None
        assert ctx.genre is None
        assert ctx.artist_style is None
        assert ctx.technique is None
        assert ctx.objective is None
        assert ctx.era is None
        assert ctx.subgenre is None

    def test_empty_context_has_zero_confidence(self):
        """Empty context has zero confidence on all dimensions."""
        ctx = StructuredProductionContext()
        assert ctx.role_confidence == 0.0
        assert ctx.genre_confidence == 0.0
        assert ctx.artist_style_confidence == 0.0


class TestP71ContextAltersPreference:
    """Context influences candidate preference."""

    def test_policy_with_context_produces_nonzero_delta(self):
        """Context dimensions produce non-zero score_delta."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            role="bass", role_confidence=0.8,
            genre="house", genre_confidence=0.7
        )
        pref = policy.preference({}, ctx)

        assert isinstance(pref, ContextPreference)
        assert pref.score_delta > 0.0
        assert "role" in pref.reasons[0] or "genre" in pref.reasons[0]

    def test_more_context_higher_score(self):
        """More context dimensions = higher score."""
        policy = DeterministicContextPolicy()

        ctx_minimal = StructuredProductionContext(
            role="bass", role_confidence=0.5
        )
        ctx_rich = StructuredProductionContext(
            role="bass", role_confidence=0.5,
            genre="house", genre_confidence=0.6,
            technique="filtering", technique_confidence=0.7
        )

        score_minimal = policy.preference({}, ctx_minimal).score_delta
        score_rich = policy.preference({}, ctx_rich).score_delta

        assert score_rich > score_minimal

    def test_zero_confidence_no_contribution(self):
        """Dimension with 0.0 confidence contributes nothing."""
        policy = DeterministicContextPolicy()

        ctx_with_zero = StructuredProductionContext(
            role="bass", role_confidence=0.0
        )
        pref = policy.preference({}, ctx_with_zero)

        assert pref.score_delta == 0.0
        assert "no context" in pref.reasons[0].lower()


class TestP71ContextNotParameterMapping:
    """Context cannot create parameters or capabilities."""

    def test_context_policy_returns_only_preference(self):
        """ContextPreference has only score_delta, reasons, provenance."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(genre="techno", genre_confidence=0.8)
        pref = policy.preference({}, ctx)

        # Only these fields exist
        assert hasattr(pref, "score_delta")
        assert hasattr(pref, "reasons")
        assert hasattr(pref, "provenance")

        # No parameter fields
        forbidden_attrs = {
            "cutoff", "resonance", "attack", "route", "binding",
            "capability", "admitted", "execute"
        }
        pref_attrs = set(dir(pref))
        bad = forbidden_attrs & pref_attrs
        assert not bad, f"ContextPreference has forbidden fields: {bad}"

    def test_genre_is_preference_not_mapping(self):
        """Genre dimension informs preference, never maps to cutoff/resonance."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            genre="techno", genre_confidence=0.9
        )
        pref = policy.preference({}, ctx)

        # Score exists but no parameter assignment
        assert pref.score_delta > 0.0
        assert not any(
            param in str(pref).lower()
            for param in ["cutoff", "resonance", "attack", "release"]
        )

    def test_artist_style_is_preference_not_mapping(self):
        """Artist/style informs preference, never maps target."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            artist_style="experimental", artist_style_confidence=0.7
        )
        pref = policy.preference({}, ctx)

        assert pref.score_delta > 0.0
        assert "artist_style" in pref.reasons[0]

    def test_technique_is_preference_not_mapping(self):
        """Technique informs preference, never maps target."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            technique="fm_synthesis", technique_confidence=0.8
        )
        pref = policy.preference({}, ctx)

        assert pref.score_delta > 0.0
        assert "technique" in pref.reasons[0]


class TestP71DeterministicPreference:
    """Same inputs produce same preference."""

    def test_same_context_same_score(self):
        """Deterministic: identical input → identical output."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            role="bass", role_confidence=0.8,
            genre="house", genre_confidence=0.7
        )

        pref1 = policy.preference({}, ctx)
        pref2 = policy.preference({}, ctx)

        assert pref1.score_delta == pref2.score_delta
        assert pref1.reasons == pref2.reasons


class TestP71ContextNotTargetIdentity:
    """Context never replaces target identity."""

    def test_context_does_not_mutate_candidate(self):
        """Context policy never modifies candidate structure."""
        policy = DeterministicContextPolicy()
        candidate = {"canonical_target": "env1.release", "operation": "set"}
        ctx = StructuredProductionContext(
            role="bass", role_confidence=0.8,
            genre="house", genre_confidence=0.7
        )

        pref = policy.preference(candidate, ctx)

        # Candidate unchanged
        assert candidate["canonical_target"] == "env1.release"
        assert candidate["operation"] == "set"
        # Preference is separate
        assert pref.score_delta > 0.0


class TestP71NoHardcodedMappings:
    """AST-level: no genre/artist/technique → parameter mappings."""

    def test_no_genre_cutoff_mapping_in_source(self):
        """DeterministicContextPolicy source has no genre→parameter logic."""
        import inspect
        source = inspect.getsource(DeterministicContextPolicy.preference)

        # Forbidden patterns (examples)
        forbidden = [
            'genre" == "techno"',
            'genre" == "house"',
            '"cutoff"',
            'resonance = ',
            'if context.genre',
        ]

        for pattern in forbidden:
            assert pattern not in source, \
                f"Found hardcoded mapping: {pattern}"

    def test_no_artist_style_target_mapping(self):
        """No artist_style → target substitution logic."""
        import inspect
        source = inspect.getsource(DeterministicContextPolicy.preference)

        forbidden = [
            'artist_style" == ',
            'canonical_target = ',
            'if context.artist',
        ]

        for pattern in forbidden:
            assert pattern not in source

    def test_no_technique_parameter_mapping(self):
        """No technique → parameter value assignment."""
        import inspect
        source = inspect.getsource(DeterministicContextPolicy.preference)

        assert 'if context.technique' not in source
        assert 'technique_value' not in source
        assert 'technique ==' not in source


class TestP71ObjectiveAsPreference:
    """Objective informs preference, not execution."""

    def test_objective_affects_score_not_action(self):
        """Objective produces preference signal, no execution directive."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            objective="create_ambience", objective_confidence=0.7
        )
        pref = policy.preference({}, ctx)

        # Preference exists
        assert pref.score_delta > 0.0
        # No execution
        assert "execute" not in str(pref).lower()
        assert "route" not in str(pref).lower()


class TestP71ContextAuthorityBoundary:
    """Context never becomes authority."""

    def test_preference_has_no_capability_field(self):
        """ContextPreference cannot carry capability info."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext()
        pref = policy.preference({}, ctx)

        assert not hasattr(pref, "capability")
        assert not hasattr(pref, "contract")
        assert not hasattr(pref, "route")
        assert not hasattr(pref, "admitted")

    def test_preference_has_no_bypass_field(self):
        """ContextPreference cannot bypass resolution/admission."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(role="bass")
        pref = policy.preference({}, ctx)

        forbidden_keys = {
            "bypass", "override", "force_admit", "skip_validation",
            "admission_bypass", "resolution_override"
        }
        pref_str = str(pref).lower()
        for key in forbidden_keys:
            assert key not in pref_str

    def test_preference_has_no_execution_field(self):
        """ContextPreference cannot contain execution directive."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(genre="ambient")
        pref = policy.preference({}, ctx)

        forbidden = {"execute", "tool_call", "mcp_call", "route", "binding"}
        pref_str = str(pref).lower()
        for key in forbidden:
            assert key not in pref_str


class TestP71ProvenanceAudit:
    """Context preference includes audit trail."""

    def test_preference_includes_provenance(self):
        """ContextPreference has provenance tuple."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(role="bass", role_confidence=0.8)
        pref = policy.preference({}, ctx)

        assert pref.provenance is not None
        assert len(pref.provenance) > 0
        assert "policy" in str(pref.provenance).lower()

    def test_preference_includes_reasons(self):
        """ContextPreference documents which dimensions affected score."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            role="bass", role_confidence=0.8,
            genre="house", genre_confidence=0.7
        )
        pref = policy.preference({}, ctx)

        assert len(pref.reasons) > 0
        assert any("role" in r for r in pref.reasons)
        assert any("genre" in r for r in pref.reasons)


class TestP71ContextIntegration:
    """Context integrates with existing P4 without replacing it."""

    def test_context_policy_is_separate_from_candidate_generator(self):
        """ContextPolicy is not part of CandidateGenerator."""
        from serum2.producer.candidate_ranking import CandidateGenerator

        # Generator takes intent and advisories, never context
        gen_sig = str(CandidateGenerator.generate)
        assert "context" not in gen_sig.lower()

    def test_context_does_not_appear_in_candidate(self):
        """Candidate object has no context field."""
        from serum2.producer.candidate_ranking import Candidate

        # Create a candidate (simulated)
        fields = Candidate.__dataclass_fields__.keys()
        assert "context" not in fields
        assert "contextual_preference" not in fields


class TestP71MutationTests:
    """Prove boundaries by deliberate mutation."""

    def test_mutation_removing_context_loses_preference(self):
        """If context is ignored, preference doesn't change."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            role="bass", role_confidence=0.8,
            genre="house", genre_confidence=0.7
        )

        pref_with = policy.preference({}, ctx)

        ctx_empty = StructuredProductionContext()
        pref_without = policy.preference({}, ctx_empty)

        assert pref_with.score_delta > pref_without.score_delta

    def test_mutation_hardcoding_genre_fails_ast_check(self):
        """Anti-mutation: no genre→parameter in source."""
        import inspect
        source = inspect.getsource(DeterministicContextPolicy)

        # Forbidden pattern
        assert 'if context.genre == "techno"' not in source
        assert 'if context.genre == "house"' not in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
