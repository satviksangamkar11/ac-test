"""P4: candidate generation + ranking. Advisory only: ranking never executes, admits, invents a
capability, or silently replaces a target."""
import ast
import itertools
from pathlib import Path

import pytest

from serum2.producer import candidate_ranking as cr
from serum2.producer.candidate_ranking import (
    PRIMARY, REFERENCE_ALTERNATIVE, SKILL_VARIANT, Candidate, CandidateGenerator, CandidateRanker, to_intent,
)
from serum2.producer.concept_representation import ConceptRepresentation, Provenance
from serum2.producer.operation_spec import Operand, OperationSpec, OperationType
from serum2.producer.request_context import RequestContext
from serum2.producer.skill_library import SkillAdvisory, SkillRecord, _FORBIDDEN_SKILL_FIELDS
from serum2.producer.universal_intent import UniversalProductionIntent

GEN, RANK = CandidateGenerator(), CandidateRanker()


def intent(target="env1.release", op=OperationType.INCREASE, value=None, unit=None):
    spec = OperationSpec(operation=op, operand=Operand(value=value, unit=unit) if value is not None else None,
                         base_phrase="longer", certainty=0.7, interpretation_chain=["parsed"])
    rep = ConceptRepresentation(canonical_target=target, provenance=Provenance.ATLAS_CANONICAL, confidence=0.5)
    return UniversalProductionIntent(canonical_target=target, representation=rep, operation=spec, context=RequestContext())


def advisory(target="env1.release", op="SET", conf=0.2, sid=None, after="838 ms"):
    rec = SkillRecord(skill_id=sid or "skill:%s:%s" % (target, op.lower()), canonical_target_id=target,
                      target_concept="c", semantic_target="T", operation=op,
                      trigger={"observed_change": {"before": "15 ms", "after": after}}, preconditions=(),
                      supporting_evidence=({"episode_id": "e", "verified": True},), outcome_stats={}, confidence=conf,
                      provenance={"source_episode_ids": ["e"]})
    return SkillAdvisory.from_skill(rec)


# ---- contract --------------------------------------------------------------------------------------
def test_candidate_has_only_advisory_fields():
    assert set(Candidate.__dataclass_fields__) == {"candidate_id", "canonical_target", "operation", "operand", "origin",
                                                   "target_changed", "evidence", "rationale", "advisory"}
    assert not _FORBIDDEN_SKILL_FIELDS & set(Candidate.__dataclass_fields__)


@pytest.mark.parametrize("kw", [{"origin": "MADE_UP"}, {"advisory": False}, {"canonical_target": ""}, {"operation": ""}])
def test_malformed_candidate_is_refused(kw):
    base = dict(candidate_id="c", canonical_target="env1.release", operation="set", operand=None, origin=PRIMARY, target_changed=False)
    base.update(kw)
    with pytest.raises(ValueError):
        Candidate(**base)


def test_candidate_is_frozen_and_not_an_execution_request():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    (c,) = GEN.generate(intent())
    with pytest.raises(Exception):
        c.origin = SKILL_VARIANT
    with pytest.raises(TypeError):
        ProducerRequest(**c.to_dict())
    with pytest.raises(Exception):
        ProducerBrain().execute(c)
    for attr in ("execute", "admitted", "execution_route", "contract_id", "binding", "capability"):
        assert not hasattr(c, attr)


