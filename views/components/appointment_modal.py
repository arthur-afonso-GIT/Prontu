"""Modal de criação de Consulta (agendamento)."""

from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QTimeEdit,
    QWidget,
)

from forms.patient_schemas import PacienteListItemSchema
from views.components.base_modal import BaseModal
from views.components.buttons import primary_button, secondary_button


class AppointmentModal(BaseModal):
    """Modal para agendar uma nova consulta, com seleção de paciente."""

    def __init__(
        self,
        pacientes_disponiveis: list[PacienteListItemSchema],
        parent: QWidget | None = None,
        data_inicial: date | None = None,
    ) -> None:
        super().__init__(title="Nova Consulta", parent=parent)

        form_layout = QFormLayout()

        self._paciente_combo = QComboBox()
        for paciente in pacientes_disponiveis:
            self._paciente_combo.addItem(paciente.nome, userData=paciente.id)

        self._data_input = QDateEdit()
        self._data_input.setCalendarPopup(True)
        if data_inicial:
            self._data_input.setDate(QDate(data_inicial.year, data_inicial.month, data_inicial.day))
        else:
            self._data_input.setDate(QDate.currentDate())

        self._horario_input = QTimeEdit()
        self._horario_input.setDisplayFormat("HH:mm")
        self._horario_input.setTime(QTime(9, 0))

        self._duracao_input = QSpinBox()
        self._duracao_input.setRange(10, 240)
        self._duracao_input.setSingleStep(10)
        self._duracao_input.setValue(30)
        self._duracao_input.setSuffix(" min")

        self._observacoes_input = QLineEdit()
        self._observacoes_input.setPlaceholderText("Observações (opcional)")

        form_layout.addRow("Paciente *", self._paciente_combo)
        form_layout.addRow("Data *", self._data_input)
        form_layout.addRow("Horário *", self._horario_input)
        form_layout.addRow("Duração", self._duracao_input)
        form_layout.addRow("Observações", self._observacoes_input)

        self.content_layout.addLayout(form_layout)

        actions_layout = QHBoxLayout()
        cancel_button = secondary_button("Cancelar")
        cancel_button.clicked.connect(self.reject)

        save_button = primary_button("Agendar")
        save_button.clicked.connect(self.accept)

        actions_layout.addStretch()
        actions_layout.addWidget(cancel_button)
        actions_layout.addWidget(save_button)
        self.content_layout.addLayout(actions_layout)

    def get_values(self) -> dict:
        """Retorna os valores preenchidos no modal, prontos para `AppointmentService`."""
        qdate = self._data_input.date()
        qtime = self._horario_input.time()

        return {
            "paciente_id": self._paciente_combo.currentData(),
            "data_consulta": date(qdate.year(), qdate.month(), qdate.day()),
            "horario": f"{qtime.hour():02d}:{qtime.minute():02d}",
            "duracao_minutos": self._duracao_input.value(),
            "observacoes": self._observacoes_input.text() or None,
        }
