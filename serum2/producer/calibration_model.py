"""Phase 3.5: Generic Slider Calibration Model

Universal calibration engine for slider-based observations.
Converts pixel geometry to normalized parameter values.

No knowledge of parameter identity, row context, or Serum internals.
Pure geometric transformation + domain validation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple
from enum import Enum


class CalibrationStatus(Enum):
    """Calibration outcome status."""
    CALIBRATED = "CALIBRATED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    OUT_OF_TRACK = "OUT_OF_TRACK"
    AMBIGUOUS_TRACK = "AMBIGUOUS_TRACK"
    MISSING_GEOMETRY = "MISSING_GEOMETRY"
    VALIDATION_REJECTED = "VALIDATION_REJECTED"


@dataclass
class TrackGeometry:
    """Slider track boundaries and orientation.

    Defines the pixel coordinate system for the slider.
    Must be deterministic and independent of parameter identity.
    """
    track_id: str  # unique identifier for this track
    left_pixel: float  # leftmost pixel coordinate (inclusive)
    right_pixel: float  # rightmost pixel coordinate (inclusive)
    top_pixel: float  # topmost pixel coordinate
    bottom_pixel: float  # bottommost pixel coordinate
    orientation: str  # "horizontal" or "vertical"

    # Calibration provenance
    source_image: str  # which screenshot established this geometry
    detection_method: str  # how was track detected? (e.g., "ROI_CROP", "MANUAL_MEASUREMENT")
    confidence: float  # [0, 1] confidence in geometry detection


@dataclass
class SliderObservation:
    """A single observed slider position from reference evidence.

    Captures geometric evidence without interpreting parameter meaning.
    """
    observation_id: str  # unique within episode
    canonical_id: str  # which control (e.g., "matrix.amount")
    row_detail: Optional[str]  # row context if applicable (e.g., "Env 2 → Filter 1 Freq")

    # Geometry: what was extracted from the screenshot
    geometry: TrackGeometry
    observed_position_pixel: float  # pixel position of slider knob [left_pixel, right_pixel]

    # Calibration identity
    calibration_id: str  # reference to which calibration model

    # Provenance
    source_image: str
    roi_bbox: Optional[Dict[str, float]] = None  # {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    extraction_method: str = "SLIDER_PIXEL"
    confidence: float = 0.5  # [0, 1] confidence in position extraction

    def validate_geometry(self) -> Tuple[bool, Optional[str]]:
        """Verify observed position is within track bounds.

        Returns: (is_valid, error_reason)
        """
        if self.geometry.orientation == "horizontal":
            min_px = self.geometry.left_pixel
            max_px = self.geometry.right_pixel
            position = self.observed_position_pixel
        else:  # vertical
            min_px = self.geometry.top_pixel
            max_px = self.geometry.bottom_pixel
            position = self.observed_position_pixel

        if position < min_px or position > max_px:
            return False, f"Position {position} outside track [{min_px}, {max_px}]"

        return True, None


@dataclass
class CalibrationResult:
    """Output of calibration process."""
    status: CalibrationStatus
    normalized_position: Optional[float] = None  # [0, 1] normalized within track
    candidate_value: Optional[float] = None  # numeric value for domain validation
    error_message: Optional[str] = None
    provenance: Dict[str, str] = field(default_factory=dict)


class GenericSliderCalibration:
    """Universal slider calibration model.

    Transforms pixel position to normalized value.
    Parameterless: works for any slider, any parameter, any row.
    """

    def __init__(self, calibration_id: str):
        self.calibration_id = calibration_id
        self.reference_tracks: Dict[str, TrackGeometry] = {}

    def register_track(self, track: TrackGeometry) -> None:
        """Register a track geometry for this calibration."""
        self.reference_tracks[track.track_id] = track

    def calibrate(self, observation: SliderObservation) -> CalibrationResult:
        """Convert slider observation to normalized position.

        Returns:
            CalibrationResult with normalized_position (0.0 to 1.0)
        """
        # Validate geometry
        is_valid, error = observation.validate_geometry()
        if not is_valid:
            return CalibrationResult(
                status=CalibrationStatus.OUT_OF_TRACK,
                error_message=error,
                provenance={
                    "observation_id": observation.observation_id,
                    "source_image": observation.source_image,
                }
            )

        # Check track is registered
        if observation.geometry.track_id not in self.reference_tracks:
            return CalibrationResult(
                status=CalibrationStatus.MISSING_GEOMETRY,
                error_message=f"Track {observation.geometry.track_id} not registered",
                provenance={
                    "observation_id": observation.observation_id,
                    "track_id": observation.geometry.track_id,
                }
            )

        # Compute normalized position
        geom = observation.geometry
        if geom.orientation == "horizontal":
            track_range = geom.right_pixel - geom.left_pixel
            position_in_track = observation.observed_position_pixel - geom.left_pixel
        else:  # vertical
            track_range = geom.bottom_pixel - geom.top_pixel
            position_in_track = observation.observed_position_pixel - geom.top_pixel

        if track_range <= 0:
            return CalibrationResult(
                status=CalibrationStatus.INVALID_GEOMETRY,
                error_message=f"Invalid track range: {track_range}",
                provenance={
                    "observation_id": observation.observation_id,
                    "track_range": str(track_range),
                }
            )

        normalized = position_in_track / track_range

        # Clamp to [0, 1] (position is within bounds, so this should be natural)
        normalized = max(0.0, min(1.0, normalized))

        return CalibrationResult(
            status=CalibrationStatus.CALIBRATED,
            normalized_position=normalized,
            provenance={
                "observation_id": observation.observation_id,
                "canonical_id": observation.canonical_id,
                "row_detail": observation.row_detail or "none",
                "track_id": observation.geometry.track_id,
                "source_image": observation.source_image,
                "detection_method": observation.geometry.detection_method,
                "extraction_confidence": str(observation.confidence),
                "track_detection_confidence": str(geom.confidence),
            }
        )
