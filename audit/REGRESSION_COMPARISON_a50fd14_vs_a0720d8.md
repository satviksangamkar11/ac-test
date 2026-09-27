# Regression Comparison: a50fd14 → a0720d8

**Date:** 2026-09-27  
**Branch:** `claude/gallant-cerf-u953wn`  
**Baseline commit:** `a50fd14` — "Add universal one-command end-to-end pipeline runner"  
**Current commit:** `a0720d8` — "One-command runner: remove tutorial-specific references, add AWAITING_NATIVE_ENVIRONMENT boundary"

---

## Method

Both suites run in isolated directories under the same ignore list:

```bash
python -m pytest --tb=no -p no:warnings -q \
  --ignore=serum2/producer/test_slider_calibration_pipeline.py \
  --ignore=serum2/producer/test_slider_evidence_extractor_v3.py \
  --ignore=serum2/producer/test_verified_state_adapter_v3_integration.py \
  --ignore=serum2/producer/test_detector_v2.py \
  --ignore=serum2/producer/test_detector_v3.py \
  --ignore=serum2/producer/test_e2e_reference_pipeline_heegn1xl5o4.py \
  2>&1 | grep -E '^(FAILED|ERROR)'
```

`a50fd14` ran in a `git worktree` at that commit.  
`a0720d8` ran in the live working tree at HEAD.  
Both output files were compared with `diff` — result: **IDENTICAL**.

---

## Summary counts

| Metric | a50fd14 (baseline) | a0720d8 (current) | Delta |
|---|---|---|---|
| passed | 1525 | 1534 | **+9** |
| failed | 27 | 27 | 0 |
| errors | 16 | 16 | 0 |
| skipped | 20 | 20 | 0 |

The +9 new passing tests are the tests added in a0720d8 for `_NativeVLMUnavailable`, `_is_native_environment()`, `_run_observation_census()`, `halted_for` key, W2-path exclusion, generic filenames, and fast-path docstring.

---

## FAILED node IDs (identical in both commits)

```
FAILED tests/test_compiler_serum_mcp_e2e.py::TestCompilerSerumMcpE2E::test_compiler_to_serum_mcp_end_to_end
FAILED tests/test_reference_boundaries.py::test_fx_and_field_bindings_are_mandatory_and_must_match
FAILED tests/test_reference_boundaries.py::test_frozen_nine_operation_live_ui_regression
FAILED tests/test_reference_episode.py::test_proof_level_and_coverage_are_separate_axes
FAILED tests/test_reference_episode.py::test_only_a_live_ui_verified_run_becomes_an_episode
FAILED tests/test_reference_episode.py::test_a_wrong_or_missing_ui_readback_is_not_verified
FAILED tests/test_reference_episode.py::test_operation_level_learning_never_becomes_whole_reference_learning
FAILED tests/test_reference_episode.py::test_skills_only_from_strictly_verified_episodes
FAILED tests/test_state_ledger.py::test_legacy_contracts_cannot_authorize_a_2_0_23_run
FAILED tests/test_state_ledger.py::test_the_same_ops_are_admitted_under_2_0_21_only_by_2_0_21_contracts
FAILED tests/test_state_ledger.py::test_compiler_only_accepts_admitted_operations_and_never_drops
FAILED tests/test_state_ledger.py::test_file_readback_alone_is_never_live_verification
FAILED tests/test_state_ledger.py::test_reference_reproduction_run_end_to_end
FAILED serum2/producer/test_observe_frames_full_census.py::test_observe_frames_captures_controls_the_transcript_never_named
FAILED serum2/producer/test_stage_a_required_seam.py::test_transcript_first_visual_path_stops_at_stage_a_required_without_observation
FAILED serum2/producer/test_step1_complete_integration.py::TestStep1D_VerifiedStateBuilderEndToEnd::test_verified_state_builder_with_universal_extraction
FAILED serum2/producer/test_step1_complete_integration.py::TestStep1D_VerifiedStateBuilderEndToEnd::test_verified_state_builder_four_routes
FAILED serum2/producer/test_step1_complete_integration.py::TestStep1E_DomainRepresentationContract::test_verified_route_carries_domain_contract
FAILED serum2/producer/test_step1_complete_integration.py::TestStep1F_AntiBypassProtection::test_manual_amount_injection_detectable
FAILED serum2/producer/test_step1_complete_integration.py::TestStep1I_FullTestSuite::test_no_hardcoded_fixture_values_in_production
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_atlas_knob_is_promoted_as_numeric_only_because_the_contract_says_so
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_toggle_buttons_is_enum_when_the_evidence_says_enum
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_evidence_contradicting_the_atlas_domain_is_rejected_not_forced
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_unverified_or_missing_ui_semantics_never_promotes
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_numeric_contract_needs_verified_bounds_and_in_range_value
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_boolean_contract_requires_boolean_shaped_value
FAILED serum2/qualification/test_evidence_promotion_contract.py::test_legacy_evidence_without_a_parameter_contract_is_unchanged
```

