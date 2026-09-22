"""Debug: print actual RGB values in the track area to understand geometry."""

import numpy as np
from PIL import Image

image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# Sample across one row at the auditor's reported track boundaries
row_y = 160  # LFO 1 → A Fine
x_positions = [198, 220, 261, 290, 324]  # auditor's range (198-324) plus midpoints

print("Row 160 (LFO 1 → A Fine) RGB values:")
print(f"x:    {x_positions}")
for x in x_positions:
    r, g, b = arr[row_y, x, :3]
    print(f"{x}: RGB({r:3d}, {g:3d}, {b:3d})")

print("\n" + "="*60)
print("Scanning across the full x-range at this row:")
print("="*60)
print("x     R    G    B    status")
for x in range(190, 330, 10):
    r, g, b = arr[row_y, x, :3]
    # Auditor's criterion: track ≈ RGB(46–53,66–73,73–80)
    is_track = (46 <= r <= 53 and 66 <= g <= 73 and 73 <= b <= 80)
    # My criterion: (40 < r < 100 and 60 < g < 120 and 70 < b < 130)
    is_my_criterion = (40 < r < 100 and 60 < g < 120 and 70 < b < 130)

    print(f"{x:3d}  {r:3d}  {g:3d}  {b:3d}  auditor={is_track}, mine={is_my_criterion}")

print("\n" + "="*60)
print("Detailed scan, 1px at a time, x=195-330:")
print("="*60)

track_pixels_auditor = []
track_pixels_mine = []

for x in range(195, 331):
    r, g, b = arr[row_y, x, :3]
    is_auditor = (46 <= r <= 53 and 66 <= g <= 73 and 73 <= b <= 80)
    is_mine = (40 < r < 100 and 60 < g < 120 and 70 < b < 130)

    if is_auditor:
        track_pixels_auditor.append(x)
    if is_mine:
        track_pixels_mine.append(x)

if track_pixels_auditor:
    print(f"Auditor criterion (46–53, 66–73, 73–80): pixels {min(track_pixels_auditor)} to {max(track_pixels_auditor)}")
else:
    print("Auditor criterion: NO PIXELS MATCHED")

if track_pixels_mine:
    print(f"My criterion (40<r<100, 60<g<120, 70<b<130): pixels {min(track_pixels_mine)} to {max(track_pixels_mine)}")
else:
    print("My criterion: NO PIXELS MATCHED")

# Also check empty row for comparison
print("\n" + "="*60)
print("Row 280 (Empty row r6) for comparison:")
print("="*60)
row_y_empty = 280
for x in [198, 261, 324]:
    r, g, b = arr[row_y_empty, x, :3]
    print(f"x={x}: RGB({r}, {g}, {b})")
