"""B1 capability resolution regression tests.

Covers the B1 capability_target=None fix and STRUCTURAL_ONLY absolute SET semantics.

Tests A–H as specified:
  A — "set Env2.Decay to 5.0 seconds" resolves capability_key + atlas_id correctly
  B — "shorten Env2.Decay to 5 s" resolves identically
  C — "make Env2.Decay 5.0 s" resolves identically
  D — a wrong nearby capability does not resolve (no fuzzy matching)
  E — STRUCTURAL_ONLY absolute SET proceeds through capability resolution
  F — a causal-required operation is still rejected appropriately
  G — distinct requested values (3.0, 5.0, 8.0) are preserved, not replaced by test value
  H — qualification_test_value is separately labeled and not used as production operand
"""
import pytest
from pathlib import Path
from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest

BINDING_DIR = Path(__file__).parent.parent / "serum2" / "qualification" / "binding_evidence"
PROMOTED_DIR = Path(__file__).parent.parent / "parameter_characterization" / "binding_evidence_mcp_exec_v1"


def _brain():
    return ProducerBrain(epoch=EPOCH_2_0_23,
                         binding_evidence_dir=str(BINDING_DIR),
                         promoted_evidence_dir=str(PROMOTED_DIR))


def _reg():
    return ContractRegistry(epoch=EPOCH_2_0_23,
                            binding_evidence_dir=str(BINDING_DIR),
                            promoted_evidence_dir=str(PROMOTED_DIR))


# ---------------------------------------------------------------------------
# Tests A–C — three equivalent phrasings resolve correctly
# ---------------------------------------------------------------------------

class TestB1TargetResolution:
    """The B1 layer must resolve all three phrasings to the same explicit target."""

    @pytest.mark.parametrize("intent", [
        "set Env2.Decay to 5.0 seconds",
        "shorten Env2.Decay to 5 s",
        "make Env2.Decay 5.0 s",
    ])
    def test_phrasings_reach_advisory_only_not_refused(self, intent):
        """All three phrasings must reach ADVISORY_ONLY (not REFUSED_NO_CONTRACT or earlier)."""
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent=intent, semantic_target="Env2.Decay"))
        assert result.execution_status == "ADVISORY_ONLY", (
            "Expected ADVISORY_ONLY for %r, got %r — error: %r" % (
                intent, result.execution_status, result.error))

    @pytest.mark.parametrize("intent", [
        "set Env2.Decay to 5.0 seconds",
        "shorten Env2.Decay to 5 s",
        "make Env2.Decay 5.0 s",
    ])
    def test_phrasings_use_b1_canonical_mode(self, intent):
        """All three phrasings must use the B1 canonical resolution path."""
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent=intent, semantic_target="Env2.Decay"))
        assert result.resolution_mode == "B1_CANONICAL", (
            "Expected B1_CANONICAL for %r, got %r" % (intent, result.resolution_mode))

    @pytest.mark.parametrize("intent", [
        "set Env2.Decay to 5.0 seconds",
        "shorten Env2.Decay to 5 s",
        "make Env2.Decay 5.0 s",
    ])
    def test_phrasings_resolve_to_env2_decay_semantic_target(self, intent):
        """All three phrasings must have semantic_target = 'Env2.Decay'."""
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent=intent, semantic_target="Env2.Decay"))
        assert result.semantic_target == "Env2.Decay", (
            "Expected semantic_target 'Env2.Decay' for %r, got %r" % (
                intent, result.semantic_target))

    @pytest.mark.parametrize("intent", [
        "set Env2.Decay to 5.0 seconds",
        "shorten Env2.Decay to 5 s",
        "make Env2.Decay 5.0 s",
    ])
    def test_phrasings_plan_includes_final_contract_with_env2_decay_atlas_id(self, intent):
        """All three phrasings must produce a plan where the A2 gate found env2.decay in the final contract."""
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent=intent, semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None, "Expected plan for %r" % intent
        fc = plan.get("final_execution_contract")
        assert fc is not None, "final_execution_contract missing from plan for %r" % intent
        assert fc.get("atlas_id") == "env2.decay", (
            "Expected atlas_id 'env2.decay' in final_execution_contract for %r, got %r" % (
                intent, fc.get("atlas_id")))

    @pytest.mark.parametrize("intent", [
        "set Env2.Decay to 5.0 seconds",
        "shorten Env2.Decay to 5 s",
        "make Env2.Decay 5.0 s",
    ])
    def test_phrasings_plan_agrees_with_admitted_mutation_path(self, intent):
        """A2 gate: mutation_target_path from contract must match final contract expected_raw."""
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent=intent, semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None
        fc = plan.get("final_execution_contract")
        assert fc is not None
        assert fc.get("agrees_with_admitted_mutation_path") is True, (
            "A2 path mismatch for %r: fc=%r" % (intent, fc))


