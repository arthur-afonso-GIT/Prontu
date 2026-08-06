import logging
from datetime import datetime, timezone
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


def test_recent_events_keep_only_technical_markers(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = diagnostics.log_file_path()
    path.parent.mkdir(parents=True)
    path.write_text(
        "2026-08-05 10:00:00 | ERROR | MainThread | "
        "paciente=MARIA DA SILVA telefone=81999998888 "
        "RemoteProtocolError HTTP 503 PGRST202\n",
        encoding="utf-8",
    )

    events = diagnostics.recent_technical_events()

    assert len(events) == 1
    assert "RemoteProtocolError" in events[0]
    assert "HTTP 503" in events[0]
    assert "PGRST202" in events[0]
    assert "MARIA" not in events[0]
    assert "81999998888" not in events[0]


def test_export_support_diagnostic_has_environment_but_no_clinical_data(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    destination = tmp_path / "diagnostico.txt"

    result = diagnostics.export_support_diagnostic(
        destination,
        version="2.5.0",
        secure_storage_backend="keyring",
        connectivity={"internet": "Disponível", "supabase": "Disponível"},
        screens=[{"width": 1366, "height": 768, "scale": 1.25, "dpi": 120}],
        technical_events=["2026-08-05 10:00:00 | ERROR | RemoteProtocolError"],
        generated_at=datetime(2026, 8, 5, 12, 30, tzinfo=timezone.utc),
    )

    content = result.read_text(encoding="utf-8-sig")
    assert "Versão do Prontu: 2.5.0" in content
    assert "Tela 1: 1366x768" in content
    assert "Supabase: Disponível" in content
    assert "Cofre de credenciais do sistema" in content
    assert "pacientes, fichas, anexos" in content
    assert "access_token" not in content


def test_connectivity_does_not_query_clinic_tables(monkeypatch):
    calls = []

    class Response:
        status_code = 200

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(diagnostics.httpx, "get", fake_get)

    result = diagnostics.check_connectivity(
        "https://example.supabase.co", "public-key", timeout=1
    )

    assert result == {"internet": "Disponível", "supabase": "Disponível"}
    assert calls[0][0] == "https://example.supabase.co/auth/v1/health"
    assert "/rest/v1/" not in calls[0][0]
