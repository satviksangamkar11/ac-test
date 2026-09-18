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


_CANONICAL_KNOWLEDGE_DIR = Path(__file__).parent  # serum2/knowledge/


def ingest_canonical(
    source_id: str,
    transcript: str,
    source_url: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Ingest transcript into the CANONICAL KnowledgeItem store that
    ProducerBrain actually reads (via knowledge_retrieval_adapter.py's
    UniversalRetriever), not the lightweight KnowledgeRecord format above.

    Reuses the same sentence-splitting + sound-keyword extraction heuristic
    as ingest()/_extract_claims() above — only the output schema and
    storage layer differ. This closes the "two knowledge truths" gap: the
    old ingest() wrote {knowledge_id, topic, claim} to data/knowledge/,
    which the brain's retrieval never reads, so newly supplied YouTube
    videos were invisible to ProducerBrain's knowledge-informed reasoning.

    Writes to serum2/knowledge/{source_id}_canonical_knowledge_store_5_6.json
    — same naming convention and file format as the existing canonical demo
    store (yt_f507169bd7cb_canonical_knowledge_store_5_6.json). Multiple
    per-source stores coexist by design (this matches how the pre-existing
    demo corpus itself was organized); knowledge_retrieval_adapter discovers
    and queries all of them, merging results by relevance score. "One
    knowledge truth" means one schema and one retrieval path, not
    literally one file.
    """
    import sys as _sys
    if str(_CANONICAL_KNOWLEDGE_DIR) not in _sys.path:
        _sys.path.insert(0, str(_CANONICAL_KNOWLEDGE_DIR))

    from knowledge_item import (
        KnowledgeItem, KnowledgeType, EpistemicStatus,
        SemanticBinding, SourceReference, ExtractionMetadata,
    )
    from step_5_6_knowledge_store import KnowledgeStore

    store_path = _CANONICAL_KNOWLEDGE_DIR / f"{source_id}_canonical_knowledge_store_5_6.json"

    if store_path.exists() and not force:
        store = KnowledgeStore(store_path=str(store_path), create_if_missing=False)
        return {
            "status": "ALREADY_INGESTED", "source_id": source_id,
            "record_count": store.count(), "path": str(store_path),
        }

    claims = _extract_claims(transcript, source_id)
    store = KnowledgeStore(store_path=str(store_path), create_if_missing=True)
    now = datetime.now(timezone.utc).isoformat()

    for i, claim in enumerate(claims):
        sentence = claim["claim"]
        seg_id = f"seg_{i:04d}"
        prop_hash = KnowledgeItem.compute_proposition_hash(sentence)
        item_id = KnowledgeItem.compute_stable_id(source_id, [seg_id], prop_hash)

        item = KnowledgeItem(
            knowledge_item_id=item_id,
            source_reference=SourceReference(
                source_id=source_id,
                source_type="YOUTUBE_VIDEO",
                source_url=source_url,
                segment_ids=[seg_id],
            ),
            original_proposition=sentence,
            knowledge_type=KnowledgeType.OBSERVATION,
            epistemic_status=EpistemicStatus.SOURCE_REPORTED,
            semantic_bindings=[
                SemanticBinding(dimension="concept", value=claim["topic"], confidence=0.6),
            ],
            extraction_confidence=0.6,  # heuristic keyword/sentence split, not a trained classifier
            extraction_metadata=ExtractionMetadata(
                extraction_timestamp=now,
                extraction_method="heuristic_keyword_sentence_extraction_v1",
                extraction_confidence=0.6,
                raw_extraction_status="EXTRACTED",
                original_segments_count=1,
            ),
        )
        store.insert(item)

    return {
        "status": "INGESTED", "source_id": source_id,
        "record_count": len(claims), "path": str(store_path),
    }
