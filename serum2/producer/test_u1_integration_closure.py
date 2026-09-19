"""U1 Integration Closure: End-to-End Reference -> Brain -> Capability Independence

Proves U1 across the complete pipeline:
  1. Atlas knows env1.hold
  2. TargetResolver produces canonical concept independently
  3. ConceptDerivationEngine accepts canonical concept (ATLAS_CANONICAL)
  4. CapabilityResolver correctly says REFUSED_NO_CAPABILITY

ATLAS_CANONICAL means IDENTITY ESTABLISHED, not CAPABILITY ESTABLISHED.
"""
from serum2.producer.concept_representation import ConceptDerivationEngine, Provenance
from serum2.producer.target_resolution import TargetResolver
from serum2.producer.producer_brain import _MCP_CONCEPT_BRIDGE
from serum2.reference.serum_atlas import normalize_control
from serum2.producer.contract_registry import ContractRegistry
from serum2.knowledge.step_6_6_capability_resolution import SemanticTargetMapping


def _make_resolver(contract_registry):
    return TargetResolver(
        contract_registry=contract_registry,
        semantic_targets={},
        mcp_host_map={},
        legacy_mappings={},
        mcp_bridge=_MCP_CONCEPT_BRIDGE,
        mapping_factory=SemanticTargetMapping,
        atlas_resolve=normalize_control
    )


def test_u1_brain_layer_accepts_atlas_canonical_target():
    """Step 3 closure: ConceptDerivationEngine produces ATLAS_CANONICAL for env1.hold."""
    contract_registry = ContractRegistry()
    resolver = _make_resolver(contract_registry)

    target_res = resolver.resolve("set Env1.Hold to 1 ms", None)
    assert target_res.refusal is None, f"TargetResolver should resolve: {target_res.refusal}"
    assert target_res.canonical_id == "env1.hold"
    assert target_res.concept == "canonical:env1.hold"

    derivation = ConceptDerivationEngine(
        contract_registry=contract_registry,
        semantic_targets={},
        mcp_host_map={},
        target_resolver=resolver
    )
    concept_res = derivation.derive_from_resolution(res=target_res, surface="Env1.Hold")

    assert concept_res.provenance == Provenance.ATLAS_CANONICAL, \
        f"U1 FAILED: got {concept_res.provenance}. Brain must accept Atlas-known targets."
    assert concept_res.semantic_target_name is None or concept_res.semantic_target_name == ""
    assert concept_res.capability_key is None


def test_u1_full_chain_env1_hold_reaches_refused_no_capability():
    """
    Full U1 closure: env1.hold flows all the way to CapabilityResolver.

    Chain:
        REAL Atlas
          -> TargetResolver (succeeds)
          -> ConceptDerivationEngine (ATLAS_CANONICAL)
          -> Capability layer (REFUSED_NO_CAPABILITY)

    Proves: ATLAS_CANONICAL = IDENTITY ESTABLISHED, not CAPABILITY ESTABLISHED.
    env1.hold is Atlas-known and not in SEMANTIC_TARGETS; it must fail at CAPABILITY, not BRAIN.
    """
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.compiler.targets import SEMANTIC_TARGETS

    # Verify boundary: env1.hold must not be registered (otherwise test is invalid)
    assert "env1.hold" not in SEMANTIC_TARGETS, "Test pre-condition: env1.hold not in SEMANTIC_TARGETS"
    assert normalize_control("env1.hold").status == "EXACT", "Test pre-condition: Atlas must know env1.hold"

    brain = ProducerBrain()
    result = brain.execute(ProducerRequest(user_intent="shorter Env1.Hold to 1 ms"))

    print(f"\nFull Chain Test Result:")
    print(f"  refusal code:  {result.refusal['code']}")
    print(f"  refusal layer: {result.refusal['layer']}")
    print(f"  canonical_target: {result.refusal['canonical_target']}")

    assert result.refusal is not None, "env1.hold has no contract; must be refused"
    assert result.refusal["code"] == "REFUSED_NO_CAPABILITY", \
        f"Must fail at CAPABILITY layer, got {result.refusal['code']}"
    assert result.refusal["layer"] == "CAPABILITY_RESOLUTION", \
        f"Expected CAPABILITY_RESOLUTION, got {result.refusal['layer']}"
    # canonical:env1.hold is carried in the reason; canonical_target is None on this path
    # because the legacy semantic_target field is not set for ATLAS_CANONICAL targets.
    assert "env1.hold" in result.refusal["reason"], \
        f"Refusal reason should reference env1.hold: {result.refusal['reason']}"


if __name__ == "__main__":
    import sys
    tests = [
        ("brain_layer_accepts_atlas_canonical", test_u1_brain_layer_accepts_atlas_canonical_target),
        ("full_chain_reaches_refused_no_capability", test_u1_full_chain_env1_hold_reaches_refused_no_capability),
    ]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"\nPASSED {name}")
            passed += 1
        except Exception as e:
            print(f"\nFAILED {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
