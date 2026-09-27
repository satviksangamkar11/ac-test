"""Regression tests for two real bugs found during an actual Local W1 native run against
serum-preset-orchestrator commit 95e4ea1: env1.attack (route "Env1.Attack") reached ADVISORY_ONLY
through the WRONG route (ableton_mcp instead of dawdreamer_serum), and once routed correctly, crashed
with KeyError('mutation_value_used') before a plan could even be produced. Both fixes are generic --
no per-target branch in route selection or plan-building logic -- verified here against the real
ProducerBrain admission chain, zero mocks.

Bug 1 (capability_crosswalk): ContractRegistry.get_by_capability_key("envelope_field_attack") returned
None because serum2/producer/capability_crosswalk.py's CAPABILITY_KEY_TO_ATLAS_ID (an intentionally
small, hand-reviewed allowlist -- see that module's own docstring) had an entry for "envelope2_field_decay"
but none for "envelope_field_attack", even though env1.attack has a real, qualified, accessor-bound
contract. RouteSelector then fell through to ABLETON_MCP (MCP_HOST_MAP does have "Env1.Attack") instead
of the correct DAWDREAMER_SERUM route -- silently routing a Serum-internal envelope field through
Ableton host-parameter automation, which architecture explicitly prohibits (Env1.Attack is not on the
127-param Ableton-exposed surface). Fixed by adding the missing, human-reviewed crosswalk entry -- the
exact mechanism the module already documents for this situation, not a change to the matching logic.

Bug 2 (producer_brain._build_serum_preset_plan): once routed correctly, `scope["mutation_value_used"]`
KeyError'd, because promote_verified_evidence() (the generic promoter behind the ENTIRE
binding_evidence_mcp_exec_v1 corpus -- 222 of 232 real SERUM_PRESET_STRUCTURAL contracts) names this
same fact "mutated_value", not "mutation_value_used" (the older Pass-1/candidate_binding_qualifier
schema). Fixed by preferring "mutation_value_used" when present, falling back to "mutated_value" --
never silently defaulting, never guessing a value.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer.capability_crosswalk import CAPABILITY_KEY_TO_ATLAS_ID
from serum2.producer.serum_preset_orchestrator import _generate_canonical_preset

BINDING_DIR = Path(__file__).parent.parent / "parameter_characterization" / "binding_evidence"
PROMOTED_DIR = Path(__file__).parent.parent / "parameter_characterization" / "binding_evidence_mcp_exec_v1"


def _brain() -> ProducerBrain:
    return ProducerBrain(epoch=EPOCH_2_0_23, binding_evidence_dir=str(BINDING_DIR),
                         promoted_evidence_dir=str(PROMOTED_DIR))


class TestCapabilityCrosswalkCoversEnv1Attack:
    def test_crosswalk_has_the_reviewed_entry(self):
        assert CAPABILITY_KEY_TO_ATLAS_ID.get("envelope_field_attack") == "env1.attack"

    def test_get_by_capability_key_resolves_env1_attack(self):
        reg = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=str(BINDING_DIR),
                               promoted_evidence_dir=str(PROMOTED_DIR))
        c = reg.get_by_capability_key("envelope_field_attack")
        assert c is not None
        assert c is reg.get("env1.attack"), "the alias must point at the SAME contract object, never a copy"
        assert c.execution_binding.resolver_operation_id == "envelopes[0].attack"


class TestEnv1AttackRoutesToDawdreamerSerum:
    """The real bug: without the crosswalk entry, this reached ADVISORY_ONLY via the WRONG route."""

    def test_env1_attack_route_is_dawdreamer_serum_not_ableton_mcp(self):
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent="set Env1.Attack to 5.0 seconds",
                                               semantic_target="Env1.Attack"))
        assert result.execution_route == "dawdreamer_serum", (
            "Env1.Attack is a Serum-internal envelope field, never on the Ableton-exposed 127-param "
            "surface -- routing it through ableton_mcp would fake a Serum-internal mutation via host "
            "parameter automation, which architecture explicitly prohibits. Got route=%r, error=%r"
            % (result.execution_route, result.error)
        )
        assert result.execution_status == "ADVISORY_ONLY", result.error
        assert not hasattr(result, "_mcp_plan"), "must not have taken the MCP fallback path"
        assert getattr(result, "_serum_preset_plan", None) is not None


class TestPlanBuildingHandlesBothScopeSchemas:
    """The real bug: scope["mutation_value_used"] KeyError'd for any contract sourced purely from
    evidence_promotion.promote_verified_evidence (the "mutated_value" schema)."""

    def test_env1_attack_plan_builds_without_keyerror(self):
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent="set Env1.Attack to 5.0 seconds",
                                               semantic_target="Env1.Attack"))
        assert result.execution_status == "ADVISORY_ONLY", result.error
        plan = result._serum_preset_plan
        assert plan["status"] == "ADVISORY_ONLY"
        assert plan["mutation_target_path"] == "Env0.plainParams.kParamAttack"
        # qualification_test_value must come from the real evidence's "mutated_value" fallback,
        # never fabricated or left as a KeyError.
        assert plan["qualification_test_value"] == pytest.approx(5.000000000000001)

    def test_contract_with_neither_scope_key_refuses_not_crashes(self, monkeypatch):
        """A contract missing BOTH schema keys must refuse cleanly (REFUSED_AUTHORITY), never crash
        the brain with an unhandled KeyError."""
        brain = _brain()
        contract = brain._registry.get("env1.attack")
        original_scope = dict(contract.scope)
        stripped = {k: v for k, v in original_scope.items()
                   if k not in ("mutation_value_used", "mutated_value")}
        import dataclasses
        stripped_contract = dataclasses.replace(contract, scope=stripped)
        monkeypatch.setitem(brain._registry.contracts, "env1.attack", stripped_contract)
        monkeypatch.setitem(brain._registry.contracts, "envelope_field_attack", stripped_contract)

        result = brain.execute(ProducerRequest(user_intent="set Env1.Attack to 5.0 seconds",
                                               semantic_target="Env1.Attack"))
        assert result.execution_status == "REFUSED_AUTHORITY", (
            "expected a clean refusal, got %r (error=%r)" % (result.execution_status, result.error)
        )


class TestEnv1AttackFullOrchestratorChain:
    """End to end: the exact chain the Local W1 run needs, now unblocked."""

    def test_env1_attack_produces_genuine_preset_via_real_compile_ops(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SERUM_PRESETS_PATH", str(tmp_path))
        brain = _brain()
        result = brain.execute(ProducerRequest(user_intent="set Env1.Attack to 5.0 seconds",
                                               semantic_target="Env1.Attack"))
        assert result.execution_status == "ADVISORY_ONLY", result.error

        gen = _generate_canonical_preset(result, result._serum_preset_plan, EPOCH_2_0_23, brain)

        assert gen["status"] == "SUCCESS", gen
        preset_path = Path(gen["preset_path"])
        assert preset_path.is_file()
        assert preset_path.read_bytes()[:8] == b"XferJson"
        assert hashlib.sha256(preset_path.read_bytes()).hexdigest() == gen["preset_sha256"]
