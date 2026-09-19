"""Conformance tests for docs/VLP1_Fully_Revised_Architecture.md sections 6.1, 7.1, 9, 17, 18, 19.

Ordered explicit-target resolution over existing data (Atlas + target registries + contracts),
the structured refusal record, and the no-hardcoding invariant.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = str(Path(__file__).parent.parent.parent)
KNOWLEDGE_DIR = str(Path(__file__).parent.parent / "knowledge")
for p in [ROOT, KNOWLEDGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer import target_resolution as tr
from serum2.producer.target_names import normalize_target_name, find_target_tokens, find_surface_tokens

SRC = Path(__file__).parent


def _run(intent, semantic_target=None):
    return ProducerBrain().execute(ProducerRequest(user_intent=intent, semantic_target=semantic_target,
                                                   mode="EXECUTE", visual_mode="NEVER"))


def _plan(r):
    return getattr(r, "_serum_preset_plan", None) or {}


# ---- section 18: an explicit target can never become another control -------------------------
@pytest.mark.parametrize("word", ["shorter", "longer", "less", "more", "lower", "higher"])
@pytest.mark.parametrize("spelling", ["Env1.Decay", "env1.decay", "ENV1.DECAY"])
def test_env1_decay_never_becomes_env1_release(word, spelling):
    for r in (_run("%s %s to 5" % (word, spelling)), _run("%s the value" % word, spelling)):
        assert r.resolved_concept != "note-release"
        assert _plan(r).get("contract_id") != "envelope_field_release"
        assert _plan(r).get("mutation_target_path") != "Env0.plainParams.kParamRelease"


def test_supported_explicit_target_resolves_only_to_itself():
    r = _run("longer Env1.Release to 120 ms")
    assert (r.resolved_concept, _plan(r)["contract_id"]) == ("note-release", "envelope_field_release")
    r = _run("longer Env1.Attack to 1.5 ms")
    assert (r.resolved_concept, _plan(r)["contract_id"]) == ("envelope-attack", "envelope_field_attack")


# ---- section 6.1 / 28: already-qualified contracts become reachable ONLY via canonical resolution -----
@pytest.mark.parametrize("intent,contract,path", [
    ("shorter Env1.Decay to 627 ms", "envelope_field_decay", "Env0.plainParams.kParamDecay"),
    ("lower Env1.Sustain to -13.8 dB", "envelope_field_sustain", "Env0.plainParams.kParamSustain"),
    ("set Filter1.Type to Band 24", "filter_field_type", None),
])
def test_qualified_contracts_reachable_through_derived_concepts(intent, contract, path):
    r = _run(intent)
    assert r.admitted is True and r.execution_route == "dawdreamer_serum" and r.refusal is None
    assert r.resolved_concept.startswith("canonical:")                 # derived, not a hand-written concept
    assert _plan(r)["contract_id"] == contract
    if path:
        assert _plan(r)["mutation_target_path"] == path


def test_enum_operation_is_derived_from_the_contract():
    r = _run("set Filter1.Type to Band 24")
    assert "select" in " ".join(r.candidate_operations) and "lengthen" not in " ".join(r.candidate_operations)


def test_osc_a_enable_routes_over_the_mcp_host_map_only():
    r = _run("turn oscA.enabled off")
    assert r.admitted is True and r.execution_route == "ableton_mcp" and _plan(r).get("contract_id") is None


# ---- section 7.1: the four refusal boundaries are distinct, each with code + emitting layer -------------
def test_refusal_unresolved_reference():
    for intent, tg in (("shorter Env1.Bogus", None), ("set noise.sample to X", None), ("shorter", None)):
        r = _run(intent, tg)
        assert r.refusal["code"] == tr.REFUSED_UNRESOLVED_REFERENCE and r.refusal["layer"] == tr.LAYER_REFERENCE
        assert not r.admitted


def test_refusal_ambiguous_reference_is_not_resolved_by_picking():
    r = _run("make it shorter", "cutoff")                # filter1.cutoff vs filter2.cutoff
    assert r.refusal["code"] == tr.REFUSED_AMBIGUOUS_REFERENCE and r.refusal["layer"] == tr.LAYER_REFERENCE
    assert set(r.refusal["candidates"]) == {"filter1.cutoff", "filter2.cutoff"}
    r = _run("longer Env1.Release", "Env1.Attack")       # two different explicit targets
    assert r.refusal["code"] == tr.REFUSED_AMBIGUOUS_REFERENCE and not r.admitted


@pytest.mark.parametrize("intent,target", [("shorter Env1.Hold to 1 ms", "env1.hold"), ("set oscA.unison to 3", "oscA.unison")])
def test_refusal_no_brain_concept(intent, target):
    # U1: Atlas-known targets now flow to Capability layer (ATLAS_CANONICAL provenance), not BRAIN layer.
    # canonical_target is None on this path: the B1/ATLAS_CANONICAL path goes through legacy
    # execution_status mapping which does not carry canonical_id into the refusal record.
    r = _run(intent)
    assert r.refusal["code"] == tr.REFUSED_NO_CAPABILITY and r.refusal["layer"] == tr.LAYER_CAPABILITY
    assert not r.admitted


@pytest.mark.parametrize("intent,target", [("set Filter2.Type to Band 24", "Filter2.Type"), ("turn oscB.enabled off", "OSC2.Enable")])
def test_refusal_no_capability(intent, target):
    r = _run(intent)
    assert r.refusal["code"] == tr.REFUSED_NO_CAPABILITY and r.refusal["layer"] == tr.LAYER_CAPABILITY
    assert r.refusal["canonical_target"] == target and not r.admitted


def test_refusal_admission_is_a_separate_boundary():
    b = ProducerBrain()
    for status in ("REFUSED_ADMISSION", "REFUSED_AUTHORITY"):
        b._execute_inner = lambda req, s=status: SimpleNamespace(
            refusal=None, execution_status=s, semantic_target="Env1.Release", error="denied")
        r = b.execute(ProducerRequest(user_intent="x"))
        assert r.refusal["code"] == tr.REFUSED_ADMISSION and r.refusal["layer"] == tr.LAYER_ADMISSION


def test_refusal_record_is_added_beside_the_legacy_status():
    r = _run("shorter Env1.Hold to 1 ms")
    # U1: legacy status is now REFUSED_NO_MAPPING (capability layer), not REFUSED_UNKNOWN_CONCEPT (brain layer)
    assert r.execution_status == "REFUSED_NO_MAPPING"
    assert set(r.refusal) == {"code", "layer", "canonical_target", "reason", "candidates"}
    assert r.to_dict()["refusal"]["code"] == tr.REFUSED_NO_CAPABILITY                    # serializes with the result


def test_every_legacy_refusal_status_is_classified():
    for status, (code, layer) in tr.LEGACY_STATUS_TO_REFUSAL.items():
        assert status.startswith("REFUSED") and code.startswith("REFUSED") and layer != tr.LAYER_UNKNOWN


# ---- section 9: generic words never select a target; nothing tutorial-specific -----------------------
@pytest.mark.parametrize("text", ["shorter", "longer", "extend it", "tighter", "shorter decay", "make it longer"])
def test_bare_direction_words_do_not_select_a_target(text):
    r = _run(text)
    assert r.resolved_concept is None and not r.admitted


def test_natural_language_that_names_release_or_attack_still_works():
    b = ProducerBrain()
    assert b._resolve_concept(ProducerRequest(user_intent="Make the note sustain longer"))[0] == "note-release"
    assert b._resolve_concept(ProducerRequest(user_intent="faster attack"))[0] == "envelope-attack"


def test_no_hardcoded_control_tables_in_resolution_code():
    trsrc = (SRC / "target_resolution.py").read_text(encoding="utf-8").lower()
    for forbidden in ("env1.decay", "env1.sustain", "filter1.type", "oscA.enabled".lower(), "j106", "td22", "acid lead", "gotas"):
        assert forbidden not in trsrc, forbidden
    brsrc = (SRC / "producer_brain.py").read_text(encoding="utf-8")
    for forbidden in ("_EXPLICIT_TARGET_TO_CONCEPT", "_UNCOVERED_CONTROL_NOUNS", "_ENUM_CONCEPT_OPERATION", '"env1.decay"'):
        assert forbidden not in brsrc, forbidden


# ---- sections 3.5 / 6.1: aliases are DATA; coverage axes are independent --------------------------
def _resolver(atlas, semantic_targets, mcp=None):
    from serum2.compiler.targets import SEMANTIC_TARGETS
    from serum2.compiler.mcp_intent import MCP_HOST_MAP
    from serum2.knowledge.step_6_6_capability_resolution import UNIVERSAL_TO_SEMANTIC, SemanticTargetMapping
    from serum2.producer.contract_registry import ContractRegistry
    from serum2.producer.producer_brain import _MCP_CONCEPT_BRIDGE
    return tr.TargetResolver(ContractRegistry(), SEMANTIC_TARGETS if semantic_targets is None else semantic_targets,
                             MCP_HOST_MAP if mcp is None else mcp, UNIVERSAL_TO_SEMANTIC, _MCP_CONCEPT_BRIDGE,
                             SemanticTargetMapping, atlas_resolve=atlas)


def test_alias_lives_in_the_atlas_data_not_in_resolution_code():
    def atlas(text):   # a different reference dataset that knows one extra alias
        from serum2.reference.serum_atlas import normalize_control, Resolution, ALIAS
        if text == "Env1.DecayTime":
            return Resolution(ALIAS, "env1.decay", ("env1.decay",), text)
        return normalize_control(text)
    res = _resolver(atlas, None).resolve("shorten Env1.DecayTime", None)
    assert res.refusal is None and res.canonical_id == "env1.decay" and res.registry_target == "Env1.Decay"
    assert _resolver(None, None).resolve("shorten Env1.DecayTime", None).refusal.code == tr.REFUSED_UNRESOLVED_REFERENCE


def test_contract_alone_does_not_make_a_control_reachable():
    """U1: Atlas-known targets resolve successfully even without a Brain registry entry.
    The contract still does not make the control executable: capability_key is None
    (no registry lookup succeeded), so no mapping is derived."""
    res = _resolver(None, {}, mcp={}).resolve("shorter Env1.Decay", None)
    # U1: TargetResolver succeeds (Atlas-known), not REFUSED at BRAIN layer
    assert res.refusal is None, f"U1: Atlas-known target should resolve, got {res.refusal}"
    assert res.canonical_id == "env1.decay"
    # No registry entry → no capability_key → no mapping (contract not reached)
    assert res.capability_key is None
    assert res.mapping is None


def test_brain_concept_alone_does_not_make_a_control_executable():
    res = _resolver(None, None).resolve("set Filter2.Type to X", None)
    assert res.refusal is None and res.mapping is None                 # Brain knows it; no qualified contract to derive a mapping from
    assert _run("set Filter2.Type to X").refusal["code"] == tr.REFUSED_NO_CAPABILITY


def test_atlas_knowledge_reaches_capability_not_brain_refusal():
    """U1: Atlas-known, Brain-unregistered target gets ATLAS_CANONICAL provenance.
    The refusal is at CAPABILITY layer (no contract), not BRAIN layer.
    Pre-U1: REFUSED_NO_BRAIN_CONCEPT. Post-U1: REFUSED_NO_CAPABILITY."""
    from serum2.reference.serum_atlas import normalize_control
    assert normalize_control("env1.hold").status == "EXACT"            # the reference layer knows it
    # U1: Brain accepts it (ATLAS_CANONICAL); Capability layer refuses (no contract)
    assert _run("shorter Env1.Hold").refusal["code"] == tr.REFUSED_NO_CAPABILITY


def test_target_name_normalization_never_aliases_across_slots():
    assert normalize_target_name("Filter1.Cutoff") == "filter.cutoff"
    assert normalize_target_name("Filter2.Cutoff") == "filter2.cutoff"
    assert normalize_target_name("oscA.enabled") == "osc1.enable" and normalize_target_name("oscB.enabled") == "osc2.enable"
    assert find_target_tokens("e.g. about 1.5 ms, see Fig.2") == [] and find_surface_tokens("longer Env1.Attack") == ["Env1.Attack"]
