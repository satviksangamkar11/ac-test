# Reference-to-Serum Reproduction (VLP1)

A pipeline that watches a reference (a tutorial video or sound), works out which **Serum 2.0.23** controls were
changed, and reproduces that state in a `.SerumPreset` — with every step gated by evidence, not by naming or
memory. Serum is driven only through [serum-mcp](vendor/serum-mcp) (vendored here). Claude Code is the model
runtime; there is no Anthropic SDK call in the canonical path.

> **Status (measured 2026-09-26):** `python -m pytest` → **1223 passed, 25 failed, 22 errors, 19 skipped**.
> All 25 failures and 22 errors are environment-bound (Windows Serum binary unavailable, serum-mcp not running).
> Cloud-only tests are green.
>
> **Known integrity gaps (being fixed — see [SECOND_OPINION_AUDIT_2026-09-26.md](SECOND_OPINION_AUDIT_2026-09-26.md)):**
> - Only 10 of 231 CapabilityContracts are reachable on the real 2.0.23 epoch (F1).
> - The ledger crashes on `macro` and `singleton_field` controls (F3).
> - Reference verification can pass with 1/300 frames and a hand-typed readback (F7).
> - ProducerBrain uses the qualification test value as the production operand (F4).
> - Cross-epoch execution is possible via `epoch=None` (F5).
>
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

The project has four machine-checkable certificates, produced in order:

| Certificate | Where | What it proves |
|---|---|---|
| **Cert 1 — Integrity** | Cloud | No authority bypass, no cross-epoch execution, no qualification-value substitution, no incomplete Stage-A success, no fake UI readback, no out-of-domain execution, no unsupported mutation |
| **Cert 2 — Native Serum** | W1 Windows + Cloud | Loaded-module SHA matches 2.0.23 pin, genuine preset SHA, native re-save matches compiled operand, screenshot-bound readback matches, restoration verified, no DawDreamer in chain |
| **Cert 3 — Product** | W2 Windows + Cloud | One untuned real tutorial → `reference_verified=True` with COMPLETE coverage + verified audible 16-bar render |
| **Cert 4 — Control Surface** | Cloud + selective Local | Every non-exception control `EXECUTABLE+VERIFIED`, all 20 exceptions classified as `EXECUTABLE+UNVERIFIED`, `UNQUALIFIED`, or `GENUINELY_NON_EXECUTABLE` |

**Critical path:** Step 0 → Gate A-core (A1+A2+A3+A7) → Gate A rest + Track B + C1 (parallel) → W1 → Cert 2 → C3 local VLM → integrate → W2 → Cert 3 → 16-bar render → Cert 3 product → 20 exceptions → Cert 4

See [SECOND_OPINION_AUDIT_2026-09-26.md](SECOND_OPINION_AUDIT_2026-09-26.md) for the full adversarial audit (findings F1–F16, Q1–Q20, branch topology, conformance-exception root causes).

## Current Implementation State

### What works (cloud, no Windows required)
- CapabilityContract loading from pickle stores (`experiments/*.pkl`, `PASS1-*.pkl`) — 10 Pass-1 contracts with `mutation_target_path` set
- `state_ledger.build_all()` for `osc/env/lfo/filter/fx` module kinds (crashes on `macro`/`singleton_field` — F3, being fixed)
- `state_admission.admit_rows()` — 10 controls admittable under the real 2.0.23 epoch
- `authorized_state_compiler.compile_ops()` — generic compiler with `_validate()` defense-in-depth
- `serum_mcp.generate_preset` / `pack_file` — genuine `.SerumPreset` output
- `run_reference_reproduction()` — run object, proof level, coverage (but currently bypassed by F1/F7)
- Test suite: 1223 passing tests (all environment-bound failures are expected)

### What is broken or missing (being fixed)
- **F1:** 221 of 231 promoted contracts are pathless — `promote_verified_evidence()` missing `mutation_target_path` → only 10 reachable
- **F2:** 89 of 310 evidence files rejected as `MISSING_DOMAIN` at runtime; `BINDING_EVIDENCE_DIR` points at wrong directory (0 of 9 load)
- **F3:** `_coerce()` crashes on `macro` (16 bindings) and `singleton_field` (53 bindings)
- **F4:** `_build_serum_preset_plan` uses `scope["mutation_value_used"]` (the qualification test value, e.g. 0.8 for attack), not the user's requested value
- **F5:** `epoch=None` serves 2.0.21 contracts to a 2.0.23 runtime; the env1.attack "proof" only works cross-epoch
- **F7:** `stage_a_is_filled` uses `any()` — 1/300 frames analysed → `reference_verified=True`; hand-typed UI dict accepted
- **F8:** `_ui_equal` unit-string comparison causes false negatives ("300" + unit "ms" ≠ "300 ms")
- **F9:** Orchestrator returns `COMPLETE` even when bridge unavailable; never feeds UI readback into run
- **F10:** Two independent authority models; NL path skips the final-contract gate entirely
- **F11:** 330-control sweep requires `D:/ableton claude` (deleted); headless DawDreamer mislabelled as "live MCP"
- **F12:** Frame acquisition caches by video only (not by decode params), truncates at 300 s, silently drops failures
- **F13:** Legacy `VisualReasoner` cloud fallback still reachable from `ProducerBrain`
- **F15:** "2.0.21" string in Atlas, `production_pipeline.py`, `reference_state_reconstructor`, README, main.py
- **F16:** The existing test suite never exercises the real 2.0.23 end-to-end path (uses `epoch=None` or `admit()` directly)

### Gate-A fix targets (active, cloud)
| Step | Fix | Closes |
|---|---|---|
| A1 | `ProducerBrain` → `ADVISORY_ONLY`; rename `mutation_value_used` → `qualification_test_value` | F4 |
| A2 | Common gate in `admit_rows`: final-contract epoch + exception + path + domain check | F10 |
| A3 | `epoch=None` raises; `OFFLINE_TEST` epoch caps claims at `OFFLINE_ONLY` | F5 |
| A4 | `promote_verified_evidence` writes `mutation_target_path`; fix `BINDING_EVIDENCE_DIR` | F1, F2 |
| A5 | `_coerce`/`compile_ops` support all 9 module kinds; unknown → `UNSUPPORTED` terminal | F3 |
| A6 | Per-frame `analysis_status`; `stage_a_is_filled` → `all()`; ExpectedInventory coverage | F7 (partial) |
| A7 | UI readback requires loader evidence (module SHA, nonce, run id, screenshot hashes + crops); native re-save channel; fix `_ui_equal` unit normalization | F7, F8 |
| A8 | Relabel DawDreamer evidence as `HEADLESS_DAWDREAMER` in final-contract metadata | F11 |

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

# Cloud tests (expected: 1223 passed, 19 skipped, 25 failed*, 22 errors*)
# * all failures/errors require Windows + Serum binary + serum-mcp running
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
