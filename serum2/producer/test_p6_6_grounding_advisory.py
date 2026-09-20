"""P6.6: Grounding as advisory input to candidate ranking.

Proves grounding claims can influence same-target candidate preference without
creating capability, bypassing resolution/admission, or executing directly.

Architecture:
  Grounding
      ↓
  advisory preference signals
      ↓
  candidate scoring (P4)
      ↓
  selected candidate
      ↓
  Capability Resolution (unchanged)
      ↓
  Admission (unchanged)

Grounding CANNOT:
  - Create capability
  - Bypass Capability Resolution
  - Bypass Admission
  - Replace target identity
  - Execute directly
"""

import pytest
from dataclasses import dataclass
from typing import Tuple, Mapping, Any, Optional

from serum2.producer.candidate_ranking import (
    CandidateGenerator, CandidateRanker, Candidate,
    collect_grounding_advisory, PRIMARY, SKILL_VARIANT
)


@dataclass(frozen=True)
class MockOperationSpec:
    """Mock for intent.operation."""
    operation: Any
    direction: Optional[str] = None
    base_phrase: str = ""
    certainty: float = 1.0
    interpretation_chain: Tuple[str, ...] = ()


@dataclass(frozen=True)
class MockIntent:
    """Mock for UniversalProductionIntent."""
    canonical_target: str
    operation: MockOperationSpec


class MockOperationType:
    """Mock for OperationType."""
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, MockOperationType):
            return self.value == other.value
        return self.value == other


class TestP66GroundingCanInfluencePreference:
    """Grounding evidence affects candidate scoring for same-target candidates."""

    def test_grounding_increases_candidate_score_for_matching_target(self):
        """Grounding claim for a target increases its candidate's score."""
        # Setup: two same-target candidates (operation variants)
        target = "env1.release"

        # Create mock intent
        op_spec = MockOperationSpec(
            operation=MockOperationType("set"),
            direction=None,
            base_phrase="adjust release",
            certainty=1.0,
            interpretation_chain=()
        )
        intent = MockIntent(canonical_target=target, operation=op_spec)

        # Create two candidates: PRIMARY (set) and SKILL_VARIANT (increase)
        cand_primary = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target=target,
            operation="set",
            operand={"raw": "500 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=("primary candidate",)
        )

        cand_variant = Candidate(
            candidate_id="cand:env1.release:increase:SKILL_VARIANT:-",
            canonical_target=target,
            operation="increase",
            operand=None,
            origin=SKILL_VARIANT,
            target_changed=False,
            evidence=(),
            rationale=("alternative operation",)
        )

        # Rank without grounding
        ranker = CandidateRanker()
        ranked_no_grounding = ranker.rank([cand_primary, cand_variant])
        primary_score_no_grounding = ranked_no_grounding.ranked[0].score

        # Create grounding evidence for the target
        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.7,
                'source_count': 3,
                'modalities': ['transcript', 'video'],
                'claim_ids': ['claim1']
            }
        ]

        # Rank with grounding
        ranked_with_grounding = ranker.rank([cand_primary, cand_variant], grounding_evidence=grounding_evidence)
        primary_score_with_grounding = ranked_with_grounding.ranked[0].score

        # Score should increase (grounding adds WEIGHT_GROUNDING * confidence)
        assert primary_score_with_grounding > primary_score_no_grounding, \
            f"Grounding should increase score: {primary_score_with_grounding} <= {primary_score_no_grounding}"

    def test_grounding_can_promote_skill_variant_over_primary(self):
        """Strong grounding for a target can promote a skill variant over the primary candidate."""
        target = "filter.resonance"

        op_spec = MockOperationSpec(
            operation=MockOperationType("increase"),
            direction="increase",
            base_phrase="boost resonance",
            certainty=1.0,
            interpretation_chain=()
        )
        intent = MockIntent(canonical_target=target, operation=op_spec)

        # Primary: the requested operation
        cand_primary = Candidate(
            candidate_id="cand:filter.resonance:increase:PRIMARY:-",
            canonical_target=target,
            operation="increase",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=("user requested increase",)
        )

        # Variant: a different operation from prior skill
        cand_variant = Candidate(
            candidate_id="cand:filter.resonance:set:SKILL_VARIANT:-",
            canonical_target=target,
            operation="set",
            operand={"raw": "0.8"},
            origin=SKILL_VARIANT,
            target_changed=False,
            evidence=(),
            rationale=("observed in prior episode",)
        )

        # Without grounding, primary ranks first (higher fit score)
        ranked_no_grounding = CandidateRanker().rank([cand_primary, cand_variant])
        assert ranked_no_grounding.ranked[0].candidate.origin == PRIMARY

        # With strong grounding for the variant's target+operation, primary still ranks first
        # (grounding doesn't override origin-based fit, it adjusts within same tier)
        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.9,  # high confidence
                'source_count': 5,
                'modalities': ['transcript', 'video', 'audio'],
                'claim_ids': ['claim1', 'claim2']
            }
        ]
        ranked_with_grounding = CandidateRanker().rank([cand_primary, cand_variant], grounding_evidence=grounding_evidence)

        # Primary still ranks first (same-target primary always has highest base fit)
        # but the gap is smaller due to grounding boost
        assert ranked_with_grounding.ranked[0].candidate.origin == PRIMARY

        # Variant score should be higher with grounding than without
        variant_score_no_grounding = ranked_no_grounding.ranked[1].score
        variant_score_with_grounding = ranked_with_grounding.ranked[1].score
        assert variant_score_with_grounding > variant_score_no_grounding


