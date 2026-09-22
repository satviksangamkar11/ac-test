"""Phase 4: Reference State Reconstructor

Universal conversion: reference evidence → complete canonical state manifest

Input: reference video/screenshots + episode context
Output: ReferenceStateManifest
  ├── episode/source metadata
  ├── Serum version (frozen: 2.0.21)
  ├── controls[] (every visible control with value + evidence)
  ├── matrix_routes[] (modulation connections)
  ├── topology[] (module enable states)
  ├── unknown[] (unresolved/unobserved)
  └── verification_status

The manifest is the bridge between evidence and execution:
- Evidence layer: capture what the screenshots show
- Completeness gate: every required item has a value (or explicit failure reason)
- Verification layer: Claude independently audits the manifest
- Execution layer: manifest → PresetSpec → serum-mcp → .SerumPreset
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import json


class ControlValueStatus(Enum):
    """Status of a control value in the manifest."""
    OBSERVED = "OBSERVED"  # extracted from evidence
    OBSERVED_BUT_UNVERIFIED = "OBSERVED_BUT_UNVERIFIED"
    VERIFIED = "VERIFIED"  # Claude-audited and matching
    VERIFICATION_CONFLICT = "VERIFICATION_CONFLICT"  # Claude sees different value
    SOURCE_INSUFFICIENT = "SOURCE_INSUFFICIENT"  # expected but unreadable
    NOT_VISIBLE_IN_FRAME = "NOT_VISIBLE_IN_FRAME"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    UNRESOLVED_METADATA = "UNRESOLVED_METADATA"
    UNSUPPORTED_MODALITY = "UNSUPPORTED_MODALITY"


@dataclass
class ControlValue:
    """A single control value in the reference state."""
    canonical_id: str  # e.g., "oscA.unison"
    value: Optional[float] = None  # numeric value (if applicable)
    value_text: Optional[str] = None  # text value (e.g., enum label)
    unit: Optional[str] = None  # e.g., "%", "ms", "Hz"

    # Evidence
    modality: str = "UNKNOWN"  # TEXT, ENUM, NUMERIC, SLIDER_PIXEL, GRAPH_DERIVED, etc.
    status: ControlValueStatus = ControlValueStatus.OBSERVED
    confidence: float = 0.5  # [0, 1] extraction confidence

    # Provenance
    frame_source: Optional[str] = None  # which screenshot/frame
    roi_bbox: Optional[Dict[str, float]] = None  # ROI used for extraction
    evidence_hash: Optional[str] = None  # hash of evidence

    # Verification
    verification_status: ControlValueStatus = ControlValueStatus.OBSERVED
    verification_notes: Optional[str] = None
    claude_value: Optional[float] = None  # what Claude independently extracted
    claude_value_text: Optional[str] = None
    claude_confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "canonical_id": self.canonical_id,
            "value": self.value,
            "value_text": self.value_text,
            "unit": self.unit,
            "modality": self.modality,
            "status": self.status.value,
            "confidence": self.confidence,
            "frame_source": self.frame_source,
            "verification_status": self.verification_status.value,
            "verified": self.verification_status == ControlValueStatus.VERIFIED,
        }


@dataclass
class MatrixRoute:
    """A matrix modulation route in the reference state.

    amount_unit/amount_domain are mandatory once amount is set: two manifests
    built with different conventions (e.g. normalized [0,1] vs canonical
    [-100,+100]%) must never be compared as if the numbers meant the same
    thing. declares_canonical_representation() is the gate check for this.
    """
    route_id: str  # e.g., "matrix_row_1"
    source: str  # e.g., "Env 2"
    destination: str  # e.g., "Filter 1 Freq"
    amount: Optional[float] = None
    amount_unit: Optional[str] = None  # must be "%" for canonical representation
    amount_domain: Optional[Tuple[float, float]] = None  # must be (-100.0, 100.0)
    amount_source: Optional[str] = None  # e.g. TOOLTIP, SLIDER_PIXEL_CALIBRATION
    status: ControlValueStatus = ControlValueStatus.OBSERVED
    frame_source: Optional[str] = None
    verification_status: ControlValueStatus = ControlValueStatus.OBSERVED

    def declares_canonical_representation(self) -> bool:
        return self.amount_unit == "%" and self.amount_domain == (-100.0, 100.0)

    def to_dict(self) -> Dict:
        return {
            "route_id": self.route_id,
            "source": self.source,
            "destination": self.destination,
            "amount": self.amount,
            "amount_unit": self.amount_unit,
            "amount_domain": self.amount_domain,
            "amount_source": self.amount_source,
            "status": self.status.value,
            "verified": self.verification_status == ControlValueStatus.VERIFIED,
        }


@dataclass
class ReferenceStateManifest:
    """Complete extracted reference state."""
    episode_id: str  # e.g., "HEEGN1Xl5o4"
    source_description: str  # e.g., "Serum 2.0.21 tutorial video, step 3"
    serum_version: str = "2.0.21"  # frozen version

    # Evidence frames
    frames: List[str] = field(default_factory=list)  # list of frame sources

    # Extracted state
    controls: Dict[str, ControlValue] = field(default_factory=dict)  # keyed by canonical_id
    matrix_routes: List[MatrixRoute] = field(default_factory=list)
    topology: Dict[str, bool] = field(default_factory=dict)  # module enable states

    # Unresolved items
    unknown: List[Dict] = field(default_factory=list)  # items that couldn't be resolved

    # Verification
    verification_status: str = "UNVERIFIED"  # UNVERIFIED, VERIFIED, CONFLICT
    verification_conflicts: List[str] = field(default_factory=list)  # canonical_ids with conflicts
    unresolved_required: List[str] = field(default_factory=list)  # required items with insufficient evidence

    def add_control(self, control: ControlValue) -> None:
        """Add a control value to the manifest."""
        self.controls[control.canonical_id] = control

    def add_route(self, route: MatrixRoute) -> None:
        """Add a matrix route to the manifest."""
        self.matrix_routes.append(route)

    def add_unknown(self, item_description: str, reason: str) -> None:
        """Record an item that couldn't be resolved."""
        self.unknown.append({
            "description": item_description,
            "reason": reason,
        })

    def get_required_unresolved(self) -> List[str]:
        """Return list of required items with insufficient evidence."""
        unresolved = []
        for canonical_id, control in self.controls.items():
            if control.status in [
                ControlValueStatus.SOURCE_INSUFFICIENT,
                ControlValueStatus.IDENTITY_AMBIGUOUS,
                ControlValueStatus.UNRESOLVED_METADATA,
            ]:
                unresolved.append(canonical_id)
        return unresolved

    def is_complete_and_verified(self) -> bool:
        """Check if manifest is complete and all values are verified."""
        # No unresolved required values
        if self.get_required_unresolved():
            return False

        # No verification conflicts
        if self.verification_conflicts:
            return False

        # All controls either VERIFIED or NOT_APPLICABLE
        for control in self.controls.values():
            if control.verification_status not in [
                ControlValueStatus.VERIFIED,
                ControlValueStatus.NOT_VISIBLE_IN_FRAME,
            ]:
                return False

        return True

    def to_dict(self) -> Dict:
        return {
            "episode_id": self.episode_id,
            "source_description": self.source_description,
            "serum_version": self.serum_version,
            "frames": self.frames,
            "controls": {cid: c.to_dict() for cid, c in self.controls.items()},
            "matrix_routes": [r.to_dict() for r in self.matrix_routes],
            "topology": self.topology,
            "unknown": self.unknown,
            "verification_status": self.verification_status,
            "verification_conflicts": self.verification_conflicts,
            "unresolved_required": self.unresolved_required,
            "is_complete_and_verified": self.is_complete_and_verified(),
        }


