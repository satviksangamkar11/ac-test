# Phase 2 Cloud Gate-A Closure Matrix

**Exact commands to verify this yourself (do not trust any count in this file):**
```
python3 -m pytest tests/test_gate_a_real_canonical_flows.py -q   # 69 passed
python3 -m pytest tests/test_gate_a_fixes.py -q                  # 20 passed
python3 -m pytest tests/ -q                                      # 451 passed, 4 skipped, 15 failed, 2 errors
```
The 15 failures + 2 errors in the full-suite run are **pre-existing and environment-caused** (missing
`cbor2` package in this container; confirmed identical via `git stash` against the commit before this
round of work — see the exact list below). None are regressions from this round's changes.

```
grep -n "MockResult" tests/test_gate_a_real_canonical_flows.py tests/test_gate_a_fixes.py       # 5 hits, all in docstrings documenting its ABSENCE, zero in executable code
grep -n "inspect.getsource" tests/test_gate_a_real_canonical_flows.py tests/test_gate_a_fixes.py # 1 hit, in the module docstring documenting the rule
grep -n "pytest.skip" tests/test_gate_a_real_canonical_flows.py tests/test_gate_a_fixes.py       # 0 hits
```

Pre-existing full-suite failures (all `ModuleNotFoundError: cbor2`, confirmed via `git stash`):
`test_state_ledger.py` (5), `test_reference_boundaries.py` (2), `test_reference_episode.py` (5),
`test_stage_a_completeness.py` (3), `test_compiler_serum_mcp_e2e.py` (2 errors).

## This round: independent cross-check found real vacuity, all fixed

An independent review of commit `69d33d1` found that "A2–A8 genuinely closed" was premature. Four
specific classes of remaining vacuity were identified and are now fixed, each with a **new real
production bug** uncovered along the way — this file only claims what the commands above can reproduce.

### 1. A4 still had an execution_spec-as-reachability shortcut, and a loose physical-coverage identity check

- `test_a4_every_user_facing_control_reachable` used `execution_spec(ctrl_id) is not None` as its
  PRIMARY reachability criterion — exactly the evidence/authority conflation this whole closure effort
  exists to eliminate. **Rewritten** as `test_a4_every_user_facing_control_exhaustively_partitioned`:
  every one of the 330 controls is classified via `find_contract()` alone (the function `admit_rows()`
  itself calls), into REACHABLE or an explicit, understood NOT_YET_CAPABILITY_BACKED reason
  (`NO_CAPABILITY` / `SCOPE_WOULD_EXPAND` / `INCOMPATIBLE_OPERATION` — never a crash, never
  `execution_spec`). **61 of 330 controls are honestly NOT capability-backed today** (macro names, several
  FX units, mixer bus-send levels, some warp/sample-loop fields) — this was always true; the old test's
  "0 unreachable" claim was an artifact of the shortcut, not a real invariant.
- The promoted-target test compared only physical coverage (root/index/kparam), not `contract_key`
  identity — a different contract covering the same physical parameter could pass even if it disagreed on
  **operand kind**. Investigating this surfaced a **real production bug**: `oscB.enabled` / `oscC.enabled`
  (real, valid, boolean-typed promoted contracts) were being shadowed by an older, differently-keyed
  contract (`oscillator_field_OSC2/3-ENABLE`) that happened to share the same structural path but was
  proven `mutate_numeric_value`, not boolean — `admit_rows()` returned `INCOMPATIBLE_OPERATION` for every
  real toggle observation, permanently. **Fixed**: `contract_scope._select_by_operand()` now prefers, among
  structurally-tied candidates, the one whose own operand kind agrees with the operation actually being
  attempted. 16 candidate collisions dropped to 14 confirmed-harmless duplicates (same physical parameter
  AND same operand kind, from two legitimate provenance sources — Pass-1 pickle store vs. promoted
  evidence) after the fix; those 14 are named exactly in `KNOWN_DUPLICATE_COVERAGE` and proven
  deterministic (5 repeated calls, identical result) and harmless (operand agreement) by
  `test_a4_duplicate_coverage_set_is_exhaustive_and_harmless`. The strong claim — `found.contract_key ==
  target` — now holds for every OTHER promoted target (207 of 221), with a hard failure if the exception
  set ever grows silently.

### 2. A7 accepted "a known pinned epoch" as equivalent to "the epoch this run executed on"

- `_binding_quality()` now takes `expected_epoch` and, when given, requires BOTH
  `loader_evidence["epoch"] == expected_epoch.serum_version` AND
  `loader_evidence["serum_module_sha256"] == expected_epoch.binary_sha256` — a real, known 2.0.21 readback
  can no longer satisfy a 2.0.23 run. `compare_ui()` and `gate_b_status()` both now pass their own run's
  epoch through.
- **Real bug fixed**: `gate_b_certificate()` read `ui_rb.get("screenshot_sha256")` — a top-level key that
  never existed in any real evidence shape. A7's actual schema puts it at
  `loader_evidence["screenshot_sha"]`. This field always read back `None` in every certificate ever
  produced. Fixed to read the real field.
