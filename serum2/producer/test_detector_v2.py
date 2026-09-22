"""Test the improved v2 detector against the golden image."""

import numpy as np
from PIL import Image
from slider_geometry_detector_v2 import detect_amount_slider_in_row, GeometryDetectionError

# Load image
image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# Golden fixture: Amount column bounds (from blind auditor validation)
AMOUNT_COLUMN = (198, 324)

# Row seeds (from visual inspection)
ROWS = [
    {'name': 'LFO 1 → A Fine', 'seed_y': 160},
    {'name': 'LFO 1 → B Fine', 'seed_y': 184},
    {'name': 'Env 3 → Noise Level', 'seed_y': 207},
    {'name': 'Env 2 → Filter 1 Freq', 'seed_y': 232},
]

print("="*80)
print("Testing v2 Detector (Structural Constraints)")
print("="*80)
print(f"\nAmount column bounds: {AMOUNT_COLUMN[0]}–{AMOUNT_COLUMN[1]}")
print(f"Expected track width: 126px\n")

for route in ROWS:
    print(f"{route['name']} (seed y={route['seed_y']})")
    try:
        geometry = detect_amount_slider_in_row(
            arr=arr,
            row_y=route['seed_y'],
            amount_column_x_range=AMOUNT_COLUMN,
            search_radius=5
        )

        print(f"  ✓ Detected row center: y={route['seed_y']} (no search needed)")
        print(f"    Track:  {geometry.left_pixel}–{geometry.right_pixel} (width={geometry.width}px)")
        print(f"    Handle: {geometry.handle_x}")
        print(f"    Normalized: {geometry.normalized_handle:.4f}")

        # Compare to blind auditor
        blind_tracks = {
            'LFO 1 → A Fine': (198, 324, 262),
            'LFO 1 → B Fine': (198, 324, 262),
            'Env 3 → Noise Level': (198, 324, 282),
            'Env 2 → Filter 1 Freq': (198, 324, 305),
        }

        if route['name'] in blind_tracks:
            blind_left, blind_right, blind_handle = blind_tracks[route['name']]
            left_match = geometry.left_pixel == blind_left
            right_match = geometry.right_pixel == blind_right
            handle_diff = abs(geometry.handle_x - blind_handle)

            print(f"    vs Blind: track [{blind_left}–{blind_right}], handle {blind_handle}")
            print(f"    Left match: {left_match}, Right match: {right_match}, Handle diff: {handle_diff}px")

        print()

    except GeometryDetectionError as e:
        print(f"  ✗ FAILED: {e}\n")

print("="*80)
print("EXPECTED RESULT:")
print("All four routes should detect geometry matching blind auditor (~198-324, handles 262-305)")
print("v1 detector failed with track_right~418 (wrong region)")
print("v2 detector should pass by enforcing Amount column bounds")
print("="*80)
