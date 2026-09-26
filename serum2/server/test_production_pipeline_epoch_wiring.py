"""Proof: _run_brain_intent_admission passes installed_epoch() to execute_producer_request.

This is the CREATE-path closure proof -- the missing link between 'Brain epoch cache works'
(serum2/producer/test_producer_brain_epoch_evidence.py) and 'the real production pipeline
actually uses it.'

The test monkeypatches installed_epoch to a known value (no real Serum binary in CI) and
intercepts execute_producer_request via a spy, then asserts the epoch that arrived at the
spy matches the pinned value exactly.
"""
import importlib

import pytest

from serum2.producer import producer_brain as pb
from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.qualification import evidence_promotion
import serum2.producer.execution_epoch as ee


@pytest.fixture(autouse=True)
def _reset_brain_caches():
    pb._BRAIN = None
    pb._BRAINS.clear()
    yield
    pb._BRAIN = None
    pb._BRAINS.clear()


def test_production_pipeline_passes_installed_epoch_to_brain(monkeypatch):
    """The real CREATE call site derives and passes epoch; evidence contracts are reachable."""
    monkeypatch.setattr(evidence_promotion, "installed_epoch", lambda: EPOCH_2_0_23)
    monkeypatch.setattr(ee, "installed_epoch", lambda: EPOCH_2_0_23)

    import serum2.server.production_pipeline as pp
    importlib.reload(pp)   # pick up the monkeypatched installed_epoch in the lazy import

    captured = {}
    real_exec = pb.execute_producer_request

    def spy(request, epoch=None):
        captured["epoch"] = epoch
        return real_exec(request, epoch=epoch)

    monkeypatch.setattr(pb, "execute_producer_request", spy)

    try:
        pp._run_brain_intent_admission("test_src", "deep dark bass tutorial")
    except Exception:
        pass  # result unpacking may fail with no real Serum; epoch capture already happened

    assert "epoch" in captured, "execute_producer_request was never called"
    assert captured["epoch"] is not None, \
        "epoch=None reached the Brain -- installed_epoch() was not passed through"
    assert captured["epoch"].binary_sha256 == EPOCH_2_0_23.binary_sha256, \
        f"wrong epoch sha: {captured['epoch'].binary_sha256!r}"
