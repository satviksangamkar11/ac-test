"""
Test suite for AuthorizedPresetCompiler.

Verifies:
- Compilation from authorized capabilities to executable PresetSpec
- Atomicity (all-or-nothing, no silent drops)
- Provenance preservation
- FX chain construction (distortion, hyper, EQ, delay, compressor)
- Generic capability handling (oscillators, filters, envelopes)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from serum2.execution.authorized_preset_compiler import (
    AuthorizedPresetCompiler,
    AuthorizedExecutionSet,
    AuthorizedCapability,
    CompilationStatus,
)


class TestAuthorizedPresetCompiler:
    """Test suite for compiler."""

    @pytest.fixture
    def prague_lead_capabilities(self):
        """Load Prague Lead Phase 5 capabilities from admission file."""
        admission_file = Path(__file__).parent.parent / "capability_resolution_admission.json"
        with open(admission_file) as f:
            data = json.load(f)

        capabilities = []
        for cap_data in data["capability_resolutions"]:
            cap = AuthorizedCapability(
                capability_id=cap_data["capability_id"],
                brain_decision_id=cap_data["brain_decision"],
                requested_operation=cap_data["requested_operation"],
                serum_capability=cap_data["serum_capability"],
                qualified_parameters=cap_data["qualified_parameters"],
                admission_status=cap_data["admission_status"],
                authorization_rationale=cap_data["authorization_rationale"],
                timestamp=cap_data["timestamp"],
            )
            capabilities.append(cap)

        execution_set = AuthorizedExecutionSet(
            video_id=data["source_video_id"],
            execution_phase="Phase5_Gate6",
            capabilities=capabilities,
            admission_summary=data["admission_summary"],
        )
        return execution_set

    def test_compiler_creation(self):
        """Compiler instantiates correctly."""
        compiler = AuthorizedPresetCompiler()
        assert compiler is not None

    def test_prague_lead_compilation_success(self, prague_lead_capabilities):
        """Prague Lead Phase 5 capabilities compile successfully."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        assert result.status == CompilationStatus.SUCCESS
        assert result.preset_spec is not None
        assert len(result.errors) == 0

    def test_prague_lead_atomic_success(self, prague_lead_capabilities):
        """Prague Lead achieves atomic success (no drops)."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        assert result.is_atomic_success()
        assert len(result.dropped_capabilities) == 0

    def test_prague_lead_fx_chain_complete(self, prague_lead_capabilities):
        """All 5 FX present in effects array."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        assert result.preset_spec is not None
        fx_chain = result.preset_spec.fx_chain

        assert len(fx_chain) == 5, f"Expected 5 FX, got {len(fx_chain)}"

        # Check FX types present
        fx_types = [fx.type for fx in fx_chain]
        assert "FXDistortion" in fx_types, "Missing FXDistortion"
        assert "FXHyperD" in fx_types, "Missing FXHyperD"
        assert "FXEQ" in fx_types, "Missing FXEQ"
        assert "FXDelay" in fx_types, "Missing FXDelay"
        assert "FXComp" in fx_types, "Missing FXComp"


    def test_prague_lead_oscillators_present(self, prague_lead_capabilities):
        """Oscillators (A, B, Noise) configured correctly."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        oscs = result.preset_spec.oscillators
        assert len(oscs) >= 3, f"Expected ≥3 oscillators, got {len(oscs)}"

        # OSC A
        osc_a = oscs[0]
        assert osc_a.volume == 0.85
        assert osc_a.enabled is True

        # OSC B
        osc_b = oscs[1]
        assert osc_b.volume == 0.0  # Silent modulation target

    def test_prague_lead_filter_configured(self, prague_lead_capabilities):
        """Filter (MG18 ladder) configured correctly."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        filters = result.preset_spec.filters
        assert len(filters) >= 1
        filt = filters[0]
        assert filt.type == "LadderMg"
        assert filt.cutoff == 0.375  # normalized
        assert filt.resonance == 0.75

    def test_prague_lead_envelopes_present(self, prague_lead_capabilities):
        """Envelopes (2-4) configured correctly."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        envs = result.preset_spec.envelopes
        assert len(envs) >= 3, f"Expected ≥3 envelopes, got {len(envs)}"

        # ENV2 is at index 1 in the list
        env2 = envs[1]
        assert env2.attack == 0.01
        assert env2.decay == 0.1
        assert env2.sustain == 0.1
        assert env2.release == 0.5

    def test_prague_lead_lfo_configured(self, prague_lead_capabilities):
        """LFO (Chaos Lorentz) configured correctly."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        lfos = result.preset_spec.lfos
        assert len(lfos) >= 1

        lfo0 = lfos[0]
        assert lfo0.rate == 0.5
        assert lfo0.beat_sync is False  # free-running Hz mode

    def test_prague_lead_provenance_complete(self, prague_lead_capabilities):
        """Provenance map includes all major components."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        provenance_keys = set(result.provenance_map.keys())

        # Check major provenance entries exist
        assert "oscillators.0" in provenance_keys, "Missing OSC A provenance"
        assert "oscillators.1" in provenance_keys, "Missing OSC B provenance"
        assert "filters.0" in provenance_keys, "Missing filter provenance"
        assert "envelopes.1" in provenance_keys, "Missing ENV2 provenance"
        assert "lfos.0" in provenance_keys, "Missing LFO provenance"
        assert "fx_chain.distortion" in provenance_keys, "Missing distortion provenance"
        assert "fx_chain.hyper" in provenance_keys, "Missing hyper provenance"
        assert "fx_chain.delay" in provenance_keys, "Missing delay provenance"
        assert "fx_chain.compressor" in provenance_keys, "Missing compressor provenance"

    def test_prague_lead_provenance_traceability(self, prague_lead_capabilities):
        """Provenance chains trace back to authorized capabilities."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        for key, prov in result.provenance_map.items():
            # Every provenance entry must have a capability_id
            assert prov.capability_id is not None
            assert prov.capability_id.startswith("cap_")

            # Check that capability_id exists in input
            cap_ids = {c.capability_id for c in prague_lead_capabilities.capabilities}
            assert prov.capability_id in cap_ids, (
                f"Provenance references unknown capability: {prov.capability_id}"
            )

    def test_empty_capabilities_fails_safely(self):
        """Empty capability set fails with COMPLETE_FAILURE."""
        compiler = AuthorizedPresetCompiler()
        execution_set = AuthorizedExecutionSet(
            video_id="test",
            execution_phase="test",
            capabilities=[],
            admission_summary={},
        )

        result = compiler.compile(execution_set)
        assert result.status == CompilationStatus.COMPLETE_FAILURE
        assert len(result.errors) > 0
        assert result.preset_spec is None

    def test_unauthorized_capability_fails_safely(self):
        """Unauthorized capability causes COMPLETE_FAILURE."""
        compiler = AuthorizedPresetCompiler()

        unauthorized_cap = AuthorizedCapability(
            capability_id="cap_test_unauthorized",
            brain_decision_id="br_test",
            requested_operation="test",
            serum_capability="test",
            qualified_parameters=[],
            admission_status="REJECTED",  # NOT authorized
            authorization_rationale="test",
            timestamp="2026-09-20T00:00:00Z",
        )

        execution_set = AuthorizedExecutionSet(
            video_id="test",
            execution_phase="test",
            capabilities=[unauthorized_cap],
            admission_summary={},
        )

        result = compiler.compile(execution_set)
        assert result.status == CompilationStatus.COMPLETE_FAILURE
        assert len(result.errors) > 0

    def test_spec_schema_validity(self, prague_lead_capabilities):
        """Generated PresetSpec has required schema fields."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        spec = result.preset_spec
        assert spec is not None

        # Required top-level fields (Pydantic model attributes)
        assert spec.name is not None
        assert hasattr(spec, "oscillators")
        assert hasattr(spec, "filters")
        assert hasattr(spec, "envelopes")
        assert hasattr(spec, "lfos")
        assert hasattr(spec, "fx_chain")

        # Type checks
        assert isinstance(spec.oscillators, list)
        assert isinstance(spec.filters, list)
        assert isinstance(spec.envelopes, list)
        assert isinstance(spec.lfos, list)
        assert isinstance(spec.fx_chain, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
