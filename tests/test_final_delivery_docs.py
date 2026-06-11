from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_final_delivery_doc_exists():
    assert (ROOT / "docs/FINAL_DELIVERY.md").is_file()


def test_readme_contains_final_validation():
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Final validation" in content
    assert "final_release_check.sh" in content


def test_validation_checklist_contains_release_commands():
    content = (ROOT / "docs/VALIDATION_CHECKLIST.md").read_text(encoding="utf-8")
    assert "final_release_check" in content
    assert "dashboard/GROUP_STAGE_MD1/index.html" in content
    assert "final_reports/GROUP_STAGE_MD1/batch_report.html" in content


def test_submission_contains_real_vs_demo_section():
    content = (ROOT / "docs/SUBMISSION.md").read_text(encoding="utf-8")
    assert "## What Is Real vs Demo" in content


def test_project_status_contains_phase_28a():
    content = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "Completed through Phase 28A." in content
