# One-Command Pipeline: Universal YouTube → Serum → Ableton Runner

**Command:**
```
python -m serum2.pipeline <youtube-url-or-id> [options]
```

**Branch:** `claude/gallant-cerf-u953wn`

---

## Purpose

A single resumable runner that composes all pipeline stages in strict order.
Parameter-agnostic: no `if control_id == "..."` branches anywhere in the runner.
Fail-closed: produces `PRODUCT_NOT_CLOSED` if any mandatory gate is unmet.

---

## Command Reference

```
python -m serum2.pipeline <youtube-url-or-id> [options]

Positional:
  youtube_url             YouTube video URL or video ID

Options:
  --work-dir DIR          Run directory (default: serum2/data/pipeline_runs/<video_id>)
  --sample-interval-sec N Frame sampling interval in seconds (default: 2.0)
  --max-frames N          Maximum frames to acquire (default: all)
  --resume                Resume from last saved state (default: True)
  --no-resume             Start fresh, ignore saved state
  --dry-run               Print run_id without executing stages
  --status                Print status of an existing run and exit
```

**Exit codes:**
- `0` — PRODUCT_CLOSED (all gates passed)
- `1` — FAILED or PRODUCT_NOT_CLOSED
- `2` — AWAITING_INPUT (halted at a LOCAL_NATIVE boundary; re-run after Windows steps)

---

## Stage Graph

```
CLOUD ────────────────────────────────────────────────────────────────────────────
 ACQUIRE           Download video, extract frames (sample_interval_sec, max_frames)
   │                 Cache key: hash(url, interval, max_frames)
   ▼
 TRANSCRIPT        Extract spoken content with timestamps
   │                 Identifies Serum-UI moments in the tutorial
   ▼
 VISUAL_EVIDENCE   Frame artifact inventory + storyboard detection guard
   │                 Records artifact paths + SHA-256 per frame
   │
 ─── CLOUD/LOCAL_NATIVE BOUNDARY ────────────────────────────────────────────────
   │
LOCAL_NATIVE ────────────────────────────────────────────────────────────────────
   ▼
 OBSERVATION       VLM (Qwen2.5-VL) + OCR per frame
   │                 adjudicated_observe() per control
   │                 contract_covered_controls() + filter_contract_covered() (generic)
   │                 HALTS with AWAITING_INPUT if no c3_observation_metrics.json
   │                 ─── PRODUCT_NOT_CLOSED if 0 admissible OBSERVED ───
 ─── LOCAL / CLOUD ────────────────────────────────────────────────────────────────
CLOUD ─────────────────────────────────────────────────────────────────────────────
   ▼
 LEDGER            derive() per admitted observation → Row records
   ▼
 ADMISSION         admit_rows() — A2 gate (mandatory, no bypass)
   │                 ─── PRODUCT_NOT_CLOSED if 0 rows admitted ───
   ▼
 COMPILE           authorized_state_compiler.compile_ops()
   │                 Only admitted rows with valid execution contracts compile
   │
 ─── CLOUD/LOCAL_NATIVE BOUNDARY ────────────────────────────────────────────────
LOCAL_NATIVE ────────────────────────────────────────────────────────────────────
   ▼
 NATIVE_LOAD       create_serum_track() → module SHA check
   │                 Verified: Serum 2.0.23 SHA = 9293eb90...bf9b3
   ▼
 NATIVE_VERIFY     Screenshot-bound readback, native re-save diff
   │                 proof_level must be LIVE_UI_VERIFIED
   ▼
 REFERENCE_VERIFY  run_reference_reproduction() with bound create_serum_track evidence
   │                 reference_verified=True only if coverage_status=COMPLETE
   ▼
 ARRANGE           16-bar Ableton arrangement clip
   ▼
 RENDER            Export WAV, check RMS > -60 dBFS (no silent render)
   │
 ─── LOCAL / CLOUD ────────────────────────────────────────────────────────────────
CLOUD ─────────────────────────────────────────────────────────────────────────────
   ▼
 FINALIZE          Collect all gate results, write certificate
                    PRODUCT_CLOSED requires ALL of:
                      • native_verified = True
                      • reference_verified = True
                      • coverage_status = COMPLETE
                      • proof_level = LIVE_UI_VERIFIED
                      • render RMS > -60 dBFS
                      • serum_module_sha256 matches pinned SHA
                    Otherwise: PRODUCT_NOT_CLOSED
```

---

## Resume Semantics

Each stage's result is persisted to `<work_dir>/pipeline_manifest.json` after completion.
Re-running with `--resume` (the default) skips COMPLETE and SKIPPED stages.

The runner halts at LOCAL_NATIVE stages with `AWAITING_INPUT` status and prints
exact instructions for the Windows session. After completing those steps and
committing evidence to `tests/fixtures/`, re-run:

```bash
python -m serum2.pipeline <url> --resume
```

---

## Cache Validation

| What is cached | Cache key | Invalidated when |
|---|---|---|
| Acquired frames | `hash(url, sample_interval_sec, max_frames)` | URL, interval, or max_frames changes |
| Stage outputs | Per-stage `cache_key` in manifest | Inputs change |
| Contract | `content_hash(final_execution_contract_v1.json)` | Contract file changes |

SKIPPED status is only set when the cache key matches. A FAILED stage is never skipped.

---

