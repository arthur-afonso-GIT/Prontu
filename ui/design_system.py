"""Identidade visual compartilhada do Prontu.

As telas continuam em PySide6 Widgets, mas passam a receber uma base visual
única. Estilos locais ficam reservados apenas para exceções de contexto.
"""
from __future__ import annotations

from pathlib import Path


def instalar_design_system(app) -> None:
    """Aplica uma única vez a base visual a toda a aplicação."""
    if getattr(app, "_prontu_design_system", False):
        return

    caminho = Path(__file__).with_name("styles.qss")
    app.setStyleSheet(caminho.read_text(encoding="utf-8"))
    app._prontu_design_system = True


def definir_variante(widget, variante: str) -> None:
    """Aplica uma variante sem duplicar QSS em cada botão."""
    widget.setProperty("variant", variante)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
