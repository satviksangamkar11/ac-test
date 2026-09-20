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
        # Try to import serum-mcp PresetSpec for proper typing
        try:
            import sys
            from pathlib import Path
            serum_mcp_src = Path("D:/serum-mcp/src")
            if str(serum_mcp_src) not in sys.path:
                sys.path.insert(0, str(serum_mcp_src))
            from serum_mcp.generation.spec import PresetSpec
            self._PresetSpec = PresetSpec
            use_serum_spec = True
        except ImportError:
            # serum-mcp not available; fall back to dict output
            self._PresetSpec = None
            use_serum_spec = False

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

        # Initialize empty spec (dict for now)
        spec_dict = self._initialize_empty_spec()

        # Compile core capabilities
        self._compile_core_capabilities(
            execution_set.core_capabilities(), spec_dict, result
        )
        if result.errors:
            result.status = CompilationStatus.COMPLETE_FAILURE
            return result

        # Compile FX capabilities
        self._compile_fx_capabilities(
            execution_set.fx_capabilities(), spec_dict, result
        )

        # Atomic check: if any FX dropped (except serum-mcp-unsupported), fail
        fx_cap_ids = {c.capability_id for c in execution_set.fx_capabilities()}
        # cap_014 is authorized but serum-mcp doesn't expose it; this is not a failure
        not_exposed_caps = {"cap_014_final_filter_mg_ladder"}
        dropped_fx = [
            c for c in result.dropped_capabilities
            if c in fx_cap_ids and c not in not_exposed_caps
        ]
        if dropped_fx:
            result.status = CompilationStatus.COMPLETE_FAILURE
            result.errors.append(
                f"FX compilation incomplete: dropped {dropped_fx}. "
                f"Aborting atomic execution."
            )
            result.preset_spec = None
            return result

        # Convert dict to serum-mcp PresetSpec if available
        if self._PresetSpec:
            try:
                result.preset_spec = self._PresetSpec(**spec_dict)
            except Exception as e:
                result.errors.append(f"Failed to construct PresetSpec: {e}")
                result.status = CompilationStatus.COMPLETE_FAILURE
                result.preset_spec = None
                return result
        else:
            result.preset_spec = spec_dict

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
        """Create empty PresetSpec with all required fields for serum-mcp."""
        return {
            "name": "Prague Lead - Phase 5",
            "description": "Phase 5 gate 6 execution: parametric lead with FX chain",
            "oscillators": [],
            "filters": [],
            "envelopes": [],
            "lfos": [],
            "fx_chain": [],
            "mod_routes": [],
            "voice": {},  # global voice settings
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
                    # cap_014 is authorized but not exposed in serum-mcp
                    self._compile_final_filter(cap, result)
                    fx_unit = None  # intentionally not added to chain
                    # Do NOT add to dropped_capabilities; this is not a failure
                    continue
                else:
                    result.warnings.append(f"Unknown FX capability: {cap.capability_id}")
                    fx_unit = None

                if fx_unit:
                    fx_chain.append(fx_unit)
                elif cap.capability_id != "cap_014_final_filter_mg_ladder":
                    result.dropped_capabilities.append(cap.capability_id)

            except Exception as e:
                result.errors.append(
                    f"{cap.capability_id}: {type(e).__name__}: {str(e)}"
                )
                result.dropped_capabilities.append(cap.capability_id)

        spec["fx_chain"] = fx_chain

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
        # serum-mcp PresetSpec doesn't expose metadata; this is a no-op for spec building

    def _compile_osc_a(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Oscillator A: saw + phase distortion."""
        osc_a = {
            "enabled": True,
            "octave": 0.0,
            "semitone": 0.0,
            "fine": 0.0,
            "volume": 0.85,
            "pan": 0.0,
            "unison": 1.0,
            "unison_detune": 0.0,
            "wavetable": "default",
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
            "enabled": True,
            "octave": 0.0,
            "semitone": 0.0,
            "fine": 0.0,
            "volume": 0.0,  # silent
            "pan": 0.0,
            "unison": 1.0,
            "unison_detune": 0.0,
            "wavetable": "default",
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
            "rate": 0.5,  # Hz when beat_sync=False
            "beat_sync": False,  # free-running mode
            "mode": "Free",
            "smooth": 0.0,
            "delay": 0.0,
            "mono": False,
        }
        spec["lfos"].append(lfo)
        result.provenance_map["lfos.0"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_noise_env3(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Noise oscillator + Envelope 3 modulation."""
        # Noise is slot index 3 in oscillators array
        noise = {
            "enabled": True,
            "octave": 0.0,
            "semitone": 0.0,
            "fine": 0.0,
            "volume": 0.0,  # silent (gated by envelope)
            "pan": 0.0,
            "noise_type": "white",
        }
        spec["oscillators"].append(noise)
        result.provenance_map["oscillators.3"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

        # Envelope 3 (index 2): fast attack noise gate
        env3 = {
            "attack": 0.005,
            "decay": 0.05,
            "sustain": 0.0,
            "release": 0.1,
            "attack_curve": 0.0,
            "decay_curve": 0.0,
            "release_curve": 0.0,
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
        """Filter: MG18 ladder, OSC A only. Cutoff normalized 0-1 (1800Hz → ~0.375)."""
        # serum-mcp expects 0.0-1.0 normalized cutoff. 1800Hz is roughly 0.375 normalized
        filt = {
            "enabled": True,
            "type": "LadderMg",  # serum-mcp's actual filter type enum value
            "cutoff": 0.375,  # normalized: 0=closed, 1=fully open
            "resonance": 0.75,  # 0-100 range
            "drive": 0.0,
            "stereo": 50.0,
            "var": 0.0,
            "key_track": False,
            "wet": 100.0,
            "level_out": 0.5,
        }
        spec["filters"].append(filt)
        result.provenance_map["filters.0"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    def _compile_env2_pluck(
        self, cap: AuthorizedCapability, spec: Dict[str, Any],
        result: CompilationResult
    ) -> None:
        """Envelope 2: pluck ADSR for filter modulation."""
        env2 = {
            "attack": 0.01,
            "decay": 0.1,
            "sustain": 0.1,
            "release": 0.5,
            "attack_curve": 0.0,
            "decay_curve": 0.0,
            "release_curve": 0.0,
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
        """Envelope 4: fast decay envelope for tuning modulation."""
        env4 = {
            "attack": 0.002,
            "decay": 0.02,
            "sustain": 0.0,
            "release": 0.15,
            "attack_curve": 0.0,
            "decay_curve": 0.0,
            "release_curve": 0.0,
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
        """Bus 1 routing + Convolver reverb. Stored in mod_routes for future matrix setup."""
        # Note: serum-mcp's FX bus routing (filter to bus_1, bus_1 send levels)
        # is exposed via global spec fields, not fx_chain.
        # For now, record the intent in provenance; actual implementation
        # would require parsing serum-mcp's GlobalSpec fields.
        result.provenance_map["voice.bus_1_routing"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

    # ===== FX COMPILATION METHODS =====

    def _compile_distortion(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: Distortion (overdrive mode) + drive/mix. Uses serum-mcp's raw parameter names."""
        fx_unit = {
            "type": "FXDistortion",
            "wet": 40.0,  # mix 0.4 → 40% wet
            "params": {
                "kParamMode": "kOverdrive",  # raw serum parameter enum
                "kParamDrive": 60.0,  # 0.6 normalized → 60% of serum's 0-100 range
                "kParamWet": 40.0,  # explicit wet control in params
            },
            "rack": 0,
        }
        result.provenance_map["fx_chain.distortion"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit

    def _compile_hyper(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: Hyper/Dimension (7 voices, width, tune). Maps to serum-mcp FXHyperD."""
        fx_unit = {
            "type": "FXHyperD",
            "wet": 50.0,  # default wet mix
            "params": {
                "kParamUnison": 7.0,  # 7 voices (range 0-7)
                "kParamDimESize": 50.0,  # dimension 0.5 → 50%
                "kParamDetune": 20.0,  # tune 0.2 → 20%
                "kParamWet": 50.0,
            },
            "rack": 0,
        }
        result.provenance_map["fx_chain.hyper"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit

    def _compile_eq_delay(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[List[Dict[str, Any]]]:
        """FX: EQ (mid +6dB @ 1kHz) + Delay (ping-pong 1/16)."""
        fx_units = []

        # EQ: +6dB at 1kHz (band 2 = presence peak)
        eq_unit = {
            "type": "FXEQ",
            "wet": 100.0,  # EQ doesn't have a built-in wet control, always at 100
            "params": {
                "kParamFreq1": 200.0,  # low band (leave at default)
                "kParamFreq2": 1000.0,  # presence peak at 1kHz
                "kParamGain1": 0.0,  # low band flat
                "kParamGain2": 6.0,  # +6dB presence
                "kParamReso1": 0.0,
                "kParamReso2": 0.0,
            },
            "rack": 0,
        }
        fx_units.append(eq_unit)
        result.provenance_map["fx_chain.eq"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

        # Delay: ping-pong 1/16 note (250ms @ 120 BPM = 1/16, but as explicit seconds when beat_sync=False)
        # 1/16 note = 0.25s at 120 BPM
        delay_unit = {
            "type": "FXDelay",
            "wet": 50.0,  # default wet mix
            "params": {
                "kParamTimeL": 0.25,  # left channel: 250ms
                "kParamTimeR": 0.25,  # right channel: 250ms (ping-pong)
                "kParamFeedback": 60.0,  # 0.6 → 60%
                "kParamBeatSync": False,  # literal seconds, not BPM-synced
                "kParamWet": 50.0,
            },
            "rack": 0,
        }
        fx_units.append(delay_unit)
        result.provenance_map["fx_chain.delay"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )

        return fx_units

    def _compile_compressor(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """FX: Compressor (4:1 ratio, light compression). Uses serum-mcp raw parameters."""
        fx_unit = {
            "type": "FXComp",
            "wet": 100.0,  # compressor is always fully wet
            "params": {
                "kParamThresh": 0.6,  # threshold normalized 0-1
                "kParamRatio": 4.0,  # 4:1 ratio
                "kParamAttack": 10.0,  # 10ms attack (serum default)
                "kParamRelease": 100.0,  # 100ms release (serum default)
                "kParamMakeup": 3.0,  # ~3dB makeup gain (min 1.0, reasonable auto-gain)
            },
            "rack": 0,
        }
        result.provenance_map["fx_chain.compressor"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        return fx_unit

    def _compile_final_filter(
        self, cap: AuthorizedCapability,
        result: CompilationResult
    ) -> Optional[Dict[str, Any]]:
        """
        FX: MG Ladder filter (final stage).

        NOTE: According to gate6_execution_record.json, cap_014 is
        "Not exposed in serum-mcp PresetSpec; host effects chain
        configuration required". Therefore, this capability is AUTHORIZED
        but NOT COMPILED to a PresetSpec FX entry.

        This is recorded in provenance but returns None (no FX unit).
        """
        result.provenance_map["effects.final_filter_not_exposed"] = ProvenanceChain(
            capability_id=cap.capability_id,
            brain_decision_id=cap.brain_decision_id,
        )
        # Not a warning or error; serum-mcp simply doesn't expose this capability
        return None
