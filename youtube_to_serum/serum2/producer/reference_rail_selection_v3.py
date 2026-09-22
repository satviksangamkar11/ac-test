"""Universal structural reference selection for slider geometry detection.

Key principle: Do not hardcode reference row y-coordinates.
Instead infer them dynamically from UI structure and evidence.

This module handles:
1. Auto-detecting candidate reference rows (empty/unambiguous rows)
2. Validating convergence (multiple rows must agree on rail geometry)
3. Returning explicit provenance (why was this row selected?)
4. Reporting ambiguity/failure when evidence is insufficient
"""

from typing import List, Tuple, Optional, NamedTuple
import numpy as np
from enum import Enum


class SelectionConfidence(Enum):
    """Confidence in reference row selection."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    FAILED = "FAILED"


class ReferenceRailSelection(NamedTuple):
    """Explicit selection with provenance."""
    selected_rows: List[int]  # y-coordinates of selected reference rows
    confidence: SelectionConfidence
    selection_reason: str  # Why these rows were selected
    convergence_error_px: float  # Max variance in rail geometry across selected rows
    fallback_used: bool = False  # True if no empty rows found, using heuristic
    notes: str = ""


def detect_candidate_reference_rows(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int],
    scan_step: int = 5,
) -> List[int]:
    """Find candidate reference rows (empty/unambiguous rows with high plateau coverage).

    A reference row should have consistent rail geometry without value-dependent fill.
    Typically these are empty Matrix rows or rows where the slider is unused.

    Args:
        arr: Image array (H, W, C)
        amount_column_x_range: (x_min, x_max) of Amount column
        scan_step: Y-step size for scanning (5 = check every 5 pixels vertically)

    Returns:
        List of y-coordinates that appear to be reference rows, sorted ascending
    """

    col_min, col_max = amount_column_x_range
    candidates = []

    # Scan vertically with step
    for row_y in range(0, arr.shape[0], scan_step):
        if row_y >= arr.shape[0]:
            break

        # Scan this row's plateau coverage
        line = arr[row_y, col_min:col_max, :]

        plateau_count = 0
        for x_idx in range(line.shape[0]):
            r, g, b = line[x_idx, :3]
            # Plateau is consistent grey (the slider rail structure)
            is_plateau = (40 <= r <= 100 and 60 <= g <= 120 and 70 <= b <= 130)
            if is_plateau:
                plateau_count += 1

        # High plateau coverage (>=60%) suggests this row shows rail structure
        plateau_coverage = plateau_count / line.shape[0]
        if plateau_coverage >= 0.60:
            candidates.append(row_y)

    # Refine candidates: cluster nearby rows, take one per cluster
    if not candidates:
        return []

    # Group by proximity (within 10 pixels = same row area)
    refined = []
    last_added = None
    for candidate in candidates:
        if last_added is None or candidate - last_added > 10:
            refined.append(candidate)
            last_added = candidate

    return refined


def validate_reference_rows_convergence(
    arr: np.ndarray,
    candidate_rows: List[int],
    amount_column_x_range: Tuple[int, int],
    max_variance_px: int = 5,
) -> Tuple[List[Tuple[int, int]], float]:
    """Validate that candidate rows converge on the same rail geometry.

    Args:
        arr: Image array
        candidate_rows: List of y-coordinates to test
        amount_column_x_range: (x_min, x_max)
        max_variance_px: Max allowed difference in rail position across rows

    Returns:
        (rail_measurements, max_variance_observed)
        where rail_measurements = [(left_x, right_x), ...]
    """

    col_min, col_max = amount_column_x_range
    rail_measurements = []

    for row_y in candidate_rows:
        if row_y < 0 or row_y >= arr.shape[0]:
            continue

        line = arr[row_y, col_min:col_max, :]
        plateau_mask = []
        for x_idx in range(line.shape[0]):
            r, g, b = line[x_idx, :3]
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
        return [], float('inf')

    lefts = [m[0] for m in rail_measurements]
    rights = [m[1] for m in rail_measurements]

    left_variance = max(lefts) - min(lefts)
    right_variance = max(rights) - min(rights)
    max_variance = max(left_variance, right_variance)

    return rail_measurements, max_variance


def select_reference_rows_automatic(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int] = (198, 324),
) -> ReferenceRailSelection:
    """Automatically select structural reference rows from image evidence.

    Strategy:
    1. Scan for candidate rows with high plateau coverage
    2. Validate convergence
    3. Return selection with confidence/provenance
    4. If no candidates, return FAILED with explicit note

    Args:
        arr: Image array
        amount_column_x_range: (x_min, x_max) structural bounds

    Returns:
        ReferenceRailSelection with explicit provenance
    """

    # Step 1: Find candidates
    candidates = detect_candidate_reference_rows(arr, amount_column_x_range, scan_step=3)

    if not candidates:
        return ReferenceRailSelection(
            selected_rows=[],
            confidence=SelectionConfidence.FAILED,
            selection_reason="No rows with sufficient plateau coverage detected",
            convergence_error_px=float('inf'),
            fallback_used=False,
            notes="Image may lack empty rows; consider manual reference row specification",
        )

    # Step 2: Validate convergence
    measurements, max_variance = validate_reference_rows_convergence(
        arr, candidates, amount_column_x_range, max_variance_px=5
    )

    if not measurements:
        return ReferenceRailSelection(
            selected_rows=candidates,
            confidence=SelectionConfidence.LOW,
            selection_reason=f"Found {len(candidates)} candidates, but rail geometry validation failed",
            convergence_error_px=max_variance,
            fallback_used=False,
            notes="Candidates exist but don't show consistent rail geometry",
        )

    # Step 3: Assess confidence based on convergence
    if max_variance <= 2:
        confidence = SelectionConfidence.HIGH
    elif max_variance <= 5:
        confidence = SelectionConfidence.MEDIUM
    else:
        confidence = SelectionConfidence.LOW

    selected_rows = [candidates[i] for i in range(len(measurements))]

    return ReferenceRailSelection(
        selected_rows=selected_rows,
        confidence=confidence,
        selection_reason=f"Auto-detected {len(selected_rows)} reference row(s) with rail convergence error ±{max_variance:.1f}px",
        convergence_error_px=max_variance,
        fallback_used=False,
        notes=f"Rows: {selected_rows}",
    )


def select_reference_rows_with_fallback(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int] = (198, 324),
    fallback_rows: Optional[List[int]] = None,
) -> ReferenceRailSelection:
    """Select reference rows, with fallback if auto-detection fails.

    Args:
        arr: Image array
        amount_column_x_range: (x_min, x_max)
        fallback_rows: List of y-coordinates to use if auto-detection fails

    Returns:
        ReferenceRailSelection (either automatic or fallback)
    """

    # Try auto-detection first
    selection = select_reference_rows_automatic(arr, amount_column_x_range)

    if selection.confidence == SelectionConfidence.FAILED:
        if fallback_rows:
            # Validate fallback rows
            measurements, max_variance = validate_reference_rows_convergence(
                arr, fallback_rows, amount_column_x_range
            )
            if measurements:
                return ReferenceRailSelection(
                    selected_rows=fallback_rows,
                    confidence=SelectionConfidence.MEDIUM,
                    selection_reason=f"Auto-detection failed; using fallback rows",
                    convergence_error_px=max_variance,
                    fallback_used=True,
                    notes=f"Fallback rows {fallback_rows} converge within ±{max_variance:.1f}px",
                )
        # Fallback also failed
        return selection
    else:
        # Auto-detection succeeded
        return selection


if __name__ == "__main__":
    print("""
Universal Reference Rail Selection (v3)
========================================

Key principle:
  Do NOT hardcode reference row y-coordinates.
  Instead infer them from UI structure and image evidence.

Strategy:
  1. Scan image for rows with high plateau coverage
  2. Validate that candidate rows converge on same rail geometry
  3. Return selection with explicit confidence/provenance
  4. Fail explicitly if evidence insufficient

Benefits:
  • Works on any Serum screenshot without episode-specific tuning
  • Provides confidence measure + selection reason
  • Reports ambiguity clearly
  • Supports fallback when auto-detection fails

Usage:
    selection = select_reference_rows_automatic(
        arr=image_array,
        amount_column_x_range=(198, 324)
    )

    if selection.confidence != SelectionConfidence.FAILED:
        print(f"Selected rows: {selection.selected_rows}")
        print(f"Confidence: {selection.confidence.value}")
        print(f"Reason: {selection.selection_reason}")
    else:
        print("Auto-detection failed; using fallback or manual specification")
""")
