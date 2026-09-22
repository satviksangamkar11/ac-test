"""STEP 2A + 2B: Canonical Production Entry Point — Reference Extraction Engine

ONE authoritative production path from evidence to VerifiedReferenceState.

Flow:

    reference image
        ↓
    ReferenceExtractionEngine.extract()
        ├─ Universal structural extraction (V3)
        ├─ Calibration (GenericSliderCalibration)
        ├─ VerifiedStateBuilder integration
        ├─ ExpectedInventory reconciliation
        └─ Returns VerifiedReferenceState
        ↓
    Post-extraction:
    State is created but NOT verified (agreement=False).
    Independent audit is required before gate passes.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from pathlib import Path

from slider_evidence_extractor_v3 import (
    ExtractionRequest,
    SliderEvidenceExtractorV3,
    extraction_result_to_calibration_observation,
    ExtractionStatus,
)
from phase4_2_verified_state_adapter import (
    VerifiedStateBuilder,
    VerifiedReferenceState,
    VerifiedMatrixRoute,
)


@dataclass
class ReferenceExtractionRequest:
    """Request for reference-state extraction from evidence."""

    episode_id: str
    source_image_path: str
    matrix_routes: Optional[List[Dict]] = None  # [{"row_y": 160, "source": "...", "destination": "..."}]
    amount_column_x_range: Tuple[int, int] = (198, 324)
    use_universal_reference_selection: bool = True


@dataclass
class ReferenceExtractionResult:
    """Result of reference-state extraction."""

    episode_id: str
    verified_reference_state: Optional[VerifiedReferenceState] = None
    extraction_success: bool = False
    error_message: Optional[str] = None
    routes_extracted: int = 0
    routes_unverified: int = 0  # Initially all unverified
    extraction_provenance: Dict = None

    def __post_init__(self):
        if self.extraction_provenance is None:
            self.extraction_provenance = {}


class ReferenceExtractionEngine:
    """Canonical production entry point for reference-state extraction.

    STEP 2A + 2B: ONE production path.

    Do NOT create competing extraction paths.
    All extraction must route through this engine.
    """

    def __init__(self, engine_id: str = "reference_extraction_engine_v1"):
        self.engine_id = engine_id
        self.extractor = SliderEvidenceExtractorV3()

    def extract(
        self, request: ReferenceExtractionRequest
    ) -> ReferenceExtractionResult:
        """Extract reference state from evidence image.

        STEP 2B: Wire V3 extraction into real production path.

        Flow:
            Image
            → SliderEvidenceExtractorV3 (universal)
            → GenericSliderCalibration
            → VerifiedStateBuilder
            → VerifiedReferenceState (unverified)

        Returns:
            ReferenceExtractionResult with VerifiedReferenceState
            State is NOT verified (agreement=False on all routes).
            Independent audit required before gate passes.
        """

        result = ReferenceExtractionResult(
            episode_id=request.episode_id,
            extraction_provenance={
                "engine_id": self.engine_id,
                "episode_id": request.episode_id,
                "source_image": request.source_image_path,
                "extraction_method": "v3_universal_structural",
                "reference_selection_mode": "automatic"
                if request.use_universal_reference_selection
                else "manual",
            },
        )

        # Verify image exists
        image_path = Path(request.source_image_path)
        if not image_path.exists():
            result.error_message = f"Source image not found: {request.source_image_path}"
            return result

        # STEP 2A + 2B: ONE production path
        # No fixture-specific branches
        # No alternative extraction paths
        # All extraction through SliderEvidenceExtractorV3

        builder = VerifiedStateBuilder(episode_id=request.episode_id)

        # Extract each route specified
        if not request.matrix_routes:
            result.error_message = "No matrix_routes specified"
            return result

        extracted_routes = []
        for route_spec in request.matrix_routes:
            row_y = route_spec.get("row_y")
            source = route_spec.get("source")
            destination = route_spec.get("destination")
            route_id = route_spec.get("route_id") or f"{source}_{destination}"

            if not row_y or not source or not destination:
                continue

            # STEP 2B: Wire universal V3 extraction
            extraction_request = ExtractionRequest(
                observation_id=route_id,
                canonical_id="matrix.amount",
                row_detail=str(row_y),
                image_path=request.source_image_path,
            )

            extraction_result = self.extractor.extract(
                extraction_request,
                reference_row_ys=None,  # Universal auto-detection
                amount_column_x_range=request.amount_column_x_range,
                use_universal_selection=request.use_universal_reference_selection,
            )

            if extraction_result.status != ExtractionStatus.EXTRACTED:
                continue

            # STEP 2D: Create route-aware observation
            # VerifiedStateBuilder expects extraction_result, not calibration_observation
            try:
                control_value, matrix_route = builder.add_matrix_route_observation(
                    extraction_result,
                    route_id=route_id,
                    source=source,
                    destination=destination,
                )

                # STEP 2C: Preserve observation identity
                # Route identity must survive pipeline
                assert matrix_route.route_id == route_id
                assert matrix_route.source == source
                assert matrix_route.destination == destination

                # STEP 2I: Two-phase verification
                # Initially unverified
                assert matrix_route.agreement is False

                extracted_routes.append(matrix_route)
                result.routes_extracted += 1
                result.routes_unverified += 1

            except Exception as e:
                result.error_message = f"Failed to add route {route_id}: {e}"
                continue

        # STEP 2H: Build verified reference state
        if not extracted_routes:
            result.error_message = "No routes extracted"
            return result

        try:
            # STEP 2I: Two-phase verification
            # Finalize with NO audit provenance (state is unverified)
            # audit_provenance=None signals: extraction only, audit pending
            verified_state = builder.finalize(audit_provenance=None)

            # STEP 2C: Preserve provenance
            # All routes must retain identity and calibration provenance
            # matrix_routes is Dict[route_id, VerifiedMatrixRoute]
            for route_id, route in verified_state.matrix_routes.items():
                assert route.amount_source == "SLIDER_PIXEL_CALIBRATION"
                assert route.agreement is False  # Not verified yet

            result.verified_reference_state = verified_state
            result.extraction_success = True

        except Exception as e:
            result.error_message = f"Failed to finalize verified state: {e}"
            return result

        return result


if __name__ == "__main__":
    print("""
ReferenceExtractionEngine
=========================

Canonical production entry point for reference-state extraction.

STEP 2A + 2B: ONE production path from evidence to VerifiedReferenceState.

Do NOT create competing extraction paths.
All extraction must route through this engine.

Usage:
    engine = ReferenceExtractionEngine()

    result = engine.extract(
        request=ReferenceExtractionRequest(
            episode_id="HEEGN1Xl5o4",
            source_image_path="step3_04m35s_matrix_mod_routes.jpg",
            matrix_routes=[
                {
                    "row_y": 160,
                    "source": "LFO 1",
                    "destination": "Osc A Fine",
                },
                ...
            ],
        )
    )

    if result.extraction_success:
        print(f"Extracted {result.routes_extracted} routes")
        # Routes are unverified (agreement=False)
        # Independent audit required before gate passes

Features:
  • One canonical production path
  • Universal V3 extraction
  • No fixture-specific branches
  • Routes initially unverified
  • Provenance preserved end-to-end
  • Ready for independent audit
""")
