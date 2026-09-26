# Runtime-Consumption Proof v1 — `env1.attack`

Wires the committed `final_execution_contract_v1.json` into the real producer runtime as an
execution-evidence index, without touching the existing authority chain. No new sweep, campaign,
or evidence discovery was performed.

## Files changed

| File | Change |
|---|---|
| `serum2/producer/contract_registry.py` | Added `execution_specs` index + `execution_spec(atlas_id)`, loaded from the committed `final_execution_contract_v1.json` at init. No new class, no parallel subsystem. |
| `serum2/producer/producer_brain.py` | Threaded the Atlas `canonical_id` (atlas_id) from `TargetResolver` through `_run_serum_preset_path` into `_build_serum_preset_plan`, which now also attaches `final_execution_contract` (evidence) to the returned plan and cross-checks it against the admitted `mutation_target_path`. `allowed_operation`/admission/authority code paths are untouched. |
| `serum2/producer/test_final_execution_contract_runtime.py` | New — proof layer A (deterministic pytest integration proof). |
| `serum2/qualification/bulk_causal/live_proof_env1_attack.py` | New — proof layer B (live agent-driven execution script; see below for what could run in this environment). |

No existing Step 6 file (`step_6_6/6_7/6_8`), `admission.py`, `ClaimEngine`, compiler validation, or
epoch module was modified. None of the 20 conformance exceptions were touched or reclassified.

## Control used

`env1.attack` — the one already-proven `MCP_EXEC_HOST_CONFIRMED` control named in the task. No new
control was characterized.

## Runtime call chain (as traced, and as exercised by the new test)

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
            -> authority.scope["mutation_target_path"], ["mutation_value_used"]   [AUTHORITY]
            -> ContractRegistry.execution_spec("env1.attack")              [EVIDENCE: final contract]
            -> plan["final_execution_contract"] = {...}                    [attached, non-authoritative]
```

## Exact final-contract source path

`parameter_characterization/bulk_causal_evidence/final_execution_contract_v1.json`
(`ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH`)

## Exact final-contract fields consumed

`rows[atlas_id].mcp_operation`, `.expected_raw`, `.declared_domain`, `.final_execution_classification`,
`.restoration_verified`, plus `producer_lookup[atlas_id].exception_policy`. No `allowed_operation`,
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
stay unchanged. This is only possible if the execution-evidence fields are read from the file the
registry is pointed at, not from a pickle store, an evidence directory, or a hand-authored table.

## Serum version / SHA

`2.0.23` / `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3` (unchanged; carried in the
committed final contract's rows and in `serum2/producer/execution_epoch.EPOCH_2_0_23`).

## Proof layer A — deterministic pytest integration proof

`serum2/producer/test_final_execution_contract_runtime.py`, 9 tests, all passing:

- source-path identity, `env1.attack` row is `MCP_EXEC_HOST_CONFIRMED` + restoration-verified
- `ContractRegistry.execution_spec("env1.attack")` matches the committed row exactly
- unknown atlas_id / `None` → no fallback, returns `None`
- real `ProducerBrain` admits `env1.attack` through the real chain
- authority fields (`mutation_target_path`, `mutation_value_used`) equal the `CapabilityContract`,
  not the final contract's own differently-shaped test value
- plan's `final_execution_contract` fields equal the committed row, `agrees_with_admitted_mutation_path=True`
- the sentinel-swap provenance proof described above
- no `allowed_operation`/`raw_body_path`/`valid_domain` exists anywhere in the new index

Focused pytest result: **9 passed** (this file), **55 passed** together with
`test_ordered_resolution.py` (no regressions in the existing ordered-resolution suite).

## Proof layer B — live agent-driven execution

`serum2/qualification/bulk_causal/live_proof_env1_attack.py` builds the admitted plan through the
same real `ProducerBrain` chain, then — using only the existing generic pieces
(`run_mcp_execution_harness.LiveBackend`, `serum_mcp.preset.mapping.apply_spec`,
`serum2.producer.execution_epoch`) — checks the installed Serum epoch and, if it matches
`2.0.23`/`9293eb90...`, performs the real load → mutate → save → readback → restore sequence and
writes a full evidence record (atlas_id, final-contract source path and fields used,
CapabilityContract authority fields used, generated preset path + SHA256, MCP result, raw readback,
restoration result).

**Honest result of running it in this session:** this cloud/CI container has no DawDreamer
installation and no `Serum2.vst3` binary (verified: `import dawdreamer` fails; no `*.vst3` file
exists on the filesystem; `LiveBackend()` requires the hardcoded Windows path
`C:\Program Files\Common Files\VST3\Serum2.vst3\...`). Running the script here raises
`FileNotFoundError` at the epoch-check step, exactly as it should — the existing epoch machinery was
not weakened or bypassed to make it "succeed." The script caught this and wrote an honest
`NOT_RUN_NO_LIVE_SERUM_IN_THIS_ENVIRONMENT` record (including the real admitted plan) to
`parameter_characterization/bulk_causal_evidence/env1_attack_live_proof_v1.json` rather than
fabricating a live result. **No claim is made that pytest, or this script in this session, performed
the actual MCP mutation.** The script is ready for the orchestrating agent layer to run on a
Serum-attached machine; that run is outside this session's environment.

## Final committed contract — regression check

Rebuilding `final_execution_contract_v1.json` from `build_final_execution_contract_v1.py` after
these changes produces a **byte-identical** file (`git status` shows no diff) with:

- 330 total, 310 conforming/executable, 20 conformance exceptions
- 183 `MCP_EXEC_HOST_CONFIRMED`, 127 `MCP_EXEC_RAW_ONLY`
- 0 `MCP_EXEC_FAILED`, 0 `MCP_EXEC_NOOP_SUSPECT`
- 330/330 restoration verified
- v3 == v2

`test_final_execution_contract_v1.py` (23 tests, incl. `test_mcp_execution_harness.py`): all passing.

## Commit

See the commit this file was committed with, on `claude/final-mcp-execution-contract-2mew5v`, on top
of `e907aac`.
