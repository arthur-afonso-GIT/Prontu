import logging
from pathlib import Path

from utils import diagnostics


def _reset_logger():
    logger = logging.getLogger(diagnostics.LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    return logger


def test_diagnostic_log_is_persistent_and_sanitizes_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    logger = _reset_logger()

    diagnostics.configure_diagnostics("9.9.9")
    logger.error("access_token=segredo senha:123456 Authorization=Bearer token-secreto")
    for handler in logger.handlers:
        handler.flush()

    log_path = Path(tmp_path) / "Prontu" / "logs" / "prontu.log"
    content = log_path.read_text(encoding="utf-8")
    assert "versão=9.9.9" in content
    assert "segredo" not in content
    assert "123456" not in content
    assert "token-secreto" not in content
    assert content.count("[PROTEGIDO]") >= 2

    _reset_logger()


def test_app_data_dir_uses_local_app_data(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert diagnostics.app_data_dir() == Path(tmp_path) / "Prontu"
