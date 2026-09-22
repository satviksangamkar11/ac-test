"""v3 Geometry Detector: Structural rail + independent handle detection.

Key insight: Track fill changes with value, but rail geometry is fixed.
Use reference rows (empty slots) to establish the structural rail once,
then detect only handle positions in populated rows.

Reference rows are selected dynamically from image evidence (not hardcoded).
"""

from typing import Tuple, Optional, NamedTuple, List
import numpy as np
from reference_rail_selection_v3 import (
    select_reference_rows_automatic,
    select_reference_rows_with_fallback,
    ReferenceRailSelection,
)


class StructuralRail(NamedTuple):
    """Authoritative slider rail geometry, established from reference row."""
    left_pixel: int
    right_pixel: int
    width: int
    center_x: float

    def __repr__(self):
        return f"Rail[{self.left_pixel}..{self.right_pixel}]"


class SliderGeometry(NamedTuple):
    """Complete slider geometry: rail + handle."""
    rail: StructuralRail
    handle_x: int
    normalized_handle: float  # in [0, 1]

    def __repr__(self):
        norm_pct = self.normalized_handle * 100
        return f"Slider(rail={self.rail}, handle={self.handle_x}, norm={norm_pct:.1f}%)"


class GeometryDetectionError(Exception):
    """Raised when geometry detection fails validation."""
    pass


def establish_structural_rail(
    arr: np.ndarray,
    reference_row_ys: List[int],
    amount_column_x_range: Tuple[int, int],
) -> StructuralRail:
    """Establish the structural rail geometry from reference (empty) rows.

    Uses multiple reference rows to validate consistency and establish the
    authoritative rail geometry that remains fixed across all rows.

    Args:
        arr: Image array (H, W, C)
        reference_row_ys: List of y-coordinates for empty/reference rows
        amount_column_x_range: (x_min, x_max) of Amount column

    Returns:
        StructuralRail representing the fixed slider rail

    Raises:
        GeometryDetectionError: If reference rows don't converge on same rail
    """

    col_min, col_max = amount_column_x_range

    rail_measurements = []

    for row_y in reference_row_ys:
        if row_y < 0 or row_y >= arr.shape[0]:
            continue

        # Scan for plateau in reference row
        line = arr[row_y, col_min:col_max, :]

        plateau_mask = []
        for x_idx in range(line.shape[0]):
            r, g, b = line[x_idx, :3]
            # Plateau is consistent grey (not affected by value/fill)
            is_plateau = (40 <= r <= 100 and 60 <= g <= 120 and 70 <= b <= 130)
            plateau_mask.append(is_plateau)

        plateau_mask = np.array(plateau_mask)
        true_indices = np.where(plateau_mask)[0]

        if len(true_indices) > 0:
            left_local = true_indices[0]
            right_local = true_indices[-1]

            left_x = col_min + left_local
            right_x = col_min + right_local

            rail_measurements.append((left_x, right_x))

    if not rail_measurements:
        raise GeometryDetectionError("No valid rail found in reference rows")

    # Validate consistency across reference rows
    lefts = [m[0] for m in rail_measurements]
    rights = [m[1] for m in rail_measurements]

    left_variance = max(lefts) - min(lefts)
    right_variance = max(rights) - min(rights)

    if left_variance > 5 or right_variance > 5:
        raise GeometryDetectionError(
            f"Reference rows don't converge: left_var={left_variance}px, right_var={right_variance}px. "
            f"Measurements: {rail_measurements}"
        )

    # Use median rail geometry
    rail_left = int(np.median(lefts))
    rail_right = int(np.median(rights))
    rail_width = rail_right - rail_left

    return StructuralRail(
        left_pixel=rail_left,
        right_pixel=rail_right,
        width=rail_width,
        center_x=(rail_left + rail_right) / 2.0,
    )


