"""Reproducible pixel-level Matrix Amount calibration.

Takes user-verified Matrix ROI coordinates from visual inspection
and produces exact pixel measurements + GenericSliderCalibration outputs.

MEASUREMENT CONTRACT:
  Original 1280×720 image
       ↓
  Fixed Matrix ROI (user-verified from visual inspection)
       ↓
  Per-row y coordinate
       ↓
  Track left/right detection
       ↓
  Handle center detection
       ↓
  Raw pixel coordinates
       ↓
  GenericSliderCalibration
       ↓
  MatrixAmountDomain [-100,+100] %

OUTPUT: per-route raw evidence for comparison against blind audit
"""

import numpy as np
from PIL import Image
from typing import Tuple, Optional

# USER-VERIFIED MATRIX ROI (from visual inspection of step3_04m35s_matrix_mod_routes.jpg)
# These values should be filled in based on your visual inspection
MATRIX_ROI = {
    'x_min': None,  # Left edge of Matrix Amount column (user fills from inspection)
    'x_max': None,  # Right edge of Matrix Amount column
    'y_min': None,  # Top of first populated row
    'y_max': None,  # Bottom of last populated row
}

# Populated routes in the Matrix (row_y values to be determined from inspection)
ROUTES = [
    {'name': 'LFO 1 → A Fine', 'row_y': None, 'source': 'LFO 1', 'dest': 'A Fine'},
    {'name': 'LFO 1 → B Fine', 'row_y': None, 'source': 'LFO 1', 'dest': 'B Fine'},
    {'name': 'Env 3 → Noise Level', 'row_y': None, 'source': 'Env 3', 'dest': 'Noise Level'},
    {'name': 'Env 2 → Filter 1 Freq', 'row_y': None, 'source': 'Env 2', 'dest': 'Filter 1 Freq'},
]

# Empty/unassigned rows (for zero-reference verification)
EMPTY_ROWS = [
    {'name': 'Empty row (control)', 'row_y': None},
]


def find_track_plateau_in_row(
    arr: np.ndarray,
    row_y: int,
    x_search_range: Tuple[int, int],
) -> Tuple[Optional[int], Optional[int]]:
    """Find track left/right edges by detecting the grey plateau region.

    Returns: (track_left_x, track_right_x) or (None, None) if not found
    """
    line = arr[row_y, x_search_range[0]:x_search_range[1], :]

    # The track plateau is a specific shade of grey
    # Measure it by looking for sustained mid-tone pixels
    # (not too dark like background, not too bright like text/handle)

    plateau_mask = []
    for x_idx in range(line.shape[0]):
        r, g, b = line[x_idx, :3]
        # Track is typically in the range of moderate greys
        # Looking for ~(50-90, 70-110, 80-120) range roughly
        is_plateau = (40 <= r <= 120 and 60 <= g <= 130 and 70 <= b <= 140)
        plateau_mask.append(is_plateau)

    plateau_mask = np.array(plateau_mask)
    true_indices = np.where(plateau_mask)[0]

    if len(true_indices) > 0:
        left_x = x_search_range[0] + true_indices[0]
        right_x = x_search_range[0] + true_indices[-1]
        return left_x, right_x

    return None, None


def find_handle_center_in_row(
    arr: np.ndarray,
    row_y: int,
    x_search_range: Tuple[int, int],
    y_offset_above: int = 5,
) -> Optional[int]:
    """Find the handle center by detecting the brightest pixel in a band above the track.

    Returns: handle_x or None if not found
    """
    if row_y < y_offset_above:
        return None

    y_band = arr[row_y - y_offset_above:row_y, x_search_range[0]:x_search_range[1], :]

    # Average brightness across the band
    brightness = np.mean(y_band, axis=(0, 2))

    if brightness.shape[0] > 0:
        brightest_idx = np.argmax(brightness)
        handle_x = x_search_range[0] + brightest_idx
        return handle_x

    return None


def generic_slider_calibration(
    observed_position_px: float,
    left_px: float,
    right_px: float,
) -> float:
    """Apply GenericSliderCalibration formula.

    Returns: normalized value in [0, 1]
    """
    normalized = (observed_position_px - left_px) / (right_px - left_px)
    return normalized


def matrix_amount_domain(normalized: float) -> float:
    """Map normalized [0, 1] to Matrix Amount domain [-100, +100] %.

    Returns: amount in percentage
    """
    return normalized * 200.0 - 100.0


