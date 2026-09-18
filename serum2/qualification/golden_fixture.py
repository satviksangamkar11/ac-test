"""
Golden Production-Slice Fixture: ep_prod_001

Immutable frozen reference for the validated serum-mcp integration proof.
All 11-point provenance locked in; serves as regression baseline for Gate 2.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path

ROOT = str(Path(__file__).parent.parent.parent)


@dataclass(frozen=True)
class GoldenProductionSliceFixture:
    """Immutable reference to the frozen ep_prod_001 production slice."""

    # Episode metadata
    episode_id: str = "ep_prod_001"
    episode_intent_text: str = "bright, fat lead sound with slight movement"

    # Semantic decision (producer brain output)
    semantic_role: str = "lead"
    semantic_brightness: str = "bright"
    semantic_oscillator: str = "saw"
    semantic_density: str = "fat"
    semantic_movement: str = "subtle"

    # Admitted capabilities
    admitted_capabilities: tuple = (
        "cap_osc_wavetable",
        "cap_filter_cutoff",
        "cap_envelope_attack_release",
    )

    # PresetSpec signature
    preset_name: str = "Lead Bright"
    preset_description: str = "Auto-generated: lead with bright brightness, saw oscillator, fat density, subtle movement"

    # serum-mcp invocation
    mcp_tool_name: str = "serum-mcp:generate_preset"
    mcp_spec_hash: str = "848c8d1395d10074"
    preset_sha256: str = "472618eb46084ce78794b5f36431c928cac95d134ac8c2d131da367b0c18c106"

    # Serum file path
    preset_filename: str = "Lead Bright.SerumPreset"
    preset_relative_path: str = "Presets\\User\\Lead Bright.SerumPreset"

    # Serum 2.0.21 load confirmation
    serum_load_status: str = "MANUALLY_LOADED_CONFIRMED"

    # DawDreamer render metadata
    render_duration_bars: int = 4
    render_tempo_bpm: int = 120
    render_sample_rate: int = 44100

    # Acoustic measurements (predicted vs actual)
    actual_rms_db: float = -12.5
    actual_peak_db: float = -3.2
    actual_spectral_centroid_hz: float = 3100.0

    predicted_rms_db: float = -13.0
    predicted_peak_db: float = -3.0
    predicted_centroid_hz: float = 3200.0

    # Measurement deltas
    rms_delta: float = 0.5
    peak_delta: float = -0.2
    centroid_delta: float = -100.0

    # Tolerances
    rms_tolerance: float = 2.0
    peak_tolerance: float = 1.5
    centroid_tolerance: float = 500.0

    # Final outcome
    outcome: str = "PASS"

    # Evidence record path
    evidence_record_filename: str = "prod_slice_1_ep_prod_001.json"


GOLDEN_FIXTURE = GoldenProductionSliceFixture()


def load_evidence_record() -> Dict[str, Any]:
    """Load the frozen evidence record from disk."""
    import json

    evidence_path = Path(ROOT) / "serum2" / "qualification" / GOLDEN_FIXTURE.evidence_record_filename

    if not evidence_path.exists():
        raise FileNotFoundError(f"Evidence record not found: {evidence_path}")

    with open(evidence_path, "r") as f:
        return json.load(f)


def validate_golden_fixture() -> bool:
    """Verify all 11 provenance points intact and unchanged."""

    evidence = load_evidence_record()

    # 1. Episode ID
    assert evidence["episode_id"] == GOLDEN_FIXTURE.episode_id, \
        f"Episode ID mismatch: {evidence['episode_id']} != {GOLDEN_FIXTURE.episode_id}"

    # 2. Episode intent text
    assert evidence["episode_intent_text"] == GOLDEN_FIXTURE.episode_intent_text, \
        f"Intent mismatch: {evidence['episode_intent_text']}"

    # 3. Semantic decision
    sem = evidence["semantic_decision"]
    assert sem["role"] == GOLDEN_FIXTURE.semantic_role
    assert sem["brightness"] == GOLDEN_FIXTURE.semantic_brightness
    assert sem["oscillator"] == GOLDEN_FIXTURE.semantic_oscillator
    assert sem["density"] == GOLDEN_FIXTURE.semantic_density
    assert sem["movement"] == GOLDEN_FIXTURE.semantic_movement

    # 4. Admitted capabilities
    assert tuple(evidence["admitted_capability_ids"]) == GOLDEN_FIXTURE.admitted_capabilities, \
        f"Capabilities mismatch: {evidence['admitted_capability_ids']}"

    # 5. PresetSpec
    spec = evidence["preset_spec"]
    assert spec["name"] == GOLDEN_FIXTURE.preset_name
    assert spec["description"] == GOLDEN_FIXTURE.preset_description

    # 6. MCP invocation
    mcp = evidence["mcp_invocation"]
    assert mcp["tool_name"] == GOLDEN_FIXTURE.mcp_tool_name
    assert mcp["spec_hash"] == GOLDEN_FIXTURE.mcp_spec_hash
    assert mcp["preset_sha256"] == GOLDEN_FIXTURE.preset_sha256

    # 7. Preset path + SHA-256
    assert evidence["preset_sha256"] == GOLDEN_FIXTURE.preset_sha256
    assert GOLDEN_FIXTURE.preset_relative_path in evidence["preset_path"]

    # 8. Serum load status
    assert evidence["serum_load_status"] == GOLDEN_FIXTURE.serum_load_status
    assert evidence["serum_load_evidence"] is not None

    # 9. Render artifact path
    assert evidence.get("render_artifact_path") is not None

    # 10. Measurements
    meas = evidence["measurements"]
    assert meas["rms_db"] == GOLDEN_FIXTURE.actual_rms_db
    assert meas["peak_db"] == GOLDEN_FIXTURE.actual_peak_db
    assert meas["spectral_centroid_hz"] == GOLDEN_FIXTURE.actual_spectral_centroid_hz
    assert meas["render_duration_bars"] == GOLDEN_FIXTURE.render_duration_bars
    assert meas["render_tempo_bpm"] == GOLDEN_FIXTURE.render_tempo_bpm

    # Predicted measurements
    pred = evidence["predicted_measurements"]
    assert pred["rms_db"] == GOLDEN_FIXTURE.predicted_rms_db
    assert pred["peak_db"] == GOLDEN_FIXTURE.predicted_peak_db
    assert pred["spectral_centroid_hz"] == GOLDEN_FIXTURE.predicted_centroid_hz

    # Deltas
    deltas = evidence["measurement_deltas"]
    assert abs(deltas["rms_db"] - GOLDEN_FIXTURE.rms_delta) < 0.01
    assert abs(deltas["peak_db"] - GOLDEN_FIXTURE.peak_delta) < 0.01
    assert abs(deltas["spectral_centroid_hz"] - GOLDEN_FIXTURE.centroid_delta) < 1

    # 11. Outcome
    assert evidence["outcome"] == GOLDEN_FIXTURE.outcome

    return True


if __name__ == "__main__":
    try:
        validate_golden_fixture()
        print("[OK] Golden fixture validated — all 11 provenance points intact")
        print(f"Episode: {GOLDEN_FIXTURE.episode_id}")
        print(f"Preset SHA-256: {GOLDEN_FIXTURE.preset_sha256[:16]}...")
        print(f"Outcome: {GOLDEN_FIXTURE.outcome}")
    except AssertionError as e:
        print(f"[ERROR] Golden fixture validation failed: {e}")
        exit(1)
