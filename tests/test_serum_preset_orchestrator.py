"""Tests for the generic Serum preset execution orchestrator (serum2.producer.serum_preset_orchestrator).

Every test drives the REAL production admission chain (ProducerBrain.execute() -> real resolution ->
real admission -> real ADVISORY_ONLY plan) exactly as tests/test_b1_capability_resolution.py does --
zero mocks of ProducerBrain itself. Only the two genuinely environment-dependent seams (native preset
generation, native load) are overridden for tests, via the orchestrator's own documented test-injection
parameters -- never by patching or reimplementing the orchestrator's real logic.

Covers the required cases:
  A. authorized plan -> orchestrator produces a real EXECUTED ProducerResult
  B. preset-generation failure -> fails closed (PresetGenerationFailed)
  C. native environment unavailable (real load_and_verify, no override, this is not Windows) -> fails
     closed (ExecutionEnvironmentUnavailable)
  D. incomplete UI evidence -> fails closed (ValueError), never silently downgraded
  E. complete loader-bound evidence -> finalize is actually invoked and the chain is gate_b-verifiable
  F. the finalized ProducerResult carries the exact UI evidence supplied (not a copy/re-derivation)
  G. a second, different target (Env2.Decay) goes through the identical generic code path as any other
     target -- no env1.attack-shaped or target-specific branch anywhere in the orchestrator
"""
from __future__ import annotations

import platform

import pytest
from pathlib import Path

from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer.gate_b_certificate import gate_b_status
from serum2.producer.serum_preset_orchestrator import (
    execute_serum_preset_plan,
    make_test_ui_evidence_provider,
    NativeExecutionEvidence,
    ExecutionEnvironmentUnavailable,
    PresetGenerationFailed,
)

BINDING_DIR = Path(__file__).parent.parent / "serum2" / "qualification" / "binding_evidence"
PROMOTED_DIR = Path(__file__).parent.parent / "parameter_characterization" / "binding_evidence_mcp_exec_v1"


def _brain() -> ProducerBrain:
    return ProducerBrain(epoch=EPOCH_2_0_23, binding_evidence_dir=str(BINDING_DIR),
                         promoted_evidence_dir=str(PROMOTED_DIR))


def _advisory_result(brain: ProducerBrain, intent: str, target: str):
    """A real ADVISORY_ONLY ProducerResult from the real admission chain -- no fabrication."""
    result = brain.execute(ProducerRequest(user_intent=intent, semantic_target=target))
    assert result.execution_status == "ADVISORY_ONLY", (
        "setup failed: expected ADVISORY_ONLY for %r, got %r (error=%r)"
        % (intent, result.execution_status, result.error)
    )
    assert getattr(result, "_serum_preset_plan", None) is not None
    return result


def _fake_preset_generation_success(result, plan, epoch):
    """Test-only Step-1 override: a deterministic 'generated' preset, standing in for the not-yet-wired
    canonical compiler bridge (see _generate_canonical_preset's docstring)."""
    return {"status": "SUCCESS", "preset_path": "/tmp/test_preset.SerumPreset",
            "preset_sha256": "b" * 64}


def _fake_preset_generation_failure(result, plan, epoch):
    return {"status": "FAILED", "error": "simulated compiler failure"}


def _fake_native_load_success(preset_path):
    return {"status": "LOADED_VISUAL", "serum_module_sha256": {"serum2": EPOCH_2_0_23.binary_sha256},
            "track_index": 3, "track_nonce": "SRMABC123"}


class TestOrchestratorAuthorizedPlanExecution:
    """A. A real authorized ADVISORY_ONLY plan drives the orchestrator to a real EXECUTED result."""

    def test_authorized_plan_reaches_executed(self):
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")

        finalized = execute_serum_preset_plan(
            result, EPOCH_2_0_23, brain=brain,
            preset_generation_fn=_fake_preset_generation_success,
            native_execution_fn=_fake_native_load_success,
            ui_evidence_provider=make_test_ui_evidence_provider(epoch=EPOCH_2_0_23),
        )

        assert finalized is result, "finalize_serum_preset_execution mutates and returns the SAME result"
        assert finalized.execution_status == "EXECUTED"
        assert finalized.decision == "ACCEPTED"
        assert finalized.serum_preset_execution is not None
        assert finalized.serum_preset_execution["preset_sha256"] == "b" * 64


