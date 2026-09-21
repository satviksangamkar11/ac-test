# Repository Audit

Scope: everything tracked in this repo (274 files, ~43k lines of Python) plus the untracked `serum2/qualification/candidate_binding_qualifier.py`.
Read-only audit by six parallel reviewers, each covering a disjoint slice; the highest-severity items were then re-checked by hand
(marked **[re-verified]**). Items marked *suspected* were not confirmed by running code.

Test baseline (measured, not quoted): `python -m pytest -q` → **925 passed, 3 skipped** before vendoring serum-mcp;
**1178 passed, 3 skipped** after (the extra 253 are `vendor/serum-mcp/tests`).
Older docs quote 149 / 255 / 799 / 861 — all stale.

## 1. Invariant scorecard

| Invariant | Enforced? | Evidence |
|---|---|---|
| HOST_PARAMETER is not execution authority | **Yes** | `target_surfaces.EXECUTION_ELIGIBLE_ROUTES = {SERUM_PRESET_STRUCTURAL, BODY_STATE}`; compiler restricts to `{SERUM_PRESET_STRUCTURAL, BODY_STATE, TOPOLOGY}`; five direct tests |
| Every derived op reaches a terminal admission outcome | **Yes** | `state_admission.admit_rows` raises on a DERIVED row left un-admitted; `conservation()`; partial direct test (`test_u8_event_audit`) |
| Compiler requires an execution-eligible binding | **Yes, but forgeable** (F2) | `compile_ops._validate` per kind; only tested in `tests/test_authorized_preset_compiler.py`, none in `serum2/producer` |
| Epoch isolation | **Partly** | `ContractRegistry._apply_epoch` filters by binary SHA; atlas data is hard-stamped 2.0.21 (F5) |
| Learned skills / memory cannot grant authority | **Yes for the canonical path** | ten direct tests; candidate layer verified advisory. Legacy `skill.py` gates only on `admitted` |
| Brain never authorizes execution | **No** (B1, B2) | MCP and host paths set `admitted=True` without a contract |
| Proof level and coverage are separate axes | **Yes** | `reference_reproduction`: `verification_level` vs `coverage_status`; `reference_verified` needs LIVE_UI_VERIFIED + COMPLETE |
| No per-parameter hardcoded execution logic | **No** (H3, M-tables) | `contract_registry.py:148,164`; `ACCESSORS`; legacy compiler |
| No SDK, Claude Code is the runtime | **No** (B4) | `VisualReasoner` imports the Anthropic SDK and loads `.env` |

## 2. HIGH findings

**H1. `canonical.digest` breaks the claim → contract chain. [re-verified]**
`serum2/evidence/claim.py:148-153` calls `digest(obj, 8)`; `serum2/evidence/canonical.py` defines `digest(evidence)` with one argument.
`ClaimDefinition.claim_definition_id` raises `TypeError`, so `ClaimEngine.add` → `build_contract` cannot run from this repo.
Existing contracts only load because they are unpickled, not rebuilt.

**H2. Evidence generation depends on the old repo.** `serum2/evidence/{harness,spec,epoch}.py` and `serum2/qualification/a3_evidence_extension`
are not in this repo [re-verified for the first three]. `qualification/pass1/{harness_v9,run_pass1_experiments,run_positive_controls,build_pass1_contracts}.py`
put `D:\ableton claude` first on `sys.path` and import a *different* `serum2` package from it, then pickle contract objects built with the old classes.
Pass-1 experiments therefore cannot be reproduced from this repo alone, and the old package can shadow this one.

**H3. Hardcoded per-target branches in contract loading.** `producer/contract_registry.py:148,164` special-case
`'envelope_field_release'` / `'envelope_field_attack'` inside the generic loader. [re-verified]

