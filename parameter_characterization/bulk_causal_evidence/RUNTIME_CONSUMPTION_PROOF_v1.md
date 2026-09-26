# Runtime-Consumption Proof v1 — `env1.attack`

Wires the committed `final_execution_contract_v1.json` into the real producer runtime as the
required execution-evidence source for every atlas_id it covers, without touching the existing
authority chain. No new sweep, campaign, or evidence discovery was performed.

Revision note: after the first pass (commit `54bee02`) was reviewed, four gaps were identified and
closed in this revision — see "Repairs from review" below.

## Files changed

| File | Change |
|---|---|
| `serum2/producer/contract_registry.py` | `execution_specs` index (unchanged from `54bee02`) + epoch-aware `execution_spec(atlas_id)`: with an explicit run epoch set, a final-contract row proven on a different epoch is excluded (`execution_spec_excluded`), never served across epochs. `epoch=None` (legacy frontier) serves it unfiltered, the same convention every other loader in this class already uses. |
| `serum2/producer/producer_brain.py` | Same atlas_id threading as `54bee02`, but `_build_serum_preset_plan` now **fails closed**: for any atlas_id the final contract is meant to cover, a missing row, an epoch-excluded row, a row still classified `MCP_EXEC_CONFORMANCE_EXCEPTION`, or a row whose `expected_raw` disagrees with the admitted `mutation_target_path` all refuse the plan (`NOT_ADMITTED`) instead of silently proceeding. `allowed_operation`/admission/`ContractGovernedExecutor`/epoch machinery remain untouched. |
| `serum2/producer/test_final_execution_contract_runtime.py` | 13 tests (was 9): added the four fail-closed cases (missing row, forced exception, forced mismatch, epoch mismatch). |
| `serum2/qualification/bulk_causal/live_proof_env1_attack.py` | Fixed to call `campaign_derive.base_spec()/with_field()` and `preset_build.BASE`/`serum_mcp.preset.mapping.apply_spec` with their real signatures, and to write the edited body with the actual generic Serum preset packer (`serum_mcp.preset.packer.pack_file`) instead of a hand-rolled `json.dumps` — a genuine, round-trippable `.SerumPreset` container. |

No existing Step 6 file (`step_6_6/6_7/6_8`), `admission.py`, `ClaimEngine`, compiler validation, or
epoch module was modified. None of the 20 conformance exceptions were touched, reclassified, or made
executable — the new gate specifically enforces the opposite.

## Repairs from review (of `54bee02`)

1. **"Final contract not actually driving execution" / "missing spec never blocks the plan."**
   Fixed: `_build_serum_preset_plan` now fails closed on a missing, epoch-excluded, exception-classed,
   or mismatched final-contract row for any atlas_id it should cover (see the 4 new tests). The
   original task's explicit constraint — `CapabilityContract` stays sole authority for
   `allowed_operation`/status/prerequisites, and the final contract must never bypass
   `CapabilityResolver`/`AdmissionHandoff`/`admit()`/epoch checks/`ContractGovernedExecutor` — is kept:
   `mutation_target_path`/`mutation_value_used` still come only from the admitted `CapabilityContract`.
   The final contract is now a hard gate on top of that authority, not a value source for it.
2. **Epoch bypass.** `execution_spec()` now checks the run's `self.epoch` against the final contract's
   own recorded `(serum_version, serum_binary_sha256)` and excludes the row on mismatch — proven by
   `test_epoch_mismatch_fails_closed`, which runs a real `ProducerBrain(epoch=EPOCH_2_0_21)` and shows
   `env1.attack`'s plan is refused rather than silently served 2.0.23 evidence under a 2.0.21 run.
3. **Real MCP + Serum execution not proven.** Still true, and still cannot be made true inside this
   cloud container: there is no DawDreamer, no `Serum2.vst3` binary, and no live `serum-mcp` MCP tool
   connection here (verified again this pass). This is an environment limit, not a code gap — see
   "Proof layer B" below for exactly what could and could not be verified in this session.
4. **Fake preset write / wrong generic-loader calls.** Fixed: `live_proof_env1_attack.py` now calls
   `campaign_derive.base_spec()`/`with_field(spec, edit, value)` and
   `serum_mcp.preset.mapping.apply_spec(BASE.data, spec)` with their real signatures, and writes the
   edited body through `serum_mcp.preset.packer.pack_file` — the same generic packer the 330-row sweep
   code uses. I verified in this container (without touching real Serum) that this produces a real,
   round-trippable `.SerumPreset`: `pack_file(...)` then `unpack_file(...)` round-trips
   `kParamAttack` from `0.0005` (baseline) to `5.000000000000001` (edited) exactly.

