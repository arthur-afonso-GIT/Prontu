"""
Configuração centralizada de logging.

Por que centralizar:
    Sem isso, cada módulo configuraria handlers de forma independente,
    gerando duplicação de mensagens e arquivos de log inconsistentes.
    Esta função garante que toda a aplicação escreva no mesmo arquivo,
    com o mesmo formato, e que módulos individuais só precisem chamar
    `get_logger(__name__)`.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import config

_CONFIGURED = False


def _configure_root_logger() -> None:
    """Configura o logger raiz uma única vez por processo."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_file = config.logs_dir() / "clinic_manager.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado, garantindo configuração prévia.

    Args:
        name: Geralmente `__name__` do módulo chamador.

    Returns:
        Instância de `logging.Logger` configurada.
    """
    _configure_root_logger()
    return logging.getLogger(name)
