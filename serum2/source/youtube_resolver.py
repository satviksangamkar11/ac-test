"""YouTube URL → SourceArtifact with transcript.

Tries youtube-transcript-api first (fast, no download),
falls back to yt-dlp auto-captions.
Result is cached to data/sources/ — idempotent.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT / "serum2" / "data" / "sources"


@dataclass
class SourceArtifact:
    source_id: str
    youtube_url: str
    video_id: str
    title: str
    channel: str
    published_at: str
    transcript: str
    transcript_source: str
    transcript_language: str
    transcription_method: str
    timestamp: str


def _extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    if not m:
        raise ValueError(f"Cannot extract video ID from: {url}")
    return m.group(1)


def _transcript_api(video_id: str) -> tuple[str, str]:
    """(text, language_code) via youtube-transcript-api."""
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
    api = YouTubeTranscriptApi()
    listing = api.list(video_id)
    try:
        t = listing.find_transcript(["en", "en-US", "en-GB"])
    except NoTranscriptFound:
        t = next(iter(listing))
    fetched = t.fetch()
    text = " ".join(s.text for s in fetched)
    return text, t.language_code


def _yt_dlp_metadata(video_id: str) -> dict:
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-download",
         f"https://www.youtube.com/watch?v={video_id}"],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        return {"title": "unknown", "uploader": "unknown", "upload_date": ""}
    data = json.loads(r.stdout.strip().splitlines()[-1])
    return {
        "title": data.get("title", "unknown"),
        "uploader": data.get("uploader", "unknown"),
        "upload_date": data.get("upload_date", ""),
    }


def resolve(url: str, cache_dir: Optional[Path] = None) -> SourceArtifact:
    """Resolve YouTube URL → SourceArtifact. Cached to disk (idempotent)."""
    video_id = _extract_video_id(url)
    source_id = "yt_" + hashlib.md5(url.encode()).hexdigest()[:12]

    cache = cache_dir or CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    cache_file = cache / f"{source_id}.json"

    if cache_file.exists():
        return SourceArtifact(**json.loads(cache_file.read_text()))

    meta = _yt_dlp_metadata(video_id)

    try:
        transcript, lang = _transcript_api(video_id)
        method = "youtube_transcript_api"
    except Exception as e1:
        raise RuntimeError(
            f"youtube-transcript-api failed ({e1}). "
            "Ensure the video has captions enabled."
        ) from e1

    artifact = SourceArtifact(
        source_id=source_id,
        youtube_url=url,
        video_id=video_id,
        title=meta["title"],
        channel=meta["uploader"],
        published_at=meta["upload_date"],
        transcript=transcript,
        transcript_source=method,
        transcript_language=lang,
        transcription_method=method,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    cache_file.write_text(json.dumps(asdict(artifact), indent=2))
    return artifact
