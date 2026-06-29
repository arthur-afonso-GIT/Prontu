"""
Componente Uploader (drag-and-drop de arquivos PDF/DOCX).

Usado na tela de Fichas Dinâmicas para que o profissional importe um
modelo de ficha médica arrastando o arquivo ou clicando para selecionar
através do diálogo nativo do sistema operacional.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QVBoxLayout, QWidget

from styles.design_tokens import Colors, Radius, Spacing


class FileUploader(QFrame):
    """Área de upload por arrastar-e-soltar ou clique, restrita a PDF/DOCX.

    Emite `file_selected(caminho_absoluto)` quando um arquivo válido é
    escolhido por qualquer um dos dois métodos.
    """

    file_selected = Signal(str)

    ACCEPTED_EXTENSIONS = {".pdf", ".docx"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self._set_idle_style()

        layout = QVBoxLayout(self)
        layout.setAlignment(layout.alignment())
        layout.setSpacing(Spacing.SM)

        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(layout.alignment())

        self._main_label = QLabel("Arraste um arquivo PDF ou DOCX aqui")
        self._main_label.setObjectName("sectionTitle")

        hint_label = QLabel("ou clique para selecionar do computador")
        hint_label.setObjectName("mutedText")

        for widget in (icon_label, self._main_label, hint_label):
            widget.setAlignment(widget.alignment() | self._center_alignment())
            layout.addWidget(widget)

        self.mousePressEvent = self._on_click  # type: ignore[method-assign]

    @staticmethod
    def _center_alignment():
        from PySide6.QtCore import Qt
        return Qt.AlignmentFlag.AlignCenter

    def _set_idle_style(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 2px dashed {Colors.BORDER_STRONG};
                border-radius: {Radius.LG}px;
            }}
            """
        )

    def _set_active_style(self) -> None:
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {Colors.ACCENT_SOFT};
                border: 2px dashed {Colors.ACCENT};
                border-radius: {Radius.LG}px;
            }}
            """
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and self._has_valid_extension(event.mimeData().urls()):
            self._set_active_style()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._set_idle_style()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_idle_style()
        urls = event.mimeData().urls()
        if self._has_valid_extension(urls):
            caminho = urls[0].toLocalFile()
            self.file_selected.emit(caminho)

    def _on_click(self, event) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar ficha médica", "", "Documentos (*.pdf *.docx)"
        )
        if caminho:
            self.file_selected.emit(caminho)

    def _has_valid_extension(self, urls) -> bool:
        if not urls:
            return False
        extensao = Path(urls[0].toLocalFile()).suffix.lower()
        return extensao in self.ACCEPTED_EXTENSIONS
