# W2 Windows Runbook

**Purpose:** Final product proof — one untouched tutorial → full pipeline → `reference_verified=True` +
COMPLETE coverage + 16-bar Ableton render with audible signal. Also serves as the larger real-world
C3 validation: every parameter observation must go through `adjudicated_observe()` and the
C3 metrics must be recorded.

**Requires:**
- Windows machine, Serum 2.0.23 VST3 (`9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3`)
- Ableton 11.3, serum-mcp bridge active on port 8765
- `SERUM_PRESETS_PATH` environment variable set
- easyocr 1.7.2 installed (for OCR corroboration — required for C3 metrics)
- Qwen2.5-VL-3B-Instruct available locally (or any local VLM)
- Repo at `claude/gallant-cerf-u953wn`, latest commit

**Hard rules:**
- Real Windows/Ableton/Serum only — no DawDreamer substitution
- Loaded-module SHA must match `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3`
- No fake screenshots, no fabricated UI readbacks
- No bypassing A2 or the final execution contract

---

## Prerequisites

Verify epoch before starting:

```python
from serum2.producer.execution_epoch import installed_epoch
e = installed_epoch()
assert e.binary_sha256 == "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3", e
print("Epoch OK:", e.label)
```

---

## Phase 1 — Select an untouched tutorial

Pick a real YouTube tutorial that:
- Has not been used in any previous evidence run
- Contains at least 5 distinct Serum parameter settings visible in the video
- Is NOT the CAL_* or BULK_* presets from C3 ground truth

Record the YouTube URL. This URL must NOT be a URL from any previous run.

---

## Phase 2 — Exhaustive frame acquisition

```python
from serum2.source.acquire_visual_evidence import acquire_visual_evidence

bundle = acquire_visual_evidence(
    url="<TUTORIAL_URL>",
    max_frames=None,          # decode ALL frames, no truncation
    sample_interval_sec=2.0,  # or appropriate for the video length
)
assert not bundle.storyboard_only, "storyboard fallback is not acceptable for value reading"
assert bundle.duration is not None, "ffprobe must return duration"
print(f"Acquired {len(bundle.frames)} frames from {bundle.duration:.1f}s video")
```

Every frame must have `sha256` and `frame_index`. The cache key includes `max_frames`
and `sample_interval_sec` — changing either forces re-acquisition.

---

## Phase 3 — ASR / transcript

Run the existing ASR pipeline on the video audio to extract the transcript.
The transcript is advisory context only — it does NOT authorize any parameter value.

---

## Phase 4 — Stage-A (VLM/OCR observation + C3 metrics)

For every Serum-visible frame, for every parameter identified:

```python
from serum2.producer.observation_engine import ObservationEngine
from serum2.producer.observation_policy import OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS

engine = ObservationEngine()
c3_metrics = []

for param in identified_parameters:
    result = engine.adjudicated_observe(
        sources=[
            {"raw_value": vlm_output, "source": "qwen2.5-vl", "confidence": vlm_confidence},
            {"raw_value": ocr_output, "source": "easyocr-1.7.2", "confidence": ocr_confidence},
        ],
        context={
            "control_id": param.atlas_id,     # e.g. "env2.decay"
            "element_kind": "CONTROL",
            "control_type": "continuous",
            "unit": param.unit,
            "roi_hash": crop_sha256,           # SHA256 of the crop image
        },
    )
    c3_metrics.append({
        "control_id": param.atlas_id,
        "frame_index": frame.index,
        "adjudicated_outcome": result.outcome,
        "adjudicated_value": result.value,
        "confident_wrong": False,              # set True only if ground truth available
        "exact_match": False,                  # set True after native readback comparison
        "ocr_used_as_source": not result.single_source and result.outcome == OUTCOME_OBSERVED,
        "vlm_confidence": vlm_confidence,
        "evidence_hash": result.evidence_hash,
        "single_source": result.single_source,
    })
```

Record counts:
- Total observations
- OBSERVED (corroborated)
- AMBIGUOUS (abstained)
- UNREADABLE
- IDENTITY_UNRESOLVED
- single_source count
- confident_wrong count (requires comparison to native readback)
- exact_match count (requires comparison to native readback)

This is the real-world C3 population expansion. Write the full `c3_metrics` list to
`tests/fixtures/w2/c3_observation_metrics.json`.

---

## Phase 5 — State ledger

Only `OBSERVED` values from Phase 4 enter the state ledger. `AMBIGUOUS`, `UNREADABLE`,
and `IDENTITY_UNRESOLVED` values are discarded — they are NOT passed to `_coerce()`.

```python
from serum2.producer.state_ledger import derive
for obs in c3_metrics:
    if obs["adjudicated_outcome"] == "OBSERVED":
        row = derive(obs["control_id"], obs["adjudicated_value"], ...)
        # proceed to admission
```

---

## Phase 6 — Admission (A2 gate)

```python
from serum2.producer.state_admission import admit_rows
admitted = admit_rows(rows, epoch=installed_epoch())
# Only admitted rows reach the compiler
```

The A2 gate and final execution contract check run here. Nothing from C3 bypasses this.

---

## Phase 7 — Compile + generate .SerumPreset

```python
from serum2.execution.authorized_state_compiler import compile_ops
ops = compile_ops(admitted_rows)
# ... generate the .SerumPreset
```

---

## Phase 8 — Native Serum load + readback

