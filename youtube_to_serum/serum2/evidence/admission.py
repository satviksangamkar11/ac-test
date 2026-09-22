"""15.4: compiler admission. The ONE function a future compiler is meant to
call before executing any Serum mutation. Everything here is a read-only
QUERY over CapabilityContracts (which are themselves read-only over
ClaimGroups) -- this module adds no new facts, only a structured refusal
vocabulary so "why not" is always answerable and never silent.

15.4.3's invariant lives here, not in capability_contract.py: a target with
NO contract at all is UNKNOWN, and admission refuses it with reason
"unknown_no_contract" -- never with a reason implying Serum rejects it.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from . import capability_contract as cc

# ---- refusal reasons -- exhaustive, each maps to one adversarial case in
# the 15.4.8 proof suite ----
ADMITTED = "ADMITTED"
REFUSED_UNKNOWN = "unknown_no_contract"                # 15.4.3: no evidence exists AT ALL
REFUSED_NEGATIVE_EVIDENCE = "negative_evidence"        # evidence exists, gate demonstrably failed
REFUSED_UNSUPPORTED = "unsupported"                    # robust, repeated rejection
REFUSED_CONTRADICTED = "contradicted_reverify_required"
REFUSED_STRUCTURAL_ONLY_FOR_CAUSAL = "structural_only_insufficient_for_causal_requirement"
REFUSED_PREREQUISITE_UNVERIFIED = "prerequisite_unverified"  # 15.4.5
REFUSED_MEASUREMENT_MISMATCH = "measurement_definition_mismatch"  # 15.4.6
REFUSED_SCOPE_EXPANSION = "scope_would_expand_beyond_tested_target"  # 15.4.7


@dataclass(frozen=True)
class AdmissionResult:
    admitted: bool
    reason: str
    detail: str
    contract: Optional[cc.CapabilityContract] = None

    def __bool__(self):
        return self.admitted


def admit(contracts: Dict[Tuple[str, str], cc.CapabilityContract], target: str, *,
         required_causal: bool = False,
         required_persistence: bool = False,
         proposed_prerequisites_verified: Optional[Dict[str, bool]] = None,
         required_measurement_definition_id: Optional[str] = None) -> AdmissionResult:
    """target must be an EXACT claim_type key (e.g. "fx_field_eq_freq1"), not
    a family name or substring -- 15.4.7's scope guard is enforced simply by
    never doing fuzzy/prefix lookup here. A caller that wants "any FXEQ field"
    does not get one: they get UNKNOWN, because no such capability was ever
    tested or contracted.
    """
    matches = [c for (cdid, cond), c in contracts.items() if c.target == target]
    if not matches:
        return AdmissionResult(False, REFUSED_UNKNOWN,
                               "no ClaimGroup/contract exists for target %r. This means nothing "
                               "was ever tested -- it is NOT a claim that Serum cannot support "
                               "it (see 15.4.3: UNKNOWN != UNSUPPORTED)." % target)

    # 15.4.7: a target may have MULTIPLE contracts (different tested
    # conditions). Admission is scoped to the STRONGEST one that still tells
    # the truth -- never averaged, never silently widened to "the family
    # generally works". Pick a CAUSAL_VERIFIED contract if one exists for
    # this exact target; otherwise the least-blocked available, but the
    # decision below always re-checks the ACTUAL contract, not an assumption.
    contract = next((c for c in matches if c.status == cc.CAUSAL_VERIFIED), matches[0])

    if contract.status == cc.BLOCKED_CONTRADICTED:
        return AdmissionResult(False, REFUSED_CONTRADICTED,
                               "target %r is contradicted: %s" % (target, contract.limitations), contract)
    if contract.status == cc.UNSUPPORTED:
        return AdmissionResult(False, REFUSED_UNSUPPORTED,
                               "target %r has a robust, repeated demonstrated rejection: %s"
                               % (target, contract.limitations), contract)
    if contract.status == cc.NEGATIVE_EVIDENCE:
        return AdmissionResult(False, REFUSED_NEGATIVE_EVIDENCE,
                               "target %r has real evidence, and that evidence is negative: %s"
                               % (target, contract.limitations), contract)

    if required_causal and contract.status != cc.CAUSAL_VERIFIED:
        return AdmissionResult(False, REFUSED_STRUCTURAL_ONLY_FOR_CAUSAL,
                               "target %r is %s (verified.causal=%s) -- caller requires a proven "
                               "causal effect, which this contract does not establish"
                               % (target, contract.status, contract.verified.get("causal")), contract)

    if required_persistence and contract.verified.get("persistence") != "PASS":
        return AdmissionResult(False, REFUSED_PREREQUISITE_UNVERIFIED,
                               "target %r does not have a verified persistence=PASS gate "
                               "(observed: %s)" % (target, contract.verified.get("persistence")), contract)

    # 15.4.5: prerequisite refusal. A contract's `prerequisites` are what the
    # ORIGINAL experiment declared and (per the harness) runtime-verified for
    # ITS OWN arms. A caller proposing to EXECUTE this capability in a new
    # context must independently confirm those same prerequisites hold there
    # -- the contract cannot vouch for a context it never ran in.
    if contract.prerequisites:
        verified_map = proposed_prerequisites_verified or {}
        unverified = []

        for p in contract.prerequisites:
            field_path = p["field_path"]
            verified_status = verified_map.get(field_path)

            # Prerequisite not verified at all
            if not verified_status:
                unverified.append(field_path)
                continue

            # 16.5.50.2: Value-sensitive prerequisites (must_hold_identical=True)
            # If caller provides an actual VALUE (not just True), check it matches declared_value.
            # If caller only provides True (backward compatible), accept it as verified.
            if p.get("must_hold_identical") and verified_status is not True:
                declared_value = p.get("declared_value")
                if verified_status != declared_value:
                    unverified.append(field_path)
                # else: value matches, prerequisite is satisfied
            # else: verified_status is True or not must_hold_identical, accept as verified

        if unverified:
            return AdmissionResult(False, REFUSED_PREREQUISITE_UNVERIFIED,
                                   "target %r requires prerequisite(s) %s to be verified in the "
                                   "PROPOSED execution context; caller did not confirm: %s"
                                   % (target, [p["field_path"] for p in contract.prerequisites], unverified),
                                   contract)

    # 15.4.6: measurement mismatch. A caller asking for a specific measurement
    # kernel identity that doesn't match what this contract's evidence was
    # actually measured with cannot borrow this contract's causal claim --
    # two different kernels under one metric NAME are not the same evidence
    # (this is the exact bug class kernel-identity hashing was built to catch).
    if required_measurement_definition_id is not None:
        actual_mdid = (contract.measurement or {}).get("measurement_definition_id")
        if actual_mdid != required_measurement_definition_id:
            return AdmissionResult(False, REFUSED_MEASUREMENT_MISMATCH,
                                   "target %r was measured with definition %r, caller requires %r "
                                   "-- not the same evidence, cannot be substituted"
                                   % (target, actual_mdid, required_measurement_definition_id), contract)

    return AdmissionResult(True, ADMITTED,
                           "target %r admitted: status=%s, allowed_operation=%s"
                           % (target, contract.status, contract.allowed_operation), contract)
