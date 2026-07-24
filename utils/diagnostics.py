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
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import Callable


LOGGER_NAME = "prontu"
MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5

_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(access_token|refresh_token|authorization|apikey|api_key|senha)"
    r"\b(\s*[:=]\s*)([^\s,;}\]]+)"
)
_BEARER_VALUE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


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
