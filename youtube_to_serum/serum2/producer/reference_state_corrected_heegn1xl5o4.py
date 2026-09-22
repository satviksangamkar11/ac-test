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

ROUTE AMOUNTS (v3 detector pixel-calibration, January 2025):
Domain: [-100, +100]% (Matrix Amount canonical representation)
Unit: % (percentage points)
Tolerance: ±5.0 (must agree within 5 percentage points for gate to pass)
Source: SLIDER_PIXEL_CALIBRATION (structural rail architecture v3)

- LFO 1 → A Fine:       +2.4 %   (v3 rail [198-323], handle 262)
- LFO 1 → B Fine:       +2.4 %   (v3 rail [198-323], handle 262)
- Env 3 → Noise Level:  +34.4 %  (v3 rail [198-323], handle 282)
- Env 2 → Filter 1 Freq: +71.2 % (v3 rail [198-323], handle 305)

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

# Corrected route definitions — v3 detector calibration
# All amounts in canonical domain: [-100, +100] % (percentage points)
# All amounts from production v3 detector (structural rail [198-323], handle detection)
CORRECTED_ROUTES = [
    {
        "route_id": "LFO 1 → A Fine",
        "source": "LFO 1",
        "destination": "Osc A Fine",
        "amount": 2.4,  # v3: rail [198-323], handle 262, normalized 0.512, amount +2.4%
        "amount_unit": "%",
        "amount_domain": (-100.0, 100.0),
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "v3 detector: structural rail 198-323, handle pixel 262. GenericSliderCalibration: normalized=(262-198)/125=0.512, amount=0.512*200-100=+2.4%",
        "geometry_provenance": "v3_structural_rail_architecture",
        "reference_row": 280,
    },
    {
        "route_id": "LFO 1 → B Fine",
        "source": "LFO 1",
        "destination": "Osc B Fine",
        "amount": 2.4,  # v3: rail [198-323], handle 262 (same as row 1)
        "amount_unit": "%",
        "amount_domain": (-100.0, 100.0),
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "v3 detector: structural rail 198-323, handle pixel 262. GenericSliderCalibration: +2.4%",
        "geometry_provenance": "v3_structural_rail_architecture",
        "reference_row": 280,
    },
    {
        "route_id": "Env 3 → Noise Level",
        "source": "Env 3",
        "destination": "Noise Level",
        "amount": 34.4,  # v3: rail [198-323], handle 282
        "amount_unit": "%",
        "amount_domain": (-100.0, 100.0),
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "v3 detector: structural rail 198-323, handle pixel 282. GenericSliderCalibration: normalized=(282-198)/125=0.672, amount=0.672*200-100=+34.4%",
        "geometry_provenance": "v3_structural_rail_architecture",
        "reference_row": 280,
    },
    {
        "route_id": "Env 2 → Filter 1 Freq",
        "source": "Env 2",
        "destination": "Filter 1 Freq",
        "amount": 71.2,  # v3: rail [198-323], handle 305
        "amount_unit": "%",
        "amount_domain": (-100.0, 100.0),
        "amount_source": "SLIDER_PIXEL_CALIBRATION",
        "calibration_note": "v3 detector: structural rail 198-323, handle pixel 305. GenericSliderCalibration: normalized=(305-198)/125=0.856, amount=0.856*200-100=+71.2%",
        "geometry_provenance": "v3_structural_rail_architecture",
        "reference_row": 280,
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