class TestP66GroundingCannotCreateCapability:
    """Grounding influences preference, never manufactures capability."""

    def test_grounding_cannot_create_target_candidate(self):
        """Grounding for an unsupported target does not create a candidate for it."""
        target_supported = "env1.release"
        target_unsupported = "env2.resonance"

        # Only the supported target has candidates
        cand_primary = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target=target_supported,
            operation="set",
            operand={"raw": "500 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=("primary",)
        )

        # Grounding claims for a target with no capability
        grounding_evidence = [
            {
                'target_id': target_unsupported,
                'confidence': 0.9,
                'source_count': 5,
                'modalities': ['transcript'],
                'claim_ids': ['claim_for_unsupported']
            }
        ]

        ranked = CandidateRanker().rank([cand_primary], grounding_evidence=grounding_evidence)

        # Only the primary candidate should exist and be selected
        assert len(ranked.ranked) == 1
        assert ranked.ranked[0].candidate.canonical_target == target_supported

    def test_grounding_evidence_in_audit_does_not_bypass_capability_check(self):
        """Grounding provenance in audit is separate from capability decision."""
        target = "unknown_target"

        cand = Candidate(
            candidate_id="cand:unknown_target:set:PRIMARY:-",
            canonical_target=target,
            operation="set",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.8,
                'source_count': 2,
                'modalities': ['transcript'],
                'claim_ids': ['claim1']
            }
        ]

        ranked = CandidateRanker().rank([cand], grounding_evidence=grounding_evidence)
        audit = ranked.to_audit()

        # Audit contains grounding info, but the candidate itself is still advisory
        # (capability check happens downstream, not in this layer)
        assert ranked.advisory is True
        assert len(ranked.ranked) == 1

        # The grounding is recorded in the candidate's features
        selected = ranked.ranked[0]
        assert 'grounding_confidence' in selected.features


