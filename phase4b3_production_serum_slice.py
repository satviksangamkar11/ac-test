#!/usr/bin/env python3
"""
PHASE 4B.3 — Production Vertical Slice: serum-mcp integration

Single-episode end-to-end flow:
  Episode → Producer Brain → Semantic Intent → Capability Admission
  → PresetSpec → serum-mcp MCP call → .SerumPreset
  → Evidence Record (11-point provenance)

No Ableton yet. No 908/396 inventory yet. One clean, auditable chain.
"""

import json
import hashlib
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

ROOT = str(Path(__file__).parent)
for p in [ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)


# ============================================================================
# PART 1: Semantic Intent Structure
# ============================================================================

class OscillatorType(str, Enum):
    """Semantic oscillator character."""
    SAW = "saw"
    SINE = "sine"
    SQUARE = "square"
    PULSE = "pulse"


class Brightness(str, Enum):
    """Semantic brightness (relates to filter cutoff)."""
    DARK = "dark"
    WARM = "warm"
    BRIGHT = "bright"
    VERY_BRIGHT = "very_bright"


class Density(str, Enum):
    """Semantic density (relates to unison/detune)."""
    THIN = "thin"
    NORMAL = "normal"
    FAT = "fat"


class Movement(str, Enum):
    """Semantic movement (relates to modulation/LFO)."""
    STATIC = "static"
    SUBTLE = "subtle"
    ANIMATED = "animated"


class Role(str, Enum):
    """Semantic role in the mix."""
    LEAD = "lead"
    PAD = "pad"
    BASS = "bass"
    PLUCK = "pluck"
    BELL = "bell"


@dataclass(frozen=True)
class SemanticSerumIntent:
    """Producer brain output: semantic intent, not raw Serum JSON."""
    role: Role
    brightness: Brightness
    oscillator: OscillatorType
    density: Density
    movement: Movement


# ============================================================================
# PART 2: Semantic → PresetSpec Translator
# ============================================================================

def semantic_to_preset_spec(intent: SemanticSerumIntent) -> Dict[str, Any]:
    """Translate semantic intent to serum-mcp PresetSpec.

    This is the capability admission layer: semantic decision → actual Serum config.
    """

    # Oscillator wavetable selection
    wavetable_map = {
        OscillatorType.SAW: "default",
        OscillatorType.SINE: "sine",
        OscillatorType.SQUARE: "square",
        OscillatorType.PULSE: "default",  # Will use pulse warp
    }

    # Brightness → filter cutoff
    cutoff_map = {
        Brightness.DARK: 0.15,
        Brightness.WARM: 0.35,
        Brightness.BRIGHT: 0.60,
        Brightness.VERY_BRIGHT: 0.80,
    }

    # Density → unison voices
    unison_map = {
        Density.THIN: 1.0,
        Density.NORMAL: 1.0,
        Density.FAT: 3.0,
    }

    # Density → detune amount
    detune_map = {
        Density.THIN: 0.0,
        Density.NORMAL: 0.0,
        Density.FAT: 0.15,
    }

    # Movement → LFO/modulation
    has_lfo = intent.movement != Movement.STATIC
    lfo_rate = 0.5 if intent.movement == Movement.SUBTLE else 1.0 if intent.movement == Movement.ANIMATED else 0.0

    # Build PresetSpec (serum-mcp format)
    spec = {
        "name": f"{intent.role.value.title()} {intent.brightness.value.title()}",
        "description": f"Auto-generated: {intent.role.value} with {intent.brightness.value} brightness, {intent.oscillator.value} oscillator, {intent.density.value} density, {intent.movement.value} movement",

        "oscillators": [
            {
                "enabled": True,
                "octave": 0.0,
                "volume": 0.75 if intent.role == Role.LEAD else 0.6,
                "wavetable": wavetable_map[intent.oscillator],
                "unison": unison_map[intent.density],
                "detune": detune_map[intent.density],
            },
            {"enabled": False},
            {"enabled": False},
            {"enabled": False},  # Noise
            {"enabled": False},  # Sub
        ],

        "filters": [
            {
                "enabled": True,
                "type": "lowpass_24",
                "cutoff": cutoff_map[intent.brightness],
                "resonance": 0.1,
            }
        ],

        "envelopes": [
            {
                "attack": 0.02 if intent.role == Role.LEAD else 0.1,
                "decay": 0.2,
                "sustain": 0.7,
                "release": 0.5 if intent.role == Role.PLUCK else 1.0,
            }
        ],
    }

    return spec


# ============================================================================
# PART 3: serum-mcp MCP Call Orchestrator
# ============================================================================

@dataclass(frozen=True)
class MCPInvocationRecord:
    """Record of a single serum-mcp MCP tool call."""
    tool_name: str
    timestamp: str
    spec_hash: str
    preset_path: str
    preset_sha256: str