## Local/Native Boundary

Stages requiring Windows + Serum 2.0.23 + Ableton:

| Stage | Requires |
|---|---|
| OBSERVATION | Qwen2.5-VL (local GPU), EasyOCR |
| NATIVE_LOAD | Serum 2.0.23 VST3, Ableton |
| NATIVE_VERIFY | Serum 2.0.23 + screenshot binding |
| REFERENCE_VERIFY | Serum 2.0.23 + run_reference_reproduction |
| ARRANGE | Ableton arrangement |
| RENDER | Ableton WAV export |

CLOUD-only stages (can run without Serum or Ableton):
ACQUIRE, TRANSCRIPT, VISUAL_EVIDENCE, LEDGER, ADMISSION, COMPILE, FINALIZE

---

## Failure Semantics

- A stage failure records `status=FAILED` with `failure_reason` in the manifest.
- The runner records `PRODUCT_NOT_CLOSED` + `failure_stage` on the manifest.
- Exit code 1 is returned.
- No stage output is fabricated; no gate is bypassed.

The only way to reach PRODUCT_CLOSED is for every mandatory gate to pass genuinely:
- Observations from real VLM+OCR on real frames
- Admission through `admit_rows()` with real contract rows
- Native verification with the pinned Serum 2.0.23 module
- Reference reproduction with COMPLETE coverage
- Audible 16-bar render (RMS above threshold)

---

## Closure Criteria

`PRODUCT_CLOSED` requires (checked in FINALIZE):

1. `native_verified == True` — `create_serum_track` module SHA matched
2. `reference_verified == True` — `run_reference_reproduction` returned `reference_verified=True`
3. `coverage_status == "COMPLETE"` — all manifest frames have terminal analysis_status
4. `proof_level == "LIVE_UI_VERIFIED"` — native readback bound to screenshot + module SHA
5. `render_rms_dbfs > -60.0` — WAV file has audible signal
6. `serum_module_sha256 == "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"` — pinned Serum 2.0.23

Failure of any gate → `PRODUCT_NOT_CLOSED` with `failure_stage` pointing to the first gate that failed.

---

## Fast-Path Helpers

`serum2.producer.w2_fast_path` provides `contract_covered_controls()` and
`filter_contract_covered()`, which are **evidence/cache optimizations only**.
They are not parameter-specific orchestration. The runner uses them generically
to select which controls from the execution contract to observe; it never names
specific parameter IDs (e.g. `oscA.octave`, `env1.decay`).

When the OBSERVATION stage cannot find VLM+OCR tools, it halts with
`AWAITING_NATIVE_ENVIRONMENT`. Running the same command on the LOCAL Windows
machine (with Qwen2.5-VL-3B-Instruct and easyocr-1.7.2) causes the runner to
automatically execute the full observation census for all contract-covered
controls and write `c3_observation_metrics.json` to the run directory.

---

## Key Invariants (tested in tests/test_pipeline_runner.py)

- `oscA.rand_phase` is never referenced in runner.py
- No `if control_id == "..."` branches in runner.py
- `admit_rows()` is always called; no bypass path exists
- `DawDreamer` is not imported anywhere in runner.py
- Serum 2.0.23 SHA is pinned: certificate records `dawdreamer_used: False`
- `PRODUCT_CLOSED` certificate includes `failures: []`
- `PRODUCT_NOT_CLOSED` certificate includes all failing gate names
- `OBSERVATION` stage boundary is `LOCAL_NATIVE` — cannot be fabricated in cloud
- No `tests/fixtures/w2/` paths in runner.py — fully tutorial-agnostic
- All native-boundary halts use `halted_for: "AWAITING_NATIVE_ENVIRONMENT"`

---

## Files

| File | Description |
|---|---|
| `serum2/pipeline/__init__.py` | Package marker |
| `serum2/pipeline/__main__.py` | `python -m serum2.pipeline` entry point |
| `serum2/pipeline/runner.py` | Universal 13-stage orchestrator |
| `serum2/pipeline/stage_manifest.py` | Durable stage records + RunManifest |
| `tests/test_pipeline_runner.py` | 83 deterministic tests |

---

## LOCAL Execution Procedure (after CLOUD stages complete)

After the CLOUD stages have run and the runner halts at `AWAITING_NATIVE_ENVIRONMENT`:

1. On the Windows machine with Serum 2.0.23 and Ableton 11.3:
   ```
   git pull origin claude/gallant-cerf-u953wn
   python -m serum2.pipeline <url> --resume
   ```

2. The runner automatically proceeds through OBSERVATION using Qwen2.5-VL on
   the local GPU and EasyOCR. No separate observation command is needed.
   Observation results are written to `<work_dir>/c3_observation_metrics.json`.

3. After OBSERVATION completes, the runner continues through LEDGER → ADMISSION
   → COMPILE automatically.

4. NATIVE_LOAD, NATIVE_VERIFY, REFERENCE_VERIFY, ARRANGE, RENDER all require
   active Serum 2.0.23 in Ableton. The runner calls the serum-mcp bridge
   for each automatically. No separate commands are needed.

5. Once FINALIZE completes, check exit code 0 for PRODUCT_CLOSED.
   The certificate is at `<work_dir>/pipeline_certificate.json`.

---

*See also: `audit/W1_RUNBOOK.md` (Gate B native verification runbook)*
