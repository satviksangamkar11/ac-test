"""Phase 1: Route Classification.

Classify all 255 Atlas targets by their execution route:
  - VST3_HOST_PARAMETER: exposed via Serum's VST3 interface
  - SERUM_BODY_STATE: directly in the preset body schema
  - STRUCTURED_OPERATION: handled by OperationRegistry
  - UNBOUND: not yet mapped to any execution surface
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from serum2.reference.serum_atlas import normalize_control
from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.compiler.mcp_intent import MCP_HOST_MAP
from serum2.producer.contract_registry import ContractRegistry


class ExecutionRoute(Enum):
    """How a target is executed in Serum 2.0.21."""
    VST3_HOST_PARAMETER = "vst3_host_parameter"      # Via semantic_vst3_mapping.json
    SERUM_BODY_STATE = "serum_body_state"            # Via body_state_mapping.json
    STRUCTURED_OPERATION = "structured_operation"    # Via OperationRegistry
    UNBOUND = "unbound"                              # No route found yet


@dataclass
class RouteClassification:
    """Classification of one target's execution route."""
    atlas_target: str                           # e.g., "env2.decay"
    semantic_target: Optional[str]              # from SEMANTIC_TARGETS
    capability_key: Optional[str]               # the semantic target's capability_key

    route: ExecutionRoute                       # which execution surface
    binding: Optional[str] = None               # e.g., "Env 2 Decay" or body path
    binding_source: Optional[str] = None        # "vst3_mapping" or "body_state_mapping"

    contract_exists: bool = False
    contract_status: Optional[str] = None

    rationale: str = ""


class RouteClassifier:
    """Classify all targets by execution route."""

    def __init__(self):
        self._targets = SEMANTIC_TARGETS
        self._mcp_map = MCP_HOST_MAP
        self._contracts = ContractRegistry()

        # Load VST3 mapping
        self._vst3_map = self._load_vst3_mapping()

        # Load body-state mapping
        self._body_map = self._load_body_state_mapping()

    def _load_vst3_mapping(self) -> Dict[str, str]:
        """Load semantic_vst3_mapping.json."""
        path = Path(__file__).parent.parent / "qualification" / "semantic_vst3_mapping.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                return data.get("mappings", {})
            except Exception as e:
                print(f"[RouteClassifier] Warning: could not load VST3 mapping: {e}")
        return {}

    def _load_body_state_mapping(self) -> Dict[str, Dict]:
        """Load body_state_mapping.json."""
        path = Path(__file__).parent.parent / "qualification" / "body_state_mapping.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                return data.get("bindings", {})
            except Exception as e:
                print(f"[RouteClassifier] Warning: could not load body-state mapping: {e}")
        return {}

    def classify(self, semantic_target: str) -> RouteClassification:
        """Classify one target's execution route."""
        target_ref = self._targets.get(semantic_target)
        capability_key = target_ref.capability_key if target_ref else None

        # Try to resolve atlas canonical identity
        try:
            atlas_res = normalize_control(semantic_target)
            if atlas_res.status in ("EXACT", "ALIAS"):
                canonical_id = atlas_res.canonical_id
            else:
                canonical_id = semantic_target
        except Exception:
            canonical_id = semantic_target

        # Check if contract already exists
        contract = self._contracts.contracts.get(capability_key) if capability_key else None

        # Route 1: VST3 Host Parameter
        if capability_key and capability_key in self._vst3_map:
            vst3_name = self._vst3_map[capability_key]
            return RouteClassification(
                atlas_target=canonical_id,
                semantic_target=semantic_target,
                capability_key=capability_key,
                route=ExecutionRoute.VST3_HOST_PARAMETER,
                binding=vst3_name,
                binding_source="vst3_mapping",
                contract_exists=contract is not None,
                contract_status=contract.status if contract else None,
                rationale=f"VST3 parameter '{vst3_name}' found in semantic_vst3_mapping.json",
            )

        # Route 2: Serum Body State
        if capability_key and capability_key in self._body_map:
            body_path = self._body_map[capability_key].get("body_path")
            return RouteClassification(
                atlas_target=canonical_id,
                semantic_target=semantic_target,
                capability_key=capability_key,
                route=ExecutionRoute.SERUM_BODY_STATE,
                binding=body_path,
                binding_source="body_state_mapping",
                contract_exists=contract is not None,
                contract_status=contract.status if contract else None,
                rationale=f"Body state path '{body_path}' found in body_state_mapping.json",
            )

        # Route 3: Structured Operation (check OperationRegistry)
        # TODO: integrate OperationRegistry.is_operation_qualified(capability_key)
        # For now, structured operations are deferred to Phase 2.

        # Route 4: Unbound
        return RouteClassification(
            atlas_target=canonical_id,
            semantic_target=semantic_target,
            capability_key=capability_key,
            route=ExecutionRoute.UNBOUND,
            contract_exists=contract is not None,
            contract_status=contract.status if contract else None,
            rationale="No binding found in vst3_mapping, body_state_mapping, or OperationRegistry",
        )

    def classify_all(self) -> Dict[ExecutionRoute, List[RouteClassification]]:
        """Classify all semantic targets."""
        results_by_route = {
            ExecutionRoute.VST3_HOST_PARAMETER: [],
            ExecutionRoute.SERUM_BODY_STATE: [],
            ExecutionRoute.STRUCTURED_OPERATION: [],
            ExecutionRoute.UNBOUND: [],
        }

        for semantic_target in sorted(self._targets.keys()):
            classification = self.classify(semantic_target)
            results_by_route[classification.route].append(classification)

        return results_by_route


def main():
    classifier = RouteClassifier()
    results = classifier.classify_all()

    print("=== ROUTE CLASSIFICATION: ALL 255 ATLAS TARGETS ===\n")

    for route in [
        ExecutionRoute.VST3_HOST_PARAMETER,
        ExecutionRoute.SERUM_BODY_STATE,
        ExecutionRoute.STRUCTURED_OPERATION,
        ExecutionRoute.UNBOUND,
    ]:
        items = results[route]
        print(f"{route.value.upper():40s} ({len(items):3d})")
        for item in items[:5]:
            status_str = f" contract={item.contract_status}" if item.contract_exists else " (no contract)"
            binding_str = f" binding={item.binding}" if item.binding else ""
            print(f"  {item.atlas_target:30s}{binding_str}{status_str}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
        print()

    # Summary
    print("\n=== SUMMARY ===\n")
    print(f"VST3 bound:            {len(results[ExecutionRoute.VST3_HOST_PARAMETER]):3d}")
    print(f"Body-state bound:      {len(results[ExecutionRoute.SERUM_BODY_STATE]):3d}")
    print(f"Structured ops:        {len(results[ExecutionRoute.STRUCTURED_OPERATION]):3d}")
    print(f"Unbound (need mapping):{len(results[ExecutionRoute.UNBOUND]):3d}")
    print(f"---")
    print(f"TOTAL:                 {sum(len(items) for items in results.values()):3d}")

    # Show which unbound targets are highest-priority (from frozen tutorial)
    print("\n=== FROZEN TUTORIAL TARGETS (in route classification) ===\n")
    frozen_targets = ["env2.decay", "env2.sustain", "oscb.enabled", "lfo1.rate", "filter1.enabled"]
    for target in frozen_targets:
        c = classifier.classify(target)
        print(f"{target:25s} → {c.route.value:30s} binding={c.binding or '(none)'}")


if __name__ == "__main__":
    main()
