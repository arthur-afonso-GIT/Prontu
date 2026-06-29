"""Modal de criação/edição de Pasta de organização."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from styles.design_tokens import Colors
from views.components.base_modal import BaseModal
from views.components.buttons import primary_button, secondary_button


class FolderModal(BaseModal):
    """Modal para criar uma nova pasta ou renomear/recolorir uma existente."""

    def __init__(
        self,
        parent: QWidget | None = None,
        nome_inicial: str = "",
        cor_inicial: str = Colors.FOLDER_PALETTE[0],
    ) -> None:
        super().__init__(title="Nova Pasta" if not nome_inicial else "Editar Pasta", parent=parent)

        self._nome_input = QLineEdit(nome_inicial)
        self._nome_input.setPlaceholderText("Nome da pasta")
        self.content_layout.addWidget(self._nome_input)

        self._cor_selecionada = cor_inicial
        cor_layout = QHBoxLayout()
        self._color_buttons: list[QWidget] = []

        for cor in Colors.FOLDER_PALETTE:
            swatch = self._build_color_swatch(cor)
            cor_layout.addWidget(swatch)
            self._color_buttons.append(swatch)

        self.content_layout.addLayout(cor_layout)

        actions_layout = QHBoxLayout()
        cancel_button = secondary_button("Cancelar")
        cancel_button.clicked.connect(self.reject)

        save_button = primary_button("Salvar")
        save_button.clicked.connect(self.accept)

        actions_layout.addStretch()
        actions_layout.addWidget(cancel_button)
        actions_layout.addWidget(save_button)
        self.content_layout.addLayout(actions_layout)

    def _build_color_swatch(self, cor: str):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QPushButton

        swatch = QPushButton()
        swatch.setFixedSize(28, 28)
        swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        swatch.setStyleSheet(
            f"background-color: {cor}; border-radius: 14px; border: 2px solid "
            f"{'#1A2233' if cor == self._cor_selecionada else 'transparent'};"
        )
        swatch.clicked.connect(lambda: self._select_color(cor))
        return swatch

    def _select_color(self, cor: str) -> None:
        self._cor_selecionada = cor
        for swatch, cor_swatch in zip(self._color_buttons, Colors.FOLDER_PALETTE):
            borda = "#1A2233" if cor_swatch == cor else "transparent"
            swatch.setStyleSheet(
                f"background-color: {cor_swatch}; border-radius: 14px; border: 2px solid {borda};"
            )

    def get_values(self) -> tuple[str, str]:
        """Retorna (nome, cor) escolhidos pelo usuário."""
        return self._nome_input.text().strip(), self._cor_selecionada
