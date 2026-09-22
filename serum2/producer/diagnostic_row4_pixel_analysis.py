"""Detailed pixel-level diagnostic for row 4 (Env 2 → Filter 1 Freq).

Hypothesis: v2 detector found 198-259 (filled segment) instead of 198-324 (full rail).
Test: Compare against empty row to see if underlying rail is same width.
"""

import numpy as np
from PIL import Image, ImageDraw
import csv

# Load image
image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# Row 4 (Env 2 → Filter 1 Freq)
ROW4_Y = 232
EMPTY_ROW_Y = 280  # For comparison

# Scan range: full Amount column area plus margin
X_SCAN_MIN = 180
X_SCAN_MAX = 340

print("="*80)
print("ROW 4 PIXEL DIAGNOSTIC: Env 2 → Filter 1 Freq")
print("="*80)
print(f"\nRow 4 center: y={ROW4_Y}")
print(f"Empty row (reference): y={EMPTY_ROW_Y}")
print(f"Scan range: x={X_SCAN_MIN}–{X_SCAN_MAX}\n")

# --- Part 1: Horizontal profile at row 4 ---

print("PART 1: Horizontal profile at row 4")
print("-" * 80)

profile_data = []
for x in range(X_SCAN_MIN, X_SCAN_MAX, 5):  # Every 5 pixels for brevity
    r, g, b = arr[ROW4_Y, x, :3]
    luminance = 0.299*r + 0.587*g + 0.114*b

    # Check if plateau (grey)
    is_plateau = (40 <= r <= 100 and 60 <= g <= 120 and 70 <= b <= 130)

    profile_data.append({
        'x': x,
        'r': r,
        'g': g,
        'b': b,
        'luminance': luminance,
        'is_plateau': is_plateau,
    })

# Print as ASCII profile
print(f"{'x':>3} {'RGB':^20} {'Luminance':>10} {'Plateau':>8}")
print("-" * 50)

for data in profile_data:
    rgb_str = f"({data['r']:3d},{data['g']:3d},{data['b']:3d})"
    plateau_str = "YES" if data['is_plateau'] else "   "
    print(f"{data['x']:3d} {rgb_str:^20} {data['luminance']:>10.1f} {plateau_str:>8}")

# Find contiguous plateau regions
plateau_regions = []
in_region = False
region_start = None

for i, data in enumerate(profile_data):
    if data['is_plateau'] and not in_region:
        region_start = data['x']
        in_region = True
    elif not data['is_plateau'] and in_region:
        plateau_regions.append((region_start, profile_data[i-1]['x']))
        in_region = False

if in_region:
    plateau_regions.append((region_start, profile_data[-1]['x']))

print(f"\nDetected plateau regions:")
for region_start, region_end in plateau_regions:
    print(f"  x={region_start}–{region_end} (width={region_end-region_start}px)")

# --- Part 2: Vertical band inspection ---

print("\n" + "="*80)
print("PART 2: Vertical band (y=227–237, x=190–335)")
print("-" * 80)

y_band_min = 227
y_band_max = 237
x_band_min = 190
x_band_max = 335

# Extract the band
vertical_band = arr[y_band_min:y_band_max, x_band_min:x_band_max, :]

# For each x in the band, compute:
# - mean RGB across the y-band
# - std dev across the y-band
# - max luminance

print(f"{'x':>3} {'Mean RGB':^20} {'StdDev':>8} {'Max Lum':>8} {'Description'}")
print("-" * 70)

for x_offset in range(0, (x_band_max - x_band_min), 10):
    x = x_band_min + x_offset

    # Get pixels in this vertical band at this x
    column = vertical_band[:, x_offset, :3]

    mean_r = np.mean(column[:, 0])
    mean_g = np.mean(column[:, 1])
    mean_b = np.mean(column[:, 2])

    std_dev = np.std(column)
    max_lum = np.max(0.299*column[:, 0] + 0.587*column[:, 1] + 0.114*column[:, 2])

    # Classify
    is_plateau = (40 <= mean_r <= 100 and 60 <= mean_g <= 120 and 70 <= mean_b <= 130)
    is_bright = max_lum > 200

    desc = ""
    if is_plateau:
        desc = "PLATEAU"
    elif is_bright:
        desc = "BRIGHT (handle/fill?)"
    else:
        desc = "background"

    rgb_str = f"({mean_r:5.1f},{mean_g:5.1f},{mean_b:5.1f})"
    print(f"{x:3d} {rgb_str:^20} {std_dev:8.1f} {max_lum:8.1f} {desc}")

# --- Part 3: Compare with empty row ---

print("\n" + "="*80)
print("PART 3: Comparison with empty row (y=280)")
print("-" * 80)

print(f"{'x':>3} {'Row4 RGB':^20} {'Empty RGB':^20} {'Match':>6}")
print("-" * 65)

for x in range(198, 325, 10):
    r4, g4, b4 = arr[ROW4_Y, x, :3]
    re, ge, be = arr[EMPTY_ROW_Y, x, :3]

    rgb4_str = f"({r4:3d},{g4:3d},{b4:3d})"
    rgbe_str = f"({re:3d},{ge:3d},{be:3d})"

    # Check if both are plateau
    is_plateau4 = (40 <= r4 <= 100 and 60 <= g4 <= 120 and 70 <= b4 <= 130)
    is_plateaue = (40 <= re <= 100 and 60 <= ge <= 120 and 70 <= be <= 130)

    match = "BOTH" if (is_plateau4 and is_plateaue) else ("4 only" if is_plateau4 else ("E only" if is_plateaue else "NONE"))

    print(f"{x:3d} {rgb4_str:^20} {rgbe_str:^20} {match:>6}")

print("\n" + "="*80)
print("DIAGNOSTIC QUESTIONS:")
print("-" * 80)
print("1. Does the full rail 198-324 exist in row 4, or just the filled segment 198-259?")
print("2. Is the boundary at x=259 a real UI edge, or JPEG compression artifact?")
print("3. Do the empty row and row 4 show the same underlying rail geometry?")
print("4. Is 198-259 the FILLED track while 259-324 is the UNFILLED track for this slider?")
print("\nExpected interpretation:")
print("- If full rail 198-324 exists but only 198-259 is grey, detector must handle fill vs rail")
print("- If only 198-259 really exists, then blind auditor's 198-324 for row 4 is wrong")
print("- If empty row matches row 4, the rendering difference is value-dependent fill")
print("="*80)

# Save detailed profile to CSV for further inspection
csv_path = r"D:\ableton claude final best\serum2\producer\row4_profile.csv"
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['x', 'r', 'g', 'b', 'luminance', 'is_plateau'])
    writer.writeheader()
    writer.writerows(profile_data)

print(f"\nDetailed profile saved to: {csv_path}")
