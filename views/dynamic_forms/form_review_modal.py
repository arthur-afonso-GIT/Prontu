"""
Modal de Revisão e Preenchimento de formulário dinâmico.

Exibe os campos detectados pela engine de parsing (via
`DynamicFormBuilder`) dentro de um modal, permitindo ao profissional
revisar a estrutura importada e, opcionalmente, já preencher uma
resposta associada a um paciente.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from forms.field_schema import FieldDefinition
from forms.patient_schemas import PacienteListItemSchema
from views.components.base_modal import BaseModal
from views.components.buttons import primary_button, secondary_button
from views.dynamic_forms.form_builder import DynamicFormBuilder


class FormReviewModal(BaseModal):
    """Modal que exibe o formulário construído dinamicamente para revisão/preenchimento.

    Args:
        campos: Estrutura de campos detectada pela engine de parsing.
        pacientes_disponiveis: Lista de pacientes para associar a resposta.
        dados_iniciais: Valores pré-existentes, para reabertura de uma resposta salva.
    """

    def __init__(
        self,
        campos: list[FieldDefinition],
        pacientes_disponiveis: list[PacienteListItemSchema],
        parent: QWidget | None = None,
        dados_iniciais: dict | None = None,
        paciente_id_inicial: int | None = None,
    ) -> None:
        super().__init__(title="Ficha Dinâmica", parent=parent, min_width=640)
        self.setMaximumHeight(720)

        self._paciente_combo = QComboBox()
        self._paciente_combo.addItem("Selecione um paciente...", userData=None)
        for paciente in pacientes_disponiveis:
            self._paciente_combo.addItem(paciente.nome, userData=paciente.id)

        if paciente_id_inicial:
            index = self._paciente_combo.findData(paciente_id_inicial)
            if index >= 0:
                self._paciente_combo.setCurrentIndex(index)

        self.content_layout.addWidget(self._paciente_combo)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(scroll_area.Shape.NoFrame)

        self._form_builder = DynamicFormBuilder(campos, dados_iniciais=dados_iniciais)
        scroll_area.setWidget(self._form_builder)
        self.content_layout.addWidget(scroll_area)

        actions_layout = QHBoxLayout()
        cancel_button = secondary_button("Cancelar")
        cancel_button.clicked.connect(self.reject)

        save_button = primary_button("Salvar Resposta")
        save_button.clicked.connect(self.accept)

        actions_layout.addStretch()
        actions_layout.addWidget(cancel_button)
        actions_layout.addWidget(save_button)
        self.content_layout.addLayout(actions_layout)

    def get_selected_patient_id(self) -> int | None:
        return self._paciente_combo.currentData()

    def get_form_data(self) -> dict:
        return self._form_builder.collect_data()
