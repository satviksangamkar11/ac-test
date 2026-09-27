"""Regression test for the generic accessor-derivation fix in serum2.qualification.evidence_promotion.

Root cause (found by independently re-verifying a cross-session claim about env1.attack.json against
the actual committed repository state, not trusting the claim): promote_verified_evidence() accepted
an explicit "accessor"/"resolver_operation_id" key from raw evidence, but never derived one when
absent -- so every promoted-evidence contract whose source JSON lacked that key (203 of the loaded
promoted-evidence corpus; 185 of them 'field'-kind) got execution_binding.resolver_operation_id=None.
authorized_state_compiler._validate() requires this accessor to equal the state-ledger op's own
reconstructed "<list>[<index>].<field>" string for ANY field-kind binding -- so every one of those 185
targets could reach ADMITTED but could never reach compile_ops() SUCCESS, silently, with no test ever
having caught it (the existing Gate-A/Gate-B suites use serum2/qualification/binding_evidence, a
DIFFERENT, already-accessor-bearing evidence source for env1.attack -- so this gap was invisible there).

Fix: _accessor() now falls back to a GENERIC lookup in the same serum_mcp_binding_table.json
derive()/admit_rows() already trust, keyed by control_id (== this evidence's own `target`) -- never a
per-target branch, never guessed from body_path.
"""
from __future__ import annotations

import json

import pytest

from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.state_ledger import Row, derive, binding_table
from serum2.producer.state_admission import admit_rows
from serum2.execution.authorized_state_compiler import ops_from_rows, compile_ops
from serum2.qualification.evidence_promotion import promote_verified_evidence, _accessor_from_binding_table

# The exact production dirs producer_brain.py's module-level constants point to.
BINDING_DIR = "parameter_characterization/binding_evidence"
PROMOTED_DIR = "parameter_characterization/binding_evidence_mcp_exec_v1"


class TestAccessorFromBindingTable:
    def test_derives_env1_attack_accessor_from_the_real_binding_table(self):
        assert _accessor_from_binding_table("env1.attack") == "envelopes[0].attack"

    def test_returns_none_for_non_field_kind_control(self):
        controls = binding_table()["controls"]
        non_field = next((cid for cid, e in controls.items() if isinstance(e, dict) and e.get("kind") != "field"), None)
        if non_field is None:
            pytest.skip("no non-field-kind control in the current binding table")
        assert _accessor_from_binding_table(non_field) is None

    def test_returns_none_for_unknown_target(self):
        assert _accessor_from_binding_table("no.such.control.exists") is None

    def test_explicit_evidence_accessor_still_wins_over_derivation(self):
        """An evidence file that already names its own accessor must never be overridden by the
        generic fallback -- explicit, evidenced data always outranks a derived convenience value."""
        evidence = {
            "target": "env1.attack", "accessor": "explicit_value_from_evidence",
            "epoch": {"serum_sha256": EPOCH_2_0_23.binary_sha256}, "status": "STRUCTURAL_VERIFIED",
            "restoration_verified": True,
            "body_diff_filtered": [{"path": "Env0.plainParams.kParamAttack", "before": 0.0005, "after": 5.0}],
            "baseline_value": 0.0005, "mutated_value": 5.0,
        }
        result = promote_verified_evidence(evidence, trusted_epoch=EPOCH_2_0_23)
        assert result.promoted, result.reason
        assert result.contract.execution_binding.resolver_operation_id == "explicit_value_from_evidence"


class TestPromotedCorpusAccessorCoverage:
    """Scans the REAL, currently-committed promoted-evidence corpus (never a synthetic fixture) and
    proves every field-kind contract now has an accessor -- the exact corpus-wide check the accessor
    fix's own review demanded, not just a single-target spot check."""

    def test_every_field_kind_promoted_contract_has_an_accessor(self):
        reg = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=BINDING_DIR, promoted_evidence_dir=PROMOTED_DIR)
        controls = binding_table()["controls"]

        total_structural, field_kind, missing = 0, 0, []
        for target, c in reg.contracts.items():
            eb = c.execution_binding
            if eb is None or eb.mutation_type != "SERUM_PRESET_STRUCTURAL":
                continue
            total_structural += 1
            entry = controls.get(target)
            if not (isinstance(entry, dict) and entry.get("kind") == "field"):
                continue
            field_kind += 1
            if not eb.resolver_operation_id:
                missing.append(target)

        assert total_structural > 0, "setup: expected at least one SERUM_PRESET_STRUCTURAL contract"
        assert field_kind > 100, "setup: expected the bulk-causal corpus to contribute >100 field-kind contracts"
        assert missing == [], "field-kind contracts still missing an accessor (regression): %r" % missing

    def test_env1_attack_end_to_end_compile_ops_succeeds(self):
        """The exact chain a real orchestrator run exercises: derive -> admit_rows -> ops_from_rows ->
        compile_ops, from the real committed evidence, with a genuine non-empty compiled preset spec."""
        row = Row(control_id="env1.attack", value=5.0, unit="s", status="OBSERVED", control_type="fader",
                  source_ts=0.0, n_readings=1, changed_from_previous=False, context={})
        derive(row, tempo=120.0)
        assert row.terminal == "OPERATION_DERIVED", row.reason

        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=BINDING_DIR, promoted_evidence_dir=PROMOTED_DIR)
        assert row.admission == "ADMITTED", row.admission
        assert row.op["contract_binding"] == "envelopes[0].attack"

        ops = ops_from_rows([row], EPOCH_2_0_23)
        assert len(ops) == 1
        report = compile_ops(ops, "test", "regression: env1.attack accessor fix", EPOCH_2_0_23)
        assert report.status == "SUCCESS", report.missing
        assert report.spec["envelopes"] == [{"attack": 5.0}]
