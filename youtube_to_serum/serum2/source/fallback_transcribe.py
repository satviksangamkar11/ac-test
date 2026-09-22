#!/usr/bin/env python
"""External local speech-to-text fallback for videos with no YouTube transcript.

Used only when youtube-transcript-api reports NO_TRANSCRIPT / NO_SUPPORTED_LANGUAGE.
Runs entirely outside Claude's reasoning context: downloads audio with yt-dlp,
transcribes it locally with faster-whisper, and writes a structured transcript
JSON to disk. Never uploads audio or transcript text anywhere.

Usage (as a library):
    from fallback_transcribe import transcribe_from_url
    result = transcribe_from_url(url, source_id, model_size="tiny")

Output artifact: data/transcripts/<source_id>_fallback.json
"""
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class FallbackResult:
    status: str  # AVAILABLE | UNAVAILABLE | NOT_RUN | ERROR
    engine: Optional[str] = None
    model: Optional[str] = None
    language: Optional[str] = None
    segment_count: int = 0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    output_path: Optional[str] = None
    error: Optional[str] = None


def _check_dependencies() -> Optional[str]:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return "yt-dlp not installed"
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return "faster-whisper not installed"
    return None


def _download_audio(url: str, dest_dir: Path) -> Path:
    import yt_dlp

    outtmpl = str(dest_dir / "audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    candidates = list(dest_dir.glob("audio.*"))
    if not candidates:
        raise RuntimeError("yt-dlp did not produce an audio file")
    return candidates[0]


def transcribe_from_url(
    url: str,
    source_id: str,
    model_size: str = "tiny",
    output_dir: str = "data/transcripts",
) -> FallbackResult:
    """Download audio for `url` and transcribe it locally with faster-whisper."""
    missing = _check_dependencies()
    if missing is not None:
        return FallbackResult(status="UNAVAILABLE", error=missing)

    from faster_whisper import WhisperModel

    print(f"[FALLBACK] Downloading audio for local transcription...", file=sys.stderr)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            audio_path = _download_audio(url, tmp_path)

            print(f"[FALLBACK] Running faster-whisper ({model_size})...", file=sys.stderr)
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            segments_iter, info = model.transcribe(str(audio_path))

            segments = []
            for i, seg in enumerate(segments_iter):
                segments.append({
                    "segment_id": i,
                    "text": seg.text.strip(),
                    "start": seg.start,
                    "start_time_sec": seg.start,
                    "duration": seg.end - seg.start,
                })

            if not segments:
                return FallbackResult(
                    status="UNAVAILABLE",
                    engine="faster-whisper",
                    model=model_size,
                    error="transcription produced no segments",
                )

            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / f"{source_id}_fallback.json"

            payload = {
                "source_id": source_id,
                "url": url,
                "transcription_engine": "faster-whisper",
                "model": model_size,
                "language": info.language,
                "language_probability": info.language_probability,
                "segment_count": len(segments),
                "segments": segments,
                "timestamp_provenance": "local_speech_recognition",
                "retrieval_timestamp": datetime.utcnow().isoformat() + "Z",
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=1)

            return FallbackResult(
                status="AVAILABLE",
                engine="faster-whisper",
                model=model_size,
                language=info.language,
                segment_count=len(segments),
                segments=segments,
                output_path=str(output_path),
            )

    except Exception as e:
        return FallbackResult(status="ERROR", error=str(e)[:300])


def main():
    if len(sys.argv) < 3:
        print("Usage: python fallback_transcribe.py <URL> <source_id> [model_size]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    source_id = sys.argv[2]
    model_size = sys.argv[3] if len(sys.argv) > 3 else "tiny"

    result = transcribe_from_url(url, source_id, model_size=model_size)

    print(f"[OK] status: {result.status}", file=sys.stderr)
    print(f"[OK] engine: {result.engine}", file=sys.stderr)
    print(f"[OK] segments: {result.segment_count}", file=sys.stderr)
    print(f"[OK] output_path: {result.output_path}", file=sys.stderr)
    if result.error:
        print(f"[ERROR] {result.error}", file=sys.stderr)

    sys.exit(0 if result.status == "AVAILABLE" else 1)


if __name__ == "__main__":
    main()
