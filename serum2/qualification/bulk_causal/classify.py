"""Pure classification for the bulk causal harness (no Serum, no old-repo imports: unit-testable in this repo).

A test record (produced by worker.py) is turned into exactly one status. The harness PROVES mappings; it never
authorizes them -- promotion to a binding/contract stays with the existing evidence_promotion/admission pipeline.

Statuses:
  PROVEN         Serum retained the key, every declared expectation held, baseline restored, file round-trip ok
  FAILED         Serum retained the key and something changed, but a declared expectation was violated
  AMBIGUOUS      an effect was observed but the manifest declared no expectation (discovery run; identity unproven)
  NOT_OBSERVED   Serum retained the key but no observable change exceeded the noise floor for any value
  REJECTED       Serum did not retain the key/value (dropped or rewritten): not a real writable parameter here
  RESTORE_FAILED baseline did not come back after the mutations (session contaminated; nothing else is trusted)
"""
from __future__ import annotations

RELATIONS = {
    "decrease_db": lambda d, t: d <= -t,
    "increase_db": lambda d, t: d >= t,
    "unchanged": lambda d, t: abs(d) <= t,
}


def band_delta(rec, value_key, band, vs="baseline"):
    """Band change of one written value vs the reference (default the baseline) or vs another written value."""
    ref = rec["baseline"] if vs == "baseline" else rec["observations"][vs]
    return rec["observations"][value_key]["band_db"][band] - ref["band_db"][band]


def effect_size(rec, value_key):
    """Largest absolute band change vs baseline for one written value."""
    return max(abs(a - b) for a, b in zip(rec["observations"][value_key]["band_db"], rec["baseline"]["band_db"]))



def classify(rec: dict) -> dict:
    """rec: {baseline, observations{value_key: {state_value, band_db, ...}}, restoration{ok}, file_roundtrip{ok},
    noise_floor_db, expect[]} -> {status, reasons[], expectations[]}"""
    reasons = []
    if not rec["restoration"]["ok"]:
        return {"status": "RESTORE_FAILED", "reasons": ["baseline did not return: %s" % rec["restoration"].get("detail")],
                "expectations": []}
    obs = rec["observations"]
    rejected = [k for k, o in obs.items() if not o["state_retained"] and not o.get("probe")]
    if rejected and len(rejected) == len([o for o in obs.values() if not o.get("probe")]):
        return {"status": "REJECTED", "reasons": ["Serum did not retain the written key for values %s" % rejected], "expectations": []}
    floor = rec.get("noise_floor_db", 0.5)
    checked = []
    for e in rec.get("expect", []):
        vk = e["value"]
        d = band_delta(rec, vk, e["band"], e.get("vs", "baseline"))
        ok = RELATIONS[e["relation"]](d, max(e["threshold"], floor) if e["relation"] == "unchanged" else e["threshold"])
        checked.append({**e, "observed_delta_db": round(d, 2), "held": bool(ok)})
    if not rec["file_roundtrip"]["ok"]:
        reasons.append("file round-trip lost the key")
    if checked:
        held = all(c["held"] for c in checked) and rec["file_roundtrip"]["ok"] and not rejected
        if not held and not reasons:
            reasons.append("violated: %s" % [(c["value"], c["band"], c["relation"], c["observed_delta_db"]) for c in checked if not c["held"]])
        if rejected:
            reasons.append("values not retained: %s" % rejected)
        return {"status": "PROVEN" if held else "FAILED", "reasons": reasons, "expectations": checked}
    moved = any(effect_size(rec, k) > floor for k in obs)
    return {"status": "AMBIGUOUS" if moved else "NOT_OBSERVED",
            "reasons": reasons + (["effect observed, no expectation declared"] if moved else ["no change above noise floor %.2f dB" % floor]),
            "expectations": []}


# ---------------------------------------------------------------------------------------------------------------------
# Evidence hierarchy (never collapsed into one status):
#   causal status PROVEN            -> tier CAUSAL_RAW_PROVEN  (raw kParam is real, writable, restorable; behaviour changes)
#   + GUI observations agree        -> tier SEMANTIC_BINDING_PROVEN (this raw value shows as this Atlas label on this control)
# The registry disposition is a third, separate axis and only changes when the binding actually lands.
# ---------------------------------------------------------------------------------------------------------------------
def semantic_classify(causal: dict, gui: list, atlas_labels: list) -> dict:
    """causal: a worker record; gui: observations [{written, kind, displayed_label, agrees_with_causal}] for the SAME
    test; atlas_labels: the Atlas control's enum labels. -> {status, tier, raw_to_label, reasons}"""
    reasons = []
    if causal.get("status") != "PROVEN":
        return {"status": "SEMANTIC_NOT_ATTEMPTED", "tier": None, "raw_to_label": {}, "reasons": ["causal status is %s" % causal.get("status")]}
    vals = [g for g in gui if g["kind"] in ("value",)]
    m = {("null" if g["written"] is None else repr(g["written"])): g["displayed_label"] for g in vals}
    if not vals:
        return {"status": "SEMANTIC_INCOMPLETE", "tier": "CAUSAL_RAW_PROVEN", "raw_to_label": m, "reasons": ["no GUI observations"]}
    off_vocab = sorted({g["displayed_label"] for g in vals} - set(atlas_labels))
    if off_vocab:
        reasons.append("labels not in Atlas vocabulary: %s" % off_vocab)
    disagree = [g["written"] for g in vals if not g.get("agrees_with_causal", False)]
    if disagree:
        reasons.append("GUI disagrees with causal evidence for %s" % disagree)
    # every value the causal test wrote must have a GUI observation
    causal_vals = {k for k, o in causal["observations"].items() if not o.get("probe")}
    missing = sorted(causal_vals - set(m))
    if missing:
        reasons.append("no GUI observation for values %s" % missing)
    if reasons:
        return {"status": "SEMANTIC_MISMATCH" if (off_vocab or disagree) else "SEMANTIC_INCOMPLETE", "tier": "CAUSAL_RAW_PROVEN",
                "raw_to_label": m, "reasons": reasons}
    return {"status": "SEMANTIC_BINDING_PROVEN", "tier": "SEMANTIC_BINDING_PROVEN", "raw_to_label": m, "reasons": []}
