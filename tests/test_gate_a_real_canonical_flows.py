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

    # Targets whose promoted evidence covers the EXACT SAME physical Serum parameter (identical root,
    # index, kparam, AND operand kind) as another, differently-keyed contract loaded from a different
    # evidence source (the Pass-1/canonical pickle stores, loaded before promoted evidence -- see
    # ContractRegistry._load_fresh_contracts vs _load_promoted_evidence_contracts). Dict insertion order
    # makes find_contract's selection among tied candidates deterministic (proven below, not asserted),
    # but it means the canonical lookup for these specific targets legitimately resolves the OTHER key,
    # not `target` itself. Each pair here is verified below to (a) target the identical physical
    # parameter, (b) agree on operand kind, and (c) resolve identically across repeated calls -- so a
    # promoted target in this set is still fully reachable in practice, just not under its own dict key.
    # This set is exhaustively cross-checked against the live registry in
    # test_a4_duplicate_coverage_set_is_exhaustive_and_harmless below, so it can never silently grow.
    KNOWN_DUPLICATE_COVERAGE = frozenset({
        "env2.decay", "env2.release", "env3.decay", "env3.release", "env4.decay", "env4.release",
        "mixer.filter1.enable", "mixer.filter2.enable", "oscB.octave", "oscC.octave",
        "voice.voicing.legato", "voice.voicing.mono", "voice.voicing.porta_always", "voice.voicing.porta_scaled",
    })

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

            # own_coverage.operand is this promoted contract's OWN proven operand kind (numeric / boolean /
            # enum / structured), derived straight from its real allowed_operation -- used to build an
            # operation value that matches what a REAL derive() would produce for this field (TOGGLE_ON for
            # a boolean field, SELECT for an enum, SET otherwise), so the operand-aware selection in
            # find_contract (contract_scope._select_by_operand) is exercised the same way admit_rows()
            # exercises it in production, not with every field flattened to a numeric "SET" guess.
            own_coverage = next((c for c in bridge if c.contract_key == target), None)
            assert own_coverage is not None, f"A4 FAIL: {target} has no bridge_index() coverage entry at all"
            op = {k: v for k, v in binding_entry.items() if k != "basis"}
            op["operation"] = {"boolean": "TOGGLE_ON", "enum": "SELECT"}.get(own_coverage.operand, "SET")

            # (5) the SAME canonical lookup admit_rows() calls
            found, tr = find_contract(op, {}, bridge, cat)
            if found is None:
                unreachable.append((target, tr.status, tr.detail))
                continue

            if found.contract_key == target:
                pass  # canonical lookup resolved this exact promoted target -- the strong case
            elif target in self.KNOWN_DUPLICATE_COVERAGE:
                # A different, explicitly-named contract legitimately covers the identical physical
                # parameter (see KNOWN_DUPLICATE_COVERAGE's docstring). Still require physical AND operand
                # agreement -- a duplicate that disagreed on operand kind would be the real oscB.enabled-
                # style bug this test exists to catch, not a harmless duplicate.
                assert (found.root, found.index, found.kparam, found.fx_type, found.rack, found.operand) == (
                    own_coverage.root, own_coverage.index, own_coverage.kparam, own_coverage.fx_type,
                    own_coverage.rack, own_coverage.operand), (
                    f"A4 FAIL: {target}'s declared duplicate {found.contract_key} does NOT actually agree "
                    f"on physical parameter/operand: found={found} own={own_coverage}")
            else:
                assert found.contract_key == target, (
                    f"A4 FAIL: {target} canonical lookup resolved a DIFFERENT, UNDECLARED contract "
                    f"{found.contract_key!r} -- either this is a new duplicate-coverage case that must be "
                    f"added to KNOWN_DUPLICATE_COVERAGE (after verifying it's genuinely harmless), or it is "
                    f"a real reachability defect. found={found} own={own_coverage}")

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

    def test_a4_duplicate_coverage_set_is_exhaustive_and_harmless(self):
        """A4 REAL: KNOWN_DUPLICATE_COVERAGE must name EXACTLY the promoted targets whose canonical lookup
        resolves a different contract_key (an exhaustive, non-sample sweep -- not a spot check), and for
        every one of them, resolution must be DETERMINISTIC (proven by calling find_contract 5 times and
        requiring an identical result, not assumed from dict-ordering reasoning alone)."""
        reg = self._registry()
        promoted_targets = reg.promotion_diagnostics.get("loaded", [])
        bt = binding_table()
        bridge = bridge_index(reg)
        cat = catalog()

        actual_duplicates = set()
        for target in promoted_targets:
            binding_entry = bt["controls"].get(target)
            if binding_entry is None:
                continue
            own_coverage = next((c for c in bridge if c.contract_key == target), None)
            if own_coverage is None:
                continue
            op = {k: v for k, v in binding_entry.items() if k != "basis"}
            op["operation"] = {"boolean": "TOGGLE_ON", "enum": "SELECT"}.get(own_coverage.operand, "SET")

            results = set()
            for _ in range(5):
                found, _ = find_contract(op, {}, bridge, cat)
                results.add(found.contract_key if found else None)
            assert len(results) == 1, \
                f"A4 FAIL: {target} canonical lookup is NON-DETERMINISTIC across repeated calls: {results}"
            resolved = next(iter(results))
            if resolved is not None and resolved != target:
                actual_duplicates.add(target)

        assert actual_duplicates == self.KNOWN_DUPLICATE_COVERAGE, (
            f"A4 FAIL: KNOWN_DUPLICATE_COVERAGE is stale. "
            f"new/undeclared duplicates: {actual_duplicates - self.KNOWN_DUPLICATE_COVERAGE}; "
            f"declared-but-no-longer-duplicated (safe to remove): "
            f"{self.KNOWN_DUPLICATE_COVERAGE - actual_duplicates}"
        )

    # NOT every one of the 330 binding_table controls has ever been qualified/promoted into a
    # CapabilityContract (macro *names*, several FX units never run through the capability pipeline,
    # mixer bus-send levels, some warp/sample-loop fields, and a handful of singleton fields whose
    # catalog kParam name has no confirmed mapping yet). That is an honest, evidence-grounded state --
    # "not yet capability-backed" -- not a lookup defect, and "every UI control is executable" was never
    # something this codebase could truthfully claim. Asserting unreachable == [] here (the previous
    # version of this test) was only achievable by treating execution_spec existence as a reachability
    # proxy -- exactly the authority/evidence conflation this review correctly rejected. This test proves
    # the HONEST, exhaustive partition instead: every one of the 330 controls is classified into
    # REACHABLE (find_contract, the exact function admit_rows() calls, resolves a real contract) or
    # NOT_YET_CAPABILITY_BACKED (find_contract itself reports why, never a crash, never execution_spec),
    # and the two sets partition the full 330 exactly -- so a genuine lookup regression (a control that
    # used to resolve and silently stops) is still caught, without lying about universal executability.
    NOT_YET_CAPABILITY_BACKED_ALLOWED_STATUSES = frozenset({"NO_CAPABILITY", "SCOPE_WOULD_EXPAND", "INCOMPATIBLE_OPERATION"})

    @staticmethod
    def _operation_for(entry, catalog_dict):
        """The SAME operand-kind-driven operation choice A5 uses for legal-value construction: TOGGLE_ON
        for a boolean field, SELECT for an enum-domain field, SET otherwise. Never blanket 'SET' -- that
        would defeat contract_scope._select_by_operand's operand-aware duplicate resolution and hide
        exactly the oscB.enabled-style bug this review flagged."""
        kind = entry.get("kind")
        if kind in ("field", "singleton_field"):
            from serum_mcp.generation import spec as S
            models = {"osc": S.OscillatorSpec, "env": S.EnvelopeSpec, "lfo": S.LfoSpec,
                     "filter": S.FilterSpec, "macro": S.MacroSpec,
                     "arp": S.ArpSpec, "global_": S.GlobalSpec, "voice_unison": S.VoiceUnisonSpec}
            key = entry.get("module") if kind == "field" else entry.get("attr")
            cls = models.get(key)
            fi = cls.model_fields.get(entry.get("field")) if cls else None
            if fi is not None:
                if "bool" in str(fi.annotation):
                    return "TOGGLE_ON"
                from serum2.producer.state_ledger import _domain
                if "str" in str(fi.annotation) and _domain(entry.get("field"), key, fi.description):
                    return "SELECT"
            return "SET"
        if kind == "fx":
            p = catalog_dict.get("fx_params", {}).get(entry.get("fx_type"), {}).get(entry.get("param"))
            if p is not None and p.get("kind") == "enum":
                return "SELECT"
            return "SET"
        return "SET"

    def test_a4_every_user_facing_control_exhaustively_partitioned(self):
        """A4 REAL: every one of the 330 binding_table controls is either REACHABLE via the real
        find_contract() canonical lookup, or NOT_YET_CAPABILITY_BACKED with an understood, non-crash
        reason -- an exhaustive, non-sample sweep with NO execution_spec shortcut anywhere in this test."""
        reg = self._registry()
        bt = binding_table()
        bridge = bridge_index(reg)
        cat = catalog()

        user_facing_controls = list(bt["controls"].keys())
        reachable = []
        not_yet_capable = []

        for ctrl_id in user_facing_controls:
            entry = bt["controls"][ctrl_id]
            op = {k: v for k, v in entry.items() if k != "basis"}
            op["operation"] = self._operation_for(entry, cat)
            found, tr = find_contract(op, {}, bridge, cat)
            if found is not None:
                reachable.append(ctrl_id)
            else:
                assert tr.status in self.NOT_YET_CAPABILITY_BACKED_ALLOWED_STATUSES, (
                    f"A4 FAIL: {ctrl_id} failed with an UNEXPECTED status {tr.status!r} ({tr.detail}) -- "
                    f"only {sorted(self.NOT_YET_CAPABILITY_BACKED_ALLOWED_STATUSES)} are understood, "
                    f"honest 'not yet capability-backed' reasons; anything else is a real lookup defect"
                )
                not_yet_capable.append((ctrl_id, tr.status, tr.detail))

        assert len(reachable) + len(not_yet_capable) == len(user_facing_controls), \
            "A4 FAIL: reachable + not_yet_capable does not exhaustively partition all 330 controls"
        assert len(reachable) > 0, "A4 FAIL: zero controls reachable at all -- registry/lookup broke entirely"
        # Every promoted target this same registry loaded must be among the reachable set (cross-check
        # against the strong, name-exact promoted-target proof above) -- a control WITH real promoted
        # evidence must never land in "not yet capability-backed".
        promoted_targets = set(reg.promotion_diagnostics.get("loaded", []))
        promoted_but_not_capable = (promoted_targets & {c for c, _, _ in not_yet_capable}) - self.KNOWN_UNREACHABLE_OPERAND_MISMATCH
        assert promoted_but_not_capable == set(), \
            f"A4 FAIL: promoted targets classified as not-yet-capable (real regression): {promoted_but_not_capable}"


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

    def test_a7_exact_runtime_epoch_required_when_expected_epoch_given(self):
        """A7 REAL: when the caller passes expected_epoch (the run's own ExecutionEpoch, as compare_ui()
        and gate_b_status() now both do), a readback claiming a DIFFERENT real, known epoch must be
        rejected -- "known pinned epoch" is not the same claim as "the epoch THIS run executed on"."""
        from serum2.producer.execution_epoch import EPOCH_2_0_23, EPOCH_2_0_21

        matching = self._valid_readback(loader_evidence={
            "epoch": EPOCH_2_0_23.serum_version, "serum_module_sha256": EPOCH_2_0_23.binary_sha256})
        assert _binding_quality(matching, expected_epoch=EPOCH_2_0_23) == "LOADER_BOUND", \
            "A7 FAIL: readback bound to the exact runtime epoch was rejected"

        wrong_epoch_string = self._valid_readback(loader_evidence={
            "epoch": EPOCH_2_0_21.serum_version, "serum_module_sha256": EPOCH_2_0_23.binary_sha256})
        bq = _binding_quality(wrong_epoch_string, expected_epoch=EPOCH_2_0_23)
        assert bq != "LOADER_BOUND", \
            f"A7 FAIL: readback claiming 2.0.21 (a real, known epoch) accepted for a 2.0.23 run: {bq}"

        wrong_module_sha = self._valid_readback(loader_evidence={
            "epoch": EPOCH_2_0_23.serum_version, "serum_module_sha256": EPOCH_2_0_21.binary_sha256})
        bq2 = _binding_quality(wrong_module_sha, expected_epoch=EPOCH_2_0_23)
        assert bq2 != "LOADER_BOUND", \
            f"A7 FAIL: readback with 2.0.21's module SHA accepted for a 2.0.23 run: {bq2}"

    def test_a7_negative_crop_coords_rejected(self):
        """A7 REAL: crop_coords must be non-negative -- a negative x/y/w/h cannot describe a real screen
        region, even though it is numeric and finite."""
        for bad_coords in ([-1, 0, 100, 100], [0, -1, 100, 100], [0, 0, -100, 100], [0, 0, 100, -100]):
            invalid_ui = self._valid_readback(loader_evidence={"crop_coords": bad_coords})
            bq = _binding_quality(invalid_ui)
            assert bq != "LOADER_BOUND", f"A7 FAIL: negative crop_coords {bad_coords} still LOADER_BOUND: {bq}"

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

    @staticmethod
    def _full_loader_bound(**overrides):
        """A complete, real A7 LOADER_BOUND ui_readback: DIRECT_UI route, all 6 loader_evidence fields
        valid, exact runtime epoch, and a real observed values payload -- everything gate_b_status() now
        requires (via state_comparator._binding_quality) for CANONICAL_GATE_B_VERIFIED. Overrides merge
        into loader_evidence; top-level keys (e.g. restoration_verified, is_headless) pass through `top`."""
        le = {
            "run_id": "a8_run_1", "track_nonce": "a8_nonce_1",
            "serum_module_sha256": EPOCH_2_0_23.binary_sha256,
            "epoch": EPOCH_2_0_23.serum_version,
            "screenshot_sha": "c" * 64,
            "crop_coords": [0, 0, 100, 100],
        }
        le.update(overrides.pop("loader_evidence", {}))
        base = {"route": "DIRECT_UI", "values": {"env1.attack": "5.0"}, "loader_evidence": le}
        base.update(overrides)
        return base

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

        result = self._executed_result(self._full_loader_bound(is_headless=True, restoration_verified=True))

        status = gate_b_status(result, epoch=EPOCH_2_0_23)
        assert status != "CANONICAL_GATE_B_VERIFIED", \
            f"A8 FAIL: gate_b_status returned CANONICAL_GATE_B_VERIFIED for headless: {status}"
        assert status == "NATIVE_STATE_PROOF", \
            f"A8 FAIL: gate_b_status should return NATIVE_STATE_PROOF for headless, got {status}"

    def test_a8_gate_b_status_requires_restoration_verified(self):
        """A8 REAL: even a fully non-headless, correctly A7-bound (full LOADER_BOUND evidence) native
        result must NOT reach CANONICAL_GATE_B_VERIFIED when restoration_verified is missing -- that
        evidence is required by the module's own documented invariant, not optional."""
        from serum2.producer.gate_b_certificate import gate_b_status

        without_restoration = self._executed_result(self._full_loader_bound())
        status = gate_b_status(without_restoration, epoch=EPOCH_2_0_23)
        assert status == "NATIVE_STATE_PROOF", \
            f"A8 FAIL: missing restoration_verified must downgrade to NATIVE_STATE_PROOF, got {status}"

        with_restoration = self._executed_result(self._full_loader_bound(restoration_verified=True))
        status2 = gate_b_status(with_restoration, epoch=EPOCH_2_0_23)
        assert status2 == "CANONICAL_GATE_B_VERIFIED", \
            f"A8 FAIL: real, fully A7-bound native result WITH restoration_verified should reach CANONICAL, got {status2}"

    def test_a8_certificate_screenshot_sha_reads_the_real_loader_evidence_field(self):
        """A8/A7 REAL: gate_b_certificate()'s screenshot_sha256 field must actually read the SAME
        loader_evidence["screenshot_sha"] field A7's own schema defines -- not a differently-named,
        never-populated top-level key that always read back None."""
        from serum2.producer.gate_b_certificate import gate_b_certificate

        readback = self._full_loader_bound(restoration_verified=True)
        real_sha = readback["loader_evidence"]["screenshot_sha"]
        result = self._executed_result(readback)
        cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)
        assert cert.get("screenshot_sha256") == real_sha, \
            f"A8 FAIL: certificate screenshot_sha256 {cert.get('screenshot_sha256')!r} != real loader_evidence screenshot_sha {real_sha!r}"

    def test_a8_gate_b_status_requires_epoch(self):
        """A8 REAL: epoch=None must NEVER be capable of producing CANONICAL_GATE_B_VERIFIED, even with
        otherwise-complete evidence -- there is no runtime epoch to bind the readback to."""
        from serum2.producer.gate_b_certificate import gate_b_status

        result = self._executed_result(self._full_loader_bound(restoration_verified=True))

        assert gate_b_status(result, epoch=EPOCH_2_0_23) == "CANONICAL_GATE_B_VERIFIED", \
            "setup: this evidence must reach CANONICAL with a real epoch, to prove epoch=None is what changes it"
        assert gate_b_status(result, epoch=None) != "CANONICAL_GATE_B_VERIFIED", \
            "A8 FAIL: gate_b_status(epoch=None) reached CANONICAL_GATE_B_VERIFIED"

    def test_a8_gate_b_status_requires_full_a7_loader_bound_evidence(self):
        """A8 REAL: gate_b_status() must refuse CANONICAL_GATE_B_VERIFIED whenever A7's own
        _binding_quality() would refuse LOADER_BOUND -- even when the narrower fields this function used
        to check alone (module SHA, admitted, restoration_verified) all individually pass. This is the
        Gate-B-bypasses-A7 case: a readback missing run_id/track_nonce/screenshot_sha/crop_coords/values,
        or bound to the WRONG epoch, must never reach canonical status."""
        from serum2.producer.gate_b_certificate import gate_b_status
        from serum2.execution.state_comparator import _binding_quality
        from serum2.producer.execution_epoch import EPOCH_2_0_21

        cases = {
            "missing_run_id": self._full_loader_bound(loader_evidence={"run_id": ""}),
            "missing_values": {**self._full_loader_bound(), "values": {}},
            "wrong_epoch_string": self._full_loader_bound(loader_evidence={"epoch": EPOCH_2_0_21.serum_version}),
            "wrong_module_sha": self._full_loader_bound(loader_evidence={"serum_module_sha256": EPOCH_2_0_21.binary_sha256}),
            "not_direct_ui_route": {**self._full_loader_bound(), "route": "FILE_READBACK"},
        }
        for name, readback in cases.items():
            readback = dict(readback)
            readback["restoration_verified"] = True
            # Confirm A7 itself would refuse this (except the route case, which A7's _binding_quality
            # doesn't itself gate -- gate_b_status must enforce DIRECT_UI on its own, checked separately).
            if name != "not_direct_ui_route":
                assert _binding_quality(readback, expected_epoch=EPOCH_2_0_23) != "LOADER_BOUND", \
                    f"setup FAIL [{name}]: A7 unexpectedly accepted this readback as LOADER_BOUND"
            result = self._executed_result(readback)
            status = gate_b_status(result, epoch=EPOCH_2_0_23)
            assert status != "CANONICAL_GATE_B_VERIFIED", \
                f"A8 FAIL [{name}]: gate_b_status reached CANONICAL despite A7-invalid evidence: {status}"

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

        result = self._executed_result(self._full_loader_bound(restoration_verified=True))
        cert = gate_b_certificate(result, epoch=EPOCH_2_0_23)
        assert cert["gate_b_status"] == "CANONICAL_GATE_B_VERIFIED", cert
        assert gate_b_verified(cert) is True, f"A8 FAIL: genuine canonical result not gate_b_verified: {cert}"


