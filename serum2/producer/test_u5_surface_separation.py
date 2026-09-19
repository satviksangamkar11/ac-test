"""U5: Multi-Surface Binding Separation — RED tests.

Proves that one canonical target exposes independently typed surfaces
without any surface implying another.

Architecture under test:
    CanonicalTargetSurfaces
    ├── reference  — Atlas identity (EXACT/ALIAS/AMBIGUOUS/UNRESOLVED)
    ├── preset     — Serum preset representation (oscillators[1].enabled, …)
    ├── ui         — Live UI observation (label, screen_region, status)
    └── execution  — Qualified execution route (BODY_STATE / HOST_PARAMETER /
                     SERUM_PRESET_STRUCTURAL / …) with explicit provenance

Six invariants:
    U5-A  All four surfaces are independently queryable
    U5-B  Reference does NOT imply execution
    U5-C  Preset surface ≠ UI surface
    U5-D  Execution binding carries provenance (route_type, binding_source,
           verification_level, evidence_reference)
    U5-E  VST3 HOST_PARAMETER ("B Enable") does NOT become Serum preset execution
    U5-F  Missing execution surface is explicitly NOT_EXECUTABLE, not UNKNOWN

These tests are RED until serum2/producer/target_surfaces.py is created.
Do NOT create a second binding registry — TargetSurfaceView builds over the
existing ContractRegistry, Atlas, and ControlState infrastructure.
"""
import pytest
from serum2.producer.target_surfaces import (
    CanonicalTargetSurfaces,
    ReferenceSurface,
    PresetSurface,
    UISurface,
    ExecutionSurface,
    TargetSurfaceResolver,
    SERUM_PRESET_STRUCTURAL,
    HOST_PARAMETER,
    BODY_STATE,
    NOT_EXECUTABLE,
    EXECUTION_ELIGIBLE_ROUTES,
)
from serum2.reference.serum_atlas import normalize_control, EXACT, ALIAS, AMBIGUOUS, UNRESOLVED
from serum2.producer.contract_registry import ContractRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolver():
    return TargetSurfaceResolver(ContractRegistry())


# ---------------------------------------------------------------------------
# U5-A: All four surfaces are independently queryable
# ---------------------------------------------------------------------------

class TestU5IndependentSurfaces:
    """Each surface can be present or absent independently."""

    def test_surfaces_dataclass_has_all_four_fields(self):
        """CanonicalTargetSurfaces must have reference, preset, ui, execution."""
        s = CanonicalTargetSurfaces(
            canonical_id="oscB.enabled",
            reference=None,
            preset=None,
            ui=None,
            execution=None,
        )
        assert hasattr(s, "reference")
        assert hasattr(s, "preset")
        assert hasattr(s, "ui")
        assert hasattr(s, "execution")

    def test_reference_surface_has_status_and_canonical_id(self):
        ref = ReferenceSurface(
            status=EXACT,
            canonical_id="oscB.enabled",
            raw_input="oscB.enabled",
            provenance="serum_atlas",
        )
        assert ref.status == EXACT
        assert ref.canonical_id == "oscB.enabled"
        assert ref.provenance == "serum_atlas"

    def test_execution_surface_has_route_type_binding_source_and_verification(self):
        es = ExecutionSurface(
            route_type=BODY_STATE,
            binding_source="body_state_mapping.json",
            verification_level="CAUSAL_VERIFIED",
            evidence_reference="envelope_field_release",
            body_path="Envelope0.plainParams.kParamRelease",
        )
        assert es.route_type == BODY_STATE
        assert es.binding_source == "body_state_mapping.json"
        assert es.verification_level == "CAUSAL_VERIFIED"
        assert es.evidence_reference is not None

    def test_known_qualified_target_has_reference_and_execution(self):
        """env1.decay has both Atlas identity and a qualified CAUSAL_VERIFIED contract."""
        resolver = _resolver()
        surfaces = resolver.resolve("env1.decay")
        assert surfaces.reference is not None, "env1.decay must have a reference surface"
        assert surfaces.reference.status == EXACT
        assert surfaces.execution is not None, "env1.decay must have an execution surface"

    def test_atlas_only_target_has_reference_but_no_execution(self):
        """env1.hold is Atlas-known but has no CAUSAL_VERIFIED contract."""
        resolver = _resolver()
        surfaces = resolver.resolve("env1.hold")
        assert surfaces.reference is not None, "env1.hold must have a reference surface"
        assert surfaces.reference.status == EXACT
        assert surfaces.execution is None or surfaces.execution.route_type == NOT_EXECUTABLE, \
            "env1.hold must not have an execution surface (no qualified contract)"

    def test_surfaces_report_is_answerable_without_collapsing(self):
        """The surface view must answer all six U5-completion-gate questions."""
        resolver = _resolver()
        surfaces = resolver.resolve("env1.decay")
        report = surfaces.to_report()
        assert "target_known" in report
        assert "reference_surface" in report
        assert "preset_surface" in report
        assert "ui_surface" in report
        assert "execution_surface" in report
        assert "execution_qualified" in report
        # Values are boolean or None, never fused
        assert isinstance(report["target_known"], bool)
        assert isinstance(report["execution_qualified"], bool)


