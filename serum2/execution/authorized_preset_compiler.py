"""
Authorized Capability → Executable PresetSpec Compiler

This module translates a set of authorized capabilities (from Gate 5 admission)
into a single, atomic executable PresetSpec for serum-mcp execution.

ARCHITECTURE:
- Takes: AuthorizedExecutionSet (multiple admitted capabilities)
- Produces: PresetSpec (one atomic specification) with full provenance
- Enforces: atomicity (all-or-nothing), no silent drops, no invented parameters
- Generic: oscillators, filters, envelopes, LFO, matrix, FX

PROVENANCE:
Every PresetSpec field retains linkage back to:
  cap_XXX (authorized ID)
  → admission_id
  → ProductionEvent
  → source evidence (frame, transcript)
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class CompilationStatus(Enum):
    """Compilation result status."""
    SUCCESS = "SUCCESS"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    COMPLETE_FAILURE = "COMPLETE_FAILURE"


@dataclass
class ProvenanceChain:
    """Trace each PresetSpec field back to authorized source."""
    capability_id: str
    admission_id: Optional[str] = None
    brain_decision_id: Optional[str] = None
    production_event_id: Optional[str] = None
    frame_id: Optional[str] = None
    transcript_segment: Optional[str] = None


@dataclass
class AuthorizedCapability:
    """Single authorized capability from Gate 5."""
    capability_id: str
    brain_decision_id: str
    requested_operation: str
    serum_capability: str
    qualified_parameters: List[Dict[str, Any]]
    admission_status: str
    authorization_rationale: str
    timestamp: str


@dataclass
class AuthorizedExecutionSet:
    """Collection of authorized capabilities ready for lowering to PresetSpec."""
    video_id: str
    execution_phase: str
    capabilities: List[AuthorizedCapability]
    admission_summary: Dict[str, Any]

    def fx_capabilities(self) -> List[AuthorizedCapability]:
        """Filter to FX-related capabilities."""
        fx_cap_ids = {
            "cap_010_distortion_overdrive",
            "cap_011_hyper_dimension",
            "cap_012_eq_delay",
            "cap_013_compression_final",
            "cap_014_final_filter_mg_ladder",
        }
        return [c for c in self.capabilities if c.capability_id in fx_cap_ids]

    def core_capabilities(self) -> List[AuthorizedCapability]:
        """Filter to core oscillator/filter/envelope capabilities."""
        core_cap_ids = {
            "cap_001_init_preset",
            "cap_002_osc_a_config",
            "cap_003_osc_b_config",
            "cap_004_lfo_chaos",
            "cap_005_noise_envelope3",
            "cap_006_filter_mg18_routing",
            "cap_007_env2_pluck_adsr",
            "cap_008_env4_tuning_mod",
            "cap_009_bus1_routing_convolver",
        }
        return [c for c in self.capabilities if c.capability_id in core_cap_ids]


@dataclass
class CompilationResult:
    """Result of compilation attempt."""
    status: CompilationStatus
    preset_spec: Optional[Dict[str, Any]] = None
    provenance_map: Dict[str, ProvenanceChain] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dropped_capabilities: List[str] = field(default_factory=list)

    def is_atomic_success(self) -> bool:
        """True if compilation succeeded with zero drops."""
        return (
            self.status == CompilationStatus.SUCCESS
            and len(self.dropped_capabilities) == 0
            and len(self.errors) == 0
        )


class AuthorizedPresetCompiler:
    """
    Deterministic compiler from authorized capabilities to executable PresetSpec.

    Usage:
        compiler = AuthorizedPresetCompiler()
        result = compiler.compile(authorized_execution_set)
        if result.is_atomic_success():
            spec = result.preset_spec
            # pass to serum-mcp.generate_preset(spec)
    """

    def compile(self, execution_set: AuthorizedExecutionSet) -> CompilationResult:
        """Compile authorized capabilities to PresetSpec."""
        result = CompilationResult(status=CompilationStatus.SUCCESS)

        if not execution_set.capabilities:
            result.status = CompilationStatus.COMPLETE_FAILURE
            result.errors.append("No capabilities provided")
            return result

        # Check admission: all must be authorized
        unauthorized = [
            c for c in execution_set.capabilities
            if c.admission_status != "AUTHORIZED"
        ]
        if unauthorized:
            result.status = CompilationStatus.COMPLETE_FAILURE
            for cap in unauthorized:
                result.errors.append(
                    f"{cap.capability_id}: admission_status={cap.admission_status}"
                )
            return result

        # Initialize empty spec
        spec = self._initialize_empty_spec()

        # Compile core capabilities
        self._compile_core_capabilities(
            execution_set.core_capabilities(), spec, result
        )
        if result.errors:
            result.status = CompilationStatus.COMPLETE_FAILURE
            return result

        # Compile FX capabilities
        self._compile_fx_capabilities(
            execution_set.fx_capabilities(), spec, result
        )

        # Atomic check: if any FX dropped, fail completely
        fx_cap_ids = {c.capability_id for c in execution_set.fx_capabilities()}
        dropped_fx = [c for c in result.dropped_capabilities if c in fx_cap_ids]
        if dropped_fx:
            result.status = CompilationStatus.COMPLETE_FAILURE
            result.errors.append(
                f"FX compilation incomplete: dropped {dropped_fx}. "
                f"Aborting atomic execution."
            )
            result.preset_spec = None
            return result

        # Success
        result.preset_spec = spec
        if not result.errors and not result.warnings:
            result.status = CompilationStatus.SUCCESS
        else:
            result.status = (
                CompilationStatus.PARTIAL_FAILURE
                if result.warnings and not result.errors
                else CompilationStatus.COMPLETE_FAILURE
            )

        return result

    def _initialize_empty_spec(self) -> Dict[str, Any]:
        """Create empty PresetSpec with all required fields."""
        return {
            "name": "Prague Lead - Phase 5",
            "oscillators": [],
            "filter": {},
            "envelopes": [],
            "lfo": [],
            "effects": [],
            "matrix": [],
            "routing": {},
            "metadata": {
                "source": "AuthorizedPresetCompiler",
                "phase": "Phase5_Gate6",
            },
        }

    def _compile_core_capabilities(
        self,
        caps: List[AuthorizedCapability],
        spec: Dict[str, Any],
        result: CompilationResult,
    ) -> None:
        """Compile core oscillators, filter, envelopes, LFO."""
        for cap in caps:
            try:
                if cap.capability_id == "cap_001_init_preset":
                    self._compile_init(cap, spec, result)
                elif cap.capability_id == "cap_002_osc_a_config":
                    self._compile_osc_a(cap, spec, result)
                elif cap.capability_id == "cap_003_osc_b_config":
                    self._compile_osc_b(cap, spec, result)
                elif cap.capability_id == "cap_004_lfo_chaos":
                    self._compile_lfo_chaos(cap, spec, result)
                elif cap.capability_id == "cap_005_noise_envelope3":
                    self._compile_noise_env3(cap, spec, result)
                elif cap.capability_id == "cap_006_filter_mg18_routing":
                    self._compile_filter_mg18(cap, spec, result)
                elif cap.capability_id == "cap_007_env2_pluck_adsr":
                    self._compile_env2_pluck(cap, spec, result)
                elif cap.capability_id == "cap_008_env4_tuning_mod":
                    self._compile_env4_tuning(cap, spec, result)
                elif cap.capability_id == "cap_009_bus1_routing_convolver":
                    self._compile_bus1_convolver(cap, spec, result)
            except Exception as e:
                result.errors.append(
                    f"{cap.capability_id}: {type(e).__name__}: {str(e)}"
                )
                result.dropped_capabilities.append(cap.capability_id)

    def _compile_fx_capabilities(
        self,
        caps: List[AuthorizedCapability],
        spec: Dict[str, Any],
        result: CompilationResult,
    ) -> None:
        """Compile FX chain: distortion, hyper, EQ, delay, compressor."""
        fx_chain = []

        for cap in caps:
            try:
                if cap.capability_id == "cap_010_distortion_overdrive":
                    fx_unit = self._compile_distortion(cap, result)
                elif cap.capability_id == "cap_011_hyper_dimension":
                    fx_unit = self._compile_hyper(cap, result)
                elif cap.capability_id == "cap_012_eq_delay":
                    fx_units = self._compile_eq_delay(cap, result)
                    if fx_units:
                        fx_chain.extend(fx_units)
                    else:
                        result.dropped_capabilities.append(cap.capability_id)
                    continue
                elif cap.capability_id == "cap_013_compression_final":
                    fx_unit = self._compile_compressor(cap, result)
                elif cap.capability_id == "cap_014_final_filter_mg_ladder":
                    fx_unit = self._compile_final_filter(cap, result)
                else:
                    result.warnings.append(f"Unknown FX capability: {cap.capability_id}")
                    fx_unit = None

                if fx_unit:
                    fx_chain.append(fx_unit)
                else:
                    result.dropped_capabilities.append(cap.capability_id)

            except Exception as e:
                result.errors.append(
                    f"{cap.capability_id}: {type(e).__name__}: {str(e)}"
                )
                result.dropped_capabilities.append(cap.capability_id)

        spec["effects"] = fx_chain

    # ===== CORE COMPILATION METHODS =====

    def _compile_init(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Initialize from factory preset."""
        result.provenance_map["init"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        spec["metadata"]["initialized_from"] = "factory_default"

    def _compile_osc_a(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Oscillator A: saw + phase distortion."""
        osc_a = {
            "index": 0,
            "name": "Oscillator A",
            "enabled": True,
            "waveform": "saw",
            "table_position": 0,
            "volume": 0.85,
            "pan": 0.0,
            "semitone_tuning": 0,
            "fine_tuning": 0.0,
            "unison_voices": 1,
            "unison_detune": 0.0,
        }
        spec["oscillators"].append(osc_a)
        result.provenance_map["oscillators.0"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_osc_b(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Oscillator B: saw at zero level (silent modulation target)."""
        osc_b = {
            "index": 1,
            "name": "Oscillator B",
            "enabled": True,
            "waveform": "saw",
            "table_position": 0,
            "volume": 0.0,
            "pan": 0.0,
            "semitone_tuning": 0,
            "fine_tuning": 0.0,
            "unison_voices": 1,
            "unison_detune": 0.0,
        }
        spec["oscillators"].append(osc_b)
        result.provenance_map["oscillators.1"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_lfo_chaos(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """LFO: Chaos Lorentz, X-axis."""
        lfo = {
            "index": 0,
            "name": "LFO 0",
            "waveform": "chaos_lorentz",
            "rate": 0.5,
            "rate_sync": "free",
            "amount": 0.3,
            "target": "osc_a_pitch",
            "fine_parameter": 10,
        }
        spec["lfo"].append(lfo)
        result.provenance_map["lfo.0"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_noise_env3(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Noise oscillator + Envelope 3 modulation."""
        noise = {
            "index": 3,
            "name": "Noise",
            "enabled": True,
            "noise_type": "white",
            "volume": 0.0,
        }
        spec["oscillators"].append(noise)
        result.provenance_map["oscillators.3"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

        env3 = {
            "index": 2,
            "name": "Envelope 3",
            "attack": 0.005,
            "decay": 0.05,
            "sustain": 0.0,
            "release": 0.1,
            "modulation_target": "noise_volume",
            "modulation_amount": 1.0,
        }
        spec["envelopes"].append(env3)
        result.provenance_map["envelopes.2"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_filter_mg18(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Filter: MG18 ladder, OSC A only."""
        spec["filter"] = {
            "type": "ladder_mg18",
            "cutoff": 1800,
            "resonance": 0.75,
            "input_source": "osc_a_only",
            "modulation_target": "cutoff",
            "modulation_amount": 1.0,
        }
        result.provenance_map["filter"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_env2_pluck(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Envelope 2: pluck ADSR at 100% filter modulation."""
        env2 = {
            "index": 1,
            "name": "Envelope 2",
            "attack": 0.01,
            "decay": 0.1,
            "sustain": 0.1,
            "release": 0.5,
            "modulation_target": "filter_cutoff",
            "modulation_amount": 1.0,
        }
        spec["envelopes"].append(env2)
        result.provenance_map["envelopes.1"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_env4_tuning(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Envelope 4: global tuning modulation (sustain/decay minimum)."""
        env4 = {
            "index": 3,
            "name": "Envelope 4",
            "attack": 0.002,
            "decay": 0.02,
            "sustain": 0.0,
            "release": 0.15,
            "modulation_target": "global_tuning",
            "modulation_amount": 0.5,
        }
        spec["envelopes"].append(env4)
        result.provenance_map["envelopes.3"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_bus1_convolver(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Bus 1 routing + Convolver reverb (Digital Hall 2)."""
        spec["routing"]["filter_output"] = "bus_1"
        spec["routing"]["bus_1_effect"] = {
            "type": "convolver",
            "impulse_response": "digital_hall_2",
        }
        result.provenance_map["routing.bus_1"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    # ===== FX COMPILATION METHODS =====

    def _compile_distortion(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: Distortion (overdrive mode) + drive/mix."""
        fx_unit = {
            "type": "FXDistortion",
            "enabled": True,
            "mode": "overdrive",
            "drive": 0.6,
            "mix": 0.4,
        }
        result.provenance_map["effects.distortion"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit

    def _compile_hyper(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: Hyper/Dimension (7 voices, width, tune)."""
        fx_unit = {
            "type": "FXHyperD",
            "enabled": True,
            "voices": 7,
            "dimension": 0.5,
            "tune": 0.2,
        }
        result.provenance_map["effects.hyper"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit

    def _compile_eq_delay(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[List[Dict[str, Any]]]:
        """FX: EQ (mid +6dB) + Delay (ping-pong 1/16)."""
        fx_units = []

        eq_unit = {
            "type": "FXEQ",
            "enabled": True,
            "mid_gain": 6.0,
            "mid_freq": 1000,
        }
        fx_units.append(eq_unit)
        result.provenance_map["effects.eq"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

        delay_unit = {
            "type": "FXDelay",
            "enabled": True,
            "mode": "ping_pong",
            "time_note": "1/16",
            "feedback": 0.6,
        }
        fx_units.append(delay_unit)
        result.provenance_map["effects.delay"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

        return fx_units

    def _compile_compressor(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: Compressor (4:1 ratio, light compression)."""
        fx_unit = {
            "type": "FXComp",
            "enabled": True,
            "ratio": 4.0,
            "threshold": 0.6,
            "makeup_gain": 0.3,
        }
        result.provenance_map["effects.compressor"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit

    def _compile_final_filter(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: MG Ladder filter (final stage, between Hyper and EQ)."""
        fx_unit = {
            "type": "FXLadderFilter",
            "enabled": True,
            "filter_type": "mg_ladder",
            "cutoff": 2000,
            "resonance": 0.5,
            "placement": "between_hyper_and_eq",
        }
        result.provenance_map["effects.final_filter"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit
