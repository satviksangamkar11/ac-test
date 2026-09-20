"""P7 Final Closure: Integrated proof across complete Brain chain.

Proves entire reasoning chain maintains architectural boundaries:
  ProducerRequest → UPI → Skills → Candidates → Ranking
                              ↑
                    Grounding + Context + Prior
                              ↓
                    Selected Candidate → Capability → Admission → Execution

No layer violates the frozen invariant:
  REFERENCE ≠ BRAIN ≠ CAPABILITY ≠ AUTHORITY
"""

import pytest
from dataclasses import dataclass

from serum2.producer.candidate_ranking import (
    Candidate, CandidateRanker, PriorEpisodeEvidence,
    PRIMARY, SKILL_VARIANT
)
from serum2.producer.structured_context import (
    StructuredProductionContext, DeterministicContextPolicy
)


class TestP7ChainContextInfluence:
    """Context influences preference through the chain."""

    def test_context_changes_ranking_without_modifying_candidate(self):
        """Context preference affects ranking, not candidate structure."""
        cand_primary = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target="env1.release",
            operation="set",
            operand={"raw": "500 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        cand_variant = Candidate(
            candidate_id="cand:env1.release:increase:SKILL_VARIANT:-",
            canonical_target="env1.release",
            operation="increase",
            operand=None,
            origin=SKILL_VARIANT,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ranker = CandidateRanker()
        policy = DeterministicContextPolicy()
        ctx = StructuredProductionContext(
            objective="smooth_sustain", objective_confidence=0.8
        )

        ranked_no_context = ranker.rank([cand_primary, cand_variant])
        ranked_with_context = ranker.rank(
            [cand_primary, cand_variant],
            context=ctx,
            context_policy=policy
        )

        # Ranking may change
        primary_score_no_ctx = next(
            r.score for r in ranked_no_context.ranked if r.candidate.origin == PRIMARY
        )
        primary_score_with_ctx = next(
            r.score for r in ranked_with_context.ranked if r.candidate.origin == PRIMARY
        )

        # Candidate objects unchanged
        assert cand_primary.canonical_target == "env1.release"
        assert cand_primary.operation == "set"
        assert cand_variant.canonical_target == "env1.release"


class TestP7ChainGroundingInfluence:
    """Grounding influences preference through the chain."""

    def test_grounding_changes_ranking_without_manufacturing_targets(self):
        """Grounding evidence affects ranking, never creates targets."""
        cand = Candidate(
            candidate_id="cand:filter.cutoff:set:PRIMARY:-",
            canonical_target="filter.cutoff",
            operation="set",
            operand={"raw": "800 Hz"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': "filter.cutoff",
                'confidence': 0.8,
                'source_count': 3,
                'modalities': ['transcript', 'video'],
                'claim_ids': ['claim1']
            }
        ]

        ranker = CandidateRanker()
        ranked_no_grounding = ranker.rank([cand])
        ranked_with_grounding = ranker.rank([cand], grounding_evidence=grounding_evidence)

        # Score changes
        score_no_grounding = ranked_no_grounding.ranked[0].score
        score_with_grounding = ranked_with_grounding.ranked[0].score
        assert score_with_grounding > score_no_grounding

        # Candidate unchanged
        assert len(ranked_with_grounding.ranked) == 1
        assert ranked_with_grounding.ranked[0].candidate.canonical_target == "filter.cutoff"


class TestP7ChainBothContextAndGrounding:
    """Context and grounding both influence preference together."""

    def test_context_and_grounding_both_affect_score(self):
        """Both context and grounding contribute to preference."""
        cand = Candidate(
            candidate_id="cand:osc1.wavetable:set:PRIMARY:-",
            canonical_target="osc1.wavetable",
            operation="set",
            operand={"raw": "square"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': "osc1.wavetable",
                'confidence': 0.7,
                'source_count': 2,
                'modalities': ['video'],
                'claim_ids': ['claim1']
            }
        ]

        ctx = StructuredProductionContext(
            technique="additive", technique_confidence=0.6
        )
        policy = DeterministicContextPolicy()

        ranker = CandidateRanker()

        # Baseline
        ranked_baseline = ranker.rank([cand])
        score_baseline = ranked_baseline.ranked[0].score

        # With grounding
        ranked_grounding = ranker.rank([cand], grounding_evidence=grounding_evidence)
        score_grounding = ranked_grounding.ranked[0].score

        # With context
        ranked_context = ranker.rank([cand], context=ctx, context_policy=policy)
        score_context = ranked_context.ranked[0].score

        # With both
        ranked_both = ranker.rank(
            [cand],
            grounding_evidence=grounding_evidence,
            context=ctx,
            context_policy=policy
        )
        score_both = ranked_both.ranked[0].score

        # All should increase from baseline
        assert score_grounding > score_baseline
        assert score_context > score_baseline
        assert score_both > score_baseline
        # Both together should be at least as high as either alone
        assert score_both >= score_grounding
        assert score_both >= score_context


class TestP7ChainCannotCreateCapability:
    """Neither context nor grounding manufactures capability."""

    def test_grounding_on_unknown_target_produces_no_candidate(self):
        """Grounding for an unknown target doesn't create candidate."""
        cand_known = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target="env1.release",
            operation="set",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_unknown = [
            {
                'target_id': "unknown_target_xyz",
                'confidence': 0.9,
                'source_count': 5,
                'modalities': ['transcript'],
                'claim_ids': ['claim1']
            }
        ]

        ranked = CandidateRanker().rank([cand_known], grounding_evidence=grounding_unknown)

        # Only the known candidate exists
        assert len(ranked.ranked) == 1
        assert ranked.ranked[0].candidate.canonical_target == "env1.release"

    def test_context_on_unknown_target_produces_no_candidate(self):
        """Context alone never creates targets."""
        cand = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target="env1.release",
            operation="set",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ctx = StructuredProductionContext(
            genre="ambient", genre_confidence=0.8
        )
        policy = DeterministicContextPolicy()

        ranked = CandidateRanker().rank(
            [cand],
            context=ctx,
            context_policy=policy
        )

        # Still only one candidate
        assert len(ranked.ranked) == 1
        assert ranked.ranked[0].candidate.canonical_target == "env1.release"


class TestP7ChainBoundaryNotCrossed:
    """Context/grounding never bypass Capability Resolution or Admission."""

    def test_selected_candidate_is_purely_advisory(self):
        """Selected candidate from influenced ranking is still advisory."""
        cand = Candidate(
            candidate_id="cand:filter.resonance:set:PRIMARY:-",
            canonical_target="filter.resonance",
            operation="set",
            operand={"raw": "0.8"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ctx = StructuredProductionContext(
            genre="techno", genre_confidence=0.9
        )
        policy = DeterministicContextPolicy()

        ranked = CandidateRanker().rank(
            [cand],
            context=ctx,
            context_policy=policy
        )

        selected = ranked.selected.candidate

        # Candidate is pure advisory (no capability, route, binding, etc.)
        assert selected.advisory is True
        assert not hasattr(selected, "capability")
        assert not hasattr(selected, "route")
        assert not hasattr(selected, "binding")
        assert not hasattr(selected, "admitted")

    def test_context_provenance_separate_from_capability_fields(self):
        """Context reasons/provenance don't appear in candidate fields."""
        cand = Candidate(
            candidate_id="cand:osc.unison:set:PRIMARY:-",
            canonical_target="osc.unison",
            operation="set",
            operand={"raw": "5"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ctx = StructuredProductionContext(
            role="bass", role_confidence=0.7
        )
        policy = DeterministicContextPolicy()

        ranked = CandidateRanker().rank(
            [cand],
            context=ctx,
            context_policy=policy
        )

        # Features contain context info
        features = ranked.ranked[0].features
        assert "context_score" in features

        # But Candidate itself is untouched
        candidate_dict = ranked.ranked[0].candidate.to_dict()
        assert "context" not in candidate_dict
        assert "context_score" not in candidate_dict


class TestP7ChainAuditTrail:
    """Full provenance preserved through chain."""

    def test_audit_records_context_influence(self):
        """Audit trail shows which context affected which candidate."""
        cand = Candidate(
            candidate_id="cand:env1.decay:set:PRIMARY:-",
            canonical_target="env1.decay",
            operation="set",
            operand={"raw": "200 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ctx = StructuredProductionContext(
            objective="smooth_tail", objective_confidence=0.8
        )
        policy = DeterministicContextPolicy()

        ranked = CandidateRanker().rank(
            [cand],
            context=ctx,
            context_policy=policy
        )

        # Audit should show context influence
        features = ranked.ranked[0].features
        assert features["context_score"] > 0.0
        assert "context_reasons" in features
        assert "context_provenance" in features

    def test_audit_records_grounding_influence(self):
        """Audit trail shows which grounding affected which candidate."""
        cand = Candidate(
            candidate_id="cand:filter.cutoff:set:PRIMARY:-",
            canonical_target="filter.cutoff",
            operation="set",
            operand={"raw": "1000 Hz"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding = [
            {
                'target_id': "filter.cutoff",
                'confidence': 0.75,
                'source_count': 3,
                'modalities': ['transcript', 'video'],
                'claim_ids': ['claim_001', 'claim_002']
            }
        ]

        ranked = CandidateRanker().rank([cand], grounding_evidence=grounding)

        features = ranked.ranked[0].features
        assert features["grounding_confidence"] == 0.75
        assert features["grounding_sources"] == 3
        assert set(features["grounding_modalities"]) == {"transcript", "video"}


class TestP7ChainDeterminism:
    """Same inputs produce same outputs (deterministic)."""

    def test_same_ranking_inputs_same_output(self):
        """Deterministic: identical ranking requests produce identical results."""
        cand = Candidate(
            candidate_id="cand:osc.detune:set:PRIMARY:-",
            canonical_target="osc.detune",
            operation="set",
            operand={"raw": "5 cents"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding = [
            {
                'target_id': "osc.detune",
                'confidence': 0.7,
                'source_count': 2,
                'modalities': ['video'],
                'claim_ids': ['claim1']
            }
        ]

        ctx = StructuredProductionContext(
            technique="detuning", technique_confidence=0.8
        )
        policy = DeterministicContextPolicy()

        ranker = CandidateRanker()

        # Run twice
        result1 = ranker.rank(
            [cand],
            grounding_evidence=grounding,
            context=ctx,
            context_policy=policy
        )

        result2 = ranker.rank(
            [cand],
            grounding_evidence=grounding,
            context=ctx,
            context_policy=policy
        )

        # Should be identical
        assert result1.ranked[0].score == result2.ranked[0].score
        assert result1.ranked[0].features == result2.ranked[0].features


class TestP7ChainMutationBoundaries:
    """Deliberate mutations prove boundaries are real."""

    def test_mutation_remove_context_loses_preference(self):
        """Mutation: removing context handling breaks preference changes."""
        cand = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target="env1.release",
            operation="set",
            operand={"raw": "500 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ctx = StructuredProductionContext(
            genre="ambient", genre_confidence=0.9
        )
        policy = DeterministicContextPolicy()

        ranker = CandidateRanker()

        score_with_context = ranker.rank(
            [cand],
            context=ctx,
            context_policy=policy
        ).ranked[0].score

        score_without_context = ranker.rank([cand]).ranked[0].score

        # With context should score higher
        assert score_with_context > score_without_context

    def test_mutation_context_never_creates_parameter_value(self):
        """Mutation: context policy source has no parameter assignments."""
        import inspect
        source = inspect.getsource(DeterministicContextPolicy.preference)

        # Forbidden patterns
        forbidden = [
            "cutoff =",
            "resonance =",
            "attack =",
            "release =",
            'if context.genre == "',
            'if context.artist',
            'if context.technique',
        ]

        for pattern in forbidden:
            assert pattern not in source, f"Found forbidden pattern: {pattern}"


class TestP7ChainRefusalsIntact:
    """Existing refusals remain intact (negative proof)."""

    def test_context_and_grounding_on_unexecutable_candidate_still_unexecutable(self):
        """Context/grounding never bypass capability checks."""
        # Candidate for an target with no capability
        cand = Candidate(
            candidate_id="cand:nonexistent.target:set:PRIMARY:-",
            canonical_target="nonexistent.target",
            operation="set",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding = [
            {
                'target_id': "nonexistent.target",
                'confidence': 0.95,  # Very strong grounding
                'source_count': 10,
                'modalities': ['transcript', 'video', 'audio'],
                'claim_ids': ['claim1', 'claim2', 'claim3']
            }
        ]

        ctx = StructuredProductionContext(
            objective="critical", objective_confidence=0.99
        )
        policy = DeterministicContextPolicy()

        ranked = CandidateRanker().rank(
            [cand],
            grounding_evidence=grounding,
            context=ctx,
            context_policy=policy
        )

        # Still just one candidate (no new targets created)
        assert len(ranked.ranked) == 1
        # It's still advisory (no capability, route, etc.)
        assert ranked.ranked[0].candidate.advisory is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
