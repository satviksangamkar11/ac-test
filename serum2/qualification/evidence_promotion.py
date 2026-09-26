"""Generic empirical-evidence -> CapabilityContract promotion.

Consumes evidence already collected by candidate_binding_qualifier.py and the
DawDreamer causal/structural probe scripts
(parameter_characterization/binding_evidence/*.json). Both of those producers
are documented as evidence-only: candidate_binding_qualifier.py's own
docstring/README.md entry says explicitly "it creates no CapabilityContract.
A binding is not a contract." This module fills exactly that gap.

It constructs the SAME CapabilityContract/ExecutionBinding dataclasses
capability_contract.py already defines -- there is no second contract model.
It deliberately does NOT go through ClaimGroup/build_contract(): this
evidence never ran the ClaimDefinition/CausalMeasurement experiment
apparatus (audio-rendered causal measurement, breadth/coverage rules,
measurement cohorts) that build_contract() requires, and forcing it through
that path would mean fabricating fields nothing here actually measured.
capability_contract.py's own docstring declares a strict one-directional
"ClaimGroup -> CapabilityContract" layering invariant for THAT module, which
is why this constructor lives here instead of inside it.

Authority boundary: this module ONLY constructs a CapabilityContract. It
never calls serum2.evidence.admission.admit(), never mutates Serum, never
marks anything "admitted", never touches target/route resolution. The
existing admission.admit() remains the sole decision point.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from serum2.evidence.capability_contract import (
    CapabilityContract, ExecutionBinding, STRUCTURAL_ONLY,
    MUTATE_BOOLEAN, MUTATE_NUMERIC, MUTATE_ENUM,
)
from serum2.evidence.canonical import digest
from serum2.producer.execution_epoch import installed_epoch
from serum2.reference.serum_atlas import get_control

# ---- explicit, exhaustive rejection vocabulary -- no evidence is silently
# filled in or guessed; every rejection names exactly what was missing/wrong ----
REJECT_MISSING_TARGET = "MISSING_TARGET"
REJECT_MISSING_EPOCH = "MISSING_EPOCH"
REJECT_EPOCH_MISMATCH = "EPOCH_MISMATCH"
REJECT_MISSING_BODY_PATH = "MISSING_BODY_PATH"
REJECT_MISSING_DOMAIN = "MISSING_DOMAIN"
REJECT_MISSING_VERIFICATION = "MISSING_VERIFICATION"
REJECT_RESTORATION_NOT_VERIFIED = "RESTORATION_NOT_VERIFIED"
REJECT_NO_ATLAS_IDENTITY = "NO_ATLAS_IDENTITY"
REJECT_INCONSISTENT_OPERAND_KIND = "INCONSISTENT_OPERAND_KIND"
REJECT_ATLAS_DOMAIN_CONFLICT = "ATLAS_DOMAIN_CONFLICT"
REJECT_UI_SEMANTICS_NOT_VERIFIED = "UI_SEMANTICS_NOT_VERIFIED"
REJECT_BAD_PARAMETER_CONTRACT = "BAD_PARAMETER_CONTRACT"

_VERIFIED_STATUSES = {"BINDING_VERIFIED", "STRUCTURAL_VERIFIED"}
_ATLAS_KIND_TO_OPERAND = {  # LEGACY path only -- generic widget-type -> operand-kind reference data, no per-control branching
    "toggle": MUTATE_BOOLEAN, "continuous": MUTATE_NUMERIC, "enum": MUTATE_ENUM,
    "knob": MUTATE_NUMERIC, "stepper": MUTATE_NUMERIC, "draggable_value": MUTATE_NUMERIC,
    "checkbox": MUTATE_BOOLEAN, "dropdown": MUTATE_ENUM, "nested_dropdown": MUTATE_ENUM,
}
_CONTRACT_KIND_TO_OPERAND = {"boolean": MUTATE_BOOLEAN, "numeric": MUTATE_NUMERIC, "enum": MUTATE_ENUM}
_BOUND_TOL = 1e-3


@dataclass(frozen=True)
class PromotionResult:
    promoted: bool
    reason: str
    contract: Optional[CapabilityContract] = None
    detail: str = ""


# ---- evidence field extraction -- branches on evidence SHAPE (which of the
# two existing producers wrote it), never on `target`'s identity. Every
# target of a given shape goes through the identical extraction. ----

def _target(evidence: Dict[str, Any]) -> Optional[str]:
    return evidence.get("target") or evidence.get("control_id")


def _epoch(evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    e = evidence.get("epoch") or evidence.get("serum_identity")
    if not isinstance(e, dict):
        return None
    sha = e.get("serum_sha256") or e.get("serum_binary_sha256")
    if not sha:
        return None
    return {"sha": sha}


def _status_verified(evidence: Dict[str, Any]) -> bool:
    status = evidence.get("status") or evidence.get("run_status")
    return status in _VERIFIED_STATUSES


def _restoration_verified(evidence: Dict[str, Any]) -> Optional[bool]:
    if "restoration_verified" in evidence:
        return evidence["restoration_verified"]
    restore = evidence.get("restore")
    if isinstance(restore, dict):
        return restore.get("verified")
    return None


def _leaf_diff(entries):
    """A single filtered body-diff entry may stop at a container boundary
    (e.g. path='Oscillator0.plainParams', after={'kParamPitch': 2.4}) rather
    than the leaf field itself -- descend one level when exactly one key
    changed. Returns (path, before, after) or (None, None, None)."""
    if not entries or len(entries) != 1:
        return None, None, None
    e = entries[0]
    path, before, after = e.get("path"), e.get("before"), e.get("after")
    if isinstance(after, dict) and len(after) == 1:
        k, v = next(iter(after.items()))
        b = before.get(k) if isinstance(before, dict) else None
        return "%s.%s" % (path, k), b, v
    return path, before, after


def _diff_entries(evidence: Dict[str, Any]):
    return evidence.get("body_diff_filtered") or evidence.get("observed_body_diff") or []


def _body_path(evidence: Dict[str, Any]) -> Optional[str]:
    if evidence.get("derived_body_path"):
        return evidence["derived_body_path"]
    path, _b, _a = _leaf_diff(_diff_entries(evidence))
    return path


def _accessor(evidence: Dict[str, Any]) -> Optional[str]:
    return evidence.get("accessor") or evidence.get("resolver_operation_id")


def _mutation_values(evidence: Dict[str, Any]) -> Tuple[Any, Any]:
    """Priority: (1) an explicit baseline/mutated pair already in the
    evidence's own body/display domain, (2) the body-diff leaf (also
    body-domain), (3) the raw host-normalized value -- last resort, only
    domain-correct when host normalization happens to coincide with the body
    domain (true for a plain 0/1 toggle, NOT true for e.g. a host-normalized
    pitch knob)."""
    if "baseline_value" in evidence and "mutated_value" in evidence:
        return evidence["baseline_value"], evidence["mutated_value"]
    _p, b, a = _leaf_diff(_diff_entries(evidence))
    if a is not None:
        return b, a
    host = evidence.get("host")
    if isinstance(host, dict) and "value_test" in host:
        return host.get("value_before"), host.get("value_test")
    return None, None



def _promote_from_parameter_contract(evidence, target, control, epoch, body_path, accessor, baseline_value, mutated_value, pc):
    """Operand kind and domain come from the evidenced PARAMETER CONTRACT (the swept domain + verified range + live-UI semantics),
    never from the Atlas UI widget type: a 'knob' is not thereby numeric and 'toggle_buttons' is not thereby boolean. The Atlas
    supplies identity only, and is checked AGAINST the evidence: a declared bound the evidence contradicts is a rejection (fix the
    Atlas first), not something to paper over."""
    kind = _CONTRACT_KIND_TO_OPERAND.get(pc.get("operand_kind"))
    dom = pc.get("domain")
    if kind is None or not isinstance(dom, dict):
        return PromotionResult(False, REJECT_BAD_PARAMETER_CONTRACT, detail="operand_kind=%r domain=%r" % (pc.get("operand_kind"), dom))
    ui = pc.get("ui_semantics") or {}
    if ui.get("status") != "VERIFIED":
        return PromotionResult(False, REJECT_UI_SEMANTICS_NOT_VERIFIED, detail="ui_semantics=%r" % (ui.get("status"),))
    if mutated_value is None:
        return PromotionResult(False, REJECT_MISSING_VERIFICATION, detail="no mutation value recorded")

    domain: Dict[str, Any] = {"kind": kind}
    if kind == MUTATE_BOOLEAN:
        if not (isinstance(mutated_value, bool) or mutated_value in (0, 1, 0.0, 1.0)):
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND, detail="boolean contract but mutation value %r" % (mutated_value,))
    elif kind == MUTATE_NUMERIC:
        lo, hi = dom.get("lo"), dom.get("hi")
        if lo is None or hi is None:
            return PromotionResult(False, REJECT_MISSING_DOMAIN, detail="numeric contract without verified lo/hi")
        if isinstance(mutated_value, bool) or not isinstance(mutated_value, (int, float)) or not (lo <= mutated_value <= hi):
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND, detail="numeric contract [%s,%s] but mutation value %r" % (lo, hi, mutated_value))
        a_lo, a_hi = getattr(control, "min_value", None), getattr(control, "max_value", None)
        if a_lo is not None and a_hi is not None and (abs(a_lo - lo) > _BOUND_TOL * max(1.0, abs(lo)) or abs(a_hi - hi) > _BOUND_TOL * max(1.0, abs(hi))):
            return PromotionResult(False, REJECT_ATLAS_DOMAIN_CONFLICT,
                                   detail="Atlas declares [%s,%s], evidence verified [%s,%s]" % (a_lo, a_hi, lo, hi))
        domain.update({"lo": lo, "hi": hi})
    else:
        labels = dom.get("enum_values")
        if not labels or not isinstance(mutated_value, str) or mutated_value not in labels:
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND, detail="enum contract %r but mutation value %r" % (labels, mutated_value))
        a_enum = tuple(getattr(control, "enum_values", None) or ())
        if a_enum and set(labels) - set(a_enum):
            return PromotionResult(False, REJECT_ATLAS_DOMAIN_CONFLICT, detail="evidence labels %r not all in Atlas enum %r" % (labels, a_enum))
        domain.update({"enum_values": list(labels)})

    binding = ExecutionBinding(
        mutation_type="SERUM_PRESET_STRUCTURAL", body_path=body_path, binding_source="evidence_promotion:%s" % target,
        binding_version=digest({"target": target, "body_path": body_path, "accessor": accessor}), resolver_operation_id=accessor)
    contract = CapabilityContract(
        target=target, allowed_operation=kind, status=STRUCTURAL_ONLY, prerequisites=(),
        verified={"load": "PASS", "persistence": "PASS", "causal": "NOT_RUN"}, measurement=None,
        scope={"tested_context_only": True, "domain": domain, "baseline_value": baseline_value, "mutated_value": mutated_value},
        provenance={"promoted_from": "serum2.qualification.evidence_promotion.promote_verified_evidence",
                    "evidence_epoch_sha": epoch["sha"], "atlas_control_type": control.control_type,
                    "operand_kind_source": "parameter_contract", "domain_source": pc.get("domain_source"), "ui_semantics": ui.get("evidence")},
        limitations=("STRUCTURAL_ONLY: proven via parameter-state diff (host/body write observed and restored), not an audio-measured causal effect",),
        execution_binding=binding)
    return PromotionResult(True, "PROMOTED", contract)

def promote_verified_evidence(evidence: Dict[str, Any]) -> PromotionResult:
    """Pure function of one evidence dict -> PromotionResult. No branch on
    `target`'s identity anywhere in this function; every per-control fact
    (operand kind, numeric bounds, enum vocabulary) comes from the Atlas's
    existing get_control() -- the same source candidate_binding_qualifier.py
    already uses for domain derivation -- never hardcoded here."""
    target = _target(evidence)
    if not target:
        return PromotionResult(False, REJECT_MISSING_TARGET)

    epoch = _epoch(evidence)
    if not epoch:
        return PromotionResult(False, REJECT_MISSING_EPOCH, detail=target)
    try:
        pinned = installed_epoch()
    except Exception as exc:
        return PromotionResult(False, REJECT_EPOCH_MISMATCH, detail="cannot resolve installed epoch: %r" % exc)
    if epoch["sha"] != pinned.binary_sha256:
        return PromotionResult(False, REJECT_EPOCH_MISMATCH,
                               detail="evidence sha %s != installed epoch sha %s" % (epoch["sha"], pinned.binary_sha256))

    if not _status_verified(evidence):
        return PromotionResult(False, REJECT_MISSING_VERIFICATION,
                               detail="status=%r is not a verified terminal status" % (evidence.get("status") or evidence.get("run_status")))

    if _restoration_verified(evidence) is not True:
        return PromotionResult(False, REJECT_RESTORATION_NOT_VERIFIED,
                               detail="restoration_verified=%r" % _restoration_verified(evidence))

    body_path = _body_path(evidence)
    accessor = _accessor(evidence)
    if not body_path and not accessor:
        return PromotionResult(False, REJECT_MISSING_BODY_PATH, detail=target)

    control = get_control(target)
    if control is None:
        return PromotionResult(False, REJECT_NO_ATLAS_IDENTITY, detail=target)

    baseline_value, mutated_value = _mutation_values(evidence)
    pc = evidence.get("parameter_contract")
    if pc is not None:
        return _promote_from_parameter_contract(evidence, target, control, epoch, body_path, accessor, baseline_value, mutated_value, pc)

    operand_kind = _ATLAS_KIND_TO_OPERAND.get(control.control_type)
    if operand_kind is None:
        return PromotionResult(False, REJECT_MISSING_DOMAIN,
                               detail="Atlas control_type=%r has no generic operand mapping" % control.control_type)

    if mutated_value is None:
        return PromotionResult(False, REJECT_MISSING_VERIFICATION, detail="no mutation value recorded")

    # Generic guard against the boolean-classified-as-numeric bug class: the
    # Atlas-declared operand kind, not the raw Python type of a stored float,
    # decides boolean semantics.
    if operand_kind == MUTATE_BOOLEAN:
        if isinstance(mutated_value, bool):
            pass
        elif isinstance(mutated_value, (int, float)) and mutated_value in (0, 1, 0.0, 1.0):
            pass
        else:
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND,
                                   detail="control_type=toggle but mutation value %r is not boolean-shaped" % mutated_value)
    elif operand_kind == MUTATE_NUMERIC:
        if isinstance(mutated_value, bool) or not isinstance(mutated_value, (int, float)):
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND,
                                   detail="control_type=continuous but mutation value %r is not numeric" % mutated_value)
        if control.min_value is None and control.max_value is None:
            return PromotionResult(False, REJECT_MISSING_DOMAIN, detail="continuous control has no Atlas-declared bounds")
    elif operand_kind == MUTATE_ENUM:
        if not isinstance(mutated_value, str):
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND,
                                   detail="control_type=enum but mutation value %r is not a string" % mutated_value)
        if control.enum_values and mutated_value not in control.enum_values:
            return PromotionResult(False, REJECT_INCONSISTENT_OPERAND_KIND,
                                   detail="mutation value %r not in Atlas enum_values %r" % (mutated_value, control.enum_values))

    domain: Dict[str, Any] = {"kind": operand_kind}
    if operand_kind == MUTATE_NUMERIC:
        domain.update({"lo": control.min_value, "hi": control.max_value})
    elif operand_kind == MUTATE_ENUM:
        domain.update({"enum_values": list(control.enum_values)})

    binding = ExecutionBinding(
        mutation_type="SERUM_PRESET_STRUCTURAL",
        body_path=body_path,
        binding_source="evidence_promotion:%s" % target,
        binding_version=digest({"target": target, "body_path": body_path, "accessor": accessor}),
        resolver_operation_id=accessor,
    )

    contract = CapabilityContract(
        target=target,
        allowed_operation=operand_kind,
        # Honest tier: this is proven parameter-state causal evidence (a
        # host/body write was observed and independently restored), not an
        # audio-rendered causal EFFECT_OBSERVED measurement -- this repo
        # reserves CAUSAL_VERIFIED for the latter (capability_contract.py's
        # own state-machine doc). Never upgraded past what was measured.
        status=STRUCTURAL_ONLY,
        prerequisites=(),
        verified={"load": "PASS", "persistence": "PASS", "causal": "NOT_RUN"},
        measurement=None,
        scope={
            "tested_context_only": True,
            "domain": domain,
            "baseline_value": baseline_value,
            "mutated_value": mutated_value,
        },
        provenance={
            "promoted_from": "serum2.qualification.evidence_promotion.promote_verified_evidence",
            "evidence_epoch_sha": epoch["sha"],
            "atlas_control_type": control.control_type,
        },
        limitations=(
            "STRUCTURAL_ONLY: proven via parameter-state diff (host/body write "
            "observed and restored), not an audio-measured causal effect",
        ),
        execution_binding=binding,
    )
    return PromotionResult(True, "PROMOTED", contract)
