"""Regression tests for route_selection.py.

Pins the evidence-driven routing decisions against the actual current
repository evidence stores (targets.py, mcp_intent.MCP_HOST_MAP,
ContractRegistry, and the historical 37-contract inventory). If any of
these tests break, it means the underlying evidence changed -- re-derive
the expectation from the stores, never hardcode around a failure.
"""
import pytest

from serum2.producer.route_selection import (
    RouteSelector,
    ExecutionRoute,
    EvidenceTier,
)


@pytest.fixture(scope="module")
def selector():
    return RouteSelector()


def test_env1_release_requires_dawdreamer_only(selector):
    """Env1.Release is explicitly NOT in MCP_HOST_MAP (16.5.63 finding:
    Env1 Decay/Sustain/Release aren't exposed as VST3 automation params).
    It IS a fresh 4.Q CAUSAL_VERIFIED contract. This is the canonical
    'DawDreamer required' example."""
    d = selector.select_route("Env1.Release")
    assert d.route == ExecutionRoute.DAWDREAMER_SERUM
    assert d.dawdreamer_evidence == EvidenceTier.FRESH_4Q_VERIFIED
    assert d.dawdreamer_admission_ready is True
    assert d.ableton_mcp_admission_ready is False


def test_env1_attack_is_hybrid(selector):
    """Env1.Attack has BOTH a fresh 4.Q contract AND an MCP_HOST_MAP entry
    -- the canonical 'either route works' example."""
    d = selector.select_route("Env1.Attack")
    assert d.route == ExecutionRoute.HYBRID
    assert d.dawdreamer_admission_ready is True
    assert d.ableton_mcp_admission_ready is True


def test_filter_cutoff_is_mcp_only(selector):
    """Filter.Cutoff has MCP evidence but no DawDreamer contract (fresh or
    historical) at all."""
    d = selector.select_route("Filter.Cutoff")
    assert d.route == ExecutionRoute.ABLETON_MCP
    assert d.ableton_mcp_admission_ready is True
    assert d.dawdreamer_admission_ready is False


def test_osc1_volume_prefers_mcp_but_has_historical_dawdreamer_evidence(selector):
    """OSC1.Volume was CAUSAL_VERIFIED historically (pre-4.Q) but has not
    been re-qualified under the current authority substrate, so it is not
    currently DawDreamer-admission-ready. It IS MCP-admission-ready."""
    d = selector.select_route("OSC1.Volume")
    assert d.route == ExecutionRoute.ABLETON_MCP
    assert d.ableton_mcp_admission_ready is True
    assert d.dawdreamer_admission_ready is False
    assert d.dawdreamer_evidence == EvidenceTier.HISTORICAL_VERIFIED
    assert d.limitations, "historical-only evidence must be flagged, not silently dropped"


def test_historical_only_target_refuses_not_silently_substitutes(selector):
    """FXEQ.Freq1 has historical CAUSAL_VERIFIED evidence but no fresh
    re-qualification and no MCP mapping. Must REFUSE, not guess a route."""
    d = selector.select_route("FXEQ.Freq1")
    assert d.route == ExecutionRoute.REFUSE
    assert d.dawdreamer_evidence == EvidenceTier.HISTORICAL_VERIFIED
    assert d.dawdreamer_admission_ready is False


def test_fully_unqualified_target_refuses(selector):
    d = selector.select_route("OSC1.Detune")
    assert d.route == ExecutionRoute.REFUSE
    assert d.dawdreamer_evidence == EvidenceTier.UNQUALIFIED
    assert d.ableton_mcp_evidence == EvidenceTier.UNQUALIFIED


def test_unknown_vocabulary_refuses_explicitly(selector):
    """A name absent from SEMANTIC_TARGETS must refuse, never silently
    fuzzy-match to a similar-sounding target."""
    d = selector.select_route("something_made_up")
    assert d.route == ExecutionRoute.REFUSE
    assert d.capability_key is None
    assert "UNKNOWN_SEMANTIC_TARGET" in d.rationale


def test_route_selection_grants_no_authority(selector):
    """The route decision itself must never be mistaken for admission.
    This module has no admit()/execute() method -- verify that contract."""
    d = selector.select_route("Env1.Release")
    assert not hasattr(d, "admit")
    assert not hasattr(d, "execute")
    assert not hasattr(RouteSelector, "admit")
    assert not hasattr(RouteSelector, "execute")