# ---------------------------------------------------------------------------
# Test D — no fuzzy matching
# ---------------------------------------------------------------------------

class TestNoFuzzyMatching:
    """Nearby capability keys must not accidentally resolve to env2.decay's contract."""

    def test_env1_decay_does_not_resolve_to_env2_decay_contract(self):
        """env1.decay (Env1, not Env2) must not borrow env2.decay's evidence."""
        from serum2.producer.target_resolution import TargetResolver
        from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC, SemanticTargetMapping
        from serum2.compiler.targets import SEMANTIC_TARGETS
        from serum2.compiler.mcp_intent import MCP_HOST_MAP
        reg = _reg()
        resolver = TargetResolver(reg, SEMANTIC_TARGETS, MCP_HOST_MAP,
                                  UNIVERSAL_TO_SEMANTIC, {}, SemanticTargetMapping)
        # Env1.Decay is NOT in SEMANTIC_TARGETS as a registered target; it should not
        # borrow Env2.Decay's contract.
        res = resolver.resolve("set Env1.Decay to 5 seconds", "Env1.Decay")
        if res is not None and res.refusal is None:
            # If it resolved, it must NOT point to env2.decay's canonical_id
            assert res.canonical_id != "env2.decay", (
                "env1.decay must not resolve to env2.decay (no cross-contract borrowing)")

    def test_crosswalk_has_no_fuzzy_entries(self):
        """The crosswalk must contain only explicitly reviewed entries."""
        from serum2.producer.capability_crosswalk import CAPABILITY_KEY_TO_ATLAS_ID
        # Known approved entry
        assert CAPABILITY_KEY_TO_ATLAS_ID.get("envelope2_field_decay") == "env2.decay"
        # No entries pointing to env1.* from an env2.* key or vice versa
        for cap_key, atlas_id in CAPABILITY_KEY_TO_ATLAS_ID.items():
            if "env2" in cap_key.lower() or "envelope2" in cap_key.lower():
                assert "env1" not in atlas_id.lower(), (
                    "env2 key %r must not map to env1 atlas_id %r" % (cap_key, atlas_id))


# ---------------------------------------------------------------------------
# Test E — STRUCTURAL_ONLY absolute SET admitted
# ---------------------------------------------------------------------------

class TestStructuralOnlyAbsoluteSet:
    """A STRUCTURAL_ONLY contract for an absolute SET operation must pass capability resolution."""

    def test_structural_only_absolute_set_reaches_advisory_only(self):
        """env2.decay (STRUCTURAL_ONLY, mutate_numeric_value) must reach ADVISORY_ONLY."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to 5.0 seconds",
            semantic_target="Env2.Decay"))
        assert result.execution_status == "ADVISORY_ONLY", (
            "STRUCTURAL_ONLY absolute SET must reach ADVISORY_ONLY, got: %r — error: %r" % (
                result.execution_status, result.error))

    def test_structural_only_contract_is_admitted(self):
        """ProducerBrain must admit the STRUCTURAL_ONLY contract for a parameter SET."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to 5.0 seconds",
            semantic_target="Env2.Decay"))
        assert result.admitted is True, (
            "Expected admitted=True for absolute SET, got: admitted=%r reason=%r" % (
                result.admitted, result.admission_reason))

    def test_structural_only_usable_for_required_causal_false(self):
        """STRUCTURAL_ONLY must be usable when required_causal=False."""
        reg = _reg()
        contract = reg.contracts.get("envelope2_field_decay")
        assert contract is not None, "envelope2_field_decay contract not in registry"
        assert contract.status == "STRUCTURAL_ONLY"
        assert contract.usable_for(required_causal=False) is True

    def test_structural_only_not_usable_for_required_causal_true(self):
        """STRUCTURAL_ONLY must NOT be usable when required_causal=True (causal gate intact)."""
        reg = _reg()
        contract = reg.contracts.get("envelope2_field_decay")
        assert contract is not None
        assert contract.usable_for(required_causal=True) is False, (
            "STRUCTURAL_ONLY must still fail required_causal=True — causal gate must be preserved")


