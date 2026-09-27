# C3 Observation Policy — Validation Report

**Benchmark version:** c3-3.0.0  
**Remediation commit:** 9115382  
**Report date:** 2026-09-27  
**Platform:** Windows 11 / RTX 3050 6GB Laptop GPU  
**VLM:** Qwen/Qwen2.5-VL-3B-Instruct (local, 4-bit nf4)  
**OCR:** easyocr 1.7.2 (local, CUDA, en)

---

## Summary

This report documents the outcome of the C3 local VLM/OCR observation benchmark
run against the three remediated gaps (GAP A/B/C) in `observation_policy.py`
(commit 9115382).

**Disposition: `C3_REMEDIATION_STILL_INSUFFICIENT`**

The three architectural mechanisms are validated. The sample-size limitation
(n=5 real readable cases) prevents a statistical certification of the confident-wrong
rate. The remaining real-world validation will be completed naturally during W2.

---

## Real evidence

| # | Case ID | GT value | VLM | OCR | Outcome | Confident-wrong |
|---|---------|----------|-----|-----|---------|-----------------|
| 1 | real_bulk01_env1_decay | 1.0 s | 20.0 (wrong) | — (untrusted pos.) | AMBIGUOUS | No |
| 2 | real_cal06_env1_decay | 1.0 s | 1.0 ✓ | 1.0 ✓ | OBSERVED ✓ | No |
| 3 | real_c3_env1_diverse_decay | 3.5 s | 3.5 ✓ | 3.5 ✓ | OBSERVED ✓ | No |
| 4 | real_c3_env3_diverse_sustain | 61% | 61.0 ✓ | 6191.0 (wrong) | AMBIGUOUS | No |
| 5 | real_c3_global_tuning | 442.0 Hz | 442.0 ✓ | 4.0 (wrong) | AMBIGUOUS | No |
| 6 | real_missing_filter1_cutoff_tooltip | — | — | — | UNREADABLE | No |

**Real readable: 5**  
**OBSERVED (corroborated): 2** (cases 2 and 3 — VLM + OCR agreement)  
**AMBIGUOUS (abstained): 3** (correct policy behavior: VLM/OCR disagreed or OCR misread)  
**UNREADABLE: 1** (screenshot capture never persisted)  
**Confident-wrong: 0** (out of 5 readable real cases)

### Notes on AMBIGUOUS cases

- **real_bulk01_env1_decay**: VLM returned "20" (wrong); OCR could not locate the
  field positionally. Single-source, VLM confidence 0.303 — below threshold even before
  the single-source rule. Correct outcome: AMBIGUOUS.
- **real_c3_env3_diverse_sustain**: VLM correct (61%), OCR produced 6191.0 (wrong — a
  multi-digit hallucination). Values disagree → AMBIGUOUS. Correct outcome.
- **real_c3_global_tuning**: VLM correct (442 Hz), OCR produced 4.0 (positional fragment
  mismatch). Values disagree → AMBIGUOUS. Correct outcome.

All three AMBIGUOUS cases represent the safety mechanism working as intended: when
evidence is insufficient or conflicting, the policy abstains rather than admitting a
potentially wrong value.

---

## Synthetic adversarial cases

9 synthetic cases from c3-1.0.0 and 3 new GAP A cases (c3-3.0.0). All 12 are clearly
labelled `SYNTHETIC` and are not presented as real Serum ground truth.

**Confident-wrong in synthetic: 0** (in c3-3.0.0 with remediated policy)  
— All 3 former confident-wrong cases (single-source high-confidence wrong) now correctly
  resolve AMBIGUOUS under the GAP B corroboration requirement.

---

## GAP closure status

### GAP A — Identity binding ✓ CLOSED

**Mechanism:** `ObservationCandidate` now carries `control_id`. `adjudicate()` accepts
`requested_control_id`; candidates with a non-empty mismatching `control_id` are
excluded. If all candidates are filtered, `IDENTITY_UNRESOLVED` is returned.

**Validation:** Synthetic case `synthetic_gap_a2` (correct value, wrong identity) resolves
`IDENTITY_UNRESOLVED` — not OBSERVED, not AMBIGUOUS. Deterministic test `test_s8` confirms.

