"""Diagnóstico local do Prontu.

Os arquivos ficam fora da pasta de instalação para sobreviver a atualizações.
O conteúdo é limitado a eventos técnicos e exceções; tokens e senhas não são
registrados por este módulo.
"""
from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import Callable, Iterable, Mapping, Sequence

import httpx


LOGGER_NAME = "prontu"
MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5

_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(access_token|refresh_token|authorization|apikey|api_key|senha)"
    r"\b(\s*[:=]\s*)([^\s,;}\]]+)"
)
_BEARER_VALUE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_TECHNICAL_EXCEPTION = re.compile(
    r"\b(?:[A-Za-z_][\w.]*)(?:Error|Exception)\b"
)
_HTTP_STATUS = re.compile(r"(?i)\bHTTP\s+[1-5]\d{2}\b")
_SUPABASE_CODE = re.compile(
    r"\b(?:PGRST\d{3}|(?=[0-9A-Z]{5}\b)(?=[0-9A-Z]*\d)[0-9A-Z]{5})\b"
)
_LOG_EVENT = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r"\s*\|\s*(?P<level>WARNING|ERROR|CRITICAL)\s*\|.*?\|\s*(?P<message>.*)$"
)


def app_data_dir() -> Path:
    """Retorna a pasta persistente do usuário atual."""
    base = os.getenv("LOCALAPPDATA")
    if not base:
        base = (
            str(Path.home() / "AppData" / "Local")
            if sys.platform == "win32"
            else str(Path.home() / ".local" / "share")
        )
    return Path(base) / "Prontu"


def log_file_path() -> Path:
    return app_data_dir() / "logs" / "prontu.log"


