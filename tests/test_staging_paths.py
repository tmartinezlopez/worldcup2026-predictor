from datetime import UTC, datetime

from src.staging import paths


def test_ensure_staging_dirs_creates_import_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        paths, "STAGING_ROOT", tmp_path / "data" / "staging" / "imports"
    )

    root = paths.ensure_staging_dirs()

    assert root.is_dir()
    assert root == tmp_path / "data" / "staging" / "imports"


def test_make_import_run_dir_creates_timestamped_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "STAGING_ROOT", tmp_path / "imports")

    run_dir = paths.make_import_run_dir(
        "Smoke Source", timestamp=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    )

    assert run_dir.is_dir()
    assert run_dir.parent.name == "smoke_source"
    assert run_dir.name == "20260102T030405Z"
