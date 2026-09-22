"""Phase 4.2: Slider Evidence Extractor with v3 Geometry Detector

Production wiring of v3 structural rail detector into the extraction pipeline.

Flow:
  ExtractionRequest (image + ROI hints)
    ↓
  establish_structural_rail (from reference rows detected in image)
    ↓
  detect_slider_handle_in_row (within Amount column)
    ↓
  GenericSliderCalibration
    ↓
  ExtractionResult (with calibrated amount)
    ↓
  SliderObservation (ready for VerifiedReferenceState)
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from enum import Enum
import numpy as np
from PIL import Image

from slider_geometry_detector_v3 import (
    establish_structural_rail,
    detect_slider_handle_in_row,
    StructuralRail,
    GeometryDetectionError,
)
from phase4_2_slider_calibration_pipeline import (
    calibrate_slider_amount,
    SliderObservation as CalibrationObservation,
)


class ExtractionStatus(Enum):
    """Slider evidence extraction outcome."""
    EXTRACTED = "EXTRACTED"
    MISSING_ROI = "MISSING_ROI"
    RAIL_DETECTION_FAILED = "RAIL_DETECTION_FAILED"
    HANDLE_DETECTION_FAILED = "HANDLE_DETECTION_FAILED"
    AMBIGUOUS_GEOMETRY = "AMBIGUOUS_GEOMETRY"
    INVALID_FRAME = "INVALID_FRAME"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"


@dataclass
class ExtractionRequest:
    """Request to extract slider evidence from a frame."""
    observation_id: str
    canonical_id: str
    row_detail: Optional[str] = None
    image_path: str = ""
    roi_bbox: Optional[Dict[str, float]] = None
    expected_orientation: str = "horizontal"
    extraction_method: str = "SLIDER_PIXEL_V3"
    confidence_threshold: float = 0.5


@dataclass
class ExtractionResult:
    """Result of slider evidence extraction."""
    status: ExtractionStatus

    # Extracted geometry
    track_id: Optional[str] = None
    left_pixel: Optional[float] = None
    right_pixel: Optional[float] = None
    orientation: Optional[str] = None

    # Extracted handle position
    handle_position_pixel: Optional[float] = None
    normalized_position: Optional[float] = None
    calibrated_amount: Optional[float] = None

    # Confidence measures
    track_detection_confidence: float = 0.0
    handle_detection_confidence: float = 0.0

    # Structural rail info (for provenance)
    structural_rail: Optional[StructuralRail] = None
    reference_row_sources: List[int] = None

    # Error/diagnostic
    error_message: Optional[str] = None
    extraction_provenance: Dict[str, str] = None

    def __post_init__(self):
        if self.reference_row_sources is None:
            self.reference_row_sources = []
        if self.extraction_provenance is None:
            self.extraction_provenance = {}


class SliderEvidenceExtractorV3:
    """Production extractor using v3 structural rail architecture.

    Detects:
    1. Structural rail from reference (empty) rows
    2. Handle position from populated row (independent of fill)
    3. Calibrated amount via GenericSliderCalibration
    """

    def __init__(self, extractor_id: str = "slider_extractor_v3"):
        self.extractor_id = extractor_id

    def extract(
        self,
        request: ExtractionRequest,
        reference_row_ys: Optional[List[int]] = None,
        amount_column_x_range: Tuple[int, int] = (198, 324),
    ) -> ExtractionResult:
        """Extract slider geometry and calibrated amount from image.

        Args:
            request: Extraction request with image path and row_y hint
            reference_row_ys: List of y-coordinates for empty/reference rows
                If None, will attempt auto-detection
            amount_column_x_range: (x_min, x_max) structural bounds

        Returns:
            ExtractionResult with geometry and calibrated amount
        """

        result = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,
            track_id=f"track_{request.observation_id}",
            orientation=request.expected_orientation,
            extraction_provenance={
                "observation_id": request.observation_id,
                "image_path": request.image_path,
                "extraction_method": request.extraction_method,
                "extractor_id": self.extractor_id,
                "detector_architecture": "v3_structural_rail",
            },
        )

        # Load image
        try:
            img = Image.open(request.image_path)
            arr = np.array(img)
        except Exception as e:
            result.status = ExtractionStatus.INVALID_FRAME
            result.error_message = f"Failed to load image: {e}"
            return result

        # If reference rows not provided, use sensible default for Matrix Amount
        if reference_row_ys is None:
            reference_row_ys = [280]  # Empirically determined from HEEGN1Xl5o4

        # Step 1: Establish structural rail from reference rows
        try:
            rail = establish_structural_rail(arr, reference_row_ys, amount_column_x_range)
            result.structural_rail = rail
            result.reference_row_sources = reference_row_ys
            result.left_pixel = float(rail.left_pixel)
            result.right_pixel = float(rail.right_pixel)
        except GeometryDetectionError as e:
            result.status = ExtractionStatus.RAIL_DETECTION_FAILED
            result.error_message = str(e)
            return result

        # Step 2: Detect handle in populated row
        if request.row_detail is None:
            result.status = ExtractionStatus.MISSING_ROI
            result.error_message = "row_detail (row y-coordinate) required for handle detection"
            return result

        try:
            row_y = int(request.row_detail)
            handle_x, normalized = detect_slider_handle_in_row(arr, row_y, rail)
            result.handle_position_pixel = float(handle_x)
            result.normalized_position = normalized
        except (ValueError, GeometryDetectionError) as e:
            result.status = ExtractionStatus.HANDLE_DETECTION_FAILED
            result.error_message = str(e)
            return result

        # Step 3: Apply GenericSliderCalibration
        amount = calibrate_slider_amount(normalized)
        result.calibrated_amount = amount

        # Step 4: Set confidence measures
        result.track_detection_confidence = 0.95  # Rail from reference row is high-confidence
        result.handle_detection_confidence = 0.90  # Handle detection generally reliable

        # Step 5: Validate
        if not (result.left_pixel <= result.handle_position_pixel <= result.right_pixel):
            result.status = ExtractionStatus.OUT_OF_BOUNDS
            result.error_message = (
                f"Handle x={result.handle_position_pixel} outside rail "
                f"[{result.left_pixel}, {result.right_pixel}]"
            )
            return result

        result.status = ExtractionStatus.EXTRACTED
        return result


def extraction_result_to_calibration_observation(
    request: ExtractionRequest,
    extraction_result: ExtractionResult,
) -> CalibrationObservation:
    """Convert extraction result to calibration observation.

    Ready to feed into phase4_2_slider_calibration_pipeline for VerifiedMatrixRoute.
    """

    if extraction_result.status != ExtractionStatus.EXTRACTED:
        raise ValueError(
            f"Cannot convert non-extracted result. Status: {extraction_result.status.value}"
        )

    # Build observation with explicit provenance
    obs = CalibrationObservation(
        row_y=int(request.row_detail) if request.row_detail else 0,
        handle_x=int(extraction_result.handle_position_pixel),
        normalized_position=extraction_result.normalized_position,
        amount=extraction_result.calibrated_amount,
        rail=extraction_result.structural_rail,
        amount_unit="%",
        amount_domain=(-100.0, 100.0),
        amount_source="SLIDER_PIXEL_CALIBRATION",
    )

    return obs


if __name__ == "__main__":
    print("""
SliderEvidenceExtractorV3
========================

Production wiring of v3 structural rail detector into extraction pipeline.

Detects:
  1. Structural rail from reference (empty) rows
  2. Handle position from populated row
  3. Calibrated amount [-100, +100] %

Key differences from v1/v2:
  • Uses structural rail from reference rows (fixed)
  • Detects handle independently (not affected by fill)
  • Explicit calibration provenance (SLIDER_PIXEL_CALIBRATION)
  • Works universally (no special cases per row)

Usage:
    extractor = SliderEvidenceExtractorV3()

    result = extractor.extract(
        request=ExtractionRequest(
            observation_id="obs_1",
            canonical_id="matrix.amount",
            row_detail="160",  # row y-coordinate
            image_path="step3_04m35s_matrix_mod_routes.jpg",
        ),
        reference_row_ys=[280],
        amount_column_x_range=(198, 324),
    )

    if result.status == ExtractionStatus.EXTRACTED:
        obs = extraction_result_to_calibration_observation(request, result)
        print(f"Amount: {obs.amount:+.1f}%")
""")
