"""U2: Typed Parameter/Value/Unit Semantics

Proves that ConceptDerivationEngine populates ValueDomain from Atlas schema
for ATLAS_CANONICAL targets — without any hand-written tables in the Brain layer.

Architecture:
  Atlas frozen fields (control_type, unit, min_value, max_value)
    → quantity_type  (semantic category: time, rate, cutoff_frequency, …)
    → native_unit    (preserved verbatim from Atlas: "normalized rate", "seconds", …)
    → interpretation (direct | mode_dependent)

Key invariant: native_unit is NOT collapsed into a display/effective unit.
  lfo1.rate stores "normalized rate" natively; Hz is only valid in free mode.
  That distinction is preserved in interpretation="mode_dependent".
"""
import pytest
from serum2.producer.concept_representation import ConceptDerivationEngine, Provenance, ValueDomain
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.target_resolution import TargetResolver
from serum2.producer.producer_brain import _MCP_CONCEPT_BRIDGE
from serum2.reference.serum_atlas import normalize_control
from serum2.knowledge.step_6_6_capability_resolution import SemanticTargetMapping


def _engine():
    contract_registry = ContractRegistry()
    resolver = TargetResolver(
        contract_registry=contract_registry,
        semantic_targets={},
        mcp_host_map={},
        legacy_mappings={},
        mcp_bridge=_MCP_CONCEPT_BRIDGE,
        mapping_factory=SemanticTargetMapping,
        atlas_resolve=normalize_control,
    )
    return ConceptDerivationEngine(
        contract_registry=contract_registry,
        semantic_targets={},
        mcp_host_map={},
        target_resolver=resolver,
    )


@pytest.mark.parametrize("cid,expected_quantity,expected_native_unit,expected_interp", [
    # Time controls: Atlas unit IS the physical unit
    ("env1.hold",        "time",             "seconds",          "direct"),
    ("env1.decay",       "time",             "seconds",          "direct"),
    ("env1.attack",      "time",             "seconds",          "direct"),
    # Rate: native = "normalized rate"; effective unit is mode-dependent (Hz or BPM-domain)
    ("lfo1.rate",        "rate",             "normalized rate",  "mode_dependent"),
    # Cutoff: semantic quantity is cutoff_frequency; native representation is normalized 0-1
    ("filter1.cutoff",   "cutoff_frequency", "normalized cutoff", "direct"),
    # Voice count
    ("oscA.unison",      "count",            "voices",           "direct"),
    # Phase
    ("oscA.phase",       "angle",            "degrees",          "direct"),
    # Wavetable position
    ("oscA.wt_position", "wavetable_position", "frame",          "direct"),
])
def test_u2_value_domain_derives_from_atlas(cid, expected_quantity, expected_native_unit, expected_interp):
    """U2: ConceptDerivationEngine derives ValueDomain from Atlas frozen fields — no Brain tables."""
    engine = _engine()
    rep = engine.derive(cid)

    assert rep.provenance == Provenance.ATLAS_CANONICAL, \
        f"{cid}: expected ATLAS_CANONICAL, got {rep.provenance}"
    assert rep.value_domain is not None, \
        f"{cid}: value_domain must be populated from Atlas"
    vd = rep.value_domain
    assert vd.type == expected_quantity, \
        f"{cid}: quantity_type expected={expected_quantity!r}, got={vd.type!r}"
    assert vd.unit == expected_native_unit, \
        f"{cid}: native_unit expected={expected_native_unit!r}, got={vd.unit!r}"
    assert vd.interpretation == expected_interp, \
        f"{cid}: interpretation expected={expected_interp!r}, got={vd.interpretation!r}"