# ---------------------------------------------------------------------------
# U5-B: Reference does NOT imply execution
# ---------------------------------------------------------------------------

class TestU5ReferenceDoesNotImplyExecution:
    """Having an Atlas-known identity does not grant execution authority."""

    def test_atlas_known_without_contract_is_not_executable(self):
        """env1.hold: Atlas EXACT, no CAUSAL_VERIFIED contract → NOT_EXECUTABLE."""
        from serum2.reference.serum_atlas import normalize_control
        # Verify boundary condition: Atlas knows it
        assert normalize_control("env1.hold").status == EXACT
        # Verify no contract exists
        cr = ContractRegistry()
        assert "env1.hold" not in cr.contracts  # capability_key form may differ
        # Resolve surfaces
        surfaces = _resolver().resolve("env1.hold")
        assert surfaces.reference is not None, "Reference must be present"
        assert surfaces.execution is None or surfaces.execution.route_type == NOT_EXECUTABLE, \
            f"Reference alone must not produce an execution surface; got {surfaces.execution}"

    def test_reference_surface_provenance_is_atlas_not_contract(self):
        """ReferenceSurface.provenance must trace to Atlas, not ContractRegistry."""
        resolver = _resolver()
        surfaces = resolver.resolve("env1.hold")
        assert surfaces.reference.provenance in ("serum_atlas", "atlas"), \
            f"Reference provenance must be Atlas; got {surfaces.reference.provenance!r}"

    def test_is_executable_returns_false_when_no_execution_surface(self):
        surfaces = CanonicalTargetSurfaces(
            canonical_id="env1.hold",
            reference=ReferenceSurface(status=EXACT, canonical_id="env1.hold",
                                       raw_input="env1.hold", provenance="serum_atlas"),
            preset=None, ui=None, execution=None,
        )
        assert not surfaces.is_executable(), \
            "Surfaces with no execution binding must not report is_executable()"


# ---------------------------------------------------------------------------
# U5-C: Preset surface ≠ UI surface
# ---------------------------------------------------------------------------

class TestU5PresetNotUI:
    """Preset path and UI representation describe the same control differently
    and must remain separate surfaces."""

    def test_preset_surface_carries_serialization_path(self):
        """Preset surface: how the value appears in a .SerumPreset file."""
        ps = PresetSurface(
            preset_path="oscillators[1].enabled",
            provenance="serum_mcp_schema",
        )
        assert ps.preset_path == "oscillators[1].enabled"
        assert ps.provenance == "serum_mcp_schema"

    def test_ui_surface_carries_display_label_and_region(self):
        """UI surface: how the control appears on screen."""
        ui = UISurface(
            label="OSC B",
            screen_region="OSC B panel, enable button",
            observation_status="OBSERVED",
            provenance="visual_observation",
        )
        assert ui.label == "OSC B"
        assert ui.screen_region is not None

    def test_osc2_enable_preset_path_differs_from_ui_label(self):
        """oscillators[1].enabled (preset) ≠ 'OSC B indicator' (UI).
        They describe the same canonical target but remain different surfaces."""
        ps = PresetSurface(preset_path="oscillators[1].enabled", provenance="serum_mcp_schema")
        ui = UISurface(label="OSC B", screen_region="OSC B panel", observation_status="OBSERVED",
                       provenance="visual_observation")
        surfaces = CanonicalTargetSurfaces(
            canonical_id="oscB.enabled",
            reference=ReferenceSurface(status=EXACT, canonical_id="oscB.enabled",
                                       raw_input="oscB.enabled", provenance="serum_atlas"),
            preset=ps, ui=ui, execution=None,
        )
        assert surfaces.preset.preset_path == "oscillators[1].enabled"
        assert surfaces.ui.label == "OSC B"
        assert surfaces.preset.preset_path != surfaces.ui.label, \
            "Preset path and UI label must stay separate"


