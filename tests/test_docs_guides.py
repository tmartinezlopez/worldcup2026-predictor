from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_guides_exist():
    expected_files = [
        "docs/guides/CODEX_CONTEXT.md",
        "docs/guides/ARCHITECTURE_RULES.md",
        "docs/guides/DATA_PIPELINE_RULES.md",
        "docs/guides/DB_RULES.md",
        "docs/guides/DEVELOPMENT_WORKFLOW.md",
        "docs/guides/PHASE_ROADMAP.md",
    ]

    for relative_path in expected_files:
        assert (ROOT / relative_path).is_file()
