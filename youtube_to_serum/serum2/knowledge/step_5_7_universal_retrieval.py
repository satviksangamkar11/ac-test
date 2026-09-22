"""
STEP 5.7 — UNIVERSAL SEMANTIC RETRIEVAL

Retrieve relevant KnowledgeItems from the canonical 5.6 store.

Retrieval operates on UNIVERSAL MUSIC SEMANTICS:
  intent, concept, technique, role, context, genre, instrument, etc.

NOT Serum-specific.

Key distinctions:
  RETRIEVAL ≠ TEACHING
  RETRIEVAL ≠ EXECUTION
  RETRIEVAL ≠ AUTHORITY
  KNOWLEDGE ≠ EPISODE ≠ EVIDENCE ≠ CAPABILITY

Retrieval produces ranked, provenance-bearing KnowledgeItems.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from step_5_6_knowledge_store import KnowledgeStore
from knowledge_item import KnowledgeItem


class MatchType(Enum):
    """Categorize the type of match."""
    EXACT_CONCEPT = "EXACT_CONCEPT"
    EXACT_INTENT = "EXACT_INTENT"
    EXACT_TECHNIQUE = "EXACT_TECHNIQUE"
    EXACT_ROLE = "EXACT_ROLE"
    EXACT_CONTEXT = "EXACT_CONTEXT"
    LEXICAL_TEXT = "LEXICAL_TEXT"
    STRUCTURED_FIELD = "STRUCTURED_FIELD"
    SEMANTIC_BINDING = "SEMANTIC_BINDING"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    MULTIPLE_DIMENSION = "MULTIPLE_DIMENSION"


@dataclass
class UniversalQuery:
    """
    Universal semantic retrieval query.

    All fields optional. Query represents multi-dimensional intent.
    """
    # Textual query
    free_text: Optional[str] = None

    # Semantic dimensions
    intent: Optional[str] = None
    concept: Optional[str] = None
    technique: Optional[str] = None
    role: Optional[str] = None
    instrument: Optional[str] = None
    context: Optional[str] = None
    genre: Optional[str] = None
    subgenre: Optional[str] = None
    artist_style: Optional[str] = None
    production_stage: Optional[str] = None

    # Epistemic preference (advisory, not required)
    prefer_epistemic_status: Optional[str] = None  # e.g., "SOURCE_REPORTED"
    prefer_source_id: Optional[str] = None

    # Backend scope (optional)
    backend: Optional[str] = None  # e.g., "Serum" - filters but doesn't require

    def has_semantic_content(self) -> bool:
        """Check if query has meaningful content."""
        return any([
            self.free_text,
            self.intent,
            self.concept,
            self.technique,
            self.role,
            self.instrument,
            self.context,
            self.genre,
            self.subgenre,
            self.artist_style,
            self.production_stage,
        ])

    def active_dimensions(self) -> List[str]:
        """List non-None dimensions."""
        dims = []
        if self.intent:
            dims.append("intent")
        if self.concept:
            dims.append("concept")
        if self.technique:
            dims.append("technique")
        if self.role:
            dims.append("role")
        if self.instrument:
            dims.append("instrument")
        if self.context:
            dims.append("context")
        if self.genre:
            dims.append("genre")
        if self.subgenre:
            dims.append("subgenre")
        if self.artist_style:
            dims.append("artist_style")
        if self.production_stage:
            dims.append("production_stage")
        return dims


@dataclass
class MatchReason:
    """Explain why a KnowledgeItem matched."""
    match_type: MatchType
    dimension: Optional[str] = None  # e.g., "intent", "role"
    evidence: Optional[str] = None  # what matched what
    confidence: float = 0.5  # 0.0-1.0


@dataclass
class RetrievalResult:
    """
    A single ranked retrieval result.

    Contains full provenance and explainability.
    """
    knowledge_item: KnowledgeItem
    relevance_score: float  # 0.0-1.0
    match_reasons: List[MatchReason] = field(default_factory=list)
    primary_match_type: Optional[MatchType] = None
    is_ambiguous: bool = False
    ambiguity_candidates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for inspection."""
        return {
            "knowledge_item_id": self.knowledge_item.knowledge_item_id,
            "original_proposition": self.knowledge_item.original_proposition,
            "normalized_proposition": self.knowledge_item.normalized_proposition,
            "knowledge_type": self.knowledge_item.knowledge_type.value,
            "epistemic_status": self.knowledge_item.epistemic_status.value,
            "relevance_score": self.relevance_score,
            "primary_match_type": self.primary_match_type.value if self.primary_match_type else None,
            "match_reasons": [
                {
                    "match_type": r.match_type.value,
                    "dimension": r.dimension,
                    "evidence": r.evidence,
                    "confidence": r.confidence,
                }
                for r in self.match_reasons
            ],
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_candidates": self.ambiguity_candidates,
            "source_reference": {
                "source_id": self.knowledge_item.source_reference.source_id,
                "source_type": self.knowledge_item.source_reference.source_type,
                "source_title": self.knowledge_item.source_reference.source_title,
                "segment_ids": self.knowledge_item.source_reference.segment_ids,
            },
            "extraction_confidence": self.knowledge_item.extraction_confidence,
            "ambiguity": self.knowledge_item.ambiguity,
        }


