"""Bulk causal verification worker: manifest in, machine-generated evidence out. No per-parameter branches.

    python worker.py <manifest.json> <evidence_out.json> [--session-size N]

Runs in its OWN process against the REAL Serum 2 VST3 hosted in DawDreamer (headless; not the GUI). It imports the
OLDER repo's `serum2` (bridge/codec/vst3_state) -- that package shares a name with this repo's `serum2`, so this
file must never be imported by the rest of this repo; only classify.py (pure) is shared.

Per test (manifest.tests[i]): baseline = init preset + one FX unit with `unit.params`; for each value in `values`
(null = key omitted) write ONE raw kParam via apply_spec -> load into Serum -> observe (state readback, host-param
diff, rendered band energies) ; then reload the baseline and verify restoration; then verify the file round-trip.
Manifest extras: `contexts` (shared base unit/spec_patch a test names via `context`), `domain` (declared kind/min/max/values ->
range_plan.py generates the value vector + out-of-range probes and adds rec["range"]: declared vs reachable vs discovered
default), `purpose: "range"` (status RANGE_CHARACTERIZED). The candidate key is written RAW so out-of-schema probes reach Serum;
each observation records whether serum-mcp's own validator would have accepted that value.
Batched by Serum session: one plugin instance serves `session_size` tests via repeated load_state, then is rebuilt so a
contaminated session cannot poison the batch. The observation channel is audio + state, NOT UI pixels.
"""
import datetime
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "vendor", "serum-mcp", "src"))
sys.path.insert(0, "D:/ableton claude")
sys.path.insert(1, HERE)
import numpy as np  # noqa: E402
from serum2 import bridge, codec, processor_state, vst3_state  # noqa: E402
from serum2.evidence import epoch  # noqa: E402
processor_state.PROCESSOR_VERSION = 9.0  # Serum 2.0.23 epoch (see qualification/pass1/harness_v9.py)
import dawdreamer as daw  # noqa: E402
from classify import classify  # noqa: E402
from preset_build import expand, write_preset  # noqa: E402
from range_plan import characterize  # noqa: E402
from serum_mcp.preset.introspect import extract_spec  # noqa: E402
from serum_mcp.preset.packer import unpack_file  # noqa: E402

PINNED_SHA = "9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3"
PREFIXES = ("Oscillator", "Filter", "Env", "Global", "ModSlot", "FXRack", "VoicePanel")
SR, BLOCK = 44100, 512
SKEL = None


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def key_of(v):
    return "null" if v is None else repr(v)


class Session:
    def __init__(self, cfg):
        self.cfg = cfg
        self.eng = daw.RenderEngine(SR, BLOCK)
        self.syn = self.eng.make_plugin_processor("serum", epoch.SERUM_VST3)
        self.tmp = tempfile.mkdtemp(prefix="bulk_causal_")

    def load(self, preset_path):
        meta, body, _ = bridge.build_v8_state(preset_path, SKEL, PREFIXES)
        p = os.path.join(self.tmp, "state.bin")
        bridge.write_state_file(p, meta, body)
        self.syn.load_state(p)

    def state(self):
        p = os.path.join(self.tmp, "rb.bin")
        self.syn.save_state(p)
        return codec.decode(vst3_state.unwrap_vc2(open(p, "rb").read()))[1]

    def hosts(self):
        return {d["name"]: self.syn.get_parameter_text(d["index"]) for d in self.syn.get_parameters_description()
                if not d["name"].startswith(("CC", "Pitch Bend Chan", "Aftertouch", "Mod "))}

    def bands(self):
        c = self.cfg
        self.syn.clear_midi()
        self.syn.add_midi_note(c["note"], 110, 0.0, c["render_sec"])
        self.eng.load_graph([(self.syn, [])])
        self.eng.render(c["render_sec"] + 0.3)
        a = np.asarray(self.eng.get_audio())
        x = (a.mean(axis=0) if a.ndim > 1 else a)[int(0.2 * SR):int(c["render_sec"] * SR)]
        sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
        f = np.fft.rfftfreq(len(x), 1 / SR)
        e = c["bands"]
        return [round(float(10 * np.log10(sp[(f >= lo) & (f < hi)].sum() + 1e-12)), 2) for lo, hi in zip(e, e[1:])]


