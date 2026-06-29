"""
Componente Modal (Dialog) base.

Fornece um `QDialog` pré-estilizado com cabeçalho padronizado (título +
botão de fechar) e área de conteúdo livre, usado como base para todos
os modais da aplicação (confirmação de exclusão, formulário de
nova pasta, revisão de campos importados, etc.).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from styles.design_tokens import Spacing
from styles.shadow import apply_card_shadow


class BaseModal(QDialog):
    """Modal base com cabeçalho padronizado, usado como classe-pai de modais específicos.

    Args:
        title: Título exibido no cabeçalho do modal.
        parent: Widget pai (geralmente a janela principal).
        min_width: Largura mínima do modal.
    """

    def __init__(self, title: str, parent: QWidget | None = None, min_width: int = 420) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(min_width)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget(self)
        self._container.setObjectName("card")
        apply_card_shadow(self._container, level="medium")
        outer_layout.addWidget(self._container)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.XL)
        container_layout.setSpacing(Spacing.MD)

        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")

        close_button = QPushButton("✕")
        close_button.setObjectName("ghostButton")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.reject)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button)

        container_layout.addLayout(header_layout)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(Spacing.MD)
        container_layout.addLayout(self.content_layout)
