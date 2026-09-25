"""Step 2 of the DIRECT_UI speed-up: read Serum's OWN display text for every host parameter of a preset, no clicking.

    python dump_reference_parameter_text.py [preset] [out.json]
    (defaults: giant_verify_out/VERIFY_REFERENCE_FULL.SerumPreset -> giant_verify_out/reference_parameter_text.json)

Windows / DawDreamer machine only (imports serum_backend, i.e. the real Serum VST3). The preset's body goes through the
exact load path the campaign used (SerumBackend.load), then every host parameter's get_parameter_text is recorded, plus
the same dump for the plain init body so each parameter's change from init is visible. Host names are Serum's own
(e.g. 'Env 1 Sustain'); mapping them to atlas_ids happens offline, not here.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from preset_build import BASE, unpack_file  # noqa: E402
import serum_backend as sb  # noqa: E402

SKIP = ("CC", "Pitch Bend Chan", "Aftertouch", "Mod ")


def host_texts(backend):
    syn = backend.syn
    return {d["name"]: {"index": d["index"], "text": syn.get_parameter_text(d["index"]), "value": syn.get_parameter(d["index"])}
            for d in syn.get_parameters_description() if not d["name"].startswith(SKIP)}


def main(preset_path, out_path):
    backend = sb.SerumBackend({})         # cfg is only used for rendering bands, which this script never does
    backend.load(BASE.data)
    init = host_texts(backend)
    backend.load(unpack_file(preset_path).data)
    ref = host_texts(backend)
    changed = sorted(n for n in ref if ref[n]["text"] != init.get(n, {}).get("text"))
    json.dump({"preset_file": os.path.abspath(preset_path), "n_host_params": len(ref), "changed_from_init": changed,
               "reference": ref, "init": init}, open(out_path, "w"), indent=1)
    print("%d host params, %d display differently from init -> %s" % (len(ref), len(changed), out_path))


if __name__ == "__main__":
    a = sys.argv[1:] + [None] * 2
    main(a[0] or os.path.join(HERE, "giant_verify_out", "VERIFY_REFERENCE_FULL.SerumPreset"),
         a[1] or os.path.join(HERE, "giant_verify_out", "reference_parameter_text.json"))
