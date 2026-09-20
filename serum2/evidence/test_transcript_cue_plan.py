"""Tests for TranscriptCuePlan schema and validation."""

import pytest
from serum2.evidence.transcript_cue_plan import (
    TranscriptCue,
    TranscriptCuePlan,
    TranscriptCueKind,
    transcript_sha256,
)


class TestTranscriptCueSchema:
    """TranscriptCue immutability and structure."""

    def test_cue_is_frozen(self):
        """TranscriptCue is immutable."""
        cue = TranscriptCue(
            cue_id="cue-1",
            segment_ids=("seg-1", "seg-2"),
            start_s=10.0,
            end_s=15.0,
            preferred_timestamps_s=(12.0,),
            kind=TranscriptCueKind.ACTION,
            focus_terms=("cutoff",),
            verification_reason="test",
            confidence=0.8,
        )

        with pytest.raises((AttributeError, TypeError)):
            cue.cue_id = "cue-2"

    def test_cue_has_all_fields(self):
        """TranscriptCue contains required fields."""
        cue = TranscriptCue(
            cue_id="cue-1",
            segment_ids=("seg-1",),
            start_s=5.0,
            end_s=10.0,
            preferred_timestamps_s=(),
            kind=TranscriptCueKind.VALUE_MENTION,
            focus_terms=("resonance",),
            verification_reason="check value",
            confidence=0.9,
        )

        assert cue.cue_id == "cue-1"
        assert cue.start_s == 5.0
        assert cue.end_s == 10.0
        assert cue.confidence == 0.9


class TestTranscriptCuePlanSchema:
    """TranscriptCuePlan immutability and structure."""

    def test_plan_is_frozen(self):
        """TranscriptCuePlan is immutable."""
        plan = TranscriptCuePlan(
            schema_version="1.0",
            runtime="claude-code",
            direct_anthropic_sdk=False,
            api_key_used=False,
            source_id="yt_123",
            video_id="ABC123",
            source_url="https://youtube.com/watch?v=ABC123",
            transcript_sha256="abc",
            transcript_language="en",
            cues=(),
        )

        with pytest.raises((AttributeError, TypeError)):
            plan.runtime = "bad"

    def test_plan_requires_runtime_claude_code(self):
        """Plan runtime must be 'claude-code'."""
        plan = TranscriptCuePlan(
            schema_version="1.0",
            runtime="claude-code",
            direct_anthropic_sdk=False,
            api_key_used=False,
            source_id="yt_123",
            video_id="ABC123",
            source_url=None,
            transcript_sha256="sha",
            transcript_language="en",
        )

        assert plan.runtime == "claude-code"

    def test_plan_requires_no_sdk(self):
        """Plan must declare no SDK usage."""
        plan = TranscriptCuePlan(
            schema_version="1.0",
            runtime="claude-code",
            direct_anthropic_sdk=False,
            api_key_used=False,
            source_id="yt_123",
            video_id="ABC123",
            source_url=None,
            transcript_sha256="sha",
            transcript_language="en",
        )

        assert plan.direct_anthropic_sdk is False
        assert plan.api_key_used is False


class TestTranscriptSHA256:
    """Transcript integrity hashing."""

    def test_sha256_deterministic(self):
        """Same text produces same hash."""
        text = "Hello, world!"
        hash1 = transcript_sha256(text)
        hash2 = transcript_sha256(text)
        assert hash1 == hash2

    def test_sha256_different_for_different_text(self):
        """Different text produces different hash."""
        hash1 = transcript_sha256("text1")
        hash2 = transcript_sha256("text2")
        assert hash1 != hash2

    def test_sha256_is_hex(self):
        """Hash is hexadecimal string."""
        h = transcript_sha256("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
