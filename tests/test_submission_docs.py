from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_submission_docs_exist():
    assert (ROOT / "docs/SUBMISSION.md").is_file()
    assert (ROOT / "docs/VALIDATION_CHECKLIST.md").is_file()
    assert (ROOT / "docs/PROJECT_STATUS.md").is_file()


def test_readme_contains_quick_start():
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Quick start" in content


def test_runbook_contains_fast_path():
    content = (ROOT / "docs/RUNBOOK.md").read_text(encoding="utf-8")
    assert "## Fast path" in content


def test_show_final_artifacts_script_exists_and_avoids_staging_primary_focus():
    script_path = ROOT / "scripts/show_final_artifacts.sh"
    content = script_path.read_text(encoding="utf-8")

    assert script_path.is_file()
    assert "final_reports" in content
    assert "data/staging" not in content
