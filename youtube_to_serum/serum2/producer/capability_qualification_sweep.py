"""Global Capability Qualification Sweep.

Iterate all Atlas targets, classify their current state, identify which can be
STRUCTURAL_ONLY vs which require CAUSAL_VERIFIED, determine required experiments.

Preserves frozen rule: every contract from its own evidence, no shortcuts.
Scales capability coverage discovery and contract generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from serum2.reference.serum_atlas import normalize_control
from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.compiler.mcp_intent import MCP_HOST_MAP
from serum2.producer.target_resolution import TargetResolver, REFUSED_NO_CAPABILITY
from serum2.evidence.capability_contract import CapabilityContract
from serum2.producer.contract_registry import ContractRegistry

# Avoid frozen step 6 imports; get UNIVERSAL_TO_SEMANTIC from the producer directly
def _get_universal_to_semantic():
    try:
        from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC
        return UNIVERSAL_TO_SEMANTIC
    except ImportError:
        # Fallback: return empty dict, sweep will still work
        return {}


class CapabilityState(Enum):
    """Classification of a target's current capability coverage."""
    ALREADY_CAUSAL_VERIFIED = "already_causal_verified"           # Contract exists, CAUSAL_VERIFIED
    ALREADY_STRUCTURAL_ONLY = "already_structural_only"           # Contract exists, STRUCTURAL_ONLY
    EVIDENCE_SUPPORTS_STRUCTURAL = "evidence_supports_structural" # No contract, but structural proof exists
    EVIDENCE_SUPPORTS_CAUSAL = "evidence_supports_causal"         # No contract, but causal proof exists
    BINDING_MISSING = "binding_missing"                           # No VST3/body binding found
    EVIDENCE_MISSING = "evidence_missing"                         # Binding exists, no evidence yet
    REFERENCE_MISSING = "reference_missing"                       # Atlas has no entry for this target


@dataclass
class QualificationStatus:
    """Current state of one target's capability coverage."""
    atlas_target: str                    # e.g., "env2.decay"
    semantic_target: Optional[str]       # from SEMANTIC_TARGETS, if registered
    capability_key: Optional[str]        # from the mapping
    state: CapabilityState

    # Evidence found
    existing_contract: Optional[CapabilityContract] = None
    vst3_binding: Optional[str] = None   # e.g., "Env 2 Decay"
    body_binding: Optional[str] = None   # e.g., "Envelope1.plainParams.kParamDecay"

    # What's needed
    requires_causal_proof: bool = False
    experiment_id: Optional[str] = None  # if experiment required, its ID
    rationale: str = ""


