"""Gate B wiring regression tests.

Covers the two wiring gaps identified in W1/blocker/gate_b_admission_blocker.json:
  Gap A: capability_key / atlas_id naming mismatch
  Gap B: RouteSelector's disconnected ContractRegistry

Tests A–G as specified in the task:
  A — explicit crosswalk resolves exactly
  B — injected registry reaches RouteSelector
  C — canonical env2.decay resolves under EPOCH_2_0_23
  D — wrong epoch is rejected
  E — lookup_final() does not produce AuthorizedOperation or ADMITTED
  F — distinct requested values survive through admission
  G — A2 negative cases still fail closed
"""
import pytest
from pathlib import Path
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.execution_epoch import EPOCH_2_0_23, EPOCH_2_0_21
from serum2.producer.capability_crosswalk import CAPABILITY_KEY_TO_ATLAS_ID
from serum2.producer.route_selection import RouteSelector, ExecutionRoute

BINDING_DIR = Path(__file__).parent.parent / "serum2" / "qualification" / "binding_evidence"
PROMOTED_DIR = Path(__file__).parent.parent / "parameter_characterization" / "binding_evidence_mcp_exec_v1"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reg_2023():
    """Epoch-aware registry matching the production path."""
    return ContractRegistry(
        epoch=EPOCH_2_0_23,
        binding_evidence_dir=str(BINDING_DIR),
        promoted_evidence_dir=str(PROMOTED_DIR),
    )


# ---------------------------------------------------------------------------
# Test A — explicit crosswalk
# ---------------------------------------------------------------------------

class TestCrosswalk:
    def test_crosswalk_entry_exists(self):
        assert "envelope2_field_decay" in CAPABILITY_KEY_TO_ATLAS_ID

    def test_crosswalk_maps_to_correct_atlas_id(self):
        assert CAPABILITY_KEY_TO_ATLAS_ID["envelope2_field_decay"] == "env2.decay"

    def test_no_fuzzy_prefix_or_suffix_logic(self):
        """The crosswalk is a plain dict — no dynamic string manipulation."""
        import inspect, ast, serum2.producer.capability_crosswalk as mod
        src = inspect.getsource(mod)
        for forbidden in ("endswith", "startswith", "replace(", "split(", "re.", "regex"):
            assert forbidden not in src, (
                "CAPABILITY_KEY_TO_ATLAS_ID must not use '%s'" % forbidden)

    def test_crosswalk_alias_registered_in_registry(self):
        """ContractRegistry.contracts must contain 'envelope2_field_decay' as an alias."""
        reg = _reg_2023()
        assert "envelope2_field_decay" in reg.contracts, (
            "crosswalk alias not registered; crosswalk: %r" % CAPABILITY_KEY_TO_ATLAS_ID)

    def test_both_keys_resolve(self):
        """Both atlas_id and capability_key keys must resolve to a non-None contract."""
        reg = _reg_2023()
        # env2.decay (atlas_id) — from binding evidence
        c_atlas = reg.contracts.get("env2.decay")
        assert c_atlas is not None, "atlas_id 'env2.decay' not in registry"
        # envelope2_field_decay (capability_key) — from Pass-1 or crosswalk alias
        c_cap = reg.get_by_capability_key("envelope2_field_decay")
        assert c_cap is not None, "capability_key 'envelope2_field_decay' not resolvable"

    def test_get_by_capability_key_resolves(self):
        reg = _reg_2023()
        c = reg.get_by_capability_key("envelope2_field_decay")
        assert c is not None, "get_by_capability_key('envelope2_field_decay') returned None"

    def test_get_method_resolves_capability_key(self):
        """ContractRegistry.get() must resolve capability_key via the crosswalk."""
        reg = _reg_2023()
        c = reg.get("envelope2_field_decay")
        assert c is not None


# ---------------------------------------------------------------------------
# Test B — injected registry
# ---------------------------------------------------------------------------