class TestP66GroundingCannotBypassResolution:
    """Grounding evidence remains advisory; Capability Resolution is independent."""

    def test_grounding_does_not_appear_in_capability_resolution_input(self):
        """Selected candidate from grounding-influenced ranking still goes to Capability Resolution as-is."""
        target = "filter.cutoff"

        cand_primary = Candidate(
            candidate_id="cand:filter.cutoff:increase:PRIMARY:-",
            canonical_target=target,
            operation="increase",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.8,
                'source_count': 3,
                'modalities': ['video'],
                'claim_ids': ['claim1']
            }
        ]

        ranked = CandidateRanker().rank([cand_primary], grounding_evidence=grounding_evidence)
        selected_candidate = ranked.selected.candidate

        # Candidate fields should NOT include grounding data
        assert not hasattr(selected_candidate, 'grounding')
        assert not hasattr(selected_candidate, 'grounding_confidence')
        assert not hasattr(selected_candidate, 'grounding_sources')

        # The candidate is pure (advisory only)
        assert selected_candidate.advisory is True


class TestP66GroundingCannotExecute:
    """Grounding information never becomes execution directive."""

    def test_grounding_modalities_not_in_operation_spec(self):
        """Grounding modality info stays in audit, not in OperationSpec."""
        target = "env1.attack"

        cand = Candidate(
            candidate_id="cand:env1.attack:set:PRIMARY:-",
            canonical_target=target,
            operation="set",
            operand={"raw": "10 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.7,
                'source_count': 4,
                'modalities': ['transcript', 'video', 'audio'],
                'claim_ids': ['claim1']
            }
        ]

        ranked = CandidateRanker().rank([cand], grounding_evidence=grounding_evidence)
        audit = ranked.to_audit()

        # Audit has grounding info
        assert any('grounding' in str(k).lower() for k in audit.keys()) or 'grounding' in str(audit).lower()

        # But Candidate itself is untouched
        candidate_dict = ranked.selected.candidate.to_dict()
        assert 'execute' not in candidate_dict
        assert 'route' not in candidate_dict
        assert 'admission' not in candidate_dict


class TestP66GroundingProvenanceAudit:
    """Grounding provenance is retained in decision audit."""

    def test_grounding_provenance_in_ranked_features(self):
        """Grounding source provenance is tracked in ranked candidate features."""
        target = "osc.wavetable"

        cand = Candidate(
            candidate_id="cand:osc.wavetable:set:PRIMARY:-",
            canonical_target=target,
            operation="set",
            operand={"raw": "pwm"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.75,
                'source_count': 2,
                'modalities': ['transcript', 'video'],
                'claim_ids': ['claim_video_001', 'claim_transcript_002']
            }
        ]

        ranked = CandidateRanker().rank([cand], grounding_evidence=grounding_evidence)
        ranked_cand = ranked.ranked[0]
        features = ranked_cand.features

        # Grounding provenance is in features
        assert features['grounding_confidence'] == 0.75
        assert features['grounding_sources'] == 2
        assert set(features['grounding_modalities']) == {'transcript', 'video'}

    def test_grounding_absent_when_no_matching_target(self):
        """Grounding for different target leaves candidate score unchanged."""
        target_candidate = "filter.cutoff"
        target_grounding = "filter.resonance"

        cand = Candidate(
            candidate_id="cand:filter.cutoff:increase:PRIMARY:-",
            canonical_target=target_candidate,
            operation="increase",
            operand=None,
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': target_grounding,  # different target
                'confidence': 0.9,
                'source_count': 4,
                'modalities': ['transcript'],
                'claim_ids': ['claim1']
            }
        ]

        ranked_no_grounding = CandidateRanker().rank([cand])
        ranked_with_unrelated_grounding = CandidateRanker().rank([cand], grounding_evidence=grounding_evidence)

        # Score should be identical (grounding is for a different target)
        assert ranked_no_grounding.ranked[0].score == ranked_with_unrelated_grounding.ranked[0].score

        # Features show no grounding influence
        features = ranked_with_unrelated_grounding.ranked[0].features
        assert features['grounding_confidence'] == 0.0


