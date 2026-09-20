"""Tests for TranscriptCuePlan validation."""

import pytest
from serum2.evidence.validate_transcript_cue_plan import (
    validate_transcript_cue_plan,
)


class TestValidationRequiredFields:
    """Validation checks required fields."""

    def test_valid_minimal_plan(self):
        """Minimal valid plan passes validation."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef123456",
            "cues": [],
        }

        validate_transcript_cue_plan(
            plan,
            transcript_sha256="abcdef123456",
            duration_s=100.0,
        )

    def test_missing_required_field(self):
        """Missing required field raises ValueError."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            # Missing api_key_used
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [],
        }

        with pytest.raises(ValueError, match="missing fields"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )


class TestValidationRuntime:
    """Validation checks runtime constraints."""

    def test_runtime_must_be_claude_code(self):
        """Runtime must be exactly 'claude-code'."""
        plan = {
            "schema_version": "1.0",
            "runtime": "anthropic-api",  # Wrong
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [],
        }

        with pytest.raises(ValueError, match="Unexpected.*runtime"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_sdk_must_be_false(self):
        """direct_anthropic_sdk must be False."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": True,  # Wrong
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [],
        }

        with pytest.raises(ValueError, match="must not use.*SDK"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_api_key_must_be_false(self):
        """api_key_used must be False."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": True,  # Wrong
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [],
        }

        with pytest.raises(ValueError, match="must not use.*API key"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )


class TestValidationTranscriptHash:
    """Validation checks transcript integrity."""

    def test_hash_mismatch_rejected(self):
        """Stale plan (hash mismatch) is rejected."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "OLD_HASH",
            "cues": [],
        }

        with pytest.raises(ValueError, match="does not match"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="NEW_HASH",
                duration_s=100.0,
            )


class TestValidationForbiddenFields:
    """Validation guards against semantic reasoning leakage."""

    def test_forbidden_semantic_target_rejected(self):
        """semantic_target field is forbidden."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 15.0,
                    "preferred_timestamps_s": [12.0],
                    "kind": "ACTION",
                    "focus_terms": ["cutoff"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                    "semantic_target": "filter.cutoff",  # FORBIDDEN
                }
            ],
        }

        with pytest.raises(ValueError, match="forbidden.*semantic_target"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_forbidden_operation_rejected(self):
        """operation field is forbidden."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 15.0,
                    "preferred_timestamps_s": [12.0],
                    "kind": "ACTION",
                    "focus_terms": ["cutoff"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                    "operation": "set",  # FORBIDDEN
                }
            ],
        }

        with pytest.raises(ValueError, match="forbidden.*operation"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_forbidden_execution_rejected(self):
        """execution field is forbidden."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 15.0,
                    "preferred_timestamps_s": [12.0],
                    "kind": "ACTION",
                    "focus_terms": ["cutoff"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                    "execution": "mcp_call",  # FORBIDDEN
                }
            ],
        }

        with pytest.raises(ValueError, match="forbidden.*execution"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )


class TestValidationTimestamps:
    """Validation checks timestamp constraints."""

    def test_negative_start_rejected(self):
        """Negative start_s is rejected."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": -1.0,  # Invalid
                    "end_s": 15.0,
                    "preferred_timestamps_s": [12.0],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                }
            ],
        }

        with pytest.raises(ValueError, match="cannot be negative"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_end_before_start_rejected(self):
        """end_s < start_s is rejected."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 15.0,
                    "end_s": 10.0,  # Invalid
                    "preferred_timestamps_s": [],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                }
            ],
        }

        with pytest.raises(ValueError, match="end precedes start"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_end_exceeds_duration_rejected(self):
        """end_s > duration_s is rejected."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 150.0,  # Exceeds 100s duration
                    "preferred_timestamps_s": [],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                }
            ],
        }

        with pytest.raises(ValueError, match="exceeds video duration"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )

    def test_preferred_outside_window_rejected(self):
        """preferred_timestamps outside [start, end] rejected."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 15.0,
                    "preferred_timestamps_s": [20.0],  # Outside window
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 0.8,
                }
            ],
        }

        with pytest.raises(ValueError, match="outside cue window"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )


class TestValidationConfidence:
    """Validation checks confidence bounds."""

    def test_confidence_out_of_range_rejected(self):
        """confidence outside [0, 1] rejected."""
        plan = {
            "schema_version": "1.0",
            "runtime": "claude-code",
            "direct_anthropic_sdk": False,
            "api_key_used": False,
            "source_id": "yt_123",
            "video_id": "ABC123",
            "transcript_sha256": "abcdef",
            "cues": [
                {
                    "cue_id": "cue-1",
                    "segment_ids": ["seg-1"],
                    "start_s": 10.0,
                    "end_s": 15.0,
                    "preferred_timestamps_s": [12.0],
                    "kind": "ACTION",
                    "focus_terms": ["test"],
                    "verification_reason": "test",
                    "confidence": 1.5,  # Invalid
                }
            ],
        }

        with pytest.raises(ValueError, match="confidence out of range"):
            validate_transcript_cue_plan(
                plan,
                transcript_sha256="abcdef",
                duration_s=100.0,
            )
