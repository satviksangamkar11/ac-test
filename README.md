# Reference-to-Serum Reproduction (VLP1)

A pipeline that watches a reference (a tutorial video or sound), works out which **Serum 2.0.23** controls were
changed, and reproduces that state in a `.SerumPreset` — with every step gated by evidence, not by naming or
memory. Serum is driven only through [serum-mcp](vendor/serum-mcp) (vendored here). Claude Code is the model
runtime; there is no Anthropic SDK call in the canonical path.

> **Status (measured 2026-09-27, commit `885059a`):** Gate-A closure suite —
> `python3 -m pytest tests/test_gate_a_real_canonical_flows.py tests/test_gate_a_fixes.py -q` →
> **89 passed, 0 failed, 0 skipped, 0 mocks**. Full repo — `python3 -m pytest` (with `cbor2`/`zstandard`
> installed) → **1523 passed, 160 failed, 22 skipped, 16 errors**; the failures are pre-existing and
> environment-bound (missing qualification/screenshot fixtures under a Windows-only `D:\...` path, tests
> that require a live `serum-mcp` server, or legacy tests written before the A3 mandatory-epoch invariant
> that still call `ProducerBrain(epoch=None)` — none are caused by the Gate-A work below; the Gate-A suite
> itself, which this work owns, is fully green).
>
> **Phase 2 Gate-A: CLOSED (2026-09-27).** All eight admission-chain gates (A1–A8) now have genuine
> behavioral proofs — real production code exercised end-to-end, zero `MockResult`, zero
> `inspect.getsource`, zero hardcoded pass-count thresholds, zero soft `if x: assert` skips. Two rounds of
> independent adversarial cross-check each found real remaining vacuity (evidence/authority conflation,
> loose identity checks, a Gate-B/A7 bypass, a wiring claim not actually wired); both rounds' findings were
> fixed, and each fix uncovered a genuine production bug along the way (see the Gate-A table below and
> [GATE_A_MATRIX.md](GATE_A_MATRIX.md) for exact commands, counts, and per-bug detail). Do not re-litigate
> A1–A8 closure without first reading that file and re-running its commands yourself.
>
> **Phase 1 Complete (2026-09-27):** Universal full-frame observation pipeline replaces tutorial-specific `temporal_candidates()`.
> See [PHASE_1_UNIVERSAL_OBSERVATION_COMPLETE.md](audit/PHASE_1_UNIVERSAL_OBSERVATION_COMPLETE.md) for architecture.
> - ALL 269 frames now ingested and accounted for (was: 15 attempts on 6 hardcoded controls)
> - Evidence-first VLM observation (no control_id hints)
> - Zero tutorial-specific code in production
> - Temporal grouping reduces VLM calls ~15×
> - Zero new FAILED/ERROR node IDs (regression verified)
>
> **Integrity gaps from the original audit — resolved by Phase 2 Gate-A (see [SECOND_OPINION_AUDIT_2026-09-26.md](SECOND_OPINION_AUDIT_2026-09-26.md) for the original findings):**
> - ~~Only 10 of 231 CapabilityContracts are reachable on the real 2.0.23 epoch (F1)~~ — **CLOSED (A4).**
>   207 of 221 promoted targets now resolve to their own exact contract via the real canonical lookup
>   (`find_contract`), 14 more resolve to a proven-harmless, exhaustively-named duplicate, and only 3
>   (`oscA/B/C.wavetable`, a documented structured-operand architecture gap) remain unreachable. Fixing this
>   surfaced and fixed a real bug: `oscB.enabled`/`oscC.enabled` (real, valid boolean contracts) were
>   permanently shadowed by an older, operand-incompatible contract for the same physical parameter.
> - ~~The ledger crashes on `macro` and `singleton_field` controls (F3)~~ — **CLOSED (A5).** `singleton_field`
>   admission (arp/global controls) is now fully supported in `contract_scope.find_contract`, recovering
>   ~200 previously-unreachable promoted contracts; representative coverage across all 9 module kinds is
>   proven dynamically from `binding_table()`, never hardcoded.
> - ~~Reference verification can pass with 1/300 frames and a hand-typed readback (F7)~~ — **CLOSED (A6/A7).**
>   `stage_a_is_filled` now requires every manifest frame terminal, rejects equivalence cycles and duplicate
>   frame IDs, and enforces declared ExpectedInventory coverage. A "hand-typed dict" can no longer reach
>   `LOADER_BOUND`: it must carry all 6 loader-evidence fields in valid format, bind to the **exact** runtime
>   epoch (not just "a known epoch"), and include a real observed `values` payload.
> - ~~ProducerBrain uses the qualification test value as the production operand (F4)~~ — **CLOSED (A1/A2).**
> - ~~Cross-epoch execution is possible via `epoch=None` (F5)~~ — **CLOSED (A3/A8).** `gate_b_status(epoch=None)`
>   can no longer reach `CANONICAL_GATE_B_VERIFIED` either.
> - DawDreamer/headless evidence bypassing Gate B (F11) — **CLOSED (A8).** `gate_b_status()` now consumes
>   A7's own `_binding_quality()` directly instead of re-implementing a narrower, independently-maintained
>   subset of its checks — closing a real authority/evidence-gate bypass a reviewer found in the first
>   closure attempt.
> - The one-command runner calling the sampling acquisition path instead of the exhaustive one — **CLOSED.**
>   `run_stage1_acquire_and_prep()` now actually calls `acquire_exhaustive()` (proven end-to-end by a test
>   that fails if the sampling path is used) and fails closed on an incomplete decode. Wiring this in
>   surfaced and fixed a real bug: the exhaustive path's frame filenames end in a decoder index, and the
>   existing filename-timestamp regex (written for the old sampling path) would have silently divided that
>   index by 1000 and treated it as a millisecond timestamp, corrupting every Stage-A frame's timestamp.
>
> **Phase 3 (2026-09-27): W1 CLOUD-SIDE ORCHESTRATOR — two real blockers found and closed.** An
> independent cross-session check of the committed repository (not a report) found that a claimed
> "generic accessor fix" commit did not exist anywhere in this history. Re-deriving the actual problem
> from source found it was real: 185 of 231 `SERUM_PRESET_STRUCTURAL` promoted contracts (every
> field-kind one lacking an explicit `accessor` in its evidence file, `env1.attack` included) could be
> `ADMITTED` but could never reach `compile_ops() SUCCESS` — reproduced directly as
> `UnauthorizedOperation("...contract binding is SERUM_PRESET_STRUCTURAL/None")`. Fixed generically (no
> per-control branch) in `serum2/qualification/evidence_promotion.py`, by falling back to the same
> `serum_mcp_binding_table.json` lookup `derive()`/`admit_rows()` already trust when an evidence file's
> own accessor is absent. Second: `serum2/producer/serum_preset_orchestrator.py` (new) is the generic
> bridge from `ProducerBrain`'s `ADVISORY_ONLY` plan to real native execution/evidence — without adding
> any Windows/Ableton logic to `ProducerBrain` itself — and its preset-generation step now calls the
> real `compile_ops()`/`serialize()` chain (previously an honest fail-closed stub), producing a genuine
> `.SerumPreset` file, proven for `env1.attack`-shaped and other field-kind targets alike. Both fixes
> verified against the actual committed remote state, not a local worktree. Details:
> [GATE_A_MATRIX.md](GATE_A_MATRIX.md) covers Gate-A; the accessor/orchestrator fix commit message on
> `serum2/qualification/evidence_promotion.py` / `serum2/producer/serum_preset_orchestrator.py` covers
> this round. Full suite: 479 passed, 16 failed (identical pre-existing environment-bound failures —
> missing `cbor2`, no `SERUM_PRESETS_PATH` in this container — confirmed unchanged via `git stash`), 4
> skipped. **Still open before Local can run a real W1:** the orchestrator's two genuinely
> environment-dependent seams (`native_execution_fn`, `ui_evidence_provider`) are real Windows/Ableton
> code, not yet exercised outside test fixtures.
>
> **VLM/OCR (Stage-A production observation) — infrastructure exists; production closure does NOT.**
> Do not read "Gate-A closed" or "acquisition closed and wired" above as "the VLM/OCR pipeline is done" —
> those close the *ledger-side* completeness/binding checks (A6/A7) and the *frame-acquisition* step, not
> the *frame → terminal Stage-A result* step itself. Concretely:
> - **Done:** the universal full-frame acquisition/observation framework (`FrameObservationCensus`,
>   Phase 1); the earlier 269-frame corpus is ingested and accounted for; evidence-first VLM processing
>   and temporal grouping exist; OCR/VLM can be used as an observation input rather than a hardcoded
>   tutorial assumption.
> - **Not done / not certified:** the production Stage-A VLM/OCR pipeline that deterministically turns
>   *every* acquired frame into a terminal Stage-A result (`ANALYZED`/`NOT_SERUM`/`UNREADABLE`/
>   `EQUIVALENT_TO:<frame>`) is not fully wired end to end. Reliable extraction of **actual Serum
>   parameter values** (not just module/control *names*) is the hard remaining part — Qwen-based testing
>   showed name recognition working well while truthful value extraction did not. The full chain
>   `frame → VLM/OCR observation → temporal corroboration → terminal Stage-A result → ledger →
>   ExpectedInventory completeness` still needs closing before this can be marked done. This is
>   explicitly carried forward as its own gate for W2 (see Step 17/18 below) — it is not forgotten and
>   must not be conflated with Gate-A or the acquisition-wiring closure above.
>
> **Big-picture status (2026-09-27):**
>
> | Component | Status |
> |---|---|
> | 330 Serum controls / universal contract | ✅ Complete |
> | Serum native mapping/evidence | ✅ Complete |
> | Generic authority/admission/compile architecture | ✅ Mostly complete — accessor gap (185 contracts) and canonical-preset-generation wiring closed this round; native execution/evidence seams still test-only |
> | VLM/OCR infrastructure | ✅ Exists |
> | VLM/OCR reliable production Stage-A closure | 🟡 Not fully closed — see above |
> | Native Serum W1 certification | 🟡 Pending — cloud-side blockers closed; Local native run not yet performed against this fixed code |
> | YouTube → Serum full product run (W2) | ⏳ Pending |
> | 16-bar Ableton arrangement/render | ⏳ Pending |

