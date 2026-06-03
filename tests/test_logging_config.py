import logging

from src.utils.logging_config import setup_logging


def test_setup_logging_creates_logs_and_writes_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    logger = setup_logging()
    logger.info("test log message")

    logs_dir = tmp_path / "logs"
    log_file = logs_dir / "pipeline.log"

    assert logs_dir.is_dir()
    assert log_file.is_file()
    assert "test log message" in log_file.read_text(encoding="utf-8")

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
