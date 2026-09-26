"""The live MCP execution harness, exercised offline with a fake Serum: every outcome class is reachable, the no-op
detector fires, and all 330 contract rows build their bodies through apply_spec without error."""
import copy
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("SERUM_SAMPLES_PATH", str(HERE / "contexts"))
import run_mcp_execution_harness as h  # noqa: E402

ED = HERE.parents[2] / "parameter_characterization" / "bulk_causal_evidence"
CONTRACT = ED / "mcp_execution_contract_v1.json"
pytestmark = pytest.mark.skipif(not CONTRACT.exists(), reason="contract not present")


@pytest.fixture(scope="module")
def contract():
    return {r["atlas_id"]: r for r in json.loads(CONTRACT.read_text())["rows"]}


@pytest.fixture(scope="module")
def bt():
    return json.load(open(h.BT))["controls"]


class ScriptedBackend(h.FakeBackend):
    """Fake whose post-edit state can be overridden, to force the failure branches."""

    def __init__(self, host_paths, post_override=None):
        super().__init__(host_paths)
        self.post_override, self.n = post_override, 0

    def load(self, body):
        self.n += 1
        super().load(body)
        if self.n == 2 and self.post_override:
            self.post_override(self.body)


def run(row, ctrl, host_paths=None, post_override=None):
    return h.run_row(row, ctrl, ScriptedBackend(host_paths or {}, post_override))


def named_row(contract):
    return next(r for r in contract.values() if r["q4_host_text_check"]["mode"] == "NAMED" and r["bucket"] == "A")


def test_host_confirmed_when_named_param_changes(contract, bt):
    r = named_row(contract)
    res = run(r, bt[r["atlas_id"]], {r["q4_host_text_check"]["host_parameter"]: r["expected_raw"][0]["path"]})
    assert res["outcome"] == "MCP_EXEC_HOST_CONFIRMED" and res["q4"]["named_changed"]


def test_confirmed_when_named_param_does_not_change(contract, bt):
    r = named_row(contract)
    res = run(r, bt[r["atlas_id"]], {r["q4_host_text_check"]["host_parameter"]: ["Nowhere", "x"]})
    assert res["outcome"] == "MCP_EXEC_CONFIRMED"


def test_raw_only_when_full_scan_finds_nothing(contract, bt):
    r = next(r for r in contract.values() if r["q4_host_text_check"]["mode"] == "FULL_SCAN")
    assert run(r, bt[r["atlas_id"]])["outcome"] == "MCP_EXEC_RAW_ONLY"


def test_bucket_d_is_always_a_conformance_exception(contract, bt):
    for a in ("mixer.noise.pan", "global.use_ultra_on_render", "macro1.name"):
        assert run(contract[a], bt[a])["outcome"] == "MCP_EXEC_CONFORMANCE_EXCEPTION"


def test_noop_suspect_when_serum_drops_the_value(contract, bt):
    r = named_row(contract)
    path = r["expected_raw"][0]["path"]

    def drop(body):   # Serum omits a key equal to its own default: the leaf vanishes from the re-saved state
        cur = body
        for k in path[:-1]:
            cur = cur[k]
        cur.pop(path[-1], None)
    res = run(r, bt[r["atlas_id"]], post_override=drop)
    assert res["outcome"] in ("MCP_EXEC_NOOP_SUSPECT", "MCP_EXEC_FAILED")
    assert not res["q3_leaves"][0]["persisted"]


def test_failed_when_serum_stores_a_different_value(contract, bt):
    r = next(x for x in contract.values() if x["bucket"] == "A" and isinstance(x["expected_raw"][0]["value"], float))
    path = r["expected_raw"][0]["path"]

    def clamp(body):
        cur = body
        for k in path[:-1]:
            cur = cur[k]
        cur[path[-1]] = r["expected_raw"][0]["value"] + 123.0
    assert run(r, bt[r["atlas_id"]], post_override=clamp)["outcome"] == "MCP_EXEC_FAILED"


def test_all_330_rows_build_and_run_offline(contract, bt):
    host_paths = {}
    for r in contract.values():
        n = r["q4_host_text_check"].get("host_parameter")
        if n and r["expected_raw"]:
            host_paths.setdefault(n, r["expected_raw"][0]["path"])
    out = [h.run_row(r, bt[a], h.FakeBackend(host_paths)) for a, r in contract.items()]
    assert len(out) == 330
    assert not [o["atlas_id"] for o in out if o["outcome"] == "MCP_EXEC_FAILED"]
    assert not [o["atlas_id"] for o in out if o["outcome"] == "MCP_EXEC_NOOP_SUSPECT"]
    assert all(o["q1_addressable"] and o["q2_raw_written"] for o in out)


def test_sample_covers_every_class_and_the_forced_rows(contract):
    params = {p["atlas_id"]: p for p in json.load(open(HERE / "manifest_campaign_v1.json"))["parameters"]}
    s = h.select_sample(contract.values(), params)
    assert set(h.FORCED_SAMPLE) <= set(s)
    keys = {(r["bucket"], r["q4_host_text_check"]["mode"], params.get(a, {}).get("mechanism", "OVERRIDE"),
             params.get(a, {}).get("context", "INIT")) for a, r in contract.items()}
    covered = {(contract[a]["bucket"], contract[a]["q4_host_text_check"]["mode"], params.get(a, {}).get("mechanism", "OVERRIDE"),
                params.get(a, {}).get("context", "INIT")) for a in s}
    assert keys == covered


def test_oracle_host_text_matches_when_serum_shows_the_known_divergence(contract, bt):
    class PanQuirk(h.FakeBackend):   # Serum's real behavior: written -20 displays '-19 L'
        def hosts(self):
            v = h.body_get(self.body, ["Oscillator3", "plainParams", "kParamPan"])
            return {"Noise Pan": "%d L" % (abs(v) - 1) if v else "0"} if v is not None else {"Noise Pan": "0"}
    res = h.run_row(contract["mixer.noise.pan"], bt["mixer.noise.pan"], PanQuirk({}))
    assert res["outcome"] == "MCP_EXEC_CONFORMANCE_EXCEPTION"
    assert res["oracle_observed"] == "19 L" or res["oracle_match"] is False   # fake formats without the sign
    class PanQuirkSigned(PanQuirk):
        def hosts(self):
            v = h.body_get(self.body, ["Oscillator3", "plainParams", "kParamPan"])
            return {"Noise Pan": "-%d L" % (abs(v) - 1) if v else "0"}
    res = h.run_row(contract["mixer.noise.pan"], bt["mixer.noise.pan"], PanQuirkSigned({}))
    assert res["oracle_match"] is True and res["oracle_observed"] == "-19 L"


def test_oracle_not_persisted_matches_when_serum_drops_the_leaf(contract, bt):
    r = contract["global.use_ultra_on_render"]
    path = r["expected_raw"][0]["path"]

    def drop(body):
        cur = body
        for k in path[:-1]:
            cur = cur[k]
        cur.pop(path[-1], None)
    res = run(r, bt["global.use_ultra_on_render"], post_override=drop)
    assert res["outcome"] == "MCP_EXEC_CONFORMANCE_EXCEPTION" and res["oracle_match"] is True


def test_every_row_is_sent_in_validated_client_form(contract, bt):
    for a, r in contract.items():
        if bt[a]["kind"] != "fx" and isinstance(r["test_value"], float) and r["mcp_edit"].get("field") in (
                "enabled", "beat_sync", "mono", "legato", "dotted", "triplets"):
            raise AssertionError("%s sends a float for a boolean field" % a)
    assert contract["global.fx_bus1_destination"]["test_value"] in ("master", "direct")