# ---------------------------------------------------------------------------
# U5-D: Execution binding carries provenance
# ---------------------------------------------------------------------------

class TestU5ExecutionProvenance:
    """ExecutionSurface must carry route_type, binding_source,
    verification_level, and evidence_reference."""

    def test_qualified_target_execution_surface_is_complete(self):
        """env1.decay has a CAUSAL_VERIFIED contract with a body_path."""
        resolver = _resolver()
        surfaces = resolver.resolve("env1.decay")
        assert surfaces.execution is not None
        ex = surfaces.execution
        assert ex.route_type is not None, "route_type must be set"
        assert ex.binding_source, "binding_source must be non-empty"
        assert ex.verification_level in ("CAUSAL_VERIFIED", "STRUCTURAL_ONLY"), \
            f"verification_level must reflect contract status; got {ex.verification_level!r}"
        assert ex.evidence_reference, "evidence_reference must trace back to a contract or evidence id"

    def test_execution_surface_route_type_is_typed_constant_not_string_literal(self):
        """route_type must use the typed constant, not a free-form string."""
        ex = ExecutionSurface(
            route_type=BODY_STATE,
            binding_source="body_state_mapping.json",
            verification_level="CAUSAL_VERIFIED",
            evidence_reference="envelope_field_release",
        )
        # The constants BODY_STATE, HOST_PARAMETER, SERUM_PRESET_STRUCTURAL
        # must all be importable from target_surfaces
        assert ex.route_type == BODY_STATE
        from serum2.producer.target_surfaces import SERUM_PRESET_STRUCTURAL, HOST_PARAMETER
        assert SERUM_PRESET_STRUCTURAL is not None
        assert HOST_PARAMETER is not None


# ---------------------------------------------------------------------------
# U5-E: VST3 HOST_PARAMETER does not become Serum preset execution
# ---------------------------------------------------------------------------

class TestU5VST3NotPresetExecution:
    """'B Enable' (VST3 host parameter) is a reference surface, not a
    Serum preset structural execution route.

    The semantic_vst3_mapping.json entry for oscillator_field_OSC2-ENABLE
    maps to 'B Enable' — a HOST_PARAMETER reference, not a preset binding.
    oscB.enabled's canonical execution route is SERUM_PRESET_STRUCTURAL
    (via serum-mcp), not HOST_PARAMETER.
    """

    def test_vst3_b_enable_is_not_serum_preset_structural(self):
        """oscillator_field_OSC2-ENABLE → 'B Enable' is HOST_PARAMETER (VST3).
        This must NOT be presented as SERUM_PRESET_STRUCTURAL execution."""
        import json
        from pathlib import Path
        mapping = json.loads(
            (Path(__file__).parent.parent / "qualification" / "semantic_vst3_mapping.json")
            .read_text()
        )
        # Verify the boundary: 'B Enable' is in the VST3 map
        mappings = mapping.get("mappings", {})
        assert "oscillator_field_OSC2-ENABLE" in mappings
        assert mappings["oscillator_field_OSC2-ENABLE"] == "B Enable"
        # Construct what the contract registry would produce
        cr = ContractRegistry()
        # If a contract exists for oscillator_field_OSC2-ENABLE, its execution_binding
        # must be HOST_PARAMETER, not SERUM_PRESET_STRUCTURAL
        contract = cr.contracts.get("oscillator_field_OSC2-ENABLE")
        if contract is not None and contract.execution_binding is not None:
            assert contract.execution_binding.mutation_type == "HOST_PARAMETER", \
                f"VST3 mapping must produce HOST_PARAMETER, not {contract.execution_binding.mutation_type}"
            assert contract.execution_binding.mutation_type != SERUM_PRESET_STRUCTURAL, \
                "VST3 'B Enable' must not become SERUM_PRESET_STRUCTURAL"

    def test_host_parameter_execution_surface_is_not_serum_preset_structural(self):
        """An ExecutionSurface with route_type=HOST_PARAMETER is explicitly
        NOT the Serum preset structural route."""
        ex = ExecutionSurface(
            route_type=HOST_PARAMETER,
            binding_source="semantic_vst3_mapping.json",
            verification_level="STRUCTURAL_ONLY",
            evidence_reference="oscillator_field_OSC2-ENABLE",
            host_parameter_name="B Enable",
        )
        assert ex.route_type == HOST_PARAMETER
        assert ex.route_type != SERUM_PRESET_STRUCTURAL, \
            "HOST_PARAMETER and SERUM_PRESET_STRUCTURAL must be distinct route types"

    def test_osc2_enable_surfaces_distinguish_vst3_from_preset(self):
        """For oscB.enabled:
          reference   = Atlas EXACT (oscB.enabled)
          execution via HOST_PARAMETER = VST3 reference evidence only
          execution via SERUM_PRESET_STRUCTURAL = the canonical Serum route
        These are not interchangeable.
        """
        vst3_surface = ExecutionSurface(
            route_type=HOST_PARAMETER,
            binding_source="semantic_vst3_mapping.json",
            verification_level="STRUCTURAL_ONLY",
            evidence_reference="oscillator_field_OSC2-ENABLE",
            host_parameter_name="B Enable",
        )
        serum_surface = ExecutionSurface(
            route_type=SERUM_PRESET_STRUCTURAL,
            binding_source="serum_mcp",
            verification_level="CAUSAL_VERIFIED",
            evidence_reference="oscB.enabled_mcp_qualified",
        )
        assert vst3_surface.route_type != serum_surface.route_type, \
            "VST3 HOST_PARAMETER and Serum preset structural must remain distinct surfaces"