def establish_structural_rail_universal(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int],
    fallback_rows: Optional[List[int]] = None,
) -> Tuple[StructuralRail, ReferenceRailSelection]:
    """Establish structural rail using automatic reference row selection.

    Universal version: selects reference rows from image evidence, no hardcoding.

    Args:
        arr: Image array (H, W, C)
        amount_column_x_range: (x_min, x_max) of Amount column
        fallback_rows: List of y-coordinates to use if auto-detection fails

    Returns:
        (StructuralRail, ReferenceRailSelection) - geometry and selection provenance

    Raises:
        GeometryDetectionError: If rail cannot be established even with fallback
    """

    # Select reference rows automatically or with fallback
    selection = select_reference_rows_with_fallback(
        arr,
        amount_column_x_range,
        fallback_rows=fallback_rows,
    )

    if not selection.selected_rows:
        raise GeometryDetectionError(
            f"Could not select reference rows. Reason: {selection.selection_reason}"
        )

    # Establish rail from selected rows
    try:
        rail = establish_structural_rail(
            arr,
            selection.selected_rows,
            amount_column_x_range,
        )
        return rail, selection
    except GeometryDetectionError as e:
        # Selection returned rows, but rail establishment failed
        raise GeometryDetectionError(
            f"Selected reference rows {selection.selected_rows} but rail establishment failed: {e}"
        )


def detect_slider_handle_in_row(
    arr: np.ndarray,
    row_y: int,
    structural_rail: StructuralRail,
    y_offset_above: int = 5,
) -> Tuple[int, float]:
    """Detect slider handle position in a populated row.

    Uses the structural rail geometry to constrain the handle search,
    independent of the visual fill/value appearance.

    Args:
        arr: Image array
        row_y: Row y-coordinate (center of slider row)
        structural_rail: Reference rail geometry
        y_offset_above: How many pixels above row_y to scan for handle

    Returns:
        (handle_x, normalized_position) where normalized_position is in [0, 1]

    Raises:
        GeometryDetectionError: If handle not found or lies outside rail
    """

    if row_y < y_offset_above:
        raise GeometryDetectionError(f"Row y={row_y} too close to image edge")

    # Scan for brightest pixel in band above row (the handle indicator)
    y_band = arr[
        row_y - y_offset_above:row_y,
        structural_rail.left_pixel:structural_rail.right_pixel,
        :
    ]

    if y_band.shape[0] == 0 or y_band.shape[1] == 0:
        raise GeometryDetectionError(f"Invalid scan band at row y={row_y}")

    # Average brightness across the band
    brightness = np.mean(y_band, axis=(0, 2))

    if brightness.shape[0] == 0:
        raise GeometryDetectionError("No brightness data in scan band")

    brightest_idx = np.argmax(brightness)
    handle_x = structural_rail.left_pixel + brightest_idx

    # Validate handle lies within rail
    if not (structural_rail.left_pixel <= handle_x <= structural_rail.right_pixel):
        raise GeometryDetectionError(
            f"Handle x={handle_x} outside rail [{structural_rail.left_pixel}, {structural_rail.right_pixel}]"
        )

    # Compute normalized position
    normalized = (handle_x - structural_rail.left_pixel) / structural_rail.width

    return handle_x, normalized


def calibrate_slider(
    structural_rail: StructuralRail,
    handle_x: int,
) -> SliderGeometry:
    """Create calibrated slider geometry from rail and handle.

    Args:
        structural_rail: The fixed rail geometry
        handle_x: The detected handle position

    Returns:
        Complete SliderGeometry with normalized handle position
    """

    normalized = (handle_x - structural_rail.left_pixel) / structural_rail.width

    return SliderGeometry(
        rail=structural_rail,
        handle_x=handle_x,
        normalized_handle=normalized,
    )


if __name__ == "__main__":
    print("""
SliderGeometryDetector v3: Structural Rail Architecture
========================================================

Key principle:
  Slider rail geometry is FIXED (physical structure)
  Slider fill/value changes with amount (visual feedback)

Therefore:
  1. Establish rail from reference row (empty/unambiguous)
  2. For each populated row: detect ONLY handle position
  3. Combine structural rail + detected handle for calibration

This separates:
  - Structural geometry (rail) ← from reference rows
  - Value geometry (fill)      ← from populated rows
  - Handle position            ← from bright pixel detection

Result:
  Row 4's fill changes do NOT affect the rail geometry.
  The same structural rail applies to all four populated rows.

Usage:
    # Establish rail from reference rows
    rail = establish_structural_rail(
        arr=image_array,
        reference_row_ys=[256, 280],  # empty rows
        amount_column_x_range=(198, 324)
    )

    # For each populated row
    for row_y in [160, 184, 207, 232]:
        handle_x, normalized = detect_slider_handle_in_row(
            arr=image_array,
            row_y=row_y,
            structural_rail=rail
        )
        geometry = calibrate_slider(rail, handle_x)
        amount = normalized * 200 - 100  # GenericSliderCalibration
""")
