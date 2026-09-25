"""Frozen engine contract v1 + unified evidence: the bulk engine feeds the existing promotion pipeline as a DRY RUN only."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ED = ROOT / "parameter_characterization" / "bulk_causal_evidence"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import bulk_engine  # noqa: E402
from unify import CONTRACT_KEYS  # noqa: E402

UNIFIED = ED / "unified_evidence_v1.json"
AUTHORITY = ["serum2/reference/serum_mcp_binding_table.json", "parameter_characterization/serum_mcp_mutable_surface.json",
             "parameter_characterization/serum2_master_parameter_registry.json", "parameter_characterization/serum_mcp_mutable_coverage.json",
             "serum2/reference/serum_atlas.py", "serum2/evidence/admission.py", "serum2/evidence/capability_contract.py"]
# evidence_promotion.py is deliberately NOT frozen any more: Phase 2.3 gave it the parameter-contract path (test_evidence_promotion_contract.py)


def test_engine_contract_is_versioned_and_pinned():
    assert bulk_engine.ENGINE_CONTRACT_VERSION == 1


@pytest.mark.parametrize("name", ["bulk_fx_eq_pilot_v1.json", "bulk_osc_a_pilot_v1.json"])
def test_pilot_records_carry_exactly_the_frozen_contract_keys(name):
    for r in json.loads((ED / name).read_text())["records"]:
        assert CONTRACT_KEYS["record"] <= set(r), name
        for v in r["values"]:
            assert CONTRACT_KEYS["row"] <= set(v), name


@pytest.mark.skipif(not UNIFIED.exists(), reason="unified evidence not generated")
def test_unified_evidence_invariants():
    d = json.loads(UNIFIED.read_text())
    assert d["authorizes_nothing"] and d["changes_no_authority_file"] and d["engine_contract_version"] == 1
    assert d["summary"]["records"] == len(d["records"]) == 26
    assert d["incidents"][0]["id"] == "ableton-crash-2026-09-25"
    for r in d["records"]:
        assert r["atlas"] is not None or "NO_ATLAS_IDENTITY" in r["blocked_by"]     # no id is ever invented
        assert r["eligible_for_promotion_review"] == (not r["blocked_by"])
        if r["eligible_for_promotion_review"]:
            assert r["promotion_dry_run"]["promoted"] and not r["atlas_domain_conflicts"] and r["tiers"]["causal_raw"]["ok"]
        if r["atlas_domain_conflicts"]:
            assert "ATLAS_DOMAIN_CONFLICT" in r["blocked_by"]          # evidence that contradicts the Atlas is never forced through
        assert len(r["blocked_by"]) == len(set(r["blocked_by"]))
    by = {r["atlas_id"]: r for r in d["records"]}
    assert by["oscA.coarse_pitch"]["atlas_domain_conflicts"][0]["serum_reachable"] == [-64.0, 64.0]   # Atlas says +-72
    assert by["oscA.fine"]["atlas_domain_conflicts"][0]["serum_reachable"][1] == 100.0                # Atlas says +-80
    assert by["fx.equalizer.left_type"]["promotion_dry_run"]["promoted"] and not by["fx.equalizer.left_type"]["blocked_by"]  # enum via contract, not boolean
    assert by["oscA.blend"]["pilot_atlas_id"] == "oscA.unison_width" and by["oscA.blend"]["blocked_by"] == ["UI_SEMANTICS_NOT_VERIFIED"]


def test_unify_writes_only_its_output_artifact():
    src = (HERE / "unify.py").read_text()
    assert src.count("open(out_path") == 1 and ".write_text(" not in src and 'open(' in src
    for banned in ("admit(", "json.dump(", "dump_preset"):
        assert src.count(banned) <= (1 if banned == "json.dump(" else 0), banned


def test_authority_files_are_unmodified_versus_git_head():
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--"] + AUTHORITY, cwd=ROOT, capture_output=True, text=True, timeout=60)
    except Exception:
        pytest.skip("git unavailable")
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    assert out.stdout.strip() == "", out.stdout
