# Gate B: ROI Evidence Provenance + Completeness Audit

**Scope:** the 5 source images and 5 crops used by the Gate A benchmark (`five_roi_tests.py` @ commit `80e5183`). No production code changed. No Gate C work started.

**Method:** each source image and crop was independently re-opened and visually inspected in this session — not inferred from the existing JSON, filenames, or prior notes. Findings below come from direct pixel observation, cross-checked against `five_roi_test_results.json`.

---

## Audit table

| Image | Target | Visible state | Current JSON captures | Missing state | Observation modality | Status |
|---|---|---|---|---|---|---|
| `step2_03m14s_filter_mg18_setup` | oscA.unison | Unison=7; OSC A waveform (sawtooth shape rendered); OCT=-1, SEM=0, FIN=0; wavetable name "Default Shapes" + WT POS knob | Unison=7 only | Waveform shape; OCT/SEM/FIN text; wavetable name/WT POS | CONTROL (text) captured; shape needs a separate WAVEFORM_SHAPE_OBSERVED record | **PARTIAL** |
| `step3_04m35s_matrix_mod_routes` | matrix.row[Env2→Filter1Freq] | Source="Env 2", Destination="Filter 1 Freq", Amount=visual slider only (no text anywhere), bipolar/unipolar icon | Source + Destination text | **Amount value — zero text representation exists in the UI at all**; toggle icon state; 4 other matrix rows not in scope | ROUTE (text) captured for source/dest; Amount needs pixel-position calibration, not OCR — untested modality | **PARTIAL** |
| `step2_02m08s_lfo1_lorenz_full_pattern` | lfo1.mode | Text "Chaos: Lorenz"; separately, an actual rendered Lorenz attractor curve (animated, dynamic) | Text only | Curve rendering itself | SELECTOR (text) captured; curve likely NOT_APPLICABLE as a distinct preset parameter (animated visualization of live chaos process, not a stored value) — **flagged as open judgment call, not resolved here** | **PARTIAL** |
| `step5_07m04s_main_delay_ping_pong` | fx.overdrive.drive | Drive=1.9; Hyper/Dimension (Rate=7, Unison toggle, Detune/Size/Mix knobs); EQ (an actual response curve drawn, plus Freq/Q/Gain ×2 bands); Delay (sync times, Feedback/Freq knobs, spectrum panel); Distortion header icon | Drive=1.9 only | Everything else in this FX chain — most under-sampled frame in the set | CONTROL (text) captured for Drive; EQ curve needs GRAPH modality; all knob values need CONTROL (text) modality, untested here | **PARTIAL** |
| `step1_01m09s_osc_a_sawtooth_setup` | voicing.legato | Legato checkbox=unchecked(OFF); **same crop bbox also contains** Mono checkbox=unchecked, Poly=8, "0/8" voice-count meter; elsewhere in frame: OSC waveforms, ENV1 curve, LFO curve | Legato=OFF only | Mono, Poly, voice-count (and note: voice-count is *runtime state*, not a preset parameter — different category entirely, must not be conflated with the others) | ENABLE_STATE (visual, correctly not OCR'd) captured for Legato; Mono needs the same modality; Poly needs CONTROL (text); voice-count needs a distinct "transient/live" category, not a ground-truth target | **PARTIAL** |

---

## Key findings

1. **All 5 assigned targets were correctly captured.** Gate A's 5/5 claim stands — it was never wrong about what it tested.
2. **All 5 crops/frames are `PARTIAL` at the observation-completeness level.** Every single crop bbox or its surrounding source frame contains additional visible state — text, checkbox, or shape — that the current 5-test benchmark never asked about or scored. This was true even inside test bboxes that were supposedly "tight" (test 5's Legato crop also contains Mono, Poly, and a voice meter).
3. **The most important gap: the Matrix row's Amount value has no text representation on screen at all.** Source/Destination being readable via OCR says nothing about whether the modulation depth (arguably the actual point of a mod-matrix row) is capturable — it isn't, by any modality tested so far. This needs pixel-position-to-value calibration, a fundamentally different technique than anything validated in Gate A.
4. **Graphical/shape state exists and was never scored:** OSC waveform shapes (a real, stable, likely-reproducible parameter tied to wavetable name + position), an EQ response curve, and the Lorenz attractor curve. These require a `GRAPH`/`CURVE`/shape-comparison approach, not OCR — Gate A only validated OCR-style text/enum/boolean extraction.
5. **One category confusion identified and flagged, not fixed:** the "0/8" voice-count readout next to Legato is *live runtime state* (depends on playhead position at capture time), not a *stored preset parameter* like Legato's ON/OFF. If a future pipeline treated all values inside a crop uniformly, it would wrongly try to treat a transient meter as reproducible ground truth.
6. **The Lorenz curve's status is explicitly left open**, not resolved: I don't have certainty about whether Serum's actual preset file stores anything beyond the enum name + Rate/Sync for a Chaos LFO, so I'm not asserting the curve shape is redundant — only that it was never captured or scored, and someone with the Serum preset schema in hand needs to close that question.

---

## What the existing JSON does NOT overclaim

`five_roi_test_results.json` already states its scope honestly: "5/5 on this controlled 5-case benchmark," explicitly not a general OCR-accuracy claim. This audit doesn't find the JSON *lying* about anything — it finds that the JSON's scope was narrower than the visual information actually present in the same images, which is a different and more useful finding for planning Gate C: the perception problem is bigger than 5 OCR-style targets, even within these same 5 screenshots.

---

## Consistency result

```
Per-target claim ("5/5 correctly extracted"):        TRUE, verified
Per-image completeness claim (implicit, if assumed):  FALSE — every image PARTIAL
Observation modalities validated so far:              TEXT/enum (OCR), ENABLE_STATE (checkbox)
Observation modalities identified but untested:       GRAPH/CURVE (shape), pixel-position calibration (slider amount)
Category error risk identified:                       runtime/transient meter vs. stored parameter
```

## Gate B acceptance criteria — status

| # | Criterion | Status |
|---|---|---|
| 1 | Every source image has verified SHA256 | ✅ |
| 2 | Every ROI has exact bbox + crop SHA256 | ✅ |
| 3 | Every target has canonical ID | ✅ |
| 4 | Every target has explicit observation kind | ✅ |
| 5 | Model + quantization + processor config pinned | ✅ |
| 6 | Prompt/version pinned | ✅ |
| 7 | Ground truth explicitly recorded | ✅ |
| 8 | Images independently inspected | ✅ |
| 9 | JSON compared against actual pixels, not just structurally validated | ✅ |
| 10 | Missing observable state explicitly reported | ✅ — see table above |
| 11 | Wavetable/waveform/graph/curve shapes audited separately from text | ✅ — flagged in tests 1, 3, 4 |
| 12 | Manifest immutable/versioned | ✅ — `gate_b_manifest.json`, `benchmark_version: roi-v1-gateB-audit` |
| 13 | No production pipeline code changed | ✅ — only new audit files added |
| 14 | Final report states captured/missing/required modality | ✅ — this document |

**Gate B: COMPLETE.** Stopping here per instructions — not proceeding to Gate C, not touching `roi_crop_extractor.py`.