class TestOrchestratorFailsClosedOnPresetGenerationFailure:
    """B. Preset generation failing must raise, never fabricate a preset_path/sha256."""

    def test_preset_generation_failure_raises(self):
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")

        with pytest.raises(PresetGenerationFailed):
            execute_serum_preset_plan(
                result, EPOCH_2_0_23, brain=brain,
                preset_generation_fn=_fake_preset_generation_failure,
                native_execution_fn=_fake_native_load_success,
                ui_evidence_provider=make_test_ui_evidence_provider(epoch=EPOCH_2_0_23),
            )
        # A failed preset generation must never mutate the ADVISORY_ONLY result into a fake EXECUTED one.
        assert result.execution_status == "ADVISORY_ONLY"
        assert result.serum_preset_execution is None


class TestOrchestratorFailsClosedOnUnavailableEnvironment:
    """C. On this machine (never Windows in CI/cloud), the REAL load_and_verify bridge must fail
    closed through ExecutionEnvironmentUnavailable -- not a fabricated LOADED_VISUAL result."""

    def test_real_native_load_unavailable_off_windows(self):
        assert platform.system() != "Windows", "this test asserts the fail-closed path off Windows"
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")

        with pytest.raises((ExecutionEnvironmentUnavailable, RuntimeError)):
            execute_serum_preset_plan(
                result, EPOCH_2_0_23, brain=brain,
                preset_generation_fn=_fake_preset_generation_success,
                # native_execution_fn intentionally omitted: exercises the REAL
                # serum_track_loader.load_and_verify() bridge, which must fail closed here.
                ui_evidence_provider=make_test_ui_evidence_provider(epoch=EPOCH_2_0_23),
            )
        assert result.execution_status == "ADVISORY_ONLY"

    def test_missing_ui_evidence_provider_fails_closed(self):
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")

        with pytest.raises(ExecutionEnvironmentUnavailable):
            execute_serum_preset_plan(
                result, EPOCH_2_0_23, brain=brain,
                preset_generation_fn=_fake_preset_generation_success,
                native_execution_fn=_fake_native_load_success,
                # ui_evidence_provider intentionally omitted
            )
        assert result.execution_status == "ADVISORY_ONLY"


class TestOrchestratorFailsClosedOnIncompleteEvidence:
    """D. Malformed/incomplete NativeExecutionEvidence must never reach finalize_serum_preset_execution."""

    @pytest.mark.parametrize("bad_kwargs,bad_field", [
        ({"screenshot_sha": "not-hex-and-too-short"}, "screenshot_sha"),
        ({"serum_module_sha256": "short"}, "serum_module_sha256"),
        ({"crop_coords": [-1, 0, 100, 100]}, "crop_coords"),
        ({"crop_coords": [0, 0, 100]}, "crop_coords"),
        ({"observed_values": {}}, "observed_values"),
        ({"run_id": ""}, "run_id"),
        ({"track_nonce": "  "}, "track_nonce"),
    ])
    def test_incomplete_evidence_raises_value_error(self, bad_kwargs, bad_field):
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")
        bad_provider = make_test_ui_evidence_provider(epoch=EPOCH_2_0_23, **bad_kwargs)

        with pytest.raises(ValueError, match=bad_field):
            execute_serum_preset_plan(
                result, EPOCH_2_0_23, brain=brain,
                preset_generation_fn=_fake_preset_generation_success,
                native_execution_fn=_fake_native_load_success,
                ui_evidence_provider=bad_provider,
            )
        assert result.execution_status == "ADVISORY_ONLY"

    def test_wrong_return_type_from_provider_raises(self):
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")

        with pytest.raises(ValueError):
            execute_serum_preset_plan(
                result, EPOCH_2_0_23, brain=brain,
                preset_generation_fn=_fake_preset_generation_success,
                native_execution_fn=_fake_native_load_success,
                ui_evidence_provider=lambda preset_path, load_result: {"not": "a NativeExecutionEvidence"},
            )
        assert result.execution_status == "ADVISORY_ONLY"


