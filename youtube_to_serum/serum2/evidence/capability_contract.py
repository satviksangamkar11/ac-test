"""15.3: Capability Contracts -- a DERIVED, READ-ONLY layer on top of the
evidence/claim system. It formalizes what a ClaimGroup has already proven; it
never asserts anything the ClaimGroup does not itself support.

Layering (one-directional, never reversed):

    Experiment -> EvidenceRecord -> ClaimDefinition -> ClaimGroup -> CapabilityContract

A CapabilityContract is built ONLY by reading a ClaimGroup's own derived_*
methods and its supporting EvidenceRecords. It has no fields that are written
independently of that evidence, and nothing here ever writes back into the
evidence or claim layers (Capability -> Evidence is forbidden by construction:
this module only ever calls read-only methods on ClaimGroup/EvidenceRecord).

The critical invariant this module exists to enforce: a well-characterized
family (e.g. FXEQ, mostly EFFECT_OBSERVED) must NOT cause an individual
NO_OBSERVED_EFFECT result (e.g. FXEQ.Type1) to be reported as causally
verified. Each contract is built from its OWN ClaimGroup's OWN evidence only.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .claim import ClaimGroup, CONTRADICTED
from .canonical import digest
from .record import PASS, NOT_RUN

# ---- allowed_operation vocabulary -- derived from the mutation VALUE TYPE
# actually present in evidence, never assumed from the field name ----
MUTATE_NUMERIC = "mutate_numeric_value"
MUTATE_ENUM = "mutate_enum_value"
MUTATE_STRUCTURED = "mutate_structured_value"
CONSTRUCT_ONLY = "construct_persist_only"   # no operation semantics proven beyond this
UNKNOWN_OPERATION = "unknown_operation"

# ---- contract status -- distinct from capability.py's FAMILY ladder. This is
# per-CLAIM, not per-FAMILY: a family can carry contracts at different tiers
# simultaneously (see FXEQ: Type2 CAUSAL_VERIFIED, Type1 STRUCTURAL_ONLY) ----
#
# 15.4.1 state machine. Five states, each covering a semantically DIFFERENT
# epistemic situation -- not added speculatively, each earned by a real case
# hit in this session's own evidence:
#
#   UNKNOWN              no ClaimGroup/contract exists for this target at all
#                         (a lookup miss -- see admission.py). NOT a claim
#                         that Serum can't do it; simply nothing was tried.
#   NEGATIVE_EVIDENCE     a ClaimGroup EXISTS, admitted evidence EXISTS, but
#                         the definition's required gate was demonstrably NOT
#                         met by any of it (e.g. Macro.name: persistence
#                         actually FAILED; LFO-as-source: causal actually
#                         measured as NO_OBSERVED_EFFECT on 6 candidates).
#                         Different from UNKNOWN: we HAVE an answer, and the
#                         answer is negative -- not merely absent.
#   STRUCTURAL_ONLY       construct+mutate+persist proven; causal either
#                         NOT_RUN or NO_OBSERVED_EFFECT, under a
#                         ClaimDefinition that never required causal PASS to
#                         promote (predicate="constructs_mutates_persists").
#   CAUSAL_VERIFIED       causal outcome == EFFECT_OBSERVED, and the
#                         definition required causal PASS to reach this tier.
#   BLOCKED_CONTRADICTED  group has contradicting evidence -- reverify_required.
#   UNSUPPORTED           NEGATIVE_EVIDENCE PLUS a robust, repeated,
#                         consistent demonstration of rejection (breadth_rule's
#                         sampled_min met by uniformly-failing qualifying-
#                         eligible records, zero successes, zero contradiction).
#                         Reserved, currently unreached by any contract in this
#                         corpus -- no target has yet earned "Serum
#                         demonstrably rejects this" at that evidentiary bar;
#                         a single failing instance is NEGATIVE_EVIDENCE, not
#                         UNSUPPORTED.
CAUSAL_VERIFIED = "CAUSAL_VERIFIED"
STRUCTURAL_ONLY = "STRUCTURAL_ONLY"
BLOCKED_CONTRADICTED = "BLOCKED_CONTRADICTED"
NEGATIVE_EVIDENCE = "NEGATIVE_EVIDENCE"
UNSUPPORTED = "UNSUPPORTED"
BLOCKED_NO_EVIDENCE = NEGATIVE_EVIDENCE  # back-compat alias; NEGATIVE_EVIDENCE is the honest name


@dataclass(frozen=True)
class ExecutionBinding:
    """Authoritative execution primitive binding.

    Derived from evidence, never caller-supplied.
    Maps semantic target to concrete execution primitive.
    """
    mutation_type: str                # "BODY_STATE" | "HOST_PARAMETER" | "TOPOLOGY" | "COMPOUND" | "META_STRING"
    body_path: Optional[str] = None   # e.g. "Envelope0.plainParams.kParamRelease" (BODY_STATE)
    host_parameter_name: Optional[str] = None  # e.g. "Env 1 Release" (HOST_PARAMETER)
    meta_path: Optional[str] = None   # e.g. "presetName" (META_STRING) -- a top-level key in
                                       # the .SerumPreset file's JSON meta dict, not a CBOR body path
    binding_source: str = ""          # e.g. "semantic_vst3_mapping.json", "evidence_mutation_0001.pkl"
    binding_version: str = ""         # version/hash of the mapping used

    # AUTHORITY INTEGRATION (STATE, first of the Execution Coverage V2
    # "authority-integrated generic operations" milestone): for BODY_STATE
    # targets whose concrete body_path is NOT yet directly known (e.g. FX
    # parameters addressed by rack/slot/effect/parameter rather than a
    # literal dotted path), the contract may instead name a resolver
    # operation registered in serum2.operations.registry.OperationRegistry.
    # When set, body_path is left None and the executor resolves the real
    # path (and validates the value) by calling this resolver's compiler --
    # strictly AFTER admission has already passed, never before. This is
    # the one and only sanctioned way an OperationRegistry compiler may run:
    # as a backend invoked from inside the authority-gated executor, never
    # called directly by a producer or any other caller.
    resolver_operation_id: Optional[str] = None  # e.g. "fx_set_parameter"


@dataclass(frozen=True)
class CapabilityContract:
    target: str                      # e.g. "FXEQ.kParamType1"
    allowed_operation: str
    status: str
    prerequisites: Tuple[Dict[str, Any], ...]
    verified: Dict[str, Any]         # {"load":..., "persistence":..., "causal":...} -- ACTUAL outcomes, never upgraded
    measurement: Optional[Dict[str, Any]]
    scope: Dict[str, Any]            # tested-context-only description + any flagged limitation
    provenance: Dict[str, Any]       # evidence ids, claim_definition_id, condition hash -- traceable back
    execution_binding: Optional[ExecutionBinding] = None  # AUTHORITATIVE execution primitive binding
    limitations: Tuple[str, ...] = ()

    def usable_for(self, required_causal: bool = False) -> bool:
        """The one query the compiler layer is meant to call. A contract
        BLOCKED_* or STRUCTURAL_ONLY (when the caller needs a causal
        guarantee) is correctly refused -- this is the enforcement point for
        'LFO source -> UNKNOWN must remain unavailable to the compiler', etc."""
        if self.status in (BLOCKED_CONTRADICTED, NEGATIVE_EVIDENCE, UNSUPPORTED):
            return False
        if required_causal and self.status != CAUSAL_VERIFIED:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target, "allowed_operation": self.allowed_operation,
            "status": self.status, "prerequisites": list(self.prerequisites),
            "verified": self.verified, "measurement": self.measurement,
            "scope": self.scope, "provenance": self.provenance,
            "limitations": list(self.limitations),
        }


def _mutation_value_kind(value) -> str:
    if isinstance(value, bool):
        return MUTATE_ENUM  # booleans behave as a 2-valued enum, not a continuous range
    if isinstance(value, (int, float)):
        return MUTATE_NUMERIC
    if isinstance(value, str):
        return MUTATE_ENUM
    if isinstance(value, dict):
        return MUTATE_STRUCTURED
    return UNKNOWN_OPERATION


def _primary_mutation(record) -> Optional[Dict[str, Any]]:
    muts = record.experiment.get("mutations", [])
    return muts[0] if len(muts) == 1 else None  # SINGLE_FIELD contracts only, by construction


def _causal_outcome_for(record) -> str:
    """The ACTUAL recorded outcome -- NOT_RUN, EFFECT_OBSERVED, NO_OBSERVED_EFFECT,
    or WRONG_DIRECTION. Never coerced to PASS/FAIL; that coercion is exactly
    what would let a well-characterized family launder a negative result."""
    if not record.causal_measurements:
        return NOT_RUN
    return record.causal_measurements[0].status


def _binding_from_evidence(rec, mut) -> Optional[ExecutionBinding]:
    """Execution binding derived ONLY from the witness record's own immutable binding_evidence (the
    candidate_binding_qualifier output stored on the record). No caller argument exists. It must be
    BINDING_VERIFIED, all three qualifier checks true, and its derived body path must be the very path
    this record's single mutation targeted -- evidence for one path is never a binding for another."""
    be = rec.experiment.get("binding_evidence")
    if not isinstance(be, dict) or not mut:
        return None
    path = be.get("derived_body_path")
    if (be.get("status") != "BINDING_VERIFIED" or not path or not be.get("accessor")
            or not all(be.get(k) is True for k in ("value_landed_in_derived_path",
                                                    "collateral_semantically_neutral", "second_write_neutral"))):
        return None
    if path != str(mut.get("target_path", "")).removeprefix("body:"):
        return None
    return ExecutionBinding(mutation_type="SERUM_PRESET_STRUCTURAL", body_path=path,
                            binding_source="evidence:%s" % rec.experiment_id, binding_version=digest(be),
                            resolver_operation_id=be["accessor"])


