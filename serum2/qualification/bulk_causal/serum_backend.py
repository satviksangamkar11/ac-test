"""Serum side of the bulk engine: a Backend that puts a full preset BODY (dict, in memory) into a live real-Serum instance.

Runs only inside the worker process (imports the OLDER repo's `serum2` for bridge/codec/vst3_state). It writes NO preset: the
body is overlaid onto Serum's own state skeleton, encoded, and written to ONE transient transport file that is overwritten on
every load (Serum's VST3 load_state needs a file). Observation = Serum's own re-saved state + rendered band energy + host
parameter display texts.
"""
import copy
import os
import sys
import tempfile

sys.path.insert(0, "D:/ableton claude")
import numpy as np  # noqa: E402
from serum2 import bridge, codec, processor_state, vst3_state  # noqa: E402
from serum2.evidence import epoch  # noqa: E402
processor_state.PROCESSOR_VERSION = 9.0  # Serum 2.0.23 epoch (see qualification/pass1/harness_v9.py)
import dawdreamer as daw  # noqa: E402

PREFIXES = ("Oscillator", "Filter", "Env", "Global", "ModSlot", "FXRack", "VoicePanel")
SR, BLOCK = 44100, 512
_SKEL = None


def skeleton():
    global _SKEL
    if _SKEL is None:
        _SKEL = bridge.capture_v8_skeleton(epoch.SERUM_VST3)
    return _SKEL


def _selected(key):
    return any(key == p or key.rstrip("0123456789") == p for p in PREFIXES)


class SerumBackend:
    def __init__(self, cfg):
        self.cfg = cfg
        self.eng = daw.RenderEngine(SR, BLOCK)
        self.syn = self.eng.make_plugin_processor("serum", epoch.SERUM_VST3)
        self._dir = tempfile.mkdtemp(prefix="bulk_ctx_")
        self.transport = os.path.join(self._dir, "transport.state")   # the ONE transient file, overwritten per load
        self.loads = 0

    def load(self, body):
        meta, sbody = skeleton()
        b8 = copy.deepcopy(sbody)
        for k, v in body.items():
            if k in b8 and _selected(k):
                b8[k] = v
        bridge.write_state_file(self.transport, dict(meta), b8)
        self.syn.load_state(self.transport)
        self.loads += 1

    def _state(self):
        p = os.path.join(self._dir, "readback.state")
        self.syn.save_state(p)
        return codec.decode(vst3_state.unwrap_vc2(open(p, "rb").read()))[1]

    def _bands(self):
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

    def observe(self):
        hosts = {d["name"]: self.syn.get_parameter_text(d["index"]) for d in self.syn.get_parameters_description()
                 if not d["name"].startswith(("CC", "Pitch Bend Chan", "Aftertouch", "Mod "))}
        return {"state": self._state(), "band_db": self._bands(), "hosts": hosts}
