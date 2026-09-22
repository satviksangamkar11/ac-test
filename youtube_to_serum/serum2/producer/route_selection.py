"""ROUTE SELECTION — Serum vs Ableton MCP vs Hybrid vs Refuse.

Answers, for one semantic target (e.g. "OSC1.Volume", "Env1.Release"):
    "Which real execution backend has EVIDENCE that it can perform this
     operation, and which is currently ADMITTABLE right now?"

The ExecutionRoute.DAWDREAMER_SERUM value (and the "DawDreamer" naming
throughout this module) refers to the qualification campaign that verified
these contracts, not to an active DawDreamer-based executor — the actual
canonical execution mechanism for this route is
producer_brain._build_serum_preset_plan() -> serum-mcp -> Serum 2.0.21's own
UI -> readback (see producer_brain.py's module docstring). This module only
decides WHICH route is admission-ready; it never executes anything.

This module GRANTS NO AUTHORITY. It is a pure advisory lookup over
EXISTING evidence stores. The only things that actually authorize
execution remain, unchanged:

    - serum2.producer.contract_registry.ContractRegistry
      (loads ONLY 4.Q-fresh CAUSAL_VERIFIED contracts; DawDreamer route)
    - serum2.compiler.mcp_intent.MCP_HOST_MAP
      (127-parameter MCP discovery; Ableton MCP route)
    - serum2.knowledge.step_6_6_capability_resolution.CapabilityResolver
      / serum2.evidence.admission.admit()
      (the actual admission gate — still runs regardless of what this
      module reports)

Evidence tiers are kept EXPLICIT and never collapsed, per CLAUDE.md's
"do not launder historical evidence into current-runtime verification":

    FRESH_4Q_VERIFIED   - passed the current authority-hardened
                          re-qualification (step4_q4_*). Loadable by
                          ContractRegistry TODAY. Admission-ready.
    HISTORICAL_VERIFIED - CAUSAL_VERIFIED under the OLD (pre-4.Q)
                          qualification campaign. Real evidence, but
                          NOT currently loaded by ContractRegistry and
                          NOT re-verified under the current authority
                          substrate. Route CANDIDATE only -- requires
                          re-qualification (see next-action from the
                          4.Q audit) before it can actually be admitted.
    MCP_QUALIFIED       - proven writable via the 127-parameter MCP
                          discovery experiment (16.5.59 / "ALL 127").
                          Independent evidence chain from DawDreamer;
                          admission-ready via MCP_HOST_MAP today.
    UNQUALIFIED         - no evidence in any store.

Reuses, does not duplicate:
    - serum2.compiler.targets.SEMANTIC_TARGETS   (name -> capability_key)
    - serum2.compiler.mcp_intent.MCP_HOST_MAP    (MCP admission gate)
    - serum2.producer.contract_registry.ContractRegistry (DawDreamer gate)
    - experiments/_capability_contracts.pkl       (historical 37-contract
      inventory, read-only, for CANDIDATE evidence only)
"""
import pickle
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.compiler.mcp_intent import MCP_HOST_MAP
from serum2.producer.contract_registry import ContractRegistry


class ExecutionRoute(Enum):
    DAWDREAMER_SERUM = "dawdreamer_serum"
    ABLETON_MCP = "ableton_mcp"
    REFUSE = "refuse"


class EvidenceTier(Enum):
    FRESH_4Q_VERIFIED = "fresh_4q_verified"
    HISTORICAL_VERIFIED = "historical_verified"
    MCP_QUALIFIED = "mcp_qualified"
    UNQUALIFIED = "unqualified"


_HISTORICAL_STORE_PATH = (
    Path(__file__).parent.parent.parent / "experiments" / "_capability_contracts.pkl"
)


def _load_historical_status() -> Dict[str, str]:
    """Read-only: capability_key -> status, from the OLD 37-contract store.

    Never mutated, never used to authorize -- CANDIDATE evidence only.
    """
    if not _HISTORICAL_STORE_PATH.exists():
        return {}
    try:
        with open(_HISTORICAL_STORE_PATH, "rb") as f:
            store = pickle.load(f)
        out = {}
        for contract in store.values():
            # Keep the strongest status seen if a target appears more than once.
            prev = out.get(contract.target)
            if prev != "CAUSAL_VERIFIED":
                out[contract.target] = contract.status
        return out
    except Exception:
        return {}


