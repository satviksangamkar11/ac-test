"""Skill dependency graph — Producer Brain Phase P3.4.

Organizes learned skills as a DAG where edges represent prerequisite
relationships. Skills do NOT execute dependencies; they only describe
"skill X should be understood before attempting skill Y" based on
evidence and structure.

No execution path runs this graph. No admission decision reads it.
It is purely for advisory skill organization and retrieval.

Graph operations:
  - Add a skill node
  - Link prerequisites (derived from evidence, not manual insertion)
  - Query transitive closure (all skills needed to learn X)
  - Find candidate skills for a context
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from serum2.producer.skill import Skill, SkillPrerequisite


_GRAPH_PATH = Path(__file__).parent.parent / "data" / "skill_graph.json"


@dataclass
class SkillNode:
    """A node in the dependency graph."""
    skill_id: str
    name: str
    prerequisites: List[str] = field(default_factory=list)  # skill_ids
    dependents: List[str] = field(default_factory=list)     # skill_ids that require this


@dataclass
class SkillGraphSnapshot:
    """Serializable snapshot of graph state."""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # skill_id -> node data
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "skill_graph_v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillGraph:
    """In-memory skill dependency graph."""

    def __init__(self):
        self.nodes: Dict[str, SkillNode] = {}

    def add_skill(self, skill: Skill) -> None:
        """Register a skill in the graph."""
        node = SkillNode(
            skill_id=skill.skill_id,
            name=skill.name,
            prerequisites=[p.prerequisite_skill_id for p in skill.prerequisites],
        )
        self.nodes[skill.skill_id] = node

        # Update dependents in reverse direction
        for prereq_id in node.prerequisites:
            if prereq_id in self.nodes:
                if skill.skill_id not in self.nodes[prereq_id].dependents:
                    self.nodes[prereq_id].dependents.append(skill.skill_id)

    def link_prerequisite(self, skill_id: str, prerequisite_id: str, reasoning: Optional[str] = None) -> None:
        """Add a prerequisite edge (skill_id requires prerequisite_id).

        This is called when evidence shows the relationship.
        """
        if skill_id not in self.nodes:
            raise ValueError(f"Unknown skill: {skill_id}")
        if prerequisite_id not in self.nodes:
            raise ValueError(f"Unknown prerequisite: {prerequisite_id}")

        node = self.nodes[skill_id]
        if prerequisite_id not in node.prerequisites:
            node.prerequisites.append(prerequisite_id)

        # Reverse link
        prereq_node = self.nodes[prerequisite_id]
        if skill_id not in prereq_node.dependents:
            prereq_node.dependents.append(skill_id)

    def transitive_prerequisites(self, skill_id: str) -> Set[str]:
        """All skills that must be learned before this one (transitive closure)."""
        if skill_id not in self.nodes:
            return set()

        visited = set()
        stack = [skill_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            node = self.nodes.get(current)
            if node:
                for prereq_id in node.prerequisites:
                    if prereq_id not in visited:
                        stack.append(prereq_id)

        visited.discard(skill_id)  # Don't include the skill itself
        return visited

    def transitive_dependents(self, skill_id: str) -> Set[str]:
        """All skills that depend on this one (direct and indirect)."""
        if skill_id not in self.nodes:
            return set()

        visited = set()
        stack = [skill_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            node = self.nodes.get(current)
            if node:
                for dependent_id in node.dependents:
                    if dependent_id not in visited:
                        stack.append(dependent_id)

        visited.discard(skill_id)
        return visited

    def learning_path(self, target_skill_id: str) -> Optional[List[str]]:
        """Return a linear learning order to reach target_skill_id.

        Returns prerequisites in order (deepest first), then the target.
        Returns None if there's a cycle.
        """
        if target_skill_id not in self.nodes:
            return None

        prerequisites = self.transitive_prerequisites(target_skill_id)
        if not prerequisites:
            return [target_skill_id]

        # Topological sort of prerequisites + target
        order = []
        visited = set()

        def visit(skill_id: str) -> bool:
            if skill_id in visited:
                return True
            if skill_id in ["visiting"]:  # Cycle detection
                return False
            visited.add(skill_id)

            node = self.nodes.get(skill_id)
            if node:
                for prereq_id in node.prerequisites:
                    if not visit(prereq_id):
                        return False

            order.append(skill_id)
            return True

        # Visit all prerequisites
        for prereq_id in prerequisites:
            if not visit(prereq_id):
                return None  # Cycle detected

        # Then the target
        order.append(target_skill_id)
        return order

    def snapshot(self) -> SkillGraphSnapshot:
        """Export graph to a serializable snapshot."""
        nodes_data = {}
        for skill_id, node in self.nodes.items():
            nodes_data[skill_id] = asdict(node)
        return SkillGraphSnapshot(nodes=nodes_data)

    def from_snapshot(self, snap: SkillGraphSnapshot) -> None:
        """Restore graph from a snapshot."""
        self.nodes = {}
        for skill_id, node_data in snap.nodes.items():
            self.nodes[skill_id] = SkillNode(**node_data)

    def save(self, path: Optional[Path] = None) -> str:
        """Persist graph to disk."""
        p = path or _GRAPH_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.snapshot().to_dict(), indent=2))
        return str(p)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "SkillGraph":
        """Load graph from disk."""
        p = path or _GRAPH_PATH
        if not p.exists():
            return cls()
        data = json.loads(p.read_text())
        snap = SkillGraphSnapshot(**data)
        graph = cls()
        graph.from_snapshot(snap)
        return graph


def build_graph_from_skills(skills: List[Skill]) -> SkillGraph:
    """Construct a graph from a list of Skill objects."""
    graph = SkillGraph()

    # Add all skills first
    for skill in skills:
        graph.add_skill(skill)

    # Then add prerequisite edges from skill metadata
    for skill in skills:
        for prereq in skill.prerequisites:
            try:
                graph.link_prerequisite(skill.skill_id, prereq.prerequisite_skill_id, prereq.reasoning)
            except ValueError:
                # Prerequisite skill not yet registered; skip edge
                pass

    return graph
