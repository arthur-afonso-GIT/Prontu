"""
ViewModel do Calendário (Agenda).

Gerencia o modo de visualização ativo (Diário/Semanal/Mensal), a data
de referência atual, e expõe as consultas do período correspondente.
"""

from __future__ import annotations

import enum
from datetime import date, timedelta

from PySide6.QtCore import QObject, Signal

from database.models import StatusConsultaEnum
from services.appointment_service import AppointmentService, AppointmentServiceError
from services.patient_service import PatientService
from utils.logger import get_logger

logger = get_logger(__name__)


class CalendarViewMode(str, enum.Enum):
    DIARIO = "diario"
    SEMANAL = "semanal"
    MENSAL = "mensal"


class CalendarViewModel(QObject):
    """Gerencia o estado do calendário e os dados de consultas a exibir."""

    appointments_changed = Signal(list, object, object)  # (consultas, data_inicio, data_fim)
    error_occurred = Signal(str)
    appointment_saved = Signal()

    def __init__(
        self,
        appointment_service: AppointmentService | None = None,
        patient_service: PatientService | None = None,
    ) -> None:
        super().__init__()
        self._appointment_service = appointment_service or AppointmentService()
        self._patient_service = patient_service or PatientService()

        self._mode = CalendarViewMode.SEMANAL
        self._reference_date = date.today()

    def set_mode(self, mode: CalendarViewMode) -> None:
        self._mode = mode
        self.refresh()

    def go_to_today(self) -> None:
        self._reference_date = date.today()
        self.refresh()

    def go_to_date(self, target_date: date) -> None:
        self._reference_date = target_date
        self.refresh()

    def go_next(self) -> None:
        self._reference_date = self._shift_reference_date(forward=True)
        self.refresh()

    def go_previous(self) -> None:
        self._reference_date = self._shift_reference_date(forward=False)
        self.refresh()

    def _shift_reference_date(self, forward: bool) -> date:
        sinal = 1 if forward else -1
        if self._mode == CalendarViewMode.DIARIO:
            return self._reference_date + timedelta(days=sinal)
        if self._mode == CalendarViewMode.SEMANAL:
            return self._reference_date + timedelta(weeks=sinal)
        # Mensal: avança/retrocede aproximadamente um mês, preservando o dia quando possível.
        mes = self._reference_date.month + sinal
        ano = self._reference_date.year
        if mes > 12:
            mes = 1
            ano += 1
        elif mes < 1:
            mes = 12
            ano -= 1
        dia = min(self._reference_date.day, 28)
        return self._reference_date.replace(year=ano, month=mes, day=dia)

    def refresh(self) -> None:
        try:
            if self._mode == CalendarViewMode.DIARIO:
                consultas = self._appointment_service.get_appointments_for_day(self._reference_date)
                inicio = fim = self._reference_date
            elif self._mode == CalendarViewMode.SEMANAL:
                consultas = self._appointment_service.get_appointments_for_week(self._reference_date)
                inicio = self._reference_date - timedelta(days=self._reference_date.weekday())
                fim = inicio + timedelta(days=6)
            else:
                consultas = self._appointment_service.get_appointments_for_month(self._reference_date)
                inicio = self._reference_date.replace(day=1)
                fim = self._shift_reference_date(forward=True).replace(day=1) - timedelta(days=1)

            self.appointments_changed.emit(consultas, inicio, fim)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao carregar consultas")
            self.error_occurred.emit(str(exc))

    def create_appointment(
        self, paciente_id: int, data_consulta: date, horario: str, duracao_minutos: int, observacoes: str = ""
    ) -> bool:
        try:
            self._appointment_service.create_appointment(
                paciente_id, data_consulta, horario, duracao_minutos, observacoes
            )
            self.appointment_saved.emit()
            self.refresh()
            return True
        except AppointmentServiceError as exc:
            self.error_occurred.emit(str(exc))
            return False

    def update_status(self, consulta_id: int, status: StatusConsultaEnum) -> None:
        try:
            self._appointment_service.update_appointment_status(consulta_id, status)
            self.refresh()
        except AppointmentServiceError as exc:
            self.error_occurred.emit(str(exc))

    def delete_appointment(self, consulta_id: int) -> None:
        try:
            self._appointment_service.delete_appointment(consulta_id)
            self.refresh()
        except AppointmentServiceError as exc:
            self.error_occurred.emit(str(exc))

    @property
    def mode(self) -> CalendarViewMode:
        return self._mode

    @property
    def reference_date(self) -> date:
        return self._reference_date