def calibrate_routes():
    """Main calibration pipeline."""

    # Validation: check that ROI is set
    if MATRIX_ROI['x_min'] is None or MATRIX_ROI['x_max'] is None:
        print("ERROR: MATRIX_ROI not set. User must provide visual inspection coordinates.")
        print("Set MATRIX_ROI['x_min'], MATRIX_ROI['x_max'], and route row_y values before running.")
        return

    if not any(r['row_y'] is not None for r in ROUTES):
        print("ERROR: No route row_y coordinates set. User must provide from visual inspection.")
        return

    # Load image
    image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
    img = Image.open(image_path)
    arr = np.array(img)

    x_search_range = (MATRIX_ROI['x_min'], MATRIX_ROI['x_max'])

    print("="*80)
    print("MATRIX AMOUNT CALIBRATION — RAW PIXEL MEASUREMENTS")
    print("="*80)
    print(f"\nMatrix ROI: x={MATRIX_ROI['x_min']}–{MATRIX_ROI['x_max']}")
    print(f"Image size: {arr.shape}")

    measurements = {}

    # Measure each populated route
    print("\n" + "-"*80)
    print("POPULATED ROUTES")
    print("-"*80)

    for route in ROUTES:
        if route['row_y'] is None:
            continue

        row_y = route['row_y']
        name = route['name']

        # Detect track geometry
        left_x, right_x = find_track_plateau_in_row(arr, row_y, x_search_range)

        if left_x is None:
            print(f"\n{name} (row y={row_y})")
            print(f"  ERROR: Could not detect track plateau")
            measurements[name] = {'error': 'track not found'}
            continue

        # Detect handle position
        handle_x = find_handle_center_in_row(arr, row_y, x_search_range)

        if handle_x is None:
            print(f"\n{name} (row y={row_y})")
            print(f"  Track: {left_x} ← {(left_x+right_x)/2:.1f} → {right_x}")
            print(f"  ERROR: Could not detect handle")
            measurements[name] = {'error': 'handle not found', 'track_left': left_x, 'track_right': right_x}
            continue

        # Apply calibration
        normalized = generic_slider_calibration(handle_x, left_x, right_x)
        amount_pct = matrix_amount_domain(normalized)

        print(f"\n{name}")
        print(f"  row_y:         {row_y}")
        print(f"  track_left:    {left_x}")
        print(f"  track_right:   {right_x}")
        print(f"  track_width:   {right_x - left_x}")
        print(f"  track_center:  {(left_x + right_x) / 2.0:.1f}")
        print(f"  handle_x:      {handle_x}")
        print(f"  normalized:    {normalized:.4f}")
        print(f"  amount:        {amount_pct:+.1f}%")

        measurements[name] = {
            'row_y': row_y,
            'track_left': left_x,
            'track_right': right_x,
            'handle_x': handle_x,
            'normalized': normalized,
            'amount_pct': amount_pct,
        }

    # Measure empty rows for zero-reference verification
    print("\n" + "-"*80)
    print("EMPTY ROWS (zero-reference verification)")
    print("-"*80)

    for empty_row in EMPTY_ROWS:
        if empty_row['row_y'] is None:
            continue

        row_y = empty_row['row_y']
        left_x, right_x = find_track_plateau_in_row(arr, row_y, x_search_range)
        handle_x = find_handle_center_in_row(arr, row_y, x_search_range)

        if left_x is not None and handle_x is not None:
            normalized = generic_slider_calibration(handle_x, left_x, right_x)
            amount_pct = matrix_amount_domain(normalized)

            print(f"\n{empty_row['name']} (row y={row_y})")
            print(f"  track: {left_x} ← {(left_x+right_x)/2:.1f} → {right_x}")
            print(f"  handle: {handle_x}")
            print(f"  amount: {amount_pct:+.1f}%")

    # Summary
    print("\n" + "="*80)
    print("CALIBRATED AMOUNTS")
    print("="*80)

    for route in ROUTES:
        if route['name'] in measurements and 'amount_pct' in measurements[route['name']]:
            amount = measurements[route['name']]['amount_pct']
            print(f"{route['name']:30} {amount:+6.1f}%")

    return measurements


if __name__ == "__main__":
    print("""
SETUP REQUIRED:
Before running calibration, set these values based on visual inspection
of step3_04m35s_matrix_mod_routes.jpg:

1. MATRIX_ROI coordinates:
   - x_min: left edge of the Amount column (Matrix sliders start here)
   - x_max: right edge of the Amount column

2. Route row_y coordinates (the y-pixel of each populated row):
   - ROUTES[0]['row_y']: LFO 1 → A Fine
   - ROUTES[1]['row_y']: LFO 1 → B Fine
   - ROUTES[2]['row_y']: Env 3 → Noise Level
   - ROUTES[3]['row_y']: Env 2 → Filter 1 Freq

3. Empty row y-coordinate (for zero-reference verification):
   - EMPTY_ROWS[0]['row_y']: one of the unassigned/empty matrix rows

Example (hypothetical, you must verify):
  MATRIX_ROI = {'x_min': 200, 'x_max': 350, 'y_min': 155, 'y_max': 310}
  ROUTES[0]['row_y'] = 165  # LFO 1 → A Fine
  ROUTES[1]['row_y'] = 188  # LFO 1 → B Fine
  ROUTES[2]['row_y'] = 211  # Env 3 → Noise Level
  ROUTES[3]['row_y'] = 234  # Env 2 → Filter 1 Freq
  EMPTY_ROWS[0]['row_y'] = 280  # Empty row

Then run: python -Xutf8 calibrate_matrix_amounts_reproducible.py
""")

    calibrate_routes()