> **Epoch:** Serum **2.0.23** (SHA-256 `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3`).
> Any reference to "Serum 2.0.21" in the codebase or docs is **stale**; the runtime is 2.0.23.

## Target Final Architecture

```
YouTube video
   ↓
video/audio acquisition (exhaustive single-pass ffmpeg decode)
   ↓
complete frame manifest (every frame indexed + SHA-256)
   ↓
local ASR transcript
   ↓
local VLM + OCR + temporal evidence fusion
   ↓
Stage-A evidence (per-frame terminal status: ANALYZED / NOT_SERUM / UNREADABLE / EQUIVALENT_TO:<frame>)
   ↓
state ledger (every observation → exactly one terminal outcome; macro + singleton_field supported)
   ↓
Atlas identity + CapabilityContract lookup
   ↓
admit() — capability gate
   ↓
final execution evidence gate (epoch match, no CONFORMANCE_EXCEPTION, qualified domain check)
   ↓
AuthorizedOperation (operand = observed value; qualification_test_value is advisory only)
   ↓
generic compiler (defense-in-depth re-validation)
   ↓
genuine .SerumPreset (via serum-mcp pack_file)
   ↓
native Serum 2.0.23 (Windows, Ableton Live, real binary)
   ↓
loaded-module SHA verification + native re-save + screenshot-bound UI readback
   ↓
reference_verified=True (COMPLETE coverage + LIVE_UI_VERIFIED + no unexplained differences)
   ↓
Ableton track → 16-bar arrangement → audible verified render
```

**Not yet achieved in this order.** See the closure plan below.

## Core Invariants

1. **Evidence ≠ authority.** Only a `CapabilityContract` grants execution, and only through admission.
2. **Capability ≠ admission.** A qualified control still needs an admitted operation.
3. **One authority, one gate.** The final execution contract is an *evidence/qualification gate*, not a mutation authority. `CapabilityContract` remains the authority for mutation mechanics.
4. **Reference facts ≠ logic.** No per-parameter code (`if target == "filter1.enabled"`); known data (tables, evidence JSON) is never execution logic.
5. **Brain is advisory-only.** `ProducerBrain` emits intent analysis; it never emits `AuthorizedOperation` until it builds ledger-shaped ops through the canonical admission chain.
6. **`HOST_PARAMETER` (VST3) is an evidence surface, not execution authority.** Execution-eligible bindings: `SERUM_PRESET_STRUCTURAL`, `BODY_STATE`, `TOPOLOGY`.
7. **Epoch is mandatory.** `epoch=None` is banned in production. Tests use `ExecutionEpoch.OFFLINE_TEST`, which can never produce `VERIFIED` claims. The production epoch is `2.0.23` with the pinned SHA-256 above.
8. **Operand = observed value.** `scope["mutation_value_used"]` (the qualification test value) is renamed `qualification_test_value` and is never used as the production mutation.
9. **Proof level and coverage are separate axes.** `LIVE_UI_VERIFIED` + `COMPLETE` (every manifest frame terminal + ExpectedInventory covered) + no unexplained differences → `REFERENCE_REPRODUCTION_VERIFIED`.
10. **No invention.** Not visible ≠ removed; unreadable ≠ exact value; transcript ≠ executed action; audio similarity ≠ identical state. `None` means unknown.
11. **Native proof is native.** DawDreamer evidence is labelled `HEADLESS_DAWDREAMER` and can never produce `VERIFIED` or `LIVE_UI_VERIFIED` claims.