# ---------------------------------------------------------------------------
# U5-F: Missing execution surface is explicitly NOT_EXECUTABLE
# ---------------------------------------------------------------------------

class TestU5MissingExecutionExplicit:
    """An Atlas-known target with no execution binding must report
    NOT_EXECUTABLE, not UNKNOWN_TARGET."""

    def test_atlas_known_no_execution_reports_not_executable(self):
        """env1.hold: known target, no execution → NOT_EXECUTABLE (not UNKNOWN)."""
        resolver = _resolver()
        surfaces = resolver.resolve("env1.hold")
        # Must have reference
        assert surfaces.canonical_id == "env1.hold" or surfaces.reference is not None
        # Must explicitly report not executable
        assert not surfaces.is_executable(), \
            "Missing execution surface must report is_executable()=False"
        report = surfaces.to_report()
        assert report["target_known"] is True, \
            "Target is known (Atlas EXACT) — must not be UNKNOWN"
        assert report["execution_qualified"] is False, \
            "Execution is NOT qualified — must be explicitly False, not None/missing"

    def test_not_executable_constant_is_importable_and_distinct(self):
        """NOT_EXECUTABLE is a typed sentinel, not None or False."""
        assert NOT_EXECUTABLE is not None
        assert NOT_EXECUTABLE != BODY_STATE
        assert NOT_EXECUTABLE != HOST_PARAMETER
        assert NOT_EXECUTABLE != SERUM_PRESET_STRUCTURAL

    def test_surfaces_to_report_never_collapses_absent_surface_to_unknown_target(self):
        """A target with no execution surface must still report target_known=True."""
        surfaces = CanonicalTargetSurfaces(
            canonical_id="oscA.unison",
            reference=ReferenceSurface(status=EXACT, canonical_id="oscA.unison",
                                       raw_input="oscA.unison", provenance="serum_atlas"),
            preset=None, ui=None, execution=None,
        )
        report = surfaces.to_report()
        assert report["target_known"] is True
        assert report["execution_surface"] is False
        assert report["execution_qualified"] is False


# ---------------------------------------------------------------------------
# U5-G (regression): HOST_PARAMETER is NOT canonical Serum execution
# ---------------------------------------------------------------------------

