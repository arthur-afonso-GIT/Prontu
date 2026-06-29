"""
View da tela de Pacientes.

Lista completa de pacientes com pesquisa textual, filtros por cidade e
convênio, ordenação e paginação, conforme especificado no projeto.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from styles.design_tokens import Spacing
from views.components.buttons import ghost_button, primary_button, secondary_button
from views.components.card import Card
from views.components.patient_row import PatientRow
from viewmodels.patients_viewmodel import PatientsViewModel


class PatientsView(QWidget):
    """Tela de listagem completa de pacientes, com busca/filtro/paginação."""

    add_patient_requested = Signal()
    open_patient_requested = Signal(int)
    edit_patient_requested = Signal(int)

    def __init__(self, view_model: PatientsViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model or PatientsViewModel()

        self._build_ui()
        self._connect_view_model()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_filters())

        self._results_card = Card(self)
        self._results_list_container = QWidget()
        self._results_list_layout = QVBoxLayout(self._results_list_container)
        self._results_list_layout.setContentsMargins(0, 0, 0, 0)
        self._results_list_layout.setSpacing(Spacing.XS)
        self._results_card.add_widget(self._results_list_container)
        layout.addWidget(self._results_card)

        layout.addLayout(self._build_pagination())

    def _build_header(self) -> QHBoxLayout:
        header_layout = QHBoxLayout()
        title = QLabel("Pacientes")
        title.setObjectName("pageTitle")

        add_button = primary_button("+ Adicionar Paciente")
        add_button.clicked.connect(self.add_patient_requested.emit)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        return header_layout

    def _build_filters(self) -> QHBoxLayout:
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(Spacing.SM)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar por nome ou telefone...")
        self._search_input.textChanged.connect(self._view_model.set_search_text)

        self._cidade_combo = QComboBox()
        self._cidade_combo.addItem("Todas as cidades", userData=None)
        self._cidade_combo.currentIndexChanged.connect(self._on_cidade_changed)

        self._convenio_combo = QComboBox()
        self._convenio_combo.addItem("Todos os convênios", userData=None)
        self._convenio_combo.currentIndexChanged.connect(self._on_convenio_changed)

        self._order_combo = QComboBox()
        self._order_combo.addItem("Ordenar por nome", userData="nome")
        self._order_combo.addItem("Mais recentes primeiro", userData="data_cadastro")
        self._order_combo.currentIndexChanged.connect(self._on_order_changed)

        filters_layout.addWidget(self._search_input, stretch=2)
        filters_layout.addWidget(self._cidade_combo, stretch=1)
        filters_layout.addWidget(self._convenio_combo, stretch=1)
        filters_layout.addWidget(self._order_combo, stretch=1)
        return filters_layout

    def _build_pagination(self) -> QHBoxLayout:
        pagination_layout = QHBoxLayout()

        self._prev_button = ghost_button("← Anterior")
        self._prev_button.clicked.connect(self._on_prev_page)

        self._page_info_label = QLabel("Página 1")
        self._page_info_label.setObjectName("mutedText")

        self._next_button = ghost_button("Próxima →")
        self._next_button.clicked.connect(self._on_next_page)

        pagination_layout.addStretch()
        pagination_layout.addWidget(self._prev_button)
        pagination_layout.addWidget(self._page_info_label)
        pagination_layout.addWidget(self._next_button)
        pagination_layout.addStretch()
        return pagination_layout

    def _connect_view_model(self) -> None:
        self._view_model.results_changed.connect(self._render_results)
        self._view_model.filter_options_changed.connect(self._populate_filter_options)
        self._view_model.error_occurred.connect(self._show_error)

    def refresh(self) -> None:
        """Recarrega filtros e resultados (chamado pela MainWindow ao navegar para esta tela)."""
        self._view_model.load_filter_options()
        self._view_model.refresh()

    def _populate_filter_options(self, cidades: list[str], convenios: list[str]) -> None:
        self._cidade_combo.blockSignals(True)
        self._cidade_combo.clear()
        self._cidade_combo.addItem("Todas as cidades", userData=None)
        for cidade in cidades:
            self._cidade_combo.addItem(cidade, userData=cidade)
        self._cidade_combo.blockSignals(False)

        self._convenio_combo.blockSignals(True)
        self._convenio_combo.clear()
        self._convenio_combo.addItem("Todos os convênios", userData=None)
        for convenio in convenios:
            self._convenio_combo.addItem(convenio, userData=convenio)
        self._convenio_combo.blockSignals(False)

    def _on_cidade_changed(self, _index: int) -> None:
        self._view_model.set_cidade_filter(self._cidade_combo.currentData())

    def _on_convenio_changed(self, _index: int) -> None:
        self._view_model.set_convenio_filter(self._convenio_combo.currentData())

    def _on_order_changed(self, _index: int) -> None:
        self._view_model.set_order_by(self._order_combo.currentData())

    def _on_prev_page(self) -> None:
        self._view_model.go_to_page(self._view_model.current_page - 1)

    def _on_next_page(self) -> None:
        self._view_model.go_to_page(self._view_model.current_page + 1)

    def _render_results(self, pacientes: list, total: int) -> None:
        while self._results_list_layout.count():
            item = self._results_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not pacientes:
            empty_label = QLabel("Nenhum paciente encontrado com os filtros atuais.")
            empty_label.setObjectName("mutedText")
            self._results_list_layout.addWidget(empty_label)
        else:
            for paciente in pacientes:
                row = PatientRow(paciente)
                row.open_requested.connect(self.open_patient_requested.emit)
                row.edit_requested.connect(self.edit_patient_requested.emit)
                row.delete_requested.connect(self._on_delete_requested)
                self._results_list_layout.addWidget(row)

        page = self._view_model.current_page
        page_size = self._view_model.page_size
        total_paginas = max(1, (total + page_size - 1) // page_size)
        self._page_info_label.setText(f"Página {page} de {total_paginas} — {total} paciente(s)")
        self._prev_button.setEnabled(page > 1)
        self._next_button.setEnabled(page < total_paginas)

    def _on_delete_requested(self, paciente_id: int) -> None:
        confirmacao = QMessageBox.question(
            self,
            "Confirmar exclusão",
            "Tem certeza que deseja excluir este paciente? Esta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmacao == QMessageBox.StandardButton.Yes:
            self._view_model.delete_patient(paciente_id)

    def _show_error(self, mensagem: str) -> None:
        QMessageBox.warning(self, "Erro", mensagem)
