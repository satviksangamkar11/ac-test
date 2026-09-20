"""Tests for Phase 5 gate corrections: Corrections 1-3 invariants.

Three issues identified before Phase 5 interactive run:
1. Enforce preferred_timestamps against transcript segment boundaries
2. True deep-freeze for TranscriptCuePlan.provenance (scalar-only)
3. Per-cue frame allocation guarantee

These tests verify all three corrections are working correctly.
"""

import pytest
from serum2.evidence.transcript_cue_plan import (
    TranscriptCuePlan,
    TranscriptCue,
    TranscriptCueKind,
)
from serum2.evidence.validate_transcript_cue_plan import (
    validate_transcript_cue_plan,
)
from serum2.evidence.transcript_guided_frame_selection import (
    merge_frame_candidates,
    FrameCandidate,
    FrameSelectionBasis,
)


class TestCorrection2ProvenanceDeepFreeze:
    """Correction 2: Provenance must be scalar-only (runtime validation)."""

    def test_provenance_accepts_scalar_values(self):
        """Valid provenance with scalars only."""
        plan = TranscriptCuePlan(
            schema_version="1.0",
            runtime="claude-code",
            direct_anthropic_sdk=False,
            api_key_used=False,
            source_id="test-source",
            video_id="test-video",
            source_url=None,
            transcript_sha256="abc123",
            transcript_language="en",
            cues=(),
            provenance=(
                ("analyst", "claude-code"),
                ("analysis_timestamp", 1234567890),
                ("confidence_threshold", 0.75),
                ("manual_review", True),
                ("notes", None),
            ),
        )
        assert len(plan.provenance) == 5
        assert plan.provenance[0] == ("analyst", "claude-code")

    def test_provenance_rejects_nested_dict(self):
        """Provenance with nested dict rejected at construction."""
        with pytest.raises(ValueError, match="must be scalar"):
            TranscriptCuePlan(
                schema_version="1.0",
                runtime="claude-code",
                direct_anthropic_sdk=False,
                api_key_used=False,
                source_id="test-source",
                video_id="test-video",
                source_url=None,
                transcript_sha256="abc123",
                transcript_language="en",
                cues=(),
                provenance=(("config", {"nested": "dict"}),),  # type: ignore
            )

    def test_provenance_rejects_nested_list(self):
        """Provenance with nested list rejected at construction."""
        with pytest.raises(ValueError, match="must be scalar"):
            TranscriptCuePlan(
                schema_version="1.0",
                runtime="claude-code",
                direct_anthropic_sdk=False,
                api_key_used=False,
                source_id="test-source",
                video_id="test-video",
                source_url=None,
                transcript_sha256="abc123",
                transcript_language="en",
                cues=(),
                provenance=(("items", [1, 2, 3]),),  # type: ignore
            )

    def test_provenance_rejects_nested_tuple(self):
        """Provenance with nested tuple rejected at construction."""
        with pytest.raises(ValueError, match="must be scalar"):
            TranscriptCuePlan(
                schema_version="1.0",
                runtime="claude-code",
                direct_anthropic_sdk=False,
                api_key_used=False,
                source_id="test-source",
                video_id="test-video",
                source_url=None,
                transcript_sha256="abc123",
                transcript_language="en",
                cues=(),
                provenance=(("coords", (10.0, 20.0)),),  # type: ignore
            )

    def test_provenance_key_must_be_string(self):
        """Provenance key must be a string."""
        with pytest.raises(ValueError, match="key must be str"):
            TranscriptCuePlan(
                schema_version="1.0",
                runtime="claude-code",
                direct_anthropic_sdk=False,
                api_key_used=False,
                source_id="test-source",
                video_id="test-video",
                source_url=None,
                transcript_sha256="abc123",
                transcript_language="en",
                cues=(),
                provenance=((123, "numeric_key"),),  # type: ignore
            )

    def test_provenance_is_immutable_after_construction(self):
        """Provenance tuple is truly immutable."""
        plan = TranscriptCuePlan(
            schema_version="1.0",
            runtime="claude-code",
            direct_anthropic_sdk=False,
            api_key_used=False,
            source_id="test-source",
            video_id="test-video",
            source_url=None,
            transcript_sha256="abc123",
            transcript_language="en",
            cues=(),
            provenance=(("key", "value"),),
        )

        # Frozen dataclass prevents assignment
        with pytest.raises(Exception):  # FrozenInstanceError
            plan.provenance = ()  # type: ignore


