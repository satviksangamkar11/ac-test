#!/usr/bin/env python
"""YouTube source acquisition: transcript resolution with external fallbacks.

Decision tree:
    URL -> video_id -> youtube-transcript-api list()/fetch()
         -> tracks found -> AVAILABLE / TRANSLATED
         -> no tracks     -> local speech transcription fallback (fallback_transcribe.py)
                           -> success -> AVAILABLE (fallback engine)
                           -> failure -> AUDIO_REFERENCE / VISUAL_REFERENCE / TRANSCRIPT_UNAVAILABLE

Usage:
    python fetch_youtube.py "<YOUTUBE_URL>"
    python fetch_youtube.py "<YOUTUBE_URL>" --diagnose
    python fetch_youtube.py "<YOUTUBE_URL>" --no-fallback

External only - raw transcript text never enters Claude Code / stdout.
"""
import sys
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime

from youtube_transcript_resolver import resolve_youtube_transcript


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from a watch/shorts/youtu.be/embed/live URL."""
    patterns = [
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/live/([A-Za-z0-9_-]{11})",
        r"[?&]v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from URL: {url}")


def compute_source_id(url: str) -> str:
    """Compute source ID from URL."""
    return "yt_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _write_source_artifact(source_id: str, url: str, video_id: str, transcription: dict, artifacts: dict):
    sources_dir = Path("data/sources")
    sources_dir.mkdir(parents=True, exist_ok=True)
    source_path = sources_dir / f"{source_id}.json"

    source_metadata = {
        "source_id": source_id,
        "url": url,
        "video_id": video_id,
        "transcription": transcription,
        "artifacts": artifacts,
        "retrieval_timestamp": datetime.utcnow().isoformat() + "Z",
    }

    with open(source_path, "w", encoding="utf-8") as f:
        json.dump(source_metadata, f, indent=1)

    return source_path


def _try_local_fallback(url: str, source_id: str):
    """Attempt local speech transcription. Returns a FallbackResult-like object."""
    try:
        from fallback_transcribe import transcribe_from_url
    except ImportError as e:
        from fallback_transcribe import FallbackResult
        return FallbackResult(status="UNAVAILABLE", error=str(e))

    print("[FALLBACK] No YouTube transcript track usable; attempting local speech transcription...", file=sys.stderr)
    return transcribe_from_url(url, source_id, model_size="tiny")


def fetch_transcript(video_id: str, url: str, allow_fallback: bool = True) -> bool:
    """Resolve, fetch, and save a transcript. Attempts external fallbacks on failure."""
    source_id = compute_source_id(url)
    print(f"[RESOLVE] Resolving transcript for {video_id}...", file=sys.stderr)

    resolution = resolve_youtube_transcript(video_id)
    fallback_attempted = False
    fallback_result = None

    if resolution.status not in ("AVAILABLE", "TRANSLATED"):
        print(f"[STATUS] {resolution.status}", file=sys.stderr)
        if resolution.error:
            print(f"[ERROR] {resolution.error[:200]}", file=sys.stderr)
        if resolution.selection_reason:
            print(f"[REASON] {resolution.selection_reason}", file=sys.stderr)

        if resolution.status in ("NO_TRANSCRIPT", "NO_SUPPORTED_LANGUAGE") and allow_fallback:
            fallback_attempted = True
            fallback_result = _try_local_fallback(url, source_id)

        if fallback_result is None or fallback_result.status != "AVAILABLE":
            final_status = "TRANSCRIPT_UNAVAILABLE" if fallback_attempted else resolution.status
            transcription = {
                "status": final_status,
                "primary_engine": "youtube-transcript-api",
                "primary_status": resolution.status,
                "attempted_languages": ["en"],
                "available_tracks": resolution.available_tracks or [],
                "fallback_attempted": fallback_attempted,
                "fallback_status": fallback_result.status if fallback_result else "NOT_RUN",
                "fallback_error": fallback_result.error if fallback_result else None,
                "reference_mode": "AUDIO_REFERENCE" if fallback_attempted else None,
            }
            source_path = _write_source_artifact(
                source_id, url, video_id, transcription,
                artifacts={"raw_transcript": None, "structured_knowledge": None},
            )

            print(f"[OK] source_id: {source_id}", file=sys.stderr)
            print(f"[OK] video_id: {video_id}", file=sys.stderr)
            print(f"[OK] status: {final_status}", file=sys.stderr)
            print(f"[OK] fallback_used: {fallback_attempted}", file=sys.stderr)
            print(f"[OK] source_metadata: {source_path}", file=sys.stderr)
            return False

    # We have a usable transcript, either from YouTube or from the fallback.
    transcript_dir = Path("data/transcripts")
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / f"{source_id}.json"

    if resolution.status in ("AVAILABLE", "TRANSLATED"):
        engine = "youtube-transcript-api"
        language = resolution.language
        language_code = resolution.language_code
        is_generated = resolution.is_generated
        is_translated = resolution.is_translated
        segments = resolution.transcript or []
        selection_reason = resolution.selection_reason
        epistemic_status = "SOURCE_TRANSLATED" if resolution.is_translated else "SOURCE_ORIGINAL"
    else:
        engine = fallback_result.engine
        language = fallback_result.language
        language_code = fallback_result.language
        is_generated = True
        is_translated = False
        segments = fallback_result.segments
        selection_reason = f"local speech transcription ({fallback_result.model})"
        epistemic_status = "SOURCE_TRANSCRIBED_LOCALLY"

    transcript_data = {
        "source_id": source_id,
        "source_url": url,
        "video_id": video_id,
        "engine": engine,
        "language": language,
        "language_code": language_code,
        "is_generated": is_generated,
        "is_translated": is_translated,
        "original_language": resolution.original_language,
        "translated_language": resolution.translated_language,
        "epistemic_status": epistemic_status,
        "segment_count": len(segments),
        "segments": segments,
        "retrieval_timestamp": datetime.utcnow().isoformat() + "Z",
        "selection_reason": selection_reason,
    }

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=1)

    transcription_meta = {
        "status": "AVAILABLE" if resolution.status != "TRANSLATED" else "TRANSLATED",
        "engine": engine,
        "language": language,
        "language_code": language_code,
        "is_generated": is_generated,
        "is_translated": is_translated,
        "selection_reason": selection_reason,
        "segment_count": len(segments),
        "available_tracks": resolution.available_tracks or [],
        "fallback_attempted": fallback_attempted,
    }

    source_path = _write_source_artifact(
        source_id, url, video_id, transcription_meta,
        artifacts={
            "raw_transcript": str(transcript_path),
            "structured_knowledge": f"data/knowledge/{source_id}.json",
        },
    )

    # Print summary only (NO transcript text)
    print(f"[OK] source_id: {source_id}", file=sys.stderr)
    print(f"[OK] video_id: {video_id}", file=sys.stderr)
    print(f"[OK] status: {transcription_meta['status']}", file=sys.stderr)
    print(f"[OK] language: {language}", file=sys.stderr)
    print(f"[OK] generated: {is_generated}", file=sys.stderr)
    print(f"[OK] translated: {is_translated}", file=sys.stderr)
    print(f"[OK] segments: {len(segments)}", file=sys.stderr)
    print(f"[OK] transcript_path: {transcript_path}", file=sys.stderr)
    print(f"[OK] source_metadata: {source_path}", file=sys.stderr)

    return True


def diagnose(video_id: str) -> bool:
    """Diagnose transcript availability for a video. Prints only compact metadata."""
    print("VIDEO")
    print(f"  id: {video_id}")
    print()

    resolution = resolve_youtube_transcript(video_id)

    manual_en = any(t["language_code"].startswith("en") and t["is_manual"] for t in resolution.available_tracks)
    gen_en = any(t["language_code"].startswith("en") and t["is_generated"] for t in resolution.available_tracks)
    manual_other = any(not t["language_code"].startswith("en") and t["is_manual"] for t in resolution.available_tracks)
    gen_other = any(not t["language_code"].startswith("en") and t["is_generated"] for t in resolution.available_tracks)

    print("TRANSCRIPTS")
    print(f"  manual en: {'YES' if manual_en else 'NO'}")
    print(f"  generated en: {'YES' if gen_en else 'NO'}")
    print(f"  manual other: {'YES' if manual_other else 'NO'}")
    print(f"  generated other: {'YES' if gen_other else 'NO'}")
    print()

    primary_ok = resolution.status in ("AVAILABLE", "TRANSLATED")
    print("PRIMARY:")
    print(f"  youtube-transcript-api -> {resolution.status}")
    if resolution.selection_reason:
        print(f"  reason: {resolution.selection_reason}")
    print()

    print("FALLBACK:")
    if primary_ok:
        print("  local audio transcription -> NOT_RUN")
    else:
        from fallback_transcribe import _check_dependencies
        missing = _check_dependencies()
        if missing:
            print(f"  local audio transcription -> UNAVAILABLE ({missing})")
        else:
            print("  local audio transcription -> AVAILABLE (not run in diagnose mode)")
    print()

    print("RECOMMENDATION:")
    if primary_ok:
        print("  fetch and use transcript")
    elif resolution.status in ("NO_TRANSCRIPT", "NO_SUPPORTED_LANGUAGE"):
        print("  run local speech transcription fallback")
    else:
        print(f"  investigate {resolution.status.lower()}")

    return primary_ok


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_youtube.py <YOUTUBE_URL> [--diagnose] [--no-fallback]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    diagnose_mode = "--diagnose" in sys.argv
    allow_fallback = "--no-fallback" not in sys.argv

    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if diagnose_mode:
        success = diagnose(video_id)
        sys.exit(0 if success else 1)
    else:
        success = fetch_transcript(video_id, url, allow_fallback=allow_fallback)

        if success:
            print("\n[COMPLETE] Transcript fetched and saved to disk.", file=sys.stderr)
            print("[NOTE] Transcript text NOT printed to console (stays external).", file=sys.stderr)
            sys.exit(0)
        else:
            print("\n[FAILED] Transcript fetch unsuccessful.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
