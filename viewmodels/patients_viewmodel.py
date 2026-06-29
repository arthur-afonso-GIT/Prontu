"""
ViewModel da tela de Pacientes.

Gerencia o estado de busca/filtro/paginação e expõe os resultados via
sinais Qt, permitindo que a View (`views/patients/patients_view.py`)
permaneça uma camada puramente de apresentação.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from forms.patient_schemas import PacienteListItemSchema
from services.patient_service import PatientService
from utils.logger import get_logger

logger = get_logger(__name__)


class PatientsViewModel(QObject):
    """Gerencia busca, filtros e paginação da lista de pacientes."""

    results_changed = Signal(list, int)  # (itens da página atual, total de registros)
    filter_options_changed = Signal(list, list)  # (cidades distintas, convenios distintos)
    error_occurred = Signal(str)

    def __init__(self, patient_service: PatientService | None = None) -> None:
        super().__init__()
        self._patient_service = patient_service or PatientService()

        self._texto_busca: str | None = None
        self._cidade: str | None = None
        self._convenio: str | None = None
        self._pasta_id: int | None = None
        self._order_by: str = "nome"
        self._page: int = 1
        self._page_size: int = 25

    def load_filter_options(self) -> None:
        try:
            cidades = self._patient_service.list_distinct_cidades()
            convenios = self._patient_service.list_distinct_convenios()
            self.filter_options_changed.emit(cidades, convenios)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao carregar opções de filtro")
            self.error_occurred.emit(str(exc))

    def set_search_text(self, texto: str) -> None:
        self._texto_busca = texto or None
        self._page = 1
        self.refresh()

    def set_cidade_filter(self, cidade: str | None) -> None:
        self._cidade = cidade
        self._page = 1
        self.refresh()

    def set_convenio_filter(self, convenio: str | None) -> None:
        self._convenio = convenio
        self._page = 1
        self.refresh()

    def set_order_by(self, order_by: str) -> None:
        self._order_by = order_by
        self.refresh()

    def go_to_page(self, page: int) -> None:
        self._page = max(1, page)
        self.refresh()

    def refresh(self) -> None:
        try:
            pacientes, total = self._patient_service.search_patients(
                texto=self._texto_busca,
                cidade=self._cidade,
                convenio=self._convenio,
                pasta_id=self._pasta_id,
                order_by=self._order_by,
                page=self._page,
                page_size=self._page_size,
            )
            itens = [PacienteListItemSchema.model_validate(p) for p in pacientes]
            self.results_changed.emit(itens, total)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao buscar pacientes")
            self.error_occurred.emit(f"Erro ao buscar pacientes: {exc}")

    def delete_patient(self, paciente_id: int) -> None:
        try:
            self._patient_service.delete_patient(paciente_id)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))

    @property
    def current_page(self) -> int:
        return self._page

    @property
    def page_size(self) -> int:
        return self._page_size
