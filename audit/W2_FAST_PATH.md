# W2 Fast Path — LOCAL Session Handoff

**Branch:** `claude/gallant-cerf-u953wn`  
**Prepared from:** `8c716f6` (W2 partial) + cloud helper commit  
**Purpose:** Get from the current W2 partial state (0 admissible OBSERVED) to 1+ admissible
OBSERVED value as fast as possible, then immediately hand off to native W2 execution
(Phases 8–12 of W2_RUNBOOK.md).

---

## Current W2 State (from 8c716f6)

| Control | Frame | ts | VLM | OCR | Outcome | Admissible |
|---|---|---|---|---|---|---|
| env1.decay | frame_00024000 | 24s | 1.0 s | 1005 (fragmented) | AMBIGUOUS | No |
| oscA.octave | frame_00024000 | 24s | 0 | (no OCR) | AMBIGUOUS (single-source) | No |
| oscA.octave | frame_00034000 | 34s | -2 | (no OCR / minus-sign fail) | AMBIGUOUS (single-source) | No |
| oscA.rand_phase | frame_00034000 | 34s | 62 | 62 | **OBSERVED** | **No — no contract row** |

**Key insight:** `oscA.rand_phase` is genuinely corroborated but has no row in
`final_execution_contract_v1.json`. Do NOT add it. Do NOT modify the contract.

---

## Existing Artifacts (do not regenerate)

| Artifact | Path |
|---|---|
| Acquisition manifest | `tests/fixtures/w2/w2_acquisition_manifest.json` |
| Run metadata | `tests/fixtures/w2/w2_run_metadata.json` |
| C3 observation metrics | `tests/fixtures/w2/c3_observation_metrics.json` |
| Committed crops | `tests/fixtures/w2/crops/*.png` (6 crops) |
| Frame files | `serum2/data/visual_frames/yt_19935949eb0e/*.jpg` (LOCAL only) |

**269 frames are already on disk** at `serum2/data/visual_frames/yt_19935949eb0e/`.
Do NOT run yt-dlp or re-download the video.

The manifest maps frame IDs → artifact paths:

```python
from serum2.producer.w2_fast_path import load_existing_manifest, select_frames_by_timestamp
manifest = load_existing_manifest()
# frames in a timestamp window:
frames = select_frames_by_timestamp(manifest, 22.0, 28.0)
```

---

## Contract-Covered Controls (priority order for W2)

Use `serum2.producer.w2_fast_path.contract_covered_controls()` for the full 183-control
set. Priority candidates for this tutorial:

| Priority | Control | Reason | Positive value expected |
|---|---|---|---|
| 1 | `oscA.octave` | Visible at t=24s (VLM=0), needs OCR corroboration | ✓ (0, no minus sign) |
| 2 | `env1.decay` | Visible at t=24s, OCR fragmented; tighter ROI may fix | ✓ (1.0 s) |
| 3 | `lfo1.rate` | Core of wobble bass; likely visible t=38–100s | ✓ |
| 4 | `filter1.cutoff` | Sweep target; likely visible t=38–120s | ✓ |
| 5 | `env2.decay` | Second envelope if used; likely t=60–150s | ✓ |

**Excluded:**
- `oscA.rand_phase` — OBSERVED but no contract row.  
  Reason: `serum2.producer.w2_fast_path.rand_phase_exclusion_reason()`

---

## Stopping Rule

**STOP as soon as ONE contract-covered control reaches `OUTCOME_OBSERVED`.**  
Do not continue broad VLM analysis once an admissible OBSERVED candidate is available.  
Immediately proceed to Phase 8 (native Serum load + readback) of `audit/W2_RUNBOOK.md`.

---

## Candidate 1: oscA.octave at t=24s — HIGHEST PRIORITY

**Why:** VLM already read "0" with confidence 0.974 (single-source AMBIGUOUS). OCR was not
attempted on this frame at t=24s. Zero is OCR-friendly — no minus sign, single digit.