def call_serum_mcp_generate_preset(spec: Dict[str, Any]) -> MCPInvocationRecord:
    """
    Call native serum-mcp MCP: generate_preset(spec)

    NOTE: In the actual implementation, this would be a real MCP tool call.
    For now, we simulate the call by invoking the serum-mcp Python API directly.
    """
    import sys
    sys.path.insert(0, str(Path("D:/serum-mcp/src")))

    from serum_mcp.generation.spec import PresetSpec, OscillatorSpec, FilterSpec, EnvelopeSpec
    from serum_mcp.tools.generate_preset import generate_preset

    # Convert dict spec to PresetSpec (serum-mcp Pydantic model)
    osc_specs = [
        OscillatorSpec(**osc) if osc.get("enabled") else OscillatorSpec(enabled=False)
        for osc in spec["oscillators"]
    ]

    filter_specs = [FilterSpec(**f) for f in spec.get("filters", [])]
    env_specs = [EnvelopeSpec(**e) for e in spec.get("envelopes", [])]

    preset_spec = PresetSpec(
        name=spec["name"],
        description=spec["description"],
        oscillators=osc_specs,
        filters=filter_specs if filter_specs else None,
        envelopes=env_specs if env_specs else None,
    )

    # Call serum-mcp (direct Python call; in production this is MCP)
    preset_path = generate_preset(preset_spec)

    # Compute SHA-256
    preset_bytes = Path(preset_path).read_bytes()
    preset_sha256 = hashlib.sha256(preset_bytes).hexdigest()

    # Compute spec hash (preset_spec is already a dict)
    spec_json = json.dumps(preset_spec, sort_keys=True, default=str)
    spec_hash = hashlib.sha256(spec_json.encode()).hexdigest()[:16]

    return MCPInvocationRecord(
        tool_name="serum-mcp:generate_preset",
        timestamp=datetime.now(timezone.utc).isoformat(),
        spec_hash=spec_hash,
        preset_path=preset_path,
        preset_sha256=preset_sha256,
    )


# ============================================================================
# PART 4: 11-Point Evidence Recorder
# ============================================================================

@dataclass(frozen=True)
class ProductionSliceEvidence:
    """Complete provenance chain for one serum-mcp generation episode."""

    # 1. source episode ID
    episode_id: str

    # 2. source/intent
    episode_intent_text: str

    # 3. producer semantic decision
    semantic_decision: SemanticSerumIntent

    # 4. admitted capability IDs (from admission layer)
    admitted_capability_ids: list

    # 5. PresetSpec (translated from semantic)
    preset_spec: Dict[str, Any]

    # 6. MCP invocation/result
    mcp_invocation: MCPInvocationRecord

    # 7. preset path + SHA-256
    preset_path: str
    preset_sha256: str

    # 8. Serum 2.0.21 manual-load confirmation (AWAITING_HUMAN or CONFIRMED)
    serum_load_status: str
    serum_load_timestamp: Optional[str] = None

    # 9. DawDreamer render artifact (path to WAV)
    render_artifact_path: Optional[str] = None

    # 10. RMS / peak / centroid + predicted-vs-actual
    measurements: Optional[Dict[str, Any]] = None

    # 11. final outcome + provenance links
    outcome: Optional[str] = None
    deviation: Optional[str] = None


def create_production_slice_evidence(
    episode_id: str,
    episode_intent_text: str,
    semantic_decision: SemanticSerumIntent,
    admitted_capability_ids: list,
    preset_spec: Dict[str, Any],
    mcp_invocation: MCPInvocationRecord,
) -> ProductionSliceEvidence:
    """Construct 11-point evidence record."""

    return ProductionSliceEvidence(
        episode_id=episode_id,
        episode_intent_text=episode_intent_text,
        semantic_decision=semantic_decision,
        admitted_capability_ids=admitted_capability_ids,
        preset_spec=preset_spec,
        mcp_invocation=mcp_invocation,
        preset_path=mcp_invocation.preset_path,
        preset_sha256=mcp_invocation.preset_sha256,
        serum_load_status="AWAITING_HUMAN",
    )


# ============================================================================
# PART 5: Production Slice Execution
# ============================================================================

