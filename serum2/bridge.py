"""v5 (.SerumPreset) -> v8 (Serum 2.0.21 processor state) bridge.

Strategy: start from a known-good v8 skeleton captured live from Serum's own
save_state() (guarantees every key Serum expects is present, correctly typed),
then overlay only the specified module subset from the decoded preset body.
Everything not in the subset stays at the skeleton's (Serum-authored) default.
"""
import copy
import dawdreamer as daw
from . import codec, vst3_state

DEFAULT_MODULE_PREFIXES = ("Oscillator", "Filter", "Env", "Global", "ModSlot")


def capture_v8_skeleton(vst3_path: str):
    """Fresh Serum instance, untouched -> (meta, body) via its own save_state.
    This is the ground truth for what a v8 processor state must contain."""
    import tempfile, os
    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor("serum", vst3_path)
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        synth.save_state(tmp)
        raw = open(tmp, "rb").read()
    finally:
        os.remove(tmp)
    icomp = vst3_state.unwrap_vc2(raw)
    return codec.decode(icomp)


def _module_selected(key: str, prefixes) -> bool:
    return any(key == p or key.rstrip("0123456789") == p for p in prefixes)


def build_v8_state(preset_path: str, skeleton, module_prefixes=DEFAULT_MODULE_PREFIXES):
    """Decode a .SerumPreset and overlay the selected modules onto the v8
    skeleton. Returns (meta8, body8) ready for codec.encode + vst3_state.wrap_vc2."""
    skel_meta, skel_body = skeleton
    preset_meta, preset_body = codec.load_preset_file(preset_path)

    body8 = copy.deepcopy(skel_body)
    transplanted = []
    for key, val in preset_body.items():
        if key in body8 and _module_selected(key, module_prefixes):
            body8[key] = val
            transplanted.append(key)

    meta8 = dict(skel_meta)  # keep Serum's own hash/version/product fields as-is
    return meta8, body8, transplanted


def write_state_file(path: str, meta8: dict, body8: dict):
    icomp = codec.encode(meta8, body8)
    blob = vst3_state.wrap_vc2(icomp)
    open(path, "wb").write(blob)
    return len(blob)


def state_hash(meta8: dict, body8: dict) -> str:
    """Stable hash of a generated v8 state -- used to prove a mutation actually
    changed the produced bytes, before any load is attempted."""
    import hashlib
    return hashlib.sha256(codec.encode(meta8, body8)).hexdigest()[:16]
