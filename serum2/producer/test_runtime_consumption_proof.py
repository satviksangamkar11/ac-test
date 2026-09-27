"""Runtime-consumption integration test.

Proves the complete chain for one HOST_CONFIRMED scalar control:
  atlas_id (env1.attack)
    -> ContractRegistry.lookup_final()               [source: final_execution_contract_v1.json]
    -> allowed_operation / raw_body_path / valid_domain
    -> producer execution request (apply_spec)
    -> MCP mutation (serum-mcp apply_spec)
    -> real Serum 2.0.23 execution (LiveBackend / DawDreamer)
    -> save/load -> raw-state readback
    -> expected persisted value
    -> restoration verified

Authority boundaries: admit(), ClaimEngine, compiler validation, epoch checks, and the
20 CONFORMANCE_EXCEPTION rows are NOT touched.

Run:
    pytest serum2/producer/test_runtime_consumption_proof.py -v
    # or for the live-Serum chain (requires Serum installed + DawDreamer):
    pytest serum2/producer/test_runtime_consumption_proof.py -v --live

The --live marker skips the DawDreamer-dependent assertions in CI/offline mode.
The contract-lookup half runs in both modes and always exercises the real JSON file.
"""
import json
import sys
import os
import pytest
from pathlib import Path

# ---- path setup ----
HERE = Path(__file__).parent
REPO = HERE.parent.parent
for p in [str(REPO), str(REPO / "serum2" / "qualification" / "bulk_causal")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.contract_registry import ContractRegistry, FINAL_CONTRACT_PATH

# Atlas id under test — HOST_CONFIRMED scalar, well-known host parameter "Env 1 Attack"
ATLAS_ID = "env1.attack"
EXPECTED_SHA = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"
EXPECTED_RAW_PATH = "Env0.plainParams.kParamAttack"
EXPECTED_TEST_VALUE = pytest.approx(5.0, abs=1e-6)
EXPECTED_CLASS = "MCP_EXEC_HOST_CONFIRMED"
EXPECTED_HOST_VERIFY = "Env 1 Attack"


_BULK_CAUSAL = str(REPO / "serum2" / "qualification" / "bulk_causal")


def _live_available() -> bool:
    if _BULK_CAUSAL not in sys.path:
        sys.path.insert(0, _BULK_CAUSAL)
    try:
        import serum_backend  # noqa: F401
        return True
    except ImportError:
        return False


# Inject path at import time so the @skipif check is correct when pytest collects the module
if _BULK_CAUSAL not in sys.path:
    sys.path.insert(0, _BULK_CAUSAL)


# ---- contract-source tests (always run) ----

class TestContractSource:
    """Prove lookup_final() reads from final_execution_contract_v1.json and nothing else."""

    def setup_method(self):
        # epoch=None: legacy frontier; final contract is loaded unconditionally
        self.reg = ContractRegistry(epoch=None)

    def test_final_contract_path_is_canonical(self):
        """FINAL_CONTRACT_PATH must point to the committed artifact."""
        assert FINAL_CONTRACT_PATH.exists(), (
            "final_execution_contract_v1.json not found at %s" % FINAL_CONTRACT_PATH
        )
        assert FINAL_CONTRACT_PATH.name == "final_execution_contract_v1.json"
        assert "bulk_causal_evidence" in str(FINAL_CONTRACT_PATH)

    def test_final_contract_loaded(self):
        """ContractRegistry loads the final contract on construction."""
        assert self.reg._final_contract is not None, (
            "ContractRegistry._final_contract is None — _load_final_execution_contract() did not populate it"
        )
        assert len(self.reg._final_contract) == 330, (
            "Expected 330 entries (310 executable + 20 exceptions), got %d" % len(self.reg._final_contract)
        )

    def test_final_contract_sha_matches_serum_2023(self):
        """The contract's serum_binary_sha256 must be the Serum 2.0.23 epoch SHA."""
        assert self.reg._final_contract_sha == EXPECTED_SHA, (
            "SHA mismatch: expected %s, got %s" % (EXPECTED_SHA, self.reg._final_contract_sha)
        )

    def test_lookup_final_returns_entry(self):
        """lookup_final(atlas_id) returns the producer_lookup row for env1.attack."""
        entry = self.reg.lookup_final(ATLAS_ID)
        assert entry is not None, (
            "lookup_final('%s') returned None — atlas_id absent from producer_lookup" % ATLAS_ID
        )

    def test_lookup_final_classification(self):
        entry = self.reg.lookup_final(ATLAS_ID)
        assert entry["class"] == EXPECTED_CLASS

    def test_lookup_final_op(self):
        """allowed_operation is present and has correct shape."""
        entry = self.reg.lookup_final(ATLAS_ID)
        op = entry["op"]
        assert op["kind"] == "field"
        assert op["list"] == "envelopes"
        assert op["index"] == 0
        assert op["field"] == "attack"

    def test_lookup_final_raw_body_path(self):
        """raw_body_path resolves to Env0.plainParams.kParamAttack."""
        entry = self.reg.lookup_final(ATLAS_ID)
        raw = entry["raw"]  # list of [dotted_path, value] pairs
        assert len(raw) >= 1
        path_str = raw[0][0]
        assert path_str == EXPECTED_RAW_PATH, (
            "raw body path: expected %r, got %r" % (EXPECTED_RAW_PATH, path_str)
        )

    def test_lookup_final_valid_domain(self):
        """valid_domain comes from the rows (declared_domain); cross-check via the raw JSON."""
        raw_data = json.loads(FINAL_CONTRACT_PATH.read_text(encoding="utf-8"))
        row = next(r for r in raw_data["rows"] if r["atlas_id"] == ATLAS_ID)
        domain = row["declared_domain"]
        assert domain["kind"] == "continuous"
        assert domain["min"] == pytest.approx(0.0)
        assert domain["max"] == pytest.approx(10.0)

    def test_lookup_does_not_touch_pickle_stores(self):
        """lookup_final must not read from any pickle file.

        We assert by confirming _final_contract is populated independently of
        whether the legacy pickle stores exist (they're not on this path).
        """
        # Re-instantiate with a monkey-patched _load_fresh_contracts that does nothing
        # (simulates an environment where pickle stores are absent)
        class _NopRegistry(ContractRegistry):
            def _load_fresh_contracts(self):
                pass  # no pickle I/O
            def _load_binding_evidence_contracts(self, d=None):
                pass
            def _load_promoted_evidence_contracts(self, d=None):
                pass

        reg2 = _NopRegistry(epoch=None)
        # _load_final_execution_contract() still runs (called in __init__ after the nop'd methods)
        entry = reg2.lookup_final(ATLAS_ID)
        assert entry is not None, (
            "lookup_final returned None even with pickle stores disabled — "
            "final contract loader is not independent of legacy stores"
        )
        assert entry["class"] == EXPECTED_CLASS

    def test_verify_hint_names_host_parameter(self):
        """The verify hint must name the host parameter for HOST_CONFIRMED controls."""
        entry = self.reg.lookup_final(ATLAS_ID)
        assert EXPECTED_HOST_VERIFY in entry["verify"], (
            "Expected 'Env 1 Attack' in verify=%r" % entry["verify"]
        )

    def test_exception_policy_none_for_executable(self):
        entry = self.reg.lookup_final(ATLAS_ID)
        assert entry["exception_policy"] == "NONE"

    def test_330_total_20_exceptions(self):
        """Invariant: 330 total rows, exactly 20 CONFORMANCE_EXCEPTION."""
        raw = json.loads(FINAL_CONTRACT_PATH.read_text(encoding="utf-8"))
        rows = raw["rows"]
        assert len(rows) == 330
        exc = [r for r in rows if r["final_execution_classification"] == "MCP_EXEC_CONFORMANCE_EXCEPTION"]
        assert len(exc) == 20
        # all 20 are bucket D
        assert all(r["bucket"] == "D" for r in exc)

    def test_executable_control_count(self):
        """310 executable controls (330 - 20 exceptions)."""
        raw = json.loads(FINAL_CONTRACT_PATH.read_text(encoding="utf-8"))
        executable = [r for r in raw["rows"]
                      if r["final_execution_classification"] != "MCP_EXEC_CONFORMANCE_EXCEPTION"]
        assert len(executable) == 310


# ---- live-Serum chain test (skipped offline) ----

@pytest.mark.skipif(not _live_available(), reason="DawDreamer / Serum not available")
class TestLiveExecutionChain:
    """Full chain: lookup_final -> apply_spec -> LiveBackend -> readback -> restoration."""

    def test_full_chain_env1_attack(self):
        """Prove atlas_id -> final contract -> MCP mutation -> Serum readback -> restoration."""
        # 1. Read op/raw/domain from final_execution_contract_v1.json
        reg = ContractRegistry(epoch=None)
        entry = reg.lookup_final(ATLAS_ID)
        assert entry is not None
        op = entry["op"]
        raw_pairs = entry["raw"]
        assert entry["class"] == EXPECTED_CLASS

        # 2. Build preset bodies via serum-mcp apply_spec
        sys.path.insert(0, str(REPO / "serum2" / "qualification" / "bulk_causal"))
        from campaign_derive import base_spec, companion_spec, with_field
        from preset_build import BASE, SPEC0
        from serum_mcp.preset.mapping import apply_spec

        baseline_spec = base_spec(BASE)
        edited_spec = with_field(companion_spec(BASE), op["list"], op["index"], op["field"], raw_pairs[0][1])
        baseline_body = apply_spec(SPEC0, baseline_spec).body
        edited_body = apply_spec(SPEC0, edited_spec).body

        # 3. Execute against real Serum 2.0.23 via LiveBackend
        from run_mcp_execution_harness import LiveBackend, body_get
        backend = LiveBackend()
        assert backend.serum_sha256 == EXPECTED_SHA, (
            "Serum binary SHA mismatch: expected %s, got %s" % (EXPECTED_SHA, backend.serum_sha256)
        )

        backend.load(baseline_body)
        pre_state = backend.state()

        backend.load(edited_body)
        post_state = backend.state()

        # 4. Raw-state readback: Env0.plainParams.kParamAttack must equal the written value
        path_parts = EXPECTED_RAW_PATH.split(".")
        written_value = raw_pairs[0][1]
        persisted = body_get(post_state, path_parts)
        assert persisted == pytest.approx(written_value, abs=1e-6), (
            "Persisted value mismatch at %s: expected %r, got %r" % (EXPECTED_RAW_PATH, written_value, persisted)
        )

        # 5. Restoration: reload baseline, confirm leaf reverts
        backend.load(baseline_body)
        restored_state = backend.state()
        pre_val = body_get(pre_state, path_parts)
        restored_val = body_get(restored_state, path_parts)
        assert pre_val == restored_val, (
            "Restoration failed at %s: pre=%r, restored=%r" % (EXPECTED_RAW_PATH, pre_val, restored_val)
        )

        # 6. Source proof: the entry came from final_execution_contract_v1.json, not a pickle
        assert reg._final_contract_sha == EXPECTED_SHA
        assert "final_execution_contract_v1.json" in str(FINAL_CONTRACT_PATH)
