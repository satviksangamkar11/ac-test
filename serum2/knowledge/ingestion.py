"""Transcript → structured knowledge records.

Extracts sound-design claims and stores them as KnowledgeRecord dicts.
Result is cached to data/knowledge/ — idempotent.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"

_SOUND_KEYWORDS = [
    "bass", "kick", "snare", "synth", "lead", "pad", "pluck", "arp",
    "filter", "cutoff", "resonance", "attack", "release", "reverb", "delay",
    "wavetable", "oscillator", "lfo", "envelope", "distortion", "saturate",
    "bright", "dark", "warm", "cold", "thin", "fat", "wide", "stereo",
    "compression", "sidechain", "mix", "layering", "unison", "detune",
    "frequency", "eq", "high pass", "low pass", "band pass", "sub",
]

_TOPIC_MAP = [
    ("filter_cutoff", ["filter", "cutoff", "high pass", "low pass", "band pass"]),
    ("oscillator", ["oscillator", "wavetable", "osc", "waveform", "detune", "unison"]),
    ("envelope", ["attack", "release", "sustain", "decay", "envelope", "adsr"]),
    ("lfo", ["lfo", "modulation", "vibrato", "tremolo"]),
    ("fx", ["reverb", "delay", "chorus", "distortion", "saturate", "eq"]),
    ("dynamics", ["compression", "sidechain", "limiter"]),
    ("sound_character", ["bright", "dark", "warm", "cold", "thin", "fat", "wide"]),
]


def _detect_topic(sentence: str) -> str:
    low = sentence.lower()
    for topic, keywords in _TOPIC_MAP:
        if any(kw in low for kw in keywords):
            return topic
    return "general"


def _extract_claims(transcript: str, source_id: str) -> List[Dict[str, Any]]:
    sentences = re.split(r"(?<=[.!?])\s+", transcript)
    records = []
    now = datetime.now(timezone.utc).isoformat()
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if len(sentence) < 25:
            continue
        low = sentence.lower()
        if not any(kw in low for kw in _SOUND_KEYWORDS):
            continue
        rec_id = "k_" + hashlib.md5(f"{source_id}:{i}".encode()).hexdigest()[:8]
        records.append({
            "knowledge_id": rec_id,
            "source_id": source_id,
            "topic": _detect_topic(sentence),
            "claim": sentence[:300],
            "epistemic_status": "transcript_claim",
            "evidence": {"source": "youtube_transcript", "sentence_index": i},
            "timestamp": now,
        })
    return records


def ingest(source_id: str, transcript: str, force: bool = False) -> Dict[str, Any]:
    """Ingest transcript into knowledge store. Returns summary dict."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    out = KNOWLEDGE_DIR / f"{source_id}_knowledge.json"

    if out.exists() and not force:
        records = json.loads(out.read_text())
        return {"status": "ALREADY_INGESTED", "source_id": source_id,
                "record_count": len(records), "path": str(out)}

    records = _extract_claims(transcript, source_id)
    out.write_text(json.dumps(records, indent=2))
    return {"status": "INGESTED", "source_id": source_id,
            "record_count": len(records), "path": str(out)}


def retrieve_for_intent(source_id: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """Return top-10 records matching any keyword, sorted by match count."""
    f = KNOWLEDGE_DIR / f"{source_id}_knowledge.json"
    if not f.exists():
        return []
    records = json.loads(f.read_text())
    kws = [k.lower() for k in keywords]
    scored = [(sum(1 for k in kws if k in r["claim"].lower()), r) for r in records]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:10]]
