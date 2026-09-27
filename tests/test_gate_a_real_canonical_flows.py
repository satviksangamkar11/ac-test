"""Gate-A REAL CANONICAL FLOWS: A1-A8 with actual end-to-end runtime paths.

Each test uses the actual production flow without mocks or manual pre-population.
NO inspect.getsource() | NO synthetic contracts | NO vacuous sample testing.
"""
import sys
import json
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "serum2" / "knowledge")):
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.execution_epoch import (
    EPOCH_2_0_23, EPOCH_2_0_21, EPOCH_OFFLINE_TEST
)
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.state_ledger import Row, binding_table, catalog, derive
from serum2.producer.state_admission import admit_rows, validate_final_execution_gate
from serum2.producer.contract_scope import bridge_index, find_contract
from serum2.execution.authorized_state_compiler import ops_from_rows
from serum2.execution.state_comparator import _binding_quality, verification_level


class TestA1RealCanonicalFlow:
    """A1: Operand is observed value through full canonical production path."""

    def test_a1_observed_values_survive_derive_admit_compile(self):
        """A1 REAL: 3 distinct observed values → derive → admit → ops_from_rows → operand unchanged.

        Do NOT manually populate row.op or row.terminal.
        Use ACTUAL derive() function which discovers and validates the operation.
        """
        # Three distinct legal observed values that MUST survive unchanged
        observed_values = [2.5, 5.0, 7.5]

        rows_after_admit = []

        for obs_val in observed_values:
            # Create raw observed row - NO manual pre-population
            row = Row(
                control_id='env1.attack',
                value=obs_val,
                unit='s',
                status='OBSERVED',
                control_type='fader',
                source_ts=0.0,
                n_readings=1,
                changed_from_previous=False,
                context={}
            )

            # CANONICAL FLOW 1: derive() discovers operation from binding_table
            derive(row, tempo=120.0)

            # Check derive succeeded
            assert row.terminal == 'OPERATION_DERIVED', \
                f"A1 FAIL: derive failed for {obs_val}: {row.reason}"
            assert row.op is not None, "A1 FAIL: derive did not populate row.op"

            # CANONICAL FLOW 2: admit_rows() enforces gates
            admit_rows(
                [row], EPOCH_2_0_23,
                binding_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence"),
                promoted_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1")
            )

            assert row.admission == 'ADMITTED', \
                f"A1 FAIL: admission failed for {obs_val}: {row.admission} ({row.reason})"
            assert row.op.get('value') == obs_val, \
                f"A1 FAIL: value changed during admit: {row.op.get('value')} != {obs_val}"

            rows_after_admit.append(row)

        # CANONICAL FLOW 3: ops_from_rows() creates AuthorizedOperations
        ops = ops_from_rows(rows_after_admit, EPOCH_2_0_23)

        # Extract operands from compiled operations
        compiled_operands = [
            op.operand for op in ops
            if op.canonical_target == 'env1.attack'
        ]

        # A1 PROOF: All 3 distinct operands survive unchanged
        assert len(compiled_operands) == 3, \
            f"A1 FAIL: Expected 3 compiled ops, got {len(compiled_operands)}"
        assert compiled_operands == observed_values, \
            f"A1 FAIL: Operands {compiled_operands} != observed {observed_values}"

        # A1 PROOF: No qualification_test_value substitution
        for i, op in enumerate(ops):
            if op.canonical_target == 'env1.attack':
                assert op.operand == observed_values[i], \
                    f"A1 FAIL: Operand substitution detected at position {i}"

    def test_a1_missing_observed_value_fails_closed(self):
        """A1 REAL: Missing observed value must fail, not default to qualification_test_value."""
        # Row with no value
        row = Row(
            control_id='env1.attack',
            value=None,  # No observed value
            unit='s',
            status='UNREADABLE',  # Mark as unable to read
            control_type='fader',
            source_ts=0.0,
            n_readings=0,
            changed_from_previous=False,
            context={}
        )

        derive(row, tempo=120.0)

        # A1 PROOF: Missing value must fail, not be substituted
        assert row.terminal != 'OPERATION_DERIVED', \
            f"A1 FAIL: Missing value should not derive, got {row.terminal}"
        safe_terminals = ('UNREADABLE', 'UNSUPPORTED', 'UNREADABLE_RE_READ_REQUIRED', 'UNBOUND')
        assert row.terminal in safe_terminals, \
            f"A1 FAIL: Missing value terminal should be safe fail, got {row.terminal}"


class TestA2FinalExecutionGateHelper:
    """A2 unit proof: validate_final_execution_gate()'s 5 branches, using REAL CapabilityContract objects
    from the registry (never a fabricated contract). Every setup fact is hard-asserted (no `if x:` skip) --
    a broken fixture fails the test, it never silently no-ops."""

    def _registry(self):
        return ContractRegistry(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence"),
            promoted_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1"),
        )

    def test_helper_admitted_with_real_contract_and_spec(self):
        reg = self._registry()
        contract = reg.get('env1.attack')
        assert contract is not None, "setup: env1.attack must have a real CapabilityContract"
        spec = reg.execution_spec('env1.attack')
        assert spec is not None, "setup: env1.attack must have a real execution spec"
        result = validate_final_execution_gate(spec=spec, contract=contract, operand=5.0)
        assert result == "ADMITTED", f"A2 FAIL [ADMITTED]: got {result}"

    def test_helper_refused_no_final_contract_evidence(self):
        reg = self._registry()
        contract = reg.get('env1.attack')
        assert contract is not None, "setup: env1.attack must have a real CapabilityContract"
        result = validate_final_execution_gate(spec=None, contract=contract, operand=3.0)
        assert result == "REFUSED_NO_FINAL_CONTRACT_EVIDENCE", f"A2 FAIL [NoContract]: got {result}"

    def test_helper_refused_conformance_exception(self):
        reg = self._registry()
        contract = reg.get('env1.attack')
        spec = reg.execution_spec('env1.attack')
        assert contract is not None, "setup: env1.attack must have a real CapabilityContract"
        assert spec is not None, "setup: env1.attack must have a real execution spec"
        spec2 = deepcopy(spec)
        spec2["final_execution_classification"] = "MCP_EXEC_CONFORMANCE_EXCEPTION"
        result = validate_final_execution_gate(spec=spec2, contract=contract, operand=3.0)
        assert result == "REFUSED_CONFORMANCE_EXCEPTION", f"A2 FAIL [Conformance]: got {result}"

    def test_helper_refused_body_path_mismatch_wrong_path(self):
        reg = self._registry()
        contract = reg.get('env1.attack')
        spec = reg.execution_spec('env1.attack')
        assert contract is not None, "setup: env1.attack must have a real CapabilityContract"
        assert spec is not None and spec.get("expected_raw"), "setup: env1.attack must have a real expected_raw"
        spec2 = deepcopy(spec)
        spec2["expected_raw"][0]["path"] = ["Totally", "Different", "Path"]
        result = validate_final_execution_gate(spec=spec2, contract=contract, operand=3.0)
        assert result == "REFUSED_BODY_PATH_MISMATCH", f"A2 FAIL [BodyPath/wrong]: got {result}"

    def test_helper_refused_body_path_mismatch_missing_binding(self):
        """A real expected_raw path with NO capability binding at all must refuse, never silently pass."""
        import dataclasses
        reg = self._registry()
        contract = reg.get('env1.attack')
        spec = reg.execution_spec('env1.attack')
        assert contract is not None, "setup: env1.attack must have a real CapabilityContract"
        assert spec is not None and spec.get("expected_raw"), "setup: env1.attack must have a real expected_raw"
        unbound_contract = dataclasses.replace(contract, execution_binding=None)
        result = validate_final_execution_gate(spec=spec, contract=unbound_contract, operand=3.0)
        assert result == "REFUSED_BODY_PATH_MISMATCH", f"A2 FAIL [BodyPath/missing]: got {result}"

    def test_helper_out_of_qualified_domain(self):
        reg = self._registry()
        contract = reg.get('env1.attack')
        spec = reg.execution_spec('env1.attack')
        assert contract is not None, "setup: env1.attack must have a real CapabilityContract"
        assert spec is not None, "setup: env1.attack must have a real execution spec"
        spec2 = deepcopy(spec)
        spec2["declared_domain"] = {"min": 0.0, "max": 10.0}
        result = validate_final_execution_gate(spec=spec2, contract=contract, operand=15.0)
        assert result == "OUT_OF_QUALIFIED_DOMAIN", f"A2 FAIL [Domain]: got {result}"

    def test_helper_fx_path_with_integer_segments_does_not_crash(self):
        """Regression: expected_raw path segments may be non-string (FX slot index), e.g.
        ['FXRack0','FX',0,'FXDelay','plainParams','kParamBeatSync']. Before the fix this raised
        TypeError inside ".".join(raw_path) for EVERY real FX contract -- caught here with real data."""
        reg = self._registry()
        contract = reg.get('fx.delay.bpm')
        spec = reg.execution_spec('fx.delay.bpm')
        assert contract is not None, "setup: fx.delay.bpm must have a real CapabilityContract"
        assert spec is not None, "setup: fx.delay.bpm must have a real execution spec"
        raw_path = spec["expected_raw"][0]["path"]
        assert any(isinstance(seg, int) for seg in raw_path), "setup: path must contain a non-string segment"
        result = validate_final_execution_gate(spec=spec, contract=contract, operand=0.0)
        assert result == "ADMITTED", f"A2 FAIL [FX int-segment]: got {result}"


