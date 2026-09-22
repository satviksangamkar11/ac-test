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
- LFO 1 → A Fine:       +6.7%   (amount_source: SLIDER_PIXEL_CALIBRATION)
- LFO 1 → B Fine:       -12.0%  (amount_source: SLIDER_PIXEL_CALIBRATION)
- Env 3 → Noise Level:  -33.3%  (amount_source: SLIDER_PIXEL_CALIBRATION)
- Env 2 → Filter 1 Freq: +1.3%  (amount_source: SLIDER_PIXEL_CALIBRATION)

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
CORRECTED_ROUTES = [
    {
        "route_id": "matrix_row1",
        "source": "LFO 1",
        "destination": "A Fine",
        "amount": 0.067,  # +6.7% normalized
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "note": "Knob position ~53% right of track. Bipolar domain [-100, +100]%.",
    },
    {
        "route_id": "matrix_row2",
        "source": "LFO 1",
        "destination": "B Fine",
        "amount": -0.120,  # -12.0% normalized
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "note": "Knob position ~44% right of track.",
    },
    {
        "route_id": "matrix_row3",
        "source": "Env 3",
        "destination": "Noise Level",
        "amount": -0.333,  # -33.3% normalized
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "note": "Knob position ~33% right of track.",
    },
    {
        "route_id": "matrix_row4",
        "source": "Env 2",
        "destination": "Filter 1 Freq",
        "amount": 0.013,  # +1.3% normalized
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "note": "Knob position ~51% right of track.",
    },
]

def get_corrected_reference_state():
    """
    Returns the corrected reference state for HEEGN1Xl5o4 step 3.

    Use with phase4_2_verified_state_adapter.VerifiedStateBuilder
    to create the system manifest.

    Amounts are pixel-calibrated and require blind-audit verification.
    """
    return {
        "episode_id": "HEEGN1Xl5o4",
        "frame": "step3_04m35s_matrix_mod_routes.jpg",
        "timestamp": "~00:04:35",
        "routes": CORRECTED_ROUTES,
        "status": "PROVISIONAL_ROUTE_IDENTITIES_VERIFIED_AMOUNTS_PENDING",
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