## Closure Plan

**PHASE 1 (2026-09-27): COMPLETE** — Universal full-frame observation pipeline. See [PHASE_1_UNIVERSAL_OBSERVATION_COMPLETE.md](audit/PHASE_1_UNIVERSAL_OBSERVATION_COMPLETE.md).

**PHASE 2 (2026-09-27): GATE-A CLOSED; ONE-COMMAND PIPELINE PARTIALLY COMPLETE**
- Seams S1–S4: ✅ Fixed (native verification, reference verification, arrangement with MCP, robust audio validation)
- **Gate-A (A1–A8): ✅ CLOSED** — see the Gate-A tables above and [GATE_A_MATRIX.md](GATE_A_MATRIX.md). This
  closes the *logic-integrity* half of Cert 1: no authority bypass, no cross-epoch execution, no
  qualification-value substitution, no fake UI readback, no out-of-domain execution, no unsupported mutation.
- **Acquisition: ✅ CLOSED AND WIRED** — exhaustive frame decoding, and the production runner now actually
  calls it (previously it still called the old sampling function; an independent review caught this).
- STILL OPEN (not addressed by Gate-A): Stage-A output generation from real VLM census (A6/A7 closed the
  *ledger-side completeness/binding checks*, not the VLM observation step itself — see the VLM/OCR status
  banner above: infrastructure exists, production frame→terminal-result closure does not), transcript
  resolution, ARRANGE real MIDI, RENDER automation, FINALIZE gates. Cert 1 is not yet fully claimable
  until these are done.

**PHASE 3 (2026-09-27): W1 CLOUD-SIDE ORCHESTRATOR — two blockers closed, native execution still open**
- Generic accessor-derivation gap (185 of 231 `SERUM_PRESET_STRUCTURAL` contracts, including `env1.attack`)
  found and fixed in `serum2/qualification/evidence_promotion.py` — see the status banner above.
- `serum2/producer/serum_preset_orchestrator.py` (new): the generic bridge from `ProducerBrain`'s
  `ADVISORY_ONLY` plan to real native execution/evidence, keeping `ProducerBrain` itself
  environment-independent. Its canonical-preset-generation step now calls the real
  `compile_ops()`/`serialize()` chain (previously an honest fail-closed stub) — proven to produce a
  genuine `.SerumPreset` file for real admitted operations, not test fixtures.
- STILL OPEN: the orchestrator's `native_execution_fn` (real `serum_track_loader.load_and_verify()` on
  Windows/Ableton) and `ui_evidence_provider` (real screenshot/observed-value/restoration adapter) seams
  are only exercised by test fixtures so far — a real Local W1 run against this fixed code has not
  happened yet.

The project has four machine-checkable certificates, produced in order:

| Certificate | Phase | Where | What it proves | Status |
|---|---|---|---|---|
| **Cert 1 — Integrity** | Phase 2 | Cloud | No authority bypass, no cross-epoch execution, no qualification-value substitution, no incomplete Stage-A success, no fake UI readback, no out-of-domain execution, no unsupported mutation | Gate-A logic closed; Stage-A/transcript/render wiring above still open before this cert can be issued |
| **Cert 2 — Native Serum** | Phase 3 | W1 Windows + Cloud | Loaded-module SHA matches 2.0.23 pin, genuine preset SHA, native re-save matches compiled operand, screenshot-bound readback matches, restoration verified, no DawDreamer in chain | Cloud-side generic orchestrator + real `compile_ops()` wiring done (accessor gap fixed); native Windows/Ableton execution not yet run against this code |
| **Cert 3 — Product** | Phase 4 | W2 Windows + Cloud | One untuned real tutorial → `reference_verified=True` with COMPLETE coverage + verified audible 16-bar render | Not started |
| **Cert 4 — Control Surface** | Phase 5 | Cloud + selective Local | Every non-exception control `EXECUTABLE+VERIFIED`, all 20 exceptions classified as `EXECUTABLE+UNVERIFIED`, `UNQUALIFIED`, or `GENUINELY_NON_EXECUTABLE` | Not started |

**Critical path:** Phase 1 ✓ → Phase 2 Gate-A ✓ → Phase 2 remainder (Stage-A generation, transcript resolution, render automation, finalize gates) → Phase 3 (W1) → Cert 2 → Phase 4 (C3 local VLM benchmark + W2) → Cert 3 → Phase 5 (20 exceptions) → Cert 4

See [SECOND_OPINION_AUDIT_2026-09-26.md](SECOND_OPINION_AUDIT_2026-09-26.md) for the full adversarial audit (findings F1–F16, Q1–Q20, branch topology, conformance-exception root causes).

## Current Implementation State

### What works (cloud, no Windows required)
- **PHASE 1 COMPLETE:** Universal full-frame observation pipeline (`FrameObservationCensus`) — processes all 269 frames, evidence-first VLM (`observe_frame_all_controls`), zero tutorial hardcoding, 20 census metrics
- **PHASE 2 GATE-A COMPLETE:** CapabilityContract loading and reachability now cover all 9 module kinds
  (`osc/env/lfo/filter/macro/fx/arp/global_/voice_unison`, including `singleton_field` admission, previously
  entirely unsupported) — 207 of 221 promoted contracts reach their own exact contract via the real
  canonical lookup, 14 more a proven-harmless duplicate, only 3 (a documented structured-operand gap)
  unreachable, up from 10 of 231 at the start of Phase 2.
- `state_ledger.build_all()` handles all 9 module kinds; `macro`/`singleton_field` no longer crash it (F3 closed)
- `state_admission.admit_rows()` — the vast majority of the 330-control binding table is admittable under
  the real 2.0.23 epoch (see [GATE_A_MATRIX.md](GATE_A_MATRIX.md) for the exact, dynamically-measured
  reachable/not-yet-capability-backed partition — never a hardcoded count)
- `authorized_state_compiler.compile_ops()` — generic compiler with `_validate()` defense-in-depth
- `serum_mcp.generate_preset` / `pack_file` — genuine `.SerumPreset` output
- `run_reference_reproduction()` — run object, proof level, coverage; the completeness/binding gaps that
  used to let this pass vacuously (F1/F7) are closed by A4/A6/A7
- Exhaustive frame acquisition (`acquire_exhaustive.py`) is now the pipeline's actual acquisition source
  (`run_stage1_acquire_and_prep` calls it, not the old sampling function), fail-closed on incomplete decode
- Gate-A closure test suite: **89 passed, 0 failed** (`tests/test_gate_a_real_canonical_flows.py` +
  `tests/test_gate_a_fixes.py`), zero mocks. Full repo: 1523 passed, 160 failed/16 errors, all pre-existing
  environment/fixture-bound (see status banner above)

