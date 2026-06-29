"""
Barra de Pastas (organização visual estilo Notion).

Exibe as pastas cadastradas como "pills" horizontais coloridas, com
ação de clique para filtrar pacientes por pasta e um botão "+ Nova
pasta" ao final. Reordenação é feita por drag-and-drop entre pills.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QWidget

from database.models import Pasta
from styles.design_tokens import Radius, Spacing


class FolderPill(QPushButton):
    """Um botão estilizado como "pill" representando uma pasta."""

    rename_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, pasta: Pasta, parent: QWidget | None = None) -> None:
        super().__init__(f"📁 {pasta.nome}", parent)
        self.pasta_id = pasta.id
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {pasta.cor}22;
                color: {pasta.cor};
                border: 1px solid {pasta.cor}55;
                border-radius: {Radius.FULL}px;
                padding: {Spacing.XS + 2}px {Spacing.MD}px;
                font-weight: 600;
            }}
            QPushButton:checked {{
                background-color: {pasta.cor};
                color: white;
            }}
            """
        )

    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        renomear_action = menu.addAction("Renomear")
        excluir_action = menu.addAction("Excluir")

        action = menu.exec(self.mapToGlobal(position))
        if action == renomear_action:
            self.rename_requested.emit(self.pasta_id)
        elif action == excluir_action:
            self.delete_requested.emit(self.pasta_id)


class FolderBar(QWidget):
    """Barra horizontal com as pastas cadastradas e botão de criar nova pasta."""

    folder_selected = Signal(object)  # int (pasta_id) ou None (limpar filtro)
    new_folder_requested = Signal()
    rename_folder_requested = Signal(int)
    delete_folder_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(52)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFixedHeight(52)
        scroll_area.setFrameShape(scroll_area.Shape.NoFrame)
        scroll_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll_area.viewport().setAutoFillBackground(False)
        scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll_area.viewport().setStyleSheet("background: transparent;")

        self._pills_container = QWidget()
        self._pills_container.setAutoFillBackground(False)
        self._pills_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._pills_container.setStyleSheet("background: transparent;")
        self._pills_layout = QHBoxLayout(self._pills_container)
        self._pills_layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        self._pills_layout.setSpacing(Spacing.SM)

        scroll_area.setWidget(self._pills_container)
        outer_layout.addWidget(scroll_area)

        new_folder_button = QPushButton("+ Nova pasta")
        new_folder_button.setObjectName("ghostButton")
        new_folder_button.clicked.connect(self.new_folder_requested.emit)
        outer_layout.addWidget(new_folder_button)

        self._pills: list[FolderPill] = []
        self._dynamic_widgets: list[QWidget] = []

    def set_folders(self, pastas: list[Pasta]) -> None:
        """Reconstrói as pills a partir da lista atual de pastas."""
        for widget in self._dynamic_widgets:
            self._pills_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._pills.clear()
        self._dynamic_widgets.clear()

        if not pastas:
            empty_label = QLabel("Nenhuma pasta criada ainda.")
            empty_label.setObjectName("mutedText")
            self._pills_layout.addWidget(empty_label)
            self._dynamic_widgets.append(empty_label)
            return

        for pasta in pastas:
            pill = FolderPill(pasta)
            pill.clicked.connect(lambda checked, p=pasta.id: self._on_pill_clicked(p, checked))
            pill.rename_requested.connect(self.rename_folder_requested.emit)
            pill.delete_requested.connect(self.delete_folder_requested.emit)
            self._pills_layout.addWidget(pill)
            self._pills.append(pill)
            self._dynamic_widgets.append(pill)

        self._clear_trailing_stretch()
        self._pills_layout.addStretch()

    def _clear_trailing_stretch(self) -> None:
        """Remove o stretch final adicionado por uma chamada anterior de `set_folders`.

        Sem isso, múltiplas chamadas acumulariam vários `QSpacerItem` no
        layout (cada um sobrevivendo indefinidamente, já que spacers não
        são widgets e não respondem a `deleteLater`), distorcendo
        progressivamente o espaçamento horizontal das pills.
        """
        last_item = self._pills_layout.itemAt(self._pills_layout.count() - 1)
        if last_item is not None and last_item.widget() is None:
            self._pills_layout.removeItem(last_item)

    def _on_pill_clicked(self, pasta_id: int, checked: bool) -> None:
        for pill in self._pills:
            if pill.pasta_id != pasta_id:
                pill.setChecked(False)
        self.folder_selected.emit(pasta_id if checked else None)
