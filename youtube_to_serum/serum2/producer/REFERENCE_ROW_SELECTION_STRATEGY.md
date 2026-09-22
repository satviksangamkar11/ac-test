# Reference Row Selection Strategy

## The Problem

The v3 structural rail detector needs reference rows (empty/unpopulated Matrix slots) to establish the fixed slider rail geometry.

Currently: **hardcoded to `y=280`** for HEEGN1Xl5o4

This works for that screenshot, but:
- Not a universal Serum rule
- Episode-specific, rendering-specific
- Doesn't scale to other episodes or Matrix layouts
- Risk: Using wrong reference row could silently break detection

## What Makes a Good Reference Row?

A reference row is a Matrix row that:
1. Is **visually empty** (no populated route)
2. Clearly shows the **structural rail geometry** (track background)
3. Has **consistent plateau appearance** across the Amount column
4. Does **not contain fill value** (because no route is set)

When a row is empty, what you see IS the rail structure with no value-dependent fill obscuring it.

## Auto-Detection Algorithm

### Candidate Selection

Scan all rows in the Matrix grid looking for:

```python
def is_candidate_reference_row(arr, row_y, amount_column_x_range):
    """Check if row exhibits empty/reference characteristics."""
    
    col_min, col_max = amount_column_x_range
    line = arr[row_y, col_min:col_max, :]
    
    # Count plateau pixels (grey, minimal variance)
    plateau_count = 0
    plateau_pixels = []
    
    for x in range(col_min, col_max):
        r, g, b = arr[row_y, x, :3]
        is_plateau = (40 <= r <= 100 and 60 <= g <= 120 and 70 <= b <= 130)
        if is_plateau:
            plateau_count += 1
            plateau_pixels.append(x)
    
    # For an empty row, expect high plateau coverage
    plateau_ratio = plateau_count / (col_max - col_min)
    
    # For reference row: expect ≥70% plateau (not a filled slider)
    if plateau_ratio < 0.70:
        return False, plateau_ratio
    
    # For reference row: expect continuous plateau (no gaps)
    if len(plateau_pixels) > 0:
        max_gap = 0
        for i in range(1, len(plateau_pixels)):
            gap = plateau_pixels[i] - plateau_pixels[i-1]
            max_gap = max(max_gap, gap)
        
        if max_gap > 5:  # More than 5px gap suggests value fill
            return False, plateau_ratio
    
    return True, plateau_ratio
```

### Convergence Validation

Multiple candidate rows should converge on the **same rail geometry**:

```python
def validate_reference_rows(arr, candidate_rows, amount_column_x_range):
    """Check that candidate rows converge on same rail."""
    
    measurements = []
    
    for row_y in candidate_rows:
        line = arr[row_y, col_min:col_max, :]
        plateau_mask = [(40 <= r <= 100 and 60 <= g <= 120 and 70 <= b <= 130)
                        for r, g, b in line[:, :3]]
        
        indices = [i for i, p in enumerate(plateau_mask) if p]
        if indices:
            left = col_min + indices[0]
            right = col_min + indices[-1]
            measurements.append((left, right))
    
    # All measurements should be identical (or within 1-2px tolerance)
    if not measurements:
        raise error("No valid reference rows found")
    
    lefts = [m[0] for m in measurements]
    rights = [m[1] for m in measurements]
    
    if max(lefts) - min(lefts) > 2 or max(rights) - min(rights) > 2:
        raise error("Reference rows don't converge: possible detection error")
    
    # Return consensus
    return (
        median(lefts),
        median(rights),
        measurements,
        candidate_rows,
    )
```

## Result: ReferenceRailCandidate

```python
@dataclass
class ReferenceRailCandidate:
    """Auto-detected reference rail with provenance."""
    left_pixel: int
    right_pixel: int
    confidence: float  # How confident in this detection
    source_rows: List[int]  # Which rows agreed
    selection_reason: str  # Why this was chosen
    convergence_error: float  # How much rows varied
    plateau_coverage: float  # % of column that is plateau
```

## Selection Priority

