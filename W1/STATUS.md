# LOCAL W1 STATUS

**Bundle status: `W1_PARTIAL_NATIVE_EVIDENCE`** (not a Gate B certificate)

## Native env2.decay state proof
**SUCCESS**

- Loaded module SHA: `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3` (matches pinned Serum 2.0.23 epoch)
- Compiled preset SHA: `0998b65a229b275cc0c93dec290d96544e4297591bac2124d9bcb8bdf83567a0`
- Native UI value: ENV 2 `DEC = 5.00 s` (observed live via computer-use; not persisted as a standalone screenshot file, see `native_env2_decay/run_metadata.json`)
- Native re-save: `native_env2_decay/native_resave.SerumPreset`, SHA `c61700aa0a6af6778a97cf56967e483bebbe1d8c1e5fd2591a37a4d0c9b6a41b`
- readback_diff: target control `Env1.plainParams.kParamDecay` = 5.0 (compiled) vs 5.000000000000001 (native re-save) — **MATCH_WITHIN_FLOAT64_PRECISION**. 140 other diffs, all metadata/format artifacts, none touching the target path. Full detail: `native_env2_decay/readback_diff.json`
- Restoration (Gate B test track): deleted, verified 5→5 tracks

## Canonical Gate B
**BLOCKED**

Exact blocker:
```
ProducerBrain().execute(ProducerRequest(user_intent="shorten Env2.Decay to 5 s", ...))
execution_status: REFUSED_NO_EVIDENCE
refusal: REFUSED_NO_CAPABILITY — "No admission-ready evidence on either route
for 'Env2.Decay' (capability_key=envelope2_field_decay). REFUSE."
```
`finalize_serum_preset_execution()` was never reached. Root cause (two independent wiring gaps, full detail in `blocker/gate_b_admission_blocker.json`):
- **Gap A**: evidence-derived contracts register under atlas_id (`env2.decay`); the producer's capability resolution requires strict equality against the legacy capability_key (`envelope2_field_decay`) — by design, to prevent target cross-contamination. Needs an explicit, hand-reviewed crosswalk, not a fix in this local session.
- **Gap B**: `RouteSelector.__init__` hardcodes its own `ContractRegistry()` (epoch=None), disconnected from the epoch-aware registry `ProducerBrain` builds — so even a correctly-named contract wouldn't be seen by route selection.

No local code changes were made to `admit()`, `admit_rows()`, `RouteSelector`, `ContractRegistry`, `producer_brain.py`, or compiler authority logic, per the hard rule for this session.

## VLM ground-truth captures
**2 controls fully captured / 2 crops**, plus 1 documented failed capture (tooltip). See `vlm_ground_truth/labels.json` and the mirrored copy at `parameter_characterization/vlm_ground_truth/`.
- BULK_01_WAVETABLE_MAIN ENV1 (static): ATK 0.5ms, HOLD 0.0ms, DEC 1.00s, SUS -31.8dB, REL 15ms
- CAL_06_FILTER_CUTOFF ENV1 (static, GLOBAL tab): ATK 0.5ms, HOLD 0.0ms, DEC 1.00s, SUS 0.0dB, REL 15ms
- Filter 1 cutoff tooltip ("Filter 1 Freq: 172 Hz") observed live but NOT persisted to a hashable file — three attempts to reproduce the press-and-hold from a separate scripting process did not trigger the tooltip in that process's own screen capture. Recorded as a documented failure, not fabricated.
- Scope: representative sample, not exhaustive over all 330 controls or the full CAL_/BULK_ preset set.

## R1 stock-instrument render
**AUDIBLE** — peak 0.398, RMS 0.148, 100% non-zero samples (768000/768000)

## R1 Serum Arrangement render
**SILENT** — peak 0.0, RMS 0.0, 0% non-zero samples (0/768000), reproduced twice (before and after explicitly re-enabling the Serum 2 device, which is ruled out as the cause)

Full diagnosis, ruled-out and open hypotheses: `r1/diagnosis.json`

## Root-cause evidence
See `blocker/gate_b_admission_blocker.json` (Gate B admission wiring) and `r1/diagnosis.json` (Arrangement silence).

## Files produced
```
W1/
├── STATUS.md (this file)
├── native_env2_decay/
│   ├── compiled_preset.SerumPreset
│   ├── native_resave.SerumPreset
│   ├── readback_diff.json
│   ├── hashes.json
│   └── run_metadata.json
├── vlm_ground_truth/
│   ├── screenshots/ (3 files, incl. 1 documented-failed tooltip capture)
│   ├── crops/ (2 valid crops)
│   └── labels.json
├── r1/
│   ├── stock_instrument/r1_stock_operator_render.wav(+.mp3)
│   ├── serum_arrangement/r1_serum_bulk01_render.wav(+.mp3), r1_serum_bulk01_render_after_enable_device.wav(+.mp3)
│   └── diagnosis.json
└── blocker/
    └── gate_b_admission_blocker.json
```
(`parameter_characterization/vlm_ground_truth/` holds a mirrored copy of the VLM capture set, per the canonical location requirement.)

## NO CLAIMS MADE
- No `LIVE_UI_VERIFIED`
- No `reference_verified=True`
- No "Product Closed"
- No use of DawDreamer as native proof — all evidence above came from real Windows + Ableton Live + Serum 2.0.23 + AbletonMCP + native OS UI automation

## Next cloud handoff
Fix the env2.decay admission wiring (see `blocker/gate_b_admission_blocker.json` for the full proposed scope):
1. Explicit capability_key ↔ atlas_id crosswalk (hand-reviewed, no fuzzy matching)
2. Inject ProducerBrain's epoch-aware ContractRegistry into RouteSelector
3. Preserve strict target equality and the A2 gate exactly as-is
4. Add regression tests (env2.decay resolves; env1/env2 stay distinguishable; legacy no-epoch behavior unchanged)
5. Rerun the canonical ProducerBrain → admit_rows → compile → finalize path end to end
6. Only after that: LOCAL reruns Gate B and may claim LIVE_UI_VERIFIED if the full checklist passes
