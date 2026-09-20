"""Dynamic Production Memory — Producer Brain V2, Phase P1.

The smallest possible memory layer on top of ProductionExperienceRecord.
A typed, provenance-tracked relationship index between:
  episode <-> source
  episode <-> context (genre/subgenre/artist_reference/era)
  episode <-> semantic concept
  episode <-> Serum skill        (reserved; populated starting Phase P3)
  episode <-> Ableton skill      (reserved; populated starting Phase P3)
  episode <-> outcome
  episode <-> prior related episodes

ADVISORY ONLY, ENFORCED BY OMISSION: this module contains no import of, and
must never call into, producer_brain, step_6_6_capability_resolution,
step_6_7_admission_handoff, or ContractRegistry. It stores and retrieves
relationships between experience/episode IDs; it has no code path that
could decide or influence whether anything is admitted. See
serum2/server/tests or the authority-isolation test for the live proof.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_MEMORY_PATH = Path(__file__).parent.parent / "data" / "memory" / "production_memory.json"

RELATION_TYPES = frozenset({
    "source",
    "context",
    "semantic_concept",
    "serum_skill",        # Links to Skill objects (P3+)
    "ableton_skill",      # Links to Skill objects (P3+)
    "learned_skill",      # Skill extracted from episode (P3+)
    "outcome",
    "related_episode",
})


@dataclass
class MemoryEdge:
    episode_id: str
    relation_type: str
    target: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionMemory:
    """File-backed relationship index. Advisory only — see module docstring."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _MEMORY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._edges: List[MemoryEdge] = self._load()

    def _load(self) -> List[MemoryEdge]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return []
        return [MemoryEdge(**e) for e in raw.get("edges", [])]

    def _persist(self) -> None:
        data = {
            "edges": [e.to_dict() for e in self._edges],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.write_text(json.dumps(data, indent=2))

    def link(
        self,
        episode_id: str,
        relation_type: str,
        target: str,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> MemoryEdge:
        if relation_type not in RELATION_TYPES:
            raise ValueError(
                f"Unknown relation_type {relation_type!r}; must be one of {sorted(RELATION_TYPES)}"
            )
        edge = MemoryEdge(
            episode_id=episode_id,
            relation_type=relation_type,
            target=target,
            evidence=evidence or {},
            confidence=confidence,
        )
        self._edges.append(edge)
        self._persist()
        return edge

    def related(
        self,
        episode_id: Optional[str] = None,
        relation_type: Optional[str] = None,
        target: Optional[str] = None,
    ) -> List[MemoryEdge]:
        out = self._edges
        if episode_id is not None:
            out = [e for e in out if e.episode_id == episode_id]
        if relation_type is not None:
            out = [e for e in out if e.relation_type == relation_type]
        if target is not None:
            out = [e for e in out if e.target == target]
        return list(out)


def link_experience(memory: ProductionMemory, record) -> List[MemoryEdge]:
    """Derive memory edges from one ProductionExperienceRecord.

    record: experience_record.ProductionExperienceRecord (duck-typed here to
    avoid a hard import dependency in either direction beyond attribute access).
    """
    edges: List[MemoryEdge] = []
    eid = record.experience_id

    if record.source_id:
        edges.append(memory.link(
            eid, "source", record.source_id,
            evidence={"source_url": record.source_url},
        ))

    ctx = record.production_context or {}
    for field_name in ("genre", "subgenre", "artist_reference", "era"):
        value = ctx.get(field_name)
        if value:
            edges.append(memory.link(
                eid, "context", value,
                evidence={"field": field_name},
            ))

    decision = record.brain_decision or {}
    concept = decision.get("resolved_concept") or decision.get("semantic_target")
    if concept:
        edges.append(memory.link(
            eid, "semantic_concept", concept,
            evidence={"execution_route": decision.get("execution_route")},
            confidence=1.0 if decision.get("admitted") else 0.5,
        ))

    outcome = record.outcome or {}
    decision_label = outcome.get("decision")
    if decision_label:
        edges.append(memory.link(eid, "outcome", decision_label, evidence=outcome))

    for prior_id in record.retrieved_episode_ids or []:
        edges.append(memory.link(
            eid, "related_episode", prior_id,
            evidence={"relation": "retrieved_as_prior_episode"},
        ))

    return edges


def link_skill(memory: ProductionMemory, experience_id: str, skill_id: str,
               skill_type: str = "learned_skill") -> MemoryEdge:
    """Link a skill to an experience after extraction.

    Called during skill extraction (P3.2) to record that experience_id
    generated or qualified skill_id.

    Args:
        memory: ProductionMemory instance
        experience_id: the experience_id that produced the skill
        skill_id: the skill_id that was extracted/qualified
        skill_type: "learned_skill" (extracted), "serum_skill" (qualified serum-MCP skill),
                    or "ableton_skill" (qualified Ableton-MCP skill)
    """
    if skill_type not in ("learned_skill", "serum_skill", "ableton_skill"):
        skill_type = "learned_skill"
    return memory.link(
        experience_id, skill_type, skill_id,
        evidence={"linked_at": datetime.now(timezone.utc).isoformat()},
        confidence=1.0,
    )
