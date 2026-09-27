"""Generic Serum preset execution orchestrator.

Bridges ProducerBrain's ADVISORY_ONLY plan to real native execution and evidence collection,
WITHOUT putting any Windows/Ableton/Serum-GUI logic inside ProducerBrain itself. ProducerBrain
stays a pure planner: resolution -> admission -> AuthorizedOperation -> ADVISORY_ONLY plan. This
module is the environment-dependent stage that comes after it:

    ADVISORY_ONLY plan
          |
          v
    execute_serum_preset_plan()
          |
          +-- 1. generate the canonical .SerumPreset            (cloud-capable; calls the existing
          |                                                       compile_ops() via a reconstructed Row --
          |                                                       see _generate_canonical_preset's docstring)
          +-- 2. serum_track_loader.load_and_verify()            (Windows/Ableton only; fails closed
          |                                                       with ExecutionEnvironmentUnavailable
          |                                                       everywhere else)
          +-- 3. ui_evidence_provider(...)                       (the injected adapter that supplies
          |                                                       REAL screenshot/observed-value/
          |                                                       restoration evidence -- never
          |                                                       fabricated here)
          +-- 4. brain.finalize_serum_preset_execution(...)      (the SAME ProducerBrain instance that
                                                                   produced the plan; never a second,
                                                                   parallel finalize path)

Generic across every Serum control: nothing here names any one specific target (e.g. an envelope's
attack time, or any other single control). The plan's own mutation_target_path/contract_id/
capability_key drive everything.

Fails closed (raises, never returns a fabricated result) when:
  - the input result is not ADVISORY_ONLY
  - canonical preset generation does not succeed
  - the native environment (Windows + Ableton + AbletonMCP + Serum 2.0.23) is unavailable
  - the native load itself fails
  - no ui_evidence_provider is supplied
  - the supplied evidence is incomplete or malformed (missing/wrong-shaped fields A7's own
    _binding_quality would reject)

Never manufactures proof: every field placed into loader_evidence/ui_readback comes verbatim from
a NativeExecutionEvidence the caller's own adapter constructed from a REAL native execution. Test
callers use make_test_ui_evidence_provider() (deterministic fixtures, clearly test-only); production
callers wire an adapter that actually drives the Windows/Ableton/Serum GUI and reads it back.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from serum2.producer.execution_epoch import ExecutionEpoch, require_epoch
from serum2.producer.producer_brain import ProducerBrain, ProducerResult, get_brain


@dataclass(frozen=True)
class NativeExecutionEvidence:
    """Real evidence captured from one native Serum execution (Windows/Ableton).

    Every field must come from an actual observation of the actual running Serum instance this
    run loaded -- never a guessed, copied, or planned value. `readback_verified` and
    `restoration_verified` are DISTINCT claims and must each be asserted independently by whoever
    did the real comparison (this module never infers either from the raw values):

      readback_verified:     the values actually observed in the live Serum UI match what this run's
                              admitted operation intended to set (the correctness check).
      restoration_verified:  after the observation, the original/pre-mutation state was restored and
                              that restoration was itself verified (the round-trip-safety check;
                              REQUIRED by gate_b_status() for CANONICAL_GATE_B_VERIFIED).
    """
    run_id: str
    track_nonce: str
    epoch: ExecutionEpoch
    serum_module_sha256: str          # 64 lowercase-or-uppercase hex chars
    screenshot_sha: str               # 64 hex chars, sha256 of the actual screenshot
    crop_coords: List[float]          # [x, y, w, h], all finite and >= 0
    observed_values: Dict[str, str]   # {control_id: observed_text_value} -- non-empty
    readback_verified: bool
    restoration_verified: bool


class ExecutionEnvironmentUnavailable(RuntimeError):
    """Native execution cannot proceed on this machine, or no evidence adapter was supplied.
    Carries the exact remedy; never a reason to fabricate a result."""


class PresetGenerationFailed(RuntimeError):
    """Canonical preset generation did not succeed. Never a silent fallback to a partial preset."""


def execute_serum_preset_plan(
    result: ProducerResult,
    epoch: ExecutionEpoch,
    *,
    brain: Optional[ProducerBrain] = None,
    preset_generation_fn: Optional[Callable[[ProducerResult, Dict[str, Any], ExecutionEpoch], Dict[str, Any]]] = None,
    native_execution_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
    ui_evidence_provider: Optional[Callable[[str, Dict[str, Any]], NativeExecutionEvidence]] = None,
) -> ProducerResult:
    """Execute an ADVISORY_ONLY Serum preset plan end to end and return the finalized ProducerResult.

    Args:
        result: a ProducerResult with execution_status == "ADVISORY_ONLY", produced by
                execute_producer_request(request, epoch) via the Serum preset route (carries
                result._serum_preset_plan from ProducerBrain._build_serum_preset_plan()).
        epoch: the ExecutionEpoch this run executes on (must match the brain that produced `result`).
        brain: the exact ProducerBrain instance that produced `result` (so finalize_serum_preset_execution
               runs on the SAME brain, never a second one). Defaults to get_brain(epoch) -- the identical
               cache lookup execute_producer_request() itself uses, so a plain
               execute_producer_request(request, epoch) caller never has to pass this explicitly.
        preset_generation_fn: test-only override for Step 1 (preset generation). Production callers
                must leave this None; see _generate_canonical_preset's docstring for current status.
        native_execution_fn: test-only override for Step 2 (native load). Production callers must
                leave this None so the real serum_track_loader.load_and_verify() bridge runs.
        ui_evidence_provider: REQUIRED callback that returns a NativeExecutionEvidence built from a
                real native execution. Tests use make_test_ui_evidence_provider(); production wires
                an adapter that actually drove the Windows/Ableton/Serum GUI.

    Returns:
        The same `result` object, mutated by brain.finalize_serum_preset_execution(): execution_status
        becomes "EXECUTED" (or "EXECUTION_UNVERIFIED" if readback_verified was False), and
        serum_preset_execution is populated with the real evidence.

    Raises:
        ValueError: result is not ADVISORY_ONLY, or supplied evidence is incomplete/malformed.
        ExecutionEnvironmentUnavailable: no native environment (or no evidence adapter) available.
        PresetGenerationFailed: canonical preset generation did not succeed.
    """
    if result.execution_status != "ADVISORY_ONLY":
        raise ValueError(
            "execute_serum_preset_plan() requires execution_status == 'ADVISORY_ONLY', got %r"
            % result.execution_status
        )

    plan = getattr(result, "_serum_preset_plan", None)
    if not plan or plan.get("status") != "ADVISORY_ONLY":
        raise ValueError("result._serum_preset_plan is missing or not an ADVISORY_ONLY plan")

    epoch = require_epoch(epoch)
    brain = brain or get_brain(epoch)

    # ---- Step 1: generate the canonical .SerumPreset ----
    if preset_generation_fn:
        gen = preset_generation_fn(result, plan, epoch)
    else:
        gen = _generate_canonical_preset(result, plan, epoch, brain)
    if gen.get("status") != "SUCCESS":
        raise PresetGenerationFailed(
            "Canonical preset generation failed: %s" % gen.get("error", "unknown error")
        )
    preset_path, preset_sha256 = gen.get("preset_path"), gen.get("preset_sha256")
    if not preset_path or not preset_sha256:
        raise PresetGenerationFailed("Preset generation reported SUCCESS but omitted preset_path/preset_sha256")

    # ---- Step 2: load into real, running Serum (Windows/Ableton only) ----
    load_result = (native_execution_fn or _load_preset_native)(preset_path)
    if load_result.get("status") != "LOADED_VISUAL":
        raise RuntimeError("Native load failed: %s" % load_result.get("reason", load_result))

    # ---- Step 3: obtain real UI evidence from the native execution just performed ----
    if ui_evidence_provider is None:
        raise ExecutionEnvironmentUnavailable(
            "No ui_evidence_provider supplied. Real DIRECT_UI evidence (screenshot, observed values, "
            "restoration proof) must come from someone actually looking at the loaded Serum instance -- "
            "run this on Windows with Ableton Live + Serum 2.0.23 and a real observation/screenshot "
            "adapter, or supply make_test_ui_evidence_provider() in a test."
        )
    evidence = ui_evidence_provider(preset_path, load_result)
    if not isinstance(evidence, NativeExecutionEvidence):
        raise ValueError("ui_evidence_provider must return a NativeExecutionEvidence")
    _validate_evidence(evidence)

    # ---- Step 4: build the exact ui_readback shape state_comparator._binding_quality (A7) and
    # gate_b_status (A8) require, then finalize on the SAME brain that produced the plan ----
    ui_readback = {
        "route": "DIRECT_UI",
        "captured_at": evidence.run_id,
        "values": dict(evidence.observed_values),
        "restoration_verified": evidence.restoration_verified,
        "loader_evidence": {
            "run_id": evidence.run_id,
            "track_nonce": evidence.track_nonce,
            "epoch": evidence.epoch.serum_version,
            "serum_module_sha256": evidence.serum_module_sha256,
            "screenshot_sha": evidence.screenshot_sha,
            "crop_coords": list(evidence.crop_coords),
            "values": dict(evidence.observed_values),
        },
    }

    return brain.finalize_serum_preset_execution(
        result,
        preset_path=preset_path,
        preset_sha256=preset_sha256,
        ui_readback=ui_readback,
        readback_verified=evidence.readback_verified,
    )


def _validate_evidence(evidence: NativeExecutionEvidence) -> None:
    """Reject incomplete/malformed evidence before it ever reaches finalize_serum_preset_execution --
    the same shape A7's _binding_quality would reject, caught here with a specific message instead of
    a generic downstream UNBOUND/NATIVE_STATE_PROOF classification."""
    if not evidence.run_id or not evidence.run_id.strip():
        raise ValueError("NativeExecutionEvidence.run_id must be a non-empty string")
    if not evidence.track_nonce or not evidence.track_nonce.strip():
        raise ValueError("NativeExecutionEvidence.track_nonce must be a non-empty string")
    sha = evidence.serum_module_sha256
    if not isinstance(sha, str) or len(sha) != 64:
        raise ValueError("NativeExecutionEvidence.serum_module_sha256 must be 64 hex characters")
    int(sha, 16)  # raises ValueError on non-hex
    shot = evidence.screenshot_sha
    if not isinstance(shot, str) or len(shot) != 64:
        raise ValueError("NativeExecutionEvidence.screenshot_sha must be 64 hex characters")
    int(shot, 16)
    coords = evidence.crop_coords
    if not isinstance(coords, (list, tuple)) or len(coords) != 4:
        raise ValueError("NativeExecutionEvidence.crop_coords must be exactly [x, y, w, h]")
    if not all(isinstance(c, (int, float)) and not isinstance(c, bool) and c >= 0 for c in coords):
        raise ValueError("NativeExecutionEvidence.crop_coords must be finite, non-negative numbers")
    if not isinstance(evidence.observed_values, dict) or not evidence.observed_values:
        raise ValueError("NativeExecutionEvidence.observed_values must be a non-empty dict")


def _generate_canonical_preset(
    result: ProducerResult, plan: Dict[str, Any], epoch: ExecutionEpoch, brain: ProducerBrain,
) -> Dict[str, Any]:
    """Canonical preset generation for the single-target intent-based admission path, calling the
    EXISTING generic compiler (serum2.execution.authorized_state_compiler.compile_ops -- the same one
    reference_reproduction.py uses) rather than reimplementing any of its lowering/validation logic.

    The bridge: _run_serum_preset_path()'s own admission (ContractGovernedExecutor -> ExecutionAuthority.
    scope) proves the target is ADMITTED but produces a plain {mutation_target_path, mutation_value_used}
    pair -- not the AuthorizedOperation/binding-dict shape compile_ops() requires (which
    ops_from_rows() only ever builds from a state_ledger Row). Rather than re-derive that binding dict
    by hand (real risk of a subtle field-naming mistake silently producing a WRONG preset), this
    reconstructs a single observed Row from the SAME real facts the brain already produced --
    canonical_target and the user's actual requested operand, both read from result.b1_intent (never
    from plan['qualification_test_value'], which is evidence metadata only per architecture rule) --
    and runs it through the real state_ledger.derive() -> state_admission.admit_rows() ->
    authorized_state_compiler.ops_from_rows()/compile_ops() chain unchanged. admit_rows() is a SEPARATE,
    independent admission gate (the one the row-based reference-reproduction path already uses); calling
    it here can only ADD a stricter check on top of the brain's own ContractGovernedExecutor admission,
    never weaken or bypass it -- it consults the identical evidence dirs/epoch this exact brain was
    built with (brain._binding_evidence_dir/_promoted_evidence_dir), so it can never admit under
    different evidence than the brain itself was authorized against.

    Generic across every 'field'-kind control: nothing below names one specific control. A target whose
    binding is fx/route/singleton_field, or that derive()/admit_rows() itself refuses, fails closed with
    the real refusal reason -- never an approximately-correct preset.
    """
    b1 = result.b1_intent or {}
    target = b1.get("canonical_target")
    op = b1.get("operation") or {}
    value = op.get("target_value")
    if not target or value is None:
        return {"status": "FAILED",
                "error": "result.b1_intent missing canonical_target/operation.target_value "
                         "(resolution_mode=%r) -- cannot identify the real requested operand" % b1.get("resolution_mode")}

    # The target's OWN declared production-facing unit (e.g. 'seconds' for env2.decay) -- real data from
    # this same admitted resolution's representation.value_domain, never guessed or hardcoded per target.
    unit = ((b1.get("representation") or {}).get("value_domain") or {}).get("unit") or ""

    from serum2.producer.state_ledger import Row, derive
    from serum2.producer.state_admission import admit_rows
    from serum2.execution.authorized_state_compiler import ops_from_rows, compile_ops
    from serum2.execution.state_comparator import serialize

    row = Row(control_id=target, value=value, unit=unit, status="OBSERVED", control_type="fader",
              source_ts=0.0, n_readings=1, changed_from_previous=False, context={})
    derive(row, tempo=120.0)
    if row.terminal != "OPERATION_DERIVED":
        return {"status": "FAILED",
                "error": "derive() could not turn %s=%r%s into an operation: %s" % (target, value, unit, row.reason)}

    admit_rows([row], epoch, binding_evidence_dir=brain._binding_evidence_dir,
              promoted_evidence_dir=brain._promoted_evidence_dir)
    if row.admission != "ADMITTED":
        return {"status": "FAILED",
                "error": "admit_rows() (independent row-based gate) refused %s: %s" % (target, row.admission)}

    ops = ops_from_rows([row], epoch)
    if not ops:
        return {"status": "FAILED", "error": "ops_from_rows() produced no AuthorizedOperation for %s" % target}

    try:
        report = compile_ops(ops, plan.get("capability_key") or target,
                             "W1 orchestrator: %s set to admitted operand" % target, epoch)
    except Exception as e:
        return {"status": "FAILED", "error": "compile_ops() raised %s: %s" % (type(e).__name__, e)}
    if report.status != "SUCCESS":
        return {"status": "FAILED", "error": "compile_ops() incomplete: missing=%s" % report.missing}

    preset_path = serialize(report, subfolder="W1")
    preset_sha256 = hashlib.sha256(Path(preset_path).read_bytes()).hexdigest()
    return {"status": "SUCCESS", "preset_path": preset_path, "preset_sha256": preset_sha256}


def _load_preset_native(preset_path: str) -> Dict[str, Any]:
    """Load the preset into real Serum via the existing Windows/Ableton bridge. Never a second loader:
    delegates entirely to serum2.ableton.serum_track_loader.load_and_verify(). Raises
    ExecutionEnvironmentUnavailable (not a fabricated FAILED/LOADED_VISUAL dict) when this machine
    cannot run the bridge at all."""
    from serum2.ableton.serum_track_loader import load_and_verify, BridgeUnavailable

    try:
        return load_and_verify(preset_path)
    except BridgeUnavailable as e:
        raise ExecutionEnvironmentUnavailable(str(e)) from e


def make_test_ui_evidence_provider(
    *,
    epoch: ExecutionEpoch,
    run_id: str = "test-run-0001",
    track_nonce: str = "SRMTEST01",
    serum_module_sha256: Optional[str] = None,
    screenshot_sha: str = "a" * 64,
    crop_coords: Optional[List[float]] = None,
    observed_values: Optional[Dict[str, str]] = None,
    readback_verified: bool = True,
    restoration_verified: bool = True,
) -> Callable[[str, Dict[str, Any]], NativeExecutionEvidence]:
    """Deterministic test fixture for `ui_evidence_provider`. Explicitly test-only -- production code
    must supply a real adapter that reads an actual Serum instance, never this."""
    _sha = serum_module_sha256 or epoch.binary_sha256
    _coords = crop_coords if crop_coords is not None else [0, 0, 1920, 1080]
    _values = observed_values if observed_values is not None else {"test_control": "test_value"}

    def provider(preset_path: str, load_result: Dict[str, Any]) -> NativeExecutionEvidence:
        return NativeExecutionEvidence(
            run_id=run_id,
            track_nonce=track_nonce,
            epoch=epoch,
            serum_module_sha256=_sha,
            screenshot_sha=screenshot_sha,
            crop_coords=list(_coords),
            observed_values=dict(_values),
            readback_verified=readback_verified,
            restoration_verified=restoration_verified,
        )

    return provider
