# Phase 2 Cloud Gate-A Closure Matrix

**Status: A1–A8 genuinely closed, cross-checked, with real production bugs found and fixed.**
**Test suite:** `tests/test_gate_a_real_canonical_flows.py` — 61 passing, 0 skipped, 0 vacuous.
**Verify yourself, don't trust this table:**
```
python3 -m pytest tests/test_gate_a_real_canonical_flows.py -v
```
Counts above are a snapshot at commit time; re-run the suite for the current number rather than trusting
this file, which is exactly the mistake the previous version of this document made.

## What "closed" means here

Every test in this file:
- calls the real production function (`derive()`, `admit_rows()`, `find_contract()`, `gate_b_certificate()`,
  `_binding_quality()`, `stage_a_is_filled()` — never a reimplementation of the logic under test),
- uses real evidence (real `ContractRegistry`, real `binding_table()`, real pydantic field metadata) wherever
  real evidence exists, and only injects controlled evidence (via `monkeypatch` or a constructed dict) at the
  exact point where the real evidence corpus doesn't naturally exercise a branch — and where it does, an
  exhaustive audit test proves that fact so the injection can never silently paper over a real gap, and
- has no `inspect.getsource`, no `MockResult`, no `pytest.skip`, no bare `pass`, no hardcoded pass-count
  threshold, and no `if x: assert ...` soft-conditional (every setup fact is a hard `assert`, so a broken
  fixture fails loudly instead of silently no-oping).

## Real defects found and fixed during this closure pass (not just test rewrites)

1. **`validate_final_execution_gate()` crashed on every real FX contract.** `expected_raw` path segments for
   FX targets contain a non-string slot index (e.g. `['FXRack0','FX',0,'FXDelay',...]`); `".".join(raw_path)`
   raised `TypeError` for every one of the 6 real FX contracts reachable at the time. Fixed in
   `serum2/producer/state_admission.py`; regression-proven end-to-end via `admit_rows()` in
   `test_a2_canonical_fx_admitted_no_crash_on_integer_path_segments`.
2. **A missing capability binding silently PASSED the body-path gate.** When `expected_raw` named a path but
   the contract's own `execution_binding` was `None`, the old code's `if expected_path and binding_path and
   ...` skipped the check entirely instead of refusing. Fixed to refuse (`REFUSED_BODY_PATH_MISMATCH`)
   whenever a declared path has no agreeing binding.
3. **`singleton_field` operations (arp/global singleton controls) were categorically unadmittable.**
   `contract_scope.find_contract()` had no branch for `kind == "singleton_field"` at all — it fell straight to
   `NO_CAPABILITY: unsupported operation kind`. This made ~200 of the 221 promoted `evidence_promotion`
   contracts (everything under `arp.*` and `global.*`) permanently unreachable in production despite being
   real, valid `CapabilityContract`s. Fixed by adding a real `singleton_field` lookup branch, a
   `_SINGLETON_ROOT` table (attr → Serum root class, evidence-grounded), and a small set of confirmed
   kParam-abbreviation aliases (`_SINGLETON_KPARAM_ALIASES`, `_FIELD_KPARAM_ALIASES`) plus two new path-grammar
   cases (`_NESTED_INST`, `_NESTED_STRUCT`) for wavetable/noise sub-oscillator paths. Went from 40 unreachable
   promoted targets down to 3 (see A4 below for the 3 that remain, and why).
4. **`gate_b_status()` granted `CANONICAL_GATE_B_VERIFIED` without ever checking `restoration_verified`**,
   despite the module's own docstring listing it as required. Fixed; proven by
   `test_a8_gate_b_status_requires_restoration_verified` (both the downgrade AND the genuine-positive case).
5. **`gate_b_certificate()` hardcoded `native_evidence_source = "Windows/Ableton/Serum 2.0.23"`
   unconditionally** — a certificate for a headless/DawDreamer-substituted run could still read as native
   proof. Fixed to derive the field from the same evidence that sets `dawdreamer_used`/
   `headless_substitution_used`, and to name the epoch actually passed in rather than a literal string.

## Gate-by-gate

| Gate | Status | What was actually broken before | Proof |
|------|--------|----------------------------------|-------|
| A1 | CLOSED | — (already genuine) | `TestA1RealCanonicalFlow` |
| A2 | CLOSED | FX crash bug (#1), silent-pass bug (#2) | `TestA2FinalExecutionGateHelper`, `TestA2RealAdmissionGates` |
| A3 | CLOSED | — (already genuine) | epoch-mismatch tests in `test_gate_a_fixes.py` |
| A4 | CLOSED | `execution_spec` existence treated as reachability proof; singleton_field unreachable (#3) | `TestA4AllContractsReachable` |
| A5 | CLOSED | representatives were hardcoded control_id strings | `TestA5CoerceAllModuleKinds` (binding_table-driven, parametrized) |
| A6 | CLOSED | no equivalence-cycle or duplicate-frame_id check; no ExpectedInventory coverage | `TestA6FrameTerminalStatus` |
| A7 | CLOSED | epoch field accepted any non-empty string; loader_evidence needed no actual observed values | `TestA7RealContentValidation` |
| A8 | CLOSED | `MockResult` classes; missing `restoration_verified` gate; hardcoded native claim | `TestA8HeadlessBlocksVerification` (zero mocks — every result comes from `ProducerBrain.finalize_serum_preset_execution()`) |

## A4's one documented, non-growing exception

`oscA.wavetable`, `oscB.wavetable`, `oscC.wavetable` are promoted, real `CapabilityContract`s, and the
canonical lookup DOES resolve them (proven) — but they are proven for a **structured** wavetable operand,
while `binding_table`'s `wavetable` field always derives a **named-selection** op. No real `Row` can construct
the structured operand the contract requires, so no row can ever reach admission for these three. This is
`contract_scope.find_contract`'s own pre-existing wavetable special-case (untouched by this pass), not a
lookup defect. It is named explicitly as `TestA4AllContractsReachable.KNOWN_UNREACHABLE_OPERAND_MISMATCH` and
the test fails loudly if that set ever changes in either direction — it can never silently grow.

## A6's declared-vs-inferred ExpectedInventory scope

`stage_a_is_filled()` now enforces ExpectedInventory coverage **when a skeleton declares one** (a top-level
`expected_controls` list). A skeleton that declares no such list is judged on frame terminality alone, exactly
as before — this is a backward-compatible extension, not a silent narrowing of what "filled" already meant for
every existing skeleton in the repo.

## Before starting LOCAL / W1

This file is a summary, not the source of truth. Before treating W1 as unblocked:
1. Run the suite yourself: `python3 -m pytest tests/test_gate_a_real_canonical_flows.py -v`.
2. Grep the suite for the forbidden constructs listed above; confirm zero hits outside of comments describing
   the rule itself.
3. Read the diff for `serum2/producer/state_admission.py`, `serum2/producer/contract_scope.py`,
   `serum2/execution/state_comparator.py`, `serum2/producer/gate_b_certificate.py`, and
   `youtube_to_serum/reference_engine.py` directly — do not rely on this document's paraphrase of them.