def execute_production_slice():
    """Execute one complete episode through the serum-mcp pipeline."""

    print("=" * 80)
    print("PHASE 4B.3 — PRODUCTION VERTICAL SLICE: serum-mcp Integration")
    print("=" * 80)

    # ---- Step 1: Episode ----
    print("\n[Step 1] Episode Input")

    episode_id = "ep_prod_001"
    episode_intent_text = "bright, fat lead sound with slight movement"

    print(f"  Episode ID: {episode_id}")
    print(f"  Intent: {episode_intent_text}")

    # ---- Step 2: Producer Brain → Semantic Intent ----
    print("\n[Step 2] Producer Brain → Semantic Intent")

    semantic_decision = SemanticSerumIntent(
        role=Role.LEAD,
        brightness=Brightness.BRIGHT,
        oscillator=OscillatorType.SAW,
        density=Density.FAT,
        movement=Movement.SUBTLE,
    )

    print(f"  Role: {semantic_decision.role.value}")
    print(f"  Brightness: {semantic_decision.brightness.value}")
    print(f"  Oscillator: {semantic_decision.oscillator.value}")
    print(f"  Density: {semantic_decision.density.value}")
    print(f"  Movement: {semantic_decision.movement.value}")

    # ---- Step 3: Capability Admission ----
    print("\n[Step 3] Capability Admission")

    # Simulate admission (in production, this queries actual contracts)
    admitted_capability_ids = [
        "cap_osc_wavetable",
        "cap_filter_cutoff",
        "cap_envelope_attack_release",
    ]

    print(f"  Admitted capabilities: {', '.join(admitted_capability_ids)}")

    # ---- Step 4: Semantic → PresetSpec ----
    print("\n[Step 4] Semantic → PresetSpec Translation")

    preset_spec = semantic_to_preset_spec(semantic_decision)

    print(f"  Preset Name: {preset_spec['name']}")
    print(f"  Oscillator: {preset_spec['oscillators'][0]['wavetable']}")
    print(f"  Filter Cutoff: {preset_spec['filters'][0]['cutoff']}")
    print(f"  Unison: {preset_spec['oscillators'][0]['unison']}")

    # ---- Step 5: serum-mcp MCP Call ----
    print("\n[Step 5] Call serum-mcp MCP: generate_preset()")

    try:
        mcp_invocation = call_serum_mcp_generate_preset(preset_spec)

        print(f"  ✓ MCP invocation successful")
        print(f"  Preset Path: {mcp_invocation.preset_path}")
        print(f"  Preset SHA-256: {mcp_invocation.preset_sha256[:16]}...")
        print(f"  Spec Hash: {mcp_invocation.spec_hash}")
        print(f"  Timestamp: {mcp_invocation.timestamp}")
    except Exception as e:
        print(f"  ✗ MCP invocation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ---- Step 6: Build Evidence Record ----
    print("\n[Step 6] Build Evidence Record (11-point provenance)")

    evidence = create_production_slice_evidence(
        episode_id=episode_id,
        episode_intent_text=episode_intent_text,
        semantic_decision=semantic_decision,
        admitted_capability_ids=admitted_capability_ids,
        preset_spec=preset_spec,
        mcp_invocation=mcp_invocation,
    )

    print(f"  ✓ Evidence record created")
    print(f"    1. Episode ID: {evidence.episode_id}")
    print(f"    2. Intent: {evidence.episode_intent_text}")
    print(f"    3. Semantic Decision: {evidence.semantic_decision}")
    print(f"    4. Admitted Capabilities: {evidence.admitted_capability_ids}")
    print(f"    5. PresetSpec: {evidence.preset_spec['name']}")
    print(f"    6. MCP Invocation: {evidence.mcp_invocation.tool_name}")
    print(f"    7. Preset Path: {evidence.preset_path}")
    print(f"    8. Serum Load Status: {evidence.serum_load_status}")
    print(f"    9. Render Artifact: {evidence.render_artifact_path}")
    print(f"   10. Measurements: {evidence.measurements}")
    print(f"   11. Outcome: {evidence.outcome}")

    # ---- Step 7: Save Evidence Record ----
    print("\n[Step 7] Save Evidence Record")

    evidence_path = Path(ROOT) / "serum2" / "qualification" / f"prod_slice_1_{episode_id}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    evidence_json = json.dumps({
        "episode_id": evidence.episode_id,
        "episode_intent_text": evidence.episode_intent_text,
        "semantic_decision": asdict(evidence.semantic_decision),
        "admitted_capability_ids": evidence.admitted_capability_ids,
        "preset_spec": evidence.preset_spec,
        "mcp_invocation": asdict(evidence.mcp_invocation),
        "preset_path": evidence.preset_path,
        "preset_sha256": evidence.preset_sha256,
        "serum_load_status": evidence.serum_load_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, indent=2)

    with open(evidence_path, "w") as f:
        f.write(evidence_json)

    print(f"  ✓ Evidence record saved: {evidence_path}")

    # ---- Step 8: Next Steps ----
    print("\n" + "=" * 80)
    print("PRODUCTION SLICE CHECKPOINT")
    print("=" * 80)

    print("\n✓ GENERATED: .SerumPreset file created via serum-mcp MCP")
    print("\n⏳ NEXT: Manual Serum 2.0.21 Load + DawDreamer Validation")
    print("\nInstructions:")
    print(f"  1. Load preset: {evidence.preset_path}")
    print(f"  2. In Serum 2.0.21, open File → Load")
    print(f"  3. Select the preset file")
    print(f"  4. Confirm load succeeds without error")
    print(f"  5. Run DawDreamer validation (render 4 bars @ 120 BPM)")
    print(f"  6. Record measurements (RMS, peak, spectral centroid)")
    print(f"  7. Compare predicted vs actual")
    print(f"  8. Update evidence record with outcome")

    return True


if __name__ == "__main__":
    success = execute_production_slice()
    sys.exit(0 if success else 1)
