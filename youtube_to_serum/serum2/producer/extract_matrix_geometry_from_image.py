"""Extract actual Matrix Amount slider geometry from source image.

Uses systematic pixel scanning to measure track boundaries and handle
positions, then applies GenericSliderCalibration to produce canonical
amounts. This is the ground-truth calibration for HEEGN1Xl5o4 step3.
"""

import numpy as np
from PIL import Image
from pathlib import Path

# Load the source image
image_path = Path(r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg")
img = Image.open(image_path)
arr = np.array(img)

print(f"Image shape: {arr.shape}")
print(f"Image size: {img.size}\n")

# Matrix rows in the screenshot (y-coordinates approximate, will refine):
# Row 1: LFO 1 → A Fine (≈160px)
# Row 2: LFO 1 → B Fine (≈183px)
# Row 3: Env 3 → Noise Level (≈206px)
# Row 4: Env 2 → Filter 1 Freq (≈230px)
# Rows 5–8: Empty/unassigned

# The Matrix Amount widget appears to be around x=240–360 in the panel
# Let me scan a row to find the track geometry

def find_track_plateau(row_y, x_range=(200, 400)):
    """Scan a horizontal line to find the track plateau (grey area)."""
    line = arr[row_y, x_range[0]:x_range[1], :]

    # The track plateau is a greyish color (moderate RGB values)
    # Background is darker, edges may have other UI elements
    # Look for sustained grey: R, G, B all in a similar mid range

    grey_mask = []
    for x_idx in range(line.shape[0]):
        r, g, b = line[x_idx, :3]
        # Track plateau appears to be roughly (50–80, 70–100, 80–110) in this image
        is_plateau = (40 < r < 100 and 60 < g < 120 and 70 < b < 130)
        grey_mask.append(is_plateau)

    grey_mask = np.array(grey_mask)

    # Find first and last True in the mask
    true_indices = np.where(grey_mask)[0]
    if len(true_indices) > 0:
        left_x = x_range[0] + true_indices[0]
        right_x = x_range[0] + true_indices[-1]
        return left_x, right_x, grey_mask
    return None, None, grey_mask


def find_handle_position(row_y, x_range=(200, 400), y_offset=5):
    """Find the brightest pixel in a narrow band above the track (the handle tip)."""
    y_band = arr[row_y - y_offset:row_y, x_range[0]:x_range[1], :]

    # Sum brightness across the band
    brightness = np.mean(y_band, axis=(0, 2))  # average across y and RGB

    # Find the brightest point (the handle pointer)
    if brightness.shape[0] > 0:
        brightest_idx = np.argmax(brightness)
        handle_x = x_range[0] + brightest_idx
        return handle_x
    return None


# Scan each of the 4 populated rows
rows_to_measure = [
    (160, "LFO 1 → A Fine"),
    (183, "LFO 1 → B Fine"),
    (206, "Env 3 → Noise Level"),
    (230, "Env 2 → Filter 1 Freq"),
]

# Also measure a couple of empty rows for zero-reference
empty_rows = [
    (280, "Empty (r6)"),
    (303, "Empty (r7)"),
]

print("=" * 80)
print("TRACK GEOMETRY MEASUREMENT")
print("=" * 80)

measurements = {}

for row_y, label in rows_to_measure + empty_rows:
    left_x, right_x, grey_mask = find_track_plateau(row_y)
    handle_x = find_handle_position(row_y) if row_y < 280 else None

    if left_x is not None:
        half_width = (right_x - left_x) / 2.0
        center_x = left_x + half_width

        if handle_x is not None:
            normalized = (handle_x - left_x) / (right_x - left_x)
            amount_pct = normalized * 200.0 - 100.0
            measurements[label] = {
                'row_y': row_y,
                'track_left': left_x,
                'track_right': right_x,
                'center': center_x,
                'handle_x': handle_x,
                'normalized': normalized,
                'amount_pct': amount_pct,
            }
            print(f"\n{label}")
            print(f"  Track:  {left_x} ← {center_x} (center) → {right_x}")
            print(f"  Handle: {handle_x}")
            print(f"  Normalized: {normalized:.4f}")
            print(f"  Amount: {amount_pct:+.1f}%")
        else:
            measurements[label] = {
                'row_y': row_y,
                'track_left': left_x,
                'track_right': right_x,
                'center': center_x,
                'note': 'empty row (no handle detected)'
            }
            print(f"\n{label} (empty row)")
            print(f"  Track:  {left_x} ← {center_x} (center) → {right_x}")


# Now verify against the blind auditor's measurements
print("\n" + "=" * 80)
print("COMPARISON: Our extraction vs Blind Auditor")
print("=" * 80)

auditor_data = {
    "LFO 1 → A Fine": {"track_left": 198, "track_right": 324, "handle_x": 262, "amount": 1.6},
    "LFO 1 → B Fine": {"track_left": 198, "track_right": 324, "handle_x": 262, "amount": 1.6},
    "Env 3 → Noise Level": {"track_left": 198, "track_right": 324, "handle_x": 282, "amount": 33.3},
    "Env 2 → Filter 1 Freq": {"track_left": 198, "track_right": 324, "handle_x": 305, "amount": 69.8},
}

for label, our_data in measurements.items():
    if label in auditor_data:
        aud = auditor_data[label]
        our = our_data

        left_diff = our['track_left'] - aud['track_left']
        right_diff = our['track_right'] - aud['track_right']
        handle_diff = our['handle_x'] - aud['handle_x'] if 'handle_x' in our else None
        amount_diff = our['amount_pct'] - aud['amount'] if 'amount_pct' in our else None

        print(f"\n{label}")
        print(f"  Track left:  ours={our['track_left']:3d}, auditor={aud['track_left']:3d}, diff={left_diff:+3d}")
        print(f"  Track right: ours={our['track_right']:3d}, auditor={aud['track_right']:3d}, diff={right_diff:+3d}")
        if handle_diff is not None:
            print(f"  Handle x:    ours={our['handle_x']:3d}, auditor={aud['handle_x']:3d}, diff={handle_diff:+3d}")
        if amount_diff is not None:
            print(f"  Amount:      ours={our['amount_pct']:+6.1f}%, auditor={aud['amount']:+6.1f}%, diff={amount_diff:+6.1f}pp")

print("\n" + "=" * 80)
print("FINAL AMOUNTS (from our extraction)")
print("=" * 80)
for label in ["LFO 1 → A Fine", "LFO 1 → B Fine", "Env 3 → Noise Level", "Env 2 → Filter 1 Freq"]:
    if label in measurements and 'amount_pct' in measurements[label]:
        print(f"{label:30} {measurements[label]['amount_pct']:+6.1f}%")
