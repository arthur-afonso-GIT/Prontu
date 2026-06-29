"""
View de Configurações.

Tela simples contendo informações sobre a instalação (versão, caminho
do banco de dados) e ações básicas de manutenção, como abrir a pasta
de dados ou de logs no explorador de arquivos do sistema.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from config import config
from styles.design_tokens import Spacing
from views.components.buttons import secondary_button
from views.components.card import Card


class SettingsView(QWidget):
    """Tela de configurações e informações sobre a instalação."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        title = QLabel("Configurações")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        info_card = Card(self)
        section_title = QLabel("Sobre a instalação")
        section_title.setObjectName("sectionTitle")
        info_card.add_widget(section_title)

        form_layout = QFormLayout()
        form_layout.addRow("Versão", QLabel(config.APP_VERSION))
        form_layout.addRow("Banco de dados", QLabel(str(config.database_path())))
        form_layout.addRow("Logs", QLabel(str(config.logs_dir())))
        form_layout.addRow("Documentos importados", QLabel(str(config.uploads_dir())))
        info_card.body_layout.addLayout(form_layout)

        open_data_folder_button = secondary_button("Abrir pasta de dados")
        open_data_folder_button.clicked.connect(self._open_data_folder)
        info_card.add_widget(open_data_folder_button)

        layout.addWidget(info_card)
        layout.addStretch()

    def _open_data_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.user_data_dir())))
