"""
Factory de botões padronizados.

Em vez de cada tela construir um `QPushButton` e setar manualmente
`setObjectName` + ícone + cursor, este módulo centraliza a criação dos
4 estilos de botão usados na aplicação (primário, secundário/padrão,
perigo, fantasma), garantindo que todos tenham o cursor de mão e
comportamento consistentes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget


def _build_button(text: str, object_name: str | None, parent: QWidget | None) -> QPushButton:
    button = QPushButton(text, parent)
    if object_name:
        button.setObjectName(object_name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def primary_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """Botão de ação principal da tela (ex: "+ Adicionar Paciente")."""
    return _build_button(text, "primaryButton", parent)


def secondary_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """Botão de ação secundária (estilo padrão, com borda)."""
    return _build_button(text, None, parent)


def danger_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """Botão de ação destrutiva (ex: "Excluir")."""
    return _build_button(text, "dangerButton", parent)


def ghost_button(text: str, parent: QWidget | None = None) -> QPushButton:
    """Botão discreto, sem fundo nem borda (ex: ações dentro de uma tabela)."""
    return _build_button(text, "ghostButton", parent)
