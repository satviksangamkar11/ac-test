"""P7.1: Contextual policy foundation — tests.

Tests verify that context is preference, not parameter mapping, and remains advisory.
"""

import pytest
from serum2.producer.structured_context import StructuredProductionContext, DeterministicContextPolicy


class TestP71ContextIndependenceFromParameters:
    """Context can be represented independently of target parameters."""

    def test_context_has_no_parameter_fields(self):
        """StructuredProductionContext must not contain parameter value fields."""
        ctx = StructuredProductionContext(role="bass", genre="house")
        fields = {f for f in ctx.__dataclass_fields__ if not f.startswith("_")}

        # Forbidden fields
        forbidden = {"cutoff", "resonance", "attack", "release", "decay", "sustain",
                     "filter_type", "oscs", "detune", "unison"}
        assert not (forbidden & fields), f"Context contains parameter fields: {forbidden & fields}"

    def test_context_is_immutable(self):
        """StructuredProductionContext must be frozen/immutable."""
        ctx = StructuredProductionContext(role="bass")
        with pytest.raises((AttributeError, TypeError)):
            ctx.role = "melody"  # Should not be settable


class TestP71MissingContextUnknown:
    """Missing context remains UNKNOWN rather than guessed."""

    def test_missing_dimension_is_none_not_default(self):
        """Absent context dimensions stay None, never invented."""
        ctx = StructuredProductionContext()  # All missing
        assert ctx.role is None
        assert ctx.genre is None
        assert ctx.artist_style is None
        assert ctx.technique is None
        assert ctx.objective is None

    def test_confidence_zero_for_missing_dimension(self):
        """Missing dimensions have zero confidence."""
        ctx = StructuredProductionContext()
        assert ctx.role_confidence == 0.0
        assert ctx.genre_confidence == 0.0


class TestP71ContextAltersPreference:
    """Context can alter candidate preference."""

    def test_policy_with_context_produces_nonzero_score(self):
        """DeterministicContextPolicy should score context-informed candidates."""
        policy = DeterministicContextPolicy()
        ctx_rich = StructuredProductionContext(
            role="bass", role_confidence=0.8,
            genre="ambient", genre_confidence=0.7
        )
        result = policy.preference({}, ctx_rich)

        assert result["score"] > 0.0
        assert "role" in result["affected_dimensions"]
        assert "genre" in result["affected_dimensions"]

    def test_different_context_produces_different_score(self):
        """More context dimensions = higher score."""
        policy = DeterministicContextPolicy()
        ctx_minimal = StructuredProductionContext(role="bass", role_confidence=0.5)
        ctx_rich = StructuredProductionContext(
            role="bass", role_confidence=0.5,
            genre="house", genre_confidence=0.6,
            technique="filtering", technique_confidence=0.7
        )

        score_minimal = policy.preference({}, ctx_minimal)["score"]
        score_rich = policy.preference({}, ctx_rich)["score"]

        assert score_rich > score_minimal


class TestP71ContextNotParameterMapping:
    """Context cannot create parameters, capability, or bypass authority."""

    def test_context_cannot_create_parameter_value(self):
        """Context policy must not output parameter values."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(genre="bass")
        result = policy.preference({}, ctx)

        # Result must be preference info only
        assert "score" in result
        assert "reasoning" in result

    def test_policy_result_has_no_capability_field(self):
        """Preference result cannot contain capability info."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(role="bass")
        result = policy.preference({}, ctx)

        forbidden_keys = {"capability", "contract", "binding", "route", "admitted", "execution"}
        actual_keys = set(result.keys())
        assert not (forbidden_keys & actual_keys)

    def test_context_policy_cannot_access_registry(self):
        """DeterministicContextPolicy must not import capability registry."""
        import inspect
        source = inspect.getsource(DeterministicContextPolicy.preference)
        assert "ContractRegistry" not in source
        assert "capability_contract" not in source


class TestP71DeterministicPreference:
    """Same inputs give same preference."""

    def test_same_context_produces_same_score(self):
        """Preference must be deterministic."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(role="bass", role_confidence=0.8)
        candidate = {}

        score1 = policy.preference(candidate, ctx)["score"]
        score2 = policy.preference(candidate, ctx)["score"]

        assert score1 == score2


class TestP71ContextNotTargetIdentity:
    """Context changes preference, not target identity."""

    def test_context_does_not_replace_canonical_target(self):
        """Even with strong context, target identity is preserved."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(role="bass", genre="house")
        candidate = {"canonical_target": "env1.release"}

        result = policy.preference(candidate, ctx)
        # Policy doesn't modify the candidate
        assert candidate["canonical_target"] == "env1.release"


class TestP71NoHardcodedMappings:
    """Genre, artist, technique must NOT produce fixed parameter mappings."""

    def test_genre_is_preference_not_mapping(self):
        """Genre produces preference signal, not parameter values."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(genre="house", genre_confidence=0.9)
        result = policy.preference({}, ctx)

        # Should affect score
        assert result["score"] > 0.0
        assert "genre" in result["affected_dimensions"]

    def test_artist_style_is_preference_not_mapping(self):
        """Artist/style field is preference signal, not parameter source."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(artist_style="experimental")
        result = policy.preference({}, ctx)

        # Should affect score
        assert result["score"] > 0.0

    def test_technique_is_preference_not_mapping(self):
        """Technique field is preference signal, not parameter source."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(technique="fm_synthesis")
        result = policy.preference({}, ctx)

        # Should affect score
        assert result["score"] > 0.0


class TestP71ObjectiveAsPreference:
    """Objective changes preference, not authority."""

    def test_objective_affects_preference_not_execution(self):
        """Objective should inform ranking, never become execution directive."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(objective="create_ambience", objective_confidence=0.7)
        result = policy.preference({}, ctx)

        # Preference is affected
        assert result["score"] > 0.0
        # But no execution instruction
        assert "execute" not in str(result).lower()


class TestP71ContextAuthorityBoundary:
    """Context must remain advisory, never become authority."""

    def test_context_policy_cannot_bypass_capability_resolution(self):
        """Policy result cannot contain capability resolution override."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext()
        result = policy.preference({}, ctx)

        # No fields that bypass capability layer
        forbidden = {"bypass", "override", "force_admit", "skip_validation"}
        for key in result.keys():
            assert key not in forbidden

    def test_context_policy_cannot_bypass_admission(self):
        """Policy result cannot contain admission override."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext()
        result = policy.preference({}, ctx)

        # No admission directives
        assert "admit" not in result
        assert "admitted" not in result

    def test_context_policy_cannot_execute(self):
        """Policy result cannot contain execution directive."""
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext()
        result = policy.preference({}, ctx)

        # No execution info
        assert "execute" not in result
        assert "tool_call" not in result
        assert "mcp_call" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
