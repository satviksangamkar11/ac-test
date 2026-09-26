"""Proof: final_execution_contract_v1.json is the runtime source for allowed_operation,
raw_body_path, and valid_domain — not the old evidence directory or legacy pickle stores.

Control under proof: env1.attack
  expected allowed_operation : mutate_numeric_value
  expected raw_body_path      : Env0.plainParams.kParamAttack
  expected valid_domain       : {kind: mutate_numeric_value, lo: 0.0, hi: 10.0}

The test constructs ContractRegistry with epoch=EPOCH_2_0_23 and explicitly NO
promoted_evidence_dir, then asserts env1.attack is resolved entirely from the final
contract. It fails if the file is absent (FileNotFoundError propagates) or if the
lookup silently used an older source (binding_source check).
"""
import pytest

from serum2.producer import contract_registry as cr
from serum2.producer.execution_epoch import EPOCH_2_0_23
from serum2.producer.final_execution_contract import (
    FINAL_CONTRACT_PATH,
    FinalExecutionContractIndex,
    PROMOTABLE_OUTCOMES,
)
from serum2.qualification import evidence_promotion as ep

PROOF_CONTROL = "env1.attack"
PROOF_BODY_PATH = "Env0.plainParams.kParamAttack"
PROOF_ALLOWED_OP = "mutate_numeric_value"
KNOWN_EXCEPTION = "arp.transpose.range"


@pytest.fixture(autouse=True)
def _patch_epoch(monkeypatch):
    """Suppress installed_epoch() hash-check (no real binary in CI)."""
    monkeypatch.setattr(ep, "installed_epoch", lambda: EPOCH_2_0_23)


# ── 1. FinalExecutionContractIndex: file exists and is readable ───────────────

def test_final_contract_file_exists():
    """The generated artifact must exist on disk — fails loudly if absent."""
    idx = FinalExecutionContractIndex()   # raises FileNotFoundError if missing
    assert len(idx) == 330
    assert "final_execution_contract_v1.json" in idx.source_path


# ── 2. Proof control is in the index with correct fields ─────────────────────

def test_proof_control_fields_in_index():
    idx = FinalExecutionContractIndex()
    row = idx.get(PROOF_CONTROL)
    assert row is not None, "%s not found in final contract" % PROOF_CONTROL
    assert row["allowed_operation"] == PROOF_ALLOWED_OP
    assert row["raw_body_path"] == PROOF_BODY_PATH
    vd = row["valid_domain"]
    assert vd["kind"] == "continuous"
    assert vd["min"] == 0.0
    assert vd["max"] == 10.0
    assert row["execution_outcome"] in PROMOTABLE_OUTCOMES
    assert row["known_exception"] is False
    assert row["epoch_sha256"] == EPOCH_2_0_23.binary_sha256


# ── 3. Known exception is in the index with known_exception=True ─────────────

def test_known_exception_in_index():
    idx = FinalExecutionContractIndex()
    row = idx.get(KNOWN_EXCEPTION)
    assert row is not None
    assert row["known_exception"] is True
    assert idx.is_known_exception(KNOWN_EXCEPTION)
    assert not idx.is_known_exception(PROOF_CONTROL)


# ── 4. ContractRegistry resolves proof control FROM final contract, not old sources ──

def test_registry_resolves_from_final_contract_not_old_sources(monkeypatch):
    """With promoted_evidence_dir=None, the proof control must still resolve.
    If it resolves, it came from final_execution_contract_v1.json.
    If it resolves from the old evidence dir, this test would pass by accident —
    guarded by the binding_source assertion below."""
    # No promoted evidence dir → resolution must come from the final contract
    registry = cr.ContractRegistry(
        epoch=EPOCH_2_0_23,
        binding_evidence_dir=None,
        promoted_evidence_dir=None,
    )

    # Final contract was loaded without error
    assert "error" not in registry.final_contract_diagnostics, \
        "final_execution_contract_v1.json failed to load: %s" % \
        registry.final_contract_diagnostics.get("error")

    # Source path is the final contract file, not any per-control evidence file
    source = registry.final_contract_diagnostics.get("source_path", "")
    assert "final_execution_contract_v1.json" in source, \
        "unexpected source: %r" % source
    assert "binding_evidence_mcp_exec_v1" not in source, \
        "runtime fell back to old evidence dir: %r" % source

    contract = registry.get(PROOF_CONTROL)
    assert contract is not None, "%s not in registry" % PROOF_CONTROL

    # allowed_operation
    assert contract.allowed_operation == PROOF_ALLOWED_OP

    # raw_body_path (execution_binding.body_path)
    assert contract.execution_binding is not None
    assert contract.execution_binding.body_path == PROOF_BODY_PATH

    # binding_source explicitly names the final contract, not an old evidence path
    assert "final_execution_contract_v1.json" in contract.execution_binding.binding_source, \
        "binding_source came from old path: %r" % contract.execution_binding.binding_source

    # provenance explicitly names the final contract
    assert contract.provenance.get("promoted_from") == "final_execution_contract_v1.json"

    # valid_domain (scope["domain"] uses lo/hi after normalization)
    domain = contract.scope.get("domain", {})
    assert domain.get("lo") == 0.0
    assert domain.get("hi") == 10.0


# ── 5. Known exception is NOT in the registry's contracts ────────────────────

def test_known_exception_not_in_registry_contracts():
    registry = cr.ContractRegistry(
        epoch=EPOCH_2_0_23,
        promoted_evidence_dir=None,
        binding_evidence_dir=None,
    )
    assert registry.get(KNOWN_EXCEPTION) is None, \
        "exception control %s must NOT be in registry.contracts" % KNOWN_EXCEPTION
    assert KNOWN_EXCEPTION in registry.known_exceptions, \
        "exception control %s must be in registry.known_exceptions" % KNOWN_EXCEPTION


# ── 6. Absent final contract is surfaced, not silently swallowed ─────────────

def test_absent_final_contract_raises_on_direct_index():
    """FinalExecutionContractIndex raises FileNotFoundError — no silent fallback."""
    with pytest.raises(FileNotFoundError):
        FinalExecutionContractIndex(path="/nonexistent/path/final_execution_contract_v1.json")


def test_absent_final_contract_recorded_in_registry_diagnostics(tmp_path):
    """ContractRegistry records the error rather than raising (consistent with other loaders),
    but the diagnostics make the absence detectable by callers."""
    registry = cr.ContractRegistry(
        epoch=EPOCH_2_0_23,
        final_execution_contract_path=str(tmp_path / "absent.json"),
        promoted_evidence_dir=None,
        binding_evidence_dir=None,
    )
    assert "error" in registry.final_contract_diagnostics


# ── 7. 310 executable + 20 exceptions exact counts ───────────────────────────

def test_final_contract_counts_match_v2_sweep():
    registry = cr.ContractRegistry(
        epoch=EPOCH_2_0_23,
        promoted_evidence_dir=None,
        binding_evidence_dir=None,
    )
    loaded = registry.final_contract_diagnostics.get("loaded", [])
    assert len(loaded) == 310, "expected 310 executable, got %d" % len(loaded)
    assert len(registry.known_exceptions) == 20, \
        "expected 20 exceptions, got %d" % len(registry.known_exceptions)
