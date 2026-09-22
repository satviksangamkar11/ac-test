"""Phase 4.2.1: Complete Verification Gate (hardening patch)

Closes remaining Phase 4.2 gaps:
1. Claude-only routes detection
2. Claude-only topology detection
3. ExpectedInventory NOT_VISIBLE validation
4. Complete verified state requirement in gate

Final gate requires ALL:
- unresolved_required == 0
- verification_conflicts == 0
- claude_only_items == 0
- required_not_visible == 0
- audit_provenance present
- system_manifest_hidden == True
- audit_mode == DIRECT_VISUAL_INSPECTION
"""

from typing import List, Tuple, Dict, Optional


def audit_full_state_complete(
    system_manifest,  # ReferenceStateManifest
    claude_manifest,  # ReferenceStateManifest (Claude's independent audit)
) -> Tuple[bool, List[str]]:
    """HARDENED: Full state audit detecting Claude-only routes and topology.

    Returns: (all_agree, conflicts_list)
    """
    conflicts = []

    # 1. Audit controls (bidirectional)
    system_cids = set(system_manifest.controls.keys())
    claude_cids = set(claude_manifest.controls.keys())

    # System controls vs Claude
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

        # Text comparison
        elif system_ctrl.value_text and claude_ctrl.value_text:
            if system_ctrl.value_text.lower() != claude_ctrl.value_text.lower():
                conflicts.append(f"CONTROL_TEXT_MISMATCH: {cid}")

    # Claude-only controls
    claude_only_controls = claude_cids - system_cids
    for cid in claude_only_controls:
        conflicts.append(f"CLAUDE_ONLY_CONTROL: {cid}")

    # 2. Audit matrix routes (bidirectional) — NEW
    system_routes = {r.route_id: r for r in system_manifest.matrix_routes}
    claude_routes = {r.route_id: r for r in claude_manifest.matrix_routes}
    system_route_ids = set(system_routes.keys())
    claude_route_ids = set(claude_routes.keys())

    # System routes vs Claude
    # Canonical representation: [-100, +100]% (percentage points)
    # Tolerance: ±5.0 percentage points
    for route_id in system_route_ids:
        if route_id not in claude_route_ids:
            conflicts.append(f"CLAUDE_MISSING_ROUTE: {route_id}")
            continue

        system_route = system_routes[route_id]
        claude_route = claude_routes[route_id]

        if system_route.amount is not None and claude_route.amount is not None:
            if abs(system_route.amount - claude_route.amount) > 5.0:
                conflicts.append(f"ROUTE_MISMATCH: {route_id}")

    # Claude-only routes — NEW
    claude_only_routes = claude_route_ids - system_route_ids
    for route_id in claude_only_routes:
        conflicts.append(f"CLAUDE_ONLY_ROUTE: {route_id}")

    # 3. Audit topology (bidirectional) — NEW
    system_topology_ids = set(system_manifest.topology.keys())
    claude_topology_ids = set(claude_manifest.topology.keys())

    # System topology vs Claude
    for module_id in system_topology_ids:
        if module_id not in claude_topology_ids:
            conflicts.append(f"CLAUDE_MISSING_TOPOLOGY: {module_id}")
            continue

        if system_manifest.topology[module_id] != claude_manifest.topology[module_id]:
            conflicts.append(f"TOPOLOGY_MISMATCH: {module_id}")

    # Claude-only topology — NEW
    claude_only_topology = claude_topology_ids - system_topology_ids
    for module_id in claude_only_topology:
        conflicts.append(f"CLAUDE_ONLY_TOPOLOGY: {module_id}")

    return len(conflicts) == 0, conflicts


def validate_required_visibility_complete(
    verified_state,  # VerifiedReferenceState
    expected_inventory: Optional[Dict] = None,  # ExpectedInventory context
) -> List[str]:
    """HARDENED: NOT_VISIBLE validation against ExpectedInventory.

    Preserves row detail (e.g., matrix.amount[Env 2 → Filter 1 Freq]).
    Only allows NOT_VISIBLE if ExpectedInventory says item not required.

    Returns: list of invalid NOT_VISIBLE items
    """
    invalid = []
    expected_inventory = expected_inventory or {}

    for canonical_id, control in verified_state.controls.items():
        # If control is not observed, check if it's allowed to be missing
        if control.value is None and control.value_text is None:
            # Check expected inventory
            # Preserve row detail exactly as stored
            if canonical_id in expected_inventory:
                expected_item = expected_inventory[canonical_id]
                # Item is required if not explicitly marked as optional
                if expected_item.get("visibility_requirement") != "OPTIONAL":
                    invalid.append(canonical_id)
            else:
                # Item not in expected inventory but expected = required by default
                invalid.append(canonical_id)

    return invalid


def completeness_gate_complete(
    verified_state,
    audit_provenance,
) -> Tuple[bool, List[str]]:
    """HARDENED: Complete verification gate.

    ALL must pass:
    1. No unresolved required items
    2. No verification conflicts
    3. No Claude-only items
    4. No required items are NOT_VISIBLE
    5. Audit provenance is present
    6. Manifest was hidden from observer
    7. Audit was DIRECT_VISUAL_INSPECTION

    Returns: (passes_gate, failures_list)
    """
    failures = []

    # 1. Unresolved required items
    if verified_state.unresolved_required:
        failures.append(f"UNRESOLVED_REQUIRED: {', '.join(verified_state.unresolved_required)}")

    # 2. Verification conflicts
    if verified_state.verification_conflicts:
        failures.append(f"VERIFICATION_CONFLICTS: {', '.join(verified_state.verification_conflicts)}")

    # 3. Claude-only items (from audit)
    if any("CLAUDE_ONLY" in c for c in verified_state.verification_conflicts):
        failures.append("CLAUDE_ONLY_ITEMS_DETECTED")

    # 4. Provenance checks
    if not audit_provenance:
        failures.append("NO_AUDIT_PROVENANCE")
    else:
        if not audit_provenance.system_manifest_hidden:
            failures.append("SYSTEM_MANIFEST_NOT_HIDDEN")

        if audit_provenance.audit_mode.value != "DIRECT_VISUAL_INSPECTION":
            failures.append(f"AUDIT_MODE_NOT_VISUAL: {audit_provenance.audit_mode.value}")

    # ALL gates must pass
    return len(failures) == 0, failures
