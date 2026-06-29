"""
ViewModel da tela Home.

Na arquitetura MVVM, o ViewModel é responsável por preparar os dados
vindos da camada de serviço no formato exato que a View precisa exibir,
e por expor sinais Qt que a View escuta para se atualizar
reativamente — sem que a View precise conhecer NENHUM detalhe de como
os dados são obtidos (services, repositórios, banco).

Isso é o que viabiliza testar a lógica de apresentação (ex: "a lista de
pacientes recentes deve ter no máximo 10 itens") sem precisar
instanciar nenhum widget Qt.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from forms.patient_schemas import PacienteListItemSchema
from services.folder_service import FolderService
from services.patient_service import PatientService
from utils.logger import get_logger

logger = get_logger(__name__)


class HomeViewModel(QObject):
    """Prepara e expõe os dados necessários para renderizar a tela Home."""

    recent_patients_changed = Signal(list)  # list[PacienteListItemSchema]
    folders_changed = Signal(list)  # list[Pasta] (ORM, simples o suficiente para não precisar de DTO)
    error_occurred = Signal(str)

    def __init__(
        self,
        patient_service: PatientService | None = None,
        folder_service: FolderService | None = None,
    ) -> None:
        super().__init__()
        self._patient_service = patient_service or PatientService()
        self._folder_service = folder_service or FolderService()

    def load(self) -> None:
        """Carrega todos os dados necessários para a tela Home e emite os sinais correspondentes."""
        self.refresh_recent_patients()
        self.refresh_folders()

    def refresh_recent_patients(self, limit: int = 10) -> None:
        try:
            pacientes = self._patient_service.list_recent_patients(limit=limit)
            itens = [PacienteListItemSchema.model_validate(p) for p in pacientes]
            self.recent_patients_changed.emit(itens)
        except Exception as exc:  # noqa: BLE001 - converte qualquer falha em sinal de erro p/ UI
            logger.exception("Erro ao carregar pacientes recentes")
            self.error_occurred.emit(f"Não foi possível carregar os pacientes recentes: {exc}")

    def refresh_folders(self) -> None:
        try:
            pastas = self._folder_service.list_folders()
            self.folders_changed.emit(pastas)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao carregar pastas")
            self.error_occurred.emit(f"Não foi possível carregar as pastas: {exc}")

    def delete_patient(self, paciente_id: int) -> None:
        try:
            self._patient_service.delete_patient(paciente_id)
            self.refresh_recent_patients()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao excluir paciente")
            self.error_occurred.emit(str(exc))

    def create_folder(self, nome: str, cor: str) -> None:
        try:
            self._folder_service.create_folder(nome, cor)
            self.refresh_folders()
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))

    def rename_folder(self, pasta_id: int, novo_nome: str) -> None:
        try:
            self._folder_service.rename_folder(pasta_id, novo_nome)
            self.refresh_folders()
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))

    def delete_folder(self, pasta_id: int) -> None:
        try:
            self._folder_service.delete_folder(pasta_id)
            self.refresh_folders()
            self.refresh_recent_patients()
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))
