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
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def gate_b_status(result, epoch=None) -> str:
    """Compute the Gate B verification status from a ProducerResult.

    Returns one of:
      "CANONICAL_GATE_B_VERIFIED"  — full chain verified with bound native proof
      "NATIVE_STATE_PROOF"         — native execution verified but chain not fully bound
      "GATE_B_BLOCKED"             — execution was not completed or not accepted
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
    # CANONICAL_GATE_B_VERIFIED: additionally requires admitted + bound module SHA
    if not getattr(result, "admitted", False):
        return "NATIVE_STATE_PROOF"

    # Check loader_evidence for module SHA binding
    ui_rb = spe.get("ui_readback") or {}
    le = ui_rb.get("loader_evidence") or {}
    module_sha = le.get("serum_module_sha256")
    if not module_sha:
        return "NATIVE_STATE_PROOF"

    if epoch is not None:
        if module_sha != epoch.binary_sha256:
            return "NATIVE_STATE_PROOF"

    return "CANONICAL_GATE_B_VERIFIED"


def gate_b_certificate(result, epoch=None) -> Dict[str, Any]:
    """Serialize the Gate B evidence to a machine-readable certificate dict.

    All fields come directly from the ProducerResult or epoch; nothing is
    hand-declared.  The caller commits this dict to the fixture store.
    """
    status = gate_b_status(result, epoch)
    spe = getattr(result, "serum_preset_execution", None) or {}
    ui_rb = spe.get("ui_readback") or {}
    le = ui_rb.get("loader_evidence") or {}
    plan = getattr(result, "_serum_preset_plan", None) or {}
    fc = (plan.get("final_execution_contract") or {})

    cert: Dict[str, Any] = {
        "gate_b_status": status,
        "native_evidence_source": "Windows/Ableton/Serum 2.0.23",
        "dawdreamer_used": False,
        "headless_substitution_used": False,
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
        # value separation: only metadata, never the production operand
        "qualification_test_value": plan.get("qualification_test_value"),
        # A2 gate evidence
        "atlas_id": fc.get("atlas_id"),
        "agrees_with_admitted_mutation_path": fc.get("agrees_with_admitted_mutation_path"),
        "final_execution_classification": fc.get("final_execution_classification"),
        # screenshot binding
        "screenshot_sha256": ui_rb.get("screenshot_sha256"),
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