Use `create_serum_track()` to load the generated `.SerumPreset` into real Ableton/Serum 2.0.23.
Verify the loaded-module SHA:

```python
result = create_serum_track(preset_path=preset_path)
assert result.serum_module_sha256 == "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"
```

Capture a screenshot of the Serum UI showing the loaded parameters.
Perform native re-save: File → Save As → `native_resave_w2.SerumPreset`.
Run `readback_diff.py` against the compiled preset.

---

## Phase 9 — Reference reproduction (LIVE_UI_VERIFIED)

```python
from youtube_to_serum.reference_engine import run_reference_reproduction

run = run_reference_reproduction(
    stage_a=stage_a,                    # the completed Stage-A from Phase 4
    ui_readback={
        "route": "DIRECT_UI",
        "values": {control_id: value, ...},  # from the native Serum UI screenshot
        "method": "manual_screenshot",
        "screenshot_sha256": screenshot_sha256,   # SHA256 of the saved screenshot file
        "loader_evidence": {
            "run_id": result.run_id,
            "track_nonce": result.track_nonce,
            "serum_module_sha256": result.serum_module_sha256,
        },
    },
    readback_verified=True,
)
assert run.proof_level == "LIVE_UI_VERIFIED"
assert run.coverage_status == "COMPLETE"
assert run.reference_verified is True
```

The `ui_readback` dict MUST carry loader evidence (module SHA, track nonce, run ID).
A self-declared dict without loader evidence is rejected. `readback_verified=True`
alone is not sufficient.

---

## Phase 10 — 16-bar Ableton render

Create a 16-bar MIDI clip in an Arrangement track (not session mode — session clips
do not trigger on arrangement render). Use a stock MIDI pattern.

```python
# Set up 16-bar MIDI clip with notes at standard pitches
# Place Serum on the Instrument track
# Render: File → Export Audio/Video → 44100 Hz, 24-bit WAV, full arrangement length
# Verify the output WAV has non-zero audio (RMS > -60 dBFS)
```

Save the WAV as `tests/fixtures/w2/w2_render_16bar.wav`.
Record the RMS level and peak level.

---

## Phase 11 — Update C3 metrics with native readback comparison

After the native readback (Phase 8), compare each `OBSERVED` Stage-A value against the
native re-save value. Update `c3_metrics`:

```python
for m in c3_metrics:
    if m["adjudicated_outcome"] == "OBSERVED":
        native_value = readback_diff[m["control_id"]]
        m["exact_match"] = abs(float(m["adjudicated_value"]) - float(native_value)) < 1e-3
        m["confident_wrong"] = not m["exact_match"]
```

Rewrite `tests/fixtures/w2/c3_observation_metrics.json` with updated metrics.

---

## Phase 12 — Commit W2 evidence bundle

Commit the following to `tests/fixtures/w2/`:

```
tests/fixtures/w2/
  w2_cert3.json              (Product certificate — see below)
  w2_run_metadata.json       (run_id, atlas_ids, epoch SHA, etc.)
  w2_hashes.json             (SHA256 of generated .SerumPreset, native re-save, module)
  w2_readback_diff.json      (compiled vs native re-save values)
  w2_screenshot.png          (native Serum UI screenshot — SHA256 in cert)
  c3_observation_metrics.json (C3 metrics from Stage-A, updated with readback comparison)
  w2_render_16bar.wav        (16-bar render — committed or SHA recorded if too large)
```

---

## Product Certificate (Cert 3)

```json
{
  "cert_type": "PRODUCT_CERT_3",
  "gate_b_status": "CANONICAL_GATE_B_VERIFIED",
  "proof_level": "LIVE_UI_VERIFIED",
  "reference_verified": true,
  "coverage_status": "COMPLETE",
  "render_verified": true,
  "render_rms_dbfs": "<actual value>",
  "c3_real_readable_n": "<count from c3_observation_metrics>",
  "c3_real_confident_wrong": 0,
  "c3_corroborated_count": "<count of OBSERVED with OCR>",
  "epoch": "2.0.23@9293eb90",
  "epoch_binary_sha256": "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3",
  "serum_module_sha256": "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3",
  "dawdreamer_used": false,
  "headless_substitution_used": false
}
```

---

## C3 metrics to record in the commit message

The commit message for the W2 evidence bundle must include:

```
C3 real-world validation (from W2):
  real_readable_n: <N>
  observed_corroborated: <count with OUTCOME_OBSERVED>
  abstained: <count with OUTCOME_AMBIGUOUS>
  identity_unresolved: <count>
  confident_wrong: <must be 0>
  exact_match: <count>
```

If `confident_wrong > 0`, do NOT commit — diagnose the failure first.

---

## Cloud-only remaining blockers (none for W2 execution)

All cloud-side prerequisites are complete:
- Gate A (A1/A2/A3 authority + domain + epoch): done
- Gate B cert2 (env2.decay native proof): done
- C3 remediation (GAP A/B/C): done
- Observation policy tests: green
- Full test suite: 1412/21/16 (all 21 failures pre-existing, environment-bound)

The only remaining work is Windows-local:
1. Select untouched tutorial
2. Run exhaustive frame acquisition
3. Run VLM/OCR Stage-A with C3 metrics recording
4. Run ProducerBrain → compile → native load → readback → native re-save
5. Verify `reference_verified=True` and `COMPLETE`
6. Render 16-bar arrangement with audible signal

**Entry point:** Start with Phase 1 (select tutorial) then execute Phases 2–12 in order.
