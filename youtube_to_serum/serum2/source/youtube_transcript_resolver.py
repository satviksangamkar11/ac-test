#!/usr/bin/env python
"""Robust YouTube transcript resolution using the current youtube-transcript-api
object-based API (YouTubeTranscriptApi().list(video_id) -> TranscriptList).

Selection order (never assumes English exists):
  1. manually-created English
  2. generated English
  3. manually-created requested language
  4. generated requested language
  5. manually-created other available language
  6. generated other available language
  7. translatable transcript, translated to English
  8. unavailable

Never fetches blindly: tracks are enumerated via list() first, then exactly
one transcript is fetched.
"""
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

STATUSES = (
    "AVAILABLE",
    "TRANSLATED",
    "NO_TRANSCRIPT",
    "NO_SUPPORTED_LANGUAGE",
    "FETCH_BLOCKED",
    "VIDEO_NOT_FOUND",
    "RATE_LIMITED",
    "NETWORK_ERROR",
    "API_ERROR",
)


@dataclass
class TranscriptResolution:
    status: str
    video_id: str
    language: Optional[str] = None
    language_code: Optional[str] = None
    is_generated: Optional[bool] = None
    is_translated: bool = False
    original_language: Optional[str] = None
    translated_language: Optional[str] = None
    selection_reason: str = ""
    available_tracks: List[Dict[str, Any]] = field(default_factory=list)
    transcript: Optional[List[Dict[str, Any]]] = None
    segment_count: int = 0
    error: Optional[str] = None


def _classify_exception(exc: Exception) -> str:
    """Map a youtube_transcript_api exception to one of the STATUSES."""
    try:
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            VideoUnavailable,
            VideoUnplayable,
            InvalidVideoId,
            AgeRestricted,
            IpBlocked,
            RequestBlocked,
            PoTokenRequired,
            CookieError,
            HTTPError,
            YouTubeRequestFailed,
            YouTubeDataUnparsable,
        )
    except ImportError:
        TranscriptsDisabled = VideoUnavailable = VideoUnplayable = InvalidVideoId = ()
        AgeRestricted = IpBlocked = RequestBlocked = PoTokenRequired = ()
        CookieError = HTTPError = YouTubeRequestFailed = YouTubeDataUnparsable = ()

    if isinstance(exc, TranscriptsDisabled):
        return "NO_TRANSCRIPT"
    if isinstance(exc, (VideoUnavailable, VideoUnplayable, InvalidVideoId, AgeRestricted)):
        return "VIDEO_NOT_FOUND"
    if isinstance(exc, (IpBlocked, RequestBlocked, PoTokenRequired, CookieError)):
        error_str = str(exc)
        if "429" in error_str or "too many" in error_str.lower():
            return "RATE_LIMITED"
        return "FETCH_BLOCKED"
    if isinstance(exc, (HTTPError, YouTubeRequestFailed, YouTubeDataUnparsable)):
        return "NETWORK_ERROR"
    error_str = str(exc)
    if "429" in error_str or "rate limit" in error_str.lower():
        return "RATE_LIMITED"
    return "API_ERROR"


def _enumerate_transcripts(transcript_list) -> List[Dict[str, Any]]:
    """Enumerate available transcripts via the public TranscriptList iterator."""
    tracks = []
    for transcript in transcript_list:
        tracks.append({
            "language": transcript.language,
            "language_code": transcript.language_code,
            "is_manual": not transcript.is_generated,
            "is_generated": transcript.is_generated,
            "is_translatable": transcript.is_translatable,
            "translation_languages": [
                tl.get("language_code") if isinstance(tl, dict) else getattr(tl, "language_code", None)
                for tl in getattr(transcript, "translation_languages", [])
            ],
            "_transcript": transcript,
        })
    return tracks


def _fetch_segments(transcript) -> List[Dict[str, Any]]:
    """Fetch a Transcript object and normalize it to a list of segment dicts."""
    fetched = transcript.fetch()
    segments = []
    for i, snippet in enumerate(fetched):
        segments.append({
            "segment_id": i,
            "text": snippet.text,
            "start": snippet.start,
            "start_time_sec": snippet.start,
            "duration": snippet.duration,
        })
    return segments


