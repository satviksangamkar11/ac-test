"""Reference-data provenance persisted on ProductionExperienceRecord."""
import json
import pytest
from pathlib import Path
from types import SimpleNamespace

from serum2.server import experience_record as ER
from serum2.server.experience_record import (
    ProductionExperienceRecord, REFERENCE_PROVENANCE_KEY, create_initial, load, save,
    reference_provenance, stamp_reference_provenance,
)
from serum2.reference.serum_atlas import atlas_provenance
from serum2.reference import serum_audit

REQUIRED = ("serum_version", "control_atlas_version", "ui_atlas_version",
            "source_audit_version", "source_audit_hash")
EXP_DIR = Path(__file__).parents[1] / "data" / "experiences"


def _run():
    return SimpleNamespace(run_id="r1", intent={}, admission={}, source_id="s1",
                           youtube_url="https://example.com/v", transcript_snippet="t")


def test_new_episode_contains_reference_provenance():
    ref = reference_provenance(create_initial(_run()))
    assert all(ref[k] for k in REQUIRED)
    assert ref["source_audit_hash"] == serum_audit.load_audit()["manifest"]["artifact_sha256"]
    assert ref == atlas_provenance()


def test_hash_survives_round_trip_exactly(tmp_path):
    rec = create_initial(_run())
    save(rec, tmp_path)
    back = load("exp_r1", tmp_path)
    assert reference_provenance(back) == reference_provenance(rec)
    raw = json.loads((tmp_path / "exp_r1.json").read_text())
    assert raw["provenance"][REFERENCE_PROVENANCE_KEY]["source_audit_hash"].startswith("fac5ced3")


def test_old_episode_without_field_loads_and_is_not_fabricated(tmp_path):
    old = {"experience_id": "exp_old", "run_id": "old", "provenance": {"source_id": "x"}}
    (tmp_path / "exp_old.json").write_text(json.dumps(old))
    rec = load("exp_old", tmp_path)
    assert reference_provenance(rec) is None            # nothing recorded -> nothing invented
    save(rec, tmp_path)                                  # re-saving does not add it either
    assert reference_provenance(load("exp_old", tmp_path)) is None


def test_existing_provenance_is_never_substituted():
    rec = ProductionExperienceRecord(experience_id="e", run_id="r",
                                     provenance={REFERENCE_PROVENANCE_KEY: {"source_audit_hash": "old-hash"}})
    stamp_reference_provenance(rec)
    assert reference_provenance(rec) == {"source_audit_hash": "old-hash"}


def test_reference_provenance_separate_from_source_provenance():
    rec = create_initial(_run())
    src = {k: v for k, v in rec.provenance.items() if k != REFERENCE_PROVENANCE_KEY}
    assert all(isinstance(v, str) for v in src.values())          # per-field source attribution unchanged
    assert set(src) >= {"source_id", "source_url", "transcript_source_ref", "brain_decision"}
    assert isinstance(rec.provenance[REFERENCE_PROVENANCE_KEY], dict)
    assert rec.source_id == "s1"                                   # source fields untouched


def test_replay_reads_stored_provenance_without_reference_files(tmp_path, monkeypatch):
    save(create_initial(_run()), tmp_path)
    monkeypatch.setattr(serum_audit, "_AUDIT_PATH", tmp_path / "does_not_exist.json")
    monkeypatch.setattr(serum_audit, "_CACHE", None)
    ref = reference_provenance(load("exp_r1", tmp_path))           # no Atlas/audit access needed
    assert ref["source_audit_hash"].startswith("fac5ced3")


@pytest.mark.skipif(not (EXP_DIR / "vlp1_mu6_env1release_20260919_064310.json").exists(),
                    reason="real mU6 episodes live in gitignored serum2/data")
def test_real_mu6_episodes_carry_no_fabricated_provenance():
    rec_file = EXP_DIR / "vlp1_mu6_env1release_20260919_064310.json"
    raw = json.loads(rec_file.read_text())
    rec = ProductionExperienceRecord.from_dict(raw)              # still loads unchanged
    assert reference_provenance(rec) is None and REFERENCE_PROVENANCE_KEY not in raw["provenance"]
    # the other mU6 file is a run report in a different shape (never a ProductionExperienceRecord)
    report = (EXP_DIR / "vlp1_mu6_fresh_rerun_20260919_072419.json").read_text()
    assert REFERENCE_PROVENANCE_KEY not in report and "source_audit_hash" not in report