- `crop_coords` now enforces non-negative, not just finite (`[-1, 0, 100, 100]` was previously accepted).

### 3. A8's `gate_b_status()` re-implemented a narrower, independently-maintained subset of A7's own binding check

- Previously: `gate_b_status()` checked module SHA directly and nothing else — a readback missing
  `run_id`/`track_nonce`/`screenshot_sha`/`crop_coords`/observed `values`, that A7's own
  `_binding_quality()` would refuse as `UNBOUND`, could still reach `CANONICAL_GATE_B_VERIFIED` as long as
  the module SHA happened to match. This is now closed: `gate_b_status()` requires `route == "DIRECT_UI"`
  AND `_binding_quality(ui_rb, expected_epoch=epoch) == "LOADER_BOUND"` — the exact same function and
  threshold A7 uses, not a re-implementation.
- `epoch=None` can now never reach `CANONICAL_GATE_B_VERIFIED` (previously it silently skipped the epoch
  check entirely, since the check was `if epoch is not None: ...`).
- `restoration_verified` is still required (fixed in the previous round; re-verified here alongside the
  rest of the chain).

### 4. The one-command pipeline was not proven to use exhaustive acquisition

`serum2/source/acquire_exhaustive.py` existed as Step 1 closure, but `reference_engine.py`'s
`run_stage1_acquire_and_prep()` — the actual production entry point — still imported and called the older
interval-sampling `acquire_visual_evidence()` (`sample_interval_sec=1.0`). Fixed:
- `run_stage1_acquire_and_prep()` now calls `acquire_exhaustive()` and fails closed
  (`RuntimeError`) on anything but `status == "SUCCESS"` — a partial/incomplete decode can never silently
  substitute for the real thing.
- **Real bug found while wiring this**: `acquire_exhaustive()`'s frame filenames end in a decoder **frame
  index** (`frame_<source_id>_<8-digit-index>.jpg`), but `stage_a_census_prep.build_frame_manifest()`'s
  existing regex for that naming shape (`frame_.+_(\d+)\.jpg$`, written for the OLD sampling path) divides
  that trailing number by 1000 and treats it as a **millisecond timestamp**. Wiring the exhaustive path in
  naively would have silently corrupted every frame's `timestamp_sec` in every Stage-A skeleton going
  forward. Fixed: `run_stage1_acquire_and_prep()` writes a sidecar (`exhaustive_timestamps.json`, frame_id →
  the real decoder `pts_time` from ffmpeg showinfo) next to the frames; `build_frame_manifest()` consults it
  when present and only falls back to the millisecond-division heuristic for genuinely old
  `acquire_visual_evidence`-sourced frames.
- Proven end-to-end (not just "the import line changed") by
  `TestExhaustiveAcquisitionWiring::test_run_stage1_calls_acquire_exhaustive_not_sampling_path` (asserts
  `acquire_exhaustive` is called exactly once, and that the skeleton's frame timestamps are the real
  decoder `pts_time` values, not `frame_index/1000`) and
  `test_run_stage1_fails_closed_on_incomplete_exhaustive_acquisition` (a `FAILED` exhaustive result stops
  the pipeline with `RuntimeError`, never falls back to a partial set).

## Gate-by-gate (updated)

| Gate | Status | This round's finding |
|------|--------|----------------------|
| A1–A3, A5, A6 | unchanged from prior round | — |
| A4 | strengthened | execution_spec shortcut removed; real oscB/C.enabled operand-mismatch bug fixed; duplicate-coverage set now named, exhaustive, and proven deterministic |
| A7 | strengthened | exact-runtime-epoch binding (not "any known epoch"); real screenshot_sha256 field-name bug fixed; crop_coords non-negativity enforced |
| A8 | strengthened | gate_b_status now consumes A7's own LOADER_BOUND check directly (no more independently-maintained weaker subset); epoch=None can never reach canonical |
| Acquisition wiring | closed | production runner proven (not just imported) to call acquire_exhaustive; real frame-index-as-milliseconds corruption bug fixed |

## Still true from the prior round (unchanged, not re-litigated here)

- `oscA/B/C.wavetable` remain the one documented, non-growing reachability exception
  (`KNOWN_UNREACHABLE_OPERAND_MISMATCH`): the promoted contract is proven for a structured operand no real
  `Row` can construct. See the previous round's notes for detail; nothing about this changed.
- A6's ExpectedInventory coverage check activates only when a skeleton declares `expected_controls` —
  backward compatible, not a narrowing of any existing skeleton's behavior.

## Before starting LOCAL / W1

Re-run the three commands at the top of this file yourself. Read the diffs for
`serum2/producer/contract_scope.py`, `serum2/execution/state_comparator.py`,
`serum2/producer/gate_b_certificate.py`, `serum2/producer/stage_a_census_prep.py`, and
`youtube_to_serum/reference_engine.py` directly — this document is a summary, not the source of truth.