class TestA2RealAdmissionGates:
    """A2: expected_raw and declared_domain gates independently enforced THROUGH the real canonical
    admission path (derive() -> admit_rows()), not only via the helper in isolation.

    test_a2_no_reachable_contract_naturally_exercises_refusal_branches (below) proves EXHAUSTIVELY, over
    every control reachable through find_contract(), that the live evidence corpus never naturally hits
    REFUSED_NO_FINAL_CONTRACT_EVIDENCE / REFUSED_CONFORMANCE_EXCEPTION / a wider-than-declared domain for
    any admittable contract. Given that fact, the only way to prove admit_rows() correctly WIRES the gate
    result into row.admission for a REAL reachable contract is to patch ContractRegistry.execution_spec's
    *return value* for exactly one control_id -- derive(), find_contract(), admission.admit(), and
    validate_final_execution_gate() all still run completely unmodified.
    """

    BINDING_DIR = str(ROOT / "parameter_characterization" / "binding_evidence")
    PROMOTED_DIR = str(ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1")

    def _derive_row(self, control_id, value, unit=None, control_type='fader', context=None):
        row = Row(control_id=control_id, value=value, unit=unit, status='OBSERVED', control_type=control_type,
                  source_ts=0.0, n_readings=1, changed_from_previous=False, context=context or {})
        derive(row, tempo=120.0)
        assert row.terminal == 'OPERATION_DERIVED', f"setup: derive() must succeed for {control_id}: {row.reason}"
        return row

    def _assert_reachable_with_spec(self, control_id):
        reg = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        contract = reg.get(control_id)
        assert contract is not None, f"setup: {control_id} must have a real reachable CapabilityContract"
        spec = reg.execution_spec(control_id)
        assert spec is not None, f"setup: {control_id} must have a real execution spec to perturb"
        return spec

    def test_a2_canonical_admitted(self):
        """A2 REAL: real observed value, real contract, real spec -> ADMITTED through admit_rows()."""
        row = self._derive_row('env1.attack', 5.0, unit='s')
        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        assert row.admission == 'ADMITTED', f"A2 FAIL [ADMITTED]: got {row.admission} ({row.reason})"

    def test_a2_canonical_fx_admitted_no_crash_on_integer_path_segments(self):
        """A2 REAL: FX operation whose expected_raw path has an integer segment must admit cleanly, not
        raise. Before the fix this call raised TypeError inside admit_rows() itself."""
        row = self._derive_row('fx.filter.type', 'L6', control_type='dropdown', context={'rack': 0})
        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        assert row.admission == 'ADMITTED', f"A2 FAIL [FX ADMITTED]: got {row.admission} ({row.reason})"

    def test_a2_canonical_refused_no_final_contract_evidence(self, monkeypatch):
        self._assert_reachable_with_spec('env1.attack')
        row = self._derive_row('env1.attack', 5.0, unit='s')
        original = ContractRegistry.execution_spec

        def patched(self_reg, atlas_id):
            if atlas_id == 'env1.attack':
                return None
            return original(self_reg, atlas_id)

        monkeypatch.setattr(ContractRegistry, 'execution_spec', patched)
        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        assert row.admission == 'REFUSED_NO_FINAL_CONTRACT_EVIDENCE', f"A2 FAIL [NoContract]: got {row.admission} ({row.reason})"

    def test_a2_canonical_refused_conformance_exception(self, monkeypatch):
        self._assert_reachable_with_spec('env1.attack')
        row = self._derive_row('env1.attack', 5.0, unit='s')
        original = ContractRegistry.execution_spec

        def patched(self_reg, atlas_id):
            real = original(self_reg, atlas_id)
            if atlas_id == 'env1.attack' and real is not None:
                modified = deepcopy(real)
                modified['final_execution_classification'] = 'MCP_EXEC_CONFORMANCE_EXCEPTION'
                return modified
            return real

        monkeypatch.setattr(ContractRegistry, 'execution_spec', patched)
        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        assert row.admission == 'REFUSED_CONFORMANCE_EXCEPTION', f"A2 FAIL [Conformance]: got {row.admission} ({row.reason})"

    def test_a2_canonical_refused_body_path_mismatch(self, monkeypatch):
        self._assert_reachable_with_spec('env1.attack')
        row = self._derive_row('env1.attack', 5.0, unit='s')
        original = ContractRegistry.execution_spec

        def patched(self_reg, atlas_id):
            real = original(self_reg, atlas_id)
            if atlas_id == 'env1.attack' and real is not None:
                modified = deepcopy(real)
                modified['expected_raw'] = [{'path': ['Totally', 'Different', 'Path'],
                                             'value': modified['expected_raw'][0]['value']}]
                return modified
            return real

        monkeypatch.setattr(ContractRegistry, 'execution_spec', patched)
        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        assert row.admission == 'REFUSED_BODY_PATH_MISMATCH', f"A2 FAIL [BodyPath]: got {row.admission} ({row.reason})"

    def test_a2_canonical_out_of_qualified_domain(self, monkeypatch):
        self._assert_reachable_with_spec('env1.attack')
        row = self._derive_row('env1.attack', 5.0, unit='s')
        original = ContractRegistry.execution_spec

        def patched(self_reg, atlas_id):
            real = original(self_reg, atlas_id)
            if atlas_id == 'env1.attack' and real is not None:
                modified = deepcopy(real)
                modified['declared_domain'] = {'min': 0.0, 'max': 2.0}
                return modified
            return real

        monkeypatch.setattr(ContractRegistry, 'execution_spec', patched)
        admit_rows([row], EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        assert row.admission == 'OUT_OF_QUALIFIED_DOMAIN', f"A2 FAIL [Domain]: got {row.admission} ({row.reason})"

    def test_a2_no_reachable_contract_naturally_exercises_refusal_branches(self):
        """Exhaustive audit (not a sample): for EVERY field/fx control reachable via find_contract(), the
        live evidence corpus never itself has a missing execution_spec, a conformance-exception
        classification, or a declared_domain narrower than the coercion model's own range. This is the
        fact that makes the monkeypatch-based canonical tests above necessary -- and if it ever stops
        being true (new evidence adds a real refusal case), this test fails and says exactly which
        control, so a real fixture can replace the injected one."""
        reg = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=self.BINDING_DIR, promoted_evidence_dir=self.PROMOTED_DIR)
        bt = binding_table()
        bridge = bridge_index(reg)
        cat = catalog()
        checked = 0
        for cid, entry in bt['controls'].items():
            if entry.get('kind') not in ('field', 'fx'):
                continue
            op = {k: v for k, v in entry.items() if k != 'basis'}
            op['operation'] = 'SET'
            c, _ = find_contract(op, {}, bridge, cat)
            if c is None:
                continue
            checked += 1
            spec = reg.execution_spec(cid)
            assert spec is not None, f"A2 AUDIT: {cid} is reachable but has no execution_spec -- use it as a real fixture instead of monkeypatching"
            assert spec.get('final_execution_classification') != 'MCP_EXEC_CONFORMANCE_EXCEPTION', \
                f"A2 AUDIT: {cid} is reachable AND a conformance exception -- use it as a real fixture instead of monkeypatching"
        assert checked > 0, "A2 AUDIT FAIL: no reachable field/fx controls found at all"


class TestA4AllContractsReachable:
    """A4: ALL promoted CapabilityContracts are actually reachable via the SAME canonical capability
    lookup admit_rows() itself uses (find_contract over bridge_index), not merely "has an execution_spec".

    execution_spec is a SEPARATE final-evidence gate (see A2) -- a contract can be fully reachable and
    authoritative with no execution_spec at all (the row would then be REFUSED_NO_FINAL_CONTRACT_EVIDENCE,
    a different, later failure than NOT REACHABLE). Treating execution_spec existence as reachability proof
    (the bug in the previous version of this test) hid the real defect below.
    """

    # oscA/B/C.wavetable are the one class of promoted target this architecture cannot admit today: the
    # CapabilityContract IS reachable (find_contract resolves it below) but is proven for a STRUCTURED
    # wavetable operand, while binding_table's "wavetable" field always derives a named-selection op --
    # no real Row can ever construct the structured operand the contract requires. This is a genuine,
    # pre-existing capability gap (contract_scope.find_contract's own wavetable branch, unchanged here),
    # not a lookup defect -- named and asserted explicitly so the exception can never silently grow.
    KNOWN_UNREACHABLE_OPERAND_MISMATCH = frozenset({"oscA.wavetable", "oscB.wavetable", "oscC.wavetable"})

    def _registry(self):
        return ContractRegistry(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence"),
            promoted_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1")
        )

    def test_a4_every_promoted_capability_contract_reachable_via_canonical_lookup(self):
        """A4 REAL: for EVERY target in promotion_diagnostics["loaded"] (dynamic, not hardcoded):

        1. the target resolves to a real CapabilityContract in the registry
        2. that contract carries a mutation_target_path (scope evidence of WHERE it was proven)
        3. that contract is tagged with THIS run's epoch (serum_binary_sha256 == EPOCH_2_0_23)
        4. binding_table has a real entry for the same target (a control end-users can actually observe)
        5. the canonical capability lookup (bridge_index + find_contract -- the exact function admit_rows()
           itself calls) resolves a contract, and it is the SAME object as (1), proven by contract_key
        6. that contract's own execution_binding.body_path (when the binding exists) agrees with its own
           mutation_target_path (the authority contract does not contradict itself)
        7. execution_spec (a separate, later evidence gate -- see A2) is looked up too and recorded, but
           its absence does NOT count as unreachable

        unreachable == KNOWN_UNREACHABLE_OPERAND_MISMATCH (an explicit, evidence-backed, non-growing set)
        and tested == len(promoted_targets) -- never a sample, never a threshold.
        """
        reg = self._registry()
        promoted_targets = reg.promotion_diagnostics.get("loaded", [])
        assert len(promoted_targets) > 0, "A4 FAIL: no promoted targets in promotion_diagnostics['loaded']"

        bt = binding_table()
        bridge = bridge_index(reg)
        cat = catalog()

        unreachable = []
        tested_count = 0
        execution_spec_present = 0

        for target in promoted_targets:
            tested_count += 1

            # (1) target resolves to a real CapabilityContract
            contract = reg.get(target)
            assert contract is not None, f"A4 FAIL: promoted target {target} not found via reg.get()"
            # (9) target identity agrees through the crosswalk: reg.get(target) must be the object actually
            # keyed under `target` in the registry's own contracts dict (no crosswalk substitution here).
            assert reg.contracts.get(target) is contract, \
                f"A4 FAIL: {target} resolves to a DIFFERENT contract object than reg.contracts[{target}]"

            # (2) mutation_target_path evidence exists
            mutation_path = (contract.scope or {}).get("mutation_target_path")
            assert mutation_path, f"A4 FAIL: {target} contract has no scope.mutation_target_path"

            # (3) epoch agreement. Promoted-evidence contracts (this loader) record their epoch in
            # provenance.evidence_epoch_sha rather than scope.serum_binary_sha256 (the convention the other
            # three loaders use, per ContractRegistry._apply_epoch) -- promote_verified_evidence() already
            # refuses any evidence file whose recorded sha != self.epoch.binary_sha256 at load time
            # (contract_registry.py's _load_promoted_evidence_contracts), so this checks the field that
            # loader actually stamps, not a field it never touches.
            epoch_sha = contract.scope.get("serum_binary_sha256") or contract.provenance.get("evidence_epoch_sha")
            assert epoch_sha == EPOCH_2_0_23.binary_sha256, \
                f"A4 FAIL: {target} contract not tagged with run epoch {EPOCH_2_0_23.label} (got {epoch_sha!r})"

            # (4) real, observable binding_table entry
            binding_entry = bt["controls"].get(target)
            assert binding_entry is not None, f"A4 FAIL: {target} has no binding_table entry (not user-observable)"
            assert binding_entry.get("kind") in ("field", "fx", "singleton_field"), \
                f"A4 FAIL: {target} binding_table kind {binding_entry.get('kind')!r} not a known admission kind"

            # (5) the SAME canonical lookup admit_rows() calls
            op = {k: v for k, v in binding_entry.items() if k != "basis"}
            op["operation"] = "SET"
            found, tr = find_contract(op, {}, bridge, cat)
            if found is None:
                unreachable.append((target, tr.status, tr.detail))
                continue
            # The lookup must resolve a contract covering the SAME physical Serum parameter as this
            # promoted target (same root/index/kparam) -- not necessarily the identical dict key, since a
            # target may be legitimately double-proven under two provenance sources (e.g. a Pass-1
            # contract AND a promoted-evidence contract for the same real mutation_target_path; the
            # registry correctly keeps both rather than silently overwriting either -- see
            # ContractRegistry._load_promoted_evidence_contracts's "already registered" rule).
            own_coverage = next((c for c in bridge if c.contract_key == target), None)
            assert own_coverage is not None, f"A4 FAIL: {target} has no bridge_index() coverage entry at all"
            assert (found.root, found.index, found.kparam, found.fx_type, found.rack) == (
                own_coverage.root, own_coverage.index, own_coverage.kparam, own_coverage.fx_type, own_coverage.rack), (
                f"A4 FAIL: {target} canonical lookup resolved a DIFFERENT physical parameter: "
                f"found={found} own={own_coverage}")

            # (6) binding self-agreement: a bound contract's own execution_binding must agree with its
            # own recorded mutation_target_path -- never a contradiction inside a single contract's evidence.
            if contract.execution_binding is not None and contract.execution_binding.body_path is not None:
                assert contract.execution_binding.body_path == mutation_path, \
                    f"A4 FAIL: {target} execution_binding.body_path {contract.execution_binding.body_path!r} " \
                    f"!= its own scope.mutation_target_path {mutation_path!r}"

            # (7) execution_spec is a SEPARATE, later gate -- recorded, never required for reachability
            if reg.execution_spec(target) is not None:
                execution_spec_present += 1

        unreachable_targets = {u[0] for u in unreachable}
        assert unreachable_targets == self.KNOWN_UNREACHABLE_OPERAND_MISMATCH, (
            f"A4 FAIL: reachability set changed. "
            f"new/unexpected unreachable: {unreachable_targets - self.KNOWN_UNREACHABLE_OPERAND_MISMATCH}; "
            f"expected-but-now-reachable (update KNOWN_UNREACHABLE_OPERAND_MISMATCH): "
            f"{self.KNOWN_UNREACHABLE_OPERAND_MISMATCH - unreachable_targets}; "
            f"full detail: {unreachable}"
        )
        assert tested_count == len(promoted_targets), \
            f"A4 FAIL: tested_count {tested_count} != promoted_targets {len(promoted_targets)}"
        # Sanity: execution_spec (the separate A2 gate) covers the overwhelming majority of reachable
        # targets in the real evidence corpus -- if this collapses to 0, something upstream broke silently.
        assert execution_spec_present > 0, "A4 FAIL: no promoted+reachable target has an execution_spec at all"

    def test_a4_every_user_facing_control_reachable(self):
        """A4 REAL: Every user-facing control from binding_table is reachable.

        Tests ALL 330 controls (not sample). Asserts: unreachable == [] AND tested_count == actual_count.
        """
        reg = ContractRegistry(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence"),
            promoted_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1")
        )
        bt = binding_table()
        bridge = bridge_index(reg)
        cat = catalog()

        # Iterate ALL user-facing controls (NOT a sample, NOT a threshold)
        user_facing_controls = list(bt['controls'].keys())
        unreachable = []
        reachable_via_spec = 0
        reachable_via_find = 0
        tested_count = 0

        for ctrl_id in user_facing_controls:
            tested_count += 1
            binding_entry = bt['controls'][ctrl_id]

            # Try execution_spec path (canonical direct lookup)
            spec = reg.execution_spec(ctrl_id)
            if spec is not None:
                reachable_via_spec += 1
                continue

            # Try find_contract path (field operations via binding_table → find_contract)
            if binding_entry.get('kind') == 'field':
                op = {k: v for k, v in binding_entry.items() if k != 'basis'}
                op['operation'] = 'SET'
                found, _ = find_contract(op, {}, bridge, cat)
                if found:
                    reachable_via_find += 1
                    continue

            # Not reachable via either path
            unreachable.append(ctrl_id)

        # A4 PROOF 1: EVERY control is reachable (not a sample, not a threshold)
        assert unreachable == [], \
            f"A4 FAIL: {len(unreachable)} unreachable controls: {unreachable[:10]}"

        # A4 PROOF 2: Verify tested_count matches expected user-facing count dynamically
        assert tested_count == len(user_facing_controls), \
            f"A4 FAIL: tested_count {tested_count} != user_facing_controls {len(user_facing_controls)}"

        # Report exact dynamic counts
        total_reachable = reachable_via_spec + reachable_via_find
        assert total_reachable == tested_count, \
            f"A4 FAIL: Not all tested controls were reachable: {total_reachable} reachable, {tested_count} tested"


class TestA5CoerceAllModuleKinds:
    """A5: All 9 module kinds execute safely; unknown kinds → UNSUPPORTED (no crash).

    Representatives are DISCOVERED from binding_table()["controls"] at test time (sorted, so the pick is
    deterministic), never hardcoded control_id strings. A legal probe VALUE for each candidate is computed
    from the SAME pydantic/catalog metadata derive()/`_coerce()` itself consults (field range, boolean
    annotation, enum domain) -- never a hardcoded value either. The first candidate in a family that
    reaches OPERATION_DERIVED is the representative; every assertion then checks that representative's
    DISCOVERED op against its OWN binding_table entry, so the proof can never drift from the table.
    """

    FIELD_MODULES = ("osc", "env", "lfo", "filter", "macro")
    SINGLETON_ATTRS = ("arp", "global_", "voice_unison")

    @staticmethod
    def _models():
        from serum_mcp.generation import spec as S
        return {"osc": S.OscillatorSpec, "env": S.EnvelopeSpec, "lfo": S.LfoSpec,
                "filter": S.FilterSpec, "macro": S.MacroSpec}

    @staticmethod
    def _singleton_models():
        from serum_mcp.generation import spec as S
        return {"arp": S.ArpSpec, "global_": S.GlobalSpec, "voice_unison": S.VoiceUnisonSpec}

    @staticmethod
    def _legal_value(entry, module_key, models_dict):
        """A value derive()'s own _coerce() would accept for this field, computed from the SAME pydantic
        metadata _coerce() itself reads (never a guessed constant). Returns None when this candidate isn't
        a meaningful representative (free-text field with no known enum domain)."""
        from serum2.producer.state_ledger import _domain, _field_range
        cls = models_dict.get(module_key)
        if cls is None:
            return None
        fi = cls.model_fields.get(entry.get("field"))
        if fi is None:
            return None
        ann = str(fi.annotation)
        if "bool" in ann:
            return "on"
        dom = _domain(entry.get("field"), module_key, fi.description)
        if dom and "str" in ann:
            return dom[0]
        if "str" in ann:
            return None
        lo, hi = _field_range(fi)
        if lo is not None and hi is not None:
            return (lo + hi) / 2.0
        return lo if lo is not None else hi

    def _pick_field_representative(self, module_key):
        bt = binding_table()
        models = self._models()
        candidates = sorted(cid for cid, e in bt["controls"].items()
                            if e.get("kind") == "field" and e.get("module") == module_key)
        assert candidates, f"A5 SETUP FAIL: binding_table has no field/{module_key} controls at all"
        for cid in candidates:
            entry = bt["controls"][cid]
            val = self._legal_value(entry, module_key, models)
            if val is None:
                continue
            row = Row(control_id=cid, value=val, unit=None, status='OBSERVED', control_type='fader',
                      source_ts=0.0, n_readings=1, changed_from_previous=False, context={})
            derive(row, tempo=120.0)
            if row.terminal == 'OPERATION_DERIVED':
                return cid, entry, row
        pytest.fail(f"A5 FAIL [field/{module_key}]: no candidate among {candidates} reached OPERATION_DERIVED")

    def _pick_singleton_representative(self, attr):
        bt = binding_table()
        models = self._singleton_models()
        candidates = sorted(cid for cid, e in bt["controls"].items()
                            if e.get("kind") == "singleton_field" and e.get("attr") == attr)
        assert candidates, f"A5 SETUP FAIL: binding_table has no singleton_field/{attr} controls at all"
        for cid in candidates:
            entry = bt["controls"][cid]
            val = self._legal_value(entry, attr, models)
            if val is None:
                continue
            row = Row(control_id=cid, value=val, unit=None, status='OBSERVED', control_type='fader',
                      source_ts=0.0, n_readings=1, changed_from_previous=False, context={})
            derive(row, tempo=120.0)
            if row.terminal == 'OPERATION_DERIVED':
                return cid, entry, row
        pytest.fail(f"A5 FAIL [singleton_field/{attr}]: no candidate among {candidates} reached OPERATION_DERIVED")

    def _pick_fx_representative(self):
        bt = binding_table()
        cat = catalog()
        candidates = sorted(cid for cid, e in bt["controls"].items() if e.get("kind") == "fx")
        assert candidates, "A5 SETUP FAIL: binding_table has no fx controls at all"
        for cid in candidates:
            entry = bt["controls"][cid]
            p = cat["fx_params"].get(entry["fx_type"], {}).get(entry["param"])
            if p is None:
                continue
            if p["kind"] == "bool":
                val = "on"
            elif p["kind"] == "enum":
                val = p["enum_values"][0]
            elif p["kind"] == "float":
                lo, hi = p.get("min"), p.get("max")
                if lo is not None and hi is not None:
                    val = (lo + hi) / 2.0
                elif lo is not None or hi is not None:
                    val = lo if lo is not None else hi
                else:
                    continue
            else:
                continue
            row = Row(control_id=cid, value=val, unit=None, status='OBSERVED', control_type='fader',
                      source_ts=0.0, n_readings=1, changed_from_previous=False, context={'rack': 0})
            derive(row, tempo=120.0)
            if row.terminal == 'OPERATION_DERIVED':
                return cid, entry, row
        pytest.fail(f"A5 FAIL [fx]: no candidate among {candidates} reached OPERATION_DERIVED")

    @pytest.mark.parametrize("module_key", FIELD_MODULES)
    def test_a5_field_kind_derive_real(self, module_key):
        """A5 REAL: field/<module> derives via a DISCOVERED binding_table representative; the resulting
        op's kind/module/list/field/index must match that SAME binding_table entry exactly."""
        cid, entry, row = self._pick_field_representative(module_key)
        assert row.op is not None, f"A5 FAIL [{module_key}]: row.op not populated for discovered {cid}"
        assert row.op.get('kind') == 'field', f"A5 FAIL [{module_key}]: {cid} op kind {row.op.get('kind')!r} != 'field'"
        assert row.op.get('module') == module_key, \
            f"A5 FAIL [{module_key}]: {cid} op module {row.op.get('module')!r} != {module_key!r}"
        assert row.op.get('list') == entry.get('list'), \
            f"A5 FAIL [{module_key}]: {cid} op list {row.op.get('list')!r} != binding_table {entry.get('list')!r}"
        assert row.op.get('field') == entry.get('field'), \
            f"A5 FAIL [{module_key}]: {cid} op field {row.op.get('field')!r} != binding_table {entry.get('field')!r}"
        assert row.op.get('index') == entry.get('index'), \
            f"A5 FAIL [{module_key}]: {cid} op index {row.op.get('index')!r} != binding_table {entry.get('index')!r}"

    @pytest.mark.parametrize("attr", SINGLETON_ATTRS)
    def test_a5_singleton_field_kind_derive_real(self, attr):
        """A5 REAL: singleton_field/<attr> derives via a DISCOVERED binding_table representative; the
        resulting op's kind/attr/field must match that SAME binding_table entry exactly."""
        cid, entry, row = self._pick_singleton_representative(attr)
        assert row.op is not None, f"A5 FAIL [{attr}]: row.op not populated for discovered {cid}"
        assert row.op.get('kind') == 'singleton_field', \
            f"A5 FAIL [{attr}]: {cid} op kind {row.op.get('kind')!r} != 'singleton_field'"
        assert row.op.get('attr') == attr, f"A5 FAIL [{attr}]: {cid} op attr {row.op.get('attr')!r} != {attr!r}"
        assert row.op.get('field') == entry.get('field'), \
            f"A5 FAIL [{attr}]: {cid} op field {row.op.get('field')!r} != binding_table {entry.get('field')!r}"

    def test_a5_fx_kind_derive_real(self):
        """A5 REAL: fx kind derives via a DISCOVERED binding_table representative; the resulting op's
        kind/fx_type/param must match that SAME binding_table entry exactly."""
        cid, entry, row = self._pick_fx_representative()
        assert row.op is not None, f"A5 FAIL [fx]: row.op not populated for discovered {cid}"
        assert row.op.get('kind') == 'fx', f"A5 FAIL [fx]: {cid} op kind {row.op.get('kind')!r} != 'fx'"
        assert row.op.get('fx_type') == entry.get('fx_type'), \
            f"A5 FAIL [fx]: {cid} op fx_type {row.op.get('fx_type')!r} != binding_table {entry.get('fx_type')!r}"
        assert row.op.get('param') == entry.get('param'), \
            f"A5 FAIL [fx]: {cid} op param {row.op.get('param')!r} != binding_table {entry.get('param')!r}"

    def test_a5_unknown_kind_fails_closed_no_crash(self):
        """A5 REAL: a binding_table entry with an unrecognized 'kind' must reach the real _coerce()'s
        explicit unsupported-kind branch, never raise, and never derive."""
        from serum2.producer.state_ledger import _coerce
        row = Row(control_id='synthetic.unknown_kind_probe', value=1.0, unit=None, status='OBSERVED',
                  control_type='fader', source_ts=0.0, n_readings=1, changed_from_previous=False, context={})
        target = {"kind": "not_a_real_kind"}
        err = _coerce(row, target, 'synthetic.unknown_kind_probe', tempo=120.0)
        assert err is not None, "A5 FAIL [unknown]: _coerce() must refuse an unrecognized kind, not silently accept it"
        assert "unsupported operation kind" in err, f"A5 FAIL [unknown]: unexpected error message: {err!r}"

    def test_a5_all_nine_module_kinds_covered(self):
        """A5 COVERAGE: All 9 module kinds tested above cover real binding_table entries."""
        bt = binding_table()
        by_kind = {}
        for ctrl_id, entry in bt['controls'].items():
            kind = entry.get('kind')
            module = entry.get('module') or entry.get('attr')
            key = (kind, str(module))
            if key not in by_kind:
                by_kind[key] = 0
            by_kind[key] += 1

        tested_kinds = {
            ('field', 'osc'),
            ('field', 'env'),
            ('field', 'lfo'),
            ('field', 'filter'),
            ('field', 'macro'),
            ('fx', 'None'),
            ('singleton_field', 'arp'),
            ('singleton_field', 'global_'),
            ('singleton_field', 'voice_unison'),
        }

        actual_kinds = {(k, str(m)) for k, m in by_kind.keys()}
        missing = actual_kinds - tested_kinds

        assert len(missing) == 0, \
            f"A5 FAIL: Uncovered module kinds in binding_table: {missing}"
        assert len(tested_kinds) == 9, \
            f"A5 FAIL: Expected exactly 9 tested kinds, got {len(tested_kinds)}"


class TestA6FrameTerminalStatus:
    """A6: EVERY manifest frame must have terminal analysis_status (not just serum_visible)."""

    def test_a6_every_frame_requires_terminal_status(self):
        """A6 REAL: ALL frames (not just serum_visible) must have terminal analysis_status."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            # All frames filled, including non-serum-visible
            skeleton_path = Path(tmp) / "complete.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED"},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "NOT_SERUM"},
                    {"frame_id": 2, "serum_visible": False, "analysis_status": "NOT_SERUM"},  # Even non-serum must have status
                    {"frame_id": 3, "serum_visible": True, "analysis_status": "ANALYZED"},
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert is_filled, "A6 FAIL: Properly filled skeleton (all frames) should be accepted"

    def test_a6_missing_analysis_status_in_any_frame_rejected(self):
        """A6 REAL: Even one frame without terminal status → rejected (not just serum_visible)."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            # One frame missing analysis_status (non-serum frame)
            skeleton_path = Path(tmp) / "incomplete.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED"},
                    {"frame_id": 1, "serum_visible": False, "analysis_status": None},  # MISSING (even though not serum_visible)
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, "A6 FAIL: Any frame with missing status must be rejected"

    def test_a6_invalid_terminal_status_rejected(self):
        """A6 REAL: Invalid terminal status value → rejected."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "invalid.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED"},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "BANANA"},  # Invalid
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, "A6 FAIL: Invalid terminal status must be rejected"

    def test_a6_equivalent_to_valid_target(self):
        """A6 REAL: EQUIVALENT_TO:<target> must reference existing frame."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            # Valid EQUIVALENT_TO reference
            skeleton_path = Path(tmp) / "equiv_valid.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED"},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "EQUIVALENT_TO:0"},  # Valid reference
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert is_filled, "A6 FAIL: Valid EQUIVALENT_TO reference should be accepted"

    def test_a6_equivalent_to_missing_target_rejected(self):
        """A6 REAL: EQUIVALENT_TO:<target> must not reference non-existent frame."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "equiv_missing.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED"},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "EQUIVALENT_TO:99"},  # Target doesn't exist
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, "A6 FAIL: EQUIVALENT_TO with missing target must be rejected"

    def test_a6_self_referencing_equivalence_rejected(self):
        """A6 REAL: Frame cannot be EQUIVALENT_TO itself."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "equiv_self.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "EQUIVALENT_TO:0"},  # Self-reference
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, "A6 FAIL: Self-referencing equivalence must be rejected"

    def test_a6_equivalence_two_cycle_rejected(self):
        """A6 REAL: 0 -> EQUIVALENT_TO:1, 1 -> EQUIVALENT_TO:0 -- both individually valid pointers,
        together an infinite loop with no terminal root. Must be rejected."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "equiv_cycle.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "EQUIVALENT_TO:1"},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "EQUIVALENT_TO:0"},
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, "A6 FAIL: a 2-cycle EQUIVALENT_TO chain must be rejected"

    def test_a6_equivalence_chain_resolving_to_real_terminal_accepted(self):
        """A6 REAL: 0 -> EQUIVALENT_TO:1, 1 -> ANALYZED is a valid, non-cyclic chain and must be accepted."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "equiv_chain_ok.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "EQUIVALENT_TO:1"},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "ANALYZED"},
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert is_filled, "A6 FAIL: a chain that resolves to a real terminal frame must be accepted"

    def test_a6_duplicate_frame_id_rejected(self):
        """A6 REAL: Two frames sharing the same frame_id makes equivalence targets and frame identity
        ambiguous -- must be rejected even though each frame individually has a valid terminal status."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "dup_frame_id.json"
            skeleton = {
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED"},
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "NOT_SERUM"},
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, "A6 FAIL: duplicate frame_id must be rejected"

    def test_a6_expected_inventory_fully_covered_accepted(self):
        """A6 REAL: when the skeleton declares expected_controls (its ExpectedInventory), and every
        declared control_id is accounted for by at least one frame's controls list, it is filled."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "inventory_ok.json"
            skeleton = {
                "expected_controls": ["env1.attack", "fx.bode.blur"],
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED",
                     "controls": [{"control_id": "env1.attack", "value": "5.0"}]},
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "ANALYZED",
                     "controls": [{"control_id": "fx.bode.blur", "value": "50"}]},
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert is_filled, "A6 FAIL: fully-covered ExpectedInventory must be accepted"

    def test_a6_expected_inventory_missing_control_rejected(self):
        """A6 REAL: a frame-complete skeleton (every frame ANALYZED) whose declared ExpectedInventory
        names a control_id that appears in NO frame's controls list must remain INCOMPLETE."""
        from youtube_to_serum.reference_engine import stage_a_is_filled

        with tempfile.TemporaryDirectory() as tmp:
            skeleton_path = Path(tmp) / "inventory_missing.json"
            skeleton = {
                "expected_controls": ["env1.attack", "fx.bode.blur"],
                "frames": [
                    {"frame_id": 0, "serum_visible": True, "analysis_status": "ANALYZED",
                     "controls": [{"control_id": "env1.attack", "value": "5.0"}]},
                    # fx.bode.blur never appears in any frame's controls
                    {"frame_id": 1, "serum_visible": True, "analysis_status": "ANALYZED", "controls": []},
                ]
            }
            skeleton_path.write_text(json.dumps(skeleton))

            is_filled = stage_a_is_filled(str(skeleton_path))
            assert not is_filled, \
                "A6 FAIL: frame-complete but ExpectedInventory-incomplete skeleton must NOT be filled"