**Limitation:** The VLM model itself does not self-report which control it answered about.
Identity binding catches explicitly-tagged source mismatches. The broader "model answered
about the wrong panel" failure mode is mitigated by requiring corroboration (GAP B), not
resolved by identity tagging alone.

---

### GAP B — Single-source corroboration requirement ✓ CLOSED

**Mechanism:** A single source, regardless of its confidence, now returns `AMBIGUOUS`
with `single_source=True`. `OBSERVED` requires multi-source agreement.

**Validation:**
- 3 former confident-wrong synthetic cases now resolve AMBIGUOUS (not OBSERVED).
- Real cases 4 and 5 (VLM correct, OCR wrong) correctly stay AMBIGUOUS.
- Deterministic tests `test_s1`, `test_s2` confirm single-source → AMBIGUOUS at any threshold.

**Trade-off accepted:** The real case `real_cal06_env1_decay` (VLM correct, confidence 0.944)
previously resolved OBSERVED as a single source. Under the remediated policy it requires
OCR corroboration — easyocr 1.7.2 was available in c3-3.0.0 and DID corroborate (1.0 = 1.0),
so it still resolves OBSERVED. This is the correct outcome: the value is admitted because of
genuine independent corroboration, not despite the absence of it.

---

### GAP C — Evidence provenance ✓ CLOSED

**Mechanism:** `ObservationCandidate.evidence_hash` propagates through the policy layer.
`adjudicate()` propagates the `evidence_hash` of the highest-confidence agreeing candidate
to the OBSERVED result.

**Validation:** `gap_validation.GAP_C_tamper_test = True` — changing the image bytes
changes the SHA256, making tampered evidence detectable by hash comparison.
Deterministic test `test_s10` confirms hash propagation on OBSERVED.

---

## What C3 does NOT prove

- **Statistical certification**: n=5 real readable cases is insufficient to bound the true
  confident-wrong rate near zero with any standard statistical confidence interval.
- **Full coverage**: Only 5 real parameter controls have been observed. W2 will expand this.
- **VLM accuracy on all parameter types**: Only envelope/decay, sustain, and global tuning
  have been tested on real evidence.
- **OCR reliability**: easyocr shows positional fragmentation issues on multi-label crops
  (cases 4 and 5). This is expected; the policy correctly abstains rather than admitting
  misread values.

---

## Why C3 is ready for W2 natural expansion

The mechanisms are validated. The remaining question is statistical: how often does a
confident-wrong observation occur in real production use? The answer requires more real
samples, which W2 will provide naturally.

W2 must record, per parameter observed:
- `adjudicated_outcome` (OBSERVED/AMBIGUOUS/UNREADABLE/IDENTITY_UNRESOLVED)
- `confident_wrong` (True/False — can only be assessed against ground truth)
- `exact_match` (True/False — corroborated value matches native readback)
- `ocr_used_as_source` (True/False — whether OCR corroborated the VLM)
- `vlm_confidence`, `ocr_confidence`
- `evidence_hash`

Aggregating these across all W2 parameters expands the real C3 population naturally.

---

## Mutation boundary

The C3 observation policy is **not wired into any mutation-authorizing path**.

The mutation path remains:
```
ProducerBrain (advisory) → CapabilityContract → state_admission.admit_rows()
→ A2 final-contract gate → AuthorizedOperation → compiler → .SerumPreset
```

`observation_policy.adjudicate()` and `observation_engine.adjudicated_observe()` are
called only from the benchmark harness (`run_c3_benchmark.py`) and the diagnostic tests.
They are not imported by `state_admission`, `authorized_state_compiler`, or
`gate_b_certificate`. The mutation boundary test in `test_c3_remediation.py` asserts
this programmatically.

---

## Synthetic disclaimer

All synthetic cases (`provenance == "SYNTHETIC"`) are hand-authored `ObservationCandidate`
objects. They are explicitly labelled synthetic and represent policy edge cases that the
small real evidence set cannot exercise alone. No synthetic case is presented as real
Serum ground truth. No native Serum evidence was fabricated.
