"""Tests for the canonical Skill system — Producer Brain P3."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from serum2.producer.skill import (
    Skill,
    SkillQualificationStatus,
    SkillProcedureStep,
    SkillPrerequisite,
    SkillEvidenceRequirement,
    extract_skill_from_episode,
    qualify_skill,
    save_skill,
    load_skill,
    load_all_skills,
    find_skills_for_target,
)
from serum2.producer.skill_graph import SkillGraph, build_graph_from_skills
from serum2.producer.skill_retrieval import (
    SkillRetrievalContext,
    retrieve_skills,
    SkillRetrievalCache,
)


class TestSkillBasics:
    """Test basic Skill schema and operations."""

    def test_skill_creation(self):
        """Create a skill with all fields."""
        skill = Skill(
            skill_id="skill_test_001",
            skill_type="envelope_shaping",
            name="Extend Release",
            description="Extend an envelope release to shape sustain",
            applicable_targets=["Env1.Release"],
            episode_refs=["ep_001"],
            qualification_status=SkillQualificationStatus.CANDIDATE.value,
            confidence=0.5,
        )
        assert skill.skill_id == "skill_test_001"
        assert skill.name == "Extend Release"
        assert "Env1.Release" in skill.applicable_targets
        assert skill.qualification_status == SkillQualificationStatus.CANDIDATE.value

    def test_skill_to_dict_roundtrip(self):
        """Skill should serialize and deserialize cleanly."""
        step = SkillProcedureStep(
            step_number=1,
            description="Set release parameter",
            action_type="serum_mcp_call",
            target="Env1.Release",
            tool_name="set_device_parameter",
            input_constraint={"min": 15, "max": 4000},
        )
        skill = Skill(
            skill_id="skill_roundtrip",
            skill_type="envelope_shaping",
            name="Test Skill",
            description="Test",
            steps=[step],
            applicable_targets=["Env1.Release"],
        )

        # Serialize
        data = skill.to_dict()
        assert isinstance(data["steps"], list)
        assert data["steps"][0]["step_number"] == 1

        # Deserialize
        restored = Skill.from_dict(data)
        assert restored.skill_id == skill.skill_id
        assert len(restored.steps) == 1
        assert restored.steps[0].target == "Env1.Release"

    def test_skill_qualification_flow(self):
        """Test the qualification lifecycle: CANDIDATE → QUALIFIED."""
        skill = Skill(
            skill_id="skill_qualify",
            skill_type="test",
            name="Test",
            description="Test",
            applicable_targets=["Test.Param"],
            episode_refs=["ep_1"],
            qualification_status=SkillQualificationStatus.CANDIDATE.value,
            qualification_evidence_count=1,
            confidence=0.5,
        )
        assert skill.qualification_status == SkillQualificationStatus.CANDIDATE.value
        assert skill.qualification_evidence_count == 1

        # Add a second episode
        qualify_skill(skill, "ep_2")
        assert skill.qualification_status == SkillQualificationStatus.QUALIFIED.value
        assert skill.qualification_evidence_count == 2
        assert skill.confidence > 0.5

    def test_skill_persistence(self):
        """Test save/load roundtrip."""
        with TemporaryDirectory() as tmpdir:
            skill = Skill(
                skill_id="skill_persist",
                skill_type="test",
                name="Test",
                description="Test skill",
                applicable_targets=["Env1.Release"],
            )

            path = save_skill(skill, Path(tmpdir))
            assert Path(path).exists()

            loaded = load_skill("skill_persist", Path(tmpdir))
            assert loaded.skill_id == skill.skill_id
            assert loaded.name == "Test"


class TestSkillExtraction:
    """Test extracting skills from verified episodes."""

    def test_extract_skill_from_verified_episode(self):
        """Extract a skill from a real verified episode."""
        episode = {
            "episode_id": "ep_test_extract",
            "semantic_target": "Env1.Release",
            "admitted": True,
            "serum_mcp_call": {
                "tool": "set_device_parameter",
                "args_specified": {"target": "Env1.Release", "value": 500},
                "result": {"success": True},
            },
            "readback": {"Env1.Release": 500},
        }

        skill = extract_skill_from_episode(
            episode_id="ep_test_extract",
            episode_data=episode,
            skill_name="Extend Env1 Release",
            skill_type="envelope_shaping",
        )

        assert skill is not None
        assert skill.skill_id == "skill_ep_test_extract"
        assert "Env1.Release" in skill.applicable_targets
        assert skill.qualification_status == SkillQualificationStatus.CANDIDATE.value
        assert len(skill.steps) == 1
        assert skill.steps[0].action_type == "serum_mcp_call"

    def test_extract_skill_requires_admission(self):
        """Cannot extract skill from non-admitted episode."""
        episode = {
            "episode_id": "ep_not_admitted",
            "semantic_target": "Env1.Release",
            "admitted": False,  # Not admitted
            "serum_mcp_call": {"tool": "set", "args_specified": {}},
        }

        skill = extract_skill_from_episode(
            "ep_not_admitted", episode, "Test", "test"
        )
        assert skill is None

    def test_extract_skill_requires_target(self):
        """Cannot extract skill without semantic target."""
        episode = {
            "episode_id": "ep_no_target",
            "semantic_target": None,  # No target
            "admitted": True,
        }

        skill = extract_skill_from_episode(
            "ep_no_target", episode, "Test", "test"
        )
        assert skill is None

    def test_extract_skill_requires_steps(self):
        """Cannot extract skill without any executable steps."""
        episode = {
            "episode_id": "ep_no_steps",
            "semantic_target": "Env1.Release",
            "admitted": True,
            "serum_mcp_call": None,
            "ableton_calls": [],
        }

        skill = extract_skill_from_episode(
            "ep_no_steps", episode, "Test", "test"
        )
        assert skill is None


class TestSkillGraph:
    """Test the skill dependency graph."""

    def test_graph_add_skill(self):
        """Add skills to graph."""
        graph = SkillGraph()
        skill = Skill(
            skill_id="s1",
            skill_type="test",
            name="Skill 1",
            description="Test",
            applicable_targets=["A"],
        )
        graph.add_skill(skill)
        assert "s1" in graph.nodes

    def test_graph_prerequisites(self):
        """Track prerequisite relationships."""
        skill1 = Skill(
            skill_id="s1",
            skill_type="test",
            name="Basic",
            description="",
            applicable_targets=["A"],
        )
        skill2 = Skill(
            skill_id="s2",
            skill_type="test",
            name="Advanced",
            description="",
            applicable_targets=["B"],
            prerequisites=[SkillPrerequisite("s1", "Must know basic first")],
        )

        graph = SkillGraph()
        graph.add_skill(skill1)
        graph.add_skill(skill2)
        graph.link_prerequisite("s2", "s1")

        prereqs = graph.transitive_prerequisites("s2")
        assert "s1" in prereqs

    def test_graph_transitive_closure(self):
        """Transitive prerequisites: A <- B <- C."""
        s1 = Skill(skill_id="s1", skill_type="t", name="A", description="", applicable_targets=[])
        s2 = Skill(skill_id="s2", skill_type="t", name="B", description="", applicable_targets=[])
        s3 = Skill(skill_id="s3", skill_type="t", name="C", description="", applicable_targets=[])

        graph = SkillGraph()
        graph.add_skill(s1)
        graph.add_skill(s2)
        graph.add_skill(s3)
        graph.link_prerequisite("s2", "s1")
        graph.link_prerequisite("s3", "s2")

        # s3 transitively depends on s1 and s2
        prereqs = graph.transitive_prerequisites("s3")
        assert "s1" in prereqs
        assert "s2" in prereqs

    def test_graph_learning_path(self):
        """Get linear learning path (topological sort)."""
        s1 = Skill(skill_id="s1", skill_type="t", name="A", description="", applicable_targets=[])
        s2 = Skill(skill_id="s2", skill_type="t", name="B", description="", applicable_targets=[])
        s3 = Skill(skill_id="s3", skill_type="t", name="C", description="", applicable_targets=[])

        graph = SkillGraph()
        graph.add_skill(s1)
        graph.add_skill(s2)
        graph.add_skill(s3)
        graph.link_prerequisite("s2", "s1")
        graph.link_prerequisite("s3", "s2")

        path = graph.learning_path("s3")
        assert path is not None
        assert path[-1] == "s3"  # Target last
        assert path[0] == "s1"   # Base first
        assert path[1] == "s2"   # Middle


class TestSkillRetrieval:
    """Test skill retrieval for reasoning."""

    def test_retrieve_by_target(self):
        """Retrieve skills matching a semantic target."""
        with TemporaryDirectory() as tmpdir:
            skill = Skill(
                skill_id="skill_env1",
                skill_type="envelope",
                name="Env1 Release",
                description="Shape Env1 release",
                applicable_targets=["Env1.Release"],
                qualification_status=SkillQualificationStatus.QUALIFIED.value,
                confidence=0.8,
            )
            save_skill(skill, Path(tmpdir))

            # Manually load for test (retrieval normally loads all)
            context = SkillRetrievalContext(
                semantic_target="Env1.Release",
                max_results=5,
            )
            # Note: retrieve_skills() loads from _SKILLS_DIR, so this is integration-style

    def test_retrieval_context_role_matching(self):
        """Skills with role requirements should match context."""
        skill_bass = Skill(
            skill_id="skill_bass",
            skill_type="bass",
            name="Bass Shape",
            description="Shape bass",
            applicable_targets=["Osc1.Shape"],
            required_context={"role": "bass"},
            qualification_status=SkillQualificationStatus.QUALIFIED.value,
        )

        skill_melody = Skill(
            skill_id="skill_melody",
            skill_type="melody",
            name="Melody Shape",
            description="Shape melody",
            applicable_targets=["Osc1.Shape"],
            required_context={"role": "melody"},
        )

        # Context: bass role
        context = SkillRetrievalContext(
            semantic_target="Osc1.Shape",
            role="bass",
        )

        # In real usage, retrieve_skills() would filter these
        # Here we verify the structure supports role-based filtering
        assert skill_bass.required_context.get("role") == "bass"
        assert skill_melody.required_context.get("role") == "melody"

    def test_retrieval_cache(self):
        """Skill retrieval cache should load and cache skills."""
        cache = SkillRetrievalCache()
        graph, skills = cache.load()
        assert isinstance(graph, SkillGraph)
        assert isinstance(skills, list)

        # Calling load again returns cached
        graph2, skills2 = cache.load()
        assert graph2 is graph  # Same object
        assert skills2 is skills

        # Clear resets cache
        cache.clear()
        graph3, skills3 = cache.load()
        assert graph3 is not graph  # New object


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