**Frame:** `frame_yt_19935949eb0e_00024000`  
**Artifact path:** `serum2/data/visual_frames/yt_19935949eb0e/frame_yt_19935949eb0e_00024000.jpg`

**Crop strategy:** Same ROI used for oscA octave row:
```python
from PIL import Image
img = Image.open("serum2/data/visual_frames/yt_19935949eb0e/frame_yt_19935949eb0e_00024000.jpg")
# The oscA octave row was previously cropped to tests/fixtures/w2/crops/frame_00024000_oscA_octrow.png
# Use a tighter crop targeting ONLY the numeric digit (avoid the label text "OCT"):
# Approximate Serum 2 OSC A panel: upper-right area of the screen.
# Adjust to the pixel bbox you see when you open the committed crop.
crop = img.crop((x1, y1, x2, y2))  # narrow to just the number, no "OCT" label
```

**OCR run:**
```python
import easyocr
from serum2.producer.w2_fast_path import numeric_ocr_profile

reader = easyocr.Reader(["en"], gpu=True)
profile = numeric_ocr_profile(signed=False, decimal=False)  # zero is unsigned integer
results = reader.readtext(crop_array, **profile)
# Extract numeric value and confidence from results
```

**VLM re-run:** NOT needed if OCR reads "0" — that's the corroboration. Only re-run VLM if
a different frame or crop is used.

**Temporal corroboration frames** (if t=24s OCR fails):
```python
from serum2.producer.w2_fast_path import temporal_candidates, load_existing_manifest
manifest = load_existing_manifest()
frames = temporal_candidates(manifest, "oscA.octave")
# Returns up to 3 frames from t=22-28s (zero-value window) and t=32-36s (fallback)
```

Use `adjudicated_observe()` with both VLM and OCR candidates for each frame.

---

## Candidate 2: env1.decay at t=24s — TIGHTER ROI

The previous OCR read `1005` from the env1 decay row (fragmentation: "1", "0", "5" from
label text "1.0 s"). Fix: crop only the numeric value, not the "s" unit or surrounding label.

**Frame:** `frame_yt_19935949eb0e_00024000`  
**Committed wide crop:** `tests/fixtures/w2/crops/frame_00024000_env1_row.png`

Use a tight crop of only the number region. If the env1 decay value is "1.0" or "1" (in
whichever display format), OCR with decimal=True should read it correctly:

```python
profile = numeric_ocr_profile(signed=False, decimal=True)
results = reader.readtext(tight_number_crop, **profile)
```

---

## Candidate 3: LFO1 rate in wobble section (~t=40–100s)

**Frames:** Use `temporal_candidates(manifest, "lfo1.rate")` to get 3 frames from t=38–100s.
LFO1 rate in a wobble bass is typically 1/4 note or a BPM-synced value.
Positive values, no minus sign.

```python
from serum2.producer.w2_fast_path import temporal_candidates, load_existing_manifest
manifest = load_existing_manifest()
lfo_frames = temporal_candidates(manifest, "lfo1.rate")
for fr in lfo_frames:
    # Open fr["artifact_path"], crop to LFO1 rate field, run VLM+OCR
    pass
```

---

## Generic OCR Profile

```python
from serum2.producer.w2_fast_path import numeric_ocr_profile

# For positive-only values (no minus sign):
profile = numeric_ocr_profile(signed=False, decimal=True)

# For signed values (include minus sign, lower priority due to minus-sign OCR failure):
profile = numeric_ocr_profile(signed=True, decimal=True)

# Profile contents (mag_ratio=2.0, beamWidth=10 — good for small Serum glyphs):
# allowlist: "0123456789." or "0123456789-."
# Do NOT add control-specific branches; all controls use this same profile.
```

**Known OCR weakness:** At native 1920×1080 resolution, the minus sign glyph is
unreliable. For signed-value controls (e.g. oscA.octave=-2), prefer frames where
the value is zero or positive if available.

