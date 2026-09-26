"""The one-command entry point must stop at the Stage-A checkpoint with exit code 2 and the exact resume message --
never proceed past it with a fabricated preset."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "youtube_to_serum"))
import run_full_pipeline as pipeline  # noqa: E402
import reference_engine as eng  # noqa: E402


def test_stops_at_stage_a_checkpoint_with_exit_code_2(tmp_path, monkeypatch, capsys):
    def fake_stage1(url, work_dir):
        raise eng.NeedsStageACensus(str(work_dir / "stage_a_skeleton.json"),
                                    str(work_dir / "normalized_transcript.json"), 42)
    monkeypatch.setattr(pipeline, "run_stage1_acquire_and_prep", fake_stage1)
    monkeypatch.setattr(sys, "argv", ["run_full_pipeline.py", "https://www.youtube.com/watch?v=h4biGNiYJTQ",
                                      "--work-dir", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 2
    out = capsys.readouterr().out
    assert "42 frames prepared" in out
    assert "--resume-from stage_a" in out


def test_stops_at_bridge_checkpoint_with_exit_code_3_and_names_the_exact_command(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    fake_run = SimpleNamespace(
        preset={"path": str(tmp_path / "fake.SerumPreset")}, verification_level="FILE_READBACK_VERIFIED_ONLY",
        coverage_status="PARTIAL", reference_verified=False, rows=[],
    )
    monkeypatch.setattr(pipeline, "run_stage1_acquire_and_prep", lambda url, wd: {"n_frames": 1, "stage_a_skeleton_path": "x"})
    monkeypatch.setattr(pipeline, "run_stage2_reproduce", lambda *a, **kw: {"run": fake_run, "brief": []})
    monkeypatch.setattr(pipeline, "build_forensic_report", lambda *a, **kw: str(tmp_path / "report.docx"))

    def fake_load_and_verify(*a, **kw):
        raise pipeline.BridgeUnavailable("The Ableton bridge only runs on Windows. Remedy: run on that machine.")
    monkeypatch.setattr(pipeline, "load_and_verify", fake_load_and_verify)
    monkeypatch.setattr(sys, "argv", ["run_full_pipeline.py", "https://www.youtube.com/watch?v=h4biGNiYJTQ",
                                      "--work-dir", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 3
    out = capsys.readouterr().out
    assert "run_full_pipeline.py" in out and "h4biGNiYJTQ" in out   # names the exact resume command
    assert str(fake_run.preset["path"]) in out


def test_skip_bridge_stops_cleanly_after_compilation(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    fake_run = SimpleNamespace(
        preset={"path": str(tmp_path / "fake.SerumPreset")}, verification_level="FILE_READBACK_VERIFIED_ONLY",
        coverage_status="PARTIAL", reference_verified=False, rows=[],
    )
    monkeypatch.setattr(pipeline, "run_stage1_acquire_and_prep", lambda url, wd: {"n_frames": 1, "stage_a_skeleton_path": "x"})
    monkeypatch.setattr(pipeline, "run_stage2_reproduce", lambda *a, **kw: {"run": fake_run, "brief": []})
    monkeypatch.setattr(pipeline, "build_forensic_report", lambda *a, **kw: str(tmp_path / "report.docx"))
    called = []
    monkeypatch.setattr(pipeline, "load_and_verify", lambda *a, **kw: called.append(1))
    monkeypatch.setattr(sys, "argv", ["run_full_pipeline.py", "https://www.youtube.com/watch?v=h4biGNiYJTQ",
                                      "--work-dir", str(tmp_path), "--skip-bridge"])
    pipeline.main()   # must not raise SystemExit
    assert not called   # the bridge must never be invoked when --skip-bridge is set
