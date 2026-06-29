"""
Componente Sidebar (menu lateral de navegação).

Implementa o menu lateral fixo contendo: Home, Calendário, Pacientes,
Fichas Dinâmicas, Configurações — conforme especificado no projeto.
Emite o sinal `navigation_requested` quando um item é clicado, que a
`MainWindow` escuta para trocar a tela ativa no `QStackedWidget`
central, mantendo a Sidebar totalmente desacoplada da lógica de
roteamento entre telas.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QLabel, QPushButton, QVBoxLayout, QWidget

from config import config


class Sidebar(QWidget):
    """Menu lateral fixo com os itens de navegação principal da aplicação."""

    navigation_requested = Signal(str)  # emite o identificador da rota (ex: "home")

    NAV_ITEMS: list[tuple[str, str]] = [
        ("home", "🏠  Home"),
        ("calendar", "📅  Calendário"),
        ("patients", "👥  Pacientes"),
        ("dynamic_forms", "📋  Fichas Dinâmicas"),
        ("settings", "⚙️  Configurações"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(config.SIDEBAR_WIDTH)

        self._buttons: dict[str, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(4)

        brand_label = QLabel(config.APP_NAME)
        brand_label.setObjectName("sidebarBrand")
        layout.addWidget(brand_label)
        layout.addSpacing(24)

        for route_id, label in self.NAV_ITEMS:
            button = QPushButton(label)
            button.setObjectName("sidebarItem")
            button.setCheckable(True)
            button.setFlat(True)
            button.clicked.connect(lambda checked, r=route_id: self._on_item_clicked(r))

            self._button_group.addButton(button)
            self._buttons[route_id] = button
            layout.addWidget(button)

        layout.addStretch()

        version_label = QLabel(f"v{config.APP_VERSION}")
        version_label.setObjectName("sidebarVersion")
        layout.addWidget(version_label)

    def _on_item_clicked(self, route_id: str) -> None:
        self.navigation_requested.emit(route_id)

    def set_active_route(self, route_id: str) -> None:
        """Marca visualmente qual item do menu está ativo (sincronizado pela MainWindow)."""
        button = self._buttons.get(route_id)
        if button:
            button.setChecked(True)