def test_module_imports_no_brain_admission_backend_or_capability_code():
    tree = ast.parse(Path(cr.__file__).read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not [m for m in mods if any(b in m for b in ("producer_brain", "admission", "backend", "contract_registry", "capability", "serum_mcp"))]


def test_module_names_no_target():
    tree = ast.parse(Path(cr.__file__).read_text(encoding="utf-8"))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not [c for c in consts if any(t in c.lower() for t in ("env1", "env2", "filter1", "osc"))]


# ---- generator -------------------------------------------------------------------------------------
def test_primary_candidate_is_always_generated_from_the_intent():
    (c,) = GEN.generate(intent(op=OperationType.SET, value=838, unit="ms"))
    assert (c.canonical_target, c.operation, c.origin, c.target_changed) == ("env1.release", "set", PRIMARY, False)
    assert dict(c.operand) == {"raw": "838 ms"} and c.evidence == ()


def test_generation_is_deterministic():
    adv = [advisory(), advisory(op="TOGGLE_ON", sid="s2")]
    assert GEN.generate(intent(), adv, ["env2.release"]) == GEN.generate(intent(), adv, ["env2.release"])


def test_skill_supporting_the_same_operation_becomes_evidence_on_the_primary_not_a_new_candidate():
    cands = GEN.generate(intent(op=OperationType.SET, value=838, unit="ms"), [advisory()])
    assert len(cands) == 1 and cands[0].origin == PRIMARY
    assert [dict(e) for e in cands[0].evidence] == [{"skill_id": "skill:env1.release:set", "confidence": 0.2}]


def test_skill_with_a_different_operation_yields_a_variant_on_the_same_target():
    cands = GEN.generate(intent(), [advisory()])            # intent increases, skill observed a SET
    assert [c.origin for c in cands] == [PRIMARY, SKILL_VARIANT]
    v = cands[1]
    assert (v.canonical_target, v.operation, v.target_changed) == ("env1.release", "set", False)
    assert dict(v.operand) == {"raw": "838 ms"}


def test_skills_for_other_targets_never_create_candidates():
    assert len(GEN.generate(intent(), [advisory(target="filter1.cutoff")])) == 1


def test_skill_operation_outside_the_generic_model_is_ignored():
    assert len(GEN.generate(intent(), [advisory(op="FROBNICATE")])) == 1


def test_reference_alternatives_are_target_changing_and_atlas_backed():
    cands = GEN.generate(intent(), (), ["env2.release", "env1.release"])   # own target is not an alternative
    assert [c.origin for c in cands] == [PRIMARY, REFERENCE_ALTERNATIVE]
    assert cands[1].canonical_target == "env2.release" and cands[1].target_changed is True


def test_unknown_reference_alternative_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        GEN.generate(intent(), (), ["definitely.not.a.control"])


def test_duplicates_are_collapsed():
    assert len(GEN.generate(intent(), [advisory(sid="a"), advisory(sid="b")], ["env2.release", "env2.release"])) == 3


# ---- ranker ----------------------------------------------------------------------------------------
def test_primary_ranks_first_and_ranks_are_dense():
    rs = RANK.rank(GEN.generate(intent(), [advisory()], ["env2.release"]))
    assert rs.selected.candidate.origin == PRIMARY
    assert [r.rank for r in rs.ranked] == [1, 2, 3] and rs.advisory is True


def test_target_change_is_never_ranked_above_any_same_target_candidate():
    rs = RANK.rank(GEN.generate(intent(), [advisory()], ["env2.release"]))
    changed = [r.rank for r in rs.ranked if r.candidate.target_changed]
    same = [r.rank for r in rs.ranked if not r.candidate.target_changed]
    assert min(changed) > max(same)


def test_even_maximal_skill_confidence_cannot_displace_the_primary():
    rs = RANK.rank(GEN.generate(intent(), [advisory(conf=1.0)]))
    assert rs.selected.candidate.origin == PRIMARY
    assert cr.WEIGHT_FIT * 0.5 + cr.WEIGHT_SKILL * 1.0 < cr.WEIGHT_FIT


def test_skill_confidence_reorders_alternatives_among_themselves():
    hi = advisory(op="SET", conf=0.9, sid="hi")
    lo = advisory(op="TOGGLE_ON", conf=0.1, sid="lo")
    got = [r.candidate.operation for r in RANK.rank(GEN.generate(intent(), [lo, hi])).ranked]
    assert got == ["increase", "set", "toggle_on"]
    got = [r.candidate.operation for r in RANK.rank(GEN.generate(intent(), [advisory(op="SET", conf=0.1, sid="a"),
                                                                             advisory(op="TOGGLE_ON", conf=0.9, sid="b")])).ranked]
    assert got == ["increase", "toggle_on", "set"]


def test_ranking_is_deterministic_and_input_order_independent():
    cands = GEN.generate(intent(), [advisory(), advisory(op="TOGGLE_ON", sid="t")], ["env2.release"])
    a = RANK.rank(cands)
    b = RANK.rank(tuple(reversed(cands)))
    assert [r.candidate.candidate_id for r in a.ranked] == [r.candidate.candidate_id for r in b.ranked]


def test_ranker_refuses_missing_primary_and_empty_input():
    cands = GEN.generate(intent(), [advisory()])
    with pytest.raises(ValueError):
        RANK.rank([c for c in cands if c.origin != PRIMARY])
    with pytest.raises(ValueError):
        RANK.rank([])


def test_ranking_does_not_mutate_candidates_or_skill_confidence():
    adv = advisory(conf=0.4)
    cands = GEN.generate(intent(), [adv])
    snap = [c.to_dict() for c in cands]
    RANK.rank(cands)
    assert [c.to_dict() for c in cands] == snap and adv.confidence == 0.4


@pytest.mark.parametrize("skills,alts", list(itertools.product(
    [[], [advisory()], [advisory(op="TOGGLE_ON", conf=1.0)]], [[], ["env2.release"], ["env2.release", "env3.release"]])))
def test_selected_candidate_never_changes_the_target(skills, alts):
    rs = RANK.rank(GEN.generate(intent(), skills, alts))
    assert rs.selected.candidate.canonical_target == "env1.release" and not rs.selected.candidate.target_changed


# ---- selection -> Capability Resolution handoff --------------------------------------------------
def test_primary_selection_hands_back_the_original_intent_untouched():
    it = intent()
    assert to_intent(RANK.rank(GEN.generate(it, [advisory()])).selected.candidate, it) is it


def test_variant_hands_a_copy_with_only_the_operation_changed_and_marked_advisory():
    it = intent()
    var = next(c for c in GEN.generate(it, [advisory()]) if c.origin == SKILL_VARIANT)
    out = to_intent(var, it)
    assert out is not it and out.canonical_target == it.canonical_target and out.representation is it.representation
    assert out.operation.operation is OperationType.SET and it.operation.operation is OperationType.INCREASE
    assert any("not authority" in s for s in out.operation.interpretation_chain)
    assert out.capability_key is None and out.admission_status is None      # nothing pre-decided


def test_to_intent_refuses_a_target_change():
    it = intent()
    alt = next(c for c in GEN.generate(it, (), ["env2.release"]) if c.target_changed)
    with pytest.raises(ValueError):
        to_intent(alt, it)


# ---- hard boundary against the real Brain ------------------------------------------------------------
def _brain_outcome(text):
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    from serum2.producer.target_resolution import LEGACY_STATUS_TO_REFUSAL
    r = ProducerBrain().execute(ProducerRequest(user_intent=text, mode="EXECUTE", visual_mode="NEVER"))
    return (bool(r.admitted), r.execution_status, LEGACY_STATUS_TO_REFUSAL.get(r.execution_status or "", (None,))[0],
            (getattr(r, "_serum_preset_plan", None) or {}).get("contract_id"))


def test_ranking_cannot_create_capability_or_admission_for_an_unqualified_target():
    text = "longer Env2.Release to 267 ms"
    before = _brain_outcome(text)
    assert before[0] is False and before[2] == "REFUSED_NO_CAPABILITY"
    it = intent("env2.release")
    rs = RANK.rank(GEN.generate(it, [advisory("env2.release", conf=1.0)], ["env1.release"]))
    to_intent(rs.selected.candidate, it)
    assert _brain_outcome(text) == before


def test_ranking_leaves_a_qualified_targets_decision_unchanged():
    text = "longer Env1.Release to 838 ms"
    before = _brain_outcome(text)
    assert before[0] is True and before[3] == "envelope_field_release"
    it = intent()
    to_intent(RANK.rank(GEN.generate(it, [advisory()], ["env2.release"])).selected.candidate, it)
    assert _brain_outcome(text) == before


def test_tier_keeps_target_change_behind_same_target_variant_even_when_fit_and_id_would_favor_it():
    # "cand:env1.attack..." sorts before "cand:env1.release..." and both have equal fit: only the tier holds the order.
    rs = RANK.rank(GEN.generate(intent(), [advisory()], ["env1.attack"]))
    assert [(r.candidate.origin, r.candidate.canonical_target) for r in rs.ranked] == [
        (PRIMARY, "env1.release"), (SKILL_VARIANT, "env1.release"), (REFERENCE_ALTERNATIVE, "env1.attack")]
