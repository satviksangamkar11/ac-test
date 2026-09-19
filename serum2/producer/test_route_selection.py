"""Regression tests for route_selection.py.

Pins the evidence-driven routing decisions against the actual current
repository evidence stores (targets.py, mcp_intent.MCP_HOST_MAP,
ContractRegistry, and the historical 37-contract inventory). If any of
these tests break, it means the underlying evidence changed -- re-derive
the expectation from the stores, never hardcode around a failure.

For tests that need "some target belonging to evidence category X" (as
opposed to a SPECIFIC named capability the project actually cares about,
like Env1.Release), _find_target() discovers a matching real target from
SEMANTIC_TARGETS at run time instead of a hardcoded literal name. A
hardcoded stand-in silently drifts out of its category whenever the
evidence stores change (exactly what broke here: the canonical store grew
from a handful of fresh contracts to 32, and several literal target names
this file used to pin as "MCP-only"/"historical-only"/"unqualified" quietly
became fresh-verified instead) -- discovery makes the test track the real
evidence going forward instead of a snapshot of it.
"""
import pytest

from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.producer.route_selection import (
    RouteSelector,
    ExecutionRoute,
    EvidenceTier,
)


@pytest.fixture(scope="module")
def selector():
    return RouteSelector()


def _find_target(selector, *, dawdreamer_ready, mcp_ready, dawdreamer_tier=None):
    """Return (name, RouteDecision) for the first real SEMANTIC_TARGETS
    entry whose CURRENT evidence matches the given combination, or
    (None, None) if no such target exists right now. Never a fixed name."""
    for name in SEMANTIC_TARGETS:
        d = selector.select_route(name)
        if d.dawdreamer_admission_ready != dawdreamer_ready:
            continue
        if d.ableton_mcp_admission_ready != mcp_ready:
            continue
        if dawdreamer_tier is not None and d.dawdreamer_evidence != dawdreamer_tier:
            continue
        return name, d
    return None, None


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


def test_env1_attack_prefers_dawdreamer_when_both_ready(selector):
    """Env1.Attack has BOTH a fresh 4.Q contract AND an MCP_HOST_MAP entry.
    DawDreamer/Serum is the real-execution authority and takes priority;
    the MCP evidence is recorded in `limitations`, not a separate route."""
    d = selector.select_route("Env1.Attack")
    assert d.route == ExecutionRoute.DAWDREAMER_SERUM
    assert d.dawdreamer_admission_ready is True
    assert d.ableton_mcp_admission_ready is True
    assert any("Ableton MCP is also admission-ready" in lim for lim in d.limitations)


def test_some_both_ready_target_prefers_dawdreamer(selector):
    """Whatever target currently has BOTH a fresh 4.Q contract AND an
    MCP_HOST_MAP entry (Env1.Attack originally; Filter.Cutoff joined it once
    the canonical store grew — discovered dynamically, not pinned to
    either name) must prefer DawDreamer/Serum, recording the MCP evidence
    in `limitations` rather than a separate route."""
    name, d = _find_target(selector, dawdreamer_ready=True, mcp_ready=True)
    assert name is not None, "expected at least one both-ready target to exist"
    assert d.route == ExecutionRoute.DAWDREAMER_SERUM
    assert any("Ableton MCP is also admission-ready" in lim for lim in d.limitations)


def test_some_mcp_only_target_routes_to_mcp(selector):
    """Whatever target currently has MCP evidence but zero DawDreamer
    evidence (fresh or historical) must route to Ableton MCP — discovered
    dynamically since the specific target satisfying this shifts as the
    canonical store grows (OSC1.Volume today; not necessarily tomorrow)."""
    name, d = _find_target(
        selector, dawdreamer_ready=False, mcp_ready=True,
        dawdreamer_tier=EvidenceTier.UNQUALIFIED,
    )
    assert name is not None, "expected at least one MCP-only target to exist"
    assert d.route == ExecutionRoute.ABLETON_MCP


def test_historical_only_evidence_is_flagged_not_silently_dropped(selector):
    """No real target in the CURRENT evidence stores is HISTORICAL_VERIFIED-
    only (the canonical-store Phase-3 restore now loads every
    CAUSAL_VERIFIED entry as 'fresh', see ContractRegistry._load_fresh_
    contracts — HISTORICAL_VERIFIED is a reachable-but-currently-unused
    tier in real data). This exercises that code path directly by
    discovering a real, currently fully-unqualified target and injecting
    historical evidence onto it — never a hardcoded name, and never
    hardcoding around the branch having no live example today.

    Uses its OWN RouteSelector instance (not the module-scoped `selector`
    fixture) so the injected evidence never leaks into other tests.
    """
    base_name, base_d = _find_target(selector, dawdreamer_ready=False, mcp_ready=False)
    assert base_name is not None, "expected at least one fully-unqualified target to exist"
    assert base_d.capability_key, "discovered target must resolve to a capability_key"

    local_selector = RouteSelector()
    local_selector._historical_status[base_d.capability_key] = "CAUSAL_VERIFIED"
    d = local_selector.select_route(base_name)
    assert d.route == ExecutionRoute.REFUSE
    assert d.dawdreamer_evidence == EvidenceTier.HISTORICAL_VERIFIED
    assert d.dawdreamer_admission_ready is False
    assert d.limitations, "historical-only evidence must be flagged, not silently dropped"


def test_some_fully_unqualified_target_refuses(selector):
    """Whatever target currently has no evidence anywhere (no fresh
    contract, no historical CAUSAL_VERIFIED, no MCP mapping) must REFUSE —
    discovered dynamically, not pinned to a name that can later gain
    evidence and silently stop covering this case."""
    name, d = _find_target(selector, dawdreamer_ready=False, mcp_ready=False)
    assert name is not None, "expected at least one fully-unqualified target to exist"
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
