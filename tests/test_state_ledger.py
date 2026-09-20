import json, os, sys
import pytest
sys.path.insert(0, "D:/ableton claude final best")
from serum2.producer.state_ledger import (build_all, conservation, match_enum, IGNORED_NAVIGATION, DERIVED,
                                          NOT_SERUM_SURFACE)

RUN = "D:/ableton claude final best/serum2/data/runs/HEEGN1Xl5o4/stage_a_observation.json"


def test_enum_matching_is_generic():
    assert match_enum("MG Low 18", ["L18", "MgL12", "MgL18"]) == "MgL18"
    assert match_enum("MG Ladder", ["LadderAcid", "LadderMg"]) == "LadderMg"
    assert match_enum("OVERDRIVE", ["kOverdrive", "kSoftClip"]) == "kOverdrive"
    assert match_enum("Chaos: Lorenz", ["random_sh", "rossler", "lorenz"]) == "lorenz"
    assert match_enum("PD(B)", ["fm", "am", "sync"]) is None


@pytest.mark.skipif(not os.path.exists(RUN), reason="run data is gitignored")
def test_no_observation_is_silently_lost():
    sa = json.load(open(RUN))
    rows = build_all(sa)
    c = conservation(sa, rows)
    assert c["invariant_holds"], c
    assert not c["missing_from_ledger"] and not c["rows_without_terminal"]
    nav = [r for r in rows if r.control_type in ("tab", "badge_count")]
    assert nav and all(r.terminal == IGNORED_NAVIGATION and r.op is None for r in nav)
    assert all(r.terminal != DERIVED or r.op for r in rows)


def _admitted_table():
    from serum2.producer.state_admission import admit_rows
    R = "D:/ableton claude final best/serum2/data/runs/HEEGN1Xl5o4/"
    rows = build_all(json.load(open(RUN)), json.load(open(R + "reread_log.json")))
    return rows, {(t["control"], t["rack"]): t for t in admit_rows(rows)}


@pytest.mark.skipif(not os.path.exists(RUN), reason="run data is gitignored")
def test_scope_fails_closed_and_no_fuzzy_matching():
    rows, t = _admitted_table()
    assert t[("oscA.octave", None)]["status"] == "ADMITTED"
    assert t[("oscB.wavetable", None)]["status"] == "SCOPE_WOULD_EXPAND"    # wavetable contract proven on Oscillator0 only
    assert t[("oscC.wavetable", None)]["status"] == "SCOPE_WOULD_EXPAND"
    assert t[("oscA.wavetable", None)]["status"] == "INCOMPATIBLE_OPERATION"  # structured operand vs named selection
    assert t[("fx.compressor.ratio", 0)]["status"] == "NO_CAPABILITY"       # similar names are never enough
    assert all(v["contract"] for v in t.values() if v["status"] == "ADMITTED")


@pytest.mark.skipif(not os.path.exists(RUN), reason="run data is gitignored")
def test_compiler_is_operand_driven_and_never_drops():
    from serum2.execution.authorized_state_compiler import ops_from_rows, compile_ops, AuthorizedOperation
    rows, _ = _admitted_table()
    ops = ops_from_rows(rows)
    rep = compile_ops(ops, "t", "t")
    assert rep.status == "SUCCESS" and rep.compiled == rep.admitted == len(ops)
    bad = AuthorizedOperation("x", "x", "SET", 1.0, {"kind": "unknown"}, "c", None, {}, {"frame_ts": 0.0, "rack": 0})
    assert compile_ops(ops + [bad], "t", "t").status == "COMPILATION_INCOMPLETE"


PRE_PASS1_ADMITTED = {  # the 13 admitted before Pass 1; must remain admitted, unchanged
    "oscA.enabled", "oscA.octave", "env1.decay", "env1.sustain", "env1.release", "filter1.type",
    "fx.distortion.type", "fx.equalizer.left_freq", "fx.equalizer.left_q", "fx.equalizer.left_gain",
    "fx.equalizer.right_freq", "fx.equalizer.right_q", "fx.equalizer.right_gain"}
PASS1_NEWLY_ADMITTED = {"oscB.enabled", "oscC.enabled", "oscB.octave", "env2.decay", "env2.release",
                        "env3.decay", "env3.release", "env4.decay", "env4.release"}


@pytest.mark.skipif(not os.path.exists(RUN), reason="run data is gitignored")
def test_pass1_expands_authority_without_regressing_existing_admissions():
    rows, t = _admitted_table()
    admitted = {k[0] for k, v in t.items() if v["status"] == "ADMITTED"}
    assert PRE_PASS1_ADMITTED <= admitted, PRE_PASS1_ADMITTED - admitted
    assert PASS1_NEWLY_ADMITTED <= admitted, PASS1_NEWLY_ADMITTED - admitted
    assert admitted == PRE_PASS1_ADMITTED | PASS1_NEWLY_ADMITTED


def test_default_registry_frontier_is_unchanged_and_pass1_is_opt_in():
    from serum2.producer.contract_registry import ContractRegistry
    default, expanded = ContractRegistry(), ContractRegistry(include_pass1=True)
    assert len(default.contracts) == 33 and "oscillator_field_OSC2-ENABLE" not in default.contracts
    assert len(expanded.contracts) == 43
    b = expanded.contracts["oscillator_field_OSC2-ENABLE"].execution_binding
    assert b.resolver_operation_id == "oscillators[1].enabled" and b.body_path == "Oscillator1.plainParams.kParamEnable"