**H4. Wrong repo root.** `producer/route_classifier.py:18` and `producer/capability_qualification_sweep.py:17` use
`Path(__file__).resolve().parents[3]`, which is the drive root `D:\`, not the repo root (`parents[2]`). [re-verified] Inert only because the package imports another way.

**H5. Unforgeable-authority gap in the compiler (F2).** `execution/authorized_state_compiler.py:80-119` trusts the fields carried by an
`AuthorizedOperation` (`binding_type`, `contract_body_path`, `contract_domain`, epoch, status) and never re-checks them against `ContractRegistry`.
Any caller can hand-build an authorized operation; route domains come from the operation itself.

**H6. Live-UI readback is trust-based (F4).** `execution/state_comparator.py:compare_ui` checks only that `route == "DIRECT_UI"`.
It does not bind the readback to the preset's sha/name, does not check the Serum version against the epoch, looks values up by `control_id`
ignoring the rack (two racks collide; same in `reference_reproduction.py:163-166`), and `to_experience_record` accepts a caller-supplied readback
that need not be the one used in the run. `build_readback_record` compares with exact `==` while `compare_ui` normalizes, so they can disagree.
A `LIVE_UI_VERIFIED` result is only as honest as the JSON passed in.

**H7. Legacy compiler is a parallel authorization path.** `execution/authorized_preset_compiler.py:125-227` checks only
`admission_status == "AUTHORIZED"`, hardcodes every value for cap_001–cap_014, never reads `qualified_parameters`, and counts no-op steps
(`_compile_bus1_convolver`, `_compile_init`) as compiled. Still imported by `tests/test_authorized_preset_compiler.py`. Fence or remove.

**B1. Brain self-attests prerequisites.** `producer/producer_brain.py:647-663` builds `current_context` and `proposed_prerequisites_verified`
from the contract's own `declared_value`, so the prerequisite check cannot fail.

**B2. Brain grants authority on the MCP/host paths.** `producer_brain.py:1999-2002` sets `admitted=True`
(`"MCP_HOST_MAP_QUALIFIED"`) from host-map membership alone [re-verified]; the host-operation path does the same on substring keywords ("a clip", "midi track").
`u8_event_audit._terminal` then reports this as `AUTHORIZED_EXECUTION`.

**B3. Brain invents values.** `producer_brain.py:796-798` defaults to `(RELATIVE, 0.20)` (always an increase) when no value is detected;
`_direction_from_words` (line 207) silently defaults to LONGER; "darker" maps to a higher cutoff (lines 115-117).

**B4. SDK and `.env` loading.** `producer_brain.py:1015-1027,1405` instantiates the legacy `VisualReasoner`, which imports the Anthropic SDK
and loads `.env` into `os.environ` (`visual_reasoner.py:503-514,650`). Contradicts the "Claude Code is the runtime" rule.

**B5. Hand-authored verification.** `producer/_finalize_mu6_episode.py` executes on import and writes an episode with a hardcoded video id,
`Env1.Release` at 36 ms, `controls_matched: True`, a literal readback dict and status `STATE_REPRODUCTION_VERIFIED`. Do not run it; delete or quarantine.

**B6. Scope guard is a no-op.** `knowledge/step_6_6_*.py:330-352`: `_check_scope_match` returns True unconditionally. [re-verified]

**B7. Unsafe deserialization of authority artifacts.** `producer/contract_registry.py:146,162,178,200`, `route_selection.py:92`,
`qualification/pass1/qualify_bindings_pass1.py:91`, `build_pass1_contracts.py:38` call `pickle.load` on tracked `.pkl` files
(`experiments/*.pkl`, 13 `PASS1-*/PC-*` records) with no integrity check other than the later epoch filter. Anyone who can change those files can execute code.

## 3. MEDIUM findings

- **Epoch stamping.** `reference/serum_atlas.py:37-39` and `serum_ui_atlas.py:36` hardcode "2.0.21"; `atlas_provenance()` stamps it on 2.0.23 runs; the schema snapshot has no hash pin (the audit has one).
- **FX slot/rack handling.** `_FX_PATH` ignores slot index (`authorized_state_compiler.py:22`); validation uses `rack or 0`, lowering uses `provenance["rack"]` which can be `None`; two same-type FX in one rack cannot be represented; unobserved list slots are filled with `{}` (serum-mcp defaults).
- **Two admission strictness levels.** `target_resolution.py:150` hardcodes `usable_for(required_causal=True)` while `state_admission.admit_rows` admits STRUCTURAL_ONLY contracts.
- **Route taxonomies drift.** `route_classifier.ExecutionRoute`, `route_selection.ExecutionRoute`+`EvidenceTier`, `batch_qualification_system.RouteType` overlap with different members.
- **`admit()` details.** `admission.py:107-115`: passing `True` skips the `must_hold_identical` check; with no CAUSAL_VERIFIED contract it picks `matches[0]`, not the strongest.
- **Attribution and learning gates.** `step_6_9:250-257` attributes on a single before/after direction match at 0.7, ignoring tier, noise and measurement id (the `expected_direction` branch is dead: `build_contract` never writes it). `step_6_10:378` blocks learning only for INSUFFICIENT_EVIDENCE, so STRUCTURAL_ONLY/UNKNOWN episodes become `learning_eligible`. `production_pipeline.py:305-309,446,823` marks stages VERIFIED from a caller-supplied sha and sets `learning_eligible: True` unconditionally.
- **`build_contract` skips the comparability cohort filter** that `claim._qualifying` applies (`capability_contract.py:191-192`).
- **Candidate ranking.** `candidate_ranking.py:192-206`: grounding advisory reads `claim.status`/`target_canonical_id`, which `GroundedClaim` lacks, so it is a silent no-op (and would add +0.1 even for CONFLICT). A `SKILL_VARIANT` winner's operand overrides `target_value` (`producer_brain.py:1323-1331`; only direction is consumed today).
- **Skill store fail-open.** `skill_library.py:185` defaults `verified=True`; `SkillStore.load` trusts stored `confidence`/`outcome_stats`. `skill.py:190,275-277` gate only on `admitted`; `skill_id` goes into file paths unsanitized. Retrieval falls back to unfiltered candidates when the context filter rejects all.
- **Evidence fusion.** `evidence_fusion.py:266-290`: bare keyword co-occurrence ("lfo", "filter") yields event-level AGREEMENT, including for removed routes. `visual_reasoner.py:331-332` defaults status→OBSERVED, confidence→0.5.
- **Plan/finalize.** `finalize_*` accept a caller's `readback_verified` boolean and any non-empty sha256 without reading the file; a bare `MCP_PLAN_READY` is labelled PARTIALLY_RECREATED.
- **Acoustic kernel.** `acoustic_measurement.py:109-117` decodes 8-bit WAV as signed (it is unsigned) yet reports COMPUTED.
- **Storage.** `knowledge/step_5_6` re-initializes a corrupt store silently and overwrites `.backup`; persistence is non-atomic everywhere; `run_id`/`experience_id` are used unsanitized in paths.
- **Presets folder side effects.** `serialize` writes to `VLP1/`; `qualify_bindings_pass1.py:98` writes `VLP1-pass1-bindings/` and never cleans up; `candidate_binding_qualifier.py:67` writes `VLP1-qual-scratch/` and moves the file (a crash leaves it behind).
- **Per-target tables.** `qualify_bindings_pass1.ACCESSORS`; `generate_binding_table.FX_PARAM_ALIASES`/`ENUM_VALUE_ALIASES`; `body_state_mapping.json` fixes `FXRack0.FX.1`; `compiler/targets.py`, `compiler/mcp_intent.py`. `semantic_vst3_mapping.json` maps `fx_field_dist_drive` to "Filter 1 Drive" (*suspected*).
- **Silent fallbacks.** Broad `except Exception: print(...)` in `contract_registry.py` (five sites), `route_classifier.py`, `producer_brain.py:1632` (→ `BRAIN_ERROR`); `production_pipeline.py:511-526` infers role/character from keywords with silent defaults.
- **Mixed flat/package imports** (`from step_6_2_... import` vs package-qualified) can load one module twice under two names (*suspected*).

## 4. Test-suite findings

- **No active xfail.** `RED = pytest.mark.xfail(strict=True…)` is defined (`test_p3_skill_library.py:100`, `test_p6_grounding.py:739`) but never applied. The "P6.5/P6.6 xfail RED blockers" wording in older notes is stale.
- **Silent skips / false passes:** `test_timeline.py:236` prints `[SKIP]` and passes when the mU6 artifact is absent; `test_u4_observation_canonicalization.py:276`; `test_u6_qualification_planner.py:390,409`; p3/p6/stage-A tests skip when gitignored `serum2/data` is missing. `tests/test_compiler_serum_mcp_integration.py:77-80` imports a nonexistent `serum2.mcp.serum_mcp_integration`, so it always skips.
- **Machine dependence:** `test_u7_osc2_qualification.py:28` reads a `C:\Users\Satvik\...` fixture (it copies to `tmp_path`, so the user's folder is not written).
- **Weak assertions:** tautological or vacuous checks in `test_u5_surface_separation.py:266-304` and `test_u6_qualification_planner.py:322-398`.
- **Coverage gaps in `serum2/producer/`:** no test for epoch isolation, none for compiler rejection (both live only in `tests/`), and no named test for "terminal outcome on the route-admission path".
- Not fully read by the test reviewer: p4, p5, p6.6, p7, timeline, u1–u3, ordered-resolution, route-selection.

## 5. Repository hygiene

- **Not reproducible from a clean clone.** `serum2/data/` (runs, frames, stores) is gitignored but README/tests depend on it; no `requirements.txt`, `pyproject.toml`, `pytest.ini` or `conftest.py` exists.
- **Personal paths:** 104 occurrences across 32 tracked docs/JSON (`C:\Users\Satvik\…`, `D:\ableton claude final best\…`), including `vlp1_*_episode_pointer.json`, `vlp1_proof_result.json`, `qualification/pass1/bindings/*.json`.
- **Tracked binaries/generated files:** `gate_2a_ep_prod_001_render.wav` (8 MB), 13 pass-1 `.pkl` records, `experiments/*.pkl`, a `.backup` store, ~20 status JSON/MD files at root, two identical `scratch_mu6_transcript*.json`.
- **`.gitignore`** lacks `.pytest_cache/`, `.claude/settings.local.json`, `video_screenshots/` (4.7 MB, untracked); `archive/` is empty.
- **Doc contradictions:** `README_FROZEN.md` says phase B1 and a branch that no longer exists and links paths that do not exist (`serum2/audit/`) or are gitignored; `B1_COMPLETION_SUMMARY.md` body still says "25 tests, complete"; `docs/BINDING_DISCOVERY_FROZEN_5.md` and `docs/CAPABILITY_QUALIFICATION_AUDIT.md` say Env2 Decay is unbound (it is admitted on 2.0.23); both source manifests list files not in the tree; Gate 7 docs say "PERFECT MATCH" for what §29 classes as screen inspection, not Direct-UI readback.
- **Untracked planning docs** (`GROUP1_…`, `PHASE_ALPHA_…`, `QUALIFICATION_ANALYSIS.md`) contain projected counts and an "architecture validated" claim not supported by evidence; `PHASE_ALPHA_STATE_CHECKPOINT.md` quotes a 799-test figure that was never measured.
- **Dead or historical code:** `knowledge/step_6_11_closed_loop_proof.py` (static dicts, tests nothing), `intent_bridge.py`, `semantic_intent_resolver.py`, `producer/reference_skill.py` (no callers), `skill.py`/`skill_graph.py`/`skill_retrieval.py` (tests only), `compiler/` (legacy NL layer), `orchestration/` (Gate 2A scripts with hardcoded `True` flags after `input()`).

## 6. Fixed in this session

- Removed fabricated mock qualification evidence and three abandoned scripts written earlier this session.
- Vendored serum-mcp into `vendor/serum-mcp/` (upstream commit in `UPSTREAM_COMMIT.txt`) and replaced nine `D:/serum-mcp/src` references with repo-relative paths (also fixed a missing `Path` import in `state_comparator.py`).
- Added `serum2/qualification/candidate_binding_qualifier.py` (untracked): candidate-driven binding qualification through serum-mcp only. Regression: reproduces all 10 Pass-1 bindings; `filters[0].enabled` → `VoiceFilter0.plainParams.kParamEnable`, `filters[1].enabled` → `VoiceFilter1.plainParams.kParamEnable`, file-level evidence only, no contract created.
  Known limits: candidates are pre-marked `verified=True` with a label `capability_key`; verdict is not epoch-pinned; `_flat` drops empty containers.

## 7. Suggested order of fixes

1. H1 (`digest` signature) and H4 (`parents[3]`) — one-line fixes.
2. H5/H6: re-validate `AuthorizedOperation` against `ContractRegistry`; bind UI readback to preset sha, version and rack.
3. B1–B3: remove Brain self-attestation, MCP/host self-grants and invented defaults; wire them through admission.
4. B4/B5/H7: delete `_finalize_mu6_episode.py`, fence `VisualReasoner`, retire `authorized_preset_compiler.py`.
5. B7: replace pickled contract stores with hash-pinned JSON.
6. Hygiene: dependency file, scrub personal paths, move status docs to `docs/history/`, gitignore additions.