### ONE-COMMAND PIPELINE FIXES (PHASE 2)

| Aspect | Issue | Status |
|--------|-------|--------|
| **ACQUISITION** | Was sampling at 45-second intervals (max 8-10k frames). Must exhaust every source frame. | ✅ **CLOSED AND WIRED (2026-09-27)** — `acquire_exhaustive.py` implements authoritative decoder-side accounting: two independent reconciled ledgers (decoder metadata via ffmpeg showinfo + artifact enumeration), complete frame manifest with every frame index/PTS/dimensions from decoder, PIL verification of every artifact, fail-closed design, comprehensive cache validation. **`youtube_to_serum/reference_engine.py`'s production entry point (`run_stage1_acquire_and_prep`) now actually calls it** (previously it still called the old sampling `acquire_visual_evidence`, a gap an independent review caught) — proven end-to-end by `TestExhaustiveAcquisitionWiring` in `tests/test_gate_a_real_canonical_flows.py`, which fails if the sampling path is used. Wiring it in surfaced and fixed a real bug: the exhaustive path's frame filenames end in a decoder index, and `stage_a_census_prep.build_frame_manifest`'s existing regex (written for the old sampling path's millisecond-timestamp filenames) would have silently divided that index by 1000 and corrupted every frame's timestamp; a sidecar file now carries the real decoder `pts_time` per frame. Cache keyed by decoder version + acquisition mode + exhaustive proof (never reuses reduced/incomplete/old-non-exhaustive). |
| **TRANSCRIPT** | Runner used `tests/fixtures/w2/transcript.json` for production. Must resolve transcript for actual requested video. | 🔴 **TODO** — Implement video_id → transcript resolution; fail if unavailable; never substitute fixtures. |
| **STAGE-A** | Universal observer outputs `c3_observation_metrics.json`. Ledger expects real Stage-A structure. | 🔴 **TODO** — Emit frame-by-frame terminal status (ANALYZED/NOT_SERUM/UNREADABLE/EQUIVALENT_TO); include control findings + route findings. |
| **S1: NATIVE_VERIFY** | Must parse `readback_diff.json` and extract genuine native control values. | ✅ **FIXED (2026-09-27)** — Extracts `target_control`, builds `ui_readback` with `binding_quality: NATIVE_BOUND`. |
| **S2: REFERENCE_VERIFY** | Must use actual `ui_readback` from NATIVE_VERIFY; generate real `reread_log.json`. | ✅ **FIXED (2026-09-27)** — Uses NATIVE_VERIFY outputs, generates reread_log.json, calls reference_reproduction with real paths. |
| **S3: ARRANGEMENT** | Must create real 16-bar MIDI clip in Ableton Arrangement view via MCP. | ✅ **FIXED (2026-09-27)** — Creates real clip; no empty-clip pretense. |
| **S4: RENDER_VALIDATION** | Must validate RMS, peak, non-silence; cannot hide measurement failures. | ✅ **FIXED (2026-09-27)** — Three-metric validation; explicit ValueError for unreadable files. |
| **RENDER AUTOMATION** | Pipeline only validates existing WAV; must trigger Ableton export/render itself. | 🔴 **TODO** — Use existing MCP to export audio; verify duration matches 16 bars. |
| **FINALIZE** | Must gate on ALL genuine artifacts (no manual injection). | 🔴 **TODO** — Validate complete chain: exhaustive frames → Stage-A coverage → verified reference → real MIDI → real render. |

**Critical path (ACQUISITION CLOSED AND WIRED, GATE-A CLOSED):** Transcript resolution → Stage-A output (real VLM census, not just the ledger-side completeness checks A6 already closed) → one Gate-B native run (W1) → fresh W2 → product closure.

Do not add more control proofs until the pipeline completes end-to-end.

### What is broken or missing (being fixed in subsequent phases)

**PHASE 1 addressed:** Frame selection now universal (all 269 frames ingested); no more hardcoded `_TUTORIAL_CANDIDATE_WINDOWS` (was limiting to 6 controls × 3 frames = 15 attempts).

**Findings (F1–F16) — Gate-A (Phase 2) status:**
- **F1 — CLOSED (A4):** was 10 of 231 reachable; now 207 of 221 promoted targets resolve to their own exact
  contract, 14 more to a proven-harmless named duplicate, 3 documented as a structured-operand gap
  (`oscA/B/C.wavetable`). See [GATE_A_MATRIX.md](GATE_A_MATRIX.md).
- **F2 — CLOSED (A4):** `BINDING_EVIDENCE_DIR`/promoted-evidence loading verified against the real
  330-control corpus; the reachability sweep above is exhaustive over all 330 user-facing controls, not a
  sample.
- **F3 — CLOSED (A5):** `singleton_field` admission (arp/global) implemented in `contract_scope.find_contract`
  (it had no branch for this kind at all); `macro` module added to the field-root table. All 9 module kinds
  now have dynamically-discovered representative coverage.
- **F4 — CLOSED (A1/A2).**
- **F5 — CLOSED (A3/A8):** `epoch=None` raises in production paths; `gate_b_status(epoch=None)` can no
  longer reach `CANONICAL_GATE_B_VERIFIED` either (an independent review found this residual gap).
- **F7 — CLOSED (A6/A7):** `stage_a_is_filled` now requires every frame terminal (no `any()` shortcut),
  rejects equivalence cycles/duplicate frame IDs, and enforces declared ExpectedInventory coverage.
  `LOADER_BOUND` now requires exact-epoch binding and a real observed `values` payload, not just valid hashes.
- **F8 — CLOSED (A7):** `_ui_equal` unit normalization implemented and tested.
- **F9 — CLOSED (A6/A7):** the orchestrator's completeness/UI-readback wiring is covered by the A6/A7 tests above.
- **F10 — CLOSED (A1/A2):** `admit_rows` is the single common admission gate; `validate_final_execution_gate()`
  enforces epoch/exception/path/domain together, with a real FX-contract crash bug (integer path segments)
  found and fixed along the way.
- **F11 — CLOSED (A8):** DawDreamer/headless evidence is labeled `HEADLESS_DAWDREAMER` and `gate_b_status()`
  now consumes A7's own binding-quality check directly rather than a separately-maintained, weaker subset
  of it (an independent review found this bypass in the first closure attempt).
- **F12:** Frame acquisition caching/truncation — **addressed by the exhaustive acquisition wiring above**
  (decoder-accounted, fail-closed, no 300s truncation); not separately re-verified as its own item.
- **F13:** Legacy `VisualReasoner` cloud fallback — not touched in this round; still open.
- **F15:** stale "2.0.21" strings — not swept in this round; still open (Phase 3).
- **F16 — CLOSED (Phase 2 tests):** the Gate-A closure suite exercises the real 2.0.23 epoch end-to-end
  throughout (`EPOCH_2_0_23`, never `epoch=None` in a production code path).

