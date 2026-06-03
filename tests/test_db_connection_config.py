from src.db.connection import get_database_url, get_engine


def test_database_url_reads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    assert get_database_url() == "sqlite:///:memory:"


def test_get_engine_builds_sqlite_engine():
    engine = get_engine("sqlite:///:memory:")

    assert engine is not None
    assert str(engine.url) == "sqlite:///:memory:"