class TestCorrection1PreferredTimestampsValidation:
    """Correction 1: Enforce preferred_timestamps against segment boundaries."""

    def test_validation_with_exact_segment_boundaries(self):
        """Preferred timestamps at exact segment boundaries accepted."""
        payload = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "test",
            "video_id": "test-video",
            "transcript_sha256": "abc123",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [10.0, 20.0],  # exact boundaries
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ],
        }

        # Should not raise
        validate_transcript_cue_plan(
            payload,
            transcript_sha256="abc123",
            duration_s=100.0,
            transcript_segment_timestamps={"seg-1": (10.0, 20.0)},
        )

    def test_validation_with_midpoint_timestamp(self):
        """Preferred timestamp at segment midpoint accepted."""
        payload = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "test",
            "video_id": "test-video",
            "transcript_sha256": "abc123",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [15.0],  # midpoint
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ],
        }

        validate_transcript_cue_plan(
            payload,
            transcript_sha256="abc123",
            duration_s=100.0,
            transcript_segment_timestamps={"seg-1": (10.0, 20.0)},
        )

    def test_validation_with_tolerance_for_float_rounding(self):
        """Preferred timestamp within ±1ms tolerance accepted."""
        payload = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "test",
            "video_id": "test-video",
            "transcript_sha256": "abc123",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [15.0005],  # 0.5ms from midpoint
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ],
        }

        validate_transcript_cue_plan(
            payload,
            transcript_sha256="abc123",
            duration_s=100.0,
            transcript_segment_timestamps={"seg-1": (10.0, 20.0)},
        )

    def test_validation_rejects_arbitrary_timestamp_without_segments(self):
        """Preferred timestamp outside boundaries rejected (no segment map)."""
        payload = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "test",
            "video_id": "test-video",
            "transcript_sha256": "abc123",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [12.5],  # arbitrary, not exact boundary or midpoint
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ],
        }

        with pytest.raises(ValueError, match="not an exact segment boundary"):
            validate_transcript_cue_plan(
                payload,
                transcript_sha256="abc123",
                duration_s=100.0,
                transcript_segment_timestamps={"seg-1": (10.0, 20.0)},
            )

    def test_validation_requires_segment_ids_for_preferred_timestamps(self):
        """Preferred timestamps without segment_ids rejected."""
        payload = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "test",
            "video_id": "test-video",
            "transcript_sha256": "abc123",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": [],  # empty, no segments
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [15.0],  # but has preferred timestamps
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ],
        }

        with pytest.raises(ValueError, match="no segment_ids"):
            validate_transcript_cue_plan(
                payload,
                transcript_sha256="abc123",
                duration_s=100.0,
                transcript_segment_timestamps={"seg-1": (10.0, 20.0)},
            )

    def test_validation_skipped_when_segment_map_not_provided(self):
        """Preferred timestamp validation skipped if segment map is None."""
        payload = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "test",
            "video_id": "test-video",
            "transcript_sha256": "abc123",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": [],  # empty
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [12.34],  # arbitrary (would fail with map)
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ],
        }

        # Should NOT raise because we're not providing segment_timestamps
        validate_transcript_cue_plan(
            payload,
            transcript_sha256="abc123",
            duration_s=100.0,
            transcript_segment_timestamps=None,  # No map, no validation
        )


