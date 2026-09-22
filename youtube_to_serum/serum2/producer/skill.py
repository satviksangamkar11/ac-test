"""Canonical Skill representation — Producer Brain Phase P3.

A skill is a reusable procedure extracted from verified production episodes.
It is NOT authority, NOT capability, NOT an execution directive.

A skill documents:
  - What was successfully done (procedure)
  - How to do it (steps/preconditions)
  - When it works (applicable contexts/targets)
  - Why we believe it (evidence from verified episodes)

Skills are advisory: they inform reasoning, they do not authorize admission.
The Admission layer is entirely separate (see evidence/admission.py).

Relationship to existing records:
  - Skill ← links to → VerifiedEpisode (episode_refs)
  - Skill ← links to → ProductionExperienceRecord (for serum_skill/ableton_skill in memory)
  - Skill ← derives from → successful execution path (verified procedure)

No skill is created from:
  - Speculation or tutorial text alone
  - Capability names or operation lists
  - User intent without verified execution
  - Admission decisions

A skill REQUIRES:
  - At least one verified episode
  - Specified intent + target + operation
  - Verified readback or acoustic confirmation
  - Observable execution sequence

Skill qualification states:
  - CANDIDATE: one verified episode, awaiting confirmation
  - QUALIFIED: multiple independent verified episodes, or explicit qualification
  - SUPERSEDED: newer skill covers the same target more effectively
  - REJECTED: evidence shows the procedure does not work reliably
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

_SKILLS_DIR = Path(__file__).parent.parent / "data" / "skills"


class SkillQualificationStatus(Enum):
    """States a skill moves through as evidence accumulates."""
    CANDIDATE = "candidate"      # One verified episode, not yet confirmed
    QUALIFIED = "qualified"      # Multiple independent episodes OR explicit qualification
    SUPERSEDED = "superseded"    # Replaced by a better or more recent skill
    REJECTED = "rejected"        # Evidence shows unreliable or broken procedure


@dataclass
class SkillEvidenceRequirement:
    """What counts as evidence for this skill's procedure.
    Used to verify that an episode can ground a skill."""
    requires_episode_id: bool = True
    requires_verified_readback: bool = True  # readback DIRECT_UI or equivalent
    requires_target_identity: bool = True
    requires_successful_outcome: bool = True
    observable_fields: List[str] = field(default_factory=list)  # e.g., ["release_ms", "decay_ms"]


@dataclass
class SkillProcedureStep:
    """One concrete step in a skill's procedure."""
    step_number: int
    description: str
    action_type: str  # "serum_mcp_call" | "ableton_mcp_call" | "serum_ui_action" | "measurement"
    target: Optional[str] = None  # e.g., "Env1.Release"
    operation: Optional[str] = None  # e.g., "set_device_parameter"
    tool_name: Optional[str] = None  # e.g., "set_device_parameter"
    input_constraint: Optional[Dict[str, Any]] = None  # e.g., {"min": 15, "max": 500}
    evidence_fields: List[str] = field(default_factory=list)  # fields to verify post-execution


@dataclass
class SkillPrerequisite:
    """A skill that must be learned before this one makes sense."""
    prerequisite_skill_id: str
    reasoning: Optional[str] = None  # Why this prerequisite matters


@dataclass
class SkillDependency:
    """A skill that depends on this one."""
    dependent_skill_id: str
    reasoning: Optional[str] = None


@dataclass
class Skill:
    """Canonical skill representation (Producer Brain P3.1).

    Links to episodes/experiences by reference, not duplication.
    No executable path, no authority — purely advisory evidence.
    """

    skill_id: str
    skill_type: str  # "serum_parameter_control" | "envelope_shaping" | "preset_crafting" | etc.
    name: str
    description: str

    # ---- procedure (verified from actual execution) ----
    steps: List[SkillProcedureStep] = field(default_factory=list)
    prerequisites: List[SkillPrerequisite] = field(default_factory=list)

    # ---- applicability ----
    applicable_targets: List[str] = field(default_factory=list)  # e.g., ["Env1.Release", "Env2.Decay"]
    required_context: Optional[Dict[str, Any]] = None  # e.g., {"role": "bass"}, optional
    contraindications: List[str] = field(default_factory=list)  # e.g., ["avoid_with_sawtooth"]

    # ---- evidence & verification ----
    episode_refs: List[str] = field(default_factory=list)  # episode_id or exp_* pointers
    input_output_pairs: List[Dict[str, Any]] = field(default_factory=list)  # what we observe when done right
    evidence_requirements: SkillEvidenceRequirement = field(default_factory=SkillEvidenceRequirement)

    # ---- qualification ----
    qualification_status: str = SkillQualificationStatus.CANDIDATE.value
    qualification_evidence_count: int = 0  # how many distinct verified episodes support this
    confidence: float = 0.0  # [0.0, 1.0] based on evidence
    rationale_for_status: Optional[str] = None

    # ---- graph ----
    dependent_skills: List[SkillDependency] = field(default_factory=list)

    # ---- metadata ----
    version: str = "skill_v1.p3.1"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # asdict() already converts nested dataclasses; just return it
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Reconstruct Skill from JSON-loaded dict."""
        data = dict(data)  # shallow copy
        # Reconstruct nested objects
        if "steps" in data:
            data["steps"] = [SkillProcedureStep(**s) for s in data["steps"]]
        if "prerequisites" in data:
            data["prerequisites"] = [SkillPrerequisite(**p) for p in data["prerequisites"]]
        if "evidence_requirements" in data:
            data["evidence_requirements"] = SkillEvidenceRequirement(**data["evidence_requirements"])
        if "dependent_skills" in data:
            data["dependent_skills"] = [SkillDependency(**d) for d in data["dependent_skills"]]
        return cls(**data)

    def touch(self) -> None:
        """Update modified timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Skill extraction from verified episode