def resolve_youtube_transcript(
    video_id: str,
    preferred_languages: Optional[List[str]] = None,
) -> TranscriptResolution:
    """Resolve the best available transcript for a YouTube video.

    Enumerates tracks first via api.list(), then fetches exactly one
    transcript according to the documented preference order.
    """
    requested_languages = list(preferred_languages) if preferred_languages else []

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return TranscriptResolution(
            status="API_ERROR",
            video_id=video_id,
            error="youtube-transcript-api not installed",
        )

    api = YouTubeTranscriptApi()

    print(f"[INSPECT] Querying transcripts for {video_id}...", file=sys.stderr)

    try:
        transcript_list = api.list(video_id)
    except Exception as e:
        status = _classify_exception(e)
        return TranscriptResolution(
            status=status,
            video_id=video_id,
            selection_reason=f"list() failed: {type(e).__name__}",
            error=str(e)[:300],
        )

    tracks = _enumerate_transcripts(transcript_list)

    if not tracks:
        return TranscriptResolution(
            status="NO_TRANSCRIPT",
            video_id=video_id,
            selection_reason="No transcript tracks available",
        )

    print(f"[INSPECT] Found {len(tracks)} transcript track(s)", file=sys.stderr)
    for t in tracks:
        kind = "generated" if t["is_generated"] else "manual"
        print(f"  - {t['language']} ({t['language_code']}): {kind}", file=sys.stderr)

    public_tracks = [
        {k: v for k, v in t.items() if k != "_transcript"} for t in tracks
    ]

    def by(lang_code: str, generated: bool):
        for t in tracks:
            if t["language_code"] == lang_code and t["is_generated"] == generated:
                return t
        return None

    def first_available(generated: bool, exclude_codes):
        for t in tracks:
            if t["is_generated"] == generated and t["language_code"] not in exclude_codes:
                return t
        return None

    ordered_candidates = []  # list of (track, reason)
    last_fetch_error: Optional[Exception] = None

    # 1. manually-created English
    t = by("en", False) or by("en-US", False) or by("en-GB", False)
    if t:
        ordered_candidates.append((t, "manually-created English transcript"))

    # 2. generated English
    t = by("en", True) or by("en-US", True) or by("en-GB", True)
    if t:
        ordered_candidates.append((t, "generated English transcript"))

    # 3/4. requested language (manual then generated)
    for lang in requested_languages:
        if lang.lower().startswith("en"):
            continue
        t = by(lang, False)
        if t:
            ordered_candidates.append((t, f"manually-created requested language ({lang})"))
        t = by(lang, True)
        if t:
            ordered_candidates.append((t, f"generated requested language ({lang})"))

    # 5. manually-created other available language
    exclude = {"en", "en-US", "en-GB", *requested_languages}
    t = first_available(False, exclude)
    if t:
        ordered_candidates.append((t, f"manually-created other available language ({t['language_code']})"))

    # 6. generated other available language
    t = first_available(True, exclude)
    if t:
        ordered_candidates.append((t, f"generated other available language ({t['language_code']})"))

    for track, reason in ordered_candidates:
        transcript = track["_transcript"]
        try:
            segments = _fetch_segments(transcript)
        except Exception as e:
            print(f"[FETCH_ERROR] {track['language_code']}: {type(e).__name__}", file=sys.stderr)
            if last_fetch_error is None or _classify_exception(e) != "API_ERROR":
                last_fetch_error = e
            continue
        if not segments:
            continue
        return TranscriptResolution(
            status="AVAILABLE",
            video_id=video_id,
            language=transcript.language,
            language_code=transcript.language_code,
            is_generated=transcript.is_generated,
            is_translated=False,
            selection_reason=reason,
            available_tracks=public_tracks,
            transcript=segments,
            segment_count=len(segments),
        )

    # 7. translatable transcript -> translate to English
    for t in tracks:
        transcript = t["_transcript"]
        if not t["is_translatable"]:
            continue
        try:
            translated = transcript.translate("en")
            segments = _fetch_segments(translated)
        except Exception as e:
            print(f"[TRANSLATE_ERROR] {t['language_code']}: {type(e).__name__}", file=sys.stderr)
            if last_fetch_error is None or _classify_exception(e) != "API_ERROR":
                last_fetch_error = e
            continue
        if not segments:
            continue
        return TranscriptResolution(
            status="TRANSLATED",
            video_id=video_id,
            language="English (translated)",
            language_code="en",
            is_generated=transcript.is_generated,
            is_translated=True,
            original_language=transcript.language_code,
            translated_language="en",
            selection_reason=f"translated from {transcript.language_code} to en",
            available_tracks=public_tracks,
            transcript=segments,
            segment_count=len(segments),
        )

    # 8. unavailable
    if last_fetch_error is not None:
        status = _classify_exception(last_fetch_error)
        if status in ("FETCH_BLOCKED", "RATE_LIMITED", "NETWORK_ERROR"):
            return TranscriptResolution(
                status=status,
                video_id=video_id,
                available_tracks=public_tracks,
                selection_reason=f"tracks exist but fetch failed: {type(last_fetch_error).__name__}",
                error=str(last_fetch_error)[:300],
            )

    return TranscriptResolution(
        status="NO_SUPPORTED_LANGUAGE",
        video_id=video_id,
        available_tracks=public_tracks,
        selection_reason="No manual, generated, or translatable transcript could be resolved",
    )
