"""Minimum episode retrieval mechanism for producer learning.

Reads persisted production episodes and retrieves those relevant to a goal.

Authority rule:
  Episodes inform reasoning.
  Episodes do NOT authorize execution.
  Capability authority remains separate.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


EPISODE_STORAGE_DIR = Path(__file__).parent.parent / "qualification"


def retrieve_relevant_episodes(
    semantic_target: str,
    intent: Optional[str] = None,
    learning_eligible_only: bool = True,
) -> List[Dict[str, Any]]:
    """Retrieve episodes relevant to a goal.

    Args:
        semantic_target: exact semantic target to match (e.g., "Env1.Release")
        intent: optional intent substring to match
        learning_eligible_only: if True, filter to learning_eligible=true episodes

    Returns:
        List of matching episode dicts (preserves all original fields)

    Behavior:
      - Reads all .json files in qualification directory
      - Filters by semantic_target (exact match)
      - Optionally filters by intent (substring)
      - Optionally filters by learning_eligible
      - Returns complete episode dicts with all fields preserved
    """
    matching_episodes = []

    if not EPISODE_STORAGE_DIR.exists():
        return []

    # Find all .json files that look like episodes
    for episode_file in EPISODE_STORAGE_DIR.glob("*.json"):
        # Skip non-episode files
        if not episode_file.name.startswith(("ep_", "retrieval_")):
            continue

        try:
            with open(episode_file, "r") as f:
                episode = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Skip malformed files
            continue

        # Filter by semantic_target (exact match)
        if episode.get("semantic_target") != semantic_target:
            continue

        # Filter by intent (substring match, case-insensitive)
        if intent:
            episode_intent = (episode.get("human_intent") or "").lower()
            if intent.lower() not in episode_intent:
                continue

        # Filter by learning_eligible
        if learning_eligible_only and not episode.get("learning_eligible", False):
            continue

        # Preserve all fields exactly as stored
        matching_episodes.append(episode)

    return matching_episodes


def get_episode_by_id(episode_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific episode by its episode_id.

    Args:
        episode_id: the episode_id to retrieve

    Returns:
        Episode dict if found, None otherwise
    """
    # Try direct filename
    episode_file = EPISODE_STORAGE_DIR / f"{episode_id}.json"
    if episode_file.exists():
        try:
            with open(episode_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    # Try finding by searching all episodes
    for episode_file in EPISODE_STORAGE_DIR.glob("*.json"):
        if not episode_file.name.startswith(("ep_", "retrieval_")):
            continue

        try:
            with open(episode_file, "r") as f:
                episode = json.load(f)
                if episode.get("episode_id") == episode_id:
                    return episode
        except (json.JSONDecodeError, OSError):
            continue

    return None
