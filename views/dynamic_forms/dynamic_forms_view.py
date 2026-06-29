"""
View principal de Fichas Dinâmicas.

Tela que reúne: área de upload de PDF/DOCX, lista de formulários já
importados (ativos), e ação de preencher uma nova resposta para um
paciente a partir de qualquer formulário existente.
"""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from database.models import Formulario
from forms.patient_schemas import PacienteListItemSchema
from services.patient_service import PatientService
from styles.design_tokens import Spacing
from views.components.buttons import ghost_button, primary_button
from views.components.card import Card
from views.components.file_uploader import FileUploader
from views.components.import_config_modal import ImportConfigModal
from views.dynamic_forms.form_review_modal import FormReviewModal
from viewmodels.dynamic_forms_viewmodel import DynamicFormsViewModel

_TIPO_ICONS = {
    "evolucao_clinica": "📝", "avaliacao_nutricional": "🥗", "bioimpedancia": "⚖️",
    "ortopedia": "🦴", "dermatologia": "🩹", "cardiologia": "❤️",
    "pediatria": "🧒", "ginecologia": "🌸", "score_clinico": "📊", "outro": "📄",
}


class FormularioCard(QWidget):
    """Card representando um formulário dinâmico já importado, com ação de preencher."""

    def __init__(self, formulario: Formulario, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.formulario_id = formulario.id

        card = Card(self, with_shadow=True)
        layout = QHBoxLayout()

        icone = _TIPO_ICONS.get(formulario.tipo.value, "📄")
        icone_label = QLabel(icone)
        icone_label.setStyleSheet("font-size: 24px;")

        info_layout = QVBoxLayout()
        nome_label = QLabel(formulario.nome)
        nome_label.setObjectName("sectionTitle")
        meta_label = QLabel(f"v{formulario.versao} · {len(formulario.respostas)} resposta(s)")
        meta_label.setObjectName("mutedText")
        info_layout.addWidget(nome_label)
        info_layout.addWidget(meta_label)

        self.fill_button = ghost_button("Preencher")

        layout.addWidget(icone_label)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(self.fill_button)

        card.body_layout.addLayout(layout)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(card)


class DynamicFormsView(QWidget):
    """Tela de Fichas Dinâmicas: importação e preenchimento de formulários."""

    def __init__(
        self,
        view_model: DynamicFormsViewModel | None = None,
        patient_service: PatientService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model or DynamicFormsViewModel()
        self._patient_service = patient_service or PatientService()
        self._pending_import_path: str | None = None

        self._build_ui()
        self._connect_view_model()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        title = QLabel("Fichas Dinâmicas")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Importe modelos de fichas médicas em PDF ou DOCX. O sistema detecta "
            "automaticamente campos, tabelas e scores clínicos."
        )
        subtitle.setObjectName("mutedText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._uploader = FileUploader(self)
        self._uploader.file_selected.connect(self._on_file_selected)
        layout.addWidget(self._uploader)

        section_title = QLabel("Formulários Importados")
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title)

        self._forms_list_container = QWidget()
        self._forms_list_layout = QVBoxLayout(self._forms_list_container)
        self._forms_list_layout.setContentsMargins(0, 0, 0, 0)
        self._forms_list_layout.setSpacing(Spacing.SM)
        layout.addWidget(self._forms_list_container)

        layout.addStretch()

    def _connect_view_model(self) -> None:
        self._view_model.forms_list_changed.connect(self._render_forms_list)
        self._view_model.document_imported.connect(self._on_document_imported)
        self._view_model.error_occurred.connect(self._show_error)

    def refresh(self) -> None:
        """Recarrega a lista de formulários (chamado ao navegar para esta tela)."""
        self._view_model.refresh_forms_list()

    def _render_forms_list(self, formularios: list[Formulario]) -> None:
        while self._forms_list_layout.count():
            item = self._forms_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not formularios:
            empty_label = QLabel("Nenhum formulário importado ainda. Envie um PDF ou DOCX acima.")
            empty_label.setObjectName("mutedText")
            self._forms_list_layout.addWidget(empty_label)
            return

        for formulario in formularios:
            card = FormularioCard(formulario)
            card.fill_button.clicked.connect(
                lambda checked, fid=formulario.id: self._on_fill_form_clicked(fid)
            )
            self._forms_list_layout.addWidget(card)

    def _on_file_selected(self, file_path: str) -> None:
        from pathlib import Path

        nome_sugerido = Path(file_path).stem.replace("_", " ").title()
        modal = ImportConfigModal(self, nome_sugerido=nome_sugerido)

        if modal.exec():
            nome, tipo = modal.get_values()
            if not nome:
                QMessageBox.warning(self, "Nome obrigatório", "Informe um nome para o formulário.")
                return
            self._view_model.import_document(file_path, nome, tipo)

    def _on_document_imported(self, formulario_id: int, campos: list) -> None:
        QMessageBox.information(
            self, "Importação concluída",
            f"Formulário importado com sucesso! {len(campos)} campo(s) detectado(s).\n"
            "Você já pode preenchê-lo na lista abaixo.",
        )

    def _on_fill_form_clicked(self, formulario_id: int) -> None:
        formulario = self._view_model.get_form(formulario_id)
        if formulario is None:
            return

        from forms.field_schema import FieldDefinition
        campos = [FieldDefinition(**c) for c in formulario.get_estrutura()]

        pacientes, _ = self._patient_service.search_patients(page_size=500)
        itens = [PacienteListItemSchema.model_validate(p) for p in pacientes]

        modal = FormReviewModal(campos, itens, self)
        if modal.exec():
            paciente_id = modal.get_selected_patient_id()
            if paciente_id is None:
                QMessageBox.warning(self, "Paciente obrigatório", "Selecione um paciente antes de salvar.")
                return

            dados = modal.get_form_data()
            self._view_model.save_response(paciente_id, formulario_id, dados)
            QMessageBox.information(self, "Sucesso", "Resposta salva com sucesso.")

    def _show_error(self, mensagem: str) -> None:
        QMessageBox.warning(self, "Erro", mensagem)
