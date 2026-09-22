"""Phase 4.2: Slider Calibration Pipeline

Integrates v3 geometric detector with GenericSliderCalibration to produce
calibrated slider observations ready for VerifiedMatrixRoute creation.

Flow:
  Image
    ↓
  establish_structural_rail (from reference rows)
    ↓
  detect_slider_handle_in_row (per populated row)
    ↓
  GenericSliderCalibration
    ↓
  SliderObservation (amount in canonical [-100, +100] %)
    ↓
  VerifiedMatrixRoute
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from slider_geometry_detector_v3 import (
    establish_structural_rail,
    detect_slider_handle_in_row,
    StructuralRail,
    GeometryDetectionError,
)


CANONICAL_AMOUNT_UNIT = "%"
CANONICAL_AMOUNT_DOMAIN = (-100.0, 100.0)


@dataclass
class SliderObservation:
    """Raw observation from slider geometry + calibration."""
    row_y: int
    handle_x: int
    normalized_position: float  # [0, 1]
    amount: float  # [-100, +100] %
    rail: StructuralRail
    amount_unit: str = CANONICAL_AMOUNT_UNIT
    amount_domain: Tuple[float, float] = CANONICAL_AMOUNT_DOMAIN
    amount_source: str = "SLIDER_PIXEL_CALIBRATION"

    def validates_representation(self) -> bool:
        """Check that amount is in canonical representation."""
        return (
            self.amount_unit == CANONICAL_AMOUNT_UNIT
            and self.amount_domain == CANONICAL_AMOUNT_DOMAIN
        )


def calibrate_slider_amount(
    normalized_position: float,
) -> float:
    """GenericSliderCalibration: normalized → canonical amount [-100, +100] %.

    Formula: amount = normalized * 200 - 100

    Args:
        normalized_position: Handle position in [0, 1]

    Returns:
        Amount in [-100, +100] %
    """
    return normalized_position * 200.0 - 100.0


def create_slider_observation(
    arr: np.ndarray,
    row_y: int,
    rail: StructuralRail,
) -> SliderObservation:
    """Detect handle and create calibrated observation for one row.

    Args:
        arr: Image array
        row_y: Row y-coordinate
        rail: Structural rail geometry (from reference rows)

    Returns:
        SliderObservation with calibrated amount

    Raises:
        GeometryDetectionError: If handle not found or lies outside rail
    """

    handle_x, normalized = detect_slider_handle_in_row(arr, row_y, rail)
    amount = calibrate_slider_amount(normalized)

    return SliderObservation(
        row_y=row_y,
        handle_x=handle_x,
        normalized_position=normalized,
        amount=amount,
        rail=rail,
        amount_unit=CANONICAL_AMOUNT_UNIT,
        amount_domain=CANONICAL_AMOUNT_DOMAIN,
        amount_source="SLIDER_PIXEL_CALIBRATION",
    )


def calibrate_matrix_amounts(
    arr: np.ndarray,
    reference_row_ys: List[int],
    populated_rows: List[Tuple[str, int]],
    amount_column_x_range: Tuple[int, int] = (198, 324),
) -> Tuple[StructuralRail, List[Tuple[str, SliderObservation]]]:
    """Full calibration pipeline: establish rail, detect handles, calibrate amounts.

    Args:
        arr: Image array
        reference_row_ys: List of y-coordinates for empty/reference rows
        populated_rows: List of (route_name, row_y) tuples
        amount_column_x_range: (x_min, x_max) of Amount column

    Returns:
        (structural_rail, [(route_name, SliderObservation), ...])

    Raises:
        GeometryDetectionError: If rail not established or handle detection fails
    """

    # Step 1: Establish structural rail from reference rows
    rail = establish_structural_rail(arr, reference_row_ys, amount_column_x_range)

    # Step 2: Detect handles and create observations
    observations = []
    for route_name, row_y in populated_rows:
        obs = create_slider_observation(arr, row_y, rail)
        observations.append((route_name, obs))

    return rail, observations


if __name__ == "__main__":
    print("""
SliderCalibrationPipeline
=========================

Flow:
  1. establish_structural_rail() → StructuralRail (fixed)
  2. create_slider_observation() × N → SliderObservation (per row)
  3. GenericSliderCalibration → amount [-100, +100] %
  4. VerifiedMatrixRoute (with amount_source=SLIDER_PIXEL_CALIBRATION)

Usage:
    rail, observations = calibrate_matrix_amounts(
        arr=image_array,
        reference_row_ys=[280],
        populated_rows=[
            ('LFO 1 → A Fine', 160),
            ('LFO 1 → B Fine', 184),
            ('Env 3 → Noise Level', 207),
            ('Env 2 → Filter 1 Freq', 232),
        ],
    )

    for route_name, obs in observations:
        print(f"{route_name}: {obs.amount:+.1f}%")
""")
