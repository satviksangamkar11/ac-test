"""Phase 3B/3C: live MCP execution harness. Runs each mcp_execution_contract_v1.json row against real Serum via
DawDreamer (serum_backend.SerumBackend) -- no GUI, no clicking.

    python run_mcp_execution_harness.py --sample            # Phase 3B smoke run (~40 rows)
    python run_mcp_execution_harness.py --all --resume      # Phase 3C, all 330, resumable
    python run_mcp_execution_harness.py --fake --all        # offline end-to-end check (no Serum)
    python run_mcp_execution_harness.py --ids a,b,c         # re-run specific rows

Per row, three loads into the same live Serum instance:
  1. baseline body (the row's structural context, no edit)  -> pre_state (Serum's own re-save), pre_hosts
  2. edited body (context + the row's mcp_edit, built through serum-mcp's apply_spec) -> post_state, post_hosts
  3. the SAME baseline body again (unedited) -> restored_state, to prove the edit left no residue
and six answers:
  Q1 addressable     apply_spec built the edited body
  Q2 raw written     every expected_raw leaf is in the edited body we sent
  Q3 Serum persisted every expected_raw leaf in post_state equals the written value; a leaf ABSENT from post_state
                     (Serum omits values equal to its own default) or unchanged from pre_state is a no-op suspect
  Q4 host text       per the row's q4_host_text_check.mode (NAMED / NAMED_THEN_FULL_SCAN / FULL_SCAN / ORACLE)
  Q5 reference       the control map v8 conclusion this result should agree with
  Q6 restoration     reloading the untouched baseline body afterward reproduces pre_state for every judged leaf
                     (restoration_verified); required before a row can be promoted to capability evidence
Every result also carries serum_sha256, the exact Serum binary the row ran against (None for FakeBackend, which
must never be promoted as capability evidence).
Exactly one outcome per row:
  MCP_EXEC_HOST_CONFIRMED         persisted, and a host parameter's text changed (named, or discovered by scan)
  MCP_EXEC_CONFIRMED              persisted, but the NAMED host parameter did not change (worth a look)
  MCP_EXEC_RAW_ONLY               persisted, no host parameter changed at all (scan confirmed)
  MCP_EXEC_CONFORMANCE_EXCEPTION  bucket D row: known divergence, observations recorded against the oracle
  MCP_EXEC_NOOP_SUSPECT           post_state shows no change: the test value likely equals Serum's hidden default
  MCP_EXEC_FAILED                 build error, load error, or the written leaf came back with a different value
Results are appended one JSON line per row as they complete, so a crash loses nothing.
"""
import argparse
import copy
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
BT = os.path.join(REPO, "serum2", "reference", "serum_mcp_binding_table.json")
sys.path.insert(0, HERE)
from bulk_engine import body_get  # noqa: E402
from campaign_derive import base_spec, companion_spec, with_field  # noqa: E402
from preset_build import BASE, SPEC0  # noqa: E402
from range_plan import close  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402

SKIP_HOSTS = ("CC", "Pitch Bend Chan", "Aftertouch", "Mod ")
FORCED_SAMPLE = ["mixer.noise.pan", "mixer.sub.pan", "oscNoise.pan", "oscA.warp_amount", "global.use_ultra_on_render",
                 "macro1.name", "fx.compressor.ratio", "env1.attack_curve", "env2.attack_curve", "env3.attack_curve",
                 "env4.attack_curve", "oscA.wavetable", "oscA.sample_loop_start", "oscA.warp_amount2",
                 "arp.transpose.shape", "global.voice_priority"]


# ------------------------------------------------------------------------------------------------ backends ----------
class LiveBackend:
    """Real Serum 2 via DawDreamer, exactly the load path the campaign and dump_reference_parameter_text.py used."""

    def __init__(self):
        import hashlib
        import serum_backend as sb   # lazy: only importable on the Serum machine
        from serum2.producer.execution_epoch import SERUM_BINARY
        self.b = sb.SerumBackend({})
        self.serum_sha256 = hashlib.sha256(open(SERUM_BINARY, "rb").read()).hexdigest()

    def load(self, body):
        self.b.load(body)

    def state(self):
        return self.b._state()

    def hosts(self):
        syn = self.b.syn
        return {d["name"]: syn.get_parameter_text(d["index"]) for d in syn.get_parameters_description()
                if not d["name"].startswith(SKIP_HOSTS)}


