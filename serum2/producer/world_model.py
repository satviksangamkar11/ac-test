"""16.5.61: World Model — current state of the arrangement.

Represents what currently exists: sections, roles, tracks, Serum state, capabilities.

The Planner compares GoalModel against WorldModel to identify gaps.

Structure:

    WorldModel
        ├── arrangement: ArrangementState (song key, tempo, length, sections)
        └── roles: Dict[str, RoleState]
             ├── bass
             │    ├── track_id
             │    ├── serum_state (known parameters + measured characteristics)
             │    ├── verified_capabilities (what evidence proved)
             │    └── current_constraints (prerequisites, limitations)
             │
             ├── pad
             └── lead

The World Model is READ ONLY from the Planner's perspective.
Updates come from:
  1. Ableton state (track info, device parameters)
  2. Measurement (render → analyze audio)
  3. Evidence system (what capabilities are proven)

Measured characteristics (brightness, attack, sustain, etc.) come from audio analysis,
not from Serum parameter inspection. This is critical: the Planner reasons about music,
not about parameter values.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime

from .goal_model import MusicalCharacteristics


@dataclass(frozen=True)
class MeasuredCharacteristics:
    """Audio characteristics derived from rendering/measurement.

    These are measured, not parametric. Comes from audio analysis:
      - brightness: spectral centroid or high-frequency RMS
      - attack: onset detection
      - sustain_level: sustain window RMS
      - density: note density, frequency content
      - spread: stereo width analysis

    measurement_id links to the measurement kernel used (for provenance).
    timestamp records when this measurement was taken.
    """
    brightness: Optional[float] = None        # 0-1, where 1 = bright
    attack_speed: Optional[float] = None      # 0-1, where 1 = fast/punchy
    sustain_level: Optional[float] = None     # 0-1, sustain loudness relative to peak
    density: Optional[float] = None           # 0-1, frequency content density
    spread: Optional[float] = None            # 0-1, stereo width (0 = mono, 1 = wide)
    overall_loudness_db: Optional[float] = None

    measurement_id: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brightness": self.brightness,
            "attack_speed": self.attack_speed,
            "sustain_level": self.sustain_level,
            "density": self.density,
            "spread": self.spread,
            "overall_loudness_db": self.overall_loudness_db,
            "measurement_id": self.measurement_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass(frozen=True)
class VerifiedCapability:
    """One capability that evidence proved for this role/context.

    Points back into the evidence system:
      - capability_key: the semantic target (e.g., "OSC1.Volume")
      - contract_hash: fingerprint of the CapabilityContract
      - status: CAUSAL_VERIFIED, STRUCTURAL_ONLY, NEGATIVE_EVIDENCE
      - context_requirement: prerequisite values that must hold
    """
    capability_key: str
    contract_hash: str
    status: str
    context_requirement: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SerumState:
    """Known Serum parameter state for a role.

    parameter_values: dict of semantic_target_name -> host value (0-1)
    last_updated_at: when this was last read from Ableton
    source: "mcp_read" | "mcp_write_readback" | "measurement_baseline"
    """
    parameter_values: Dict[str, float] = field(default_factory=dict)
    last_updated_at: Optional[datetime] = None
    source: str = "unknown"

    def get_parameter(self, semantic_target: str) -> Optional[float]:
        """Get a known parameter value, or None if not measured."""
        return self.parameter_values.get(semantic_target)


@dataclass(frozen=True)
class RoleState:
    """Current state of one role (bass, pad, lead, etc.).

    role: name (e.g., "bass")
    track_id: Ableton track index
    device_index: Serum device index in the track chain (usually 0)
    serum_state: known parameters
    measured_characteristics: audio characteristics from last render
    verified_capabilities: what evidence proved
    unresolved_limitations: known gaps (e.g., "no MCP mapping for Env1.Sustain")
    """
    role: str
    track_id: int
    device_index: int
    serum_state: SerumState = field(default_factory=SerumState)
    measured_characteristics: MeasuredCharacteristics = field(default_factory=MeasuredCharacteristics)
    verified_capabilities: List[VerifiedCapability] = field(default_factory=list)
    unresolved_limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "track_id": self.track_id,
            "device_index": self.device_index,
            "serum_state": {
                "parameter_values": self.serum_state.parameter_values,
                "last_updated_at": self.serum_state.last_updated_at.isoformat() if self.serum_state.last_updated_at else None,
                "source": self.serum_state.source,
            },
            "measured_characteristics": self.measured_characteristics.to_dict(),
            "verified_capabilities": [
                {
                    "capability_key": vc.capability_key,
                    "contract_hash": vc.contract_hash,
                    "status": vc.status,
                    "context_requirement": vc.context_requirement,
                }
                for vc in self.verified_capabilities
            ],
            "unresolved_limitations": self.unresolved_limitations,
        }


@dataclass(frozen=True)
class SectionState:
    """One section of the arrangement (intro, verse, peak, outro, etc.)."""
    name: str
    start_beat: float
    length_beats: float
    roles_present: List[str]  # which roles are active in this section


@dataclass(frozen=True)
class ArrangementState:
    """Song-level arrangement state."""
    key: Optional[str] = None          # "A minor", etc.
    tempo_bpm: Optional[float] = None
    total_length_beats: Optional[float] = None
    sections: List[SectionState] = field(default_factory=list)

    def get_section(self, section_name: str) -> Optional[SectionState]:
        for s in self.sections:
            if s.name == section_name:
                return s
        return None


@dataclass(frozen=True)
class WorldModel:
    """Complete current state: arrangement + role states.

    READ ONLY from the Planner perspective.
    Updated by:
      1. AbletonMCP read operations
      2. Measurement/rendering
      3. Evidence system queries
    """
    arrangement: ArrangementState = field(default_factory=ArrangementState)
    roles: Dict[str, RoleState] = field(default_factory=dict)

    def get_role(self, role_name: str) -> Optional[RoleState]:
        return self.roles.get(role_name)

    def get_role_in_section(self, role_name: str, section_name: str) -> Optional[RoleState]:
        """Get role state if it exists AND is active in this section."""
        role = self.get_role(role_name)
        if role is None:
            return None
        section = self.arrangement.get_section(section_name)
        if section is None:
            return None
        if role_name not in section.roles_present:
            return None
        return role

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arrangement": {
                "key": self.arrangement.key,
                "tempo_bpm": self.arrangement.tempo_bpm,
                "total_length_beats": self.arrangement.total_length_beats,
                "sections": [
                    {
                        "name": s.name,
                        "start_beat": s.start_beat,
                        "length_beats": s.length_beats,
                        "roles_present": s.roles_present,
                    }
                    for s in self.arrangement.sections
                ],
            },
            "roles": {
                name: role.to_dict()
                for name, role in self.roles.items()
            },
        }