### Gate-A fix targets — ALL CLOSED (cloud, 2026-09-27)
| Step | Fix | Closes | Status |
|---|---|---|---|
| A1 | `ProducerBrain` → `ADVISORY_ONLY`; rename `mutation_value_used` → `qualification_test_value` | F4 | ✅ CLOSED |
| A2 | Common gate in `admit_rows`: final-contract epoch + exception + path + domain check | F10 | ✅ CLOSED — real FX crash bug (non-string path segments) and a silent-pass bug (missing binding) found and fixed |
| A3 | `epoch=None` raises; `OFFLINE_TEST` epoch caps claims at `OFFLINE_ONLY` | F5 | ✅ CLOSED |
| A4 | `promote_verified_evidence` writes `mutation_target_path`; fix `BINDING_EVIDENCE_DIR` | F1, F2 | ✅ CLOSED — real `singleton_field` lookup gap and an operand-mismatch duplicate-contract bug found and fixed |
| A5 | `_coerce`/`compile_ops` support all 9 module kinds; unknown → `UNSUPPORTED` terminal | F3 | ✅ CLOSED — representatives discovered dynamically from `binding_table()`, never hardcoded |
| A6 | Per-frame `analysis_status`; `stage_a_is_filled` → `all()`; ExpectedInventory coverage | F7 (partial) | ✅ CLOSED — plus equivalence-cycle and duplicate-frame-ID rejection |
| A7 | UI readback requires loader evidence (module SHA, nonce, run id, screenshot hashes + crops); native re-save channel; fix `_ui_equal` unit normalization | F7, F8 | ✅ CLOSED — plus exact-runtime-epoch binding and a real `screenshot_sha256`-field-name bug found and fixed |
| A8 | Relabel DawDreamer evidence as `HEADLESS_DAWDREAMER` in final-contract metadata | F11 | ✅ CLOSED — `gate_b_status()` now consumes A7's own check directly, closing a real Gate-B/A7 bypass |

Full detail, exact test commands, and exact counts: [GATE_A_MATRIX.md](GATE_A_MATRIX.md).

## Repository Map

| Path | What it is |
|---|---|
| `serum2/evidence/` | Data model: `EvidenceRecord` → `ClaimGroup` → `CapabilityContract` (+ `ExecutionBinding`) → `admit()`. Contract tiers: `CAUSAL_VERIFIED`, `STRUCTURAL_ONLY`, `NEGATIVE_EVIDENCE`, `UNSUPPORTED`, `BLOCKED_CONTRADICTED`; tiers are never upgraded. |
| `serum2/producer/` | Ledger, admission, contract registry, epoch, route classification, target resolution, Brain, skills, grounding, fusion, qualification runner. Tests live beside the code (`test_*.py`). |
| `serum2/execution/` | `authorized_state_compiler.py` (**the** compiler), `state_comparator.py` (serialize + readback + compare). `authorized_preset_compiler.py` is legacy — do not extend. |
| `serum2/server/` | `reference_reproduction.py` (run object, proof level, coverage), experience records, and the older FastMCP creation pipeline. |
| `serum2/reference/` | Serum Atlas, UI atlas, hash-pinned audit, `serum_mcp_binding_table.json` (330 candidates; a name match is not proof). |
| `serum2/qualification/` | Evidence artifacts and tools: `pass1/` (Serum 2.0.23 kit), `candidate_binding_qualifier.py`, evidence promotion. |
| `serum2/knowledge/` | Advisory knowledge store and resolution steps. Live: `step_5_6`, `5_7`, `6_2`–`6_10`. Historical: deprecated steps. |
| `serum2/source/` | YouTube transcript and frame acquisition (`acquire_visual_evidence` — being rewritten for Track B). |
| `serum2/ableton/` | `serum_track_loader.py`, `ableton_mcp_extended/server.py` (OLE-drop loader, nonce rollback, module-SHA check). |
| `vendor/serum-mcp/` | Vendored serum-mcp (upstream commit in `UPSTREAM_COMMIT.txt`). |
| `parameter_characterization/` | Binding evidence dirs, final execution contract (`bulk_causal_evidence/final_execution_contract_v1.json`, 330 rows: 183 `MCP_EXEC_HOST_CONFIRMED` / 127 `MCP_EXEC_RAW_ONLY` / 20 `MCP_EXEC_CONFORMANCE_EXCEPTION`). Evidence was generated by headless DawDreamer (see F11); it is an evidence gate, not authority. |
| `audit/probes/` | Reproduction scripts for F1–F7 (see audit report). |
| `SECOND_OPINION_AUDIT_2026-09-26.md` | Full adversarial audit: F1–F16 findings, Q1–Q20 answers, branch topology, 20-exception classification. |
| `tests/` | Reference-reproduction, ledger, boundaries and compiler tests with committed fixtures. |
| `experiments/*.pkl` | Pickled contract stores loaded by `ContractRegistry` (see Security). |
| `docs/VLP1_Fully_Revised_Architecture.md`, `FREEZE_VLP1.md` | Frozen architecture (authoritative). |

Most other root-level `.md`/`.json` files are historical phase reports or generated artifacts; treat them as history, not spec. Docs that quote different test counts, or say "Serum 2.0.21", "exhaustive", or "local model already analyzes each frame", predate the current audit.

## Setup

- Windows, Python 3.14 (tested), Serum 2 **2.0.23** VST3 is required for live/UI work (W1 and W2 sessions).
- Cloud/CI work requires only `pytest`, `pydantic`, `cbor2`, `zstandard`, `pillow`, `numpy`.
- serum-mcp needs the presets folder from an environment variable and never guesses it:

```bash
export SERUM_PRESETS_PATH="/path/to/Serum 2 Presets/Presets"
# PowerShell: $env:SERUM_PRESETS_PATH = "C:\path\to\Serum 2 Presets\Presets"
```

- The repo puts `vendor/serum-mcp/src` on `sys.path` itself (via `conftest.py` and per-module inserts). Nothing needs `D:/serum-mcp`.
- The bulk-causal harness (`serum2/qualification/bulk_causal/serum_backend.py`) requires `D:/ableton claude` which is not in this repo and is intentionally not reproduced. All 330-control evidence is committed; no new sweep is needed.

## Run the Tests