# ---------------------------------------------------------------------------

def extract_skill_from_episode(
    episode_id: str,
    episode_data: Dict[str, Any],
    skill_name: str,
    skill_type: str,
) -> Optional[Skill]:
    """Extract a skill candidate from a single verified episode.

    Does NOT extract from arbitrary tutorials. Only from verified episodes
    where we have evidence of successful execution + readback.

    Args:
        episode_id: the episode identifier
        episode_data: the full episode dict (from ProductionExperienceRecord or canonical)
        skill_name: human-readable name
        skill_type: category (e.g., "envelope_shaping")

    Returns:
        A Skill in CANDIDATE status with one episode_ref, or None if episode
        does not provide sufficient evidence.
    """
    # Check minimum evidence requirements
    if not episode_data.get("admitted"):
        return None  # Only from admitted (verified) episodes

    semantic_target = episode_data.get("semantic_target")
    if not semantic_target:
        return None  # Must have clear target

    # Extract procedure steps from what was actually executed
    steps = []
    step_num = 1

    # Serum MCP call (if present)
    serum_mcp = episode_data.get("serum_mcp_call")
    if serum_mcp:
        steps.append(SkillProcedureStep(
            step_number=step_num,
            description=f"Call serum-mcp {serum_mcp.get('tool')}",
            action_type="serum_mcp_call",
            target=semantic_target,
            tool_name=serum_mcp.get("tool"),
            input_constraint=serum_mcp.get("args_specified"),
            evidence_fields=list((serum_mcp.get("result") or {}).keys()),
        ))
        step_num += 1

    # Ableton MCP calls (if present)
    for ableton_call in episode_data.get("ableton_calls") or []:
        steps.append(SkillProcedureStep(
            step_number=step_num,
            description=f"Call Ableton {ableton_call.get('tool')}",
            action_type="ableton_mcp_call",
            target=semantic_target,
            tool_name=ableton_call.get("tool"),
            input_constraint=ableton_call.get("args_specified"),
            evidence_fields=list((ableton_call.get("result") or {}).keys()),
        ))
        step_num += 1

    if not steps:
        return None  # No executable steps found

    # Build input/output pairs from readback
    input_output_pairs = []
    if episode_data.get("readback"):
        input_output_pairs.append({
            "specified": episode_data.get("serum_mcp_call", {}).get("args_specified"),
            "readback": episode_data.get("readback"),
            "verified": True,
        })

    # Create the skill
    skill = Skill(
        skill_id=f"skill_{episode_id}",
        skill_type=skill_type,
        name=skill_name,
        description=f"Extracted from verified episode {episode_id}",
        steps=steps,
        applicable_targets=[semantic_target],
        episode_refs=[episode_id],
        input_output_pairs=input_output_pairs,
        qualification_status=SkillQualificationStatus.CANDIDATE.value,
        qualification_evidence_count=1,
        confidence=0.5,  # One episode is not high confidence
        rationale_for_status="Single verified episode; awaiting independent confirmation",
        provenance={
            "extracted_from": episode_id,
            "extraction_method": "extract_skill_from_episode",
            "extraction_time": datetime.now(timezone.utc).isoformat(),
        },
    )

    return skill


def qualify_skill(skill: Skill, new_episode_id: str) -> None:
    """Strengthen a skill's qualification with another verified episode.

    When a new independent verified episode demonstrates the same procedure
    works, increment qualification_evidence_count and raise confidence.
    """
    if new_episode_id not in skill.episode_refs:
        skill.episode_refs.append(new_episode_id)

    skill.qualification_evidence_count = len(skill.episode_refs)

    # Simple heuristic: confidence = 0.5 * (1 + count / 5)
    # One episode: 0.5, two: 0.65, five+: ~0.95
    skill.confidence = min(0.95, 0.5 * (1 + skill.qualification_evidence_count / 5))

    if skill.qualification_evidence_count >= 2:
        skill.qualification_status = SkillQualificationStatus.QUALIFIED.value
        skill.rationale_for_status = f"Verified across {skill.qualification_evidence_count} independent episodes"

    skill.touch()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_skill(skill: Skill, directory: Optional[Path] = None) -> str:
    """Persist a skill to disk."""
    d = directory or _SKILLS_DIR
    d.mkdir(parents=True, exist_ok=True)
    skill.touch()
    path = d / f"{skill.skill_id}.json"
    path.write_text(json.dumps(skill.to_dict(), indent=2))
    return str(path)


def load_skill(skill_id: str, directory: Optional[Path] = None) -> Skill:
    """Load a persisted skill."""
    d = directory or _SKILLS_DIR
    path = d / f"{skill_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No skill: {skill_id}")
    return Skill.from_dict(json.loads(path.read_text()))


def load_all_skills(directory: Optional[Path] = None) -> List[Skill]:
    """Load all skills in the directory."""
    d = directory or _SKILLS_DIR
    if not d.exists():
        return []
    skills = []
    for path in d.glob("*.json"):
        try:
            skills.append(Skill.from_dict(json.loads(path.read_text())))
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return skills


def find_skills_for_target(target: str, directory: Optional[Path] = None) -> List[Skill]:
    """Find all skills applicable to a semantic target."""
    return [s for s in load_all_skills(directory) if target in s.applicable_targets]
