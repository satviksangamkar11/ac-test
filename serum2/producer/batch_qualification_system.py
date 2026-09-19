"""Generic Phase-3 capability qualification infrastructure.

The planner joins existing Atlas/Brain/contract/binding data. It contains no
target->binding dictionary. The runner is backend-agnostic: the orchestrator
supplies the real execution/evidence adapter (serum-mcp/UI/etc.).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Tuple

from serum2.evidence.capability_contract import (
    BLOCKED_CONTRADICTED,
    CAUSAL_VERIFIED,
    NEGATIVE_EVIDENCE,
    STRUCTURAL_ONLY,
    UNSUPPORTED,
    ExecutionBinding,
)

ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION_DIR = ROOT / "serum2" / "qualification"


class RouteType(str, Enum):
    VST3_HOST_PARAMETER = "VST3_HOST_PARAMETER"
    SERUM_BODY_STATE = "SERUM_BODY_STATE"
    # PresetSpec-addressable field executed via serum-mcp's edit_preset/
    # describe_preset (file-based; no live plugin/DAW involved). Distinct
    # from VST3_HOST_PARAMETER, which is plugin-surface evidence only --
    # serum-mcp cannot address a control by its VST3 parameter name.
    SERUM_PRESET_STRUCTURAL_BINDING = "SERUM_PRESET_STRUCTURAL_BINDING"
    STRUCTURED_OPERATION = "STRUCTURED_OPERATION"
    UNBOUND = "UNBOUND"


class OperationFamily(str, Enum):
    TOGGLE = "TOGGLE"
    NUMERIC = "NUMERIC"
    ENUM = "ENUM"
    BODY_STATE = "BODY_STATE"
    STRUCTURED = "STRUCTURED"


class QualificationBucket(str, Enum):
    ALREADY_VERIFIED = "ALREADY_VERIFIED"
    READY_FOR_STRUCTURAL = "READY_FOR_STRUCTURAL"
    NEEDS_BINDING = "NEEDS_BINDING"
    NEEDS_CAUSAL = "NEEDS_CAUSAL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class BindingCandidate:
    """A binding from an authoritative source, or an explicitly unverified candidate."""

    target: str
    capability_key: Optional[str]
    route_type: RouteType
    binding: Optional[ExecutionBinding]
    operation_family: OperationFamily
    provenance: str
    confidence: float = 0.0
    verified: bool = False
    evidence_ref: Optional[str] = None
    reason: str = ""

    def is_verified(self) -> bool:
        if not self.verified or self.binding is None or not self.capability_key:
            return False
        if self.route_type == RouteType.VST3_HOST_PARAMETER:
            return bool(self.binding.host_parameter_name)
        if self.route_type == RouteType.SERUM_BODY_STATE:
            return bool(self.binding.body_path or self.binding.resolver_operation_id)
        if self.route_type == RouteType.STRUCTURED_OPERATION:
            return bool(self.binding.resolver_operation_id)
        return False


@dataclass(frozen=True)
class TargetQualification:
    target: str
    capability_key: Optional[str]
    control_type: Optional[str]
    operation_family: OperationFamily
    candidate: BindingCandidate
    bucket: QualificationBucket
    contract_status: Optional[str]
    brain_registered: bool
    reason: str = ""


@dataclass
class QualificationPlan:
    all_targets: List[TargetQualification] = field(default_factory=list)
    already_verified: List[TargetQualification] = field(default_factory=list)
    ready_for_structural: List[TargetQualification] = field(default_factory=list)
    needs_binding: List[TargetQualification] = field(default_factory=list)
    needs_causal: List[TargetQualification] = field(default_factory=list)
    blocked: List[TargetQualification] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.all_targets)

    def counts(self) -> Dict[str, int]:
        return {
            "ALREADY_VERIFIED": len(self.already_verified),
            "READY_FOR_STRUCTURAL": len(self.ready_for_structural),
            "NEEDS_BINDING": len(self.needs_binding),
            "NEEDS_CAUSAL": len(self.needs_causal),
            "BLOCKED": len(self.blocked),
            "TOTAL": self.total,
        }


@dataclass(frozen=True)
class MutationSpec:
    target: str
    value: Any
    operation: str
    note: str = ""


@dataclass(frozen=True)
class StructuralQualificationResult:
    target: str
    capability_key: Optional[str]
    status: str
    refusal_code: Optional[str]
    operation_family: OperationFamily
    route_type: RouteType
    binding: Optional[Dict[str, Any]]
    baseline: Any = None
    after_mutation: Any = None
    persisted: Any = None
    after_reload: Any = None
    state_changed: bool = False
    persistence_verified: bool = False
    trace: Tuple[str, ...] = ()
    backend_evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "capability_key": self.capability_key,
            "status": self.status,
            "refusal_code": self.refusal_code,
            "operation_family": self.operation_family.value,
            "route_type": self.route_type.value,
            "binding": self.binding,
            "baseline": self.baseline,
            "after_mutation": self.after_mutation,
            "persisted": self.persisted,
            "after_reload": self.after_reload,
            "state_changed": self.state_changed,
            "persistence_verified": self.persistence_verified,
            "trace": list(self.trace),
            "backend_evidence": dict(self.backend_evidence),
        }


class StructuralQualificationBackend(Protocol):
    def load(self, candidate: BindingCandidate) -> Mapping[str, Any]: ...
    def read(self, candidate: BindingCandidate) -> Any: ...
    def mutate(self, candidate: BindingCandidate, mutation: MutationSpec) -> Mapping[str, Any]: ...
    def persist(self, candidate: BindingCandidate) -> Mapping[str, Any]: ...
    def reload(self, candidate: BindingCandidate) -> Mapping[str, Any]: ...


class StructuralQualificationRunner:
    """Generic load/mutate/read/persist/reload cycle.

    This class deliberately does not call MCP or Serum itself. The injected
    backend must return real observed execution/readback data.
    """

    def __init__(
        self,
        backend: StructuralQualificationBackend,
        *,
        state_equal: Optional[Callable[[Any, Any], bool]] = None,
    ):
        self._backend = backend
        self._state_equal = state_equal or (lambda a, b: a == b)

    def run(self, candidate: BindingCandidate, mutation: MutationSpec) -> StructuralQualificationResult:
        if not candidate.is_verified():
            return StructuralQualificationResult(
                target=candidate.target,
                capability_key=candidate.capability_key,
                status="REFUSED_UNVERIFIED_BINDING",
                refusal_code="REFUSED_UNVERIFIED_BINDING",
                operation_family=candidate.operation_family,
                route_type=candidate.route_type,
                binding=self._binding_dict(candidate.binding),
                trace=("binding candidate rejected before backend execution",),
            )

        if mutation.target != candidate.target:
            return StructuralQualificationResult(
                target=candidate.target,
                capability_key=candidate.capability_key,
                status="REFUSED_MUTATION_TARGET_MISMATCH",
                refusal_code="REFUSED_MUTATION_TARGET_MISMATCH",
                operation_family=candidate.operation_family,
                route_type=candidate.route_type,
                binding=self._binding_dict(candidate.binding),
                trace=("mutation target does not match binding candidate",),
            )

        evidence: Dict[str, Any] = {}
        trace: List[str] = []

        evidence["load"] = dict(self._backend.load(candidate) or {})
        trace.append("LOAD")
        baseline = self._backend.read(candidate)
        evidence["baseline_read"] = baseline
        trace.append("READ_BASELINE")

        evidence["mutation"] = dict(self._backend.mutate(candidate, mutation) or {})
        trace.append("MUTATE")
        after_mutation = self._backend.read(candidate)
        evidence["after_mutation_read"] = after_mutation
        trace.append("READ_AFTER_MUTATION")

        changed = not self._state_equal(baseline, after_mutation)
        if not changed:
            return StructuralQualificationResult(
                target=candidate.target,
                capability_key=candidate.capability_key,
                status="FAILED_NO_STATE_CHANGE",
                refusal_code=None,
                operation_family=candidate.operation_family,
                route_type=candidate.route_type,
                binding=self._binding_dict(candidate.binding),
                baseline=baseline,
                after_mutation=after_mutation,
                state_changed=False,
                trace=tuple(trace + ["STATE_CHANGE_CHECK_FAILED"]),
                backend_evidence=evidence,
            )

        persisted = self._backend.persist(candidate)
        evidence["persist"] = dict(persisted or {})
        trace.append("PERSIST")

        evidence["reload"] = dict(self._backend.reload(candidate) or {})
        trace.append("RELOAD")
        after_reload = self._backend.read(candidate)
        evidence["after_reload_read"] = after_reload
        trace.append("READ_AFTER_RELOAD")

        persistence_verified = self._state_equal(after_mutation, after_reload)
        trace.append(
            "PERSISTENCE_CHECK_%s" % ("PASSED" if persistence_verified else "FAILED")
        )

        return StructuralQualificationResult(
            target=candidate.target,
            capability_key=candidate.capability_key,
            status="STRUCTURAL_VERIFIED" if persistence_verified else "FAILED_PERSISTENCE",
            refusal_code=None,
            operation_family=candidate.operation_family,
            route_type=candidate.route_type,
            binding=self._binding_dict(candidate.binding),
            baseline=baseline,
            after_mutation=after_mutation,
            persisted=persisted,
            after_reload=after_reload,
            state_changed=True,
            persistence_verified=persistence_verified,
            trace=tuple(trace),
            backend_evidence=evidence,
        )

    @staticmethod
    def _binding_dict(binding: Optional[ExecutionBinding]):
        if binding is None:
            return None
        return {
            "mutation_type": binding.mutation_type,
            "body_path": binding.body_path,
            "host_parameter_name": binding.host_parameter_name,
            "meta_path": binding.meta_path,
            "binding_source": binding.binding_source,
            "binding_version": binding.binding_version,
            "resolver_operation_id": binding.resolver_operation_id,
        }


class QualificationPlanner:
    """Classify targets using only existing authoritative data.

    No target->binding mapping lives in this class. It joins:
        Atlas -> Brain vocabulary -> capability key
        -> authoritative binding maps -> existing contract state.

    Targets lacking a Brain concept can remain in NEEDS_BINDING, but their
    reason explicitly says that Brain vocabulary is also missing. Coverage
    axes remain visible and are not silently conflated.
    """

    def __init__(
        self,
        *,
        atlas_controls: Optional[Mapping[str, Any]] = None,
        semantic_targets: Optional[Mapping[str, Any]] = None,
        contract_registry: Any = None,
        host_mapping: Optional[Mapping[str, str]] = None,
        body_mapping: Optional[Mapping[str, Mapping[str, Any]]] = None,
        target_universe: str = "CAPABILITY_TARGETS",
    ):
        self._target_universe = target_universe

        if atlas_controls is None:
            from serum2.reference.serum_atlas import all_control_ids, get_control
            atlas_controls = {cid: get_control(cid) for cid in all_control_ids()}
        self._atlas = dict(atlas_controls)

        if semantic_targets is None:
            from serum2.compiler.targets import SEMANTIC_TARGETS
            semantic_targets = SEMANTIC_TARGETS
        self._semantic_targets = dict(semantic_targets)

        if contract_registry is None:
            from serum2.producer.contract_registry import ContractRegistry
            contract_registry = ContractRegistry()
        self._registry = contract_registry

        self._host_mapping = (
            dict(host_mapping)
            if host_mapping is not None
            else self._load_json("semantic_vst3_mapping.json").get("mappings", {})
        )
        self._body_mapping = (
            dict(body_mapping)
            if body_mapping is not None
            else self._load_json("body_state_mapping.json").get("bindings", {})
        )

        self._brain_index = {
            self._normalize(name): (name, ref)
            for name, ref in self._semantic_targets.items()
        }

    @staticmethod
    def _load_json(filename: str):
        with (QUALIFICATION_DIR / filename).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _normalize(name: str) -> str:
        from serum2.producer.target_names import normalize_target_name
        return normalize_target_name(name)

    @staticmethod
    def _operation_family(control: Any) -> OperationFamily:
        kind = getattr(control, "control_type", None)
        if kind == "toggle":
            return OperationFamily.TOGGLE
        if kind == "continuous":
            return OperationFamily.NUMERIC
        if kind == "enum":
            return OperationFamily.ENUM
        return OperationFamily.STRUCTURED

    def _candidate(
        self,
        target: str,
        control: Any,
        capability_key: Optional[str],
    ) -> BindingCandidate:
        body = self._body_mapping.get(capability_key) if capability_key else None
        host = self._host_mapping.get(capability_key) if capability_key else None

        if body is not None and host is not None:
            return BindingCandidate(
                target=target,
                capability_key=capability_key,
                route_type=RouteType.UNBOUND,
                binding=None,
                operation_family=OperationFamily.STRUCTURED,
                provenance="MULTIPLE_BINDING_SOURCES",
                reason="Multiple authoritative binding sources exist; planner refuses to choose.",
            )

        if body is not None:
            binding = ExecutionBinding(
                mutation_type="BODY_STATE",
                body_path=body.get("body_path"),
                host_parameter_name=None,
                meta_path=body.get("meta_path"),
                binding_source="body_state_mapping.json",
                binding_version=str(body.get("binding_version", "1")),
                resolver_operation_id=body.get("resolver_operation_id"),
            )
            return BindingCandidate(
                target=target,
                capability_key=capability_key,
                route_type=RouteType.SERUM_BODY_STATE,
                binding=binding,
                operation_family=OperationFamily.BODY_STATE,
                provenance="body_state_mapping.json",
                confidence=1.0,
                verified=True,
                reason="Exact authoritative BODY_STATE mapping.",
            )

        if host is not None:
            binding = ExecutionBinding(
                mutation_type="HOST_PARAMETER",
                body_path=None,
                host_parameter_name=str(host),
                meta_path=None,
                binding_source="semantic_vst3_mapping.json",
                binding_version="1",
            )
            return BindingCandidate(
                target=target,
                capability_key=capability_key,
                route_type=RouteType.VST3_HOST_PARAMETER,
                binding=binding,
                operation_family=self._operation_family(control),
                provenance="semantic_vst3_mapping.json",
                confidence=1.0,
                verified=True,
                reason="Exact authoritative VST3 host-parameter mapping.",
            )

        family = self._operation_family(control)
        return BindingCandidate(
            target=target,
            capability_key=capability_key,
            route_type=(
                RouteType.STRUCTURED_OPERATION
                if family == OperationFamily.STRUCTURED
                else RouteType.UNBOUND
            ),
            binding=None,
            operation_family=family,
            provenance="UNBOUND",
            confidence=0.0,
            verified=False,
            reason="No authoritative execution binding is currently registered.",
        )

    def plan(self) -> QualificationPlan:
        plan = QualificationPlan()
        buckets = {
            QualificationBucket.ALREADY_VERIFIED: plan.already_verified,
            QualificationBucket.READY_FOR_STRUCTURAL: plan.ready_for_structural,
            QualificationBucket.NEEDS_BINDING: plan.needs_binding,
            QualificationBucket.NEEDS_CAUSAL: plan.needs_causal,
            QualificationBucket.BLOCKED: plan.blocked,
        }

        # Select target universe: CAPABILITY_TARGETS (255) or FULL_ATLAS (1136+)
        if self._target_universe == "CAPABILITY_TARGETS":
            targets_to_qualify = sorted(self._semantic_targets.keys())
        elif self._target_universe == "FULL_ATLAS":
            targets_to_qualify = sorted(self._atlas.keys())
        else:
            raise ValueError(f"Unknown target_universe: {self._target_universe}")

        for target in targets_to_qualify:
            # Resolve target to Atlas control and semantic reference
            if self._target_universe == "CAPABILITY_TARGETS":
                # target is a semantic target name; look up in brain_index
                ref = self._semantic_targets.get(target)
                capability_key = getattr(ref, "capability_key", None) if ref else None
                # Find corresponding Atlas control by normalized name
                atlas_key = None
                for ak in self._atlas.keys():
                    if self._normalize(ak) == self._normalize(target):
                        atlas_key = ak
                        break
                control = self._atlas.get(atlas_key) if atlas_key else None
                brain_registered = ref is not None
            else:  # FULL_ATLAS
                control = self._atlas[target]
                hit = self._brain_index.get(self._normalize(target))
                brain_registered = hit is not None
                ref = hit[1] if hit else None
                capability_key = getattr(ref, "capability_key", None) if ref else None

            if control is None:
                # Semantic target has no Atlas entry
                candidate = BindingCandidate(
                    target=target,
                    capability_key=capability_key,
                    route_type=RouteType.UNBOUND,
                    binding=None,
                    operation_family=OperationFamily.STRUCTURED,
                    provenance="UNIVERSE_SEMANTIC_ONLY",
                    confidence=0.0,
                    verified=False,
                    reason="No Atlas control entry found for this semantic target.",
                )
            else:
                candidate = self._candidate(target, control, capability_key)
            contract = (
                self._registry.get(capability_key)
                if capability_key
                else None
            )
            contract_status = getattr(contract, "status", None)

            if contract_status == CAUSAL_VERIFIED:
                bucket = QualificationBucket.ALREADY_VERIFIED
                reason = "CAUSAL_VERIFIED contract exists."
            elif contract_status == STRUCTURAL_ONLY:
                bucket = QualificationBucket.NEEDS_CAUSAL
                reason = "STRUCTURAL_ONLY exists; causal proof is still required."
            elif contract_status in {
                BLOCKED_CONTRADICTED,
                NEGATIVE_EVIDENCE,
                UNSUPPORTED,
            }:
                bucket = QualificationBucket.BLOCKED
                reason = "Registered contract is blocked/negative/unsupported."
            elif candidate.is_verified():
                bucket = QualificationBucket.READY_FOR_STRUCTURAL
                reason = "Authoritative binding exists; no qualifying contract is registered."
            else:
                bucket = QualificationBucket.NEEDS_BINDING
                reason = candidate.reason
                if not brain_registered:
                    reason = (
                        "No Brain semantic target is registered; "
                        "binding cannot be inferred."
                    )

            item = TargetQualification(
                target=target,
                capability_key=capability_key,
                control_type=getattr(control, "control_type", None),
                operation_family=candidate.operation_family,
                candidate=candidate,
                bucket=bucket,
                contract_status=contract_status,
                brain_registered=brain_registered,
                reason=reason,
            )
            plan.all_targets.append(item)
            buckets[bucket].append(item)

        return plan


__all__ = [
    "BindingCandidate",
    "MutationSpec",
    "OperationFamily",
    "QualificationBucket",
    "QualificationPlan",
    "QualificationPlanner",
    "RouteType",
    "StructuralQualificationBackend",
    "StructuralQualificationResult",
    "StructuralQualificationRunner",
    "TargetQualification",
]
