"""
View do Calendário (Agenda).

Implementa os três modos especificados no projeto (Diário, Semanal,
Mensal), com rolagem vertical e alta densidade de horários. Cada
compromisso exibe horário, paciente e cor de status.
"""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from forms.patient_schemas import PacienteListItemSchema
from services.patient_service import PatientService
from styles.design_tokens import Colors, Spacing
from views.components.appointment_card import AppointmentCard
from views.components.appointment_modal import AppointmentModal
from views.components.buttons import ghost_button, primary_button, secondary_button
from viewmodels.calendar_viewmodel import CalendarViewMode, CalendarViewModel

_DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

# Janela de horários exibida no grid Diário/Semanal (alta densidade, de 07h às 20h).
_HORARIO_INICIO = 7
_HORARIO_FIM = 20


class CalendarView(QWidget):
    """Tela de Calendário com os três modos de visualização especificados."""

    def __init__(
        self,
        view_model: CalendarViewModel | None = None,
        patient_service: PatientService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model or CalendarViewModel()
        self._patient_service = patient_service or PatientService()

        self._build_ui()
        self._connect_view_model()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.LG)

        layout.addLayout(self._build_header())

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(self._scroll_area.Shape.NoFrame)
        layout.addWidget(self._scroll_area)

    def _build_header(self) -> QHBoxLayout:
        header_layout = QHBoxLayout()

        title = QLabel("Calendário")
        title.setObjectName("pageTitle")

        self._period_label = QLabel()
        self._period_label.setObjectName("mutedText")

        prev_button = ghost_button("←")
        prev_button.clicked.connect(self._view_model.go_previous)

        today_button = secondary_button("Hoje")
        today_button.clicked.connect(self._view_model.go_to_today)

        next_button = ghost_button("→")
        next_button.clicked.connect(self._view_model.go_next)

        self._mode_diario_btn = self._build_mode_button("Diário", CalendarViewMode.DIARIO)
        self._mode_semanal_btn = self._build_mode_button("Semanal", CalendarViewMode.SEMANAL)
        self._mode_mensal_btn = self._build_mode_button("Mensal", CalendarViewMode.MENSAL)
        self._mode_semanal_btn.setChecked(True)

        new_appointment_button = primary_button("+ Nova Consulta")
        new_appointment_button.clicked.connect(self._on_new_appointment_clicked)

        header_layout.addWidget(title)
        header_layout.addWidget(self._period_label)
        header_layout.addStretch()
        header_layout.addWidget(prev_button)
        header_layout.addWidget(today_button)
        header_layout.addWidget(next_button)
        header_layout.addSpacing(Spacing.MD)
        header_layout.addWidget(self._mode_diario_btn)
        header_layout.addWidget(self._mode_semanal_btn)
        header_layout.addWidget(self._mode_mensal_btn)
        header_layout.addSpacing(Spacing.MD)
        header_layout.addWidget(new_appointment_button)
        return header_layout

    def _build_mode_button(self, label: str, mode: CalendarViewMode) -> QPushButton:
        button = secondary_button(label)
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self._on_mode_changed(mode))
        return button

    def _on_mode_changed(self, mode: CalendarViewMode) -> None:
        for btn in (self._mode_diario_btn, self._mode_semanal_btn, self._mode_mensal_btn):
            btn.setChecked(False)
        {
            CalendarViewMode.DIARIO: self._mode_diario_btn,
            CalendarViewMode.SEMANAL: self._mode_semanal_btn,
            CalendarViewMode.MENSAL: self._mode_mensal_btn,
        }[mode].setChecked(True)
        self._view_model.set_mode(mode)

    def _connect_view_model(self) -> None:
        self._view_model.appointments_changed.connect(self._render_appointments)
        self._view_model.error_occurred.connect(self._show_error)

    def refresh(self) -> None:
        """Recarrega as consultas do período atual (chamado ao navegar para esta tela)."""
        self._view_model.refresh()

    def _render_appointments(self, consultas: list, data_inicio: date, data_fim: date) -> None:
        if data_inicio == data_fim:
            self._period_label.setText(data_inicio.strftime("%d/%m/%Y"))
        else:
            self._period_label.setText(
                f"{data_inicio.strftime('%d/%m')} – {data_fim.strftime('%d/%m/%Y')}"
            )

        mode = self._view_model.mode
        if mode == CalendarViewMode.MENSAL:
            grid_widget = self._build_month_grid(consultas, data_inicio, data_fim)
        else:
            dias = [data_inicio] if mode == CalendarViewMode.DIARIO else [
                data_inicio + timedelta(days=i) for i in range((data_fim - data_inicio).days + 1)
            ]
            grid_widget = self._build_day_columns_grid(consultas, dias)

        self._scroll_area.setWidget(grid_widget)

    def _build_day_columns_grid(self, consultas: list, dias: list[date]) -> QWidget:
        """Constrói o grid de colunas por dia (usado nos modos Diário e Semanal)."""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(Spacing.XS)

        for col_index, dia in enumerate(dias):
            header_label = QLabel(f"{_DIAS_SEMANA[dia.weekday()]}\n{dia.strftime('%d/%m')}")
            header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_label.setStyleSheet(
                f"font-weight: 600; padding: {Spacing.SM}px; "
                f"background-color: {Colors.SURFACE}; border-radius: 8px;"
            )
            grid.addWidget(header_label, 0, col_index)

        consultas_por_dia: dict[date, list] = {dia: [] for dia in dias}
        for consulta in consultas:
            if consulta.data in consultas_por_dia:
                consultas_por_dia[consulta.data].append(consulta)

        for row_index, hora in enumerate(range(_HORARIO_INICIO, _HORARIO_FIM), start=1):
            hora_label = QLabel(f"{hora:02d}:00")
            hora_label.setObjectName("mutedText")
            grid.addWidget(hora_label, row_index, 0 if len(dias) == 1 else 0, 1, 1)

        for col_index, dia in enumerate(dias):
            coluna_container = QWidget()
            coluna_layout = QVBoxLayout(coluna_container)
            coluna_layout.setContentsMargins(0, 0, 0, 0)
            coluna_layout.setSpacing(Spacing.XS)
            coluna_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            consultas_ordenadas = sorted(consultas_por_dia[dia], key=lambda c: c.horario)
            if not consultas_ordenadas:
                empty_label = QLabel("Sem consultas")
                empty_label.setObjectName("mutedText")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                coluna_layout.addWidget(empty_label)
            else:
                for consulta in consultas_ordenadas:
                    card = AppointmentCard(consulta)
                    card.clicked.connect(self._on_appointment_clicked)
                    coluna_layout.addWidget(card)

            grid.addWidget(coluna_container, 1, col_index, _HORARIO_FIM - _HORARIO_INICIO, 1)

        return container

    def _build_month_grid(self, consultas: list, data_inicio: date, data_fim: date) -> QWidget:
        """Constrói o grid de células por dia do mês (modo Mensal)."""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(Spacing.XS)

        for col_index, nome_dia in enumerate(_DIAS_SEMANA):
            label = QLabel(nome_dia[:3])
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: 600;")
            grid.addWidget(label, 0, col_index)

        consultas_por_dia: dict[date, list] = {}
        for consulta in consultas:
            consultas_por_dia.setdefault(consulta.data, []).append(consulta)

        primeiro_dia_semana = data_inicio.weekday()
        dia_atual = data_inicio
        row, col = 1, primeiro_dia_semana

        while dia_atual <= data_fim:
            cell = self._build_month_cell(dia_atual, consultas_por_dia.get(dia_atual, []))
            grid.addWidget(cell, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1
            dia_atual += timedelta(days=1)

        return container

    def _build_month_cell(self, dia: date, consultas_do_dia: list) -> QWidget:
        cell = QWidget()
        cell.setMinimumHeight(90)
        cell.setStyleSheet(
            f"background-color: {Colors.SURFACE}; border-radius: 8px; border: 1px solid {Colors.BORDER};"
        )
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(Spacing.XS, Spacing.XS, Spacing.XS, Spacing.XS)
        layout.setSpacing(2)

        dia_label = QLabel(str(dia.day))
        dia_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(dia_label)

        for consulta in sorted(consultas_do_dia, key=lambda c: c.horario)[:3]:
            nome_paciente = consulta.paciente.nome if consulta.paciente else "Paciente"
            item_label = QLabel(f"{consulta.horario} {nome_paciente}")
            item_label.setStyleSheet(f"font-size: 11px; color: {Colors.ACCENT};")
            layout.addWidget(item_label)

        if len(consultas_do_dia) > 3:
            mais_label = QLabel(f"+{len(consultas_do_dia) - 3} mais")
            mais_label.setObjectName("mutedText")
            layout.addWidget(mais_label)

        layout.addStretch()
        return cell

    def _on_appointment_clicked(self, consulta_id: int) -> None:
        confirmacao = QMessageBox.question(
            self,
            "Consulta",
            "Deseja cancelar esta consulta?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmacao == QMessageBox.StandardButton.Yes:
            self._view_model.delete_appointment(consulta_id)

    def _on_new_appointment_clicked(self) -> None:
        pacientes, _ = self._patient_service.search_patients(page_size=500)
        itens = [PacienteListItemSchema.model_validate(p) for p in pacientes]

        if not itens:
            QMessageBox.information(
                self, "Nenhum paciente", "Cadastre um paciente antes de agendar uma consulta."
            )
            return

        modal = AppointmentModal(itens, self, data_inicial=self._view_model.reference_date)
        if modal.exec():
            valores = modal.get_values()
            sucesso = self._view_model.create_appointment(**valores)
            if sucesso:
                QMessageBox.information(self, "Sucesso", "Consulta agendada com sucesso.")

    def _show_error(self, mensagem: str) -> None:
        QMessageBox.warning(self, "Erro", mensagem)