---

## ERROR node IDs (identical in both commits)

```
ERROR serum2/producer/test_u7_osc2_qualification.py::test_route_can_execute_qualification_lifecycle[False]
ERROR serum2/producer/test_u7_osc2_qualification.py::test_route_can_execute_qualification_lifecycle[True]
ERROR serum2/producer/test_u7_osc2_qualification.py::test_only_the_targeted_oscillator_changes
ERROR serum2/producer/test_u7_osc2_qualification.py::test_backend_state_comes_from_the_file_not_the_object
ERROR serum2/producer/test_u7_osc2_qualification.py::test_backend_really_invokes_serum_mcp_tools
ERROR serum2/producer/test_u7_osc2_qualification.py::test_unavailable_serum_mcp_cannot_qualify
ERROR serum2/producer/test_u7_osc2_qualification.py::test_unresolvable_resolver_fails_structurally
ERROR serum2/producer/test_u7_osc2_qualification.py::test_vst3_route_is_refused_and_file_untouched
ERROR serum2/producer/test_u7_osc2_qualification.py::test_unbound_is_refused_and_file_untouched
ERROR serum2/producer/test_u7_osc2_qualification.py::test_mutation_reported_but_readback_unchanged_fails
ERROR serum2/producer/test_u7_osc2_qualification.py::test_reload_that_loses_the_mutation_fails_persistence
ERROR serum2/producer/test_u7_osc2_qualification.py::test_each_backend_stage_failure_is_a_structured_failure[load-START]
ERROR serum2/producer/test_u7_osc2_qualification.py::test_each_backend_stage_failure_is_a_structured_failure[read-LOAD]
ERROR serum2/producer/test_u7_osc2_qualification.py::test_each_backend_stage_failure_is_a_structured_failure[mutate-READ_BASELINE]
ERROR serum2/producer/test_u7_osc2_qualification.py::test_each_backend_stage_failure_is_a_structured_failure[persist-READ_AFTER_MUTATION]
ERROR serum2/producer/test_u7_osc2_qualification.py::test_each_backend_stage_failure_is_a_structured_failure[reload-PERSIST]
```

All 16 errors are in `test_u7_osc2_qualification.py` — they require a real serum-mcp bridge (Windows-only). They are unchanged from a50fd14.

---

## Diff result

```
$ diff baseline_a50fd14.txt current_a0720d8.txt
(no output — files are identical)
```

**Zero new FAILED or ERROR node IDs introduced by a0720d8.**

---

## New tests added in a0720d8 (all PASSED)

| Test | Class |
|---|---|
| `test_native_vlm_unavailable_class_exists` | TestNativeEvidenceNotFabricatable |
| `test_is_native_environment_callable` | TestNativeEvidenceNotFabricatable |
| `test_is_native_environment_returns_bool` | TestNativeEvidenceNotFabricatable |
| `test_run_observation_census_raises_on_no_easyocr` | TestNativeEvidenceNotFabricatable |
| `test_observation_awaiting_includes_awaiting_native_env` | TestNativeEvidenceNotFabricatable |
| `test_runner_has_no_w2_fixture_paths` | TestNativeEvidenceNotFabricatable |
| `test_runner_uses_generic_acquisition_filename` | TestCleanRunBehavior |
| `test_runner_uses_generic_render_filename` | TestCleanRunBehavior |
| `test_runner_docstring_mentions_fast_path_helpers` | TestCleanRunBehavior |
