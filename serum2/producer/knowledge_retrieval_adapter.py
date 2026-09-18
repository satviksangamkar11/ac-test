"""Knowledge retrieval adapter for the producer brain.

Wraps serum2.knowledge.step_5_7_universal_retrieval.UniversalRetriever
and handles sys.path so callers don't need to manage the knowledge-dir
import context.

RETRIEVAL ≠ AUTHORITY. Retrieved items are advisory only.
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
_CANONICAL_STORE = _KNOWLEDGE_DIR / "yt_f507169bd7cb_canonical_knowledge_store_5_6.json"


def _ensure_knowledge_path():
    """Ensure the knowledge dir is on sys.path (bare imports in step_5_x)."""
    kd = str(_KNOWLEDGE_DIR)
    if kd not in sys.path:
        sys.path.insert(0, kd)


def _discover_canonical_stores() -> List[Path]:
    """Find every per-source canonical KnowledgeItem store in the knowledge
    dir. Newly ingested YouTube sources (serum2.knowledge.ingestion.
    ingest_canonical) write {source_id}_canonical_knowledge_store_5_6.json
    alongside the original demo store — same naming convention, multiple
    files by design, discovered and queried together here."""
    return sorted(_KNOWLEDGE_DIR.glob("*_canonical_knowledge_store_5_6.json"))


def retrieve_knowledge_for_intent(
    intent_text: str,
    concept: Optional[str] = None,
    technique: Optional[str] = None,
    instrument: Optional[str] = "Serum",
    top_k: int = 8,
    store_path: Optional[str] = None,
    *,
    role: Optional[str] = None,
    context_terms: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve real KnowledgeItems relevant to a production intent.

    Replaces the hardcoded knowledge_ids in step6_live_vertical_slice.py.
    All returned items carry full provenance (source_id, segment_ids,
    epistemic_status, extraction_confidence).

    Args:
        intent_text: raw user intent or a short semantic phrase
        concept: optional concept term (e.g. "release", "envelope")
        technique: optional technique term (e.g. "sustain", "decay")
        instrument: optional instrument scope filter (default "Serum")
        top_k: maximum items to return
        store_path: override canonical store path (for testing)
        role: advisory musical role ("bass", "pad", "lead") — passed directly
              as UniversalQuery.role; the retriever's own _compute_match_reasons
              scores this via lexical fallback (0.6 confidence) against
              proposition text when no semantic binding exists.
        context_terms: additional advisory terms (genre, subgenre, artist,
              era, technique mentions from ProductionContext). Each term is
              run as ITS OWN single-term supplementary query and the results
              are merged with the primary query, deduped by knowledge_item_id.
              This is deliberate: UniversalRetriever._text_match() requires
              ALL words of a free_text query to be a subset of a proposition's
              words, so concatenating multiple terms into one free_text string
              makes matching *less* likely, not more. Querying each term alone
              exercises the retriever's real single-term matching semantics.
              A term that matches nothing (e.g. genre names/artists absent
              from the corpus) legitimately contributes zero items — that is
              a corpus-coverage fact, not a wiring defect.

    Returns:
        List of dicts with keys: knowledge_item_id, original_proposition,
        epistemic_status, relevance_score, match_reasons, source_reference
    """
    _ensure_knowledge_path()

    from step_5_6_knowledge_store import KnowledgeStore
    from step_5_7_universal_retrieval import UniversalRetriever, UniversalQuery

    if store_path:
        store_paths = [Path(store_path)]
    else:
        store_paths = _discover_canonical_stores() or [_CANONICAL_STORE]

    merged = []
    seen_ids = set()

    for sp in store_paths:
        if not sp.exists():
            continue
        store = KnowledgeStore(store_path=str(sp), create_if_missing=False)
        retriever = UniversalRetriever(store)

        primary_query = UniversalQuery(
            free_text=intent_text,
            concept=concept,
            technique=technique,
            instrument=instrument,
            role=role,
        )
        for r in retriever.retrieve(primary_query, top_k=top_k):
            if r.knowledge_item.knowledge_item_id not in seen_ids:
                merged.append(r)
                seen_ids.add(r.knowledge_item.knowledge_item_id)

        for term in (context_terms or []):
            term_query = UniversalQuery(free_text=term, instrument=instrument)
            for r in retriever.retrieve(term_query, top_k=3):
                if r.knowledge_item.knowledge_item_id not in seen_ids:
                    merged.append(r)
                    seen_ids.add(r.knowledge_item.knowledge_item_id)

    merged.sort(key=lambda r: r.relevance_score, reverse=True)
    merged = merged[:top_k]

    out = []
    for r in merged:
        item = r.knowledge_item
        out.append({
            "knowledge_item_id": item.knowledge_item_id,
            "original_proposition": item.original_proposition,
            "normalized_proposition": item.normalized_proposition,
            "epistemic_status": item.epistemic_status.value,
            "knowledge_type": item.knowledge_type.value,
            "relevance_score": r.relevance_score,
            "primary_match_type": r.primary_match_type.value if r.primary_match_type else None,
            "extraction_confidence": item.extraction_confidence,
            "source_reference": {
                "source_id": item.source_reference.source_id,
                "source_type": item.source_reference.source_type,
                "source_title": item.source_reference.source_title,
                "segment_ids": item.source_reference.segment_ids,
            },
            "match_reasons": [
                {
                    "match_type": r2.match_type.value,
                    "dimension": r2.dimension,
                    "evidence": r2.evidence,
                    "confidence": r2.confidence,
                }
                for r2 in r.match_reasons
            ],
        })
    return out


def build_knowledge_notes(retrieved_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Convert retrieved items to the knowledge_notes dict format used by Step 6.

    Returns:
        Dict mapping knowledge_item_id -> metadata dict
    """
    notes = {}
    for item in retrieved_items:
        notes[item["knowledge_item_id"]] = {
            "concept": item["original_proposition"][:120],
            "epistemic_status": item["epistemic_status"],
            "provenance": "source=%s segments=%s" % (
                item["source_reference"]["source_id"],
                item["source_reference"].get("segment_ids", [])[:3],
            ),
            "contribution": "relevance_score=%.2f match=%s" % (
                item["relevance_score"],
                item.get("primary_match_type", "unknown"),
            ),
            "extraction_confidence": item["extraction_confidence"],
        }
    return notes
