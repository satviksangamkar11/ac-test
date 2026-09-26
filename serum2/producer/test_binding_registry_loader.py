"""Generic evidence-derived registry loader + unchanged bridge_index/find_contract/admit. Fixtures are data only."""
import functools
import json
from serum2.evidence import admission as adm
from serum2.producer.contract_registry import ContractRegistry
from serum2.producer.contract_scope import bridge_index, find_contract
from serum2.producer.execution_epoch import EPOCH_2_0_21, EPOCH_2_0_23
from serum2.producer.state_ledger import catalog

def _ev(cid, path, acc, kind="float", v1=0.5, v2=0.25, lo=0.0, hi=5.2, sha=EPOCH_2_0_23.binary_sha256, **kw):
    d = {"control_id": cid, "accessor": acc, "derived_body_path": path, "status": "BINDING_VERIFIED", "run_status": "STRUCTURAL_VERIFIED",
         "mutation_value": v1, "second_write_value": v2, "value_domain": {"kind": kind, "lo": lo, "hi": hi},
         "serum_identity": {"serum_binary_sha256": sha, "serum_product_version": "x"},
         "value_landed_in_derived_path": True, "collateral_semantically_neutral": True, "second_write_neutral": True}
    d.update(kw); return d

def _write(tmp, **files):
    for name, ev in files.items():
        (tmp / (name + ".json")).write_text(json.dumps(ev) if not isinstance(ev, str) else ev)
    return tmp

def test_diagnostics_buckets(tmp_path):
    _write(tmp_path,
           good=_ev("t.good", "Env3.plainParams.kParamHold", "envelopes[3].hold"),
           badjson="{not json",
           unverified=_ev("t.u", "Env3.plainParams.kParamHold", "envelopes[3].hold", status="BINDING_NOT_VERIFIED"),
           wrongtype=_ev("t.i", "Oscillator2.plainParams.kParamUnison", "oscillators[2].unison", kind="integer", v1=2.5, v2=3.0, lo=1, hi=16),
           outofdomain=_ev("t.o", "Env3.plainParams.kParamHold", "envelopes[3].hold", v1=9.0),
           oldformat={k: v for k, v in _ev("t.old", "P.q", "l[0].f").items() if k != "value_domain"},
           wrongepoch=_ev("t.e", "Env3.plainParams.kParamAttack", "envelopes[3].attack", sha=EPOCH_2_0_21.binary_sha256),
           nobinding=_ev("t.n", "Env3.plainParams.kParamDecay", "envelopes[3].decay", value_landed_in_derived_path=False))
    r = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=tmp_path)
    d = r.binding_diagnostics
    assert d["loaded"] == ["t.good"] and "t.good" in r.contracts
    assert len(d["rejected_invalid_evidence"]) == 5 and len(d["rejected_epoch"]) == 1 and len(d["rejected_no_binding"]) == 1
    assert any("not an integer" in v for v in d["rejected_invalid_evidence"].values())

def test_legacy_frontier_untouched_when_no_epoch(tmp_path):
    _write(tmp_path, good=_ev("t.good", "Env3.plainParams.kParamHold", "envelopes[3].hold"))
    assert "t.good" not in ContractRegistry(binding_evidence_dir=tmp_path).contracts

def test_unmodified_bridge_and_admit_consume_new_arbitrary_candidate(tmp_path):
    # Env index 3 hold: no legacy contract for it; nothing names it anywhere.
    _write(tmp_path, new=_ev("anything.at_all", "Env3.plainParams.kParamHold", "envelopes[3].hold"))
    r = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=tmp_path)
    op = {"kind": "field", "module": "env", "index": 3, "field": "hold", "operation": "SET", "value": 0.5}
    c, tr = find_contract(op, {}, bridge_index(r), catalog())
    assert c is not None and c.contract_key == "anything.at_all", tr
    res = adm.admit(r.get_contracts_dict(), c.contract_key, proposed_prerequisites_verified={})
    assert res.admitted, res
    other = dict(op, index=1)                      # a different instance is NOT covered
    assert find_contract(other, {}, bridge_index(r), catalog())[0] is None or find_contract(other, {}, bridge_index(r), catalog())[0].contract_key != "anything.at_all"


# ---- the second, parallel evidence source: evidence_promotion.py's shape (build_binding_evidence_from_mcp_exec.py's
# output), loaded via promoted_evidence_dir. promote_verified_evidence() re-derives its epoch from the actual
# installed Serum binary, so every test here monkeypatches evidence_promotion.installed_epoch the same way the
# converter script does -- never a fake epoch, just an explicit path to a real (or here, fixture-standin) binary
# check that the test controls. ----

