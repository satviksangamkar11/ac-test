"""Build the Pass-1 CapabilityContracts from the fresh Serum 2.0.23 EvidenceRecords, using the existing,
unmodified ClaimEngine / build_contract machinery (same as step4_q4_2). Writes a SEPARATE store; the
archived stores are never read for writing or modified. Contract target == the SEMANTIC_TARGETS
capability_key, so the existing TargetResolver reaches it without any new vocabulary.

Each contract's scope is annotated with the epoch it was proven in (Serum binary sha + product version),
absolute-value semantics, and explicit limitations, as the 4.Q pattern does."""
import pickle
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import harness_v9  # noqa: E402
from serum2.evidence.claim import ClaimDefinition, ClaimEngine, SINGLE_FIELD, OBJECTIVELY_MEASURABLE  # noqa: E402
from serum2.evidence.record import PASS  # noqa: E402
from serum2.evidence.capability_contract import build_contract  # noqa: E402

REC = HERE / "records"
STORE = Path(r"D:\ableton claude final best\experiments\_capability_contracts_pass1.pkl")

# (record id, capability_key, kind, causal metric, measurement target)
TARGETS = [
    ("PASS1-OSC2-ENABLE", "oscillator_field_OSC2-ENABLE", "oscillator_field", "overall_rms_db", "Oscillator1.plainParams.kParamEnable"),
    ("PASS1-OSC3-ENABLE", "oscillator_field_OSC3-ENABLE", "oscillator_field", "overall_rms_db", "Oscillator2.plainParams.kParamEnable"),
    ("PASS1-OSC2-OCTAVE", "oscillator_field_OSC2-OCTAVE", "oscillator_field", "wholesignal_centroid", "Oscillator1.plainParams.kParamOctave"),
    ("PASS1-OSC3-OCTAVE", "oscillator_field_OSC3-OCTAVE", "oscillator_field", "wholesignal_centroid", "Oscillator2.plainParams.kParamOctave"),
] + [
    ("PASS1-ENV%d-%s" % (n, f.upper()), "envelope%d_field_%s" % (n, f), "envelope_field", None, None)
    for n in (2, 3, 4) for f in ("decay", "release")
]

if __name__ == "__main__":
    ident = harness_v9.enable()
    defs, recs = {}, {}
    for rid, key, kind, metric, target in TARGETS:
        rec = pickle.load(open(REC / (rid + ".pkl"), "rb"))
        recs[key] = rec
        causal = metric is not None
        defs[key] = ClaimDefinition(
            claim_type=key, subject_pattern={"kind": kind},
            predicate="produces_measurable_effect" if causal else "constructs_mutates_persists",
            required_gate={"load": PASS, "causal": PASS, "persistence": PASS} if causal else {"load": PASS, "persistence": PASS},
            required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
            dependency_rule={"enabled": False},
            measurability=OBJECTIVELY_MEASURABLE if causal else None,
            **({"required_measurement": {"metric_name": metric, "target": target}} if causal else {}))
    eng = ClaimEngine(defs)
    store = {}
    for rid, key, kind, metric, target in TARGETS:
        group = eng.add(recs[key], key)
        assert group is not None, (key, eng.rejected)
        c = build_contract(group)
        mut = recs[key].experiment["mutations"][0]
        scope = dict(c.scope)
        scope.update({"mutation_value_semantics": "ABSOLUTE_PARAMETER_VALUE",
                      "serum_binary_sha256": ident["serum_sha256"], "serum_product_version": ident["product_version"],
                      "processor_state_version": ident["state_version"],
                      "instance_scope": "this instance path only; not evidence for any other instance"})
        lims = list(c.limitations) + [
            "Proven on Serum %s (state v%s, binary %s...) only; not evidence for other builds" % (
                ident["product_version"], ident["state_version"], ident["serum_sha256"][:8]),
            "Tested only with %s = %r (absolute value); other values not separately proven" % (mut["target_path"], mut["value"]),
            "Single-field isolated mutation (N=1 witness)"]
        if metric is None:
            lims.append("STRUCTURAL_ONLY by design: modulation-source envelope, its audible effect exists only through "
                        "a matrix route and no route was declared; no causal claim is made")
        c = replace(c, scope=scope, limitations=tuple(lims))
        store[(c.provenance["claim_definition_id"], group.condition_signature_hash)] = c
        print("%-34s %-16s %-24s op=%-22s verified=%s prereqs=%d path=%s" % (
            c.target, c.status, "", c.allowed_operation, c.verified, len(c.prerequisites), c.scope.get("mutation_target_path")))
    pickle.dump(store, open(STORE, "wb"))
    print("saved", STORE, "n=", len(store))
