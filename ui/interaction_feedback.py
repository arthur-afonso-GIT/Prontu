"""Feedback visual e cursor para controles interativos do Prontu."""
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QTabBar


HOVER_STYLE = """
/* Controles acionáveis */
QToolButton:enabled:hover {
    background-color: #e0f2fe;
    border-color: #38bdf8;
}
QToolButton:enabled:pressed {
    background-color: #bae6fd;
}
QComboBox:hover, QAbstractSpinBox:hover {
    border-color: #38bdf8;
    background-color: #f8fdff;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {
    border-color: #7dd3fc;
}
QCheckBox:hover, QRadioButton:hover {
    color: #0369a1;
}
QTabBar::tab:hover {
    background: #e0f2fe;
    color: #0369a1;
}

/* Itens que representam uma seleção ou ação */
QTableWidget::item:hover, QTableView::item:hover,
QListWidget::item:hover, QListView::item:hover,
QTreeWidget::item:hover, QTreeView::item:hover {
    background-color: #eff6ff;
    color: #0369a1;
}
QHeaderView::section:hover {
    background-color: #f1f5f9;
    color: #0369a1;
}
QCalendarWidget QAbstractItemView::item:hover {
    background-color: #dbeafe;
    color: #0f172a;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}
QToolTip {
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 5px;
}
"""


class _CursorInterativo(QObject):
    """Mostra a mão somente onde o clique altera algo ou abre uma ação."""

    TIPOS_INTERATIVOS = (QAbstractButton, QComboBox, QAbstractSpinBox, QTabBar)

    def eventFilter(self, watched, event):
        if isinstance(watched, self.TIPOS_INTERATIVOS):
            if event.type() == QEvent.Type.Enter and watched.isEnabled():
                watched.setCursor(Qt.CursorShape.PointingHandCursor)
            elif event.type() == QEvent.Type.Leave:
                watched.unsetCursor()
        return False


def instalar_feedback_interativo(app) -> None:
    """Instala um único padrão para telas atuais e para controles criados depois."""
    if getattr(app, "_prontu_feedback_interativo", False):
        return
    app.setStyleSheet(f"{app.styleSheet()}\n{HOVER_STYLE}")
    filtro = _CursorInterativo(app)
    app.installEventFilter(filtro)
    # Mantém a referência para o filtro não ser coletado pelo Python.
    app._prontu_cursor_interativo = filtro
    app._prontu_feedback_interativo = True