class FakeBackend:
    """Offline stand-in: state = the loaded body; host texts = the value at each named row's raw path. Enough to run
    every row end-to-end and exercise every outcome branch without Serum."""

    def __init__(self, host_paths):
        self.host_paths = host_paths   # host name -> raw path
        self.body = None
        self.serum_sha256 = None   # never a real Serum; must never be promoted as capability evidence

    def load(self, body):
        self.body = copy.deepcopy(body)

    def state(self):
        return copy.deepcopy(self.body)

    def hosts(self):
        return {n: str(body_get(self.body, p)) for n, p in self.host_paths.items()}


# ------------------------------------------------------------------------------------------------ bodies ------------
def client_bodies(ctrl, value):
    """(baseline_body, edited_body) exactly as a serum-mcp client would produce them: the edited spec is re-validated
    through pydantic (model_copy alone skips validation, which would let raw values a real call rejects slip through),
    then encoded by apply_spec. Raises if serum-mcp's own validation rejects the value -- that IS a Q1 failure."""
    if ctrl["kind"] == "fx":
        unit = FxUnitSpec.model_validate({"type": ctrl["fx_type"], "params": {ctrl["param"]: value}, "wet": 100.0})
        base = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=ctrl["fx_type"], params={}, wet=100.0)]}))
        return base, apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [unit]}))
    spec_base = companion_spec(ctrl)[0] or base_spec()
    edited = with_field(spec_base, ctrl, value)
    edited = type(edited).model_validate(edited.model_dump())
    return apply_spec(BASE.data, spec_base), apply_spec(BASE.data, edited)


def build_bodies(row, ctrl):
    return client_bodies(ctrl, row["mcp_edit"]["value"])


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return close(a, b)
    return a == b


# ------------------------------------------------------------------------------------------------ one row -----------
def run_row(row, ctrl, backend):
    out = {"atlas_id": row["atlas_id"], "bucket": row["bucket"], "test_value": row["test_value"],
           "q4_mode": row["q4_host_text_check"]["mode"], "q5_reference": row["q5_reference_conclusion"],
           "serum_sha256": getattr(backend, "serum_sha256", None)}
    try:
        base, edited = build_bodies(row, ctrl)
    except Exception as ex:
        out.update(outcome="MCP_EXEC_FAILED", q1_addressable=False, error="build: %s" % ex)
        return out
    out["q1_addressable"] = True
    exp = row["expected_raw"]
    out["q2_raw_written"] = all(same(body_get(edited, d["path"]), d["value"]) for d in exp)
    try:
        backend.load(base)
        pre_state, pre_hosts = backend.state(), backend.hosts()
        backend.load(edited)
        post_state, post_hosts = backend.state(), backend.hosts()
        backend.load(base)   # Q6: reload the untouched baseline body -- proves the edit didn't leave Serum in a
        restored_state = backend.state()   # different resting state (nothing about "restoring a knob"; base was never touched)
    except Exception as ex:
        out.update(outcome="MCP_EXEC_FAILED", error="load: %s" % ex, trace=traceback.format_exc()[-400:])
        return out

    leaves = []
    primary = row.get("primary_path")
    for d in exp:
        pre, post = body_get(pre_state, d["path"]), body_get(post_state, d["path"])
        restored = body_get(restored_state, d["path"])
        l = {"path": d["path"], "written": d["value"], "pre": pre, "post": post, "restored": restored,
             "persisted": post is not None and same(post, d["value"]),
             "changed": not (pre is None and post is None) and not (pre is not None and post is not None and same(pre, post)),
             "restoration_matches_baseline": (pre is None and restored is None) or
                                              (pre is not None and restored is not None and same(pre, restored))}
        if primary and d["path"] != primary:
            l["side_leaf"] = True                              # a leaf set's companion write, e.g. kParamWarp2 = 0.0
            l["default_omitted"] = pre is None and post is None  # Serum omits a value equal to its own default on save
        leaves.append(l)
    out["q3_leaves"] = leaves
    out["restoration_verified"] = all(l["restoration_matches_baseline"] for l in leaves)
    judged = [l for l in leaves if not l.get("side_leaf")] or leaves   # a leaf set is judged on its primary leaf
    persisted = all(l["persisted"] for l in judged)
    noop = all(not l["changed"] for l in judged)

    changed_hosts = sorted(n for n in post_hosts if post_hosts[n] != pre_hosts.get(n))
    q4 = row["q4_host_text_check"]
    named = q4.get("host_parameter")
    named_changed = bool(named) and named in changed_hosts
    out["q4"] = {"mode": q4["mode"], "named": named, "named_changed": named_changed,
                 "named_pre": pre_hosts.get(named) if named else None, "named_post": post_hosts.get(named) if named else None,
                 "changed_hosts": changed_hosts[:20], "n_changed_hosts": len(changed_hosts)}
    if q4["mode"] == "ORACLE":
        out["q4"]["oracle"] = q4["expected"]
        chk = q4.get("oracle_check") or {}
        if chk.get("kind") == "host_text":
            got = post_hosts.get(chk["param"])
            out["oracle_match"] = got is not None and got.strip() == chk["expect"]
            out["oracle_observed"] = got
        elif chk.get("kind") == "persisted_value":
            out["oracle_match"] = any(l["post"] is not None and same(l["post"], chk["expect"]) for l in leaves)
            out["oracle_observed"] = [l["post"] for l in leaves]
        elif chk.get("kind") == "not_persisted":
            out["oracle_match"] = all(l["post"] is None for l in leaves)
        else:
            out["oracle_match"] = None   # divergence is only visible on screen; recorded, not machine-checked

    if row["bucket"] == "D":
        out["outcome"] = "MCP_EXEC_CONFORMANCE_EXCEPTION"
    elif noop:
        out["outcome"] = "MCP_EXEC_NOOP_SUSPECT"
    elif not persisted:
        out["outcome"] = "MCP_EXEC_FAILED"
        out["error"] = "written leaf came back different (see q3_leaves)"
    elif named_changed or (q4["mode"] != "NAMED" and changed_hosts):
        out["outcome"] = "MCP_EXEC_HOST_CONFIRMED"
        if q4["mode"] in ("FULL_SCAN", "NAMED_THEN_FULL_SCAN") and not named_changed:
            out["new_host_identity_candidates"] = changed_hosts[:10]
    elif q4["mode"] == "NAMED":
        out["outcome"] = "MCP_EXEC_CONFIRMED"
        out["note"] = "persisted in Serum's state, but the named host parameter %r did not change" % named
    else:
        out["outcome"] = "MCP_EXEC_RAW_ONLY"
    return out