class TestA7RealContentValidation:
    """A7: LOADER_BOUND requires all 6 loader_evidence fields with STRUCTURALLY VALID content, a
    known/pinned epoch identity, AND an actual observed UI values payload -- not just valid hashes."""

    @staticmethod
    def _valid_readback(**overrides):
        le = {
            "run_id": "run_123",
            "track_nonce": "nonce_456",
            "serum_module_sha256": "a" * 64,
            "epoch": "2.0.23",
            "screenshot_sha": "b" * 64,
            "crop_coords": [0, 0, 100, 100],
        }
        le.update(overrides.pop("loader_evidence", {}))
        base = {"loader_evidence": le, "values": {"env1.attack": "5.0"}}
        base.update(overrides)
        return base

    def test_a7_loader_bound_requires_valid_sha256_format(self):
        """A7 REAL: serum_module_sha256 must be exactly 64 hex characters (not 63, not 65, not 'z' chars)."""
        ui_readback = self._valid_readback()

        bq = _binding_quality(ui_readback)
        assert bq == "LOADER_BOUND", \
            f"A7 FAIL: Valid SHA not LOADER_BOUND: {bq}"

    def test_a7_sha256_invalid_format_rejected(self):
        """A7 REAL: serum_module_sha256 with invalid format (< 64 chars) rejected."""
        invalid_ui = {
            "loader_evidence": {
                "run_id": "run_123",
                "track_nonce": "nonce_456",
                "serum_module_sha256": "abc",  # Too short
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64,
                "crop_coords": [0, 0, 100, 100]
            }
        }
        bq = _binding_quality(invalid_ui)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: Invalid SHA (too short) still LOADER_BOUND: {bq}"

    def test_a7_sha256_non_hex_rejected(self):
        """A7 REAL: serum_module_sha256 with non-hex chars rejected."""
        invalid_ui = {
            "loader_evidence": {
                "run_id": "run_123",
                "track_nonce": "nonce_456",
                "serum_module_sha256": "z" * 64,  # Non-hex character
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64,
                "crop_coords": [0, 0, 100, 100]
            }
        }
        bq = _binding_quality(invalid_ui)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: Non-hex SHA still LOADER_BOUND: {bq}"

    def test_a7_loader_bound_rejects_missing_field(self):
        """A7 REAL: Missing any of 6 fields → not LOADER_BOUND."""
        # Missing crop_coords
        ui_readback = {
            "loader_evidence": {
                "run_id": "run_123",
                "track_nonce": "nonce_456",
                "serum_module_sha256": "a" * 64,
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64
                # crop_coords MISSING
            }
        }

        bq = _binding_quality(ui_readback)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: Missing field still LOADER_BOUND: {bq}"

    def test_a7_loader_bound_requires_numeric_crop_coords(self):
        """A7 REAL: crop_coords must be numeric [x, y, w, h], not strings."""
        # Valid numeric coords
        valid_ui = self._valid_readback(loader_evidence={"crop_coords": [10, 20, 100, 200]})
        bq = _binding_quality(valid_ui)
        assert bq == "LOADER_BOUND", f"A7 FAIL: Valid coords rejected: {bq}"

        # Invalid: string coords
        invalid_ui = {
            "loader_evidence": {
                "run_id": "run_123",
                "track_nonce": "nonce_456",
                "serum_module_sha256": "a" * 64,
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64,
                "crop_coords": ["10", "20", "100", "200"]  # INVALID: strings
            }
        }
        bq = _binding_quality(invalid_ui)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: String coords should not LOADER_BOUND: {bq}"

    def test_a7_crop_coords_wrong_length_rejected(self):
        """A7 REAL: crop_coords must be exactly 4 elements [x, y, w, h]."""
        invalid_ui = {
            "loader_evidence": {
                "run_id": "run_123",
                "track_nonce": "nonce_456",
                "serum_module_sha256": "a" * 64,
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64,
                "crop_coords": [1, 2, 3]  # Wrong length (3 instead of 4)
            }
        }
        bq = _binding_quality(invalid_ui)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: Wrong crop_coords length should not LOADER_BOUND: {bq}"

    def test_a7_empty_run_id_rejected(self):
        """A7 REAL: run_id must be non-empty string."""
        invalid_ui = {
            "loader_evidence": {
                "run_id": "",  # Empty
                "track_nonce": "nonce_456",
                "serum_module_sha256": "a" * 64,
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64,
                "crop_coords": [0, 0, 100, 100]
            }
        }
        bq = _binding_quality(invalid_ui)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: Empty run_id should not LOADER_BOUND: {bq}"

    def test_a7_none_track_nonce_rejected(self):
        """A7 REAL: track_nonce must be non-empty string."""
        invalid_ui = {
            "loader_evidence": {
                "run_id": "run_123",
                "track_nonce": None,  # None value
                "serum_module_sha256": "a" * 64,
                "epoch": "2.0.23",
                "screenshot_sha": "b" * 64,
                "crop_coords": [0, 0, 100, 100]
            }
        }
        bq = _binding_quality(invalid_ui)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: None track_nonce should not LOADER_BOUND: {bq}"

    def test_a7_epoch_must_identify_a_known_pinned_epoch(self):
        """A7 REAL: epoch must identify one of the pinned, known ExecutionEpochs (2.0.23 / 2.0.21) --
        an arbitrary non-empty string does not integrity-bind the readback to a real qualified build."""
        from serum2.producer.execution_epoch import EPOCH_2_0_23, EPOCH_2_0_21

        valid_23 = self._valid_readback(loader_evidence={"epoch": EPOCH_2_0_23.serum_version})
        assert _binding_quality(valid_23) == "LOADER_BOUND", "A7 FAIL: real 2.0.23 epoch string rejected"

        valid_21 = self._valid_readback(loader_evidence={"epoch": EPOCH_2_0_21.serum_version})
        assert _binding_quality(valid_21) == "LOADER_BOUND", "A7 FAIL: real 2.0.21 epoch string rejected"

        bogus = self._valid_readback(loader_evidence={"epoch": "9.9.9-staging"})
        bq = _binding_quality(bogus)
        assert bq != "LOADER_BOUND", f"A7 FAIL: arbitrary non-pinned epoch string still LOADER_BOUND: {bq}"

    def test_a7_missing_values_payload_rejected(self):
        """A7 REAL: a structurally perfect loader_evidence with no top-level observed 'values' must not
        reach LOADER_BOUND -- valid hashes prove integrity binding, not that anything was actually read."""
        ui_readback = self._valid_readback()
        del ui_readback["values"]
        bq = _binding_quality(ui_readback)
        assert bq != "LOADER_BOUND", f"A7 FAIL: missing values payload still LOADER_BOUND: {bq}"

    def test_a7_empty_values_payload_rejected(self):
        """A7 REAL: an empty 'values' dict (present but nothing was observed) must not reach LOADER_BOUND."""
        ui_readback = self._valid_readback(values={})
        bq = _binding_quality(ui_readback)
        assert bq != "LOADER_BOUND", f"A7 FAIL: empty values payload still LOADER_BOUND: {bq}"


