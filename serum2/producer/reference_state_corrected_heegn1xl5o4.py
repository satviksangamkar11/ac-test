"""
Phase 4.2.1 Corrected Reference State: HEEGN1Xl5o4 (step 3, 04:35)

PROVISIONAL STATUS: Route identities independently verified.
                   Route amounts pending blind-audit comparison.

Evidence source: step3_04m35s_matrix_mod_routes.jpg (visual inspection)
Frame timestamp: ~00:04:35 of reference episode

ROUTE IDENTITIES (independently verified by Claude visual audit):
✓ LFO 1 → A Fine
✓ LFO 1 → B Fine
✓ Env 3 → Noise Level
✓ Env 2 → Filter 1 Freq

ROUTE AMOUNTS (pixel-calibrated, NOT directly observed):
Domain: [-100, +100]% (Matrix Amount canonical representation)
Unit: % (percentage points)
Tolerance: ±5.0 (must agree within 5 percentage points for gate to pass)
Source: SLIDER_PIXEL_CALIBRATION (not tooltip-observed)

- LFO 1 → A Fine:       +6.7 %   (calibrated from pixel position 375)
- LFO 1 → B Fine:       -12.0 %  (calibrated from pixel position 368)
- Env 3 → Noise Level:  -33.3 %  (calibrated from pixel position 360)
- Env 2 → Filter 1 Freq: +1.3 %  (calibrated from pixel position 373)

GATE STATUS (before blind verification):
- unresolved_required:     0 (all four routes represented)
- verification_conflicts:  PENDING (awaiting amount comparison)
- claude_only_items:       0 (no extra routes in independent audit)
- required_not_visible:    0 (all four routes visible)
- blind_provenance:        READY (would use DIRECT_VISUAL_INSPECTION)
- route_identity_agreement: YES (system and claude both found 4 routes)
- route_amount_agreement:   PENDING (need numerical tolerance check)

NOTES:
1. The earlier fixture (two routes) was incorrect for this frame.
2. Amounts are fallback pixel calibration (no numeric tooltips visible in image).
3. Gate passes only when amounts also agree within tolerance (±5% tolerance).
4. This checkpoint is formally locked but functionally PROVISIONAL until
   system and independent amounts pass within-tolerance comparison.

NEXT: Run hardened gate with corrected manifests and verify amount agreement.
      Do not advance to Phase 4.3 until amounts pass verification.
"""

# Corrected route definitions
# All amounts in canonical domain: [-100, +100] % (percentage points)
CORRECTED_ROUTES = [
    {
        "route_id": "matrix_row1",
        "source": "LFO 1",
        "destination": "A Fine",
        "amount": 6.7,  # canonical domain: +6.7 percentage points
        "amount_unit": "%",
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "Knob pixel 375 of 75px track (53% right). Formula: -100 + (normalized * 200)",
    },
    {
        "route_id": "matrix_row2",
        "source": "LFO 1",
        "destination": "B Fine",
        "amount": -12.0,  # canonical domain: -12.0 percentage points
        "amount_unit": "%",
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "Knob pixel 368 of 75px track (44% right).",
    },
    {
        "route_id": "matrix_row3",
        "source": "Env 3",
        "destination": "Noise Level",
        "amount": -33.3,  # canonical domain: -33.3 percentage points
        "amount_unit": "%",
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "Knob pixel 360 of 75px track (33% right).",
    },
    {
        "route_id": "matrix_row4",
        "source": "Env 2",
        "destination": "Filter 1 Freq",
        "amount": 1.3,  # canonical domain: +1.3 percentage points
        "amount_unit": "%",
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "Knob pixel 373 of 75px track (51% right).",
    },
]

VERIFICATION_CONTRACT = {
    "episode_id": "HEEGN1Xl5o4",
    "frame": "step3_04m35s_matrix_mod_routes.jpg",
    "timestamp": "~00:04:35",

    # Amount verification: both system and Claude manifests must use same representation
    "amount_domain": "[-100, +100] % (Matrix Amount canonical)",
    "amount_unit": "%",
    "amount_tolerance": 5.0,  # ±5 percentage points

    # Gate pass condition
    "gate_condition": (
        "Gate passes when:\n"
        "1. Route identities match (VERIFIED)\n"
        "2. Route amounts agree within ±5.0 percentage points\n"
        "3. All other completeness gates pass (no conflicts, no claude_only, etc.)"
    ),
}


def get_corrected_reference_state():
    """
    Returns the corrected reference state for HEEGN1Xl5o4 step 3.

    Use with phase4_2_verified_state_adapter.VerifiedStateBuilder
    to create the system manifest.

    Amounts are pixel-calibrated in canonical [-100, +100]% domain.
    Both system and Claude manifests must use the same representation
    for blind-audit comparison to be meaningful.
    """
    return {
        "episode_id": "HEEGN1Xl5o4",
        "frame": "step3_04m35s_matrix_mod_routes.jpg",
        "timestamp": "~00:04:35",
        "routes": CORRECTED_ROUTES,
        "status": "PROVISIONAL_ROUTE_IDENTITIES_VERIFIED_AMOUNTS_PENDING",
        "verification_contract": VERIFICATION_CONTRACT,
    }


if __name__ == "__main__":
    state = get_corrected_reference_state()
    print("Corrected reference state loaded.")
    print(f"Episode: {state['episode_id']}")
    print(f"Frame: {state['frame']}")
    print(f"Routes: {len(state['routes'])}")
    for r in state['routes']:
        print(f"  {r['source']:6} → {r['destination']:15} "
              f"(amount={r['amount']:+.3f}, source={r['amount_source']})")
