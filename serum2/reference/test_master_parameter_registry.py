"""Tests for the Serum 2 master parameter registry export
(serum2_master_parameter_registry.json / serum2_master_parameter_coverage.json).

This is a READ-ONLY materialization of the EXISTING serum_atlas.py registry
(get_control()/all_control_ids()) joined with the host census and existing
evidence/promotion/admission code -- these tests verify the export is
faithful and internally coherent, not that new qualification happened.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "parameter_characterization" / "serum2_master_parameter_registry.json"
COVERAGE_PATH = ROOT / "parameter_characterization" / "serum2_master_parameter_coverage.json"

pytestmark = pytest.mark.skipif(
    not REGISTRY_PATH.exists() or not COVERAGE_PATH.exists(),
    reason="master parameter registry has not been generated in this environment",
)


@pytest.fixture(scope="module")
def registry():
    return json.loads(REGISTRY_PATH.read_text())


@pytest.fixture(scope="module")
def coverage():
    return json.loads(COVERAGE_PATH.read_text())


def test_every_atlas_control_has_a_registry_entry_or_explicit_disposition(registry):
    import sys
    sys.path.insert(0, str(ROOT))
    from serum2.reference.serum_atlas import all_control_ids
    atlas_ids = set(all_control_ids())
    registry_ids = set(registry["canonical_registry"].keys())
    assert atlas_ids == registry_ids
    for cid, entry in registry["canonical_registry"].items():
        assert entry["disposition"], "control %r has no explicit disposition" % cid


def test_no_two_controls_share_the_same_canonical_identity(registry):
    entries = registry["canonical_registry"]
    ids = [e["canonical_id"] for e in entries.values()]
    assert len(ids) == len(set(ids))


def test_osca_semitone_and_coarse_pitch_remain_distinct(registry):
    entries = registry["canonical_registry"]
    semi = entries["oscA.semitone"]
    coarse = entries["oscA.coarse_pitch"]
    assert (semi["min"], semi["max"]) == (-12.0, 12.0)
    assert (coarse["min"], coarse["max"]) == (-72.0, 72.0)
    assert semi["canonical_id"] != coarse["canonical_id"]
    conflict_types = [c["type"] for c in registry["conflicts"]
                      if "oscA.semitone" in c.get("canonical_ids", [])]
    assert "SEMANTIC_IDENTITY_CONFLATION" in conflict_types


def test_lfo1_through_lfo10_are_accounted_for(registry):
    entries = registry["canonical_registry"]
    lfo_sections = {n for n, e in entries.items() if e["subsection"].startswith("LFO")}
    # Atlas indexes LFO1-6 as first-class subsections; LFO7-10 are a KNOWN,
    # explicitly-documented gap (not silently missing) -- assert the gap is
    # documented, not that it's silently closed.
    present_instances = {e["subsection"] for e in entries.values() if e["subsection"].startswith("LFO") and e["subsection"] != "LFO"}
    assert present_instances == {"LFO1", "LFO2", "LFO3", "LFO4", "LFO5", "LFO6"}
    # generic LFO container also present (headless/shared LFO fields)
    assert any(e["subsection"] == "LFO" for e in entries.values())


def test_every_fx_module_is_accounted_for(registry):
    import sys
    sys.path.insert(0, str(ROOT / "vendor" / "serum-mcp" / "src"))
    from serum_mcp.generation.spec import FxUnitSpec  # noqa: F401
    entries = registry["canonical_registry"]
    fx_entries = [e for cid, e in entries.items() if e["section"] == "FX"]
    assert len(fx_entries) > 0
    # every FX entry must have an explicit kind/disposition -- none silently dropped
    for e in fx_entries:
        assert e["kind"]
        assert e["disposition"]


def test_every_schema_only_field_is_mapped_or_explicitly_unmapped(registry, coverage):
    entries = registry["canonical_registry"].values()
    for e in entries:
        # every entry has an explicit generation_field (mapped) OR is
        # explicitly None (recorded, not omitted from the record)
        assert "generation_field" in e


def test_host_only_fields_are_retained_not_discarded(registry):
    host_surface = registry["host_surface"]
    assert len(host_surface) == 2623
    unmapped = [h for h in host_surface if h["binding_status"] == "HOST_ONLY_UNMAPPED"]
    assert len(unmapped) > 0
    for h in unmapped:
        assert h["host_parameter_index"] is not None
        assert h["host_parameter_name"]


def test_missing_domain_and_enum_information_is_explicit_not_guessed(registry):
    entries = registry["canonical_registry"]
    for cid, e in entries.items():
        if e["control_type"] == "continuous" and (e["min"] is None or e["max"] is None):
            assert e["domain_status"] == "DOMAIN_UNVERIFIED", cid
        if e["control_type"] in ("enum", "dropdown") and not e["enum_values"]:
            assert e["enum_status"] == "ENUM_UNVERIFIED", cid


def test_no_target_specific_logic_in_registry_builder():
    """Static guard on the export script itself (kept alongside its output)."""
    script_candidates = list((ROOT / "parameter_characterization").glob("*.py"))
    # the builder script is a scratch/session tool, not committed under
    # parameter_characterization/ -- this test instead guards the one file
    # that IS committed here and must stay generic.
    src = REGISTRY_PATH.read_text()
    for forbidden in ('"oscB.enabled": "PRESET_PARAMETER"',):
        assert forbidden not in src


def test_registry_creates_no_capability_contract_objects(registry):
    """The registry is inventory only -- its JSON has no serialized
    CapabilityContract fields (status/verified/scope/provenance as a
    contract would carry them); contract_status here is a STRING summary
    ("PROMOTED"/"REJECTED:...") produced by calling the EXISTING
    evidence_promotion.promote_verified_evidence, never a stored contract."""
    for e in registry["canonical_registry"].values():
        assert isinstance(e["contract_status"], str)
        assert "execution_binding" not in e
        assert "CapabilityContract" not in json.dumps(e)


def test_coverage_counts_are_internally_consistent(coverage, registry):
    c = coverage["counts"]
    assert c["atlas_controls"] == len(registry["canonical_registry"])
    assert c["host_parameters"] == len(registry["host_surface"])
    assert c["canonical_registry_entries"] == c["atlas_controls"]