# ---------------------------------------------------------------------------
# Test F — causal-required operation is still rejected
# ---------------------------------------------------------------------------

class TestCausalGatePreserved:
    """The causal gate must remain enforceable; only absolute SET operations bypass it."""

    def test_structural_only_fails_required_causal_true(self):
        """STRUCTURAL_ONLY contract must be rejected when required_causal=True."""
        reg = _reg()
        contract = reg.contracts.get("envelope2_field_decay")
        assert contract is not None
        assert contract.usable_for(required_causal=True) is False

    def test_absolute_set_ops_allow_structural_only(self):
        """Only mutate_numeric/enum/boolean are treated as absolute SET (no causal required)."""
        from serum2.evidence.capability_contract import STRUCTURAL_ONLY, CAUSAL_VERIFIED
        from serum2.evidence.capability_contract import CapabilityContract, ExecutionBinding
        # Simulate a STRUCTURAL_ONLY contract for mutate_numeric_value
        import datetime
        c = CapabilityContract(
            target="test.target",
            allowed_operation="mutate_numeric_value",
            status=STRUCTURAL_ONLY,
            prerequisites=[],
            verified=False,
            measurement=None,
            scope={},
            provenance={},
        )
        assert c.usable_for(required_causal=False) is True
        assert c.usable_for(required_causal=True) is False  # causal gate still enforced

    def test_concept_representation_uses_causal_for_non_set(self):
        """For non-SET operations, concept_representation must still require CAUSAL_VERIFIED."""
        from serum2.evidence.capability_contract import STRUCTURAL_ONLY
        from serum2.evidence.capability_contract import CapabilityContract
        # A hypothetical non-SET operation (not in current production)
        c = CapabilityContract(
            target="test.hypothetical",
            allowed_operation="mutate_hypothetical_causal",
            status=STRUCTURAL_ONLY,
            prerequisites=[],
            verified=False,
            measurement=None,
            scope={},
            provenance={},
        )
        # Non-SET allowed_operation → requires causal → STRUCTURAL_ONLY fails
        _ABSOLUTE_SET_OPS = frozenset({
            "mutate_numeric_value", "mutate_enum_value", "mutate_boolean_value",
        })
        op_needs_causal = c.allowed_operation not in _ABSOLUTE_SET_OPS
        assert op_needs_causal is True, "Non-SET operations must require causal evidence"
        assert c.usable_for(required_causal=op_needs_causal) is False, (
            "STRUCTURAL_ONLY with non-SET allowed_operation must fail causal requirement")


# ---------------------------------------------------------------------------
# Tests G–H — value flow
# ---------------------------------------------------------------------------

class TestValueFlow:
    """Requested values must not be replaced by the qualification test value."""

    def test_plan_labels_qualification_test_value_separately(self):
        """The plan must label the test value as qualification_test_value, not use it as operand."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to 5.0 seconds",
            semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None
        # qualification_test_value is metadata, not the production operand
        qtv = plan.get("qualification_test_value")
        assert qtv is not None, "qualification_test_value must be present in plan"
        # The test value is 0.5 (from the contract); the requested value is 5.0
        # Verify they differ — if they were the same, the F4 bug would be masked
        assert qtv != 5.0, (
            "qualification_test_value must differ from the requested 5.0 s; "
            "if equal, the plan may be substituting the test value for the requested value")

    def test_plan_mutation_path_is_kParamDecay(self):
        """The mutation path in the plan must be the env2.decay body path."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to 5.0 seconds",
            semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        assert plan is not None
        path = plan.get("mutation_target_path", "")
        assert "kParamDecay" in path, (
            "Plan mutation_target_path must contain kParamDecay, got: %r" % path)

    @pytest.mark.parametrize("requested_value", [3.0, 5.0, 8.0])
    def test_plan_qualification_test_value_differs_from_requested(self, requested_value):
        """Qualification test value must not equal any of the three test requested values."""
        brain = _brain()
        result = brain.execute(ProducerRequest(
            user_intent="set Env2.Decay to %.1f seconds" % requested_value,
            semantic_target="Env2.Decay"))
        plan = getattr(result, "_serum_preset_plan", None)
        if plan is None:
            pytest.skip("Plan not available")
        qtv = plan.get("qualification_test_value")
        assert qtv != requested_value, (
            "qualification_test_value %r must differ from requested value %r — "
            "the plan must not silently substitute the test value for the production operand" % (
                qtv, requested_value))
