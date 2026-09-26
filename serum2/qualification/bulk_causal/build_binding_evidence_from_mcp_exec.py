"""Phase 1 of the full-coverage plan: turn the Phase 3E MCP execution results (330 rows, restoration-verified,
Serum-sha-stamped) into real CapabilityContracts, at whatever tier the evidence actually supports.

    python build_binding_evidence_from_mcp_exec.py <results.jsonl> [--serum-binary PATH]

Consumes `run_mcp_execution_harness.py`'s output directly (NOT the older `mcp_execution_results_*_v1.json` report,
which predates the restoration check). For each row it builds the evidence shape
`serum2.qualification.evidence_promotion.promote_verified_evidence` already consumes, dry-runs it through that
existing pure function (no admission, no mutation of any authority file), and writes only what it ACCEPTS into a new
directory. Every rejection is recorded with its exact reason -- nothing is forced through, and bucket-D
(conformance-exception) rows are never promoted; they document a known divergence, not a capability.

`promote_verified_evidence` calls `execution_epoch.installed_epoch()`, which hashes the actual Serum binary on the
machine it runs on. This container has no Serum install, so `--serum-binary` must point at a real copy of the exact
pinned build (sha256 9293eb90...) for the dry run to resolve an epoch at all -- this script overrides
`execution_epoch.SERUM_BINARY` to that path for the duration of the run; it never invents or bypasses the epoch
check itself.

Atlas bounds gap: the 908-record audit records many continuous/knob controls' displayed range as PROSE (e.g. "musical
divisions (BPM mode) or ms (Hz mode)") because that's what the UI shows, so `ReferenceControl.min_value/max_value`
are None even though the underlying raw automation parameter has a real, already-established numeric domain (the same
`domain` field `manifest_campaign_v1.json` was built from and every campaign row was swept/verified against). Where
that manifest domain is present and purely numeric (continuous/signed/log kinds), this script augments ONLY this
run's in-memory `get_control()` result with those bounds via `dataclasses.replace()` -- the same "augment at load
time, never mutate the frozen object" pattern `contract_registry.py` already uses for host-parameter names. It never
touches `serum_atlas.py` itself, never invents a bound with no evidence behind it (an "open"-kind manifest domain,
which has none, is left alone), and every augmentation is recorded in the report.

Writes:
  parameter_characterization/binding_evidence_mcp_exec_v1/<target>.json   (accepted contracts' source evidence)
  parameter_characterization/bulk_causal_evidence/binding_evidence_mcp_exec_promotion_report_v1.json (full report)
"""
import argparse
import dataclasses
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
OUT_DIR = os.path.join(REPO, "parameter_characterization", "binding_evidence_mcp_exec_v1")
sys.path.insert(0, REPO)

PROMOTABLE_OUTCOMES = {"MCP_EXEC_HOST_CONFIRMED", "MCP_EXEC_CONFIRMED", "MCP_EXEC_RAW_ONLY"}


def _leaf_for(row):
    """The single leaf this row's promotion is judged on: the primary leaf for a leaf set, the only leaf
    otherwise. Side leaves (a leaf set's companion writes) are never used -- same rule the harness itself judges
    outcomes on."""
    leaves = row.get("q3_leaves") or []
    judged = [l for l in leaves if not l.get("side_leaf")] or leaves
    return judged[0] if len(judged) == 1 else None   # multi-leaf rows with no single judged leaf: skip, don't guess


def to_evidence(row, body_key_to_canonical=None):
    """One mcp_exec result row -> the dict shape evidence_promotion.py consumes, or (None, reason).

    body_key_to_canonical: optional dict mapping Serum's internal body-representation strings to the
    canonical Atlas display-name strings (e.g. {'L12': 'lowpass_12', 'Analog/Basic Shapes.wav': 'analog_basic'}).
    Serum's VST body stores internal C++ enum keys and .wav filenames rather than the Atlas's canonical display
    names; without this normalization the promoter's enum membership check ('L12' not in ('lowpass_12', ...))
    rejects evidence that is genuinely valid. The mapping is purely canonical -- it never invents or widens a
    value, only resolves a known representation difference. Body keys absent from the map are left unchanged.
    """
    if row["outcome"] not in PROMOTABLE_OUTCOMES:
        return None, "outcome %r is not promotable (bucket D / no host confirmation path)" % row["outcome"]
    if row.get("restoration_verified") is not True:
        return None, "restoration_verified is not True"
    sha = row.get("serum_sha256")
    if not sha:
        return None, "no serum_sha256 stamped (FakeBackend row, or pre-Phase-3E result)"
    leaf = _leaf_for(row)
    if leaf is None:
        return None, "no single judged leaf (multi-leaf row with no clear primary)"
    if not leaf["persisted"]:
        return None, "leaf did not persist"
    path = ".".join(str(p) for p in leaf["path"])
    raw_after = leaf["post"]
    canonical_after = (body_key_to_canonical or {}).get(raw_after, raw_after)
    ev = {
        "target": row["atlas_id"],
        "epoch": {"serum_sha256": sha, "product_version": "2.0.23"},
        "status": "STRUCTURAL_VERIFIED",
        "restoration_verified": True,
        "body_diff_filtered": [{"path": path, "before": leaf["pre"], "after": canonical_after}],
        "baseline_value": leaf["pre"], "mutated_value": canonical_after,
        "backend": "run_mcp_execution_harness.py (real Serum VST3 in DawDreamer; load/edit/reload restoration check)",
        "source_outcome": row["outcome"], "source_q4_mode": row.get("q4_mode"),
    }
    if raw_after != canonical_after:
        ev["body_key_normalized_from"] = raw_after
    return ev, None