def build_contract(group: ClaimGroup) -> Optional[CapabilityContract]:
    """Pure function of one ClaimGroup's own state. Returns None only when
    there is nothing to say yet (no supporting evidence at all) -- that is a
    'no contract exists', not a false negative BLOCKED contract."""
    records = group._supporting_records()  # noqa: SLF001 -- read-only, same module family
    if not records and not group.contradicting_evidence:
        return None

    cdef = group.claim_definition
    target = cdef.claim_type

    if group.derived_contradiction_state() == CONTRADICTED:
        return CapabilityContract(
            target=target, allowed_operation=UNKNOWN_OPERATION, status=BLOCKED_CONTRADICTED,
            prerequisites=(), verified={"load": None, "persistence": None, "causal": None},
            measurement=None,
            scope={"tested_context_only": True,
                  "note": "contradicted -- reverify_required, no capability may be derived"},
            provenance={"claim_definition_id": cdef.claim_definition_id,
                       "condition_signature_hash": group.condition_signature_hash,
                       "supporting_evidence": list(group.supporting_evidence),
                       "contradicting_evidence": list(group.contradicting_evidence)},
            limitations=("CONTRADICTED: %s" % group.reverify.get("reason"),),
        )

    qualifying = [r for r in records if cdef.gates_met(r.gate_completeness())
                 and cdef.isolation_ok(r.experiment.get("isolation_level"))]
    if not qualifying:
        # NEGATIVE_EVIDENCE: `records` is non-empty (guaranteed by the guard
        # above), so real evidence WAS collected -- it just didn't meet this
        # definition's required gate. Surface the ACTUAL observed gate values
        # from the evidence, never None -- "we don't know" and "we tried and
        # it failed" must never render identically.
        failing_gates = [r.gate_completeness() for r in records]
        required_keys = [k for k, v in cdef.required_gate.items() if v not in (None, "ANY")]
        observed = {k: sorted({g.get(k, NOT_RUN) for g in failing_gates}) for k in required_keys}

        breadth_ok = len(records) >= cdef.breadth_rule.get("sampled_min", 2)
        all_uniformly_failing = all(
            not cdef.gates_met(g) for g in failing_gates
        )
        status = UNSUPPORTED if (breadth_ok and all_uniformly_failing) else NEGATIVE_EVIDENCE
        # UNSUPPORTED additionally requires that failure is truly UNIFORM
        # across every record's evidence -- one record's near-miss is not
        # "demonstrably rejects", it just hasn't hit the definition's bar yet.
        if status == UNSUPPORTED and any(
            any(v == "PASS" for v in observed.get(k, [])) for k in required_keys
        ):
            status = NEGATIVE_EVIDENCE  # a PASS appears somewhere -- not uniform rejection

        return CapabilityContract(
            target=target, allowed_operation=UNKNOWN_OPERATION, status=status,
            prerequisites=(), verified={k: v for k, v in
                                        [("load", observed.get("load", [NOT_RUN])[0] if len(observed.get("load", [])) == 1 else observed.get("load")),
                                         ("persistence", observed.get("persistence", [NOT_RUN])[0] if len(observed.get("persistence", [])) == 1 else observed.get("persistence")),
                                         ("causal", observed.get("causal", [NOT_RUN])[0] if len(observed.get("causal", [])) == 1 else observed.get("causal"))]},
            measurement=None,
            scope={"tested_context_only": True,
                  "note": "%d record(s) of real evidence exist for this target, but none met the "
                          "required gate(s) %s -- this is a demonstrated negative result, not an "
                          "absence of evidence" % (len(records), required_keys)},
            provenance={"claim_definition_id": cdef.claim_definition_id,
                       "condition_signature_hash": group.condition_signature_hash,
                       "supporting_evidence": list(group.supporting_evidence)},
            limitations=("required gate(s) %s observed as %s across %d record(s)"
                        % (required_keys, observed, len(records)),),
        )

    # Select witness record: prefer one with baseline_overrides (context) if available.
    # This ensures context-aware contracts use records that established the context.
    rec_with_context = next(
        (r for r in qualifying if r.experiment.get("baseline_overrides")),
        None
    )
    rec = rec_with_context or qualifying[0]

    mut = _primary_mutation(rec)
    op = _mutation_value_kind(mut["value"]) if mut else UNKNOWN_OPERATION

    causal_outcome = _causal_outcome_for(rec) if "causal" in cdef.required_gate or rec.causal_measurements else NOT_RUN
    gate = rec.gate_completeness()
    verified = {
        "load": gate.get("load", NOT_RUN),
        "persistence": gate.get("persistence", NOT_RUN),
        "causal": causal_outcome,   # honest, un-upgraded -- may be NO_OBSERVED_EFFECT even though gates_met() passed a structural-only definition
    }

    status = CAUSAL_VERIFIED if (cdef.required_gate.get("causal") == PASS
                                 and causal_outcome == "EFFECT_OBSERVED") else STRUCTURAL_ONLY

    measurement = None
    if rec.causal_measurements:
        m = rec.causal_measurements[0]
        measurement = {
            "metric": m.metric, "target_field": m.target.field_path,
            "baseline": m.baseline, "treatment": m.treatment, "delta": m.delta,
            "expected_direction": m.expected_direction, "observed_direction": m.observed_direction,
            "threshold": m.threshold, "status": m.status,
            "measurement_definition_id": m.measurement_definition_id,
        }

    prereqs = list(rec.experiment.get("prerequisites", []))

    # 16.5.50.2: Infer prerequisites from baseline_overrides if not explicitly set.
    # baseline_overrides = [{"target_path": "...", "value": ..., ...}, ...]
    # Convert to prerequisite structure: {"field_path": "...", "declared_value": ..., "must_hold_identical": True}
    baseline_overrides = rec.experiment.get("baseline_overrides", [])
    has_baseline_ctx = bool(baseline_overrides)

    if baseline_overrides and not prereqs:
        for override in baseline_overrides:
            target_path = override.get("target_path")
            value = override.get("value")
            if target_path is not None and value is not None:
                # 16.5.51: Add 'body:' prefix for harness compatibility
                # baseline_overrides contain plain paths; harness requires prefixed format
                field_path = "body:" + target_path if not target_path.startswith(("body:", "host:")) else target_path
                prereqs.append({
                    "field_path": field_path,
                    "declared_value": value,
                    "must_hold_identical": True,
                })

    prereqs = tuple(prereqs)

    limitations = []
    notes = rec.experiment.get("notes", "") or ""
    for flag in ("CONFOUND", "confound", "KNOWN LIMITATION", "NOT_RUN"):
        if flag in notes and notes not in limitations:
            limitations.append(notes)
            break
    if not has_baseline_ctx:
        limitations.append("baseline_overrides not captured in this EvidenceRecord's schema "
                           "(predates this field being added) -- shared-context prerequisites "
                           "for this contract are UNDERSTATED, not absent")
    if status == STRUCTURAL_ONLY and causal_outcome == "NO_OBSERVED_EFFECT":
        limitations.append("causal measurement WAS run and returned NO_OBSERVED_EFFECT under the "
                           "tested condition -- this is an honest negative, not NOT_RUN, and this "
                           "contract does not claim a causal effect")

    return CapabilityContract(
        target=target, allowed_operation=op, status=status,
        prerequisites=prereqs, verified=verified, measurement=measurement,
        scope={"tested_context_only": True,
              "condition_signature_hash": group.condition_signature_hash,
              "mutation_target_path": mut["target_path"] if mut else None,
              "mutation_value_used": mut["value"] if mut else None},
        provenance={"claim_definition_id": cdef.claim_definition_id,
                   "condition_signature_hash": group.condition_signature_hash,
                   "supporting_evidence": list(group.supporting_evidence),
                   "witness_experiment_id": rec.experiment_id},
        limitations=tuple(limitations),
        execution_binding=_binding_from_evidence(rec, mut),
    )


