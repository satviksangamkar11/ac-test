"""The MCP exposure crosswalk: for each of the 330 controls, whether serum-mcp can write it, whether Serum exposes
it as a named VST3 host parameter, and what evidence backs the write. Pure projection of files already in the repo
(control map v8, the two residual derivations) -- no Serum, no new presets, no GUI work.

    python build_mcp_exposure_crosswalk.py

Answers the question the map v8 doesn't: "MCP can write the preset field" != "Serum exposes that field as a named
host parameter" -- 412 host parameters exist; only some fraction of the 330 controls have a confident identity
among them (verified below to match the operator's count: HIGH 166 + MEDIUM 12 + LOW 15 = 193 with *some* identity).

Bucket meaning (A/B/C/D), assigned per control:
  A  MCP-editable AND has a confident (HIGH/MEDIUM) native host-parameter identity
  B  MCP-editable, but no confident host-parameter identity (LOW/NONE) -- MCP can still write the raw preset field;
     Serum just doesn't expose it under an automatable name serum-mcp's own dump surfaced
  C  NOT MCP-editable through serum-mcp's current PresetSpec/apply_spec surface (no field takes this value at all)
  D  a confirmed conformance exception: MCP can write it, but the written value's meaning/effect diverges from what
     the schema/binding claims (mismatch, schema mismatch, or a residual finding like "not persisted")
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")

MISMATCH_CONCLUSIONS = {"UI_MISMATCH", "UI_SCHEMA_MISMATCH", "RESIDUAL_NOT_STORED", "UI_CURVE_UNRESOLVED_FINAL"}
GUI_CONFIRMED_CONCLUSIONS = {"DIRECT_UI_CONFIRMED", "UI_MISMATCH", "UI_SCHEMA_MISMATCH", "UI_CURVE_UNRESOLVED_FINAL"}
# fixed from serum-mcp's own mapping.py / this repo's offline derivation -- NOT re-guessed here
KNOWN_OVERRIDES = {
    "arp.transpose.shape": {"raw_path": ["ArpClip0", "plainParams", "kParamTransposeShape"],
                            "mutation_mechanism": "ENUM_RAW (ArpSpec.transpose_shape; resolved offline, see residual_arp_transpose_shape_v1.json)",
                            "serum_mcp_editable": True, "editable_note": "18/18 vocabulary resolved; writable via serum-mcp's ArpSpec.transpose_shape field"},
    "global.voice_priority": {"raw_path": ["Global0", "plainParams", "kParamVoicePriority"],
                              "mutation_mechanism": "TEXT_RAW (GlobalSpec.voice_priority; raw key confirmed in mapping.py:1430, UNVALIDATED)",
                              "serum_mcp_editable": True, "editable_note": "serum-mcp writes any string through GlobalSpec.voice_priority with no "
                              "enum validation; the raw key is known even though the corresponding GUI control was never located (UI_UNOBSERVABLE)"},
}


def bucket(row):
    if not row["serum_mcp_editable"]:
        return "C"
    if row["final_conclusion"] in MISMATCH_CONCLUSIONS:
        return "D"
    return "A" if row["host_parameter_present"] and row["host_identity_confidence"] in ("HIGH", "MEDIUM") else "B"


def main():
    cmap = json.load(open(os.path.join(ED, "serum_full_control_map_v8.json")))
    rows = []
    for c in cmap["controls"]:
        ov = KNOWN_OVERRIDES.get(c["atlas_id"], {})
        hid = c["serum_native_identity"]["host_parameter"]
        row = {
            "atlas_id": c["atlas_id"],
            "raw_path": ov.get("raw_path", c["raw_path"]),
            "serum_mcp_editable": ov.get("serum_mcp_editable", c["mutation_mechanism"] is not None),
            "mutation_mechanism": ov.get("mutation_mechanism", c["mutation_mechanism"]),
            "host_parameter_present": hid is not None,
            "host_parameter_name": hid["name"] if hid else None,
            "host_parameter_index": hid["index"] if hid else None,
            "host_identity_confidence": c["serum_native_identity"]["confidence"],
            "host_text_available": bool((c["evidence"].get("B_host_text") or {}).get("reference_dump")
                                        or (c["evidence"].get("B_host_text") or {}).get("bulk")),
            "GUI_confirmed": c["final_conclusion"] in GUI_CONFIRMED_CONCLUSIONS,
            "final_conclusion": c["final_conclusion"],
        }
        row["editable_note"] = ov.get("editable_note")
        row["bucket"] = bucket(row)
        rows.append(row)

    assert len(rows) == 330 == len({r["atlas_id"] for r in rows})
    conf_counts = Counter(r["host_identity_confidence"] for r in rows)
    some_identity = sum(v for k, v in conf_counts.items() if k != "NONE")
    assert conf_counts == Counter({"HIGH": 166, "NONE": 137, "LOW": 15, "MEDIUM": 12}), conf_counts   # matches the reviewer's table exactly
    assert some_identity == 193
    bucket_counts = Counter(r["bucket"] for r in rows)
    assert sum(bucket_counts.values()) == 330

    out = {"version": 1, "total_controls": 330, "source_map": "serum_full_control_map_v8.json",
           "host_dump": {"total_host_parameters": 412, "note": "the 330 campaign controls are a curated subset the Atlas "
                        "tracks; Serum exposes 412 raw VST3 host parameters in total, most with no campaign candidate at all"},
           "host_identity_confidence_counts": dict(conf_counts), "controls_with_some_host_identity": some_identity,
           "bucket_definitions": {"A": "MCP-editable + confident (HIGH/MEDIUM) host-parameter identity",
                                  "B": "MCP-editable, no confident host-parameter identity (raw preset field only)",
                                  "C": "not MCP-editable through serum-mcp's current PresetSpec/apply_spec surface",
                                  "D": "MCP-editable, but a confirmed conformance exception (mismatch/schema mismatch/not persisted/unresolved curve)"},
           "bucket_counts": dict(bucket_counts), "controls": rows}
    json.dump(out, open(os.path.join(ED, "serum_mcp_exposure_crosswalk_v1.json"), "w"), indent=1, default=repr, ensure_ascii=False)

    print("host identity confidence:", dict(conf_counts), "-> some identity:", some_identity, "/ 330")
    print("bucket counts:", dict(bucket_counts))
    print("bucket C (not MCP-editable at all):", sorted(r["atlas_id"] for r in rows if r["bucket"] == "C"))
    print("bucket D (conformance exceptions):", sorted(r["atlas_id"] for r in rows if r["bucket"] == "D"))


if __name__ == "__main__":
    main()