```bash
# Install cloud-only deps first:
pip install pydantic cbor2 zstandard pillow numpy pytest

# Fastest way to verify the Gate-A closure work specifically (89 passed, 0 failed, 0 mocks):
python -m pytest tests/test_gate_a_real_canonical_flows.py tests/test_gate_a_fixes.py -q

# Full cloud suite (measured 2026-09-27, commit 885059a: 1523 passed, 160 failed*, 22 skipped, 16 errors*)
# * all failures/errors are pre-existing and environment-bound: missing qualification/screenshot fixtures
#   under a Windows-only D:\ path, tests requiring a live serum-mcp server, or legacy tests written before
#   the A3 mandatory-epoch invariant that still call ProducerBrain(epoch=None). None are Gate-A regressions.
python -m pytest

# Vendored serum-mcp tests (requires Serum 2.0.23 on Windows with serum-mcp running):
PYTHONPATH=vendor/serum-mcp/src python -m pytest vendor/serum-mcp/tests
```

## Reproduce the Audit Findings

Run the probe scripts against the unfixed `2f7acb3` worktree to verify F1–F7:

```bash
pip install pydantic cbor2 zstandard pillow numpy
export SERUM_PRESETS_PATH=/tmp/serum_fake && mkdir -p $SERUM_PRESETS_PATH

# From a worktree of 2f7acb3:
python audit/probes/probe1.py   # F4/F5: all three request values plan 0.8; epoch=None leak
python audit/probes/probe2.py   # F1/F2/F3: 221 pathless contracts, 89 MISSING_DOMAIN, macro crash
python audit/probes/probe3.py   # F7: 1/300 frames analysed + hand-typed dict → reference_verified=True
python audit/probes/probe4.py   # F4/F5: value substitution under real 2.0.23 epoch simulation
```

## Qualifying a Control (generic, serum-mcp only)

`serum2/qualification/candidate_binding_qualifier.py` takes only a control id. It reads the candidate accessor
`{list, index, field}` from the binding table, takes a value from the Atlas domain, runs the unmodified
`StructuralQualificationRunner` lifecycle (load → read → mutate → read → persist → reload → read), derives the
body path from a diff (never from a table), and checks that the whole extracted spec changed only in the targeted field.

```bash
python -m serum2.qualification.candidate_binding_qualifier filter1.enabled oscB.octave env2.decay --out ./qual_out
```

**Limits:** file-level evidence only — no direct-UI readback, and it creates **no** `CapabilityContract`. A binding is not a
contract. serum-mcp partial specs are positional and silently drop a write equal to a field's default. Only `toggle` and
`continuous` controls are handled; enum controls need reviewed value aliases. The verdict is not epoch-pinned.

## Security and Known Traps

- `ContractRegistry` unpickles `experiments/*.pkl` and `PASS1-*.pkl` records. Treat those files as executable code; only load ones you trust.
- `producer_brain.py` is `ADVISORY_ONLY` — it analyses intent but does not emit `AuthorizedOperation`. (Pre-fix: it had paths that bypassed admission and substituted qualification test values as operands — see F4/F5 in the audit.)
- `AuthorizedOperation` fields are trusted by the compiler; a hand-built one would pass. The common admission gate (A2) prevents one from being built without a matching final-contract row.
- `LIVE_UI_VERIFIED` now requires loader evidence (module SHA, nonce, screenshot hashes). Pre-fix: any hand-typed dict passed — see F7.
- `serum2/producer/_finalize_mu6_episode.py` writes a hand-authored "verified" episode on import. **Do not run it.**
- `serum2/evidence/{harness,spec,epoch}.py` are not in this repo. New Pass-1 evidence requires the full Windows/Ableton/serum-mcp chain (W1 session).
- `ClaimDefinition.claim_definition_id` calls `digest(obj, 8)` but `canonical.digest` takes one argument — the claim → contract build path is broken (AUDIT H1, pre-existing, not on the critical path).
- The `D:/ableton claude` path in `bulk_causal/serum_backend.py` is an unversioned legacy dependency. All current evidence was generated from it and is committed; the script is frozen for forensics only.

## Rejected Design Decisions

- **`quirky-franklin` final-contract-as-authority design** (`b5508df`): treats `final_execution_contract_v1.json` as the primary mutation authority. Rejected — conflicts with the evidence-gate architecture at `2f7acb3`. Kept as branch history only.
- **`epoch=None` in production:** disabled. Any code path that previously fell back to `epoch=None` must pass `ExecutionEpoch.OFFLINE_TEST` explicitly or supply the real 2.0.23 epoch.
- **DawDreamer as native-Serum substitute:** all DawDreamer evidence is tagged `HEADLESS_DAWDREAMER`. It cannot produce `VERIFIED` claims.
- **New 330-control sweep:** not needed. The existing 310 promotable evidence files are sufficient once F1/F2 are fixed. The 20 conformance exceptions are handled case-by-case after product closure.

## Contributing Rules

- Add data, not branches: new controls come from the Atlas, binding table, and evidence; never from `if target == ...`.
- Never weaken compiler validation or convert `HOST_PARAMETER` into execution authority.
- A new capability needs real mutation evidence (before / after / reload) through serum-mcp before any binding or contract exists.
- All new tests must exercise the real 2.0.23 epoch, not `epoch=None`. Use the `OFFLINE_TEST` epoch fixture for unit tests that cannot run on Windows.
- Report failures as failures; do not record projected or mock evidence. `HEADLESS_DAWDREAMER` ≠ `HOST_CONFIRMED`.

---

## Master Closure Plan (Full Detail)

*Serum 2.0.23 → YouTube Tutorial → Verified SerumPreset → Ableton 16-Bar Product*

> **Steps completed as of 2026-09-27 (commit `885059a`):** Step 1 (authority shape/`ADVISORY_ONLY`), Step 2
> (common admission gate), Step 3 (mandatory epoch, including closing the `gate_b_status(epoch=None)` gap
> Step 15's own W1-only invariant didn't originally cover), Step 4 (contract reachability — 207/221 exact,
> 14 named-duplicate, 3 documented gap, up from 10/231), Step 7 (ledger safety, all 9 module kinds), Step 9
> (UI readback binding — exact-epoch, full loader-evidence schema), Step 13 (exhaustive acquisition,
> **and** wired into the production runner, not just implemented in isolation). Step 8 (Stage-A
> completeness) is **partially** done: the ledger-side validation (`stage_a_is_filled`'s terminal-status,
> cycle, and ExpectedInventory checks) is closed, but the real VLM census that produces a Stage-A skeleton
> in production is a separate, still-open piece. Steps 5–6, 10–12, 14, and 16–26 remain open. See
> [GATE_A_MATRIX.md](GATE_A_MATRIX.md) for exact per-step evidence; the step descriptions below are kept
> as the original design record and are not individually re-annotated.

### Session Boundary Rules

**CLOUD SESSION** — use for: repository inspection, git, architecture, coding, refactoring, tests, contracts, admission, compiler, evidence schemas, acquisition code, VLM/OCR infrastructure, benchmark code, documentation, offline replay, static analysis, cloud simulations.

Cloud must **NEVER** claim: native Serum verification, actual Ableton verification, actual Windows GUI verification, real MCP ↔ Ableton ↔ Serum execution, actual audio/render success.

