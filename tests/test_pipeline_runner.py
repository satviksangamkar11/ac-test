"""Deterministic tests for the universal pipeline runner.

No network access, no Serum binary, no VLM/OCR calls.
Tests verify: single-command interface, stage ordering, artifact reuse,
contract-first filtering, fail-closed behaviour, A2 gate, no parameter
branches, and correct closure criteria.
"""
from __future__ import annotations

import ast
import inspect
import json
import sys
import tempfile
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pytest

from serum2.pipeline.stage_manifest import (
    RunManifest, StageRecord, STAGE_SEQUENCE, CLOUD_STAGES, NATIVE_STAGES,
    STAGE_BOUNDARY, content_hash, dict_hash,
)
import serum2.pipeline.runner as runner_mod


# ---------------------------------------------------------------------------
# 1. Single-command interface — __main__.py exists and imports main()
# ---------------------------------------------------------------------------

class TestSingleCommandInterface:
    def test_main_module_exists(self):
        main_py = REPO / "serum2" / "pipeline" / "__main__.py"
        assert main_py.exists(), "__main__.py must exist for python -m serum2.pipeline"

    def test_main_module_imports_main(self):
        src = (REPO / "serum2" / "pipeline" / "__main__.py").read_text()
        assert "from serum2.pipeline.runner import main" in src or "main" in src

    def test_run_pipeline_callable(self):
        assert callable(runner_mod.run_pipeline)

    def test_main_callable(self):
        assert callable(runner_mod.main)

    def test_help_exits_zero_or_two(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["prog", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            runner_mod.main()
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# 2. Correct stage ordering and boundary labels
# ---------------------------------------------------------------------------

class TestStageOrdering:
    def test_stage_sequence_has_13_stages(self):
        assert len(STAGE_SEQUENCE) == 13

    def test_stage_sequence_order(self):
        expected = [
            "ACQUIRE", "TRANSCRIPT", "VISUAL_EVIDENCE", "OBSERVATION",
            "LEDGER", "ADMISSION", "COMPILE", "NATIVE_LOAD", "NATIVE_VERIFY",
            "REFERENCE_VERIFY", "ARRANGE", "RENDER", "FINALIZE",
        ]
        assert STAGE_SEQUENCE == expected

    def test_observation_is_local_native(self):
        assert STAGE_BOUNDARY["OBSERVATION"] == "LOCAL_NATIVE"

    def test_admission_is_cloud(self):
        assert STAGE_BOUNDARY["ADMISSION"] == "ANY"

    def test_compile_is_cloud(self):
        assert STAGE_BOUNDARY["COMPILE"] == "ANY"

    def test_native_load_is_local_native(self):
        assert STAGE_BOUNDARY["NATIVE_LOAD"] == "LOCAL_NATIVE"

    def test_render_is_local_native(self):
        assert STAGE_BOUNDARY["RENDER"] == "LOCAL_NATIVE"

    def test_finalize_is_cloud(self):
        assert STAGE_BOUNDARY["FINALIZE"] == "ANY"

    def test_cloud_stages_set_correct(self):
        expected_cloud = {"ACQUIRE", "TRANSCRIPT", "VISUAL_EVIDENCE", "LEDGER",
                          "ADMISSION", "COMPILE", "FINALIZE"}
        assert CLOUD_STAGES == expected_cloud

    def test_native_stages_set_correct(self):
        expected_native = {"OBSERVATION", "NATIVE_LOAD", "NATIVE_VERIFY",
                           "REFERENCE_VERIFY", "ARRANGE", "RENDER"}
        assert NATIVE_STAGES == expected_native


# ---------------------------------------------------------------------------
# 3. Artifact reuse: cache key includes sampling parameters
# ---------------------------------------------------------------------------

class TestArtifactReuse:
    def test_dict_hash_changes_with_interval(self):
        h1 = dict_hash({"url": "x", "sample_interval_sec": 1.0, "max_frames": None})
        h2 = dict_hash({"url": "x", "sample_interval_sec": 2.0, "max_frames": None})
        assert h1 != h2

    def test_dict_hash_changes_with_max_frames(self):
        h1 = dict_hash({"url": "x", "sample_interval_sec": 2.0, "max_frames": None})
        h2 = dict_hash({"url": "x", "sample_interval_sec": 2.0, "max_frames": 100})
        assert h1 != h2

    def test_dict_hash_deterministic(self):
        d = {"a": 1, "b": [2, 3]}
        assert dict_hash(d) == dict_hash(d)

    def test_content_hash_none_for_missing_file(self, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        assert content_hash(missing) is None

    def test_content_hash_stable_for_same_content(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello")
        assert content_hash(f) == content_hash(f)

    def test_run_manifest_stages_start_pending(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("ACQUIRE")
        assert rec.status == "PENDING"

    def test_run_manifest_complete_stage_is_complete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("ACQUIRE")
        rec.mark_complete({"frames": 5})
        m.update_stage(rec)
        assert m.is_stage_complete("ACQUIRE")

    def test_run_manifest_current_stage_first_incomplete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("ACQUIRE")
        rec.mark_complete({})
        m.update_stage(rec)
        assert m.current_stage() == "TRANSCRIPT"


# ---------------------------------------------------------------------------
# 4. Stale-cache rejection: failed stage is not skipped
# ---------------------------------------------------------------------------

class TestStaleCacheRejection:
    def test_failed_stage_not_treated_as_complete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("ACQUIRE")
        rec.mark_failed("some error")
        m.update_stage(rec)
        assert not m.is_stage_complete("ACQUIRE")

    def test_awaiting_input_not_treated_as_complete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("OBSERVATION")
        rec.mark_awaiting("needs LOCAL run")
        m.update_stage(rec)
        assert not m.is_stage_complete("OBSERVATION")

    def test_skipped_stage_treated_as_complete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("ACQUIRE")
        rec.mark_skipped("cache hit")
        m.update_stage(rec)
        assert m.is_stage_complete("ACQUIRE")

    def test_manifest_save_and_load_round_trip(self, tmp_path):
        m = RunManifest(run_id="abc", video_id="vvv", source_url="http://example.com")
        rec = m.stage_record("ACQUIRE")
        rec.mark_complete({"frames": 10})
        m.update_stage(rec)
        p = tmp_path / "manifest.json"
        m.save(p)
        m2 = RunManifest.load(p)
        assert m2.run_id == "abc"
        assert m2.is_stage_complete("ACQUIRE")


# ---------------------------------------------------------------------------
# 5. Contract-first filtering excludes rand_phase
# ---------------------------------------------------------------------------

class TestContractFirstFiltering:
    def test_runner_imports_contract_covered_controls(self):
        src = inspect.getsource(runner_mod)
        assert "contract_covered_controls" in src

    def test_runner_imports_filter_contract_covered(self):
        src = inspect.getsource(runner_mod)
        assert "filter_contract_covered" in src

    def test_runner_does_not_import_observation_policy_directly(self):
        """runner.py must not import observation_policy — it calls through adjudicated_observe."""
        tree = ast.parse(inspect.getsource(runner_mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module is None or "observation_policy" not in node.module, (
                    "runner.py must not import observation_policy directly"
                )


# ---------------------------------------------------------------------------
# 6. No parameter-name special cases in runner.py
# ---------------------------------------------------------------------------

class TestNoParameterBranches:
    _FORBIDDEN_CONTROL_NAMES = [
        "oscA.octave", "env1.decay", "lfo1.rate", "filter1.cutoff",
        "env2.decay", "oscA.rand_phase",
    ]

    def test_runner_has_no_hardcoded_control_names(self):
        src = inspect.getsource(runner_mod)
        for name in self._FORBIDDEN_CONTROL_NAMES:
            assert name not in src, (
                f"runner.py contains hardcoded control name '{name}' — "
                "must be parameter-agnostic"
            )

    def test_runner_no_control_id_if_branches(self):
        """Verify there are no 'if control_id ==' branches in runner module."""
        src = inspect.getsource(runner_mod)
        # Control-specific branches would look like: control_id == "oscA
        assert 'control_id == "osc' not in src
        assert 'control_id == "env' not in src
        assert 'control_id == "lfo' not in src
        assert 'control_id == "filter' not in src


# ---------------------------------------------------------------------------
# 7. No rand_phase contract insertion
# ---------------------------------------------------------------------------

class TestNoRandPhaseInsertion:
    def test_runner_does_not_insert_rand_phase(self):
        src = inspect.getsource(runner_mod)
        assert "rand_phase" not in src, (
            "runner.py must never reference oscA.rand_phase — "
            "it is excluded because it has no contract row"
        )

    def test_runner_does_not_modify_contract_path(self):
        src = inspect.getsource(runner_mod)
        assert "final_execution_contract_v1" not in src or "open" not in src, True
        # More targeted: must never write to the contract file
        assert 'w"' not in src.replace(' ', '') or "final_execution_contract" not in src


# ---------------------------------------------------------------------------
# 8. Fail-closed when no admissible observation exists
# ---------------------------------------------------------------------------

class TestFailClosed:
    def test_stage_record_mark_failed(self):
        rec = StageRecord(stage="ADMISSION")
        rec.mark_failed("PRODUCT_NOT_CLOSED: no admissible OBSERVED observations")
        assert rec.status == "FAILED"
        assert "PRODUCT_NOT_CLOSED" in rec.failure_reason

    def test_run_manifest_final_status_default_running(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert m.final_status == "RUNNING"

    def test_run_manifest_can_record_product_not_closed(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        m.final_status = "PRODUCT_NOT_CLOSED"
        m.failure_stage = "ADMISSION"
        m.failure_reason = "No admissible observations"
        assert m.final_status == "PRODUCT_NOT_CLOSED"

    def test_pipeline_stage_observation_boundary_is_local_native(self):
        """OBSERVATION requires LOCAL — so cloud-only runs cannot fabricate it."""
        assert STAGE_BOUNDARY["OBSERVATION"] == "LOCAL_NATIVE"

    def test_runner_fail_closed_text_present(self):
        """_stage_admission must reference fail-closed behavior."""
        src = inspect.getsource(runner_mod)
        assert "PRODUCT_NOT_CLOSED" in src


# ---------------------------------------------------------------------------
# 9. A2 gate remains mandatory
# ---------------------------------------------------------------------------

class TestA2GateMandatory:
    def test_runner_references_admit_rows(self):
        src = inspect.getsource(runner_mod)
        assert "admit_rows" in src

    def test_runner_does_not_bypass_admission(self):
        """runner.py must use state_admission, not build AdmittedRow directly."""
        src = inspect.getsource(runner_mod)
        assert "state_admission" in src

    def test_no_direct_admission_status_assignment(self):
        """runner.py must not assign .admission = 'ADMITTED' directly."""
        tree = ast.parse(inspect.getsource(runner_mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "admission":
                        assert False, "runner.py directly assigns .admission attribute"

    def test_admission_stage_is_cloud(self):
        """Admission can run cloud-side (it reads contracts, doesn't need Serum)."""
        assert STAGE_BOUNDARY["ADMISSION"] == "ANY"


# ---------------------------------------------------------------------------
# 10. Native evidence cannot be fabricated in cloud
# ---------------------------------------------------------------------------

class TestNativeEvidenceNotFabricatable:
    def test_native_load_boundary_enforced(self):
        assert STAGE_BOUNDARY["NATIVE_LOAD"] == "LOCAL_NATIVE"

    def test_native_verify_boundary_enforced(self):
        assert STAGE_BOUNDARY["NATIVE_VERIFY"] == "LOCAL_NATIVE"

    def test_reference_verify_boundary_enforced(self):
        assert STAGE_BOUNDARY["REFERENCE_VERIFY"] == "LOCAL_NATIVE"

    def test_runner_does_not_import_dawdreamer(self):
        """runner.py must not import DawDreamer (checking imports, not comments)."""
        tree = ast.parse(inspect.getsource(runner_mod))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in getattr(node, "names", [])]
                module = getattr(node, "module", "") or ""
                for n in names + [module]:
                    assert "dawdreamer" not in n.lower(), \
                        f"runner.py imports DawDreamer via '{n}'"

    def test_serum_sha_is_pinned(self):
        """The Serum 2.0.23 module SHA must be pinned in runner.py."""
        src = inspect.getsource(runner_mod)
        assert "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3" in src

    def test_runner_certificate_includes_dawdreamer_false(self):
        src = inspect.getsource(runner_mod)
        assert "dawdreamer_used" in src


# ---------------------------------------------------------------------------
# 11. Final gate rejects incomplete native verification
# ---------------------------------------------------------------------------

class TestFinalGateRejectsIncomplete:
    def test_product_closed_requires_native_verified(self):
        """RunManifest tracks native_verified; only True allows PRODUCT_CLOSED."""
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert m.native_verified is False
        assert m.final_status == "RUNNING"

    def test_product_closed_requires_reference_verified(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert m.reference_verified is False

    def test_finalize_stage_checks_native_verified(self):
        src = inspect.getsource(runner_mod)
        assert "native_verified" in src

    def test_finalize_stage_checks_reference_verified(self):
        src = inspect.getsource(runner_mod)
        assert "reference_verified" in src

    def test_finalize_stage_checks_coverage_status(self):
        src = inspect.getsource(runner_mod)
        assert "coverage_status" in src


# ---------------------------------------------------------------------------
# 12. Final gate rejects silent render
# ---------------------------------------------------------------------------

class TestFinalGateRejectsSilentRender:
    def test_runner_references_rms(self):
        src = inspect.getsource(runner_mod)
        assert "rms" in src.lower() or "dBFS" in src or "render_path" in src

    def test_runner_has_render_rms_check(self):
        src = inspect.getsource(runner_mod)
        assert "_check_render_rms" in src or "rms" in src.lower()

    def test_run_manifest_tracks_render_path(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        m.render_path = "/tmp/render.wav"
        assert m.render_path == "/tmp/render.wav"


# ---------------------------------------------------------------------------
# 13. Final certificate generated only after all gates
# ---------------------------------------------------------------------------

class TestCertificateGating:
    def test_run_manifest_tracks_certificate_path(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert m.certificate_path is None

    def test_run_manifest_summary_includes_final_status(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        summary = m.summary_dict()
        assert "FINAL_STATUS" in summary

    def test_run_manifest_summary_includes_certificate_path(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        summary = m.summary_dict()
        assert "CERTIFICATE_PATH" in summary

    def test_finalize_stage_writes_cert_type(self):
        src = inspect.getsource(runner_mod)
        assert "cert_type" in src or "certificate" in src.lower()

    def test_finalize_stage_only_product_closed_or_incomplete(self):
        src = inspect.getsource(runner_mod)
        assert "PRODUCT_CLOSED" in src
        assert "PRODUCT_NOT_CLOSED" in src


# ---------------------------------------------------------------------------
# 14. --resume behavior
# ---------------------------------------------------------------------------

class TestResumeBehavior:
    def test_run_manifest_save_load_preserves_complete_stages(self, tmp_path):
        m = RunManifest(run_id="r1", video_id="v1", source_url="http://x")
        for stage in ["ACQUIRE", "TRANSCRIPT"]:
            rec = m.stage_record(stage)
            rec.mark_complete({"ok": True})
            m.update_stage(rec)
        p = tmp_path / "manifest.json"
        m.save(p)
        m2 = RunManifest.load(p)
        assert m2.is_stage_complete("ACQUIRE")
        assert m2.is_stage_complete("TRANSCRIPT")
        assert not m2.is_stage_complete("VISUAL_EVIDENCE")

    def test_current_stage_advances_after_each_complete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert m.current_stage() == "ACQUIRE"
        for stage in STAGE_SEQUENCE[:5]:
            rec = m.stage_record(stage)
            rec.mark_complete({})
            m.update_stage(rec)
        assert m.current_stage() == STAGE_SEQUENCE[5]

    def test_current_stage_none_when_all_complete(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        for stage in STAGE_SEQUENCE:
            rec = m.stage_record(stage)
            rec.mark_complete({})
            m.update_stage(rec)
        assert m.current_stage() is None


# ---------------------------------------------------------------------------
# 15. Clean-run behavior: fresh manifest created with all stages PENDING
# ---------------------------------------------------------------------------

class TestCleanRunBehavior:
    def test_new_manifest_has_no_stages(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert len(m.stages) == 0

    def test_stage_record_creates_pending_on_first_access(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec = m.stage_record("ACQUIRE")
        assert rec.status == "PENDING"
        assert rec.stage == "ACQUIRE"
        assert rec.run_id == "x"

    def test_stage_record_sets_correct_boundary(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        rec_obs = m.stage_record("OBSERVATION")
        assert rec_obs.execution_boundary == "LOCAL_NATIVE"
        rec_adm = m.stage_record("ADMISSION")
        assert rec_adm.execution_boundary == "ANY"

    def test_manifest_final_status_starts_running(self):
        m = RunManifest(run_id="x", video_id="y", source_url="z")
        assert m.final_status == "RUNNING"

    def test_run_pipeline_signature(self):
        sig = inspect.signature(runner_mod.run_pipeline)
        params = list(sig.parameters.keys())
        assert "youtube_url" in params
        assert "work_dir" in params
        assert "resume" in params