---

## W2 adjudicated_observe() call template

```python
import hashlib
from serum2.producer.observation_engine import ObservationEngine

engine = ObservationEngine()

result = engine.adjudicated_observe(
    sources=[
        {"raw_value": vlm_output, "source": "qwen2.5-vl", "confidence": vlm_conf},
        {"raw_value": ocr_output, "source": "easyocr-1.7.2", "confidence": ocr_conf},
    ],
    context={
        "control_id": "oscA.octave",     # use the exact atlas_id
        "element_kind": "CONTROL",
        "control_type": "continuous",
        "unit": "",
        "roi_hash": hashlib.sha256(crop_bytes).hexdigest(),
    },
)

print(result.outcome)   # OBSERVED, AMBIGUOUS, UNREADABLE, or IDENTITY_UNRESOLVED
print(result.value)
print(result.single_source)
```

If `result.outcome == "OBSERVED"` and the control is contract-covered:
→ **STOP. Proceed to Phase 5 (state ledger) of W2_RUNBOOK.md.**

---

## Phase 5+ once OBSERVED is achieved

```python
# Phase 5: State ledger
from serum2.producer.state_ledger import derive
row = derive(control_id, result.value, ...)

# Phase 6: A2 admission gate (unchanged)
from serum2.producer.state_admission import admit_rows
from serum2.producer.execution_epoch import installed_epoch
admitted = admit_rows([row], epoch=installed_epoch())

# Phase 7–12: Follow audit/W2_RUNBOOK.md exactly
```

---

## C3 Metrics Update

After each `adjudicated_observe()` call, append to `tests/fixtures/w2/c3_observation_metrics.json`:

```python
c3_metrics.append({
    "control_id": control_id,
    "frame_id": frame["frame_id"],
    "timestamp_sec": frame["timestamp_sec"],
    "evidence_hash": result.evidence_hash,
    "adjudicated_outcome": result.outcome,
    "adjudicated_value": result.value,
    "single_source": result.single_source,
    "confident_wrong": False,      # update in Phase 11 after native readback
    "exact_match": False,          # update in Phase 11 after native readback
    "ocr_used_as_source": (
        not result.single_source and result.outcome == "OBSERVED"
        and any(s["source"].startswith("easyocr") for s in sources)
    ),
    "has_execution_contract_row": control_id in contract_covered_controls(),
})
```

---

## Fast Path Summary

```
STEP 1: open serum2/data/visual_frames/yt_19935949eb0e/frame_yt_19935949eb0e_00024000.jpg
STEP 2: crop to oscA octave number-only ROI (tight, no label text)
STEP 3: run easyocr with numeric_ocr_profile(signed=False, decimal=False)
STEP 4: if OCR reads "0" and VLM reads "0" → adjudicated_observe() → OBSERVED

IF STEP 4 succeeds:
  → Append to c3_observation_metrics.json
  → Phase 5 (state ledger) → Phase 6 (A2 gate) → Phases 7-12 (W2_RUNBOOK.md)

IF NOT:
  STEP 5: try env1.decay with tighter ROI (tight number crop, not full row)
  STEP 6: try lfo1.rate on temporal_candidates(manifest, "lfo1.rate") frames
  REPEAT until one contract-covered control reaches OBSERVED.
  NEVER proceed to Phase 8 with zero admissible OBSERVED values.
```

---

## Invariants — Do NOT violate

- `observation_policy.py` is unchanged; `CONFIDENT_THRESHOLD = 0.9`
- Single source at any confidence → AMBIGUOUS
- Multi-source agreement → OBSERVED (only)
- `oscA.rand_phase` → excluded (no contract row)
- `final_execution_contract_v1.json` → read-only
- `state_admission.admit_rows()` → unchanged, all OBSERVED values must pass through it
- No fake crops, no fabricated VLM/OCR output, no repeated-text corroboration
