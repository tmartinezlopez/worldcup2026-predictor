from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_directories_exist():
    expected_dirs = [
        "config",
        "docs",
        "data/staging",
        "data/raw/sample",
        "data/processed",
        "logs",
        "src/db",
        "src/ingestion",
        "src/identity",
        "src/features",
        "src/models",
        "src/prediction",
        "src/simulation",
        "src/evaluation",
        "src/orchestration",
        "src/utils",
        "tests",
        "scripts",
    ]

    for relative_path in expected_dirs:
        assert (ROOT / relative_path).is_dir()


def test_required_files_exist():
    expected_files = [
        ".env.example",
        "docker-compose.yml",
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "config/app.yaml",
        "config/batches.yaml",
        "config/feature_config.yaml",
        "config/model_config.yaml",
        "config/simulation_config.yaml",
        "config/source_config.yaml",
        "docs/MASTER_DOCUMENT.md",
        "docs/DECISIONS.md",
        "docs/RUNBOOK.md",
        "scripts/setup_dev.sh",
        "scripts/start_db.sh",
        "scripts/stop_db.sh",
        "scripts/reset_db.sh",
        "scripts/check.sh",
        "scripts/run_batch.sh",
        "scripts/init_db.sh",
        "scripts/db_healthcheck.sh",
        "src/db/base.py",
        "src/db/connection.py",
        "src/db/models.py",
        "src/db/init_db.py",
        "src/db/drop_db.py",
        "src/db/healthcheck.py",
        "src/identity/normalizers.py",
        "src/identity/matching.py",
        "src/identity/team_identity.py",
        "src/identity/player_identity.py",
        "src/identity/generic_identity.py",
        "tests/test_identity_normalizers.py",
        "tests/test_identity_matching.py",
        "tests/test_team_identity.py",
        "tests/test_player_identity.py",
    ]

    for relative_path in expected_files:
        assert (ROOT / relative_path).is_file()