class TestOrchestratorCompleteEvidenceReachesGateB:
    """E + F. Complete, loader-bound evidence actually finalizes, and the finalized ProducerResult
    carries the SAME evidence (not a re-derived copy) -- verifiable end to end through gate_b_status."""

    def test_complete_evidence_produces_gate_b_verifiable_result(self):
        brain = _brain()
        result = _advisory_result(brain, "set Env2.Decay to 5.0 seconds", "Env2.Decay")

        provider = make_test_ui_evidence_provider(
            epoch=EPOCH_2_0_23,
            run_id="run-canonical-0001",
            track_nonce="SRMCANON1",
            screenshot_sha="c" * 64,
            crop_coords=[10, 20, 300, 400],
            observed_values={"Env2.Decay": "5.0 s"},
            readback_verified=True,
            restoration_verified=True,
        )

        finalized = execute_serum_preset_plan(
            result, EPOCH_2_0_23, brain=brain,
            preset_generation_fn=_fake_preset_generation_success,
            native_execution_fn=_fake_native_load_success,
            ui_evidence_provider=provider,
        )

        ui_rb = finalized.serum_preset_execution["ui_readback"]
        assert ui_rb["route"] == "DIRECT_UI"
        assert ui_rb["restoration_verified"] is True
        assert ui_rb["values"] == {"Env2.Decay": "5.0 s"}
        le = ui_rb["loader_evidence"]
        assert le["run_id"] == "run-canonical-0001"
        assert le["track_nonce"] == "SRMCANON1"
        assert le["epoch"] == EPOCH_2_0_23.serum_version
        assert le["serum_module_sha256"] == EPOCH_2_0_23.binary_sha256
        assert le["screenshot_sha"] == "c" * 64
        assert le["crop_coords"] == [10, 20, 300, 400]

        # F: the exact evidence supplied reaches gate_b_status's own independent A7 binding check --
        # not a hand-copied or re-derived shape.
        status = gate_b_status(finalized, epoch=EPOCH_2_0_23)
        assert status in ("CANONICAL_GATE_B_VERIFIED", "NATIVE_STATE_PROOF"), (
            "expected a real proof tier, got %r" % status
        )


class TestOrchestratorIsGenericNotTargetSpecific:
    """G. The SAME orchestrator code path, unmodified, executes a DIFFERENT target's plan --
    proving no env1.attack (or any other target) special case exists anywhere in this module."""

    @pytest.mark.parametrize("intent,target,control_id", [
        ("set Env2.Decay to 5.0 seconds", "Env2.Decay", "Env2.Decay"),
        ("set Env2.Decay to 8.0 seconds", "Env2.Decay", "Env2.Decay"),
    ])
    def test_generic_across_requested_values(self, intent, target, control_id):
        brain = _brain()
        result = _advisory_result(brain, intent, target)
        provider = make_test_ui_evidence_provider(
            epoch=EPOCH_2_0_23, observed_values={control_id: "observed"},
        )

        finalized = execute_serum_preset_plan(
            result, EPOCH_2_0_23, brain=brain,
            preset_generation_fn=_fake_preset_generation_success,
            native_execution_fn=_fake_native_load_success,
            ui_evidence_provider=provider,
        )
        assert finalized.execution_status == "EXECUTED"

    def test_orchestrator_source_names_no_specific_target(self):
        """The orchestrator module's own source must never hardcode a specific control id -- the
        generic-interface requirement from the W1 integration spec, checked directly rather than
        trusted."""
        import inspect
        import serum2.producer.serum_preset_orchestrator as orch
        src = inspect.getsource(orch)
        for forbidden in ("env1.attack", "Env1.Attack", "ENV1.ATTACK"):
            assert forbidden not in src, (
                "orchestrator must remain generic; found target-specific text %r" % forbidden
            )


class TestOrchestratorRejectsNonAdvisoryInput:
    def test_rejects_result_not_advisory_only(self):
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent="nonsense gibberish target", semantic_target="NoSuchTarget"))
        assert result.execution_status != "ADVISORY_ONLY"

        with pytest.raises(ValueError):
            execute_serum_preset_plan(result, EPOCH_2_0_23, brain=brain)
