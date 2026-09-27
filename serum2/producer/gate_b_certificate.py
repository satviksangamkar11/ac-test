"""Gate B certificate: machine-checkable verification status from a native Serum execution.

Two distinct proofs — do NOT collapse them:

  NATIVE_STATE_PROOF
    The native Serum binary was genuinely loaded and the correct value appeared in
    the live UI.  Requires:
      - execution_status == "EXECUTED"
      - decision == "ACCEPTED"
      - serum_preset_execution.readback_verified == True
      - serum_preset_execution.preset_sha256 non-empty

  CANONICAL_GATE_B_VERIFIED
    The full canonical chain ran: ProducerBrain admission → plan → native execution
    → bound UI readback → finalize_serum_preset_execution().  Requires all of
    NATIVE_STATE_PROOF plus:
      - admitted == True
      - serum_preset_execution.ui_readback carries loader_evidence with
        serum_module_sha256 == epoch.binary_sha256  (proves the right binary was active)
      - restoration_verified present in ui_readback (or execution_spec)

Neither status is granted from a hand-supplied boolean alone; every field comes from
the ProducerResult the canonical chain produced.

Operand invariant (gate_b_certificate only):
  When requested_operand, compiled_operand, and native_resave_operand are all provided:
    - requested_operand == compiled_operand  (exact equality; both are the user's value)
    - math.isclose(native_resave_operand, compiled_operand, rel_tol=1e-6, abs_tol=1e-6)
      (native re-save is allowed float64 round-trip error)
  Invariant failure downgrades CANONICAL_GATE_B_VERIFIED → NATIVE_STATE_PROOF.
  Partial operand evidence (some but not all provided) is also treated as a failure.
  qualification_test_value (the binding-test value, e.g. 0.5 s) must differ from
  requested_operand (the user's value, e.g. 5.0 s); it is evidence metadata only.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional


def gate_b_status(result, epoch=None) -> str:
    """Compute the Gate B verification status from a ProducerResult.

    Returns one of:
      "CANONICAL_GATE_B_VERIFIED"  — full chain verified with bound native proof
      "NATIVE_STATE_PROOF"         — native execution verified but chain not fully bound
      "GATE_B_BLOCKED"             — execution was not completed or not accepted

    A8: DawDreamer/headless evidence blocks CANONICAL_GATE_B_VERIFIED.

    A7/A8 integration: CANONICAL_GATE_B_VERIFIED consumes the SAME canonical binding-quality validation
    A7 owns (state_comparator._binding_quality), rather than re-implementing a narrower, independently
    maintained subset of its checks here. A readback A7 itself would refuse to call LOADER_BOUND (missing
    run_id/track_nonce/screenshot hash/crop_coords/observed values, or bound to the WRONG epoch) can
    therefore never be promoted to CANONICAL_GATE_B_VERIFIED just because this function's own older,
    narrower check (module SHA alone) happened to pass -- that gap was a real authority/evidence-gate
    bypass. `epoch` is REQUIRED (not merely accepted) for CANONICAL_GATE_B_VERIFIED: epoch=None can never
    reach canonical, since there would be no runtime epoch to bind the readback to.
    """
    # Must be executed and accepted
    if getattr(result, "execution_status", None) != "EXECUTED":
        return "GATE_B_BLOCKED"
    if getattr(result, "decision", None) != "ACCEPTED":
        return "GATE_B_BLOCKED"

    spe = getattr(result, "serum_preset_execution", None) or {}
    if not spe.get("readback_verified"):
        return "GATE_B_BLOCKED"
    if not spe.get("preset_sha256"):
        return "GATE_B_BLOCKED"

    # NATIVE_STATE_PROOF: all minimal evidence present
    # CANONICAL_GATE_B_VERIFIED: additionally requires admitted + the full A7 LOADER_BOUND evidence chain
    if not getattr(result, "admitted", False):
        return "NATIVE_STATE_PROOF"

    ui_rb = spe.get("ui_readback") or {}

    # epoch is mandatory for canonical status: with no runtime epoch, there is nothing to bind the
    # readback's own claimed epoch/module SHA to, so it can never be more than NATIVE_STATE_PROOF.
    if epoch is None:
        return "NATIVE_STATE_PROOF"

    # A canonical readback must actually come from the live plugin route, not a file-only comparison.
    if ui_rb.get("route") != "DIRECT_UI":
        return "NATIVE_STATE_PROOF"

    from serum2.execution.state_comparator import _binding_quality
    if _binding_quality(ui_rb, expected_epoch=epoch) != "LOADER_BOUND":
        return "NATIVE_STATE_PROOF"

    # Canonical Gate B additionally requires restoration evidence: the canonical chain must show the
    # mutated state was verified restorable (see module docstring), not just that a value was written and
    # read back once. Absence of this evidence downgrades to NATIVE_STATE_PROOF, never a silent pass.
    if ui_rb.get("restoration_verified") is not True:
        return "NATIVE_STATE_PROOF"

    return "CANONICAL_GATE_B_VERIFIED"


def gate_b_certificate(result, epoch=None, *,
                       requested_operand=None,
                       compiled_operand=None,
                       native_resave_operand=None,
                       native_resave_sha256=None) -> Dict[str, Any]:
    """Serialize the Gate B evidence to a machine-readable certificate dict.

    All fields come directly from the ProducerResult or epoch; nothing is
    hand-declared.  The caller commits this dict to the fixture store.

    When requested_operand, compiled_operand, and native_resave_operand are
    provided (all three must be provided together), the operand invariant is
    checked:
      - requested_operand == compiled_operand (exact)
      - math.isclose(native_resave_operand, compiled_operand, rel_tol=1e-6, abs_tol=1e-6)
    Invariant failure downgrades CANONICAL_GATE_B_VERIFIED → NATIVE_STATE_PROOF.
    Providing only some operands also downgrades (INCOMPLETE_OPERAND_EVIDENCE).

    qualification_test_value in the plan is evidence metadata; it must differ
    from requested_operand (the production value the user asked for).
    """
    base_status = gate_b_status(result, epoch)
    spe = getattr(result, "serum_preset_execution", None) or {}
    ui_rb = spe.get("ui_readback") or {}
    le = ui_rb.get("loader_evidence") or {}
    plan = getattr(result, "_serum_preset_plan", None) or {}
    fc = (plan.get("final_execution_contract") or {})

    # Operand invariant check
    operands = [requested_operand, compiled_operand, native_resave_operand]
    n_provided = sum(1 for v in operands if v is not None)

    effective_status = base_status
    operand_invariant_status: str

    if n_provided == 0:
        operand_invariant_status = "OPERAND_EVIDENCE_NOT_PROVIDED"
    elif n_provided < 3:
        operand_invariant_status = "INCOMPLETE_OPERAND_EVIDENCE"
        if effective_status == "CANONICAL_GATE_B_VERIFIED":
            effective_status = "NATIVE_STATE_PROOF"
    else:
        # All three provided — enforce invariants
        if requested_operand != compiled_operand:
            operand_invariant_status = "OPERAND_MISMATCH_REQUESTED_VS_COMPILED"
            if effective_status == "CANONICAL_GATE_B_VERIFIED":
                effective_status = "NATIVE_STATE_PROOF"
        elif not math.isclose(float(native_resave_operand), float(compiled_operand),
                               rel_tol=1e-6, abs_tol=1e-6):
            operand_invariant_status = "OPERAND_MISMATCH_NATIVE_VS_COMPILED"
            if effective_status == "CANONICAL_GATE_B_VERIFIED":
                effective_status = "NATIVE_STATE_PROOF"
        else:
            operand_invariant_status = "OPERAND_INVARIANT_VERIFIED"

    # A8: Derive headless evidence from actual ui_readback (not hardcoded False)
    dawdreamer_used = ui_rb.get("backend") and "DawDreamer" in str(ui_rb.get("backend")) or False
    headless_substitution_used = ui_rb.get("is_headless") is True or False

    # A8: native_evidence_source must never claim native (Windows/Ableton) proof for evidence this
    # certificate itself knows is headless/DawDreamer-substituted -- that would let a non-native run
    # carry a certificate that reads as native. Derived from the SAME evidence as the flags above, and
    # from the epoch actually passed in (never a hardcoded version string).
    if dawdreamer_used or headless_substitution_used:
        native_evidence_source = "DawDreamer (headless, non-native substitution)"
    elif epoch is not None:
        native_evidence_source = "Windows/Ableton/Serum %s" % epoch.serum_version
    else:
        native_evidence_source = None

    cert: Dict[str, Any] = {
        "gate_b_status": effective_status,
        "native_evidence_source": native_evidence_source,
        "dawdreamer_used": dawdreamer_used,
        "headless_substitution_used": headless_substitution_used,
        # epoch
        "epoch": epoch.label if epoch is not None else None,
        "epoch_binary_sha256": epoch.binary_sha256 if epoch is not None else None,
        # execution result
        "execution_status": getattr(result, "execution_status", None),
        "decision": getattr(result, "decision", None),
        "admitted": getattr(result, "admitted", None),
        # preset evidence
        "preset_sha256": spe.get("preset_sha256"),
        "readback_verified": spe.get("readback_verified"),
        # native module binding
        "loaded_module_sha256": le.get("serum_module_sha256"),
        "run_id": le.get("run_id"),
        "track_nonce": le.get("track_nonce"),
        # path
        "target_path": plan.get("mutation_target_path"),
        # value separation: qualification_test_value is evidence metadata only;
        # it must never equal requested_operand (the production value)
        "qualification_test_value": plan.get("qualification_test_value"),
        # operand evidence (from W1 execution, all three or none)
        "requested_operand": requested_operand,
        "compiled_operand": compiled_operand,
        "native_resave_operand": native_resave_operand,
        "operand_invariant_status": operand_invariant_status,
        # native re-save file binding
        "native_resave_sha256": native_resave_sha256,
        # A2 gate evidence
        "atlas_id": fc.get("atlas_id"),
        "agrees_with_admitted_mutation_path": fc.get("agrees_with_admitted_mutation_path"),
        "final_execution_classification": fc.get("final_execution_classification"),
        # screenshot binding. A7's loader_evidence schema (state_comparator._binding_quality) names this
        # field "screenshot_sha" inside loader_evidence -- not a top-level "screenshot_sha256" on ui_rb,
        # which never existed in any real evidence shape and always read back None.
        "screenshot_sha256": le.get("screenshot_sha"),
        # restoration
        "restoration_verified": (
            fc.get("restoration_verified")
            or ui_rb.get("restoration_verified")
        ),
    }
    return cert


def gate_b_verified(cert: Dict[str, Any]) -> bool:
    """True iff the certificate records CANONICAL_GATE_B_VERIFIED.

    This is the only correct way to ask "did Gate B pass?" — never inspect
    individual fields from outside this module.
    """
    return cert.get("gate_b_status") == "CANONICAL_GATE_B_VERIFIED"
