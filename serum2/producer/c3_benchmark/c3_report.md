# C3: Local VLM/OCR Observation Benchmark — Report

## What was tested

Whether a local VLM (Qwen2.5-VL-3B-Instruct, 4-bit, running on this machine's RTX 3050 6GB)
can safely produce parameter observations that the existing `observation_policy` module
(`adjudicate()`, `CONFIDENT_THRESHOLD=0.9`) would admit as mutation-authorizing evidence,
without confident-but-wrong values slipping through.

This benchmark adds **no new adjudication logic**. It reuses `observation_engine.ObservationEngine`
and `observation_policy.adjudicate` exactly as the production path would call them, and only adds
a case set + scoring harness (`run_c3_benchmark.py`) and regression tests (`tests/test_c3_benchmark.py`).

## Evidence base

- **2 real, readable ground-truth cases** from the committed W1 evidence
  (`parameter_characterization/vlm_ground_truth/labels.json`), each with a real local
  Qwen2.5-VL-3B-Instruct inference run against the actual crop PNG, this session
  (`vlm_raw_outputs.json`), confidence = genuine mean per-generated-token probability
  (not a placeholder).
- **1 real "evidence missing" case**: the documented failed tooltip capture from W1 (Filter 1
  cutoff) — the crop itself was never persisted, so no VLM/OCR was run against it. This is kept
  separate from a genuine VLM/OCR failure.
- **9 synthetic adversarial cases**, hand-authored and clearly labelled `SYNTHETIC`, never
  presented as real Serum ground truth, exercising failure modes the 2 real crops cannot:
  ambiguous split sources, wrong-OCR-vs-correct-VLM, a single confidently-wrong source,
  correct-value-different-unit-formatting, boolean/state agreement, wrong enum/mode from a
  confident single source, a control-identity mismatch, all-sources-unreadable, and a
  low-confidence-but-numerically-correct single source.
- **OCR**: no local OCR engine is installed or cached in this environment (checked this
  session: no `pytesseract`, no `easyocr`, no system Tesseract binary at either standard
  Program Files path, no `tesseract` on PATH). Every real case's OCR column is recorded as
  `OCR_ENGINE_UNAVAILABLE` — not fabricated, not silently skipped.

## What was correct

- The one real case where Qwen was both **correct and confident** (CAL_06 ENV1 decay,
  "1.00 s", mean token probability 0.944) was correctly admitted as `OBSERVED` and matched
  ground truth exactly.
- All 9 synthetic "should agree/should abstain/should stay unreadable" cases behaved exactly
  as the existing policy is documented to behave — no drift in `observation_policy`'s own logic.

## What was wrong

- The other real case (BULK_01 ENV1 decay, ground truth 1.00 s) got a **wrong** VLM answer
  ("20", no unit, not close to 1.00). Its mean token probability was only 0.303 — well below
  `CONFIDENT_THRESHOLD` — so the existing policy correctly treated this as a single low-confidence
  source and returned `AMBIGUOUS`, not a false `OBSERVED`. This is the safety property working
  as intended on real data, but it is one (1) real sample; it does not by itself prove the
  property holds broadly.
- Three synthetic cases (`synthetic_wrong_vlm_high_confidence`,
  `synthetic_enum_mode_wrong_single_source_high_conf`,
  `synthetic_identity_mismatch_env1_vs_env2`) demonstrate a **real, unresolved architectural
  gap**: a *single* source above `CONFIDENT_THRESHOLD` is admitted as `OBSERVED` regardless of
  whether it is actually correct — the policy has no independent way to detect that a
  confident single source is wrong, by design (there is no ground truth available to it at
  adjudication time). All three were scored `confident_wrong=True`, exactly as the real
  production policy would score them. This is not a bug introduced by this benchmark; it is
  an existing, load-bearing limitation of single-source admission that this benchmark makes
  visible with concrete numbers instead of leaving it implicit.

## Where the model abstained

- Real: 2 of 3 real cases abstained (the low-confidence wrong VLM read, and the missing-evidence
  case). Both are the *correct* outcome for their evidence.
- Synthetic: 4 of 9 abstained (the split-source case, the disagreeing-sources case, the
  all-unreadable case, and the low-confidence-but-correct case) — all four are the policy's
  intended behavior, not a false negative.

## Whether confident hallucinations occurred

Yes, by construction in synthetic cases (3 of 9), and this is the entire point of including
them: they prove the *scenario* the real 2-sample set is too small to exercise on its own.
Zero confident-wrong occurred in the real cases (0/3 real, 0/2 real-readable) — but n=2 real
readable samples is nowhere near enough to bound a true confident-wrong rate near zero with
any statistical confidence.

## Aggregate metrics

See `c3_results.json.aggregate` for the exact machine-generated numbers. Summary:

| | numerator | denominator | rate |
|---|---|---|---|
| Exact-value accuracy (all 12 cases) | 3 | 12 | 25% |
| Exact-value accuracy (real, readable only) | 1 | 2 | 50% |
| Confident-wrong rate (all 12 cases) | 3 | 12 | 25% |
| Confident-wrong rate (real only) | 0 | 3 | 0% |
| Abstention rate (all 12 cases) | 6 | 12 | 50% |
| Abstention rate (real only) | 2 | 3 | 67% |

The all-cases numbers are dominated by the synthetic set, which was deliberately constructed
to include failure modes, not to represent a realistic prevalence — they should not be read
as "the pipeline is 25% accurate in production." The real-only numbers are the honest signal,
and the honest signal is: **the sample size (n=2 readable real cases) is far too small to
certify anything.**

## Is the observation policy safe to integrate?

**No — not yet, and not because of any single bad result.** The decision is driven by evidence
volume, not by any accuracy number crossing a threshold:

- 0 real confident-wrong results out of n=2 real readable samples is a *necessary* signal
  (it did not fail outright) but is nowhere near *sufficient* — a standard worst-case binomial
  bound means a true confident-wrong rate as high as roughly 78% would still be plausible at
  n=2 with zero observed failures. No accuracy number from a sample this small can license
  authorizing real Serum mutations.
- The 3 synthetic confident-wrong cases demonstrate the exact mechanism by which a real
  confident-wrong observation *would* occur if it did: a single source above threshold with
  no independent corroboration. This mechanism is real and currently unmitigated by anything
  beyond "require 2 agreeing sources OR one source above 0.9 confidence" — and OCR, one of the
  two intended independent sources, is not even available in this environment to provide that
  corroboration for VLM-only reads.
- No unit-normalization or control-identity-mismatch detection is exercised anywhere in
  `observation_engine`/`observation_policy` beyond the numeric-tolerance agreement check —
  the identity-mismatch synthetic case had to be modeled as "wrong value for the requested
  control," because the adjudicator has no cross-control identity check of its own to trigger
  more specifically. That is a real, separate gap, not something this benchmark works around.

## Integration decision

**NOT_INTEGRATED_INSUFFICIENT_REAL_EVIDENCE.** Production mutation authority — Gate A/B,
the A2 final-contract gate, `state_admission.admit_rows()`, 2.0.23 epoch enforcement, the
20 conformance exceptions — is left completely unchanged. No observation from this benchmark
is wired into any mutation-authorizing path. This is committed as a diagnostic result only.

## Exact blockers / next steps

1. **Sample size.** Only 2 real, readable W1 ground-truth crops exist. Expanding VLM ground
   truth capture (the `parameter_characterization/vlm_ground_truth/` set, already scoped as
   "representative sample, not exhaustive" in its own `labels.json`) to dozens of real controls
   is the direct prerequisite for any integration decision with statistical weight.
2. **No local OCR engine.** `pytesseract`/`easyocr`/system Tesseract are all absent from this
   machine. Without a second independent extraction modality, single-VLM-source admission
   (the exact mechanism behind the 3 synthetic confident-wrong cases) cannot be mitigated by
   requiring cross-modality agreement.
3. **No control-identity check in the adjudicator.** `observation_policy.adjudicate()` compares
   *values*, not the *identity* of the control a source claims to be answering about. A
   confidently-wrong-identity read (the model answers about the wrong panel/control but with
   a plausible-looking value for a *different* real control) is not distinguishable from a
   correct read at the adjudication layer today.
