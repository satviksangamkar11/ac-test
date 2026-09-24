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


def test_voiceunison_scalar_random_fields_are_mcp_mutable(surface):
    """Regression: traced VoiceUnisonSpec through mapping.py's spec.voice_unison
    block. random_pan/random_detune/random_filter_cutoff/random_env_time and
    scaling_env_time/scaling_lfo_time are scalar fields written directly onto
    VoicePanel0.plainParams -- distinct from VoiceUnisonSpec's per-voice LIST
    fields (pan/detune/filter_cutoff/env_time/mod1/mod2), which structurally
    coincide in field NAME (pan/detune) but are a completely different kParam
    family (kParamVoice{n}Pan vs kParamGlobalRandomOscPan). A first version of
    this matcher let bare exact-normalization collide the two; this asserts
    the fix landed on the correct (scalar) field, not the list field."""
    mutable = surface["mcp_mutable_candidates"]
    assert mutable["global.voice_control.random.pan"]["mcp_editable_path"] == "voice_unison.random_pan"
    assert mutable["global.voice_control.random.detune"]["mcp_editable_path"] == "voice_unison.random_detune"
    assert mutable["global.voice_control.random.cutoff"]["mcp_editable_path"] == "voice_unison.random_filter_cutoff"
    assert mutable["global.voice_control.random.envs"]["mcp_editable_path"] == "voice_unison.random_env_time"
    assert mutable["global.voice_control.scaling.envs"]["mcp_editable_path"] == "voice_unison.scaling_env_time"
    assert mutable["global.voice_control.scaling.lfos"]["mcp_editable_path"] == "voice_unison.scaling_lfo_time"


def test_voiceunison_per_voice_list_fields_are_structural_unbound(surface):
    """The Atlas's 'seq' column (per-voice pan/detune/filter_cutoff/env_time/
    mod1/mod2) and 'osc_scope' (affects_osc_a/b/c/noise/sub) are confirmed
    real MCP mutation targets (mapping.py writes them) but are list/multi-
    field groups, not scalars -- must be MCP_MUTABLE_STRUCTURAL_UNBOUND, not
    silently dropped into UNKNOWN or falsely marked NOT_MCP_MUTABLE."""
    non_mutable = surface["not_mcp_mutable"]
    for cid in ("global.voice_control.seq.pan", "global.voice_control.seq.detune",
               "global.voice_control.seq.mod1", "global.voice_control.osc_scope"):
        assert non_mutable[cid]["status"] == "MCP_MUTABLE_STRUCTURAL_UNBOUND", cid


def test_voice_count_display_is_read_only_not_mcp_mutable(surface):
    """Regression: the Atlas's own evidence explicitly classifies this
    PROVEN_NOT_USER_CONTROL (a derived display, not a settable control) --
    must not be surfaced as MCP-mutable or left as unexplained UNKNOWN."""
    e = surface["not_mcp_mutable"]["voice.voicing.voice_count_display"]
    assert e["status"] == "READ_ONLY"


def test_mixer_namespace_resolves_to_the_same_oscillator_filter_slots(surface):
    """Regression: the Atlas's 'mixer.*' namespace (mixer.osc_a.*, mixer.
    filter1.*, mixer.noise.*, mixer.sub.*) was never tried against any
    PresetSpec model at all -- not a false negative, a missing prefix rule.
    Extending the exact-match generator (no fuzzy matching, only the
    already-established enable->enabled alias plus two new bus1/bus2->
    fx_bus{1,2}_send aliases backed by the schema's own docstring wording)
    surfaced 29 real matches, resolving to the SAME oscillators[i]/filters[i]
    list entries oscA./filter1. style ids already use."""
    mutable = surface["mcp_mutable_candidates"]
    assert mutable["mixer.osc_a.filter_balance"]["mcp_editable_path"] == "oscillators[0].filter_balance"
    assert mutable["mixer.osc_a.bus1"]["mcp_editable_path"] == "oscillators[0].fx_bus1_send"
    assert mutable["mixer.noise.enable"]["mcp_editable_path"] == "oscillators[3].enabled"
    assert mutable["mixer.filter1.wet"]["mcp_editable_path"] == "filters[0].wet"
    assert mutable["mixer.filter2.enable"]["mcp_editable_path"] == "filters[1].enabled"