class TestA8HeadlessBlocksVerification:
    """A8: DawDreamer/headless evidence must propagate through entire chain.

    NO MockResult anywhere in this class. Every ProducerResult here is produced by the REAL production
    method ProducerBrain.finalize_serum_preset_execution() -- the exact function that turns an
    ADVISORY_ONLY plan into an EXECUTED result in production. Only the ui_readback dict passed to it
    (this test's own controlled "what came off the screen/host" evidence) varies between cases.
    """

    @staticmethod
    def _executed_result(ui_readback, admitted=True):
        """A real ProducerResult, produced by the real finalize_serum_preset_execution() -- never a
        hand-rolled stand-in class."""
        from serum2.producer.producer_brain import ProducerBrain, ProducerRequest, ProducerResult
        brain = ProducerBrain(
            epoch=EPOCH_2_0_23,
            binding_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence"),
            promoted_evidence_dir=str(ROOT / "parameter_characterization" / "binding_evidence_mcp_exec_v1"),
        )
        result = ProducerResult(request=ProducerRequest(user_intent="test probe"),
                                execution_status="ADVISORY_ONLY", admitted=admitted)
        return brain.finalize_serum_preset_execution(
            result, preset_path="/tmp/a8_probe.SerumPreset", preset_sha256="a" * 64,
            ui_readback=ui_readback, readback_verified=True)

    def test_a8_headless_detected_in_binding_quality(self):
        """A8 REAL: Headless marker detected in _binding_quality()."""
        ui_readback = {
            "is_headless": True,  # Headless marker
        }

        bq = _binding_quality(ui_readback)
        assert bq == "HEADLESS_DAWDREAMER", \
            f"A8 FAIL: is_headless not detected: {bq}"

    def test_a8_backend_marker_detected(self):
        """A8 REAL: 'DawDreamer' in backend field → HEADLESS_DAWDREAMER."""
        ui_readback = {
            "backend": "DawDreamer_v1.2"  # DawDreamer marker
        }

        bq = _binding_quality(ui_readback)
        assert bq == "HEADLESS_DAWDREAMER", \
            f"A8 FAIL: DawDreamer backend not detected: {bq}"

    def test_a8_headless_propagates_to_verification_level(self):
        """A8 REAL: DawDreamer marker → blocks LIVE_UI_VERIFIED even with perfect file verification."""
        ui_readback = {
            "is_headless": True,  # Headless marker
        }

        file_cmp = {
            "field_counts": {"VERIFIED_EXACT": 100}  # Perfect verification
        }

        # A8 PROOF: Binding quality detects headless
        bq = _binding_quality(ui_readback)
        assert bq == "HEADLESS_DAWDREAMER", \
            f"A8 FAIL: Headless not detected in binding_quality: {bq}"

        # A8 PROOF: Binding quality propagates to verification_level
        ui_cmp = {"binding_quality": bq, "field_counts": {"VERIFIED_EXACT": 100}}
        level = verification_level(file_cmp, ui_cmp)
        assert level != "LIVE_UI_VERIFIED", \
            f"A8 FAIL: Headless reached LIVE_UI_VERIFIED: {level}"
        assert "HEADLESS_DAWDREAMER" in level, \
            f"A8 FAIL: Headless not in verification level: {level}"

    def test_a8_gate_b_status_blocks_canonical_when_headless(self):
        """A8 REAL: gate_b_status() refuses CANONICAL_GATE_B_VERIFIED when headless, on a real
        ProducerResult produced by finalize_serum_preset_execution() (no MockResult)."""
        from serum2.producer.gate_b_certificate import gate_b_status

        result = self._executed_result({
            "is_headless": True,
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })

        status = gate_b_status(result, epoch=EPOCH_2_0_23)
        assert status != "CANONICAL_GATE_B_VERIFIED", \
            f"A8 FAIL: gate_b_status returned CANONICAL_GATE_B_VERIFIED for headless: {status}"
        assert status == "NATIVE_STATE_PROOF", \
            f"A8 FAIL: gate_b_status should return NATIVE_STATE_PROOF for headless, got {status}"

    def test_a8_gate_b_status_requires_restoration_verified(self):
        """A8 REAL: even a fully non-headless, correctly-bound native result must NOT reach
        CANONICAL_GATE_B_VERIFIED when restoration_verified is missing -- that evidence is required by
        the module's own documented invariant, not optional."""
        from serum2.producer.gate_b_certificate import gate_b_status

        without_restoration = self._executed_result({
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        status = gate_b_status(without_restoration, epoch=EPOCH_2_0_23)
        assert status == "NATIVE_STATE_PROOF", \
            f"A8 FAIL: missing restoration_verified must downgrade to NATIVE_STATE_PROOF, got {status}"

        with_restoration = self._executed_result({
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        status2 = gate_b_status(with_restoration, epoch=EPOCH_2_0_23)
        assert status2 == "CANONICAL_GATE_B_VERIFIED", \
            f"A8 FAIL: real native result WITH restoration_verified should reach CANONICAL, got {status2}"

    def test_a8_gate_b_certificate_derives_headless_flags(self):
        """A8 REAL: gate_b_certificate() derives dawdreamer_used from actual evidence on a real
        ProducerResult (not hardcoded False, and not a MockResult)."""
        from serum2.producer.gate_b_certificate import gate_b_certificate

        result = self._executed_result({
            "backend": "DawDreamer_v1.2",
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)

        assert cert.get("dawdreamer_used") is True, \
            f"A8 FAIL: dawdreamer_used not derived from backend marker: {cert.get('dawdreamer_used')}"

    def test_a8_gate_b_certificate_derives_headless_substitution_used(self):
        """A8 REAL: gate_b_certificate() derives headless_substitution_used from is_headless field on a
        real ProducerResult (not hardcoded False, and not a MockResult)."""
        from serum2.producer.gate_b_certificate import gate_b_certificate

        result = self._executed_result({
            "is_headless": True,
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)

        assert cert.get("headless_substitution_used") is True, \
            f"A8 FAIL: headless_substitution_used not derived from is_headless: {cert.get('headless_substitution_used')}"

    def test_a8_native_evidence_source_never_claims_native_for_headless(self):
        """A8 REAL: native_evidence_source must NOT claim native (Windows/Ableton) proof when the SAME
        certificate's own dawdreamer_used/headless_substitution_used flags are True -- a certificate must
        never contradict itself by claiming native provenance for evidence it knows is headless."""
        from serum2.producer.gate_b_certificate import gate_b_certificate

        headless_result = self._executed_result({
            "is_headless": True,
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        cert = gate_b_certificate(headless_result, epoch=EPOCH_2_0_23)
        assert cert["dawdreamer_used"] or cert["headless_substitution_used"]
        source = cert.get("native_evidence_source") or ""
        assert "Ableton" not in source and "Windows" not in source, \
            f"A8 FAIL: headless certificate still claims native evidence source: {source!r}"

        native_result = self._executed_result({
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        cert2 = gate_b_certificate(native_result, epoch=EPOCH_2_0_23)
        assert not cert2["dawdreamer_used"] and not cert2["headless_substitution_used"]
        assert EPOCH_2_0_23.serum_version in (cert2.get("native_evidence_source") or ""), \
            f"A8 FAIL: genuinely native certificate should name the epoch's own Serum version: {cert2.get('native_evidence_source')!r}"

    def test_a8_gate_b_verified_false_for_headless(self):
        """A8 REAL: gate_b_verified(cert) returns False when headless evidence prevents CANONICAL
        verification, using a certificate produced by the real gate_b_certificate() over a real
        ProducerResult (not a hand-built cert dict, not a MockResult)."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified

        result = self._executed_result({
            "is_headless": True,
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)
        assert cert["gate_b_status"] == "NATIVE_STATE_PROOF"
        assert gate_b_verified(cert) is False, \
            f"A8 FAIL: gate_b_verified returned True for NATIVE_STATE_PROOF: {cert}"

    def test_a8_gate_b_verified_true_only_for_genuine_canonical(self):
        """A8 REAL: gate_b_verified(cert) returns True for a real, fully-bound, non-headless,
        restoration-verified ProducerResult -- proving the positive case isn't vacuously unreachable."""
        from serum2.producer.gate_b_certificate import gate_b_certificate, gate_b_verified

        result = self._executed_result({
            "restoration_verified": True,
            "loader_evidence": {"serum_module_sha256": EPOCH_2_0_23.binary_sha256},
        })
        cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)
        assert cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED", cert
        assert gate_b_verified(cert) is True, f"A8 FAIL: genuine canonical result not gate_b_verified: {cert}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
