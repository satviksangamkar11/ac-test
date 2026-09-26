"""Offline derivation of arp.transpose.shape's raw vocabulary (no Serum needed).

serum-mcp's ArpSpec.transpose_shape field is documented as accepting "one of the same values as `shape`"
(arp.pattern.shape's own vocabulary). This runs apply_spec with each of that vocabulary's 15 words on the
transpose_shape field and records the raw string it writes -- resolving 15 of the 18 display labels the
2026-09-26 scan enumerated on the TRANSPOSE tab (session 1, ui_scan_2026-09-26.md) without touching Serum.

Confidence: HIGH but not DIRECT_UI -- the raw<->word correspondence is the schema's own dict (SIMPLE_ARP_SHAPES),
not a screen read of the TRANSPOSE tab specifically. 'Up', 'Pinky Up' and 'Pinky UD' are NOT in this vocabulary
and stay unresolved; RESIDUAL_INSTRUCTIONS.md covers them.

    python derive_transpose_shape.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
sys.path.insert(0, HERE)
from campaign_derive import leaves  # noqa: E402
from preset_build import BASE, SPEC0  # noqa: E402
from serum_mcp.generation import spec as S  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402

# same word list arp.pattern.shape uses (campaign_derive.VOCAB -> schema.SIMPLE_ARP_SHAPES), in Serum's screen order
WORDS = ["down", "up_down", "down_up", "up_and_down", "down_and_up", "thumb_up", "thumb_up_down",
         "converge", "diverge", "converge_diverge", "chord", "random", "random_no_dup", "random_drift", "random_once"]
# the 18 screen labels (session 1 scan), Serum's own order, so a human can line them up against the table
SCREEN_LABELS_IN_ORDER = ["Up", "Down", "Up/Down", "Down/Up", "Up+Down", "Down+Up", "Thumb Up", "Thumb UD",
                          "Pinky Up", "Pinky UD", "Converge", "Diverge", "Con+Diverge", "Chord", "Random",
                          "Rand No Dup", "Rand Drift", "Rand Once"]
NOT_IN_PATTERN_SHAPE_VOCAB = ["Up", "Pinky Up", "Pinky UD"]


def main():
    spec0 = SPEC0.model_copy(update={"arp": S.ArpSpec()})
    base = apply_spec(BASE.data, spec0)
    rows = []
    for w in WORDS:
        spec2 = spec0.model_copy(update={"arp": spec0.arp.model_copy(update={"transpose_shape": w})})
        d = leaves(base, apply_spec(BASE.data, spec2))
        assert len(d) == 1 and d[0][0] == ["ArpClip0", "plainParams", "kParamTransposeShape"], d
        rows.append({"schema_word": w, "raw_value": d[0][2]})
    assert len({r["raw_value"] for r in rows}) == len(rows)
    out = {"atlas_id": "arp.transpose.shape", "raw_path": ["ArpClip0", "plainParams", "kParamTransposeShape"],
           "method": "offline apply_spec diff (A tier, causal) -- NOT a screen read", "confidence": "HIGH_NOT_DIRECT_UI",
           "resolved": rows, "screen_labels_in_order": SCREEN_LABELS_IN_ORDER,
           "still_unresolved": NOT_IN_PATTERN_SHAPE_VOCAB,
           "note": "transpose_shape's vocabulary is documented as identical to arp.pattern.shape's; this derives the raw "
                   "string per word the same way apply_spec would encode it. 'Up', 'Pinky Up', 'Pinky UD' are additional "
                   "labels this dropdown has that pattern.shape's vocabulary does not, so their raw values are unknown -- "
                   "see RESIDUAL_INSTRUCTIONS.md for how to get them from Serum directly."}
    json.dump(out, open(os.path.join(ED, "residual_arp_transpose_shape_v1.json"), "w"), indent=1)
    print("resolved %d/%d screen labels; unresolved: %s" % (len(rows), len(SCREEN_LABELS_IN_ORDER), NOT_IN_PATTERN_SHAPE_VOCAB))
    for r in rows:
        print(" ", r["schema_word"], "->", r["raw_value"])


if __name__ == "__main__":
    main()
