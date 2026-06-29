"""Modal de configuração de importação de documento (nome e tipo do formulário)."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QWidget

from database.models import TipoFormularioEnum
from views.components.base_modal import BaseModal
from views.components.buttons import primary_button, secondary_button

_TIPO_LABELS: dict[TipoFormularioEnum, str] = {
    TipoFormularioEnum.EVOLUCAO_CLINICA: "Evolução Clínica",
    TipoFormularioEnum.AVALIACAO_NUTRICIONAL: "Avaliação Nutricional",
    TipoFormularioEnum.BIOIMPEDANCIA: "Bioimpedância",
    TipoFormularioEnum.ORTOPEDIA: "Ortopedia",
    TipoFormularioEnum.DERMATOLOGIA: "Dermatologia",
    TipoFormularioEnum.CARDIOLOGIA: "Cardiologia",
    TipoFormularioEnum.PEDIATRIA: "Pediatria",
    TipoFormularioEnum.GINECOLOGIA: "Ginecologia",
    TipoFormularioEnum.SCORE_CLINICO: "Score Clínico",
    TipoFormularioEnum.OUTRO: "Outro",
}


class ImportConfigModal(BaseModal):
    """Modal para que o usuário nomeie e categorize o documento antes da importação."""

    def __init__(self, parent: QWidget | None = None, nome_sugerido: str = "") -> None:
        super().__init__(title="Configurar Importação", parent=parent)

        form_layout = QFormLayout()

        self._nome_input = QLineEdit(nome_sugerido)
        self._nome_input.setPlaceholderText("Ex: Ficha de Avaliação Nutricional")

        self._tipo_combo = QComboBox()
        for tipo, label in _TIPO_LABELS.items():
            self._tipo_combo.addItem(label, userData=tipo)

        form_layout.addRow("Nome do formulário *", self._nome_input)
        form_layout.addRow("Categoria", self._tipo_combo)
        self.content_layout.addLayout(form_layout)

        actions_layout = QHBoxLayout()
        cancel_button = secondary_button("Cancelar")
        cancel_button.clicked.connect(self.reject)

        confirm_button = primary_button("Importar e Analisar")
        confirm_button.clicked.connect(self.accept)

        actions_layout.addStretch()
        actions_layout.addWidget(cancel_button)
        actions_layout.addWidget(confirm_button)
        self.content_layout.addLayout(actions_layout)

    def get_values(self) -> tuple[str, TipoFormularioEnum]:
        return self._nome_input.text().strip(), self._tipo_combo.currentData()
