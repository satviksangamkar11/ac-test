"""U1 Architectural Test: Canonical Target Identity Independence

RED TEST: Proves current code fails to decouple canonical identity from capability.

SETUP:
  - Real Serum Atlas (normalize_control) knows "env1.hold"
  - Real semantic_targets DOES NOT include env1.hold
  - Real mcp_host_map DOES NOT include env1.hold
  - No capability contract exists for envelope1_field_hold

CURRENT CODE: returns REFUSED_NO_BRAIN_CONCEPT (wrong layer)
DESIRED AFTER U1: returns canonical concept (no refusal)

This proves that target identity must be independent of capability qualification.
"""
from serum2.producer.target_resolution import TargetResolver, REFUSED_NO_BRAIN_CONCEPT, LAYER_BRAIN
from serum2.compiler.targets import SEMANTIC_TARGETS
from serum2.compiler.mcp_intent import MCP_HOST_MAP
from serum2.producer.producer_brain import _MCP_CONCEPT_BRIDGE
from serum2.reference.serum_atlas import normalize_control
from serum2.producer.contract_registry import ContractRegistry
from serum2.knowledge.step_6_6_capability_resolution import SemanticTargetMapping


def test_u1_real_atlas_known_but_unregistered_target_gets_canonical_concept():
    """
    BOUNDARY TEST: Atlas knows env1.hold, but it's not in ANY registry.

    Expected: canonical concept derived from canonical_id alone
    Current (before U1): REFUSED_NO_BRAIN_CONCEPT
    """

    # Verify the boundary condition: Atlas knows it, registries don't
    atlas_result = normalize_control("env1.hold")
    assert atlas_result.status == "EXACT", f"Atlas should know env1.hold, got {atlas_result.status}"
    assert atlas_result.canonical_id == "env1.hold"

    # Confirm it's NOT in the registries (to set up the boundary)
    assert "env1.hold" not in SEMANTIC_TARGETS, "env1.hold should not be pre-registered"
    assert "env1.hold" not in MCP_HOST_MAP, "env1.hold should not be in MCP_HOST_MAP"

    # Create resolver with REAL Atlas and real contract registry
    # (ContractRegistry loads canonical contracts; for this test env1.hold will have no contract)
    contract_registry = ContractRegistry()

    resolver = TargetResolver(
        contract_registry=contract_registry,
        semantic_targets={},  # INTENTIONALLY EMPTY: boundary condition
        mcp_host_map={},      # INTENTIONALLY EMPTY: boundary condition
        legacy_mappings={},
        mcp_bridge=_MCP_CONCEPT_BRIDGE,
        mapping_factory=SemanticTargetMapping,
        atlas_resolve=normalize_control  # REAL Atlas
    )

    # Test the boundary
    result = resolver.resolve("set Env1.Hold to 1 ms", None)

    # U1 REQUIREMENT: No refusal; canonical concept established
    print(f"\nU1 Test Result:")
    print(f"  refusal: {result.refusal}")
    print(f"  canonical_id: {result.canonical_id}")
    print(f"  concept: {result.concept}")
    print(f"  capability_key: {result.capability_key}")

    assert result.refusal is None, \
        f"U1 FAILED: Expected no refusal, but got {result.refusal.code} ({result.refusal.layer}): {result.refusal.reason}"
    assert result.canonical_id == "env1.hold", f"Expected canonical_id=env1.hold, got {result.canonical_id}"
    assert result.concept is not None, f"Expected concept to be set, got None"
    assert "canonical:env1.hold" == result.concept or "canonical:env1_hold" == result.concept, \
        f"Expected canonical concept, got {result.concept}"

    # U1 BOUNDARY: Registry associations remain absent
    assert result.capability_key is None, f"Expected no capability_key (not registered), got {result.capability_key}"
    assert result.mapping is None, f"Expected no mapping (no contract), got {result.mapping}"


def test_u1_genuinely_unknown_atlas_target_still_fails_at_reference():
    """
    Boundary: Unknown Atlas target must still fail at REFERENCE layer, not BRAIN.
    """
    resolver = TargetResolver(
        contract_registry=ContractRegistry(),
        semantic_targets={},
        mcp_host_map={},
        legacy_mappings={},
        mcp_bridge=_MCP_CONCEPT_BRIDGE,
        mapping_factory=SemanticTargetMapping,
        atlas_resolve=normalize_control
    )

    result = resolver.resolve("set unknown.bogus to 42", None)

    # Should fail at REFERENCE layer, NOT BRAIN layer
    assert result.refusal is not None, "Unknown target should have refusal"
    assert result.refusal.code == "REFUSED_UNRESOLVED_REFERENCE", \
        f"Unknown target must fail at REFERENCE, got {result.refusal.code}"


def test_u1_ambiguous_atlas_target_still_fails_at_reference():
    """
    Boundary: Ambiguous Atlas target must still fail correctly.
    """
    resolver = TargetResolver(
        contract_registry=ContractRegistry(),
        semantic_targets={},
        mcp_host_map={},
        legacy_mappings={},
        mcp_bridge=_MCP_CONCEPT_BRIDGE,
        mapping_factory=SemanticTargetMapping,
        atlas_resolve=normalize_control
    )

    # "cutoff" is ambiguous (filter1.cutoff vs filter2.cutoff)
    result = resolver.resolve("set cutoff", None)

    assert result.refusal is not None, "Ambiguous target should have refusal"
    assert result.refusal.code == "REFUSED_AMBIGUOUS_REFERENCE", \
        f"Ambiguous target must fail at REFERENCE, got {result.refusal.code}"


if __name__ == "__main__":
    import sys
    print("=" * 80)
    print("U1 Architectural Test: Canonical Target Identity Independence")
    print("=" * 80)

    tests = [
        ("test_u1_real_atlas_known_but_unregistered_target",
         test_u1_real_atlas_known_but_unregistered_target_gets_canonical_concept),
        ("test_u1_unknown_atlas_reference_failure",
         test_u1_genuinely_unknown_atlas_target_still_fails_at_reference),
        ("test_u1_ambiguous_atlas_reference_failure",
         test_u1_ambiguous_atlas_target_still_fails_at_reference),
    ]

    passed = failed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}\n")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}")
            print(f"  REASON: {e}\n")
            failed += 1

    print("=" * 80)
    print(f"Result: {passed} passed, {failed} failed")
    print("=" * 80)
    sys.exit(0 if failed == 0 else 1)
