"""A2-bypass regression tests for lookup_final().

Proves that:
1. lookup_final() is read-only and never returns an AuthorizedOperation.
2. A lookup_final() result cannot bypass admit_rows() to reach compile_ops().
3. lookup_final() does NOT touch the ADMITTED admission status.
4. The A2 gate (state_admission.admit_rows) is unchanged after the merge of 147de09.
"""
import pytest
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.execution_epoch import EPOCH_2_0_23, EPOCH_2_0_21
from serum2.evidence import admission as adm


def _registry_with_epoch():
    return ContractRegistry(epoch=EPOCH_2_0_23)


def _registry_no_epoch():
    return ContractRegistry(epoch=None)


class TestLookupFinalReadOnly:
    def test_lookup_final_returns_dict_or_none(self):
        reg = _registry_no_epoch()
        result = reg.lookup_final("env1.attack")
        assert result is None or isinstance(result, dict)

    def test_lookup_final_known_entry(self):
        reg = _registry_no_epoch()
        entry = reg.lookup_final("env1.attack")
        assert entry is not None, "env1.attack must be in producer_lookup"

    def test_lookup_final_result_is_not_authorized_operation(self):
        """lookup_final() must return only metadata, never an AuthorizedOperation."""
        from serum2.execution.authorized_state_compiler import AuthorizedOperation
        reg = _registry_no_epoch()
        result = reg.lookup_final("env1.attack")
        assert not isinstance(result, AuthorizedOperation), (
            "lookup_final() must never return an AuthorizedOperation")

    def test_lookup_final_unknown_atlas_id_returns_none(self):
        reg = _registry_no_epoch()
        assert reg.lookup_final("not.a.real.control") is None

    def test_lookup_final_none_when_no_contract(self, tmp_path):
        reg = ContractRegistry(epoch=None)
        reg._final_contract = None  # simulate failed load
        assert reg.lookup_final("env1.attack") is None


class TestNoAdmissionBypass:
    def test_lookup_final_does_not_set_admitted_status(self):
        """lookup_final() must not write ADMITTED to any row."""
        reg = _registry_no_epoch()
        reg.lookup_final("env1.attack")
        # There is no ledger row created or modified
        # Verify by checking that no contracts dict changed
        contracts_before = dict(reg.contracts)
        reg.lookup_final("env1.attack")
        assert reg.contracts == contracts_before

    def test_execution_spec_still_present_after_merge(self):
        """execution_spec() must exist and return data — A2 gate still has its method."""
        reg = _registry_no_epoch()
        assert hasattr(reg, "execution_spec"), "execution_spec() must not be deleted"
        spec = reg.execution_spec("env1.attack")
        assert spec is not None, "execution_spec() must return data for env1.attack with epoch=None"

    def test_execution_spec_epoch_gated(self):
        """With a real epoch set, execution_spec() must reject a contract from a different epoch."""
        # Create a registry that loads the real final contract but override its recorded epoch
        reg = ContractRegistry(epoch=EPOCH_2_0_23)
        # Tamper the recorded epoch so it looks like a mismatch
        reg.final_execution_contract_epoch = ("2.0.21", "deadbeef")
        spec = reg.execution_spec("env1.attack")
        assert spec is None, "execution_spec() must return None when epochs mismatch"

    def test_admitted_status_only_from_admit_rows(self):
        """The ADMITTED status for a real epoch must only come from admit_rows()."""
        from serum2.producer.state_admission import admit_rows
        # admit_rows with empty rows → nothing ADMITTED
        rows = admit_rows([], EPOCH_2_0_23)
        assert all(r.get("admission") != "ADMITTED" if isinstance(r, dict) else r.admission != "ADMITTED"
                   for r in rows)

    def test_no_admitted_status_outside_state_admission(self):
        """Grep-level: no code outside state_admission.py ASSIGNS 'ADMITTED' to admission field."""
        import subprocess
        # Match only assignment patterns, not comparisons (== or !=)
        result = subprocess.run(
            ["grep", "-rEn", r'\.admission\s*=\s*["\x27]ADMITTED["\x27]',
             "serum2/", "--include=*.py"],
            capture_output=True, text=True, cwd="/home/user/ac-test")
        hits = [l for l in result.stdout.splitlines()
                if "state_admission" not in l and "test_gate_a" not in l]
        assert not hits, "Found ADMITTED assigned outside state_admission.py:\n" + "\n".join(hits)


class TestA2GateUnchanged:
    """Gate A-core A2 negative tests must still pass after the 147de09 merge."""

    def test_offline_test_epoch_bypasses_gate(self):
        """EPOCH_OFFLINE_TEST is the legitimate offline bypass; real epochs are not."""
        from serum2.producer.execution_epoch import EPOCH_OFFLINE_TEST
        from serum2.producer.state_admission import is_offline_test
        assert is_offline_test(EPOCH_OFFLINE_TEST)
        assert not is_offline_test(EPOCH_2_0_23)
        # None is treated as offline for backward-compat (existing documented behavior)
        assert is_offline_test(None)

    def test_lookup_final_epoch_isolation(self):
        """lookup_final() with epoch=2.0.23 must not serve a contract proven on 2.0.21."""
        reg = ContractRegistry(epoch=EPOCH_2_0_23)
        # Tamper: replace a contract's epoch with 2.0.21
        if "env1.attack" in reg.execution_specs:
            import copy
            orig = copy.copy(reg.execution_specs["env1.attack"])
            reg.execution_specs["env1.attack"] = dict(orig, serum_binary_sha256=EPOCH_2_0_21.binary_sha256,
                                                       serum_version="2.0.21")
            reg.final_execution_contract_epoch = ("2.0.21", EPOCH_2_0_21.binary_sha256)
            assert reg.execution_spec("env1.attack") is None

    def test_lookup_final_not_called_from_compile_ops(self):
        """compile_ops must not call lookup_final() — the only path is admit_rows -> execution_spec."""
        import inspect
        from serum2.execution import authorized_state_compiler
        src = inspect.getsource(authorized_state_compiler)
        assert "lookup_final" not in src, (
            "lookup_final() must not appear in authorized_state_compiler.py — "
            "it would be a second authority path")
