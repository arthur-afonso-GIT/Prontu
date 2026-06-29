"""
Card de linha de Paciente (item de lista/tabela reutilizável).

Usado tanto na tabela de "Pacientes Recentes" da Home quanto na tela
completa de Pacientes, garantindo que a apresentação de cada paciente
(nome, convênio, telefone, última consulta, ações) seja idêntica nos
dois contextos.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from forms.patient_schemas import PacienteListItemSchema
from styles.design_tokens import Spacing
from views.components.buttons import danger_button, ghost_button


class PatientRow(QWidget):
    """Uma linha representando um paciente, com ações de editar/excluir/abrir.

    Emite sinais que a tela contêiner escuta para navegar ou confirmar
    exclusão — o componente em si não toma nenhuma decisão de navegação
    ou persistência.
    """

    open_requested = Signal(int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, paciente: PacienteListItemSchema, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paciente = paciente

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.MD)

        nome_label = QLabel(paciente.nome)
        nome_label.setMinimumWidth(180)

        convenio_label = QLabel(paciente.convenio or "—")
        convenio_label.setObjectName("mutedText")
        convenio_label.setMinimumWidth(120)

        telefone_label = QLabel(paciente.telefone or "—")
        telefone_label.setObjectName("mutedText")
        telefone_label.setMinimumWidth(140)

        idade_label = QLabel(f"{paciente.idade} anos")
        idade_label.setObjectName("mutedText")
        idade_label.setMinimumWidth(70)

        open_button = ghost_button("Abrir ficha")
        open_button.clicked.connect(lambda: self.open_requested.emit(paciente.id))

        edit_button = ghost_button("Editar")
        edit_button.clicked.connect(lambda: self.edit_requested.emit(paciente.id))

        delete_button = danger_button("Excluir")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(paciente.id))

        layout.addWidget(nome_label)
        layout.addWidget(convenio_label)
        layout.addWidget(telefone_label)
        layout.addWidget(idade_label)
        layout.addStretch()
        layout.addWidget(open_button)
        layout.addWidget(edit_button)
        layout.addWidget(delete_button)