@dataclass
class RouteDecision:
    semantic_target_name: str
    """e.g. 'OSC1.Volume' -- from serum2.compiler.targets.SEMANTIC_TARGETS."""

    capability_key: Optional[str] = None
    """e.g. 'oscillator_field_OSC-VOLUME'. None if name is unknown vocabulary."""

    dawdreamer_evidence: EvidenceTier = EvidenceTier.UNQUALIFIED
    ableton_mcp_evidence: EvidenceTier = EvidenceTier.UNQUALIFIED

    dawdreamer_admission_ready: bool = False
    """True iff ContractRegistry can load this contract RIGHT NOW."""

    ableton_mcp_admission_ready: bool = False
    """True iff MCP_HOST_MAP contains this target name RIGHT NOW."""

    route: ExecutionRoute = ExecutionRoute.REFUSE
    rationale: str = ""

    limitations: List[str] = field(default_factory=list)
    """Non-authoritative notes, e.g. 'historical evidence only, needs re-qualification'."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "semantic_target_name": self.semantic_target_name,
            "capability_key": self.capability_key,
            "dawdreamer_evidence": self.dawdreamer_evidence.value,
            "ableton_mcp_evidence": self.ableton_mcp_evidence.value,
            "dawdreamer_admission_ready": self.dawdreamer_admission_ready,
            "ableton_mcp_admission_ready": self.ableton_mcp_admission_ready,
            "route": self.route.value,
            "rationale": self.rationale,
            "limitations": list(self.limitations),
        }


class RouteSelector:
    """Consults existing evidence stores. Grants no authority.

    Actual execution must still pass through:
      - CapabilityResolver.resolve() + admission.admit()  (DawDreamer route)
      - mcp_intent.parse_intent()/compile_intent() against MCP_HOST_MAP (MCP route)
    This class only decides WHICH of those paths to attempt, and why.
    """

    def __init__(self):
        self._historical_status = _load_historical_status()
        self._fresh_registry = ContractRegistry()

    def select_route(self, semantic_target_name: str) -> RouteDecision:
        decision = RouteDecision(semantic_target_name=semantic_target_name)

        ref = SEMANTIC_TARGETS.get(semantic_target_name)
        if ref is None:
            decision.route = ExecutionRoute.REFUSE
            decision.rationale = (
                "UNKNOWN_SEMANTIC_TARGET: '%s' is not in SEMANTIC_TARGETS. "
                "No route can be selected for an undefined vocabulary term."
                % semantic_target_name
            )
            return decision

        capability_key = ref.capability_key
        decision.capability_key = capability_key

        # ---- DawDreamer/Serum evidence ----
        if capability_key in self._fresh_registry.contracts:
            decision.dawdreamer_evidence = EvidenceTier.FRESH_4Q_VERIFIED
            decision.dawdreamer_admission_ready = True
        elif self._historical_status.get(capability_key) == "CAUSAL_VERIFIED":
            decision.dawdreamer_evidence = EvidenceTier.HISTORICAL_VERIFIED
            decision.dawdreamer_admission_ready = False
            decision.limitations.append(
                "DawDreamer route has HISTORICAL_VERIFIED evidence only "
                "(pre-4.Q qualification). Not currently loaded by "
                "ContractRegistry; requires re-qualification under the "
                "current authority substrate before it can be admitted."
            )
        else:
            decision.dawdreamer_evidence = EvidenceTier.UNQUALIFIED

        # ---- Ableton MCP evidence ----
        if semantic_target_name in MCP_HOST_MAP:
            decision.ableton_mcp_evidence = EvidenceTier.MCP_QUALIFIED
            decision.ableton_mcp_admission_ready = True
        else:
            decision.ableton_mcp_evidence = EvidenceTier.UNQUALIFIED

        # ---- Route decision: prefer what is ADMISSION-READY today ----
        dd_ready = decision.dawdreamer_admission_ready
        mcp_ready = decision.ableton_mcp_admission_ready

        if dd_ready and mcp_ready:
            decision.route = ExecutionRoute.DAWDREAMER_SERUM
            decision.limitations.append(
                "Ableton MCP is also admission-ready (%s) for this target, "
                "but DawDreamer/Serum is the real-execution authority and "
                "takes priority." % decision.ableton_mcp_evidence.value
            )
            decision.rationale = (
                "Both routes are admission-ready with real evidence: "
                "DawDreamer (%s) and Ableton MCP (%s). DawDreamer/Serum is "
                "the real Serum-mutation authority and takes priority."
                % (decision.dawdreamer_evidence.value, decision.ableton_mcp_evidence.value)
            )
        elif dd_ready:
            decision.route = ExecutionRoute.DAWDREAMER_SERUM
            decision.rationale = (
                "Only DawDreamer is admission-ready (%s)."
                % decision.dawdreamer_evidence.value
            )
        elif mcp_ready:
            decision.route = ExecutionRoute.ABLETON_MCP
            decision.rationale = (
                "Only Ableton MCP is admission-ready (%s)."
                % decision.ableton_mcp_evidence.value
            )
        elif decision.dawdreamer_evidence == EvidenceTier.HISTORICAL_VERIFIED:
            decision.route = ExecutionRoute.REFUSE
            decision.rationale = (
                "Historical DawDreamer evidence exists (%s) but is not "
                "currently admission-ready. No MCP evidence. REFUSE pending "
                "re-qualification -- this is a NEEDS_DISCOVERY candidate, "
                "not an unsupported concept."
                % capability_key
            )
        else:
            decision.route = ExecutionRoute.REFUSE
            decision.rationale = (
                "No admission-ready evidence on either route for '%s' "
                "(capability_key=%s). REFUSE." % (semantic_target_name, capability_key)
            )

        return decision

    def select_routes(self, semantic_target_names: List[str]) -> Dict[str, RouteDecision]:
        return {name: self.select_route(name) for name in semantic_target_names}


def select_route(semantic_target_name: str) -> RouteDecision:
    """Top-level convenience function."""
    return RouteSelector().select_route(semantic_target_name)