## Control used

`env1.attack` — the one already-proven `MCP_EXEC_HOST_CONFIRMED` control named in the task. No new
control was characterized.

## Runtime call chain (as traced, and as exercised by the tests)

```
ProducerBrain.execute()
  -> _resolve_concept() -> TargetResolver.resolve("Env1.Attack")
       -> serum_atlas.normalize_control -> canonical_id = "env1.attack"   (the atlas_id)
       -> capability_key = "envelope_field_attack"                        (via SEMANTIC_TARGETS)
  -> _execute_inner(): capability_target = "envelope_field_attack"; atlas_id = "env1.attack"
  -> _run_serum_preset_path(..., capability_target, atlas_id)
       -> contract = ContractRegistry.get("envelope_field_attack")        [AUTHORITY: CapabilityContract]
       -> _resolve_and_admit() -> CapabilityResolver(registry).resolve()
                                -> AdmissionHandoff(admission_mod, registry).submit_to_admission()
                                -> admission.admit()                       [unmodified]
       -> _build_serum_preset_plan(..., contract, atlas_id)
            -> ContractGovernedExecutor().create_execution_intention()     [unmodified, Step 6.8]
            -> authority.scope["mutation_target_path"], ["mutation_value_used"]   [AUTHORITY, unchanged]
            -> ContractRegistry.execution_spec("env1.attack")              [EVIDENCE + GATE: final contract]
                 -> None / exception-classed / path-mismatched -> plan REFUSED (NOT_ADMITTED)
                 -> else -> plan["final_execution_contract"] = {...} attached, plan READY
```

## Exact final-contract source path

`parameter_characterization/bulk_causal_evidence/final_execution_contract_v1.json`
(`ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH`)

## Exact final-contract fields consumed

`rows[atlas_id].mcp_operation`, `.expected_raw`, `.declared_domain`, `.final_execution_classification`,
`.restoration_verified`, plus `producer_lookup[atlas_id].exception_policy`, plus the document-level
`serum_version`/`serum_binary_sha256` (now used for the epoch gate). No `allowed_operation`,
`raw_body_path`, or `valid_domain` field was read, invented, or added to this index.

## Exact CapabilityContract fields consumed

`contract.target`, `contract.allowed_operation` (read in `_direction_for`/`_build_advisory_chain`,
unchanged), `contract.prerequisites`, `contract.scope["mutation_target_path"]`,
`contract.scope["mutation_value_used"]` — all still sourced exclusively from the pickled
`CapabilityContract` stores `ContractRegistry` already loaded before this change.

## Proof that no pickle/evidence-directory/fallback source supplies the execution-evidence fields

`test_execution_evidence_traces_only_to_the_file_the_registry_was_pointed_at` swaps
`ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH` for a temp file whose `env1.attack` row carries a
sentinel value (`test_value=999.0`, `exception_policy="PROOF_SENTINEL_7f3a9c"`) that exists nowhere
else in the repository, re-runs the real `ProducerBrain`, and asserts the plan's
`final_execution_contract` fields equal exactly that sentinel — while the authority-side
`mutation_target_path`/`mutation_value_used` (from the untouched pickle-backed `CapabilityContract`)
stay unchanged. `test_missing_final_contract_row_fails_closed`, `test_conformance_exception_row_
fails_closed_even_if_admitted`, `test_mismatched_raw_path_fails_closed`, and
`test_epoch_mismatch_fails_closed` show the same swap technique driving the gate's four refusal
paths.

## Serum version / SHA

`2.0.23` / `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3` (unchanged; carried in
the committed final contract's document-level fields and rows, and in
`serum2/producer/execution_epoch.EPOCH_2_0_23`).

## Proof layer A — deterministic pytest integration proof

`serum2/producer/test_final_execution_contract_runtime.py`, **13 tests, all passing**:

- source-path identity, `env1.attack` row is `MCP_EXEC_HOST_CONFIRMED` + restoration-verified
- `ContractRegistry.execution_spec("env1.attack")` matches the committed row exactly
- unknown atlas_id / `None` → no fallback, returns `None`
- real `ProducerBrain` admits `env1.attack` through the real chain
- authority fields (`mutation_target_path`, `mutation_value_used`) equal the `CapabilityContract`,
  not the final contract's own differently-shaped test value