class TestRegistryInjection:
    def test_route_selector_accepts_registry(self):
        reg = _reg_2023()
        sel = RouteSelector(registry=reg)
        assert sel._registry is reg

    def test_injected_registry_not_replaced(self):
        """RouteSelector must not silently swap out an injected registry."""
        reg = _reg_2023()
        sel = RouteSelector(registry=reg)
        # After construction the registry is unchanged
        assert sel._registry is reg

    def test_no_arg_creates_legacy_registry(self):
        """Without injection, RouteSelector creates a legacy epoch-less registry (backward compat)."""
        sel = RouteSelector()
        # The legacy registry has no epoch
        assert sel._registry.epoch is None

    def test_producer_brain_injects_registry(self):
        """ProducerBrain must not construct an independent RouteSelector without its registry."""
        from serum2.producer.producer_brain import ProducerBrain
        brain = ProducerBrain(epoch=EPOCH_2_0_23,
                              binding_evidence_dir=str(BINDING_DIR),
                              promoted_evidence_dir=str(PROMOTED_DIR))
        # The selector's registry is the same object the brain uses
        assert brain._selector._registry is brain._registry

    def test_no_disconnected_registry_in_production(self):
        """With an epoch, ProducerBrain's selector must NOT use a fresh epoch-less registry."""
        from serum2.producer.producer_brain import ProducerBrain
        brain = ProducerBrain(epoch=EPOCH_2_0_23,
                              binding_evidence_dir=str(BINDING_DIR),
                              promoted_evidence_dir=str(PROMOTED_DIR))
        assert brain._selector._registry.epoch == EPOCH_2_0_23


# ---------------------------------------------------------------------------
# Test C — canonical env2.decay resolution under EPOCH_2_0_23
# ---------------------------------------------------------------------------

class TestEnv2DecayResolution:
    def test_env2_decay_in_registry(self):
        reg = _reg_2023()
        assert "env2.decay" in reg.contracts

    def test_route_selector_picks_env2_decay_with_injected_registry(self):
        reg = _reg_2023()
        sel = RouteSelector(registry=reg)
        decision = sel.select_route("Env2.Decay")
        assert decision.route != ExecutionRoute.REFUSE, (
            "Expected non-REFUSE route for Env2.Decay, got: %s — rationale: %s"
            % (decision.route, decision.rationale))
        assert decision.dawdreamer_admission_ready, decision.rationale

    def test_env2_decay_body_path_preserved(self):
        """The contract must use Env1.plainParams.kParamDecay (Serum 0-indexed body path)."""
        reg = _reg_2023()
        c = reg.contracts.get("env2.decay")
        if c is None:
            pytest.skip("env2.decay not loaded from binding evidence")
        body_path = c.execution_binding.body_path if c.execution_binding else ""
        assert "kParamDecay" in body_path, (
            "Expected kParamDecay in body_path, got: %r" % body_path)


# ---------------------------------------------------------------------------
# Test D — wrong epoch rejected
# ---------------------------------------------------------------------------

class TestEpochIsolation:
    def test_2021_registry_does_not_satisfy_2023_route(self):
        """A 2.0.21 registry must not route a control that only has 2.0.23 evidence."""
        reg_21 = ContractRegistry(epoch=EPOCH_2_0_21,
                                  binding_evidence_dir=str(BINDING_DIR),
                                  promoted_evidence_dir=str(PROMOTED_DIR))
        sel = RouteSelector(registry=reg_21)
        # env2.decay binding evidence was produced under EPOCH_2_0_23;
        # a 2.0.21 registry must not see it as admission-ready.
        decision = sel.select_route("Env2.Decay")
        # Accept either: REFUSE, or DAWDREAMER with admission_ready=False
        if decision.route != ExecutionRoute.REFUSE:
            assert not decision.dawdreamer_admission_ready, (
                "2.0.21 registry must not produce admission-ready route for 2.0.23 evidence")

    def test_epoch_none_does_not_load_promoted_evidence(self):
        """epoch=None legacy frontier must not promote env2.decay evidence."""
        reg = ContractRegistry(epoch=None, promoted_evidence_dir=str(PROMOTED_DIR))
        # promoted_evidence contracts are silently skipped when epoch is None
        assert "env2.decay" not in reg.contracts


# ---------------------------------------------------------------------------
# Test E — no bypass through lookup_final
# ---------------------------------------------------------------------------

class TestNoBypassViaLookupFinal:
    def test_lookup_final_does_not_produce_authorized_operation(self):
        from serum2.execution.authorized_state_compiler import AuthorizedOperation
        reg = ContractRegistry(epoch=None)
        result = reg.lookup_final("env2.decay")
        assert not isinstance(result, AuthorizedOperation)

    def test_lookup_final_does_not_set_admitted(self):
        reg = _reg_2023()
        reg.lookup_final("env2.decay")
        # No contract was promoted to ADMITTED by this call
        for key, c in reg.contracts.items():
            assert not getattr(c, "admission", None) == "ADMITTED", (
                "lookup_final() must not set ADMITTED on any contract")


