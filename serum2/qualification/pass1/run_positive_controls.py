"""Positive controls for the Serum 2.0.23 adapter. These are the archived specs of already-qualified
targets (Env1 Release, Osc A Enable, Osc A Octave) with their ORIGINAL thresholds and stimuli. If the
harness on 2.0.23 does not reproduce EFFECT_OBSERVED for all three, the adapter is not valid and
Pass 1 must not run. Thresholds are copied, not tuned."""
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harness_v9  # noqa: E402

ident = harness_v9.enable()
from serum2.evidence import harness  # noqa: E402
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus, MeasurementPlan,  # noqa: E402
                                  TargetSpec, SINGLE_FIELD)

OUT = Path(r"D:\ableton claude final best\serum2\qualification\pass1\records")
OUT.mkdir(parents=True, exist_ok=True)


def osc(exp_id, path, value, prov, metric, direction, threshold, kernel, subject):
    return ExperimentSpec(
        experiment_id=exp_id, mutations=[Mutation(path, value, prov)], prerequisites=[], isolation_level=SINGLE_FIELD,
        claim_subject=subject, claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(metric=metric, target=TargetSpec(path), expected_direction=direction,
                                           threshold=threshold, stimulus=Stimulus(60, 110, 1.8, 2.0),
                                           kernel_artifact=kernel)],
        notes="positive control on Serum 2.0.23; archived spec + threshold")


controls = [
    ExperimentSpec(
        experiment_id="PC-ENV1-RELEASE",
        mutations=[Mutation("Env0.plainParams.kParamRelease", 1.0, "synthetic: long release")],
        prerequisites=[],
        baseline_overrides=[Mutation("Env0.plainParams.kParamDecay", 0.02, "shared: short decay")],
        isolation_level=SINGLE_FIELD, claim_subject="envelope_field:Env.kParamRelease",
        claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(
            metric="tail_rms_db", target=TargetSpec("Env0.plainParams.kParamRelease", "Env", "kParamRelease"),
            expected_direction="increase", threshold=3.0,
            stimulus=Stimulus(note=60, velocity=110, note_len=0.4, render_seconds=2.0, tail_start=0.6),
            kernel_artifact="tail_rms_db.py")],
        notes="positive control on Serum 2.0.23; archived ENV-RELEASE spec + threshold"),
    osc("PC-OSC-ENABLE", "Oscillator0.plainParams.kParamEnable", 0.0, "synthetic: disable oscillator A",
        "overall_rms_db", "decrease", 6.0, "overall_rms_db.py", "oscillator_field:Oscillator.kParamEnable"),
    osc("PC-OSC-OCTAVE", "Oscillator0.plainParams.kParamOctave", 2.0, "synthetic: +2 octaves",
        "wholesignal_centroid", "increase", 100.0, "wholesignal_centroid.py", "oscillator_field:Oscillator.kParamOctave"),
]

if __name__ == "__main__":
    print("adapter identity:", json.dumps(ident))
    ok = True
    for spec in controls:
        rec = harness.run(spec)
        m = rec.causal_measurements[0]
        good = m.status == "EFFECT_OBSERVED" and rec.gate_completeness().get("persistence") == "PASS"
        ok &= good
        print("%-16s gates=%s base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s -> %s" % (
            spec.experiment_id, rec.gate_completeness(), m.baseline, m.treatment, m.delta, m.observed_direction,
            m.status, "REPRODUCED" if good else "NOT REPRODUCED"))
        pickle.dump(rec, open(OUT / (spec.experiment_id + ".pkl"), "wb"))
    print("POSITIVE CONTROLS:", "ALL REPRODUCED" if ok else "FAILED -- adapter invalid, do not run Pass 1")
    sys.exit(0 if ok else 1)
