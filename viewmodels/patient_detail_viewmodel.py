"""
ViewModel da Ficha do Paciente (tela de edição completa de um paciente).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from database.models import Paciente
from services.patient_service import PatientService, PatientServiceError
from utils.logger import get_logger

logger = get_logger(__name__)


class PatientDetailViewModel(QObject):
    """Gerencia o carregamento, edição e histórico de um paciente específico."""

    patient_loaded = Signal(object)  # Paciente (ORM) - carregado com relacionamentos
    save_succeeded = Signal(int)  # paciente_id
    error_occurred = Signal(str)

    def __init__(self, patient_service: PatientService | None = None) -> None:
        super().__init__()
        self._patient_service = patient_service or PatientService()
        self._current_patient_id: int | None = None

    def load_patient(self, paciente_id: int) -> None:
        try:
            paciente = self._patient_service.get_patient(paciente_id)
            if paciente is None:
                self.error_occurred.emit(f"Paciente id={paciente_id} não encontrado.")
                return
            self._current_patient_id = paciente_id
            self.patient_loaded.emit(paciente)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao carregar paciente")
            self.error_occurred.emit(str(exc))

    def start_new_patient(self) -> None:
        """Sinaliza o início de um cadastro novo (sem paciente carregado ainda)."""
        self._current_patient_id = None
        self.patient_loaded.emit(None)

    def save(self, dados: dict) -> None:
        """Cria um novo paciente ou atualiza o paciente atualmente carregado."""
        try:
            if self._current_patient_id is None:
                novo_id = self._patient_service.create_patient(dados)
                self._current_patient_id = novo_id
                self.save_succeeded.emit(novo_id)
            else:
                self._patient_service.update_patient(self._current_patient_id, dados)
                self.save_succeeded.emit(self._current_patient_id)
        except PatientServiceError as exc:
            self.error_occurred.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro inesperado ao salvar paciente")
            self.error_occurred.emit(f"Erro inesperado ao salvar: {exc}")

    def get_appointment_history(self):
        if self._current_patient_id is None:
            return []
        return self._patient_service.get_patient_appointment_history(self._current_patient_id)

    def get_form_history(self):
        if self._current_patient_id is None:
            return []
        return self._patient_service.get_patient_form_history(self._current_patient_id)
