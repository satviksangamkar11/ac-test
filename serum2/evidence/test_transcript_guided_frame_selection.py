"""Tests for transcript-guided frame selection."""

import pytest
from serum2.evidence.transcript_guided_frame_selection import (
    FrameCandidate,
    FrameSelectionBasis,
    FrameSelectionConfig,
    build_transcript_candidates,
    merge_frame_candidates,
    build_uniform_candidates,
    clamp_timestamp,
)


class TestClampTimestamp:
    """Timestamp clamping."""

    def test_clamp_negative(self):
        """Negative timestamp clamped to 0."""
        assert clamp_timestamp(-5.0, 100.0) == 0.0

    def test_clamp_exceeds_duration(self):
        """Timestamp exceeding duration clamped to duration."""
        assert clamp_timestamp(150.0, 100.0) == 100.0

    def test_clamp_within_range(self):
        """Timestamp within range unchanged."""
        assert clamp_timestamp(50.0, 100.0) == 50.0


class TestBuildTranscriptCandidates:
    """Frame candidates from transcript cues."""

    def test_preferred_timestamps_used(self):
        """Preferred timestamps become candidates."""
        cue_plan = {
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [12.0, 15.0],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test action",
                    "confidence": 0.9,
                }
            ]
        }

        candidates = build_transcript_candidates(
            cue_plan,
            duration_s=100.0,
            config=FrameSelectionConfig(),
        )

        timestamps = {c.timestamp_s for c in candidates}
        assert 12.0 in timestamps
        assert 15.0 in timestamps
        assert all(c.basis == FrameSelectionBasis.TRANSCRIPT_CUE for c in candidates)

    def test_no_preferred_uses_boundaries(self):
        """Without preferred timestamps, use start/mid/end."""
        cue_plan = {
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 20.0,
                    "preferred_timestamps_s": [],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.9,
                }
            ]
        }

        candidates = build_transcript_candidates(
            cue_plan,
            duration_s=100.0,
            config=FrameSelectionConfig(),
        )

        timestamps = {c.timestamp_s for c in candidates}
        assert 10.0 in timestamps  # start
        assert 15.0 in timestamps  # midpoint
        assert 20.0 in timestamps  # end

    def test_cue_ids_preserved(self):
        """Cue IDs linked to candidates."""
        cue_plan = {
            "cues": [
                {
                    "cue_id": "cue-99",
                    "segment_ids": ["seg-1"],
                    "start_s": 30.0,
                    "end_s": 35.0,
                    "preferred_timestamps_s": [32.0],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "reason",
                    "confidence": 0.8,
                }
            ]
        }

        candidates = build_transcript_candidates(
            cue_plan,
            duration_s=100.0,
            config=FrameSelectionConfig(),
        )

        assert all("cue-99" in c.cue_ids for c in candidates)


class TestMergeFrameCandidates:
    """Merging three candidate sources."""

    def test_merge_deduplicates_within_100ms(self):
        """Candidates within 100ms bucket merged."""
        transcript_cands = [
            FrameCandidate(
                timestamp_s=50.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-1",),
            )
        ]

        visual_cands = [
            FrameCandidate(
                timestamp_s=50.04,  # 40ms away, within 100ms bucket
                basis=FrameSelectionBasis.VISUAL_CHANGE,
                cue_ids=(),
            )
        ]

        uniform_cands = []

        result = merge_frame_candidates(
            transcript_cands,
            visual_cands,
            uniform_cands,
            max_frames=10,
            duration_s=100.0,
        )

        assert len(result) == 1
        assert result[0].timestamp_s == 50.0

    def test_priority_transcript_over_visual(self):
        """TRANSCRIPT_CUE > VISUAL_CHANGE priority."""
        transcript_cands = [
            FrameCandidate(
                timestamp_s=50.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-1",),
            )
        ]

        visual_cands = [
            FrameCandidate(
                timestamp_s=50.02,
                basis=FrameSelectionBasis.VISUAL_CHANGE,
                cue_ids=(),
            )
        ]

        result = merge_frame_candidates(
            transcript_cands,
            visual_cands,
            [],
            max_frames=10,
            duration_s=100.0,
        )

        assert len(result) == 1
        assert result[0].basis == FrameSelectionBasis.TRANSCRIPT_CUE

    def test_respects_max_frames(self):
        """Result limited to max_frames."""
        candidates = [
            FrameCandidate(
                timestamp_s=float(i),
                basis=FrameSelectionBasis.UNIFORM_FALLBACK,
            )
            for i in range(100)
        ]

        result = merge_frame_candidates(
            [],
            [],
            candidates,
            max_frames=10,
            duration_s=200.0,
        )

        assert len(result) == 10

    def test_sorted_by_timestamp(self):
        """Result sorted by timestamp."""
        candidates_unordered = [
            FrameCandidate(timestamp_s=100.0, basis=FrameSelectionBasis.UNIFORM_FALLBACK),
            FrameCandidate(timestamp_s=50.0, basis=FrameSelectionBasis.UNIFORM_FALLBACK),
            FrameCandidate(timestamp_s=75.0, basis=FrameSelectionBasis.UNIFORM_FALLBACK),
        ]

        result = merge_frame_candidates(
            [],
            [],
            candidates_unordered,
            max_frames=10,
            duration_s=200.0,
        )

        timestamps = [c.timestamp_s for c in result]
        assert timestamps == sorted(timestamps)


class TestBuildUniformCandidates:
    """Baseline uniform coverage."""

    def test_uniform_coverage(self):
        """Uniform candidates at regular intervals."""
        candidates = build_uniform_candidates(
            duration_s=100.0,
            interval_s=10.0,
        )

        expected_count = 9  # 10, 20, 30, ..., 90 (no 100)
        assert len(candidates) == expected_count

    def test_uniform_timestamps(self):
        """Uniform candidates at correct timestamps."""
        candidates = build_uniform_candidates(
            duration_s=50.0,
            interval_s=10.0,
        )

        timestamps = [c.timestamp_s for c in candidates]
        assert timestamps == [10.0, 20.0, 30.0, 40.0]

    def test_all_uniform_have_correct_basis(self):
        """All uniform candidates marked as UNIFORM_FALLBACK."""
        candidates = build_uniform_candidates(
            duration_s=30.0,
            interval_s=10.0,
        )

        assert all(c.basis == FrameSelectionBasis.UNIFORM_FALLBACK for c in candidates)


class TestEndToEndMerge:
    """Full integration: all three sources."""

    def test_full_merge_pipeline(self):
        """Transcript + visual + uniform merge."""
        transcript = [
            FrameCandidate(
                timestamp_s=30.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-1",),
                selection_reason="action 1",
            ),
            FrameCandidate(
                timestamp_s=60.0,
                basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                cue_ids=("cue-2",),
                selection_reason="action 2",
            ),
        ]

        visual = [
            FrameCandidate(
                timestamp_s=45.0,
                basis=FrameSelectionBasis.VISUAL_CHANGE,
                selection_reason="detected change",
            )
        ]

        uniform = build_uniform_candidates(duration_s=120.0, interval_s=30.0)

        result = merge_frame_candidates(
            transcript,
            visual,
            uniform,
            max_frames=20,
            duration_s=120.0,
        )

        # Should have: 30 (transcript), 45 (visual), 60 (transcript), 90 (uniform), 120 (clipped)
        assert len(result) > 0
        assert result[0].timestamp_s == 30.0
        assert any(c.basis == FrameSelectionBasis.VISUAL_CHANGE for c in result)
