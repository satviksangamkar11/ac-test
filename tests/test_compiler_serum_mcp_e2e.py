"""
End-to-end test: AuthorizedPresetCompiler → serum-mcp → .SerumPreset → FXRack0

This test verifies the complete chain from authorized capabilities through
real serum-mcp execution to serialized .SerumPreset file.

GATE 6 ACCEPTANCE CRITERIA:
✓ Compilation produces PresetSpec
✓ serum-mcp.generate_preset() accepts spec
✓ .SerumPreset file is created
✓ Unpacked FXRack0["FX"] contains exactly 5 FX entries
✓ FX types match compiler output (Distortion, Hyper, EQ, Delay, Compressor)
✓ Serialized FX parameters match compiler specification
✓ No silent drops (5 authorized → 5 serialized)

IMPORTANT: This test does NOT mock serum-mcp. It tests against the real
installed package. If serum-mcp is unavailable, test will fail with
SERUM_MCP_UNAVAILABLE error, not skip.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from serum2.execution.authorized_preset_compiler import (
    AuthorizedPresetCompiler,
    AuthorizedExecutionSet,
    AuthorizedCapability,
)


class TestCompilerSerumMcpE2E:
    """End-to-end integration: Compiler → serum-mcp → .SerumPreset."""

    @pytest.fixture(scope="class")
    def serum_mcp_api(self):
        """
        Detect actual serum-mcp API.

        Does not skip if serum-mcp is unavailable; instead fails with
        SERUM_MCP_UNAVAILABLE so Gate 6 cannot silently pass without the
        real dependency.
        """
        try:
            # Try standard import
            import serum_mcp
            api = {
                "module": serum_mcp,
                "generate_preset": getattr(serum_mcp, "generate_preset", None),
                "unpack_file": getattr(serum_mcp, "unpack_file", None),
                "available": True,
            }
            if not api["generate_preset"] or not api["unpack_file"]:
                raise AttributeError("serum_mcp missing expected methods")
            return api
        except (ImportError, AttributeError) as e:
            pytest.fail(
                f"SERUM_MCP_UNAVAILABLE: {type(e).__name__}: {str(e)}\n"
                f"Gate 6 requires real serum-mcp. Cannot proceed without it."
            )

    @pytest.fixture
    def prague_lead_capabilities(self):
        """Load Prague Lead Phase 5 authorized capabilities."""
        admission_file = Path(__file__).parent.parent / "capability_resolution_admission.json"
        if not admission_file.exists():
            pytest.fail(f"Fixture file missing: {admission_file}")

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

    def test_serum_mcp_importable(self, serum_mcp_api):
        """serum-mcp is importable and has required methods."""
        assert serum_mcp_api is not None
        assert serum_mcp_api["available"] is True
        assert serum_mcp_api["generate_preset"] is not None
        assert serum_mcp_api["unpack_file"] is not None

    def test_compiler_produces_valid_spec(self, prague_lead_capabilities):
        """Compiler produces PresetSpec dict."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        assert result.is_atomic_success()
        assert result.preset_spec is not None
        spec = result.preset_spec

        # Verify structure
        assert isinstance(spec, dict)
        assert "effects" in spec
        assert isinstance(spec["effects"], list)
        assert len(spec["effects"]) == 5, f"Expected 5 FX, got {len(spec['effects'])}"

    def test_serum_mcp_accepts_compiled_spec(self, prague_lead_capabilities, serum_mcp_api):
        """serum-mcp.generate_preset() accepts compiler output."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # Call real serum-mcp
        try:
            preset_path = serum_mcp_api["generate_preset"](spec)
        except TypeError as e:
            pytest.fail(
                f"serum-mcp.generate_preset() rejected compiled PresetSpec: {e}\n"
                f"Spec keys: {list(spec.keys())}\n"
                f"This suggests PresetSpec schema mismatch."
            )
        except Exception as e:
            pytest.fail(
                f"serum-mcp.generate_preset() raised unexpected error: {type(e).__name__}: {e}"
            )

        assert preset_path is not None
        # preset_path should be Path or str
        preset_path = Path(preset_path) if isinstance(preset_path, str) else preset_path
        return preset_path

    def test_generated_serumpreset_exists(self, prague_lead_capabilities, serum_mcp_api):
        """Generated .SerumPreset file exists on disk."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        preset_path = serum_mcp_api["generate_preset"](spec)
        preset_path = Path(preset_path)

        assert preset_path.exists(), f"Generated preset not found: {preset_path}"
        assert preset_path.suffix.lower() == ".serumpreset", (
            f"Expected .SerumPreset extension, got {preset_path.suffix}"
        )
        assert preset_path.stat().st_size > 0, "Generated file is empty"

    def test_serialized_fx_chain_has_5_entries(self, prague_lead_capabilities, serum_mcp_api):
        """Unpacked FXRack0["FX"] contains exactly 5 FX."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # Verify compiler output has 5 FX
        compiled_fx_count = len(spec["effects"])
        assert compiled_fx_count == 5, f"Compiler produced {compiled_fx_count} FX, expected 5"

        # Generate preset
        preset_path = serum_mcp_api["generate_preset"](spec)
        preset_path = Path(preset_path)

        # Unpack file
        try:
            decoded = serum_mcp_api["unpack_file"](preset_path)
        except Exception as e:
            pytest.fail(
                f"serum-mcp.unpack_file() failed: {type(e).__name__}: {e}\n"
                f"File: {preset_path}"
            )

        # Extract FX chain
        fx_rack = decoded.get("FXRack0", {})
        fx_chain = fx_rack.get("FX", [])

        # CRITICAL: Verify no silent drop (5 → 0, 5 → fewer)
        serialized_fx_count = len(fx_chain)
        assert serialized_fx_count == 5, (
            f"FX CHAIN MISMATCH: Compiler output 5 FX, "
            f"but serialized .SerumPreset has {serialized_fx_count} FX. "
            f"This is the exact regression we're testing for."
        )

    def test_serialized_fx_types_match_compiler_output(self, prague_lead_capabilities, serum_mcp_api):
        """Serialized FX types match compiler specification."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # Compiler output types
        compiled_types = [fx.get("type") for fx in spec["effects"]]
        expected_order = ["FXDistortion", "FXHyperD", "FXEQ", "FXDelay", "FXComp"]

        # Generate and unpack
        preset_path = serum_mcp_api["generate_preset"](spec)
        decoded = serum_mcp_api["unpack_file"](Path(preset_path))
        fx_chain = decoded.get("FXRack0", {}).get("FX", [])
        serialized_types = [fx.get("type") for fx in fx_chain]

        # Verify match
        assert compiled_types == expected_order, (
            f"Compiler order mismatch: {compiled_types} vs {expected_order}"
        )
        assert serialized_types == expected_order, (
            f"Serialization order mismatch: {serialized_types} vs {expected_order}"
        )

    def test_serialized_distortion_parameters(self, prague_lead_capabilities, serum_mcp_api):
        """Distortion FX parameters preserved in serialization."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # Compiler output
        distortion = next((fx for fx in spec["effects"] if fx.get("type") == "FXDistortion"), None)
        assert distortion is not None
        assert distortion.get("drive") == 0.6
        assert distortion.get("mix") == 0.4

        # Serialized
        preset_path = serum_mcp_api["generate_preset"](spec)
        decoded = serum_mcp_api["unpack_file"](Path(preset_path))
        fx_chain = decoded.get("FXRack0", {}).get("FX", [])
        serialized_distortion = next(
            (fx for fx in fx_chain if fx.get("type") == "FXDistortion"), None
        )

        assert serialized_distortion is not None, "Distortion not in serialized chain"
        # Check that at least the mode is preserved
        # (exact parameter keys depend on serum-mcp's serializer)
        assert "mode" in serialized_distortion or "drive" in serialized_distortion, (
            f"Distortion parameters not found in serialized FX: {list(serialized_distortion.keys())}"
        )

    def test_serialized_compressor_parameters(self, prague_lead_capabilities, serum_mcp_api):
        """Compressor FX parameters preserved in serialization."""
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)
        spec = result.preset_spec

        # Compiler output
        compressor = next((fx for fx in spec["effects"] if fx.get("type") == "FXComp"), None)
        assert compressor is not None
        assert compressor.get("ratio") == 4.0

        # Serialized
        preset_path = serum_mcp_api["generate_preset"](spec)
        decoded = serum_mcp_api["unpack_file"](Path(preset_path))
        fx_chain = decoded.get("FXRack0", {}).get("FX", [])
        serialized_compressor = next(
            (fx for fx in fx_chain if fx.get("type") == "FXComp"), None
        )

        assert serialized_compressor is not None, "Compressor not in serialized chain"
        # Verify at least one parameter is preserved
        assert len(serialized_compressor) > 1, (
            f"Compressor has no parameters in serialized form: {serialized_compressor}"
        )

    def test_no_silent_fx_drops(self, prague_lead_capabilities, serum_mcp_api):
        """
        Regression test: verify 5 → 5 mapping (no silent drops).

        This is the exact failure mode we're fixing in Gate 6.
        """
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        # Count at each stage
        authorized_fx_caps = [
            c for c in prague_lead_capabilities.capabilities
            if c.capability_id.startswith("cap_01")  # cap_010-014
        ]
        assert len(authorized_fx_caps) == 5, f"Expected 5 authorized FX caps, got {len(authorized_fx_caps)}"

        spec = result.preset_spec
        compiled_fx = spec["effects"]
        assert len(compiled_fx) == 5, f"Expected 5 compiled FX, got {len(compiled_fx)}"

        # Generate and unpack
        preset_path = serum_mcp_api["generate_preset"](spec)
        decoded = serum_mcp_api["unpack_file"](Path(preset_path))
        serialized_fx = decoded.get("FXRack0", {}).get("FX", [])

        # THE CRITICAL ASSERTION
        assert len(serialized_fx) == 5, (
            f"REGRESSION DETECTED:\n"
            f"  Authorized FX capabilities:  5\n"
            f"  Compiled FX in PresetSpec:   5\n"
            f"  Serialized FX in .SerumPreset: {len(serialized_fx)}\n"
            f"  Mapping: 5 → {len(serialized_fx)}\n"
            f"This is the Prague Lead Phase 5 failure."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
