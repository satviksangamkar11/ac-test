"""Locate the Matrix panel and measure slider positions within it."""

import numpy as np
from PIL import Image

image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# The Matrix panel should be in the upper-left portion of the Serum UI
# It has text labels like "SOURCE", "AMOUNT", "DESTINATION" in the header
# and rows with values below

# Look for the "AMOUNT" column by scanning for text-like patterns
# Columns are approximately:
# - Source label (left)
# - Amount slider (middle-left)
# - Destination (middle-right)
# - Other controls (right)

# Let's find rows with the actual Matrix data
# by looking for the populated rows' row labels (LFO 1, Env 2, etc.)

# First, let me visualize the y-coordinates where text/data actually is
print("Scanning for non-background pixels (darker/lighter than pure background)")
print("to find where the Matrix panel actually is...\n")

# The background is darkish (around RGB 34-40, 54-60, 61-67 based on what we saw)
# Look for any row with significant variation

row_sums = []
for y in range(0, 720, 10):
    # Sum the brightness variation in this row
    row = arr[y, :, :]
    variation = np.std(row, axis=0).mean()  # std dev across RGB channels
    row_sums.append((y, variation))

print("Rows with highest pixel variation (likely text/UI):")
row_sums.sort(key=lambda x: x[1], reverse=True)
for y, var in row_sums[:20]:
    print(f"  y={y:3d}: variation={var:.1f}")

# The Matrix panel header should be around y=135-150
# The rows should be around y=160-310

# Let's find the exact x-coordinates of the Amount column
print("\n" + "="*60)
print("Looking for the Amount column (where sliders are)")
print("="*60)

# The Amount column header says "AMOUNT" and should be narrow (slider width)
# Let's scan row 135 (approximate header) for text
row_header = 138

# Look for pixels that are "text" (bright, high contrast)
pixels_at_header = arr[row_header, :, :]
brightness = np.mean(pixels_at_header, axis=1)

# Text is typically brighter than the dark background
# Find regions with high brightness
text_threshold = 150
text_regions = np.where(brightness > text_threshold)[0]

if len(text_regions) > 0:
    print(f"Text-like pixels (brightness > {text_threshold}) at row {row_header}:")
    print(f"  x ranges: {text_regions[0]} to {text_regions[-1]}")

    # Find the "AMOUNT" column specifically
    # It should be a relatively narrow column (maybe 80-120px wide)
    # Let's look for columns with consistent width

# Actually, let's try a different approach: look at the structure
# The sliders appear to be in a specific x-range across all rows
# Let's find where bright "handle" pixels appear in the populated rows

print("\n" + "="*60)
print("Finding slider handle positions in populated rows")
print("="*60)

populated_rows_approx = [160, 183, 206, 230]  # Approximate from visual inspection

for y in populated_rows_approx:
    # In this row, find pixels that are brighter than surrounding area
    row = arr[y, :, :]
    brightness = np.mean(row, axis=1)

    # Find local maxima (bright spots = handle/control)
    bright_mask = brightness > 120
    bright_indices = np.where(bright_mask)[0]

    if len(bright_indices) > 0:
        groups = []
        current_group = [bright_indices[0]]
        for i in range(1, len(bright_indices)):
            if bright_indices[i] - bright_indices[i-1] <= 2:
                current_group.append(bright_indices[i])
            else:
                groups.append((min(current_group), max(current_group)))
                current_group = [bright_indices[i]]
        groups.append((min(current_group), max(current_group)))

        print(f"\nRow y={y}:")
        print(f"  Bright regions (potential controls): {groups[:3]}")  # Show first 3

# Final verdict: let me ask what the user observed about the panel structure
print("\n" + "="*60)
print("ISSUE IDENTIFIED:")
print("="*60)
print("""
The auditor's measurements don't match the actual image data.
The track coordinates (198–324) with the reported RGB values don't exist
at the y-coordinates of the populated rows (160, 183, 206, 230).

Possible causes:
1. The auditor measured at different y-coordinates (empty rows only)
2. The Matrix panel rows don't all have the same x-geometry
3. The audit methodology needs clarification

RECOMMENDATION:
Do NOT accept the auditor's pixel coordinates as ground truth yet.
Instead, trace the actual image to find:
  - The exact pixel bounds of the Matrix Amount column
  - The actual track/slider geometry within that column
  - The handle positions for each populated row

This requires visual inspection of the source image to establish
the correct coordinate frame before pixel measurements can be trusted.
""")
