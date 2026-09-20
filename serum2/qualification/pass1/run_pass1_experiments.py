"""Authority-expansion Pass 1: Osc B/C (Enable, Octave) + Env 2-4 (Decay, Release).

DESIGN IS DECLARED HERE BEFORE ANY RUN. Thresholds/values below must not be edited after seeing a
result (same rule as the 4.Q.4 fresh-qualification scripts): a failed experiment stays a failure.

Runs the production harness (older repo `serum2.evidence.harness`, real Serum 2.0.21 VST3 in
DawDreamer). Run as its own process:  python run_pass1_experiments.py

Scope rule: evidence for Oscillator0 does NOT cover Oscillator1/2, nor Env0 -> Env1/2/3, so every
target here gets its own single-field isolated experiment on its own instance path.

Osc Enable: control = skeleton default (Osc A on), treatment = that oscillator on. Two equal
  oscillators sum ~ +3 dB, so the declared overall_rms_db threshold is 2.0 dB (not the 6.0 used for A-disable).
Osc Octave: shared baseline_overrides enables the oscillator in both arms (so it is audible) and the
  treatment sets Octave=+2; centroid must rise by >= 100 Hz (same rule as the archived OSC-OCTAVE).
Env2-4 Decay/Release: envelopes 2-4 are modulation sources only; their audible effect exists only
  through a matrix route. No route is declared, so NO causal claim is made: these are
  constructs_mutates_persists (load + persistence) experiments, which yield STRUCTURAL_ONLY contracts.
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, r"D:\ableton claude")
import harness_v9  # noqa: E402  (Serum 2.0.23 epoch adapter; validated by run_positive_controls.py)
from serum2.evidence import harness  # noqa: E402
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus, MeasurementPlan,  # noqa: E402
                                  TargetSpec, SINGLE_FIELD)

OUT = Path(r"D:\ableton claude final best\serum2\qualification\pass1\records")
OUT.mkdir(parents=True, exist_ok=True)
STIM = Stimulus(note=60, velocity=110, note_len=1.8, render_seconds=2.0)


def osc_enable(idx, label):
    path = "Oscillator%d.plainParams.kParamEnable" % idx
    return ExperimentSpec(
        experiment_id="PASS1-OSC%d-ENABLE" % label,
        mutations=[Mutation(path, 1.0, "pass1 fresh: enable oscillator slot %d" % idx)],
        prerequisites=[], isolation_level=SINGLE_FIELD,
        claim_subject="oscillator_field:Oscillator%d.kParamEnable" % idx,
        claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(
            metric="overall_rms_db", target=TargetSpec(path, "Oscillator", "kParamEnable"),
            expected_direction="increase", threshold=2.0, stimulus=STIM, kernel_artifact="overall_rms_db.py")],
        notes="control: skeleton default. treatment: Enable=1.0. Osc A is on in both arms.")


def osc_octave(idx, label):
    path = "Oscillator%d.plainParams.kParamOctave" % idx
    en = "Oscillator%d.plainParams.kParamEnable" % idx
    return ExperimentSpec(
        experiment_id="PASS1-OSC%d-OCTAVE" % label,
        mutations=[Mutation(path, 2.0, "pass1 fresh: +2 octaves")],
        prerequisites=[],
        baseline_overrides=[Mutation(en, 1.0, "shared: oscillator enabled in both arms so it is audible")],
        isolation_level=SINGLE_FIELD,
        claim_subject="oscillator_field:Oscillator%d.kParamOctave" % idx,
        claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(
            metric="wholesignal_centroid", target=TargetSpec(path, "Oscillator", "kParamOctave"),
            expected_direction="increase", threshold=100.0, stimulus=STIM, kernel_artifact="wholesignal_centroid.py")],
        notes="control: implicit default octave, oscillator enabled. treatment: Octave=+2.")


def env_field(idx, label, field, value):
    path = "Env%d.plainParams.%s" % (idx, field)
    return ExperimentSpec(
        experiment_id="PASS1-ENV%d-%s" % (label, field[6:].upper()),
        mutations=[Mutation(path, value, "pass1 fresh: absolute %s value" % field)],
        prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
        claim_subject="envelope_field:Env%d.%s" % (idx, field),
        claim_predicate="constructs_mutates_persists", measurement_plans=[],
        notes="mod-source envelope: no route declared, so no causal claim; construct/mutate/load/persist only.")


specs = [osc_enable(1, 2), osc_enable(2, 3), osc_octave(1, 2), osc_octave(2, 3)]
for idx, label in ((1, 2), (2, 3), (3, 4)):
    specs += [env_field(idx, label, "kParamDecay", 0.5), env_field(idx, label, "kParamRelease", 0.5)]

if __name__ == "__main__":
    print("adapter identity:", harness_v9.enable())
    for spec in specs:
        rec = harness.run(spec)
        line = "%-22s gates=%s" % (spec.experiment_id, rec.gate_completeness())
        if rec.causal_measurements:
            m = rec.causal_measurements[0]
            line += " base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s" % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status)
        print(line, "| persist:", rec.persistence_observation.get("status"))
        pickle.dump(rec, open(OUT / (spec.experiment_id + ".pkl"), "wb"))