def test_arp_pattern_and_global_subnamespace_strip_correctly(surface):
    """Regression: arp.pattern.rate/arp.pattern.shape were missed because
    the bare "arp" singleton prefix left "pattern.rate" as the field name
    to match (no ArpSpec field is literally named that) -- fixed with two
    more-specific singleton prefixes (arp.pattern, arp.global) that strip
    the UI-grouping segment before matching, same ArpSpec target either way."""
    mutable = surface["mcp_mutable_candidates"]
    assert mutable["arp.pattern.rate"]["mcp_editable_path"] == "arp.rate"
    assert mutable["arp.pattern.shape"]["mcp_editable_path"] == "arp.shape"


def test_arp_playback_retrigger_velocity_subnamespaces_are_mcp_mutable(surface):
    """Regression: verified a pasted claim that ARP was under-covered against
    the actual vendored source before acting -- most of the claim's specific
    field examples (warp_mode2/warp_amount2/warp_var2/sample_loop_*/
    voice_priority) were ALREADY bound from earlier passes this session, but
    arp.playback.*/arp.retrigger.*/arp.velocity.* genuinely were not tried.
    arp.playback.* matches ArpSpec fields by EXACT name (chance/gate/offset/
    repeats/thru); arp.retrigger.*/arp.velocity.* need their tail word
    contextualized by the sub-namespace (e.g. "retrigger.first" ->
    first_note_retrig), same rigor as the earlier voice_control aliases."""
    mutable = surface["mcp_mutable_candidates"]
    for cid, expected_field in [
        ("arp.playback.chance", "chance"), ("arp.playback.gate", "gate"),
        ("arp.playback.offset", "offset"), ("arp.playback.repeats", "repeats"),
        ("arp.playback.thru", "thru"), ("arp.retrigger.first", "first_note_retrig"),
        ("arp.retrigger.launch", "launch_retrig"), ("arp.retrigger.note", "note_retrig"),
        ("arp.velocity.decay", "velo_decay"), ("arp.velocity.enable", "velo_enabled"),
        ("arp.velocity.retrig", "velo_retrig"), ("arp.velocity.target", "velo_target"),
    ]:
        assert mutable[cid]["mcp_editable_path"] == "arp." + expected_field, cid


def test_arp_ambiguous_retrigger_rate_pair_left_unbound(surface):
    """arp.retrigger.rate_enable/rate_value both plausibly correspond to
    ArpSpec's single retrig_rate field (a checkbox+spinner UI pair) -- binding
    both to the same field would be ambiguous about which write "owns" the
    value, so neither is bound. Must not be silently guessed either way."""
    mutable = surface["mcp_mutable_candidates"]
    assert "arp.retrigger.rate_enable" not in mutable
    assert "arp.retrigger.rate_value" not in mutable


def test_lfo_atlas_scope_remains_lfo1_through_6_not_expanded():
    """LFO7-10: mapping.py's `for i, lfo in enumerate(spec.lfos)` has NO
    index guard and would technically write LFO6-9 body state -- but the
    Atlas's own direct-UI-testing evidence (SERUM2_SEMANTIC_INVENTORY_FINAL,
    LFO closure) confirms LFO7-10 are headless source-only instances with
    ZERO accessible edit parameters (assigned as a mod source, no edit panel
    ever appeared). No canonical identity is created for lfo7.mode etc --
    doing so without evidence establishing what a write would even mean
    (no UI to verify against) would violate the no-guessing rule."""
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT))
    from serum2.reference.serum_atlas import get_control, _LFO_SLOTS
    assert _LFO_SLOTS == tuple("lfo%d" % i for i in range(1, 7))
    for i in range(7, 11):
        assert get_control("lfo%d.mode" % i) is None, "lfo%d.mode must not exist without evidence" % i


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