class UniversalRetriever:
    """
    Universal knowledge retrieval engine.

    Operates on universal music semantics, not backend-specific logic.
    """

    def __init__(self, store: KnowledgeStore):
        """
        Initialize retriever with a knowledge store.

        Args:
            store: KnowledgeStore instance (5.6)
        """
        self.store = store
        self.min_relevance_score = 0.3

    def retrieve(self, query: UniversalQuery, top_k: Optional[int] = None) -> List[RetrievalResult]:
        """
        Retrieve relevant KnowledgeItems.

        Args:
            query: UniversalQuery with semantic dimensions
            top_k: limit results (None = all)

        Returns:
            Ranked list of RetrievalResult objects
        """
        if not query.has_semantic_content():
            return []

        # Retrieval pipeline:
        # 1. Candidate generation
        # 2. Scoring
        # 3. Ranking
        # 4. Filtering by relevance
        # 5. Limiting

        candidates = self._generate_candidates(query)
        scored = [self._score_result(cand, query) for cand in candidates]
        filtered = [r for r in scored if r.relevance_score >= self.min_relevance_score]
        ranked = sorted(filtered, key=lambda r: r.relevance_score, reverse=True)

        if top_k:
            ranked = ranked[:top_k]

        return ranked

    def _generate_candidates(self, query: UniversalQuery) -> List[Tuple[KnowledgeItem, List[MatchReason]]]:
        """
        Generate candidate KnowledgeItems that might match the query.

        Returns:
            List of (KnowledgeItem, match_reasons) tuples
        """
        candidates = []

        # Start with all items from store
        all_items = self.store.list()

        for item in all_items:
            reasons = self._compute_match_reasons(item, query)

            # Include if any dimension matches
            if reasons:
                candidates.append((item, reasons))

        return candidates

    def _compute_match_reasons(self, item: KnowledgeItem, query: UniversalQuery) -> List[MatchReason]:
        """
        Compute all match reasons between item and query.

        Returns:
            List of MatchReason objects (empty if no match)
        """
        reasons = []

        # Check free text match (highest priority)
        if query.free_text:
            if self._text_match(item, query.free_text):
                reasons.append(MatchReason(
                    match_type=MatchType.LEXICAL_TEXT,
                    evidence=f"'{query.free_text}' found in knowledge",
                    confidence=0.65,
                ))

        # Check semantic bindings (explicit dimensions)
        for binding in item.semantic_bindings:
            if query.concept and binding.dimension == "concept":
                if self._semantic_match(query.concept, binding.value):
                    reasons.append(MatchReason(
                        match_type=MatchType.EXACT_CONCEPT,
                        dimension="concept",
                        evidence=f"concept '{binding.value}' matches query '{query.concept}'",
                        confidence=0.9,
                    ))

            if query.intent and binding.dimension == "intent":
                if self._semantic_match(query.intent, binding.value):
                    reasons.append(MatchReason(
                        match_type=MatchType.EXACT_INTENT,
                        dimension="intent",
                        evidence=f"intent '{binding.value}' matches query '{query.intent}'",
                        confidence=0.9,
                    ))

            if query.technique and binding.dimension == "technique":
                if self._semantic_match(query.technique, binding.value):
                    reasons.append(MatchReason(
                        match_type=MatchType.EXACT_TECHNIQUE,
                        dimension="technique",
                        evidence=f"technique '{binding.value}' matches query '{query.technique}'",
                        confidence=0.85,
                    ))

            if query.role and binding.dimension == "role":
                if self._semantic_match(query.role, binding.value):
                    reasons.append(MatchReason(
                        match_type=MatchType.EXACT_ROLE,
                        dimension="role",
                        evidence=f"role '{binding.value}' matches query '{query.role}'",
                        confidence=0.85,
                    ))

            if query.context and binding.dimension == "context":
                if self._semantic_match(query.context, binding.value):
                    reasons.append(MatchReason(
                        match_type=MatchType.EXACT_CONTEXT,
                        dimension="context",
                        evidence=f"context '{binding.value}' matches query '{query.context}'",
                        confidence=0.8,
                    ))

        # Check concept/intent/technique/role/context in original proposition text
        prop_lower = item.original_proposition.lower()

        if query.concept and not any(r.match_type in [MatchType.EXACT_CONCEPT, MatchType.LEXICAL_TEXT] and r.dimension == "concept" for r in reasons):
            if query.concept.lower() in prop_lower or self._text_match_words(prop_lower, query.concept):
                reasons.append(MatchReason(
                    match_type=MatchType.LEXICAL_TEXT,
                    dimension="concept",
                    evidence=f"'{query.concept}' found in proposition text",
                    confidence=0.7,
                ))

        if query.intent and not any(r.match_type in [MatchType.EXACT_INTENT, MatchType.LEXICAL_TEXT] and r.dimension == "intent" for r in reasons):
            if query.intent.lower() in prop_lower or self._text_match_words(prop_lower, query.intent):
                reasons.append(MatchReason(
                    match_type=MatchType.LEXICAL_TEXT,
                    dimension="intent",
                    evidence=f"'{query.intent}' found in proposition text",
                    confidence=0.65,
                ))

        if query.technique and not any(r.match_type in [MatchType.EXACT_TECHNIQUE, MatchType.LEXICAL_TEXT] and r.dimension == "technique" for r in reasons):
            if query.technique.lower() in prop_lower or self._text_match_words(prop_lower, query.technique):
                reasons.append(MatchReason(
                    match_type=MatchType.LEXICAL_TEXT,
                    dimension="technique",
                    evidence=f"'{query.technique}' found in proposition text",
                    confidence=0.6,
                ))

        if query.role and not any(r.match_type in [MatchType.EXACT_ROLE, MatchType.LEXICAL_TEXT] and r.dimension == "role" for r in reasons):
            if query.role.lower() in prop_lower or self._text_match_words(prop_lower, query.role):
                reasons.append(MatchReason(
                    match_type=MatchType.LEXICAL_TEXT,
                    dimension="role",
                    evidence=f"'{query.role}' found in proposition text",
                    confidence=0.6,
                ))

        # Mark ambiguous items (but don't exclude them)
        if item.epistemic_status.value == "UNKNOWN":
            reasons.append(MatchReason(
                match_type=MatchType.AMBIGUOUS_MATCH,
                evidence="Item has ambiguous epistemic status (UNKNOWN)",
                confidence=0.2,  # Lower confidence for ambiguous
            ))

        return reasons

    def _score_result(
        self,
        candidate: Tuple[KnowledgeItem, List[MatchReason]],
        query: UniversalQuery
    ) -> RetrievalResult:
        """
        Score a candidate result.

        Scoring components:
          - Match type quality (exact > lexical)
          - Extraction confidence
          - Dimension count
          - Scope alignment
        """
        item, reasons = candidate

        if not reasons:
            return RetrievalResult(
                knowledge_item=item,
                relevance_score=0.0,
                match_reasons=[],
            )

        # Base score from best match reason
        max_reason_confidence = max((r.confidence for r in reasons), default=0.0)

        # Bonus for multiple matching dimensions
        unique_dimensions = len(set(r.dimension for r in reasons if r.dimension))
        dimension_bonus = unique_dimensions * 0.05

        # Factor in extraction confidence
        extraction_factor = item.extraction_confidence

        # Ambiguity penalty
        ambiguity_penalty = 0.2 if item.epistemic_status.value == "UNKNOWN" else 0.0

        # Combine
        final_score = (max_reason_confidence * extraction_factor) + dimension_bonus - ambiguity_penalty
        final_score = min(1.0, max(0.0, final_score))

        # Determine primary match type
        primary_match = max(reasons, key=lambda r: r.confidence).match_type if reasons else None

        result = RetrievalResult(
            knowledge_item=item,
            relevance_score=final_score,
            match_reasons=reasons,
            primary_match_type=primary_match,
            is_ambiguous=item.epistemic_status.value == "UNKNOWN",
            ambiguity_candidates=self._extract_candidates(item),
        )

        return result

    def _extract_candidates(self, item: KnowledgeItem) -> List[str]:
        """Extract candidate types from UNKNOWN item."""
        if item.notes and "Candidates:" in item.notes:
            # Parse "Candidates: [TYPE1, TYPE2, ...]" from notes
            try:
                start = item.notes.index("[") + 1
                end = item.notes.index("]")
                candidates_str = item.notes[start:end]
                return [c.strip() for c in candidates_str.split(",")]
            except (ValueError, IndexError):
                pass
        return []

    def _text_match(self, item: KnowledgeItem, query_text: str) -> bool:
        """Check if query text appears in item (case-insensitive, word-aware)."""
        query_lower = query_text.lower()
        prop_text = item.original_proposition.lower()
        if item.normalized_proposition:
            prop_text += " " + item.normalized_proposition.lower()

        # Try substring match first (for exact phrases)
        if query_lower in prop_text:
            return True

        # Try word-based match (for multi-word queries)
        query_words = set(query_lower.split())
        prop_words = set(prop_text.split())

        # Match if all query words appear in proposition
        return query_words.issubset(prop_words)

    def _text_match_words(self, target: str, query: str) -> bool:
        """Check if query words appear in target (word boundary)."""
        target_lower = target.lower()
        query_lower = query.lower()

        # Simple word overlap
        target_words = set(target_lower.split())
        query_words = set(query_lower.split())

        return bool(target_words & query_words)

    def _semantic_match(self, a: str, b: str) -> bool:
        """
        Check semantic match between two strings.

        Currently uses normalized substring matching.
        In future, could use embedding similarity.
        """
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()

        # Exact match
        if a_lower == b_lower:
            return True

        # Substring match (both directions)
        if a_lower in b_lower or b_lower in a_lower:
            return True

        return False

    def explain_result(self, result: RetrievalResult) -> str:
        """
        Generate human-readable explanation of why this item was retrieved.

        Returns:
            Explanation string
        """
        lines = [
            f"Knowledge Item: {result.knowledge_item.knowledge_item_id}",
            f"Relevance Score: {result.relevance_score:.2f}",
            f"Epistemic Status: {result.knowledge_item.epistemic_status.value}",
            f"Extraction Confidence: {result.knowledge_item.extraction_confidence:.2f}",
        ]

        if result.is_ambiguous:
            lines.append(f"⚠ AMBIGUOUS - Possible types: {', '.join(result.ambiguity_candidates)}")

        if result.match_reasons:
            lines.append("\nMatch Reasons:")
            for reason in result.match_reasons:
                lines.append(f"  • {reason.match_type.value}")
                if reason.evidence:
                    lines.append(f"    {reason.evidence}")

        lines.append(f"\nSource: {result.knowledge_item.source_reference.source_id}")
        lines.append(f"Original: {result.knowledge_item.original_proposition[:100]}...")

        return "\n".join(lines)