class TestCorrection3PerCueAllocation:
    """Correction 3: Guarantee at least one frame per unique transcript cue."""

    def test_per_cue_allocation_all_unique_cues_covered_within_budget(self):
        """All unique cues get at least one frame when budget allows."""
        # 8 unique cues, 10 max frames
        transcript = [
            FrameCandidate(
                timestamp_s=float(i * 10),
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=(f"cue-{i}",),
                selection_reason=f"cue {i}",
            )
            for i in range(8)
        ]

        result = merge_frame_candidates(
            transcript,
            [],
            [],
            max_frames=10,
            duration_s=100.0,
        )

        # All 8 cues should be represented
        all_cues = set()
        for frame in result:
            all_cues.update(frame.cue_ids)

        assert len(all_cues) == 8
        assert all(f"cue-{i}" in all_cues for i in range(8))

    def test_per_cue_allocation_insufficient_budget_raises(self):
        """Insufficient budget for all unique cues raises ValueError."""
        # Create 8 unique cues with well-separated timestamps (no deduplication)
        # to ensure they all merge separately, then set max_frames < unique cues
        transcript = []
        for i in range(8):
            # Spread timestamps far apart to avoid 100ms bucket collisions
            transcript.append(
                FrameCandidate(
                    timestamp_s=float(i * 20),  # 0, 20, 40, 60, 80, ...
                    basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                    cue_ids=(f"cue-{i}",),
                    selection_reason=f"cue {i}",
                )
            )
            # Add a second candidate per cue to force over-budget path
            transcript.append(
                FrameCandidate(
                    timestamp_s=float(i * 20 + 0.5),
                    basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                    cue_ids=(f"cue-{i}",),
                )
            )

        with pytest.raises(ValueError, match="Cannot fit all.*unique transcript cues"):
            merge_frame_candidates(
                transcript,
                [],
                [],
                max_frames=5,  # Only 5 frames for 8 cues -> must raise
                duration_s=200.0,
            )

    def test_per_cue_allocation_multi_cue_frames_satisfy_multiple_cues(self):
        """One frame with multiple cue_ids satisfies multiple cues."""
        # One frame mentions cues 1, 2, 3; one mentions cue 4
        # Should require only 2 frames total to cover all 4 unique cues
        transcript = [
            FrameCandidate(
                timestamp_s=10.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-1", "cue-2", "cue-3"),  # multi-cue
            ),
            FrameCandidate(
                timestamp_s=20.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-4",),
            ),
        ]

        result = merge_frame_candidates(
            transcript,
            [],
            [],
            max_frames=10,
            duration_s=100.0,
        )

        # Should have exactly 2 frames (one per cue group)
        assert len(result) == 2
        all_cues = set()
        for frame in result:
            all_cues.update(frame.cue_ids)
        assert all_cues == {"cue-1", "cue-2", "cue-3", "cue-4"}

    def test_per_cue_allocation_deterministic_ordering(self):
        """Per-cue allocation is deterministic (sorted cue_ids)."""
        transcript = [
            FrameCandidate(
                timestamp_s=30.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-b",),
            ),
            FrameCandidate(
                timestamp_s=10.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-a",),
            ),
            FrameCandidate(
                timestamp_s=20.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-c",),
            ),
        ]

        result = merge_frame_candidates(
            transcript,
            [],
            [],
            max_frames=10,
            duration_s=100.0,
        )

        # Result should be sorted by timestamp (due to final sort at line 274)
        timestamps = [c.timestamp_s for c in result]
        assert timestamps == sorted(timestamps)

        # All 3 cues covered
        all_cues = set()
        for frame in result:
            all_cues.update(frame.cue_ids)
        assert all_cues == {"cue-a", "cue-b", "cue-c"}

    def test_per_cue_allocation_over_budget_still_covers_all_cues(self):
        """Even when over budget, all unique cues are covered first."""
        # 6 unique cues, 8 max frames, 12+ transcript candidates
        # Well-separated timestamps to avoid 100ms bucket dedup
        transcript = []
        for i in range(6):
            cue_id = f"cue-{i}"
            # Primary candidate: 0, 30, 60, 90, 120, 150 (far apart, no bucket collisions)
            transcript.append(
                FrameCandidate(
                    timestamp_s=float(i * 30),
                    basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                    cue_ids=(cue_id,),
                )
            )
            # Secondary candidate: same cue (multiple options per cue)
            transcript.append(
                FrameCandidate(
                    timestamp_s=float(i * 30 + 1),
                    basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                    cue_ids=(cue_id,),
                )
            )

        result = merge_frame_candidates(
            transcript,
            [],
            [],
            max_frames=8,
            duration_s=200.0,
        )

        # At most 8 frames
        assert len(result) <= 8

        # All 6 unique cues represented in first coverage pass
        all_cues = set()
        for frame in result:
            all_cues.update(frame.cue_ids)
        assert len(all_cues) == 6, f"Expected 6 cues, got {len(all_cues)}: {all_cues}"