def build_all_contracts(claim_engine) -> Dict[Tuple[str, str], CapabilityContract]:
    """15.3.2: convert every ClaimGroup currently in the engine into a
    contract. Read-only over claim_engine.groups -- never mutates it."""
    out = {}
    for key, group in claim_engine.groups.items():
        c = build_contract(group)
        if c is not None:
            out[key] = c
    return out


def report(contracts: Dict[Tuple[str, str], CapabilityContract]) -> str:
    lines = ["%-40s %-20s %-14s %s" % ("target", "operation", "status", "causal_outcome")]
    for (cdid, cond), c in sorted(contracts.items()):
        lines.append("%-40s %-20s %-14s %s" % (
            c.target[:40], c.allowed_operation, c.status, c.verified.get("causal")))
    counts = {}
    for c in contracts.values():
        counts[c.status] = counts.get(c.status, 0) + 1
    lines.append("")
    lines.append("=== SUMMARY ===")
    for status in (CAUSAL_VERIFIED, STRUCTURAL_ONLY, NEGATIVE_EVIDENCE, UNSUPPORTED, BLOCKED_CONTRADICTED):
        if status in counts:
            lines.append("  %-20s %d" % (status, counts[status]))
    lines.append("  %-20s %d" % ("TOTAL", len(contracts)))
    return "\n".join(lines)