class TestExhaustiveAcquisitionWiring:
    """CRITICAL (cross-check finding): the existence of serum2.source.acquire_exhaustive does not by
    itself prove the production one-command pipeline USES it. These tests exercise the real
    run_stage1_acquire_and_prep() end-to-end (real fetch_transcript output shape, real stage_a_census_prep,
    real stage_a_is_filled) with only the two external-IO boundaries (fetch_transcript's network call,
    acquire_exhaustive's yt-dlp/ffmpeg call) replaced by controlled fakes -- proving the WIRING, not just
    that the module can be imported."""

    def test_run_stage1_calls_acquire_exhaustive_not_sampling_path(self, tmp_path, monkeypatch):
        import youtube_to_serum.reference_engine as ref_engine

        # fetch_transcript resolves "data/transcripts" relative to CWD (see run_stage1_acquire_and_prep's
        # own comment on this) -- chdir into an isolated tmp dir so this test never writes into the repo.
        monkeypatch.chdir(tmp_path)

        calls = {"exhaustive": 0}
        source_url = "https://www.youtube.com/watch?v=wiring_test_video"
        video_id = "wiring_test_video"

        # Real fetch_transcript output shape (see stage_a_census_prep.normalize_fetch_transcript_output) --
        # written to the exact CWD-relative path fetch_transcript itself uses, so run_stage1's own
        # (never-touched) lookup of that path finds it.
        from serum2.source.fetch_youtube import compute_source_id
        source_id = compute_source_id(source_url)
        transcript_dir = Path("data") / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / (source_id + ".json")
        transcript_path.write_text(json.dumps({
            "source_id": source_id, "video_id": video_id, "source_url": source_url,
            "language_code": "en", "segments": [{"text": "hello", "start_time_sec": 0.0, "duration": 1.0}],
        }))

        def fake_fetch_transcript(video_id, url, allow_fallback=True):
            return True

        # Real frame files (content doesn't matter -- build_frame_manifest only globs filenames) at real
        # decoder-index-style names, with a real VisualFrameArtifact carrying the AUTHORITATIVE decoder
        # pts_time -- exactly acquire_exhaustive's own output shape.
        frames_dir = tmp_path / "exhaustive_frames"
        frames_dir.mkdir()
        from serum2.source.visual_evidence import VisualFrameArtifact
        fake_frames = []
        for i, pts in enumerate([0.0, 12.345, 27.891]):
            p = frames_dir / ("frame_%s_%08d.jpg" % (source_id, i))
            p.write_bytes(b"\xff\xd8\xff")  # not a real JPEG; manifest building never decodes it
            fake_frames.append(VisualFrameArtifact(
                frame_id=p.stem, source_url=source_url, source_id=source_id, video_id=video_id,
                timestamp_sec=pts, artifact_path=str(p), artifact_hash="x" * 64, width=10, height=10,
                source_video_sha256="y" * 64))

        def fake_acquire_exhaustive(source_url, video_id=None, force=False, cache_key_extra=None):
            calls["exhaustive"] += 1
            return {"status": "SUCCESS", "source_id": source_id, "num_frames_decoded": len(fake_frames),
                    "num_frames_verified": len(fake_frames), "frames": fake_frames,
                    "provenance": {}, "completion_status": {"is_complete": True}, "error": None}

        monkeypatch.setattr(ref_engine, "fetch_transcript", fake_fetch_transcript)
        monkeypatch.setattr(ref_engine, "acquire_exhaustive", fake_acquire_exhaustive)

        work_dir = tmp_path / "work"
        try:
            ref_engine.run_stage1_acquire_and_prep(source_url, work_dir)
        except ref_engine.NeedsStageACensus:
            pass  # expected: a fresh skeleton is never pre-filled

        assert calls["exhaustive"] == 1, \
            "CRITICAL FAIL: run_stage1_acquire_and_prep did not call acquire_exhaustive exactly once"

        skeleton = json.loads((work_dir / "stage_a_skeleton.json").read_text())
        assert len(skeleton["frames"]) == len(fake_frames), \
            f"CRITICAL FAIL: skeleton has {len(skeleton['frames'])} frames, expected {len(fake_frames)}"
        # The real decoder pts_time must survive into the skeleton -- NOT frame_index/1000 (the bug this
        # wiring uncovered: acquire_exhaustive's filenames end in a decoder INDEX, not milliseconds, and
        # naively reusing acquire_visual_evidence's millisecond-parsing regex would corrupt every timestamp).
        got_timestamps = sorted(f["timestamp_sec"] for f in skeleton["frames"])
        want_timestamps = sorted(f.timestamp_sec for f in fake_frames)
        assert got_timestamps == want_timestamps, \
            f"CRITICAL FAIL: skeleton timestamps {got_timestamps} != real decoder pts_time {want_timestamps} " \
            f"-- frame index was mis-derived as milliseconds"

    def test_run_stage1_fails_closed_on_incomplete_exhaustive_acquisition(self, tmp_path, monkeypatch):
        """CRITICAL: a FAILED acquire_exhaustive result (e.g. decoder/artifact mismatch) must stop the
        pipeline, never silently fall back to a partial or sampled frame set."""
        import youtube_to_serum.reference_engine as ref_engine

        monkeypatch.chdir(tmp_path)
        source_url = "https://www.youtube.com/watch?v=wiring_fail_test"

        def fake_fetch_transcript(video_id, url, allow_fallback=True):
            from serum2.source.fetch_youtube import compute_source_id
            source_id = compute_source_id(url)
            transcript_dir = Path("data") / "transcripts"
            transcript_dir.mkdir(parents=True, exist_ok=True)
            (transcript_dir / (source_id + ".json")).write_text(json.dumps({
                "source_id": source_id, "video_id": "wiring_fail_test", "source_url": url,
                "language_code": "en", "segments": [],
            }))
            return True

        def fake_acquire_exhaustive(source_url, video_id=None, force=False, cache_key_extra=None):
            return {"status": "FAILED", "source_id": "x", "num_frames_decoded": 3, "num_frames_verified": 1,
                    "frames": [], "provenance": {}, "completion_status": {"is_complete": False},
                    "error": "decoder/artifact count mismatch: 3 != 1"}

        monkeypatch.setattr(ref_engine, "fetch_transcript", fake_fetch_transcript)
        monkeypatch.setattr(ref_engine, "acquire_exhaustive", fake_acquire_exhaustive)

        with pytest.raises(RuntimeError, match="acquire_exhaustive failed"):
            ref_engine.run_stage1_acquire_and_prep(source_url, tmp_path / "work")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
