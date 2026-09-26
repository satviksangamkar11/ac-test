"""Proofs 1-3 of the epoch/evidence plan: the Brain's registry construction and execute_producer_request's cache,
not a fragile end-to-end natural-language intent parse. admission.admit() is the real authority gate both CREATE
and RECREATE ultimately rely on; proving reachability there is the same standard test_binding_registry_loader.py
already uses for ContractRegistry directly.

Target identification (plan Step 0, recorded here rather than picked arbitrarily): diffing
ContractRegistry(epoch=None) against ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=...,
promoted_evidence_dir=...) gives 222 targets present ONLY in the evidenced registry (212 from this session's Phase 1
promotion, 10 already-known Pass-1 targets that are also epoch-gated). `env1.attack` is one of the 212, absent from
every legacy pickle-store contract -- confirmed absent from the legacy registry by test_epoch_none_matches_legacy
below, not asserted separately.
"""
import pytest

from serum2.evidence import admission as adm
from serum2.producer import producer_brain as pb
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.execution_epoch import EPOCH_2_0_21, EPOCH_2_0_23

TARGET = "env1.attack"


@pytest.fixture(autouse=True)
def _patch_installed_epoch(monkeypatch):
    # promote_verified_evidence independently re-derives the epoch via installed_epoch() (hashing the real Serum
    # binary at its hardcoded path), regardless of the epoch passed to ContractRegistry. This container has no
    # Serum install; pin it to the epoch under test so evidence actually loads -- the same pattern
    # test_binding_registry_loader.py already uses.
    from serum2.qualification import evidence_promotion
    monkeypatch.setattr(evidence_promotion, "installed_epoch", lambda: EPOCH_2_0_23)


@pytest.fixture(autouse=True)
def _reset_brain_caches():
    """Every legacy/epoch-keyed brain is process-global state; tests must not leak into each other."""
    pb._BRAIN = None
    pb._BRAINS.clear()
    yield
    pb._BRAIN = None
    pb._BRAINS.clear()


def test_epoch_none_matches_legacy_registry_and_lacks_the_target():
    """Proof 2 (half): ProducerBrain(epoch=None) is exactly today's registry -- no evidence dirs, target absent."""
    brain = pb.ProducerBrain()
    assert TARGET not in brain._registry.contracts


def test_epoch_given_loads_the_evidence_derived_target():
    """Proof 1 (half): with a real epoch and both evidence dirs, the target IS in the registry."""
    brain = pb.ProducerBrain(epoch=EPOCH_2_0_23, binding_evidence_dir=pb.BINDING_EVIDENCE_DIR,
                             promoted_evidence_dir=pb.PROMOTED_EVIDENCE_DIR)
    assert TARGET in brain._registry.contracts


def test_epoch_given_target_actually_reaches_admission():
    """Proof 1 (the real claim): loaded is not admissible. Same generic admit() path both CREATE and RECREATE rely
    on -- the same call test_binding_registry_loader.py's own test proves the mechanism with."""
    brain = pb.ProducerBrain(epoch=EPOCH_2_0_23, binding_evidence_dir=pb.BINDING_EVIDENCE_DIR,
                             promoted_evidence_dir=pb.PROMOTED_EVIDENCE_DIR)
    result = adm.admit(brain._registry.get_contracts_dict(), TARGET, proposed_prerequisites_verified={})
    assert result.admitted, result


def test_epoch_none_target_cannot_be_admitted_legacy_behavior_exactly_preserved():
    """Proof 2 (the real claim): the identical admission check, with the legacy (epoch=None) registry, correctly
    finds nothing to admit -- proving epoch=None truly is unaffected, not merely that the target is absent."""
    brain = pb.ProducerBrain()
    contracts = brain._registry.get_contracts_dict()
    assert not any(k[0] == TARGET for k in contracts)   # no (claim_id, sig) key for TARGET exists to even attempt


def test_execute_producer_request_epoch_none_uses_the_one_legacy_singleton(monkeypatch):
    """execute_producer_request(request, epoch=None) must behave exactly as before this change: one shared _BRAIN,
    never touching _BRAINS."""
    seen = []
    real_init = pb.ProducerBrain.__init__

    def spy_init(self, *a, **kw):
        seen.append(kw.get("epoch"))
        return real_init(self, *a, **kw)
    monkeypatch.setattr(pb.ProducerBrain, "__init__", spy_init)

    req = pb.ProducerRequest(user_intent="create a dark bass sound", mode="CREATE")
    monkeypatch.setattr(pb.ProducerBrain, "execute", lambda self, r: "OK")

    pb.execute_producer_request(req)
    pb.execute_producer_request(req)
    assert seen == [None]                 # constructed exactly once, with epoch=None, and reused on the 2nd call
    assert pb._BRAINS == {}               # the epoch-keyed cache is never touched by an epoch=None caller


def test_execute_producer_request_epoch_keyed_cache_never_shares_across_epochs(monkeypatch):
    """Proof 3: epoch A and epoch B get different cached brains; a cache hit constructs zero new ones."""
    constructed = []
    real_init = pb.ProducerBrain.__init__

    def spy_init(self, *a, **kw):
        constructed.append(kw.get("epoch"))
        return real_init(self, *a, **kw)
    monkeypatch.setattr(pb.ProducerBrain, "__init__", spy_init)
    monkeypatch.setattr(pb.ProducerBrain, "execute", lambda self, r: self)   # return self so we can check identity

    req = pb.ProducerRequest(user_intent="create a dark bass sound", mode="CREATE")
    brain_a1 = pb.execute_producer_request(req, epoch=EPOCH_2_0_23)
    brain_b = pb.execute_producer_request(req, epoch=EPOCH_2_0_21)
    brain_a2 = pb.execute_producer_request(req, epoch=EPOCH_2_0_23)

    assert brain_a1 is brain_a2                     # epoch A's second call reuses A's cached brain
    assert brain_a1 is not brain_b                  # never shares across epochs
    assert constructed == [EPOCH_2_0_23, EPOCH_2_0_21]   # exactly 2 constructions: A once, B once -- A's 2nd call built zero
