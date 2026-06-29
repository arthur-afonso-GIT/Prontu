"""
Componente de campo de Telefone com botão WhatsApp integrado.

Implementa a regra obrigatória do projeto: ao lado do campo de
telefone, um botão que abre diretamente a conversa do WhatsApp com
aquele número (via `https://wa.me/55DDDNUMERO`), usando o navegador
padrão do sistema operacional.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from styles.design_tokens import Spacing
from utils.phone_utils import build_whatsapp_link, format_phone_display


class PhoneFieldWithWhatsApp(QWidget):
    """Campo de entrada de telefone com botão de atalho para o WhatsApp.

    O botão é automaticamente habilitado/desabilitado conforme o
    telefone digitado forma (ou não) um número válido, evitando que o
    usuário tente abrir um link do WhatsApp com um número incompleto.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("(00) 00000-0000")
        self.input_field.textChanged.connect(self._on_text_changed)

        self.whatsapp_button = QPushButton("💬", self)
        self.whatsapp_button.setObjectName("whatsappButton")
        self.whatsapp_button.setFixedSize(36, 36)
        self.whatsapp_button.setToolTip("Abrir conversa no WhatsApp")
        self.whatsapp_button.setEnabled(False)
        self.whatsapp_button.clicked.connect(self._open_whatsapp)

        layout.addWidget(self.input_field)
        layout.addWidget(self.whatsapp_button)

    def _on_text_changed(self, texto: str) -> None:
        link = build_whatsapp_link(texto)
        self.whatsapp_button.setEnabled(link is not None)

    def _open_whatsapp(self) -> None:
        link = build_whatsapp_link(self.input_field.text())
        if link:
            QDesktopServices.openUrl(QUrl(link))

    def get_value(self) -> str:
        """Retorna o telefone bruto digitado pelo usuário."""
        return self.input_field.text()

    def set_value(self, raw_phone: str | None) -> None:
        """Define o valor do campo, aplicando formatação de exibição."""
        if raw_phone:
            self.input_field.setText(format_phone_display(raw_phone))
        else:
            self.input_field.clear()