_NUMERIC_DOMAIN_KINDS = ("continuous", "signed", "log")   # manifest domain kinds that carry a real numeric lo/hi;
                                                            # "open" and enum-like kinds are deliberately excluded


def _augmented_get_control(real_get_control, params, augmented_log):
    """Wraps the real get_control(): if the Atlas has no numeric bounds for a continuous/knob/etc. control AND the
    campaign manifest independently established a real numeric domain for it, return a dataclasses.replace() copy
    with those bounds filled in. Every other field, and every control the Atlas already bounds, passes through
    completely unchanged -- this never overrides an Atlas-declared bound, only fills a genuine gap."""
    def wrapped(target):
        c = real_get_control(target)
        if c is None or c.control_type not in ("continuous", "knob", "stepper", "draggable_value"):
            return c
        if c.min_value is not None or c.max_value is not None:
            return c
        dom = params.get(target, {}).get("domain") or {}
        if dom.get("kind") not in _NUMERIC_DOMAIN_KINDS or dom.get("min") is None or dom.get("max") is None:
            return c
        augmented_log.append({"target": target, "min": dom["min"], "max": dom["max"],
                              "source": "manifest_campaign_v1.json domain (kind=%s)" % dom["kind"]})
        return dataclasses.replace(c, min_value=dom["min"], max_value=dom["max"])
    return wrapped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--serum-binary", required=True,
                    help="path to a real copy of the pinned Serum 2.0.23 VST3 binary (sha256 9293eb90...), "
                         "needed for execution_epoch.installed_epoch() to resolve an epoch in this environment")
    ap.add_argument("--manifest", default=os.path.join(HERE, "manifest_campaign_v1.json"))
    a = ap.parse_args()

    import functools
    from serum2.producer import execution_epoch
    from serum2.qualification import evidence_promotion
    from serum2.reference import serum_atlas
    # installed_epoch's `binary` default binds at def-time, so mutating execution_epoch.SERUM_BINARY afterward has
    # no effect on the already-imported function object. Bind the real path explicitly instead -- installed_epoch
    # still does its own hashing/epoch-lookup on this exact file; nothing about the check itself is skipped.
    evidence_promotion.installed_epoch = functools.partial(execution_epoch.installed_epoch, binary=a.serum_binary)

    params = {p["atlas_id"]: p for p in json.load(open(a.manifest))["parameters"]}
    bounds_augmented = []
    evidence_promotion.get_control = _augmented_get_control(serum_atlas.get_control, params, bounds_augmented)
    from serum2.qualification.evidence_promotion import promote_verified_evidence

    # Build body-key -> canonical-display-name normalization table from the schema snapshot.
    # Serum's VST body stores internal C++ enum keys (e.g. 'L12') and .wav filenames (e.g.
    # 'Analog/Basic Shapes.wav') rather than the Atlas's canonical display-name strings. The
    # snapshot already encodes the complete mapping; inverting it gives a normalizer that lets
    # the promoter's enum membership check pass for evidence that is genuinely valid.
    _snap_path = os.path.join(REPO, "serum2", "reference", "serum_2_0_21_schema_snapshot.json")
    _snap = json.load(open(_snap_path))["snapshot"]
    body_key_to_canonical: dict = {}
    for _canon, _body in _snap.get("simple_filter_types", {}).items():
        body_key_to_canonical[_body] = _canon          # e.g. 'L12' -> 'lowpass_12'
    for _canon, _body in _snap.get("simple_wavetables", {}).items():
        body_key_to_canonical[_body] = _canon          # e.g. 'Analog/Basic Shapes.wav' -> 'analog_basic'
    for _canon, _body in _snap.get("simple_sub_shapes", {}).items():
        body_key_to_canonical[_body] = _canon          # e.g. 'kSaw' -> 'saw'

    rows = [json.loads(l) for l in open(a.results) if l.strip()]
    os.makedirs(OUT_DIR, exist_ok=True)

    report = {"source": os.path.basename(a.results), "n_rows": len(rows), "accepted": [], "rejected": {},
              "atlas_bounds_augmented_from_manifest": bounds_augmented}
    for row in rows:
        aid = row["atlas_id"]
        ev, why = to_evidence(row, body_key_to_canonical=body_key_to_canonical)
        if ev is None:
            report["rejected"].setdefault(why, []).append(aid)
            continue
        result = promote_verified_evidence(ev)
        if not result.promoted:
            report["rejected"].setdefault("%s: %s" % (result.reason, result.detail), []).append(aid)
            continue
        json.dump(ev, open(os.path.join(OUT_DIR, aid + ".json"), "w"), indent=1)
        report["accepted"].append({"target": aid, "contract_status": result.contract.status,
                                    "allowed_operation": result.contract.allowed_operation})

    report["atlas_bounds_augmented_from_manifest"] = list({b["target"]: b for b in bounds_augmented}.values())
    report["n_accepted"] = len(report["accepted"])
    report["n_rejected"] = sum(len(v) for v in report["rejected"].values())
    report["n_atlas_bounds_augmented"] = len(report["atlas_bounds_augmented_from_manifest"])
    report["rejection_reason_counts"] = {k: len(v) for k, v in sorted(report["rejected"].items(), key=lambda kv: -len(kv[1]))}
    json.dump(report, open(os.path.join(ED, "binding_evidence_mcp_exec_promotion_report_v1.json"), "w"), indent=1)
    print(json.dumps({"n_rows": report["n_rows"], "n_accepted": report["n_accepted"], "n_rejected": report["n_rejected"],
                      "n_atlas_bounds_augmented": report["n_atlas_bounds_augmented"],
                      "rejection_reason_counts": report["rejection_reason_counts"]}, indent=1))


if __name__ == "__main__":
    main()
