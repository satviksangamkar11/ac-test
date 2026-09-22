"""Skill retrieval for advisory reasoning — Producer Brain Phase P3.5.

Extends existing episode retrieval to return reusable procedures.

Input: request context + semantic target
Output: relevant skills (bounded, ranked by confidence)

Skills are NEVER execution directives. They inform the producer brain's
reasoning step, nothing more. The admission layer remains separate.

Architecture:
  UniversalProductionIntent
        ↓
  production context + semantic target + intent
        ↓
  retrieve relevant skills
        ↓
  bounded skill set (ranked by confidence)
        ↓
  advisory reasoning (producer_brain)
        ↓
  capability resolution (unchanged)
        ↓
  admission (unchanged, never learned)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from serum2.producer.skill import Skill, load_all_skills, find_skills_for_target
from serum2.producer.skill_graph import SkillGraph, build_graph_from_skills


class SkillRetrievalContext:
    """Contextual parameters for skill retrieval."""
    def __init__(
        self,
        semantic_target: str,
        user_intent: Optional[str] = None,
        role: Optional[str] = None,
        character: Optional[str] = None,
        production_context: Optional[Dict[str, Any]] = None,
        max_results: int = 5,
    ):
        self.semantic_target = semantic_target
        self.user_intent = user_intent
        self.role = role
        self.character = character
        self.production_context = production_context or {}
        self.max_results = max_results


def retrieve_skills(context: SkillRetrievalContext) -> List[Skill]:
    """Retrieve relevant skills for an intent.

    Filter by:
      1. Applicable targets (exact semantic match or related)
      2. Required context (role, character if specified)
      3. Confidence (prefer qualified skills)
      4. Specificity (more targeted skills ranked higher)

    Returns:
        List of skills ranked by relevance, limited to max_results
    """
    # Load all available skills
    all_skills = load_all_skills()
    if not all_skills:
        return []

    # Filter by applicable target
    candidate_skills = []
    for skill in all_skills:
        if context.semantic_target in skill.applicable_targets:
            candidate_skills.append(skill)

    if not candidate_skills:
        return []

    # Filter by context requirements (if skill specifies them)
    filtered_skills = []
    for skill in candidate_skills:
        if skill.required_context:
            # Skill has context requirements; check if they match
            if context.role and skill.required_context.get("role") != context.role:
                continue  # Role mismatch
            if context.character and skill.required_context.get("character") != context.character:
                continue  # Character mismatch
        # No mismatch; include skill
        filtered_skills.append(skill)

    if not filtered_skills:
        filtered_skills = candidate_skills  # Fall back to unfiltered if all have mismatches

    # Rank by:
    #   1. Qualification status (qualified > candidate > superseded/rejected)
    #   2. Confidence score (higher = better)
    #   3. Number of supporting episodes (more = more reliable)
    def rank_key(skill: Skill) -> tuple:
        status_rank = {
            "qualified": 3,
            "candidate": 2,
            "superseded": 1,
            "rejected": 0,
        }
        return (
            status_rank.get(skill.qualification_status, 0),
            skill.confidence,
            len(skill.episode_refs),
        )

    ranked = sorted(filtered_skills, key=rank_key, reverse=True)
    return ranked[:context.max_results]


def retrieve_skill_prerequisites(skill_id: str) -> List[Skill]:
    """Get all prerequisite skills for a given skill.

    Used to check if prerequisites are met before attempting a skill.
    """
    try:
        skill = Skill.from_dict(
            __import__("json").loads(
                (__import__("pathlib").Path(__file__).parent.parent / "data" / "skills" / f"{skill_id}.json").read_text()
            )
        )
    except FileNotFoundError:
        return []

    all_skills = {s.skill_id: s for s in load_all_skills()}
    prerequisites = []
    for prereq in skill.prerequisites:
        if prereq.prerequisite_skill_id in all_skills:
            prerequisites.append(all_skills[prereq.prerequisite_skill_id])

    return prerequisites


def build_skill_retrieval_graph() -> SkillGraph:
    """Build and cache the full skill graph for transitive queries.

    Called once at startup or when skills change.
    """
    skills = load_all_skills()
    return build_graph_from_skills(skills)


class SkillRetrievalCache:
    """Lightweight cache for skill graph (used by advisory reasoning)."""

    def __init__(self):
        self._graph: Optional[SkillGraph] = None
        self._skills: Optional[List[Skill]] = None

    def load(self) -> tuple[SkillGraph, List[Skill]]:
        """Load graph + all skills into cache."""
        if self._skills is None:
            self._skills = load_all_skills()
        if self._graph is None:
            self._graph = build_graph_from_skills(self._skills)
        return self._graph, self._skills

    def clear(self) -> None:
        """Clear cache (call after skills change)."""
        self._graph = None
        self._skills = None

    def get_learning_path(self, target_skill_id: str) -> Optional[List[str]]:
        """Get prerequisite chain for a skill."""
        graph, _ = self.load()
        return graph.learning_path(target_skill_id)

    def get_required_skills(self, target_skill_id: str) -> List[Skill]:
        """Get all skills needed before attempting target_skill_id."""
        graph, skills = self.load()
        prerequisites = graph.transitive_prerequisites(target_skill_id)
        skill_map = {s.skill_id: s for s in skills}
        return [skill_map[sid] for sid in prerequisites if sid in skill_map]


# Global cache instance
_global_skill_cache = SkillRetrievalCache()


def get_retrieval_cache() -> SkillRetrievalCache:
    """Access the global skill retrieval cache."""
    return _global_skill_cache
