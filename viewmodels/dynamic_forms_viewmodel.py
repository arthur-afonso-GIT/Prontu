"""
ViewModel de Fichas Dinâmicas.

Gerencia o fluxo de importação de documentos (PDF/DOCX -> Formulario)
e o preenchimento/persistência de respostas de pacientes a esses
formulários.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from database.models import TipoFormularioEnum
from forms.field_schema import FieldDefinition
from services.dynamic_form_service import DynamicFormService, DynamicFormServiceError
from utils.logger import get_logger

logger = get_logger(__name__)


class DynamicFormsViewModel(QObject):
    """Gerencia importação de documentos e preenchimento de fichas dinâmicas."""

    forms_list_changed = Signal(list)  # list[Formulario]
    document_imported = Signal(int, list)  # (formulario_id, list[FieldDefinition])
    response_saved = Signal(int)  # resposta_id
    error_occurred = Signal(str)

    def __init__(self, dynamic_form_service: DynamicFormService | None = None) -> None:
        super().__init__()
        self._service = dynamic_form_service or DynamicFormService()

    def refresh_forms_list(self) -> None:
        try:
            formularios = self._service.list_active_forms()
            self.forms_list_changed.emit(formularios)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao listar formulários")
            self.error_occurred.emit(str(exc))

    def import_document(
        self, file_path: str, nome_formulario: str, tipo: TipoFormularioEnum
    ) -> None:
        try:
            formulario_id, campos = self._service.import_document_as_form(
                file_path, nome_formulario, tipo
            )
            self.document_imported.emit(formulario_id, campos)
            self.refresh_forms_list()
        except DynamicFormServiceError as exc:
            self.error_occurred.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro inesperado ao importar documento")
            self.error_occurred.emit(f"Erro inesperado ao importar documento: {exc}")

    def update_structure(self, formulario_id: int, campos: list[FieldDefinition]) -> None:
        try:
            self._service.update_form_structure(formulario_id, campos)
        except DynamicFormServiceError as exc:
            self.error_occurred.emit(str(exc))

    def save_response(self, paciente_id: int, formulario_id: int, dados: dict) -> None:
        try:
            resposta_id = self._service.save_response(paciente_id, formulario_id, dados)
            self.response_saved.emit(resposta_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao salvar resposta de formulário")
            self.error_occurred.emit(str(exc))

    def get_form(self, formulario_id: int):
        return self._service.get_form(formulario_id)

    def get_patient_response_history(self, paciente_id: int):
        return self._service.get_patient_response_history(paciente_id)
