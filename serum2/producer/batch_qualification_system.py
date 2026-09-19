"""Phase 3: Batch Qualification System.

Three generic, reusable pieces:

1. BindingCandidate — common structure for any verified binding
2. StructuralQualificationRunner — generic load/mutate/readback/persist cycle
3. QualificationPlanner — auto-classify 255 targets into action buckets

Batch by operation family (TOGGLE, NUMERIC, ENUM, BODY_STATE, STRUCTURED).
No target-specific code. Reusable for 1 or 234 targets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.producer.route_classifier import ExecutionRoute, RouteClassifier


class OperationFamily(Enum):
    """Batch grouping by operation type."""
    TOGGLE = "toggle"              # OSC enable, filter enable, mute
    NUMERIC = "numeric"            # Attack, decay, cutoff, rate
    ENUM = "enum"                  # Filter type, oscillator mode
    BODY_STATE = "body_state"      # Direct preset-body field
    STRUCTURED = "structured"      # Matrix routing, topology
    UNKNOWN = "unknown"


class QualificationStatus(Enum):
    """Where each target is in the qualification pipeline."""
    READY_FOR_STRUCTURAL = "ready_for_structural"      # Verified binding, can qualify
    NEEDS_BINDING = "needs_binding"                    # No binding discovered yet
    NEEDS_CAUSAL = "needs_causal"                      # Structural done, needs audio proof
    ALREADY_VERIFIED = "already_verified"              # Contract exists
    BLOCKED = "blocked"                                # Conflict or ambiguity


@dataclass
class BindingCandidate:
    """Common structure for any verified binding."""

    # Identity
    atlas_target: str                       # e.g., "env2.decay"
    semantic_target: Optional[str]          # from SEMANTIC_TARGETS
    capability_key: Optional[str]           # the semantic target's key

    # Binding
    route_type: ExecutionRoute
    binding: str                            # e.g., "B Enable" or "Envelope1.plainParams.kParamDecay"
    binding_source: str                     # "vst3_mapping", "body_state_mapping", "discovered"

    # Execution metadata
    operation_family: OperationFamily       # TOGGLE, NUMERIC, ENUM, etc.
    operation_type: str                     # e.g., "mutate_numeric_value", "mutate_enum_value"

    # Quality
    confidence: float                       # 0.0-1.0 (1.0 = verified, <1.0 = candidate)
    rationale: str                          # why we believe this binding is correct

    # Evidence
    existing_contract: Optional[str] = None # if contract already exists, its status

    def is_verified(self) -> bool:
        """Binding is verified for qualification (confidence >= threshold)."""
        return self.confidence >= 0.95


@dataclass
class QualificationPlan:
    """Automatic plan for all 255 targets."""

    # Bucketed targets
    ready_for_structural: List[BindingCandidate] = field(default_factory=list)
    needs_binding: List[str] = field(default_factory=list)  # atlas_target names
    needs_causal: List[str] = field(default_factory=list)   # atlas_target names
    already_verified: List[str] = field(default_factory=list)
    blocked: List[Tuple[str, str]] = field(default_factory=list)  # (target, reason)

    # Grouped by operation family for batching
    by_operation_family: Dict[OperationFamily, List[BindingCandidate]] = field(default_factory=dict)


class QualificationPlanner:
    """Auto-classify 255 targets into action buckets."""

    def __init__(self):
        self._classifier = RouteClassifier()
        self._targets = SEMANTIC_TARGETS

    def _infer_operation_family(self, capability_key: Optional[str]) -> OperationFamily:
        """Infer operation family from capability key."""
        if not capability_key:
            return OperationFamily.UNKNOWN

        key_lower = capability_key.lower()

        if any(word in key_lower for word in ["enable", "mute", "toggle"]):
            return OperationFamily.TOGGLE
        if any(word in key_lower for word in ["attack", "decay", "sustain", "release", "cutoff", "resonance", "rate"]):
            return OperationFamily.NUMERIC
        if any(word in key_lower for word in ["type", "mode"]):
            return OperationFamily.ENUM
        if "field" in key_lower or key_lower.startswith("envelope") or key_lower.startswith("oscillator"):
            return OperationFamily.BODY_STATE
        if "matrix" in key_lower or "routing" in key_lower:
            return OperationFamily.STRUCTURED

        return OperationFamily.UNKNOWN

    def plan(self) -> QualificationPlan:
        """Generate qualification plan for all 255 targets."""
        plan = QualificationPlan()

        for semantic_target in sorted(self._targets.keys()):
            route_class = self._classifier.classify(semantic_target)
            target_ref = self._targets.get(semantic_target)
            capability_key = target_ref.capability_key if target_ref else None
            op_family = self._infer_operation_family(capability_key)

            # Already has contract
            if route_class.contract_exists:
                plan.already_verified.append(semantic_target)
                continue

            # Has verified binding (high confidence)
            if route_class.route != ExecutionRoute.UNBOUND and route_class.binding:
                candidate = BindingCandidate(
                    atlas_target=route_class.atlas_target,
                    semantic_target=semantic_target,
                    capability_key=capability_key,
                    route_type=route_class.route,
                    binding=route_class.binding,
                    binding_source=route_class.binding_source or "unknown",
                    operation_family=op_family,
                    operation_type="unknown",  # TODO: infer from contract or schema
                    confidence=0.95,
                    rationale=f"Binding found in {route_class.binding_source}",
                    existing_contract=route_class.contract_status,
                )
                plan.ready_for_structural.append(candidate)
                plan.by_operation_family.setdefault(op_family, []).append(candidate)
            else:
                # Unbound, needs discovery
                plan.needs_binding.append(semantic_target)

        return plan


class StructuralQualificationRunner:
    """Generic runner for any target with a verified binding.

    Cycle: load → read_before → mutate → read_after → persist/reload → read_after_reload → emit evidence

    This runner processes any BindingCandidate; no target-specific code.
    """

    def __init__(self, serum_mcp=None):
        self._serum_mcp = serum_mcp

    def qualify(self, candidate: BindingCandidate, preset_path: Optional[str] = None) -> Optional[Dict]:
        """Run structural qualification on one candidate.

        Args:
            candidate: BindingCandidate with verified binding
            preset_path: Path to reference preset; if None, generates minimal seed

        Returns:
            EvidenceRecord (baseline, treatment, after_reload) suitable for ClaimGroup/Contract.
        """
        if not candidate.is_verified():
            print(f"[StructuralQualificationRunner] Skipping {candidate.atlas_target}: confidence {candidate.confidence} < 0.95")
            return None

        print(f"[StructuralQualificationRunner] Qualifying: {candidate.atlas_target}")
        print(f"  Route: {candidate.route_type.value}")
        print(f"  Binding: {candidate.binding}")
        print(f"  Operation family: {candidate.operation_family.value}")

        # Stub implementation:
        # 1. Load preset (or minimal seed)
        # 2. Read parameter (VST3 or body-state)
        # 3. Mutate based on operation_family
        # 4. Persist and reload
        # 5. Verify read-after-reload matches persisted value
        # 6. Emit EvidenceRecord(baseline={...}, treatment={...}, after_reload={...})

        return None


def main():
    planner = QualificationPlanner()
    plan = planner.plan()

    print("=== QUALIFICATION PLAN: ALL 255 ATLAS TARGETS ===\n")
    print(f"Already verified (contracts exist):  {len(plan.already_verified):3d}")
    print(f"Ready for structural:                {len(plan.ready_for_structural):3d}")
    print(f"Needs binding discovery:             {len(plan.needs_binding):3d}")
    print(f"---")
    print(f"TOTAL:                               {len(plan.already_verified) + len(plan.ready_for_structural) + len(plan.needs_binding):3d}")

    print("\n=== READY FOR STRUCTURAL (by operation family) ===\n")
    for op_family in sorted(plan.by_operation_family.keys()):
        items = plan.by_operation_family[op_family]
        print(f"{op_family.value.upper():30s} ({len(items):3d} targets)")
        for item in items[:2]:
            print(f"  {item.atlas_target:30s} binding={item.binding}")
        if len(items) > 2:
            print(f"  ... and {len(items) - 2} more")
        print()

    print("\n=== FROZEN TUTORIAL TARGETS IN PLAN ===\n")
    frozen = ["env2.decay", "env2.sustain", "oscb.enabled", "lfo1.rate", "filter1.enabled"]
    for target in frozen:
        if target in plan.needs_binding:
            print(f"{target:25s} → NEEDS_BINDING (discovery queue)")
        elif any(c.atlas_target == target for c in plan.ready_for_structural):
            c = next(c for c in plan.ready_for_structural if c.atlas_target == target)
            print(f"{target:25s} → READY_FOR_STRUCTURAL (binding: {c.binding})")
        elif target in plan.already_verified:
            print(f"{target:25s} → ALREADY_VERIFIED (contract exists)")


if __name__ == "__main__":
    main()
