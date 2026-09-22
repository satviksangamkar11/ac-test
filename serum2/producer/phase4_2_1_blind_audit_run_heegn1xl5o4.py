"""Phase 4.2.1: Blind audit run — HEEGN1Xl5o4 step3_04m35s_matrix_mod_routes.jpg

System manifest: pixel-calibrated amounts computed in this session (rough
track-boundary estimate, treated the widget as a rotary knob).

Claude manifest: produced by an independently spawned subagent with NO
access to this conversation or the system numbers — given only the image
file path. That agent identified the widget as a horizontal bipolar slider
and located the true 0% reference using the empty/unassigned rows' neutral
handle position, then measured each populated route's offset from that
reference as a fraction of the half-track-width.

Route identities: both sides found the same 4 populated routes independently.
Route amounts: run through the hardened gate below.
"""

from reference_state_reconstructor import (
    ReferenceStateReconstructor,
    MatrixRoute,
    ControlValueStatus,
)
from phase4_2_verified_state_adapter import (
    VerifiedStateBuilder,
    BlindAuditProvenance,
    AuditMode,
)

ROUTES = [
    ("matrix_row1", "LFO 1", "A Fine"),
    ("matrix_row2", "LFO 1", "B Fine"),
    ("matrix_row3", "Env 3", "Noise Level"),
    ("matrix_row4", "Env 2", "Filter 1 Freq"),
]

# System: pixel-calibrated in this session (rotary-knob assumption)
SYSTEM_AMOUNTS = {
    "matrix_row1": 6.7,
    "matrix_row2": -12.0,
    "matrix_row3": -33.3,
    "matrix_row4": 1.3,
}

# Claude: independent blind subagent audit (midpoint of stated confidence range)
CLAUDE_AMOUNTS = {
    "matrix_row1": 1.5,    # stated range 0% to +3%
    "matrix_row2": 1.5,    # stated range 0% to +3%
    "matrix_row3": 34.0,   # stated range +25% to +40%
    "matrix_row4": 71.0,   # stated range +60% to +80%
}


def build_manifest(amounts: dict, source_label: str):
    recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    for route_id, source, destination in ROUTES:
        recon.record_route(MatrixRoute(
            route_id=route_id,
            source=source,
            destination=destination,
            amount=amounts[route_id],
            amount_unit="%",
            amount_domain=(-100.0, 100.0),
            amount_source=source_label,
            status=ControlValueStatus.OBSERVED,
        ))
    return recon.get_manifest()


def run():
    system_manifest = build_manifest(SYSTEM_AMOUNTS, "SLIDER_PIXEL_CALIBRATION")
    claude_manifest = build_manifest(CLAUDE_AMOUNTS, "SLIDER_PIXEL_CALIBRATION_BLIND_SUBAGENT")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    for route_id, source, destination in ROUTES:
        builder.add_verified_route(
            route_id=route_id,
            source=source,
            destination=destination,
            amount=SYSTEM_AMOUNTS[route_id],
            amount_unit="%",
            amount_domain=(-100.0, 100.0),
            amount_source="SLIDER_PIXEL_CALIBRATION",
            agreement=False,
        )

    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    provenance = BlindAuditProvenance(
        observer="Claude (isolated subagent, no conversation memory)",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
    )
    verified_state = builder.finalize(audit_provenance=provenance)

    print("=" * 70)
    print("BLIND AUDIT RESULT: HEEGN1Xl5o4 step3_04m35s_matrix_mod_routes.jpg")
    print("=" * 70)
    print("\nRoute identity agreement: YES (all 4 routes found independently by both sides)\n")
    print(f"{'Route':30} {'System %':>10} {'Claude %':>10} {'Diff':>8}  Result")
    print("-" * 70)
    for route_id, source, destination in ROUTES:
        s = SYSTEM_AMOUNTS[route_id]
        c = CLAUDE_AMOUNTS[route_id]
        diff = abs(s - c)
        result = "FAIL" if diff > 5.0 else "PASS"
        print(f"{source + ' -> ' + destination:30} {s:>+10.1f} {c:>+10.1f} {diff:>8.1f}  {result}")

    print(f"\nall_agree = {all_agree}")
    print(f"conflicts = {conflicts}")
    print(f"\nGate result: is_verified = {verified_state.is_verified}")
    print(f"\nVERDICT: {'PASS - Phase 4.2.1 fully closed' if verified_state.is_verified else 'FAIL - keep Phase 4.2.1 open, correct the discrepancy'}")

    return verified_state


if __name__ == "__main__":
    run()