1. **Converged candidates** (multiple rows agreeing)
   - Highest confidence
   - Use all rows for consensus
   
2. **Single strong candidate** (single row, high plateau coverage)
   - Medium confidence
   - Use that row's geometry
   
3. **No candidates found**
   - Raise error: "Cannot establish structural rail"
   - Likely reason: Matrix layout different from expected

## Current State (HEEGN1Xl5o4)

```
Candidate Reference Rows:
  Row 256: plateau 40-75%, continuity OK, geometry [210, 315]
  Row 280: plateau 93%, continuity OK, geometry [198, 323] ✓
  Row 300: plateau 88%, continuity OK, geometry [198, 323] ✓

Convergence Test:
  Rows 280 + 300: geometry identical (198–323)
  Row 256: significantly different (210–315)

Selection:
  Confidence: HIGH (rows 280 + 300 converge)
  Chosen Rail: [198, 323]
  Source Rows: [280, 300]
  Convergence Error: 0px
  Plateau Coverage: 90% (average of 280 + 300)
```

## Implementation

```python
def auto_detect_reference_rows(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int],
    grid_row_ys: List[int],  # All possible Matrix row positions
) -> Tuple[StructuralRail, ReferenceRailCandidate]:
    """Auto-detect reference rows and establish structural rail.
    
    Returns:
        (rail, metadata) where metadata explains the selection
    """
    # Step 1: Find candidates
    candidates = []
    for row_y in grid_row_ys:
        is_candidate, plateau_coverage = is_candidate_reference_row(arr, row_y, ...)
        if is_candidate:
            candidates.append({
                'row_y': row_y,
                'plateau_coverage': plateau_coverage,
            })
    
    # Step 2: Validate convergence
    candidate_rows = [c['row_y'] for c in candidates]
    left, right, measurements, agreeing_rows = validate_reference_rows(...)
    
    # Step 3: Create rail + metadata
    rail = StructuralRail(
        left_pixel=left,
        right_pixel=right,
        width=right - left,
        center_x=(left + right) / 2.0,
    )
    
    metadata = ReferenceRailCandidate(
        left_pixel=left,
        right_pixel=right,
        confidence=len(agreeing_rows) / len(candidates),  # How many agreed?
        source_rows=agreeing_rows,
        selection_reason=f"Converged from {len(agreeing_rows)} empty rows",
        convergence_error=max(rights) - min(lefts),
        plateau_coverage=np.mean([c['plateau_coverage'] for c in candidates]),
    )
    
    return rail, metadata
```

## Open Questions

1. **What if no empty rows are visible?**
   - Could happen in a crowded Matrix or screenshot from middle of edit
   - Fallback: Use Amount-column structural bounds as prior (198–324)
   - Risk: Less robust than reference-row detection

2. **What if candidate rows disagree significantly?**
   - Could indicate: misidentified row types, JPEG compression artifacts, rendering anomaly
   - Action: Raise `AmbiguousGeometry` error, require manual inspection
   - Don't silently pick one; let the system know detection was uncertain

3. **How to handle non-horizontal sliders?**
   - Current code assumes horizontal (x-range detection)
   - Vertical sliders would need y-range detection
   - Defer: Only implement horizontal for Phase 4.2.1

## Next Steps

1. Implement auto-detection in `slider_geometry_detector_v3.py`
   - Make reference row selection explicit, not hardcoded
   - Return `ReferenceRailCandidate` metadata

2. Add tests
   - `test_reference_row_auto_detection.py`
   - Test convergence validation
   - Test fallback behavior

3. Validate on additional episodes
   - Run on HEEGN1Xl5o4 (should find rows 280/300)
   - Run on at least one other reference episode
   - Verify convergence holds

4. Document fallback strategy
   - What to do if no empty rows visible
   - How to recover from detection failure

---

**Key insight:** The reference row selection is not just an implementation detail. It's a **measurement guarantee**. If we can't explain why a reference row was selected, we can't fully trust the resulting rail measurement. Making this explicit and validated is essential for Phase 4.2.1 closure.