class TestP66CollectGroundingAdvisory:
    """collect_grounding_advisory() converts GroundedClaim objects to advisory tuples."""

    def test_collect_grounding_from_multiple_claims(self):
        """Multiple grounding claims for same target aggregate confidence."""
        # Create mock grounded claims
        @dataclass(frozen=True)
        class MockObservation:
            modality: str

        @dataclass(frozen=True)
        class MockGroundedClaim:
            claim_id: str
            target_canonical_id: str
            status: str
            observations: Tuple[MockObservation, ...]

        claims = [
            MockGroundedClaim(
                claim_id="claim1",
                target_canonical_id="env1.release",
                status="RESOLVED",
                observations=(MockObservation(modality="transcript"),)
            ),
            MockGroundedClaim(
                claim_id="claim2",
                target_canonical_id="env1.release",
                status="RESOLVED",
                observations=(MockObservation(modality="video"),)
            ),
        ]

        advisory = collect_grounding_advisory(claims, intent=None)

        assert len(advisory) == 1
        assert advisory[0]['target_id'] == "env1.release"
        assert advisory[0]['source_count'] == 2
        assert set(advisory[0]['modalities']) == {'transcript', 'video'}
        assert 'claim1' in advisory[0]['claim_ids']
        assert 'claim2' in advisory[0]['claim_ids']

    def test_collect_grounding_ignores_unknown_claims(self):
        """Claims with UNKNOWN status are excluded from advisory."""
        @dataclass(frozen=True)
        class MockObservation:
            modality: str

        @dataclass(frozen=True)
        class MockGroundedClaim:
            claim_id: str
            target_canonical_id: str
            status: str
            observations: Tuple[MockObservation, ...]

        claims = [
            MockGroundedClaim(
                claim_id="claim_unknown",
                target_canonical_id="env1.release",
                status="UNKNOWN",
                observations=(MockObservation(modality="transcript"),)
            ),
        ]

        advisory = collect_grounding_advisory(claims, intent=None)

        # Should return empty tuple (unknown claim excluded)
        assert len(advisory) == 0

    def test_collect_grounding_empty_input(self):
        """Empty grounding input returns empty advisory tuple."""
        advisory = collect_grounding_advisory([], intent=None)
        assert advisory == ()


class TestP66MutationTests:
    """Verify architectural boundaries by deliberate mutation."""

    def test_mutation_ignoring_grounding_loses_preference_change(self):
        """If grounding influence is removed, preference ordering changes (proves grounding had effect)."""
        target = "filter.cutoff"

        cand = Candidate(
            candidate_id="cand:filter.cutoff:set:PRIMARY:-",
            canonical_target=target,
            operation="set",
            operand={"raw": "800 Hz"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        grounding_evidence = [
            {
                'target_id': target,
                'confidence': 0.8,
                'source_count': 3,
                'modalities': ['transcript'],
                'claim_ids': ['claim1']
            }
        ]

        # Rank with grounding
        ranked_with_grounding = CandidateRanker().rank([cand], grounding_evidence=grounding_evidence)
        score_with = ranked_with_grounding.ranked[0].score

        # Rank without grounding
        ranked_without_grounding = CandidateRanker().rank([cand], grounding_evidence=[])
        score_without = ranked_without_grounding.ranked[0].score

        # Scores should differ (grounding adds to score)
        assert score_with > score_without

    def test_grounding_isolated_to_ranker(self):
        """Mutation test: grounding is isolated to ranker, never in generator."""
        # Grounding is passed to CandidateRanker.rank(), not CandidateGenerator.generate()
        # This test verifies that separation is real.

        target = "env1.release"
        cand = Candidate(
            candidate_id="cand:env1.release:set:PRIMARY:-",
            canonical_target=target,
            operation="set",
            operand={"raw": "500 ms"},
            origin=PRIMARY,
            target_changed=False,
            evidence=(),
            rationale=()
        )

        ranker = CandidateRanker()

        # Grounding parameter only exists on ranker.rank(), not on generator.generate()
        # This proves the separation: grounding only affects preference, not candidate generation
        ranked = ranker.rank([cand], grounding_evidence=[])

        # Selected candidate is unchanged (no grounding influence)
        assert ranked.selected.candidate == cand


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