def state_value(body, test):
    idx = test["unit"].get("index", 0)
    fx = (body.get("FXRack0") or {}).get("FX") or []
    if idx >= len(fx) or not isinstance(fx[idx], dict):
        return None
    pp = (fx[idx].get(test["unit"]["type"]) or {})
    pp = pp.get("plainParams") if isinstance(pp, dict) else None
    return pp.get(test["candidate"]["kparam"]) if isinstance(pp, dict) else None  # Serum writes the string 'default' for untouched units


def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b)))


def run_test(sess, test, cfg, work):
    test = expand(test, cfg)
    kp = test["candidate"]["kparam"]
    bpath, _ = write_preset(test["id"] + "_base", test, None, work, reference=True)
    sess.load(bpath)
    b1, base_state, base_hosts = sess.bands(), state_value(sess.state(), test), sess.hosts()
    sess.load(bpath)
    b2 = sess.bands()
    floor = max(cfg["min_noise_floor_db"], 2 * max(abs(x - y) for x, y in zip(b1, b2)))
    obs, hashes, rt_ok = {}, {"baseline": sha(bpath)}, True
    dflt = test["candidate"].get("default")
    for v, probe in [(v, False) for v in test["values"]] + [(v, True) for v in test.get("probe_values", [])]:
        p, mcp_ok = write_preset("%s_%s" % (test["id"], key_of(v)), test, v, work)
        hashes[key_of(v)] = sha(p)
        sess.load(p)
        sv, bands, hosts = state_value(sess.state(), test), sess.bands(), sess.hosts()
        obs[key_of(v)] = {"written": v, "state_value": sv, "state_retained": same(sv, v) or (sv is None and dflt is not None and v == dflt), "probe": probe, "mcp_validator_accepts": mcp_ok, "band_db": bands,
                          "host_params_changed": sorted(k for k in hosts if hosts[k] != base_hosts.get(k))[:8]}
        fx = extract_spec(unpack_file(p).data).fx_chain[test["unit"].get("index", 0)]
        rt_ok = rt_ok and (probe or same(fx.params.get(kp), v))
    sess.load(bpath)
    rb, rs = sess.bands(), state_value(sess.state(), test)
    drift = max(abs(x - y) for x, y in zip(rb, b1))
    rest = {"ok": drift <= floor and same(rs, base_state), "band_drift_db": round(drift, 2), "state_value": rs,
            "detail": "drift %.2f dB vs floor %.2f" % (drift, floor)}
    rec = {"id": test["id"], "atlas_id": test.get("atlas_id"), "candidate": test["candidate"], "unit": test["unit"],
           "spec_patch": test.get("spec_patch"), "baseline": {"band_db": b1, "state_value": base_state},
           "observations": obs, "restoration": rest, "file_roundtrip": {"ok": bool(rt_ok)}, "noise_floor_db": round(floor, 2),
           "expect": test.get("expect", []), "preset_sha256": hashes, "purpose": test.get("purpose"), "context": test.get("context"),
           "domain": test.get("domain"), "value_vector": {"values": test["values"], "probes": test.get("probe_values", [])},
           "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if test.get("domain"):
        rec["range"] = characterize(test["domain"], obs)
    rec.update(classify(rec))
    return rec


def main():
    global SKEL
    manifest, out = sys.argv[1], sys.argv[2]
    size = int(sys.argv[sys.argv.index("--session-size") + 1]) if "--session-size" in sys.argv else 8
    cfg = json.load(open(manifest))
    got = sha(epoch.SERUM_BINARY)
    if got != PINNED_SHA:
        raise SystemExit("Serum binary is %s, expected the pinned 2.0.23 build" % got)
    SKEL = bridge.capture_v8_skeleton(epoch.SERUM_VST3)
    work = tempfile.mkdtemp(prefix="bulk_causal_presets_")
    recs, sess = [], None
    for i, t in enumerate(cfg["tests"]):
        if sess is None or i % size == 0:
            sess = Session(cfg)  # checkpoint: fresh Serum instance per batch
        recs.append(run_test(sess, t, cfg, work))
        print("%-42s %-14s %s" % (t["id"], recs[-1]["status"], "; ".join(recs[-1]["reasons"])[:110]))
    json.dump({"harness": {"backend": "real Serum 2.0.23 VST3 in DawDreamer (headless); observation = state readback + rendered "
                           "band energy, NOT GUI pixels", "serum_sha256": got, "product_version": "2.0.23", "state_version": 9.0,
                           "manifest": os.path.abspath(manifest), "manifest_sha256": sha(manifest), "session_size": size,
                           "authorizes_nothing": True}, "records": recs}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
