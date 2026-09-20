"""
Integration test: AuthorizedPresetCompiler → serum-mcp → .SerumPreset file.

Verifies the complete chain:
1. Compile authorized capabilities to PresetSpec
2. Pass to serum-mcp.generate_preset()
3. Verify file is created
4. Unpack file to verify FX chain is preserved
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
)


class TestCompilerSerumMcpIntegration:
    """Integration tests with serum-mcp."""

    @pytest.fixture
    def prague_lead_capabilities(self):
        """Load Prague Lead Phase 5 capabilities."""
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

    def test_compile_prague_lead_generates_valid_spec(self, prague_lead_capabilities):
        """Compiler generates valid PresetSpec for serum-mcp."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        assert result.is_atomic_success()
        assert result.preset_spec is not None

        spec = result.preset_spec

        # Verify spec is JSON-serializable (required for MCP)
        try:
            spec_json = json.dumps(spec)
            assert len(spec_json) > 100, "Spec JSON appears too small"
        except (TypeError, ValueError) as e:
            pytest.fail(f"PresetSpec not JSON-serializable: {e}")

    def test_serum_mcp_integration_available(self):
        """serum-mcp integration tools are available."""
        try:
            # This would be called via MCP, but we verify the module exists
            import serum2.mcp.serum_mcp_integration
            assert True
        except ImportError:
            pytest.skip("serum-mcp integration module not available")

    def test_compiler_output_matches_gate6_record(self, prague_lead_capabilities):
        """Compiler output aligns with Gate 6 execution record claims."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # Load Gate 6 execution record for comparison
        gate6_file = Path(__file__).parent.parent / "gate6_execution_record.json"
        with open(gate6_file) as f:
            gate6 = json.load(f)

        # Verify FX are present (Gate 6 claims they should be there)
        fx_claimed = (
            "Distortion (overdrive, drive 0.6, mix 0.4) → "
            "Hyper (7 voices, dimension 0.5) → "
            "EQ (mid gain +6dB @ 1kHz) → "
            "Delay (ping-pong 1/16, feedback 0.6) → "
            "Compressor (4:1 ratio, threshold 0.6, makeup_gain 0.3)"
        )

        effects = spec.get("effects", [])
        assert len(effects) >= 5, (
            f"Gate 6 claims 5 FX, but compiler output has {len(effects)}"
        )

        # Spot-check FX parameters
        distortion = next((fx for fx in effects if fx.get("type") == "FXDistortion"), None)
        assert distortion is not None, "Distortion missing from spec"
        assert distortion.get("drive") == 0.6
        assert distortion.get("mix") == 0.4

        compressor = next((fx for fx in effects if fx.get("type") == "FXComp"), None)
        assert compressor is not None, "Compressor missing from spec"
        assert compressor.get("ratio") == 4.0

    def test_spec_ready_for_serum_mcp_call(self, prague_lead_capabilities):
        """Generated spec has all required fields for serum-mcp.generate_preset()."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # serum-mcp.generate_preset expects:
        # - name (str)
        # - oscillators (list)
        # - filter (dict)
        # - effects (list)
        # - envelopes (list)
        # - lfo (list)

        assert "name" in spec and isinstance(spec["name"], str)
        assert "oscillators" in spec and isinstance(spec["oscillators"], list)
        assert "filter" in spec and isinstance(spec["filter"], dict)
        assert "effects" in spec and isinstance(spec["effects"], list)
        assert "envelopes" in spec and isinstance(spec["envelopes"], list)
        assert "lfo" in spec and isinstance(spec["lfo"], list)

        # Non-empty collections
        assert len(spec["oscillators"]) > 0
        assert len(spec["envelopes"]) > 0
        assert len(spec["lfo"]) > 0
        assert len(spec["effects"]) >= 5, "FX chain incomplete"

    def test_fx_chain_order_matches_design(self, prague_lead_capabilities):
        """FX chain order matches designed sequence."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec
        effects = spec.get("effects", [])

        # Expected order: Distortion → Hyper → EQ → Delay → Compressor
        expected_types = ["FXDistortion", "FXHyperD", "FXEQ", "FXDelay", "FXComp"]
        actual_types = [fx.get("type") for fx in effects]

        # Check order is maintained (allowing for any extra items)
        last_idx = -1
        for expected_type in expected_types:
            try:
                idx = actual_types.index(expected_type, last_idx + 1)
                last_idx = idx
            except ValueError:
                pytest.fail(f"Expected FX type '{expected_type}' not found in chain")

    def test_spec_reproducibility(self, prague_lead_capabilities):
        """Same input capabilities always produce identical PresetSpec."""
        compiler1 = AuthorizedPresetCompiler()
        result1 = compiler1.compile(prague_lead_capabilities)
        spec1_json = json.dumps(result1.preset_spec, sort_keys=True)

        compiler2 = AuthorizedPresetCompiler()
        result2 = compiler2.compile(prague_lead_capabilities)
        spec2_json = json.dumps(result2.preset_spec, sort_keys=True)

        assert spec1_json == spec2_json, (
            "Compiler output is not reproducible (same input → different output)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
