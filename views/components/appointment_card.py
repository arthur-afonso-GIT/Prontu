"""
Card de Consulta — bloco visual representando um compromisso no calendário.

Mostra horário, nome do paciente e cor opcional do convênio, conforme
especificado no projeto. Usado dentro das colunas de dia do calendário
(modos Diário/Semanal) e nas células do modo Mensal.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from database.models import Consulta, StatusConsultaEnum
from styles.design_tokens import Colors, Radius, Spacing

_STATUS_COLORS: dict[StatusConsultaEnum, str] = {
    StatusConsultaEnum.AGENDADA: Colors.ACCENT,
    StatusConsultaEnum.CONFIRMADA: Colors.SUCCESS,
    StatusConsultaEnum.EM_ANDAMENTO: Colors.WARNING,
    StatusConsultaEnum.CONCLUIDA: Colors.TEXT_TERTIARY,
    StatusConsultaEnum.CANCELADA: Colors.DANGER,
    StatusConsultaEnum.FALTOU: Colors.HIGHLIGHT,
}


class AppointmentCard(QWidget):
    """Bloco visual clicável representando uma consulta agendada."""

    clicked = Signal(int)  # consulta_id

    def __init__(self, consulta: Consulta, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._consulta_id = consulta.id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        cor = _STATUS_COLORS.get(consulta.status, Colors.ACCENT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(2)

        horario_label = QLabel(consulta.horario)
        horario_label.setStyleSheet(f"font-weight: 700; color: {cor};")

        nome_paciente = consulta.paciente.nome if consulta.paciente else "Paciente"
        nome_label = QLabel(nome_paciente)
        nome_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        nome_label.setWordWrap(True)

        layout.addWidget(horario_label)
        layout.addWidget(nome_label)

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {cor}18;
                border-left: 3px solid {cor};
                border-radius: {Radius.SM}px;
            }}
            """
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802 - nome exigido pelo Qt
        self.clicked.emit(self._consulta_id)
        super().mousePressEvent(event)
