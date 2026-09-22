"""Phase 4.2: Verified State Adapter

Bridge: evidence layer → complete verified reference state

Integrates:
- SliderObservation (from Phase 3.5 calibration)
- ControlValue (Phase 4.1 manifest structure)
- ReferenceStateManifest (Phase 4.1)
- ExpectedInventory (Phase 3.2 completeness context)

Handles:
1. SliderObservation → ControlValue conversion
2. Full-state audit (controls + routes + topology)
3. Claude-only item detection (Claude saw more than system)
4. Visibility reconciliation (NOT_VISIBLE only when inventory allows)
5. Blind audit provenance tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import hashlib


class AuditMode(Enum):
    """How the audit was conducted."""
    DIRECT_VISUAL_INSPECTION = "DIRECT_VISUAL_INSPECTION"
    SYSTEM_EXTRACTION = "SYSTEM_EXTRACTION"
    MANUAL_MEASUREMENT = "MANUAL_MEASUREMENT"


@dataclass
class BlindAuditProvenance:
    """Tracking that Claude audit was genuinely blind."""
    observer: str  # "Claude", "System", "Manual"
    audit_mode: AuditMode
    source_frame_hashes: Dict[str, str] = field(default_factory=dict)  # frame_path → SHA256
    system_manifest_hidden: bool = True  # Were system values hidden from observer?
    audit_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    model_checkpoint: str = ""  # Which Claude version conducted audit

    def to_dict(self) -> Dict:
        return {
            "observer": self.observer,
            "audit_mode": self.audit_mode.value,
            "source_frame_hashes": self.source_frame_hashes,
            "system_manifest_hidden": self.system_manifest_hidden,
            "audit_timestamp": self.audit_timestamp,
            "model_checkpoint": self.model_checkpoint,
        }


@dataclass
class VerifiedReferenceState:
    """Final output: complete, audited, reconciled reference state.

    This is the only input to PresetSpec compilation.
    No unresolved required items.
    All controls audited and either verified or reconciled.
    """
    episode_id: str
    source_description: str
    serum_version: str = "2.0.21"

    # Complete state
    controls: Dict[str, "VerifiedControlValue"] = field(default_factory=dict)
    matrix_routes: Dict[str, "VerifiedMatrixRoute"] = field(default_factory=dict)
    topology: Dict[str, bool] = field(default_factory=dict)

    # Audit trail
    audit_provenance: Optional[BlindAuditProvenance] = None

    # Gate status
    is_verified: bool = False
    verification_conflicts: List[str] = field(default_factory=list)
    unresolved_required: List[str] = field(default_factory=list)
    claude_only_items: List[str] = field(default_factory=list)
    required_not_visible: List[str] = field(default_factory=list)

    def add_verified_control(self, control: "VerifiedControlValue") -> None:
        """Add a verified control to the state."""
        self.controls[control.canonical_id] = control

    def add_verified_route(self, route: "VerifiedMatrixRoute") -> None:
        """Add a verified matrix route."""
        self.matrix_routes[route.route_id] = route

    def pass_completeness_gate(self) -> bool:
        """Check if state passes complete verification gate.

        ALL of these must pass:
        1. unresolved_required == 0
        2. verification_conflicts == 0
        3. claude_only_items == 0
        4. required_not_visible == 0
        5. audit_provenance is present
        6. system_manifest_hidden == True
        7. audit_mode == DIRECT_VISUAL_INSPECTION
        8. Every control has agreement=True
        9. Every route has agreement=True
        """
        # Conditions 1-4: No unresolved/conflict items
        if self.unresolved_required:
            return False

        if self.verification_conflicts:
            return False

        if self.claude_only_items:
            return False

        if self.required_not_visible:
            return False

        # Condition 5-7: Provenance checks
        if not self.audit_provenance:
            return False

        if not self.audit_provenance.system_manifest_hidden:
            return False

        if self.audit_provenance.audit_mode != AuditMode.DIRECT_VISUAL_INSPECTION:
            return False

        # Conditions 8-9: Every represented item must have explicit agreement
        for control in self.controls.values():
            if not control.agreement:
                return False

        for route in self.matrix_routes.values():
            if not route.agreement:
                return False

        return True

    def to_dict(self) -> Dict:
        return {
            "episode_id": self.episode_id,
            "source_description": self.source_description,
            "serum_version": self.serum_version,
            "controls": {cid: c.to_dict() for cid, c in self.controls.items()},
            "matrix_routes": {rid: r.to_dict() for rid, r in self.matrix_routes.items()},
            "topology": self.topology,
            "is_verified": self.is_verified,
            "verification_conflicts": self.verification_conflicts,
            "unresolved_required": self.unresolved_required,
            "claude_only_items": self.claude_only_items,
            "required_not_visible": self.required_not_visible,
            "audit_provenance": self.audit_provenance.to_dict() if self.audit_provenance else None,
        }


@dataclass
class VerifiedControlValue:
    """A control value that has passed verification gates."""
    canonical_id: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None

    # Source
    modality: str = "UNKNOWN"
    frame_source: str = ""

    # Verification
    system_value: Optional[float] = None
    claude_value: Optional[float] = None
    agreement: bool = False  # system and claude agree

    # Provenance
    calibration_confidence: float = 0.0  # extraction confidence
    audit_confidence: float = 0.0  # verification confidence

    def to_dict(self) -> Dict:
        return {
            "canonical_id": self.canonical_id,
            "value": self.value,
            "value_text": self.value_text,
            "unit": self.unit,
            "modality": self.modality,
            "frame_source": self.frame_source,
            "agreement": self.agreement,
            "calibration_confidence": self.calibration_confidence,
            "audit_confidence": self.audit_confidence,
        }


CANONICAL_AMOUNT_UNIT = "%"
CANONICAL_AMOUNT_DOMAIN = (-100.0, 100.0)


@dataclass
class VerifiedMatrixRoute:
    """A matrix route that has passed verification gates."""
    route_id: str
    source: str
    destination: str
    amount: Optional[float] = None

    # Explicit representation declaration (required, not inferred)
    amount_unit: Optional[str] = None
    amount_domain: Optional[Tuple[float, float]] = None
    amount_source: Optional[str] = None  # e.g. SLIDER_PIXEL_CALIBRATION, TOOLTIP

    # Verification
    system_amount: Optional[float] = None
    claude_amount: Optional[float] = None
    agreement: bool = False

    def declares_canonical_representation(self) -> bool:
        """Reject routes that don't explicitly declare unit/domain.

        Prevents 0.067 (normalized) vs 6.7 (canonical %) from being
        silently compared as if equivalent.
        """
        return (
            self.amount_unit == CANONICAL_AMOUNT_UNIT
            and self.amount_domain == CANONICAL_AMOUNT_DOMAIN
        )

    def to_dict(self) -> Dict:
        return {
            "route_id": self.route_id,
            "source": self.source,
            "destination": self.destination,
            "amount": self.amount,
            "amount_unit": self.amount_unit,
            "amount_domain": self.amount_domain,
            "amount_source": self.amount_source,
            "agreement": self.agreement,
        }


class VerifiedStateBuilder:
    """Constructs VerifiedReferenceState from evidence + audit."""

    def __init__(self, episode_id: str, expected_inventory: Optional[Dict] = None):
        self.episode_id = episode_id
        self.expected_inventory = expected_inventory or {}  # ExpectedInventory context
        self.verified_state = VerifiedReferenceState(
            episode_id=episode_id,
            source_description=f"Reference reconstruction for {episode_id}",
        )

    def add_slider_observation(
        self,
        slider_obs,  # SliderObservation from Phase 3.5
        calibration_result,  # CalibrationResult
        domain_value: float,
    ) -> VerifiedControlValue:
        """Convert slider observation → verified control value.

        Takes calibration output and creates canonical ControlValue.
        Preserves row_detail to distinguish matrix.amount rows.
        """
        from calibration_model import SliderObservation

        # Preserve full row identity: matrix.amount[Env 2 → Filter 1 Freq]
        canonical_id = slider_obs.canonical_id
        if hasattr(slider_obs, 'row_detail') and slider_obs.row_detail:
            canonical_id = f"{canonical_id}[{slider_obs.row_detail}]"

        verified_control = VerifiedControlValue(
            canonical_id=canonical_id,
            value=domain_value,
            unit="%",  # Matrix amount is typically percent
            modality="SLIDER_PIXEL",
            frame_source=slider_obs.source_image,
            system_value=domain_value,
            calibration_confidence=slider_obs.confidence,
        )

        self.verified_state.add_verified_control(verified_control)
        return verified_control

    def add_verified_route(
        self,
        route_id: str,
        source: str,
        destination: str,
        amount: float,
        amount_unit: str,
        amount_domain: Tuple[float, float],
        amount_source: str,
        agreement: bool = True,
    ) -> VerifiedMatrixRoute:
        """Add a verified matrix route.

        amount_unit/amount_domain/amount_source are mandatory (no defaults):
        callers must state the representation explicitly rather than relying
        on an assumed convention.
        """
        verified_route = VerifiedMatrixRoute(
            route_id=route_id,
            source=source,
            destination=destination,
            amount=amount,
            amount_unit=amount_unit,
            amount_domain=amount_domain,
            amount_source=amount_source,
            system_amount=amount,
            agreement=agreement,
        )

        self.verified_state.add_verified_route(verified_route)
        return verified_route

    def detect_claude_only_items(
        self,
        system_keys: set,  # system manifest keys
        claude_keys: set,  # Claude audit keys
    ) -> List[str]:
        """Detect items Claude observed that system missed.

        Returns: list of canonical_ids only in Claude's audit
        """
        claude_only = claude_keys - system_keys
        return list(claude_only)

    def audit_full_state(
        self,
        system_manifest,  # ReferenceStateManifest
        claude_manifest,  # ReferenceStateManifest (Claude's independent audit)
    ) -> Tuple[bool, List[str]]:
        """Full state audit: controls + routes + topology (bidirectional).

        Returns: (all_agree, conflicts_list)
        """
        conflicts = []

        # 1. Bidirectional control audit
        system_cids = set(system_manifest.controls.keys())
        claude_cids = set(claude_manifest.controls.keys())

        # System → Claude
        for cid in system_cids:
            if cid not in claude_cids:
                conflicts.append(f"CLAUDE_MISSING_CONTROL: {cid}")
                continue

            system_ctrl = system_manifest.controls[cid]
            claude_ctrl = claude_manifest.controls[cid]

            # Numeric comparison
            if system_ctrl.value is not None and claude_ctrl.value is not None:
                tolerance = 0.01 * abs(system_ctrl.value) if system_ctrl.value != 0 else 0.01
                if abs(system_ctrl.value - claude_ctrl.value) > tolerance:
                    conflicts.append(f"CONTROL_MISMATCH: {cid}")
                else:
                    # Agreement: update verified state
                    if cid in self.verified_state.controls:
                        self.verified_state.controls[cid].agreement = True
                        self.verified_state.controls[cid].claude_value = claude_ctrl.value
                        self.verified_state.controls[cid].audit_confidence = getattr(
                            claude_ctrl, 'confidence', 0.0
                        )

            # Text comparison
            elif system_ctrl.value_text and claude_ctrl.value_text:
                if system_ctrl.value_text.lower() != claude_ctrl.value_text.lower():
                    conflicts.append(f"CONTROL_TEXT_MISMATCH: {cid}")
                else:
                    # Agreement: update verified state
                    if cid in self.verified_state.controls:
                        self.verified_state.controls[cid].agreement = True
                        self.verified_state.controls[cid].audit_confidence = getattr(
                            claude_ctrl, 'confidence', 0.0
                        )

        # Claude → System (claude_only items)
        claude_only_controls = claude_cids - system_cids
        for cid in claude_only_controls:
            conflicts.append(f"CLAUDE_ONLY_CONTROL: {cid}")

        # 2. Bidirectional route audit
        system_routes = {r.route_id: r for r in system_manifest.matrix_routes}
        claude_routes = {r.route_id: r for r in claude_manifest.matrix_routes}
        system_route_ids = set(system_routes.keys())
        claude_route_ids = set(claude_routes.keys())

        # System → Claude
        for route_id in system_route_ids:
            if route_id not in claude_route_ids:
                conflicts.append(f"CLAUDE_MISSING_ROUTE: {route_id}")
                continue

            system_route = system_routes[route_id]
            claude_route = claude_routes[route_id]

            # Verify identity (source and destination)
            if system_route.source != claude_route.source:
                conflicts.append(f"ROUTE_SOURCE_MISMATCH: {route_id}")
            if system_route.destination != claude_route.destination:
                conflicts.append(f"ROUTE_DESTINATION_MISMATCH: {route_id}")

            # Reject undeclared/non-canonical representation BEFORE comparing
            # numbers. Without this, 0.067 (normalized) and 6.7 (canonical %)
            # would silently compare as if the same unit.
            if not system_route.declares_canonical_representation():
                conflicts.append(f"AMOUNT_REPRESENTATION_UNDECLARED_SYSTEM: {route_id}")
                continue
            if not claude_route.declares_canonical_representation():
                conflicts.append(f"AMOUNT_REPRESENTATION_UNDECLARED_CLAUDE: {route_id}")
                continue

            # Verify amount (both in canonical [-100, +100]% domain)
            # Tolerance: ±5 percentage points
            if system_route.amount is None or claude_route.amount is None:
                conflicts.append(f"ROUTE_UNVERIFIED: {route_id}")
            elif abs(system_route.amount - claude_route.amount) > 5.0:
                conflicts.append(f"ROUTE_MISMATCH: {route_id}")
            else:
                # Agreement: update verified state
                if route_id in self.verified_state.matrix_routes:
                    self.verified_state.matrix_routes[route_id].agreement = True
                    self.verified_state.matrix_routes[route_id].claude_amount = claude_route.amount

        # Claude → System (claude_only routes)
        claude_only_routes = claude_route_ids - system_route_ids
        for route_id in claude_only_routes:
            conflicts.append(f"CLAUDE_ONLY_ROUTE: {route_id}")

        # 3. Bidirectional topology audit
        system_topology_ids = set(system_manifest.topology.keys())
        claude_topology_ids = set(claude_manifest.topology.keys())

        # System → Claude
        for module_id in system_topology_ids:
            if module_id not in claude_topology_ids:
                conflicts.append(f"CLAUDE_MISSING_TOPOLOGY: {module_id}")
                continue

            if system_manifest.topology[module_id] != claude_manifest.topology[module_id]:
                conflicts.append(f"TOPOLOGY_MISMATCH: {module_id}")

        # Claude → System (claude_only topology)
        claude_only_topology = claude_topology_ids - system_topology_ids
        for module_id in claude_only_topology:
            conflicts.append(f"CLAUDE_ONLY_TOPOLOGY: {module_id}")

        # Update verified state
        self.verified_state.verification_conflicts = conflicts
        self.verified_state.claude_only_items = [
            c for c in conflicts if "CLAUDE_ONLY_" in c
        ]

        return len(conflicts) == 0, conflicts

    def validate_required_visibility(self) -> List[str]:
        """Check that required items are visible and have usable evidence.

        Uses ExpectedInventory to determine which items are genuinely required.
        Returns: list of required items with insufficient visibility/evidence
        """
        invalid = []

        # Build required set from ExpectedInventory
        required_ids = set()
        for canonical_id, expected in self.expected_inventory.items():
            if hasattr(expected, 'applicability') and expected.applicability:
                if hasattr(expected, 'visibility_requirement'):
                    if expected.visibility_requirement != "OPTIONAL":
                        required_ids.add(canonical_id)
                else:
                    # No visibility_requirement means required by default
                    required_ids.add(canonical_id)

        # Determine what was observed
        observed_ids = (
            set(self.verified_state.controls.keys())
            | set(self.verified_state.matrix_routes.keys())
            | set(self.verified_state.topology.keys())
        )

        # Check each required item
        for expected_id in required_ids:
            if expected_id not in observed_ids:
                # Required but not observed at all
                invalid.append(expected_id)
            elif expected_id in self.verified_state.controls:
                # Control must have a value
                control = self.verified_state.controls[expected_id]
                if control.value is None and control.value_text is None:
                    invalid.append(expected_id)
            elif expected_id in self.verified_state.matrix_routes:
                # Route must have an amount
                route = self.verified_state.matrix_routes[expected_id]
                if route.amount is None:
                    invalid.append(expected_id)

        self.verified_state.required_not_visible = sorted(set(invalid))
        return invalid

    def finalize(
        self,
        audit_provenance: Optional[BlindAuditProvenance] = None,
    ) -> VerifiedReferenceState:
        """Finalize the verified state and check completion gate.

        Requires explicit provenance; does not manufacture SYSTEM audit.
        """
        # Provenance is mandatory
        self.verified_state.audit_provenance = audit_provenance

        # Validate required visibility against ExpectedInventory
        self.validate_required_visibility()

        # Check completeness gate
        self.verified_state.is_verified = self.verified_state.pass_completeness_gate()

        return self.verified_state