def _human_bytes(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"


def _check_directory_writeable(directory: Path) -> tuple[bool, str]:
    """Testa escrita sem manter qualquer arquivo do teste."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, delete=True):
            pass
        return True, "Disponível"
    except OSError as exc:
        return False, f"Indisponível ({type(exc).__name__})"


def check_connectivity(
    supabase_url: str | None,
    supabase_key: str | None,
    *,
    timeout: float = 4.0,
) -> dict[str, str]:
    """Verifica conectividade sem consultar tabelas ou dados da clínica."""
    result = {"internet": "Indisponível", "supabase": "Indisponível"}
    url = str(supabase_url or "").strip().rstrip("/")
    key = str(supabase_key or "").strip()

    if url:
        try:
            headers = {"apikey": key} if key else {}
            response = httpx.get(
                f"{url}/auth/v1/health",
                headers=headers,
                timeout=timeout,
                follow_redirects=False,
            )
            result["internet"] = "Disponível"
            result["supabase"] = (
                "Disponível"
                if response.status_code < 500
                else f"Instável (HTTP {response.status_code})"
            )
            return result
        except httpx.HTTPError:
            pass

    try:
        response = httpx.get(
            "https://www.google.com/generate_204",
            timeout=min(timeout, 3.0),
            follow_redirects=False,
        )
        if response.status_code < 500:
            result["internet"] = "Disponível"
    except httpx.HTTPError:
        pass
    return result


def _summarize_technical_event(line: str) -> str | None:
    """Resume um log sem copiar sua mensagem, protegendo dados clínicos."""
    match = _LOG_EVENT.match(line.strip())
    if not match:
        return None
    message = match.group("message")
    markers: list[str] = []
    for pattern in (_TECHNICAL_EXCEPTION, _HTTP_STATUS, _SUPABASE_CODE):
        for value in pattern.findall(message):
            marker = str(value)
            if marker not in markers:
                markers.append(marker)
    detail = ", ".join(markers[:4]) or "sem código técnico"
    return f"{match.group('date')} | {match.group('level')} | {detail}"


def recent_technical_events(limit: int = 20) -> list[str]:
    """Lista somente metadados técnicos de incidentes recentes."""
    path = log_file_path()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    events = [
        summary
        for line in lines
        if (summary := _summarize_technical_event(line)) is not None
    ]
    return events[-max(1, int(limit)) :]


def build_support_diagnostic(
    *,
    version: str,
    secure_storage_backend: str,
    connectivity: Mapping[str, str],
    screens: Sequence[Mapping[str, object]] = (),
    technical_events: Iterable[str] | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Monta um relatório técnico sem dados pessoais, clínicos ou credenciais."""
    now = generated_at or datetime.now().astimezone()
    data_dir = app_data_dir()
    writeable, writeable_text = _check_directory_writeable(data_dir)
    try:
        disk = shutil.disk_usage(data_dir)
        disk_free = _human_bytes(disk.free)
    except OSError:
        disk_free = "Não foi possível verificar"

    backend_labels = {
        "keyring": "Cofre de credenciais do sistema",
        "dpapi_file": "Arquivo protegido pelo Windows",
        "restricted_file": "Armazenamento local restrito",
    }
    screen_lines = []
    for index, screen in enumerate(screens, start=1):
        width = int(screen.get("width") or 0)
        height = int(screen.get("height") or 0)
        scale = float(screen.get("scale") or 1.0)
        dpi = float(screen.get("dpi") or 0.0)
        screen_lines.append(
            f"- Tela {index}: {width}x{height}; escala {scale:.2f}x; DPI {dpi:.0f}"
        )
    if not screen_lines:
        screen_lines.append("- Nenhuma tela foi identificada")

    events = list(technical_events if technical_events is not None else recent_technical_events())
    event_lines = [f"- {event}" for event in events]
    if not event_lines:
        event_lines.append("- Nenhum erro técnico recente registrado")

    return "\n".join(
        [
            "PRONTU - DIAGNÓSTICO PARA SUPORTE",
            "",
            "Este arquivo contém somente informações técnicas do aplicativo e do computador.",
            "Não contém senhas, tokens, chaves de ativação, pacientes, fichas, anexos ou dados financeiros.",
            "",
            "IDENTIFICAÇÃO",
            f"- Gerado em: {now.strftime('%d/%m/%Y %H:%M:%S %z')}",
            f"- Versão do Prontu: {version or 'desconhecida'}",
            f"- Aplicativo empacotado: {'Sim' if getattr(sys, 'frozen', False) else 'Não'}",
            "",
            "SISTEMA",
            f"- Sistema operacional: {platform.system()} {platform.release()}",
            f"- Arquitetura: {platform.machine() or 'não identificada'}",
            f"- Python: {platform.python_version()}",
            f"- Espaço livre no disco do aplicativo: {disk_free}",
            f"- Pasta local gravável: {'Sim' if writeable else 'Não'} ({writeable_text})",
            f"- Sessão protegida por: {backend_labels.get(secure_storage_backend, 'Não identificado')}",
            "",
            "TELAS",
            *screen_lines,
            "",
            "CONECTIVIDADE",
            f"- Internet: {connectivity.get('internet', 'Não verificada')}",
            f"- Supabase: {connectivity.get('supabase', 'Não verificado')}",
            "",
            "EVENTOS TÉCNICOS RECENTES",
            *event_lines,
            "",
        ]
    )


def export_support_diagnostic(destination: str | Path, **report_data) -> Path:
    """Gera um arquivo UTF-8 pronto para o usuário encaminhar ao suporte."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_support_diagnostic(**report_data),
        encoding="utf-8-sig",
        newline="\n",
    )
    return path


class _SensitiveDataFilter(logging.Filter):
    """Reduz o risco de um segredo aparecer por acidente no diagnóstico."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        sanitized = _BEARER_VALUE.sub("Bearer [PROTEGIDO]", message)
        sanitized = _SENSITIVE_VALUE.sub(r"\1\2[PROTEGIDO]", sanitized)
        record.msg = sanitized
        record.args = ()
        return True


def configure_diagnostics(version: str = "desconhecida") -> logging.Logger:
    """Configura log rotativo e captura exceções não tratadas."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(getattr(handler, "_prontu_handler", False) for handler in logger.handlers):
        path = log_file_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                path,
                maxBytes=MAX_LOG_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler._prontu_handler = True  # type: ignore[attr-defined]
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            handler.addFilter(_SensitiveDataFilter())
            logger.addHandler(handler)
        except OSError:
            # O diagnóstico nunca deve impedir a abertura do aplicativo.
            logger.addHandler(logging.NullHandler())

    _install_exception_hooks(logger)
    logger.info(
        "Prontu iniciado | versão=%s | sistema=%s | python=%s | empacotado=%s",
        version,
        platform.platform(),
        platform.python_version(),
        bool(getattr(sys, "frozen", False)),
    )
    return logger


def _install_exception_hooks(logger: logging.Logger) -> None:
    previous_sys_hook = sys.excepthook

    if not getattr(previous_sys_hook, "_prontu_hook", False):

        def report_exception(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_traceback: TracebackType | None,
        ) -> None:
            if issubclass(exc_type, KeyboardInterrupt):
                previous_sys_hook(exc_type, exc_value, exc_traceback)
                return
            logger.critical(
                "Exceção não tratada",
                exc_info=(exc_type, exc_value, exc_traceback),
            )

        report_exception._prontu_hook = True  # type: ignore[attr-defined]
        sys.excepthook = report_exception

    previous_thread_hook: Callable | None = getattr(threading, "excepthook", None)
    if previous_thread_hook and not getattr(previous_thread_hook, "_prontu_hook", False):

        def report_thread_exception(args: threading.ExceptHookArgs) -> None:
            if args.exc_type is SystemExit:
                return
            logger.critical(
                "Exceção não tratada em thread %s",
                getattr(args.thread, "name", "desconhecida"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        report_thread_exception._prontu_hook = True  # type: ignore[attr-defined]
        threading.excepthook = report_thread_exception


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
