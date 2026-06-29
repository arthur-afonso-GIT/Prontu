"""
View da Home (tela inicial).

Conforme especificado no projeto: exibe a tabela de "Pacientes
Recentes" com ações (editar, excluir, abrir ficha), o botão destacado
"+ Adicionar Paciente", e a barra de organização por pastas estilo
Notion.

Esta View NUNCA chama services ou repositórios diretamente — toda
comunicação com a camada de dados passa exclusivamente pelo
`HomeViewModel`, mantendo a separação MVVM.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from styles.design_tokens import Spacing
from views.components.buttons import primary_button
from views.components.card import Card
from views.components.folder_bar import FolderBar
from views.components.folder_modal import FolderModal
from views.components.patient_row import PatientRow
from viewmodels.home_viewmodel import HomeViewModel


class HomeView(QWidget):
    """Tela inicial: pacientes recentes + organização por pastas."""

    add_patient_requested = Signal()
    open_patient_requested = Signal(int)
    edit_patient_requested = Signal(int)

    def __init__(self, view_model: HomeViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model or HomeViewModel()

        self._build_ui()
        self._connect_view_model()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        header_layout = self._build_header()
        layout.addLayout(header_layout)

        self._folder_bar = FolderBar(self)
        self._folder_bar.new_folder_requested.connect(self._on_new_folder_requested)
        self._folder_bar.rename_folder_requested.connect(self._on_rename_folder_requested)
        self._folder_bar.delete_folder_requested.connect(self._on_delete_folder_requested)
        layout.addWidget(self._folder_bar)

        recent_patients_card = Card(self)
        section_title = QLabel("Pacientes Recentes")
        section_title.setObjectName("sectionTitle")
        recent_patients_card.add_widget(section_title)

        self._patients_list_container = QWidget()
        self._patients_list_layout = QVBoxLayout(self._patients_list_container)
        self._patients_list_layout.setContentsMargins(0, 0, 0, 0)
        self._patients_list_layout.setSpacing(Spacing.XS)
        recent_patients_card.add_widget(self._patients_list_container)

        layout.addWidget(recent_patients_card)
        layout.addStretch()

    def _build_header(self):
        from PySide6.QtWidgets import QHBoxLayout

        header_layout = QHBoxLayout()
        title = QLabel("Início")
        title.setObjectName("pageTitle")

        add_button = primary_button("+ Adicionar Paciente")
        add_button.clicked.connect(self.add_patient_requested.emit)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        return header_layout

    def _connect_view_model(self) -> None:
        self._view_model.recent_patients_changed.connect(self._render_patients_list)
        self._view_model.folders_changed.connect(self._folder_bar.set_folders)
        self._view_model.error_occurred.connect(self._show_error)

    def _render_patients_list(self, pacientes: list) -> None:
        while self._patients_list_layout.count():
            item = self._patients_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not pacientes:
            empty_label = QLabel("Nenhum paciente cadastrado ainda.")
            empty_label.setObjectName("mutedText")
            self._patients_list_layout.addWidget(empty_label)
            return

        for paciente in pacientes:
            row = PatientRow(paciente)
            row.open_requested.connect(self.open_patient_requested.emit)
            row.edit_requested.connect(self.edit_patient_requested.emit)
            row.delete_requested.connect(self._on_delete_patient_requested)
            self._patients_list_layout.addWidget(row)

    def _on_delete_patient_requested(self, paciente_id: int) -> None:
        confirmacao = QMessageBox.question(
            self,
            "Confirmar exclusão",
            "Tem certeza que deseja excluir este paciente? Esta ação não pode ser desfeita "
            "e removerá também todo o histórico de consultas e fichas associadas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmacao == QMessageBox.StandardButton.Yes:
            self._view_model.delete_patient(paciente_id)

    def _on_new_folder_requested(self) -> None:
        modal = FolderModal(self)
        if modal.exec():
            nome, cor = modal.get_values()
            if nome:
                self._view_model.create_folder(nome, cor)

    def _on_rename_folder_requested(self, pasta_id: int) -> None:
        modal = FolderModal(self)
        if modal.exec():
            novo_nome, _ = modal.get_values()
            if novo_nome:
                self._view_model.rename_folder(pasta_id, novo_nome)

    def _on_delete_folder_requested(self, pasta_id: int) -> None:
        confirmacao = QMessageBox.question(
            self,
            "Excluir pasta",
            "Excluir esta pasta? Os pacientes nela contidos não serão excluídos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmacao == QMessageBox.StandardButton.Yes:
            self._view_model.delete_folder(pasta_id)

    def _show_error(self, mensagem: str) -> None:
        QMessageBox.warning(self, "Erro", mensagem)

    def refresh(self) -> None:
        """Recarrega os dados da tela (chamado pela MainWindow ao navegar de volta para a Home)."""
        self._view_model.load()
