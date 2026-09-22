"""Visualize system vs blind geometry measurements on the source image.

Overlay both measurement sets to identify which detector is selecting the
correct Matrix Amount region vs. adjacent UI elements.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Load source image
image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
draw = ImageDraw.Draw(img, 'RGBA')

# Configuration
MATRIX_ROI = {'x0': 180, 'x1': 420, 'y0': 135, 'y1': 305}

# System measurements
SYSTEM_DATA = [
    {'name': 'LFO 1 → A Fine', 'row_y': 163, 'left': 198, 'right': 418, 'handle': 405},
    {'name': 'LFO 1 → B Fine', 'row_y': 186, 'left': 199, 'right': 419, 'handle': 407},
    {'name': 'Env 3 → Noise Level', 'row_y': 211, 'left': 198, 'right': 412, 'handle': 357},
    {'name': 'Env 2 → Filter 1 Freq', 'row_y': 233, 'left': 197, 'right': 418, 'handle': 396},
]

# Blind auditor measurements
BLIND_DATA = [
    {'name': 'LFO 1 → A Fine', 'left': 198, 'right': 324, 'handle': 262},
    {'name': 'LFO 1 → B Fine', 'left': 198, 'right': 324, 'handle': 262},
    {'name': 'Env 3 → Noise Level', 'left': 198, 'right': 324, 'handle': 282},
    {'name': 'Env 2 → Filter 1 Freq', 'left': 198, 'right': 324, 'handle': 305},
]

# Draw Matrix ROI bounding box (light grey)
roi_color = (200, 200, 200, 100)
draw.rectangle(
    [(MATRIX_ROI['x0'], MATRIX_ROI['y0']), (MATRIX_ROI['x1'], MATRIX_ROI['y1'])],
    outline=(150, 150, 150, 200),
    width=2
)
draw.text((MATRIX_ROI['x0'] + 5, MATRIX_ROI['y0'] - 20), "Matrix ROI", fill=(150, 150, 150, 200))

# Draw each row
track_height = 8
handle_size = 6

for i, (sys, blind) in enumerate(zip(SYSTEM_DATA, BLIND_DATA)):
    row_y = sys['row_y']
    name = sys['name']

    # Draw row center line (faint)
    draw.line([(MATRIX_ROI['x0'], row_y), (MATRIX_ROI['x1'], row_y)], fill=(100, 100, 100, 50), width=1)

    # BLIND MEASUREMENT (Blue)
    blind_track_y = row_y - track_height // 2
    draw.rectangle(
        [(blind['left'], blind_track_y), (blind['right'], blind_track_y + track_height)],
        fill=(0, 100, 255, 80),
        outline=(0, 100, 255, 200),
        width=2
    )
    # Blind handle (blue circle)
    draw.ellipse(
        [(blind['handle'] - handle_size, row_y - handle_size),
         (blind['handle'] + handle_size, row_y + handle_size)],
        fill=(0, 100, 255, 120),
        outline=(0, 100, 255, 200),
        width=2
    )

    # SYSTEM MEASUREMENT (Red)
    sys_track_y = row_y + track_height // 2
    draw.rectangle(
        [(sys['left'], sys_track_y), (sys['right'], sys_track_y + track_height)],
        fill=(255, 100, 0, 80),
        outline=(255, 100, 0, 200),
        width=2
    )
    # System handle (red square)
    draw.rectangle(
        [(sys['handle'] - handle_size, row_y - handle_size),
         (sys['handle'] + handle_size, row_y + handle_size)],
        fill=(255, 100, 0, 120),
        outline=(255, 100, 0, 200),
        width=2
    )

    # Label
    label_text = f"{i+1}. {name}"
    draw.text((10, row_y - 15), label_text, fill=(255, 255, 255, 200))

    # Draw measurement text
    sys_text = f"Sys: [{sys['left']}...{sys['handle']}...{sys['right']}]"
    blind_text = f"Blind: [{blind['left']}...{blind['handle']}...{blind['right']}]"
    draw.text((150, row_y - 25), sys_text, fill=(255, 100, 0, 180))
    draw.text((150, row_y - 10), blind_text, fill=(0, 100, 255, 180))

# Draw legend
legend_y = MATRIX_ROI['y1'] + 20
draw.text((MATRIX_ROI['x0'], legend_y), "LEGEND:", fill=(200, 200, 200, 200))
draw.rectangle([(MATRIX_ROI['x0'], legend_y + 25), (MATRIX_ROI['x0'] + 20, legend_y + 40)],
               fill=(0, 100, 255, 80), outline=(0, 100, 255, 200), width=2)
draw.text((MATRIX_ROI['x0'] + 30, legend_y + 20), "Blind (auditor) — track region + handle", fill=(0, 100, 255, 200))

draw.rectangle([(MATRIX_ROI['x0'], legend_y + 55), (MATRIX_ROI['x0'] + 20, legend_y + 70)],
               fill=(255, 100, 0, 80), outline=(255, 100, 0, 200), width=2)
draw.text((MATRIX_ROI['x0'] + 30, legend_y + 50), "System (detector) — track region + handle", fill=(255, 100, 0, 200))

draw.line([(MATRIX_ROI['x0'], legend_y + 100), (MATRIX_ROI['x1'], legend_y + 100)],
          fill=(255, 200, 0, 150), width=2)
draw.text((MATRIX_ROI['x0'], legend_y + 105), "DIAGNOSTIC: track_right = 418 extends far beyond blind's 324", fill=(255, 200, 0, 200))
draw.text((MATRIX_ROI['x0'], legend_y + 125), "Does system's right edge land on an Amount slider, or on Destination column?", fill=(255, 200, 0, 200))

# Save the overlay
output_path = r"D:\ableton claude final best\serum2\producer\geometry_mismatch_overlay.png"
img.save(output_path)
print(f"Overlay saved to: {output_path}")
print("\nKEY DIAGNOSTIC QUESTIONS:")
print("1. Does system track_right (red, ~418) land on the Amount slider itself?")
print("2. Or does it extend into the Destination / Aux columns?")
print("3. If system handle (~396–407) is not on a visible slider handle, the detection is wrong.")
print("\nExpected finding: System detector selected a different UI element than the Amount sliders.")