class ReferenceStateReconstructor:
    """Universal reconstructor: reference evidence → complete state manifest."""

    def __init__(self, episode_id: str, serum_version: str = "2.0.21"):
        self.episode_id = episode_id
        self.serum_version = serum_version
        self.manifest = ReferenceStateManifest(
            episode_id=episode_id,
            source_description=f"Serum {serum_version} reference reconstruction",
            serum_version=serum_version,
        )

    def begin_reconstruction(self, source_description: str) -> None:
        """Start a new reconstruction with description."""
        self.manifest.source_description = source_description

    def add_frame_source(self, frame_path: str) -> None:
        """Record that a frame was used as evidence source."""
        if frame_path not in self.manifest.frames:
            self.manifest.frames.append(frame_path)

    def record_control(self, control: ControlValue) -> None:
        """Record an extracted control value."""
        self.manifest.add_control(control)

    def record_route(self, route: MatrixRoute) -> None:
        """Record a matrix route."""
        self.manifest.add_route(route)

    def record_topology(self, module_id: str, enabled: bool) -> None:
        """Record module enable state."""
        self.manifest.topology[module_id] = enabled

    def record_unknown(self, item_description: str, reason: str) -> None:
        """Record an unresolved item."""
        self.manifest.add_unknown(item_description, reason)

    def get_manifest(self) -> ReferenceStateManifest:
        """Return the current reconstruction manifest."""
        self.manifest.unresolved_required = self.manifest.get_required_unresolved()
        return self.manifest

    def validate_completeness(self) -> tuple:
        """Validate that all required items are resolved.

        Returns: (is_complete, unresolved_list)
        """
        unresolved = self.manifest.get_required_unresolved()
        return len(unresolved) == 0, unresolved

    def apply_claude_audit(self, claude_manifest: ReferenceStateManifest) -> None:
        """Compare system extraction against Claude's independent audit.

        For each control:
        - If Claude and system agree → VERIFIED
        - If Claude and system disagree → VERIFICATION_CONFLICT
        - If Claude sees but system didn't → IDENTITY_AMBIGUOUS or SOURCE_INSUFFICIENT
        """
        conflicts = []

        for canonical_id, system_control in self.manifest.controls.items():
            if canonical_id not in claude_manifest.controls:
                # Claude didn't extract this; mark for review
                system_control.verification_status = ControlValueStatus.OBSERVED_BUT_UNVERIFIED
                continue

            claude_control = claude_manifest.controls[canonical_id]

            # Compare values
            if system_control.value is not None and claude_control.value is not None:
                # Numeric comparison (allow small tolerance)
                tolerance = 0.01 * abs(system_control.value) if system_control.value != 0 else 0.01
                if abs(system_control.value - claude_control.value) > tolerance:
                    conflicts.append(canonical_id)
                    system_control.verification_status = ControlValueStatus.VERIFICATION_CONFLICT
                    system_control.claude_value = claude_control.value
                    system_control.verification_notes = f"System: {system_control.value}, Claude: {claude_control.value}"
                else:
                    system_control.verification_status = ControlValueStatus.VERIFIED
                    system_control.claude_value = claude_control.value
            elif system_control.value_text and claude_control.value_text:
                # Text comparison (enum, labels)
                if system_control.value_text.lower() == claude_control.value_text.lower():
                    system_control.verification_status = ControlValueStatus.VERIFIED
                    system_control.claude_value_text = claude_control.value_text
                else:
                    conflicts.append(canonical_id)
                    system_control.verification_status = ControlValueStatus.VERIFICATION_CONFLICT
                    system_control.claude_value_text = claude_control.value_text
                    system_control.verification_notes = f"System: {system_control.value_text}, Claude: {claude_control.value_text}"
            else:
                # One side has value, other doesn't
                system_control.verification_status = ControlValueStatus.OBSERVED_BUT_UNVERIFIED

        self.manifest.verification_conflicts = conflicts
        if conflicts:
            self.manifest.verification_status = "CONFLICT"
        else:
            self.manifest.verification_status = "VERIFIED"
