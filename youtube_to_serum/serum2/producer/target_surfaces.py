"""U5: Multi-Surface Binding Separation.

One canonical target can exist at four independent surfaces:
    reference   — Atlas identity (the only identity source)
    preset      — Serum preset representation (path in .SerumPreset)
    ui          — Live UI observation (label, screen region, live status)
    execution   — Qualified execution route with explicit provenance

No surface implies another. An Atlas-known target is not executable
until it has a CAUSAL_VERIFIED contract with an execution binding.

Does NOT create a second binding registry — builds over ContractRegistry,
the existing Atlas, and the existing ExecutionBinding dataclass.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from serum2.reference.serum_atlas import EXACT, ALIAS, AMBIGUOUS, UNRESOLVED  # noqa: F401

# Route-type constants (match ExecutionBinding.mutation_type strings)
BODY_STATE = "BODY_STATE"
HOST_PARAMETER = "HOST_PARAMETER"
SERUM_PRESET_STRUCTURAL = "SERUM_PRESET_STRUCTURAL"
NOT_EXECUTABLE = "NOT_EXECUTABLE"  # explicit sentinel: known but unqualified

# Only these routes are canonical Serum execution paths.
# HOST_PARAMETER (VST3) is reference/evidence only — it identifies a control
# exists in VST3 but does NOT authorize Serum preset mutation.
EXECUTION_ELIGIBLE_ROUTES = frozenset({SERUM_PRESET_STRUCTURAL, BODY_STATE})


@dataclass
class ReferenceSurface:
    status: str             # EXACT / ALIAS / AMBIGUOUS / UNRESOLVED
    canonical_id: str
    raw_input: str
    provenance: str         # "serum_atlas"


@dataclass
class PresetSurface:
    preset_path: str        # e.g. "oscillators[1].enabled"
    provenance: str         # "serum_mcp_schema"


@dataclass
class UISurface:
    label: str
    screen_region: Optional[str]
    observation_status: str  # "OBSERVED" / "UNOBSERVED"
    provenance: str          # "visual_observation"


@dataclass
class ExecutionSurface:
    route_type: str              # BODY_STATE / HOST_PARAMETER / SERUM_PRESET_STRUCTURAL
    binding_source: str          # file or system that defines this binding
    verification_level: str      # "CAUSAL_VERIFIED" / "STRUCTURAL_ONLY"
    evidence_reference: str      # capability_key or contract id
    body_path: Optional[str] = None
    host_parameter_name: Optional[str] = None


@dataclass
class CanonicalTargetSurfaces:
    canonical_id: str
    reference: Optional[ReferenceSurface]
    preset: Optional[PresetSurface]
    ui: Optional[UISurface]
    execution: Optional[ExecutionSurface]

    def is_executable(self) -> bool:
        """True only when canonical Serum execution is eligible.

        HOST_PARAMETER (VST3) is reference/evidence only and does NOT qualify.
        Only SERUM_PRESET_STRUCTURAL and BODY_STATE are canonical Serum routes.
        """
        return (
            self.execution is not None
            and self.execution.route_type in EXECUTION_ELIGIBLE_ROUTES
        )

    def to_report(self) -> dict:
        has_surface = self.execution is not None
        is_eligible = has_surface and self.execution.route_type in EXECUTION_ELIGIBLE_ROUTES
        return {
            "target_known": self.reference is not None,
            "reference_surface": self.reference is not None,
            "preset_surface": self.preset is not None,
            "ui_surface": self.ui is not None,
            "execution_surface": has_surface,
            "execution_qualified": (
                is_eligible
                and self.execution.verification_level == "CAUSAL_VERIFIED"
            ),
        }


class TargetSurfaceResolver:
    """Resolves a canonical_id into a CanonicalTargetSurfaces view.

    Builds over ContractRegistry and SEMANTIC_TARGETS (no second registry).
    preset and ui surfaces are not populated here — they require runtime
    observation data and are set by callers that have it.
    """

    def __init__(self, contract_registry):
        from serum2.compiler.targets import SEMANTIC_TARGETS
        from serum2.producer.target_resolution import normalize_target_name
        from serum2.reference.serum_atlas import normalize_control

        self._cr = contract_registry
        self._atlas = normalize_control
        # norm(registry_name) -> capability_key, for targets that have one
        self._by_norm: dict = {}
        for name, ref in SEMANTIC_TARGETS.items():
            cap = getattr(ref, "capability_key", None)
            if cap:
                self._by_norm[normalize_target_name(name)] = cap

    def resolve(self, canonical_id: str) -> CanonicalTargetSurfaces:
        from serum2.producer.target_resolution import normalize_target_name

        atlas_res = self._atlas(canonical_id)

        reference = None
        if atlas_res.status in (EXACT, ALIAS):
            reference = ReferenceSurface(
                status=atlas_res.status,
                canonical_id=atlas_res.canonical_id,
                raw_input=canonical_id,
                provenance="serum_atlas",
            )

        execution = None
        if reference is not None:
            norm = normalize_target_name(atlas_res.canonical_id)
            cap = self._by_norm.get(norm)
            if cap:
                contract = self._cr.contracts.get(cap)
                if contract and contract.execution_binding:
                    eb = contract.execution_binding
                    execution = ExecutionSurface(
                        route_type=eb.mutation_type,
                        binding_source=eb.binding_source or "unknown",
                        verification_level=contract.status,
                        evidence_reference=cap,
                        body_path=eb.body_path,
                        host_parameter_name=eb.host_parameter_name,
                    )

        return CanonicalTargetSurfaces(
            canonical_id=atlas_res.canonical_id or canonical_id,
            reference=reference,
            preset=None,
            ui=None,
            execution=execution,
        )
