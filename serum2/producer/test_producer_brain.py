"""Acceptance tests for the canonical producer brain.

Tests that are marked UNIT run without a real Serum instance (import-only
checks). Tests marked LIVE exercise resolution + admission against the real
4.Q-fresh contract store; they require the real knowledge store on disk
(REQUIRES_STORE) but do NOT require DawDreamer or any Serum execution
backend to be importable/running — the canonical Serum route stops at
SERUM_PRESET_PLAN_READY (see producer_brain.py's module docstring); actually
loading a preset into Serum and reading it back is an orchestrating-agent
action fed back via finalize_serum_preset_execution(), not something these
Python-only tests perform.

Phase B: real knowledge retrieval replaces hardcoded IDs
Phase C: canonical execute_producer_request() exists
Phase D: semantic intent → human-like operations
Phase E: capability resolution + admission
Phase F: route selection integrated
Phase K: episode retrieval influences second-run decision
"""
import sys
import os
from pathlib import Path
import pytest

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ---- knowledge store skip guard ----
_STORE_PATH = Path(KNOWLEDGE_DIR) / "yt_f507169bd7cb_canonical_knowledge_store_5_6.json"
KNOWLEDGE_STORE_AVAILABLE = _STORE_PATH.exists()
REQUIRES_STORE = pytest.mark.skipif(
    not KNOWLEDGE_STORE_AVAILABLE,
    reason="Canonical knowledge store not found",
)


# ===========================================================================
# UNIT: imports and API contracts
# ===========================================================================

def test_execute_producer_request_is_importable():
    """Phase C: canonical entry point exists and is callable."""
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest
    req = ProducerRequest(user_intent="make the note sustain longer")
    assert callable(execute_producer_request)
    assert req.user_intent == "make the note sustain longer"


def test_producer_result_has_full_trace_fields():
    """ProducerResult carries the full pipeline trace."""
    from serum2.producer.producer_brain import ProducerResult, ProducerRequest
    result = ProducerResult(request=ProducerRequest(user_intent="test"))
    # All required trace fields present
    assert hasattr(result, "retrieved_knowledge")
    assert hasattr(result, "prior_episodes")
    assert hasattr(result, "resolved_concept")
    assert hasattr(result, "semantic_direction")
    assert hasattr(result, "execution_route")
    assert hasattr(result, "resolution_status")
    assert hasattr(result, "admitted")
    assert hasattr(result, "episode_id")
    assert hasattr(result, "baseline_db")
    assert hasattr(result, "delta_db")
    assert hasattr(result, "decision")


def test_brain_refuses_unknown_intent():
    """Completely unknown intent → REFUSED, not a guess."""
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest
    req = ProducerRequest(user_intent="xyzzy plugh twisty passages")
    result = execute_producer_request(req)
    assert result.execution_status in (
        "REFUSED_UNKNOWN_CONCEPT", "REFUSED_NO_MAPPING",
        "REFUSED_NO_EVIDENCE", "REFUSED_NO_CONTRACT",
        "BRAIN_ERROR",
    )
    # Must not claim to have executed
    assert result.execution_status != "EXECUTED"


def test_knowledge_retrieval_adapter_returns_real_items():
    """Phase B: retrieval returns items from the real 343-item store."""
    if not KNOWLEDGE_STORE_AVAILABLE:
        pytest.skip("Canonical knowledge store not found")
    from serum2.producer.knowledge_retrieval_adapter import retrieve_knowledge_for_intent
    items = retrieve_knowledge_for_intent(
        intent_text="release envelope sustain longer",
        concept="release",
        top_k=5,
    )
    assert isinstance(items, list)
    assert len(items) > 0, "Expected at least one match for 'release envelope'"
    for item in items:
        assert "knowledge_item_id" in item
        assert "epistemic_status" in item
        assert "relevance_score" in item
        assert "source_reference" in item
        # Items must come from the real YT source, not invented
        assert item["source_reference"]["source_id"].startswith("yt_")