class CapabilityQualificationSweep:
    """Scan all Atlas targets and classify their qualification state."""

    def __init__(self):
        self._atlas = normalize_control
        self._targets = SEMANTIC_TARGETS
        self._mcp_map = MCP_HOST_MAP
        self._contracts = ContractRegistry()
        self._resolver = TargetResolver(
            self._contracts,
            self._targets,
            self._mcp_map,
            _get_universal_to_semantic(),
            {},  # mcp_bridge (empty for now)
            None,  # mapping_factory (not needed for this scan)
        )

    def sweep(self, max_results: Optional[int] = None) -> List[QualificationStatus]:
        """Scan all SEMANTIC_TARGETS and classify their state.

        Returns list of QualificationStatus, sorted by qualification priority
        (already verified first, then structural, then evidence_missing, then binding_missing).
        """
        results = []

        # Scan all registered semantic targets
        for semantic_name in sorted(self._targets.keys()):
            target_ref = self._targets[semantic_name]
            capability_key = target_ref.capability_key if target_ref else None

            # Try to resolve the atlas canonical identity (simple check, no factory)
            try:
                atlas_res = self._atlas(semantic_name)
                if atlas_res.status not in ("EXACT", "ALIAS"):
                    canonical_id = semantic_name
                else:
                    canonical_id = atlas_res.canonical_id
            except Exception as e:
                results.append(QualificationStatus(
                    atlas_target=semantic_name,
                    semantic_target=semantic_name,
                    capability_key=capability_key,
                    state=CapabilityState.REFERENCE_MISSING,
                    rationale=f"Atlas lookup failed: {e}",
                ))
                continue

            # Check existing contract
            contract = self._contracts.contracts.get(capability_key) if capability_key else None

            if contract is not None:
                state = (CapabilityState.ALREADY_CAUSAL_VERIFIED
                        if contract.status == "CAUSAL_VERIFIED"
                        else CapabilityState.ALREADY_STRUCTURAL_ONLY)
                results.append(QualificationStatus(
                    atlas_target=canonical_id,
                    semantic_target=semantic_name,
                    capability_key=capability_key,
                    state=state,
                    existing_contract=contract,
                    vst3_binding=contract.execution_binding.host_parameter_name
                        if contract.execution_binding else None,
                    body_binding=contract.execution_binding.body_path
                        if contract.execution_binding else None,
                    rationale=f"Contract exists: status={contract.status}",
                ))
                continue

            # No contract yet. Check for binding.
            vst3_name = self._contracts._host_param_mapping.get(capability_key) if capability_key else None
            body_path = self._contracts._body_state_mapping.get(capability_key) if capability_key else None

            if vst3_name is None and body_path is None:
                results.append(QualificationStatus(
                    atlas_target=canonical_id,
                    semantic_target=semantic_name,
                    capability_key=capability_key,
                    state=CapabilityState.BINDING_MISSING,
                    rationale=f"No VST3 or body binding found for {capability_key}",
                ))
                continue

            # Binding exists but no contract. Check for evidence.
            # (Evidence check would happen here — for now, mark as EVIDENCE_MISSING)
            results.append(QualificationStatus(
                atlas_target=canonical_id,
                semantic_target=semantic_name,
                capability_key=capability_key,
                state=CapabilityState.EVIDENCE_MISSING,
                vst3_binding=vst3_name,
                body_binding=body_path,
                rationale=f"Binding exists ({vst3_name or body_path}), no contract yet",
            ))

        # Sort by priority (verified first, then by state)
        priority = {
            CapabilityState.ALREADY_CAUSAL_VERIFIED: 0,
            CapabilityState.ALREADY_STRUCTURAL_ONLY: 1,
            CapabilityState.EVIDENCE_SUPPORTS_CAUSAL: 2,
            CapabilityState.EVIDENCE_SUPPORTS_STRUCTURAL: 3,
            CapabilityState.EVIDENCE_MISSING: 4,
            CapabilityState.BINDING_MISSING: 5,
            CapabilityState.REFERENCE_MISSING: 6,
        }
        results.sort(key=lambda r: priority.get(r.state, 99))

        return results[:max_results] if max_results else results


def main():
    sweep = CapabilityQualificationSweep()
    results = sweep.sweep()

    # Print summary
    by_state = {}
    for r in results:
        state = r.state.value
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(r)

    print("=== GLOBAL CAPABILITY QUALIFICATION SWEEP ===\n")
    print(f"Total targets scanned: {len(results)}\n")

    for state in [
        CapabilityState.ALREADY_CAUSAL_VERIFIED,
        CapabilityState.ALREADY_STRUCTURAL_ONLY,
        CapabilityState.EVIDENCE_MISSING,
        CapabilityState.BINDING_MISSING,
        CapabilityState.REFERENCE_MISSING,
    ]:
        items = by_state.get(state.value, [])
        print(f"{state.value.upper():40s} ({len(items)} targets)")
        for r in items[:3]:  # Show first 3
            print(f"  {r.atlas_target:30s}  capability_key={r.capability_key}")
        if len(items) > 3:
            print(f"  ... and {len(items) - 3} more")
        print()

    # Focus on EVIDENCE_MISSING (these are candidates for qualification)
    print("\n=== PRIORITY: EVIDENCE_MISSING (can add contracts) ===\n")
    for r in by_state.get(CapabilityState.EVIDENCE_MISSING.value, [])[:10]:
        print(f"{r.atlas_target:25s}  {r.semantic_target:30s}")
        print(f"  capability_key: {r.capability_key}")
        print(f"  vst3_binding:  {r.vst3_binding}")
        print(f"  body_binding:  {r.body_binding}")
        print()


if __name__ == "__main__":
    main()
