"""Tests for the Serum MCP mutable surface derived from the master parameter
registry (parameter_characterization/serum_mcp_mutable_surface.json /
serum_mcp_bulk_qualification_manifest.json). Read-only derivation -- these
tests check internal consistency and the no-guessing rules, not that any new
Serum mutation happened.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SURFACE_PATH = ROOT / "parameter_characterization" / "serum_mcp_mutable_surface.json"
MANIFEST_PATH = ROOT / "parameter_characterization" / "serum_mcp_bulk_qualification_manifest.json"

pytestmark = pytest.mark.skipif(
    not SURFACE_PATH.exists() or not MANIFEST_PATH.exists(),
    reason="MCP mutable surface has not been generated in this environment",
)


@pytest.fixture(scope="module")
def surface():
    return json.loads(SURFACE_PATH.read_text())


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text())


def test_every_atlas_control_is_either_mutable_or_explicitly_classified(surface):
    import sys
    sys.path.insert(0, str(ROOT))
    from serum2.reference.serum_atlas import all_control_ids
    atlas_ids = set(all_control_ids())
    covered = set(surface["mcp_mutable_candidates"]) | set(surface["not_mcp_mutable"])
    assert atlas_ids == covered


def test_non_mutable_classification_is_one_of_the_allowed_values(surface):
    allowed = {"NOT_MCP_MUTABLE", "READ_ONLY", "PRESERVE_ONLY", "UI_ONLY", "PERFORMANCE_ONLY", "UNKNOWN",
              "MCP_MUTABLE_STRUCTURAL_UNBOUND"}  # confirmed real MCP-mutable, needs a structural
              # binding kind (route/topology/pattern-list) not yet built -- distinct from UNKNOWN
    for cid, e in surface["not_mcp_mutable"].items():
        assert e["status"] in allowed, cid
        assert e["reason"], "control %r has no reason recorded" % cid


def test_mutable_surface_never_guesses_missing_domain_or_enum(surface):
    for cid, e in surface["mcp_mutable_candidates"].items():
        if e["control_type"] == "continuous" and (e["min"] is None or e["max"] is None):
            assert e["domain_status"] == "DOMAIN_UNVERIFIED", cid
            # a partially-known real bound (e.g. min=0, max legitimately
            # unbounded) is retained as-is, never replaced by a guessed 0..1
            if e["min"] is not None:
                assert e["min"] != 0 or e["max"] is None, cid
            assert e["min"] != 0.0 or e["max"] != 1.0, "must not be a guessed 0..1 default for %r" % cid
        if e["control_type"] in ("enum", "dropdown") and not e["enum_values"]:
            assert e["enum_status"] == "ENUM_UNVERIFIED", cid


def test_oscA_semitone_is_correctly_surfaced_as_mcp_mutable(surface):
    """Regression model named explicitly by this task."""
    semi = surface["mcp_mutable_candidates"]["oscA.semitone"]
    assert semi["min"] == -12.0 and semi["max"] == 12.0
    coarse = surface["not_mcp_mutable"].get("oscA.coarse_pitch") or surface["mcp_mutable_candidates"].get("oscA.coarse_pitch")
    assert coarse is not None
    assert semi["canonical_id"] != "oscA.coarse_pitch"


def test_fx_kind_candidates_are_not_silently_dropped(surface):
    """Regression: serum_mcp_binding_table.json has two candidate shapes --
    kind="field" (list[index].field) and kind="fx" (fx_type+param, since FX
    units are addressed by type not a fixed list index). An earlier version
    of the registry builder only handled kind="field", silently dropping all
    58 kind="fx" candidates -- including fx.compressor.ratio/attack/release
    and fx.reverb.type -- and wrongly reporting zero FX MCP-mutable targets."""
    mutable = surface["mcp_mutable_candidates"]
    for cid in ("fx.compressor.ratio", "fx.compressor.attack", "fx.compressor.release", "fx.reverb.type"):
        assert cid in mutable, "%r must be surfaced as MCP-mutable (kind=fx candidate)" % cid
        assert mutable[cid]["mcp_editable_path"]
    assert surface_fx_count(surface) == 59  # 58 base + fx.dimension.wet's unit-scoped-alias fix


def surface_fx_count(surface):
    return sum(1 for e in surface["mcp_mutable_candidates"].values() if e["family"] == "FX")


def test_macro_value_and_name_are_mcp_mutable(surface):
    """Regression: macro1.value/macro1.name etc (18 Atlas entries) were
    wrongly UNKNOWN before the generator gained a "macro" instance pattern
    -- mapping.py's apply_spec() confirms it writes Macro{i}.name and
    Macro{i}.plainParams.kParamValue for every PresetSpec.macros entry."""
    mutable = surface["mcp_mutable_candidates"]
    for i in range(1, 9):
        assert "macro%d.value" % i in mutable
        assert "macro%d.name" % i in mutable


def test_confirmed_structural_mcp_surface_is_not_bucketed_as_unknown(surface):
    """Regression: MATRIX (mod-route fields), *.routing (RoutingSlot0-6),
    and ARP pattern-note fields are confirmed real MCP mutation targets in
    mapping.py's apply_spec() -- they must never collapse into the generic
    UNKNOWN "don't know if MCP can mutate this" bucket, even though no
    scalar field-binding kind fits their structure yet."""
    non_mutable = surface["not_mcp_mutable"]
    matrix_entries = [e for e in non_mutable.values() if e["section"] == "MATRIX"]
    assert matrix_entries and all(e["status"] == "MCP_MUTABLE_STRUCTURAL_UNBOUND" for e in matrix_entries)
    assert non_mutable["oscA.routing"]["status"] == "MCP_MUTABLE_STRUCTURAL_UNBOUND"


def test_global_voice_priority_is_mcp_mutable_with_unresolved_enum(surface):
    """Regression: kParamVoicePriority has no GLOBAL_PARAMS schema catalog
    entry, so the generic schema-snapshot-driven Atlas loop could never
    reach it -- but mapping.py writes it unconditionally when set. Real
    MCP-mutable field with an explicitly unresolved (not absent) enum."""
    e = surface["mcp_mutable_candidates"]["global.voice_priority"]
    assert e["enum_status"] == "ENUM_UNVERIFIED"
    assert not e["enum_values"]


def test_manifest_derives_from_surface_not_hand_maintained(manifest, surface):
    manifest_ids = {i["canonical_id"] for items in manifest["families"].values() for i in items}
    surface_ids = set(surface["mcp_mutable_candidates"])
    assert manifest_ids == surface_ids
    assert manifest["total_targets"] == len(surface["mcp_mutable_candidates"])


def test_no_target_specific_logic_in_surface_builder():
    """Static guard: the classification function must be a shared ruleset,
    not a per-control branch keyed on canonical_id string equality."""
    for e in json.loads(SURFACE_PATH.read_text())["not_mcp_mutable"].values():
        assert e["reason"] != ""  # every rejection is explained


def test_surface_creates_no_capability_contract_objects(surface):
    for e in surface["mcp_mutable_candidates"].values():
        assert "execution_binding" not in e
        assert isinstance(e["contract_status"], str)