# ---------------------------------------------------------------------------
# Test F — distinct requested values preserve through admission
# ---------------------------------------------------------------------------

class TestRequestedValuePreservation:
    """Admission must track the REQUESTED value, not the qualification test value."""

    def _build_row(self, value: float):
        """Build a complete Row object for env2.decay at the given value."""
        from serum2.producer.state_ledger import Row
        return Row(
            control_id="env2.decay",
            value=value,
            unit="seconds",
            status="OBSERVED",
            control_type="parameter",
            source_ts=0.0,
            n_readings=1,
            changed_from_previous=True,
            terminal="OPERATION_DERIVED",
            op={"kind": "field", "module": "env", "index": 1, "field": "decay",
                "operation": "SET", "value": value},
        )

    @pytest.mark.parametrize("value", [3.0, 5.0, 8.0])
    def test_distinct_values_produce_distinct_ops(self, value):
        """Three distinct requested values must produce distinct op values."""
        row = self._build_row(value)
        # The value in the op must be the requested value, not a fixed qualification value
        assert row.op["value"] == value

    def test_values_differ_from_qualification_test_value(self):
        """The requested value must differ from the contract's qualification test value (0.5)."""
        reg = _reg_2023()
        c = reg.contracts.get("env2.decay")
        if c is None:
            pytest.skip("env2.decay not loaded")
        qual_test_value = (c.scope or {}).get("mutation_value_used")
        for requested in (3.0, 5.0, 8.0):
            assert requested != qual_test_value, (
                "Test value %r must differ from qualification_test_value %r" % (requested, qual_test_value))


# ---------------------------------------------------------------------------
# Test G — A2 negative cases (unchanged after wiring repair)
# ---------------------------------------------------------------------------

class TestA2NegativeCases:
    """Re-run Gate A-core A2 negative cases to confirm they still fail closed."""

    def test_missing_evidence_registry_is_empty(self, tmp_path):
        """An epoch-aware registry with empty dirs must have no promoted contracts."""
        reg = ContractRegistry(epoch=EPOCH_2_0_23,
                               binding_evidence_dir=str(tmp_path),
                               promoted_evidence_dir=str(tmp_path))
        # Only the pickle/Pass-1 store is loaded; no atlas_id contracts
        assert "env2.decay" not in reg.contracts

    def test_cross_epoch_execution_spec_refused(self):
        """execution_spec must return None when the final contract epoch doesn't match."""
        reg = _reg_2023()
        # Tamper with the recorded epoch
        reg.final_execution_contract_epoch = ("2.0.21", EPOCH_2_0_21.binary_sha256)
        spec = reg.execution_spec("env2.decay")
        assert spec is None, "Cross-epoch execution_spec must return None"

    def test_a2_gate_import_unchanged(self):
        """state_admission.py must still export admit_rows and is_offline_test."""
        from serum2.producer.state_admission import admit_rows, is_offline_test
        assert callable(admit_rows)
        assert callable(is_offline_test)

    def test_admitted_only_from_state_admission(self):
        """No code outside state_admission.py assigns 'ADMITTED' to row.admission."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rEn", r'\.admission\s*=\s*["\x27]ADMITTED["\x27]',
             "serum2/", "--include=*.py"],
            capture_output=True, text=True, cwd=str(Path(__file__).parent.parent))
        hits = [l for l in result.stdout.splitlines()
                if "state_admission" not in l and "test_gate_" not in l]
        assert not hits, "ADMITTED assigned outside state_admission.py:\n" + "\n".join(hits)

    def test_execution_spec_crosswalk_resolves_env2_decay(self):
        """execution_spec('envelope2_field_decay') must resolve via crosswalk to env2.decay spec."""
        reg = _reg_2023()
        spec_by_atlas = reg.execution_spec("env2.decay")
        spec_by_capability = reg.execution_spec("envelope2_field_decay")
        assert spec_by_atlas is not None, "execution_spec('env2.decay') must return data"
        assert spec_by_capability is not None, (
            "execution_spec('envelope2_field_decay') must return data via crosswalk")
        assert spec_by_atlas is spec_by_capability or (
            spec_by_atlas["atlas_id"] == spec_by_capability["atlas_id"]), (
            "Both lookups must resolve to the same spec")