def _promo_ev(target, path, before=0.0004999999999999998, after=5.000000000000001, sha=EPOCH_2_0_23.binary_sha256, **kw):
    d = {"target": target, "epoch": {"serum_sha256": sha, "product_version": "2.0.23"}, "status": "STRUCTURAL_VERIFIED",
         "restoration_verified": True, "body_diff_filtered": [{"path": path, "before": before, "after": after}],
         "baseline_value": before, "mutated_value": after}
    d.update(kw); return d


def _patch_installed_epoch(monkeypatch, epoch):
    from serum2.qualification import evidence_promotion
    monkeypatch.setattr(evidence_promotion, "installed_epoch", lambda: epoch)


def test_promoted_evidence_loads_a_real_target(tmp_path, monkeypatch):
    _patch_installed_epoch(monkeypatch, EPOCH_2_0_23)
    _write(tmp_path, **{"env1.attack": _promo_ev("env1.attack", "Env0.plainParams.kParamAttack")})
    r = ContractRegistry(epoch=EPOCH_2_0_23, promoted_evidence_dir=tmp_path)
    assert r.promotion_diagnostics["loaded"] == ["env1.attack"]
    assert "env1.attack" in r.contracts


def test_promoted_evidence_never_overrides_an_existing_target(tmp_path, monkeypatch):
    _patch_installed_epoch(monkeypatch, EPOCH_2_0_23)
    binding_dir = tmp_path / "binding"
    promo_dir = tmp_path / "promo"
    binding_dir.mkdir(); promo_dir.mkdir()
    _write(binding_dir, **{"env1.attack": _ev("env1.attack", "Env0.plainParams.kParamAttack", "envelopes[0].attack")})
    _write(promo_dir, **{"env1.attack": _promo_ev("env1.attack", "Env0.plainParams.kParamAttack")})
    r = ContractRegistry(epoch=EPOCH_2_0_23, binding_evidence_dir=binding_dir, promoted_evidence_dir=promo_dir)
    assert "env1.attack" in r.binding_diagnostics["loaded"]
    assert r.promotion_diagnostics["rejected_contract"]   # env1.attack was already registered by the other source


def test_promoted_evidence_rejects_wrong_epoch(tmp_path, monkeypatch):
    _patch_installed_epoch(monkeypatch, EPOCH_2_0_23)
    _write(tmp_path, **{"env1.attack": _promo_ev("env1.attack", "Env0.plainParams.kParamAttack", sha=EPOCH_2_0_21.binary_sha256)})
    r = ContractRegistry(epoch=EPOCH_2_0_23, promoted_evidence_dir=tmp_path)
    assert "env1.attack" not in r.contracts
    assert r.promotion_diagnostics["rejected_epoch"]


def test_promoted_evidence_rejects_what_promote_verified_evidence_rejects(tmp_path, monkeypatch):
    _patch_installed_epoch(monkeypatch, EPOCH_2_0_23)
    _write(tmp_path, **{"env1.attack": _promo_ev("env1.attack", "Env0.plainParams.kParamAttack", restoration_verified=False)})
    r = ContractRegistry(epoch=EPOCH_2_0_23, promoted_evidence_dir=tmp_path)
    assert "env1.attack" not in r.contracts
    assert r.promotion_diagnostics["rejected_not_promoted"]


def test_promoted_evidence_untouched_when_no_epoch(tmp_path, monkeypatch):
    _patch_installed_epoch(monkeypatch, EPOCH_2_0_23)
    _write(tmp_path, **{"env1.attack": _promo_ev("env1.attack", "Env0.plainParams.kParamAttack")})
    assert "env1.attack" not in ContractRegistry(promoted_evidence_dir=tmp_path).contracts


def test_installed_epoch_resolution_failure_is_a_diagnostic_not_a_crash(tmp_path, monkeypatch):
    """promote_verified_evidence itself catches installed_epoch() failing (no Serum on this machine) and returns an
    ordinary EPOCH_MISMATCH rejection -- never an exception. The registry must not crash either way."""
    from serum2.qualification import evidence_promotion

    def boom():
        raise FileNotFoundError("no Serum installed on this machine")
    monkeypatch.setattr(evidence_promotion, "installed_epoch", boom)
    _write(tmp_path, **{"env1.attack": _promo_ev("env1.attack", "Env0.plainParams.kParamAttack")})
    r = ContractRegistry(epoch=EPOCH_2_0_23, promoted_evidence_dir=tmp_path)   # must not raise
    assert "env1.attack" not in r.contracts
    assert r.promotion_diagnostics["rejected_not_promoted"]
    assert "EPOCH_MISMATCH" in next(iter(r.promotion_diagnostics["rejected_not_promoted"].values()))