class TestU5RouteEligibilityRegression:
    """Regression: HOST_PARAMETER (VST3 evidence) is reference/evidence only.
    It must not be selected as the canonical Serum execution route.

    EXECUTION_ELIGIBLE_ROUTES = {SERUM_PRESET_STRUCTURAL, BODY_STATE}
    HOST_PARAMETER ∉ EXECUTION_ELIGIBLE_ROUTES
    """

    def test_host_parameter_not_in_execution_eligible_routes(self):
        """HOST_PARAMETER is explicitly excluded from canonical Serum execution."""
        assert HOST_PARAMETER not in EXECUTION_ELIGIBLE_ROUTES, \
            "HOST_PARAMETER must not be a canonical Serum execution route"

    def test_body_state_and_serum_preset_structural_are_eligible(self):
        """The two canonical Serum execution routes must be eligible."""
        assert BODY_STATE in EXECUTION_ELIGIBLE_ROUTES
        assert SERUM_PRESET_STRUCTURAL in EXECUTION_ELIGIBLE_ROUTES

    def test_host_parameter_execution_surface_is_not_executable(self):
        """A HOST_PARAMETER execution surface must NOT make is_executable() True."""
        surfaces = CanonicalTargetSurfaces(
            canonical_id="env1.decay",
            reference=ReferenceSurface(status="EXACT", canonical_id="env1.decay",
                                       raw_input="env1.decay", provenance="serum_atlas"),
            preset=None, ui=None,
            execution=ExecutionSurface(
                route_type=HOST_PARAMETER,
                binding_source="semantic_vst3_mapping.json",
                verification_level="CAUSAL_VERIFIED",
                evidence_reference="envelope_field_decay",
                host_parameter_name="Env 1 Decay",
            ),
        )
        assert not surfaces.is_executable(), \
            "HOST_PARAMETER binding must not produce is_executable()=True"

    def test_env1_decay_via_resolver_is_not_executable(self):
        """env1.decay resolved live: has HOST_PARAMETER binding but NOT executable.
        The CAUSAL_VERIFIED evidence exists; the canonical Serum route does not yet."""
        from serum2.producer.contract_registry import ContractRegistry
        resolver = TargetSurfaceResolver(ContractRegistry())
        surfaces = resolver.resolve("env1.decay")
        assert surfaces.execution is not None, \
            "env1.decay must have an execution surface (HOST_PARAMETER evidence)"
        assert surfaces.execution.route_type == HOST_PARAMETER, \
            f"Expected HOST_PARAMETER; got {surfaces.execution.route_type}"
        assert not surfaces.is_executable(), \
            "HOST_PARAMETER binding alone must not make env1.decay executable"
        report = surfaces.to_report()
        assert report["execution_surface"] is True, \
            "Execution surface EXISTS (HOST_PARAMETER evidence)"
        assert report["execution_qualified"] is False, \
            "Execution is NOT qualified for canonical Serum route"

    def test_body_state_execution_surface_is_executable(self):
        """A BODY_STATE execution surface IS canonical Serum execution."""
        surfaces = CanonicalTargetSurfaces(
            canonical_id="fxeq.freq1",
            reference=ReferenceSurface(status="EXACT", canonical_id="fxeq.freq1",
                                       raw_input="fxeq.freq1", provenance="serum_atlas"),
            preset=None, ui=None,
            execution=ExecutionSurface(
                route_type=BODY_STATE,
                binding_source="body_state_mapping.json",
                verification_level="CAUSAL_VERIFIED",
                evidence_reference="fx_field_eq_freq1",
                body_path="FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",
            ),
        )
        assert surfaces.is_executable(), \
            "BODY_STATE binding must produce is_executable()=True"
        report = surfaces.to_report()
        assert report["execution_qualified"] is True

    def test_serum_preset_structural_execution_surface_is_executable(self):
        """A SERUM_PRESET_STRUCTURAL surface is the canonical Serum execution route."""
        surfaces = CanonicalTargetSurfaces(
            canonical_id="oscB.enabled",
            reference=ReferenceSurface(status="EXACT", canonical_id="oscB.enabled",
                                       raw_input="oscB.enabled", provenance="serum_atlas"),
            preset=None, ui=None,
            execution=ExecutionSurface(
                route_type=SERUM_PRESET_STRUCTURAL,
                binding_source="serum_mcp",
                verification_level="CAUSAL_VERIFIED",
                evidence_reference="oscB.enabled_mcp_qualified",
            ),
        )
        assert surfaces.is_executable()
        assert surfaces.to_report()["execution_qualified"] is True