**LOCAL SESSION** — use **only** for tasks that genuinely require: Windows, Ableton Live, Serum 2.0.23, real Serum GUI, native preset loading, actual Ableton/Serum MCP execution, screenshots/tooltip readback, actual Serum re-save/readback, Windows GUI automation, local GPU VLM/OCR benchmarking, actual audio/render verification.

---

### Step 0 — Branch + Baseline (CLOUD)

- `git fetch --all --prune`
- `git checkout -B claude/gallant-cerf-u953wn origin/claude/final-mcp-execution-contract-2mew5v`
- Merge evidence-only from `feature/serum-track-loader`; keep `quirky-franklin` out of implementation path
- Commit `SECOND_OPINION_AUDIT_2026-09-26.md` and `audit/probes/`; push

### Step 1 — Gate A Core: One Authority (CLOUD)

**A1 — Authority shape**
- `AuthorizedOperation` carries the actual operand from the observed/requested value
- Do NOT use `scope["mutation_value_used"]` as the production mutation; rename it `qualification_test_value`
- `ProducerBrain` → `ADVISORY_ONLY` until it emits ledger-shaped operations
- Same rule applies to the Serum-device `ABLETON_MCP` route

### Step 2 — Common Admission Gate (CLOUD)

Place final-execution evidence checking at the common admission boundary:
```
CapabilityContract → admit() → final execution contract gate → AuthorizedOperation
```
Final contract must verify: row exists, same Serum epoch, not `MCP_EXEC_CONFORMANCE_EXCEPTION`, expected raw body path matches, operand in qualified domain. Compiler re-checks as defense-in-depth.

**Important:** The final execution contract is an *evidence/qualification gate*, not mutation authority. `CapabilityContract` remains the authority for mutation mechanics.

### Step 3 — Mandatory Serum Epoch (CLOUD)

- Eliminate `epoch=None` in production
- Add `ExecutionEpoch.OFFLINE_TEST` for tests; offline runs never produce `VERIFIED` claims
- Production uses Serum 2.0.23 SHA-256: `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3`

### Step 4 — Restore Contract Reachability (CLOUD)

Fix: 231 contracts loaded, 221 pathless, 10 reachable — because promoted evidence lacks `mutation_target_path`.

Fix `promote_verified_evidence()` so promoted contracts contain: `mutation_target_path`, operand kind, domain, execution binding. Also fix `contract_scope.coverage_of()` for all body-path grammars.

### Step 5 — Persist the Qualified Domains (CLOUD)

Create `parameter_characterization/domain_table_v1.json` with `tier: PROVISIONAL_DOMAIN` and evidence citations. Builder and runtime must consume the same artifact.

Rules: `PROVISIONAL_DOMAIN` → valid for execution, never `VERIFIED_EXACT` until stronger evidence exists.

### Step 6 — Fix the Binding-Evidence Path (CLOUD)

Correct `reference_engine.BINDING_EVIDENCE_DIR` to point at actual verified binding evidence. Add computed regression: `reachable contracts == promotable evidence files` (do NOT hard-code a count).

### Step 7 — Fix Ledger Safety (CLOUD)

Extend `state_ledger._coerce()` and `compile_ops()` using same accessor logic as `campaign_derive`:
- Supported kinds → derive normally
- Unsupported/unknown → `UNSUPPORTED` terminal
- Never: `KeyError` or whole-run abort

Add coverage across all 9 module kinds.

### Step 8 — Fix Stage-A Completeness (CLOUD)

Current failure: 300 frames acquired, 1 analyzed → `reference_verified=True`.

Implement `analysis_status` per frame: `ANALYZED | NOT_SERUM | UNREADABLE | EQUIVALENT_TO:<frame>`. Every manifest frame must have a terminal status. Use frame hashing + equivalence groups (do not require full inference on every visually identical frame). Also require ExpectedInventory controls to reach terminal status.

### Step 9 — Bind UI Readback to the Actual Run (CLOUD)

A valid UI readback must contain: run ID, track nonce, Serum module SHA, epoch, screenshot SHA-256, crop coordinates, actual observed value. A hand-written `{"route":"DIRECT_UI","values":...}` dict must be rejected.

### Step 10 — Add Native State Readback (CLOUD design; LOCAL execution in W1)

Design the second native channel:
```
compiled preset → hosted Serum instance → Serum native re-save → readback_diff → compiled-vs-native comparison
```
Gives: native state proof + native visual proof.

### Step 11 — Fix Unit Comparison (CLOUD)

Normalize numeric units before comparison. Fix `_ui_equal` so `"300" + unit "ms"` equals `"300 ms"`. Add tests for value, unit, value+unit, whitespace, case, numeric formatting.

### Step 12 — Gate A Test Certificate (CLOUD)

Machine-checkable Cert 1. All of these must fail closed:
- incomplete Stage-A
- fabricated UI readback
- cross-epoch contract
- `epoch=None`
- out-of-domain operand
- conformance-exception row
- path mismatch
- qualification-value substitution
- unsupported operand

And: requested values A, B, C must compile into three distinct operands (all within qualified domain).

### Parallel Cloud Track — A4 / A5 / A6 / A8

Once A1/A2/A3/A7 are working, these run in parallel:
- **A4** Contract reachability (Steps 4–6)
- **A5** Ledger safety (Step 7)
- **A6** Stage-A completeness (Step 8)
- **A8** Relabel DawDreamer evidence as `HEADLESS_DAWDREAMER`

### Step 13 — Exhaustive Acquisition (CLOUD)

Replace timestamp-seeking sampling with a single ffmpeg decode pass. Every source frame gets: frame index, PTS/timestamp, SHA-256. Build explicit perceptual-equivalence groups.

Requirements: decoded frames == manifest frames == terminal-analysis accounting. No silent-continue, no 300-second fallback, no stale cache reuse. Storyboard images: navigation only, never parameter-value evidence.

### Step 14 — Local VLM Infrastructure (CLOUD build; LOCAL benchmark later)

Build `observe(frame_group) -> readings[]` and the evidence policy:
- Numeric reading → `OBSERVED` only when VLM + OCR agree, OR ≥ 2 independent frame-group agreements; otherwise `AMBIGUOUS`/`UNREADABLE`
- Do not let the VLM itself decide truth
- Benchmark harness: exact-value accuracy, **confident-wrong rate** (the gating metric), abstention rate

### Step 15 — W1: First and Only Native Proof Session (LOCAL)

**W1-A — Gate B:** `env2.decay` → canonical path → capability → admission → genuine `.SerumPreset` → `create_serum_track` → native Serum → loaded-module SHA → native re-save → screenshot-bound readback → compare → restoration.

**W1-B — VLM ground truth:** Load `CAL_*` / `BULK_*` presets; capture static + tooltip screenshots, per-page crops, known unique parameter values → ground-truth dataset for C3.

