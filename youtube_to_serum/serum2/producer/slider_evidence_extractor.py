"""Phase 3.5.1: Generic Slider Evidence Extraction

Extracts slider track geometry and knob position from image evidence.
Input: image/frame + expected observation metadata
Output: SliderObservation with track geometry, position, provenance

No knowledge of parameter identity, row semantics, or Serum internals.
Pure image geometry extraction → deterministic slider observation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple
from enum import Enum
import json


class ExtractionStatus(Enum):
    """Slider evidence extraction outcome."""
    EXTRACTED = "EXTRACTED"
    MISSING_ROI = "MISSING_ROI"
    TRACK_DETECTION_FAILED = "TRACK_DETECTION_FAILED"
    KNOB_DETECTION_FAILED = "KNOB_DETECTION_FAILED"
    AMBIGUOUS_GEOMETRY = "AMBIGUOUS_GEOMETRY"
    INVALID_FRAME = "INVALID_FRAME"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"


@dataclass
class ExtractionRequest:
    """Request to extract slider evidence from a frame.

    Specifies what to look for (expected observation) and where (image).
    """
    observation_id: str  # unique extraction task ID
    canonical_id: str  # which control (e.g., "matrix.amount")
    row_detail: Optional[str]  # row context if applicable

    # Image input
    image_path: str  # path to screenshot

    # Hints for extraction (ROI or expected bounds if available)
    roi_bbox: Optional[Dict[str, float]] = None  # {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    expected_orientation: str = "horizontal"  # "horizontal" or "vertical"

    # Extraction parameters
    extraction_method: str = "SLIDER_PIXEL"  # what modality to detect
    confidence_threshold: float = 0.5  # minimum confidence to accept result

    def to_dict(self) -> Dict:
        return {
            "observation_id": self.observation_id,
            "canonical_id": self.canonical_id,
            "row_detail": self.row_detail,
            "image_path": self.image_path,
            "roi_bbox": self.roi_bbox,
            "expected_orientation": self.expected_orientation,
            "extraction_method": self.extraction_method,
        }


@dataclass
class ExtractionResult:
    """Result of slider evidence extraction."""
    status: ExtractionStatus

    # Extracted geometry (if successful)
    track_id: Optional[str] = None
    left_pixel: Optional[float] = None
    right_pixel: Optional[float] = None
    top_pixel: Optional[float] = None
    bottom_pixel: Optional[float] = None
    orientation: Optional[str] = None

    # Extracted knob position (if successful)
    knob_position_pixel: Optional[float] = None

    # Confidence measures
    track_detection_confidence: float = 0.0  # [0, 1]
    knob_detection_confidence: float = 0.0  # [0, 1]

    # Error/diagnostic info
    error_message: Optional[str] = None

    # Provenance
    extraction_provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "track_id": self.track_id,
            "track_bounds": {
                "left": self.left_pixel,
                "right": self.right_pixel,
                "top": self.top_pixel,
                "bottom": self.bottom_pixel,
            } if self.left_pixel is not None else None,
            "knob_position_pixel": self.knob_position_pixel,
            "track_detection_confidence": self.track_detection_confidence,
            "knob_detection_confidence": self.knob_detection_confidence,
            "orientation": self.orientation,
            "error_message": self.error_message,
            "provenance": self.extraction_provenance,
        }


class SliderEvidenceExtractor:
    """Generic slider evidence extractor from image frames.

    No parameter-specific logic. Works for any slider geometry.
    """

    def __init__(self, extractor_id: str = "slider_extractor_v1"):
        self.extractor_id = extractor_id

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        """Extract slider geometry and position from image.

        This is a stubbed implementation. In production, this would:
        1. Load the image
        2. Apply ROI if provided
        3. Detect slider track (continuous contrasting region)
        4. Detect knob position (peak of slider visual marker)
        5. Return deterministic pixel coordinates

        For now, returns a structure that can be populated by:
        - Manual measurements from screenshots
        - VLM-based detection (Qwen ROI → geometry)
        - Computer vision (edge detection, Hough transform)

        The critical point: extraction logic is PARAMETERLESS.
        """

        # Placeholder: log the request
        provenance = {
            "observation_id": request.observation_id,
            "image_path": request.image_path,
            "extraction_method": request.extraction_method,
            "extractor_id": self.extractor_id,
            "note": "Stubbed extractor; coordinates must be populated from evidence data",
        }

        # Return a structure ready to be filled by evidence fixture
        result = ExtractionResult(
            status=ExtractionStatus.EXTRACTED,  # Will be overwritten if extraction fails
            track_id=f"track_{request.observation_id}",
            orientation=request.expected_orientation,
            extraction_provenance=provenance,
        )

        return result

    def populate_from_manual_evidence(
        self,
        result: ExtractionResult,
        left_px: float,
        right_px: float,
        top_px: float,
        bottom_px: float,
        knob_px: float,
        track_confidence: float = 0.95,
        knob_confidence: float = 0.85,
    ) -> ExtractionResult:
        """Populate extraction result from manual/verified measurements.

        Used when evidence comes from:
        - Manual measurement of screenshot
        - High-confidence VLM ROI detection
        - Ground truth verification from reference
        """
        result.left_pixel = left_px
        result.right_pixel = right_px
        result.top_pixel = top_px
        result.bottom_pixel = bottom_px
        result.knob_position_pixel = knob_px
        result.track_detection_confidence = track_confidence
        result.knob_detection_confidence = knob_confidence

        # Validate consistency
        if result.orientation == "horizontal":
            if not (left_px < right_px):
                result.status = ExtractionStatus.INVALID_FRAME
                result.error_message = f"Horizontal: left_px ({left_px}) must be < right_px ({right_px})"
                return result

            if not (left_px <= knob_px <= right_px):
                result.status = ExtractionStatus.OUT_OF_BOUNDS
                result.error_message = f"Knob position {knob_px} outside track [{left_px}, {right_px}]"
                return result
        else:  # vertical
            if not (top_px < bottom_px):
                result.status = ExtractionStatus.INVALID_FRAME
                result.error_message = f"Vertical: top_px ({top_px}) must be < bottom_px ({bottom_px})"
                return result

            if not (top_px <= knob_px <= bottom_px):
                result.status = ExtractionStatus.OUT_OF_BOUNDS
                result.error_message = f"Knob position {knob_px} outside track [{top_px}, {bottom_px}]"
                return result

        result.status = ExtractionStatus.EXTRACTED
        return result


class OutOfBoundsError(Exception):
    """Raised when extracted knob position is outside track bounds."""
    pass


def extraction_result_to_slider_observation(
    request: ExtractionRequest,
    extraction_result: ExtractionResult,
) -> "SliderObservation":
    """Convert extraction result to SliderObservation for calibration.

    Returns a SliderObservation ready to feed into GenericSliderCalibration.
    """
    from calibration_model import TrackGeometry, SliderObservation

    if extraction_result.status != ExtractionStatus.EXTRACTED:
        raise ValueError(
            f"Cannot convert non-extracted result. Status: {extraction_result.status.value}"
        )

    track = TrackGeometry(
        track_id=extraction_result.track_id,
        left_pixel=extraction_result.left_pixel,
        right_pixel=extraction_result.right_pixel,
        top_pixel=extraction_result.top_pixel,
        bottom_pixel=extraction_result.bottom_pixel,
        orientation=extraction_result.orientation,
        source_image=request.image_path,
        detection_method=request.extraction_method,
        confidence=extraction_result.track_detection_confidence,
    )

    observation = SliderObservation(
        observation_id=request.observation_id,
        canonical_id=request.canonical_id,
        row_detail=request.row_detail,
        geometry=track,
        observed_position_pixel=extraction_result.knob_position_pixel,
        calibration_id=f"cal_{extraction_result.track_id}",
        source_image=request.image_path,
        extraction_method=request.extraction_method,
        confidence=extraction_result.knob_detection_confidence,
    )

    return observation