def test_u2_lfo_rate_native_semantics_preserved():
    """
    Critical U2 invariant: lfo1.rate native storage is 'normalized rate', not Hz.
    Hz is only valid in free mode (beat_sync=False), which is a contextual interpretation.
    U2 must NOT collapse native semantics into the effective free-mode display unit.
    """
    rep = _engine().derive("lfo1.rate")
    vd = rep.value_domain

    assert vd is not None
    # Quantity category
    assert vd.type == "rate", f"Expected quantity_type='rate', got {vd.type!r}"
    # Native unit — must match Atlas verbatim
    assert vd.unit == "normalized rate", \
        f"U2 must preserve Atlas native unit 'normalized rate', got {vd.unit!r}. " \
        f"Do NOT replace with 'Hz' — that is a contextual/free-mode interpretation only."
    # Interpretation — signals that effective unit is context-dependent
    assert vd.interpretation == "mode_dependent", \
        f"lfo1.rate must be mode_dependent; Hz applies only when beat_sync=False"
    # Range from Atlas (raw 0-100; raw≈Hz in free mode per calibration)
    assert vd.min_value == 0.0
    assert vd.max_value == 100.0


def test_u2_env1_hold_direct_semantics():
    """env1.hold: Atlas unit IS the physical unit — no contextual disambiguation needed."""
    rep = _engine().derive("env1.hold")
    vd = rep.value_domain
    assert vd.type == "time"
    assert vd.unit == "seconds"
    assert vd.interpretation == "direct"
    assert vd.min_value == 0.0
    assert vd.max_value == 5.2


def test_u2_filter_cutoff_semantic_quantity_preserved():
    """filter1.cutoff: semantic quantity is cutoff_frequency; native representation is normalized."""
    rep = _engine().derive("filter1.cutoff")
    vd = rep.value_domain
    assert vd.type == "cutoff_frequency", \
        f"Semantic quantity should be 'cutoff_frequency', not generic 'normalized'"
    assert vd.unit == "normalized cutoff", \
        f"Native Atlas unit should be preserved: 'normalized cutoff'"


def test_u2_operation_type_numeric_for_continuous():
    """Continuous Atlas controls map to operation_type='numeric' for Brain direction logic."""
    engine = _engine()
    for cid in ["lfo1.rate", "env1.hold", "filter1.cutoff"]:
        rep = engine.derive(cid)
        assert rep.operation_type == "numeric", \
            f"{cid}: expected operation_type='numeric', got {rep.operation_type!r}"
        assert rep.generic_language_keywords, \
            f"{cid}: numeric target must have direction keywords"


def test_u2_value_domain_present_in_derivation_chain():
    """U2 annotation appears in the derivation chain for ATLAS_CANONICAL targets."""
    rep = _engine().derive("lfo1.rate")
    u2_entries = [e for e in rep.derivation_chain if "U2" in e]
    assert u2_entries, \
        f"Derivation chain should contain U2 annotation: {rep.derivation_chain}"


def test_u2_does_not_invent_domain_for_unknown_target():
    """Unknown Atlas target still gets MISSING provenance, no ValueDomain."""
    rep = _engine().derive("completely.bogus.control")
    assert rep.provenance == Provenance.MISSING
    assert rep.value_domain is None


if __name__ == "__main__":
    import sys
    cases = [
        ("env1.hold",        "time",             "seconds",           "direct"),
        ("lfo1.rate",        "rate",             "normalized rate",   "mode_dependent"),
        ("filter1.cutoff",   "cutoff_frequency", "normalized cutoff", "direct"),
    ]
    tests = [
        (f"value_domain_{cid}", lambda cid=c, eq=eq, eu=eu, ei=ei:
         test_u2_value_domain_derives_from_atlas(cid, eq, eu, ei))
        for c, eq, eu, ei in cases
    ] + [
        ("lfo_native_semantics", test_u2_lfo_rate_native_semantics_preserved),
        ("env1_direct_semantics", test_u2_env1_hold_direct_semantics),
        ("filter_cutoff_quantity", test_u2_filter_cutoff_semantic_quantity_preserved),
        ("operation_type_numeric", test_u2_operation_type_numeric_for_continuous),
        ("derivation_chain_u2", test_u2_value_domain_present_in_derivation_chain),
        ("no_domain_unknown", test_u2_does_not_invent_domain_for_unknown_target),
    ]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED {name}")
            passed += 1
        except Exception as e:
            print(f"FAILED {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
