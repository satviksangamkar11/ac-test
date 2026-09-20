"""
End-to-end test: AuthorizedPresetCompiler → serum-mcp → .SerumPreset → FXRack0

GATE 6 ACCEPTANCE CRITERIA:
✓ Compilation produces PresetSpec
✓ serum-mcp.generate_preset() accepts spec
✓ .SerumPreset file is created
✓ Unpacked FXRack0["FX"] contains exactly 5 FX entries
✓ No silent drops (5 authorized → 5 serialized)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from serum2.execution.authorized_preset_compiler import (
    AuthorizedPresetCompiler,
    AuthorizedExecutionSet,
    AuthorizedCapability,
)


class TestCompilerSerumMcpE2E:
    """End-to-end: Compiler → serum-mcp → .SerumPreset."""

    @pytest.fixture(scope="class")
    def serum_mcp_tools(self):
        """Load real serum-mcp tools."""
        try:
            serum_mcp_src = Path("D:/serum-mcp/src")
            if not serum_mcp_src.exists():
                raise ImportError(f"serum-mcp source not found: {serum_mcp_src}")

            if str(serum_mcp_src) not in sys.path:
                sys.path.insert(0, str(serum_mcp_src))

            from serum_mcp.tools.generate_preset import generate_preset
            from serum_mcp.preset.packer import unpack_file
            from serum_mcp.generation.spec import PresetSpec

            return {
                "generate_preset": generate_preset,
                "unpack_file": unpack_file,
                "PresetSpec": PresetSpec,
            }
        except (ImportError, AttributeError) as e:
            pytest.fail(
                f"SERUM_MCP_UNAVAILABLE: {type(e).__name__}: {str(e)}\n"
                f"Gate 6 requires serum-mcp at D:/serum-mcp/src"
            )

    @pytest.fixture
    def prague_lead_capabilities(self):
        """Load Prague Lead Phase 5 authorized capabilities."""
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

        return AuthorizedExecutionSet(
            video_id=data["source_video_id"],
            execution_phase="Phase5_Gate6",
            capabilities=capabilities,
            admission_summary=data["admission_summary"],
        )

    def test_serum_mcp_available(self, serum_mcp_tools):
        """serum-mcp is available."""
        assert serum_mcp_tools is not None
        assert serum_mcp_tools["generate_preset"] is not None
        assert serum_mcp_tools["unpack_file"] is not None

    def test_compiler_to_serum_mcp_end_to_end(self, prague_lead_capabilities, serum_mcp_tools):
        """
        GATE 6 ACCEPTANCE TEST: Compiler → serum-mcp → .SerumPreset → 5 FX

        This is the critical test that verifies the complete chain.
        """
        # Compile authorized capabilities
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(prague_lead_capabilities)

        assert result.is_atomic_success(), f"Compilation failed: {result.errors}"
        spec = result.preset_spec
        assert spec is not None

        # spec is a PresetSpec object; serum-mcp uses fx_chain
        compiled_fx_count = len(spec.fx_chain) if spec.fx_chain else 0
        assert compiled_fx_count == 5, f"Compiler produced {compiled_fx_count} FX, expected 5"

        # Pass to real serum-mcp
        try:
            preset_path = serum_mcp_tools["generate_preset"](spec)
            preset_path = Path(preset_path)
        except Exception as e:
            pytest.fail(f"serum-mcp.generate_preset() failed: {type(e).__name__}: {e}")

        assert preset_path.exists(), f"File not created: {preset_path}"
        assert preset_path.stat().st_size > 0, "File is empty"

        # Unpack and verify
        try:
            decoded = serum_mcp_tools["unpack_file"](str(preset_path))
        except Exception as e:
            pytest.fail(f"unpack_file failed: {type(e).__name__}: {e}")

        # THE REGRESSION CHECK: 5 → 5 (no drops)
        fx_chain = decoded.get("FXRack0", {}).get("FX", [])
        serialized_fx_count = len(fx_chain)

        assert serialized_fx_count == 5, (
            f"FX CHAIN MISMATCH:\n"
            f"  Compiled: 5\n"
            f"  Serialized: {serialized_fx_count}\n"
            f"This is the Prague Lead Phase 5 failure."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