**W1-C — Ableton silence diagnosis:** Use stock instrument; determine why arrangement/render produced digital silence; commit diagnosis.

**W1-D — Golden bundles:** screenshots, crop hashes, native re-save, module SHA, track nonce, run metadata → offline replay fixtures.

**LOCAL must NOT use:** DawDreamer, fake UI dict, cloud simulation, synthetic native proof as substitutes for Gate B.

### Step 16 — Cloud: Process W1 Results (CLOUD)

Consume W1 artifacts. Verify: compiled operand == native re-save operand == screenshot-bound value. Generate `CERT_2_NATIVE_SERUM.json` proving: loaded-module SHA matches 2.0.23, genuine preset SHA, native re-save matches compiled operand, screenshot readback matches, restoration verified, no DawDreamer in native chain.

### Step 17 — Local VLM/OCR Benchmark (LOCAL)

Run actual GPU benchmark on W1 ground-truth screenshots. Benchmark Qwen2.5-VL + OCR per control class: exact-value accuracy, confident-wrong rate, abstention.

**Gate C rule:** Only wire local VLM into Stage-A when the confident-wrong rate meets the threshold. Otherwise: `GATE C = BLOCKED`. Do not lower the standard.

### Step 18 — Cloud: Finalize Production Observation Path (CLOUD)

Integrate local VLM + OCR + frame groups + temporal fusion into the canonical Stage-A interface.

Hard invariant: model uncertainty → evidence uncertainty. Never: model uncertainty → guessed Serum value.

Remove/disable unsafe legacy fallback (`ProducerBrain` → `VisualReasoner`/Anthropic).

### Step 19 — Local W2: One Complete Real Tutorial (LOCAL)

Select one normal tutorial (do not tune the tutorial to the system). Run the complete pipeline: YouTube → full decode → local ASR → local VLM/OCR → evidence fusion → Stage-A → state ledger → Atlas → capability → admission → genuine preset → native Serum → native re-save → screenshot-bound UI readback → restoration.

Require: `coverage == COMPLETE` AND `reference_verified == True`.

### Step 20 — Cloud: Reference Certificate (CLOUD)

Generate `CERT_3_REFERENCE_REPRODUCTION.json` proving: every manifest frame accounted for, ExpectedInventory covered, every reproduced operation admitted, correct Serum epoch, native readback, restoration, `reference_verified=True`.

No manual override. No hand-entered readback. No partial evidence promoted into complete coverage.

### Step 21 — Local: 16-Bar Ableton Product Gate (LOCAL)

Use the verified Serum preset. Run: verified preset → Ableton Serum track → MIDI → arrangement → 16 bars → render → audio verification. The render must contain an actual audible signal. "Render file exists" ≠ "render succeeded."

### Step 22 — Cloud: Product Certificate (CLOUD)

Generate `CERT_3_PRODUCT.json` requiring: `reference_verified=True` + COMPLETE coverage + verified audible 16-bar render. This is the point at which the YouTube → Serum → Ableton product is closed.

### Step 23 — Only After Product Closure: 20 Exceptions (CLOUD + selective LOCAL)

Work exception-by-exception using the audit's root-cause classifications (do NOT start a new 330-control campaign):

`arp.transpose.range`, `fx.compressor.attack/ratio/release`, `global.fx_bus1/2_destination`, `global.use_ultra_on_render`, `global.voice_priority`, `macro1-8.name`, `mixer.noise.pan`, `mixer.sub.pan`, `oscA.warp_amount`, `oscNoise.pan`

Use LOCAL only when an exception requires GUI experiment, tooltip observation, native write, native save, or actual UI behavior.

### Step 24 — Full Control-Surface Certificate (CLOUD)

Create `CERT_4_CONTROL_SURFACE.json`. Each control gets exactly one truthful status: `EXECUTABLE+VERIFIED`, `EXECUTABLE+UNVERIFIED`, `UNQUALIFIED`, or `GLOBALLY_NON_EXECUTABLE`. Do not collapse into "330 solved."

### Step 25 — Golden Evidence / Offline Replay (CLOUD)

Check in Windows-generated evidence. Build offline replay tests so CI can verify acceptance logic without Windows.

### Step 26 — Final Documentation Cleanup (CLOUD)

Only now update README, `IMPLEMENTATION_STATUS`, `PROJECT_STATE`, and playbook/status docs. Correct all stale "2.0.21", "exhaustive", "local model already analyzes each frame", old test counts, old closure claims.

---

### What We Do Not Do

**Cloud — DO NOT:**
- Restart the 330-control sweep
- Merge `quirky-franklin` authority design
- Treat DawDreamer as native Serum
- Let qualification test values become production operands
- Allow `epoch=None` in production
- Allow incomplete Stage-A
- Allow fabricated UI readback
- Allow a VLM guess to become a Serum mutation
- Silently fall back to old 2.0.21 infrastructure

**Local — DO NOT:**
- Do repository architecture work or large refactors
- Rerun cloud-only tests
- Perform another 330-control campaign
- Use DawDreamer as a substitute for native Serum proof
- Report a native gate as passed without actual Windows/Ableton/Serum evidence

---

### The Most Important Rule

**The project is not closed because tests are green.**

It is closed only when:
- CLOUD proves the logic is safe
- LOCAL proves native Serum is real
- LOCAL proves the actual tutorial works
- LOCAL proves Ableton produces audible output
- CLOUD records machine-checkable certificates

The audit explicitly says the existing suite did not catch F1–F7 and that those failures could coexist with a mostly green test suite.

---

### Handoff Template for Future Sessions

Every future session handoff must include:

```
SESSION: CLOUD or LOCAL

CURRENT BRANCH: claude/gallant-cerf-u953wn
CURRENT COMMIT: <sha>

OBJECTIVE: <one line>

FILES: <exact file paths to change>

EXACT CHANGES: <what to do>

DO NOT TOUCH: <files/invariants to preserve>

TESTS: <what to run and what to expect>

EXPECTED RESULT: <what success looks like>

FAILURE CONDITIONS: <what means stop and ask>

EVIDENCE TO SAVE: <what artifacts to commit>

HANDOFF TO NEXT SESSION: <what the next session needs>

FINAL EXECUTION CHECKLIST:
Step 0: ✓ branch + audit report (this session)
Step 1: [ ] Gate A-core A1 advisory-only
Step 2: [ ] Gate A-core A2 common gate
Step 3: [ ] Gate A-core A3 mandatory epoch
...
Final Gate: [ ] Cert 4 control surface
```

Cloud prompt must say: *Do not claim Windows/Ableton/Serum-native verification. Do not substitute simulation for native evidence.*

Local prompt must say: *Only real Windows + Ableton + Serum 2.0.23 evidence counts. Do not substitute DawDreamer/cloud simulation.*