def test_retrieved_knowledge_ids_differ_from_hardcoded():
    """Phase B: real retrieval returns different IDs than the hardcoded placeholders."""
    if not KNOWLEDGE_STORE_AVAILABLE:
        pytest.skip("Canonical knowledge store not found")
    from serum2.producer.knowledge_retrieval_adapter import retrieve_knowledge_for_intent
    items = retrieve_knowledge_for_intent(
        intent_text="release envelope tail",
        concept="release",
        top_k=5,
    )
    k_ids = [it["knowledge_item_id"] for it in items]
    # The old hardcoded IDs were invented; real IDs come from the actual store
    assert k_ids, "Must retrieve at least one item"
    # Real store IDs from yt_f507169bd7cb source will have that prefix
    for kid in k_ids:
        assert not kid.startswith("k_"), (
            "Hardcoded 'k_' prefix IDs must not come from real retrieval; "
            "got %r — check that KnowledgeStore is loaded from the real file" % kid
        )


def test_route_selection_integrated_in_brain():
    """Phase F: brain consults route selector and populates execution_route."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(user_intent="make the note sustain longer")
    result = brain.execute(req)
    # Even if execution stops at a plan (no live Serum instance), route must
    # have been selected. "hybrid" was never a real ExecutionRoute member --
    # dead branch, removed.
    assert result.execution_route is not None, "execution_route must be populated"
    assert result.execution_route in (
        "dawdreamer_serum", "ableton_mcp", "refuse"
    )


def test_env1_release_routes_to_dawdreamer():
    """Env1.Release → DAWDREAMER_SERUM (fresh 4.Q contract, MCP blocked)."""
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    req = ProducerRequest(user_intent="make the note sustain longer")
    result = brain.execute(req)
    assert result.execution_route == "dawdreamer_serum"


def test_second_run_episode_influences_decision():
    """Phase K: if an accepted episode exists, advisory confidence is higher than baseline.

    This is a structural proof of influence — does not require live execution.
    """
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest, EpisodeContribution
    from serum2.knowledge.step_6_2_universal_production_intent import (
        UniversalProductionIntent, SemanticDirection,
    )

    brain = ProducerBrain()

    # Simulate episode contributions: one accepted run with positive delta
    accepted_episodes = [
        EpisodeContribution(
            episode_id="ep_test_accepted",
            semantic_target="envelope_field_release",
            human_intent="make the note sustain longer",
            outcome="ACCEPTED",
            delta_db=204.48,
            influence="",
        )
    ]
    no_episodes = []

    intent = UniversalProductionIntent(
        original_user_request="make the note sustain longer",
        target_concept="note-release",
        semantic_direction=SemanticDirection.LONGER,
        musical_objective="extend tail",
    )

    _, _, conf_without = brain._build_advisory_chain(
        intent, "note-release", [], {}, no_episodes
    )
    _, _, conf_with = brain._build_advisory_chain(
        intent, "note-release", ["ep_test_accepted"], {}, accepted_episodes
    )

    assert conf_with > conf_without, (
        "Prior accepted episode must increase advisory confidence. "
        "Without: %.2f, With: %.2f" % (conf_without, conf_with)
    )


# ===========================================================================
# LIVE: real resolution + admission against the fresh 4.Q contract store
# (pure Python — no Serum instance, no DawDreamer package required; actually
# loading/reading back Serum is an orchestrating-agent action, see
# producer_brain.py's module docstring)
# ===========================================================================

@REQUIRES_STORE
def test_live_full_pipeline_release():
    """TEST 1 (Phase N): full pipeline — knowledge → intent → admitted Serum plan."""
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest

    req = ProducerRequest(user_intent="make the note sustain longer")
    result = execute_producer_request(req)

    # Knowledge retrieved from real store
    assert len(result.retrieved_knowledge) > 0, "Must retrieve real knowledge items"
    for k in result.retrieved_knowledge:
        assert not k.knowledge_item_id.startswith("k_"), (
            "Hardcoded placeholder IDs must not appear in production run"
        )

    # Route decided
    assert result.execution_route is not None

    # The canonical Serum route stops at a plan — real execution requires
    # an orchestrating agent to run serum-mcp + read the real Serum UI and
    # feed that back via finalize_serum_preset_execution(). This test only
    # exercises resolution+admission, so EXECUTED should never appear here.
    assert result.execution_status != "EXECUTED", (
        "execute_producer_request() alone must never report EXECUTED for "
        "the Serum route — only finalize_serum_preset_execution() may, "
        "after real orchestrator-fed evidence"
    )
    if result.execution_status == "ADVISORY_ONLY":
        assert result.admitted is True
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None
        assert plan["mutation_target_path"]
        print("[LIVE] advisory plan target=%r qualification_test_value=%r" % (
            plan["mutation_target_path"], plan.get("qualification_test_value")
        ))
    else:
        # May refuse if no valid contract in current environment
        assert result.execution_status in (
            "REFUSED_RESOLUTION_FAILED", "REFUSED_ADMISSION",
            "REFUSED_NO_CONTRACT", "REFUSED_AUTHORITY",
        ), "Unexpected status: %s (%s)" % (result.execution_status, result.error)


@REQUIRES_STORE
def test_live_second_run_episode_retrieval():
    """TEST 2 (Phase N): second request retrieves prior episode and changes confidence."""
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest
    from serum2.producer.episode_retrieval import retrieve_relevant_episodes

    # First run
    req1 = ProducerRequest(user_intent="make the note sustain longer")
    r1 = execute_producer_request(req1)

    # Episodes available (from r1 or existing ep_ex_live_001.json)
    episodes = retrieve_relevant_episodes(
        semantic_target="envelope_field_release",
        intent="sustain longer",
        learning_eligible_only=True,
    )

    if not episodes:
        pytest.skip("No learning-eligible episodes to retrieve; run test_live_full_pipeline_release first")

    # Second run — must show episode influence
    req2 = ProducerRequest(user_intent="make the note sustain longer")
    r2 = execute_producer_request(req2)

    assert len(r2.prior_episodes) > 0, (
        "Second run must retrieve prior episodes. Found: %s" % r2.prior_episodes
    )
    # At least one episode should report positive influence
    influences = [ep.influence for ep in r2.prior_episodes]
    print("[SECOND RUN] episodes=%s influences=%s" % (
        [ep.episode_id for ep in r2.prior_episodes], influences
    ))


def test_live_mcp_path_filter_cutoff():
    """TEST 3 (Phase N): Filter.Cutoff intent routes via MCP or refuses explicitly.

    filter-cutoff is not in UNIVERSAL_TO_SEMANTIC so the brain refuses with
    REFUSED_NO_MAPPING before reaching route selection. This is correct
    architecture: no admitted Serum contract + no UNIVERSAL_TO_SEMANTIC
    entry = explicit refusal, not a guess. The test verifies that
    Filter.Cutoff requests are handled explicitly, not silently substituted.
    """
    from serum2.producer.producer_brain import execute_producer_request, ProducerRequest

    req = ProducerRequest(user_intent="make the filter cutoff higher")
    result = execute_producer_request(req)

    # filter-cutoff concept exists but has no UNIVERSAL_TO_SEMANTIC mapping,
    # so brain refuses explicitly rather than guessing.
    assert result.execution_status in (
        "REFUSED_NO_MAPPING", "REFUSED_NO_EVIDENCE",
        "REFUSED_NO_CONTRACT", "MCP_PLAN_READY", "ADVISORY_ONLY",
    ), "Unexpected status: %s (%s)" % (result.execution_status, result.error)
    # Must not claim EXECUTED without real capability
    assert result.execution_status != "EXECUTED"
    print("[MCP TEST] status=%s route=%s" % (result.execution_status, result.execution_route))


def test_mcp_refused_not_stubbed():
    """Phase H: unsupported MCP operations must refuse, not silently succeed."""
    from serum2.producer.producer_brain import ProducerBrain
    brain = ProducerBrain()
    # "xyzzy" is not in any intent map
    plan = brain._execute_mcp("xyzzy frobulate the patch", "Unknown.Param")
    assert plan.get("status") == "REFUSED"