# ------------------------------------------------------------------------------------------------ selection ---------
def select_sample(rows, params):
    """One row per (bucket, q4 mode, mechanism, context), plus the forced rows."""
    seen, picked = set(), []
    for r in sorted(rows, key=lambda r: r["atlas_id"]):
        p = params.get(r["atlas_id"], {})
        key = (r["bucket"], r["q4_host_text_check"]["mode"], p.get("mechanism", "OVERRIDE"), p.get("context", "INIT"))
        if key not in seen:
            seen.add(key)
            picked.append(r["atlas_id"])
    for a in FORCED_SAMPLE:
        if a not in picked:
            picked.append(a)
    return picked


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    g.add_argument("--ids")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    contract = json.load(open(os.path.join(ED, "mcp_execution_contract_v1.json")))
    rows = {r["atlas_id"]: r for r in contract["rows"]}
    bt = json.load(open(BT))["controls"]
    params = {p["atlas_id"]: p for p in json.load(open(os.path.join(HERE, "manifest_campaign_v1.json")))["parameters"]}

    if a.sample:
        ids, tag = select_sample(rows.values(), params), "sample"
    elif a.all:
        ids, tag = sorted(rows), "all"
    else:
        ids, tag = [i.strip() for i in a.ids.split(",") if i.strip()], "ids"
    unknown = [i for i in ids if i not in rows]
    if unknown:
        sys.exit("unknown atlas ids: %s" % unknown)

    out_path = a.out or os.path.join(BUV, "mcp_exec_%s%s_results.jsonl" % ("fake_" if a.fake else "", tag))
    done = set()
    if a.resume and os.path.exists(out_path):
        done = {json.loads(l)["atlas_id"] for l in open(out_path) if l.strip()}
    elif os.path.exists(out_path):
        os.remove(out_path)

    if a.fake:
        host_paths = {}
        for r in rows.values():
            n = r["q4_host_text_check"].get("host_parameter")
            if n and r["expected_raw"]:
                host_paths.setdefault(n, r["expected_raw"][0]["path"])
        backend = FakeBackend(host_paths)
    else:
        backend = LiveBackend()

    todo = [i for i in ids if i not in done]
    print("%d rows (%d already done) -> %s" % (len(todo), len(done), out_path))
    counts = {}
    with open(out_path, "a") as f:
        for n, aid in enumerate(todo, 1):
            res = run_row(rows[aid], bt[aid], backend)
            f.write(json.dumps(res, default=repr) + "\n")
            f.flush()
            counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
            if n % 25 == 0 or n == len(todo):
                print("  %d/%d %s" % (n, len(todo), json.dumps(counts)))
    print("done:", json.dumps(counts))


if __name__ == "__main__":
    main()