- plan's `final_execution_contract` fields equal the committed row, `agrees_with_admitted_mutation_path=True`
- the sentinel-swap provenance proof described above
- **missing row → fails closed** (`REFUSED_NO_FINAL_CONTRACT_EVIDENCE`)
- **forced conformance-exception classification → fails closed** (`REFUSED_CONFORMANCE_EXCEPTION_NOT_EXECUTABLE`)
- **forced raw-path mismatch → fails closed** (`REFUSED_FINAL_CONTRACT_MISMATCH`)
- **epoch mismatch (`ProducerBrain(epoch=EPOCH_2_0_21)`) → fails closed** (`REFUSED_NO_FINAL_CONTRACT_EVIDENCE`)
- no `allowed_operation`/`raw_body_path`/`valid_domain` exists anywhere in the new index

Focused pytest result: **13 passed** (this file), **59 passed** together with
`test_ordered_resolution.py` (no regressions in the existing ordered-resolution suite). Full
`serum2/producer/` suite (excluding pre-existing, unrelated `PIL`/environment-dependent collection
errors verified present before this work via `git stash`): **893 passed** (was 889 before this
revision's 4 new tests), same 2 pre-existing failures / 16 pre-existing errors, unchanged.

## Proof layer B — live agent-driven execution

`serum2/qualification/bulk_causal/live_proof_env1_attack.py` builds the admitted plan through the
same real `ProducerBrain` chain, then — using only the existing generic pieces
(`run_mcp_execution_harness.LiveBackend`, `campaign_derive.base_spec/with_field`,
`serum_mcp.preset.mapping.apply_spec`, `serum_mcp.preset.packer.pack_file`,
`serum2.producer.execution_epoch`) — checks the installed Serum epoch and, if it matches
`2.0.23`/`9293eb90...`, performs the real load → mutate → save (as a genuine `.SerumPreset`) →
readback → restore sequence and writes a full evidence record (atlas_id, final-contract source path
and fields used, CapabilityContract authority fields used, generated preset path + SHA256, MCP
result, raw readback, restoration result).

**Honest result of running it in this session:** this cloud/CI container has no DawDreamer
installation and no `Serum2.vst3` binary (verified again: `import dawdreamer` fails; no `*.vst3` file
exists on the filesystem; `LiveBackend()` requires the hardcoded Windows path
`C:\Program Files\Common Files\VST3\Serum2.vst3\...`). Running the script here reaches the real,
unweakened `installed_epoch()` check and raises `FileNotFoundError` there — before any Serum call,
MCP call, or preset write happens — and the script caught this and wrote an honest
`NOT_RUN_NO_LIVE_SERUM_IN_THIS_ENVIRONMENT` record (including the real admitted plan) to
`parameter_characterization/bulk_causal_evidence/env1_attack_live_proof_v1.json` rather than
fabricating a live result.

What I *was* able to verify in this container, using the exact same generic pieces the script calls,
without touching real Serum or weakening the epoch check: `apply_spec`/`with_field` correctly derive
the edited body (`kParamAttack` moves from the baseline `0.0005` to the final contract's
`5.000000000000001`), and `pack_file`/`unpack_file` round-trip that body through a real
`.SerumPreset` container byte-for-byte. **No claim is made that pytest, or this script in this
session, performed the actual MCP mutation or loaded it into a real Serum instance.** The script is
ready for the orchestrating agent layer to run on a Serum-attached machine (Step 2 of the review); that run is outside this session's environment and is not claimed to have happened here.

## Final committed contract — regression check

Rebuilding `final_execution_contract_v1.json` from `build_final_execution_contract_v1.py` after
these changes produces a **byte-identical** file (`git status` shows no diff) with:

- 330 total, 310 conforming/executable, 20 conformance exceptions
- 183 `MCP_EXEC_HOST_CONFIRMED`, 127 `MCP_EXEC_RAW_ONLY`
- 0 `MCP_EXEC_FAILED`, 0 `MCP_EXEC_NOOP_SUSPECT`
- 330/330 restoration verified
- v3 == v2

`test_final_execution_contract_v1.py` + `test_mcp_execution_harness.py`: 23 tests, all passing.

## Commit

See the commit this file was committed with, on `claude/final-mcp-execution-contract-2mew5v`, on top
of `54bee02` (which is itself on top of `e907aac`).
