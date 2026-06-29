"""
View da Ficha do Paciente (cadastro/edição completo).

Implementa todos os campos especificados no projeto: dados pessoais,
campo de idade automático (somente leitura), telefone com botão
WhatsApp, e os campos clínicos (QP, HDA, Antecedentes, Exame Físico,
Observações) como TextArea expansível.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from database.models import Paciente, SexoEnum
from styles.design_tokens import Spacing
from views.components.auto_age_field import AutoAgeField
from views.components.buttons import primary_button, secondary_button
from views.components.card import Card
from views.components.expandable_textarea import ExpandableTextArea
from views.components.phone_field import PhoneFieldWithWhatsApp
from viewmodels.patient_detail_viewmodel import PatientDetailViewModel

_SEXO_LABELS = {
    SexoEnum.MASCULINO: "Masculino",
    SexoEnum.FEMININO: "Feminino",
    SexoEnum.OUTRO: "Outro",
}


class PatientDetailView(QWidget):
    """Tela de cadastro/edição completa de um paciente, com abas de dados e clínico."""

    back_requested = Signal()
    patient_saved = Signal(int)

    def __init__(
        self, view_model: PatientDetailViewModel | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model or PatientDetailViewModel()

        self._build_ui()
        self._connect_view_model()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        outer_layout.setSpacing(Spacing.LG)

        header_layout = QHBoxLayout()
        back_button = secondary_button("← Voltar")
        back_button.clicked.connect(self.back_requested.emit)

        self._title_label = QLabel("Novo Paciente")
        self._title_label.setObjectName("pageTitle")

        save_button = primary_button("Salvar")
        save_button.clicked.connect(self._on_save_clicked)

        header_layout.addWidget(back_button)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(save_button)
        outer_layout.addLayout(header_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(scroll_area.Shape.NoFrame)

        tabs = QTabWidget(self)
        tabs.addTab(self._build_personal_data_tab(), "Dados Pessoais")
        tabs.addTab(self._build_clinical_data_tab(), "Ficha Clínica")

        scroll_area.setWidget(tabs)
        outer_layout.addWidget(scroll_area)

    def _build_personal_data_tab(self) -> QWidget:
        card = Card()
        form_layout = QFormLayout()
        form_layout.setSpacing(Spacing.MD)
        form_layout.setLabelAlignment(form_layout.labelAlignment())

        self._nome_input = QLineEdit()
        self._endereco_input = QLineEdit()
        self._cidade_input = QLineEdit()

        self._telefone_field = PhoneFieldWithWhatsApp()

        self._data_nascimento_input = QDateEdit()
        self._data_nascimento_input.setCalendarPopup(True)
        self._data_nascimento_input.setDisplayFormat("dd/MM/yyyy")
        self._data_nascimento_input.setDate(QDate(1990, 1, 1))
        self._data_nascimento_input.setMaximumDate(QDate.currentDate())

        self._idade_field = AutoAgeField()
        self._idade_field.bind_to_birth_date_field(self._data_nascimento_input)

        self._sexo_combo = QComboBox()
        for sexo, label in _SEXO_LABELS.items():
            self._sexo_combo.addItem(label, userData=sexo)

        self._convenio_input = QLineEdit()

        form_layout.addRow("Nome completo *", self._nome_input)
        form_layout.addRow("Endereço", self._endereco_input)
        form_layout.addRow("Cidade", self._cidade_input)
        form_layout.addRow("Telefone", self._telefone_field)
        form_layout.addRow("Data de nascimento *", self._data_nascimento_input)
        form_layout.addRow("Idade", self._idade_field)
        form_layout.addRow("Sexo *", self._sexo_combo)
        form_layout.addRow("Convênio", self._convenio_input)

        card.body_layout.addLayout(form_layout)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(card)
        wrapper_layout.addStretch()
        return wrapper

    def _build_clinical_data_tab(self) -> QWidget:
        card = Card()

        self._qp_input = self._add_clinical_field(card, "Queixa Principal (QP)")
        self._hda_input = self._add_clinical_field(card, "História da Doença Atual (HDA)")
        self._antecedentes_input = self._add_clinical_field(card, "Antecedentes")
        self._exame_fisico_input = self._add_clinical_field(card, "Exame Físico")
        self._observacoes_input = self._add_clinical_field(card, "Observações")

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(card)
        wrapper_layout.addStretch()
        return wrapper

    def _add_clinical_field(self, card: Card, label_text: str) -> ExpandableTextArea:
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        textarea = ExpandableTextArea(placeholder=f"Digite {label_text.lower()}...")
        card.body_layout.addWidget(label)
        card.body_layout.addWidget(textarea)
        return textarea

    def _connect_view_model(self) -> None:
        self._view_model.patient_loaded.connect(self._on_patient_loaded)
        self._view_model.save_succeeded.connect(self._on_save_succeeded)
        self._view_model.error_occurred.connect(self._show_error)

    def load_for_new_patient(self) -> None:
        self._title_label.setText("Novo Paciente")
        self._clear_form()
        self._view_model.start_new_patient()

    def load_for_existing_patient(self, paciente_id: int) -> None:
        self._title_label.setText("Editar Paciente")
        self._view_model.load_patient(paciente_id)

    def _clear_form(self) -> None:
        self._nome_input.clear()
        self._endereco_input.clear()
        self._cidade_input.clear()
        self._telefone_field.set_value(None)
        self._data_nascimento_input.setDate(QDate(1990, 1, 1))
        self._sexo_combo.setCurrentIndex(0)
        self._convenio_input.clear()
        for campo in (
            self._qp_input, self._hda_input, self._antecedentes_input,
            self._exame_fisico_input, self._observacoes_input,
        ):
            campo.clear()

    def _on_patient_loaded(self, paciente: Paciente | None) -> None:
        if paciente is None:
            return

        self._nome_input.setText(paciente.nome)
        self._endereco_input.setText(paciente.endereco or "")
        self._cidade_input.setText(paciente.cidade or "")
        self._telefone_field.set_value(paciente.telefone)

        qdate_nascimento = QDate(
            paciente.data_nascimento.year, paciente.data_nascimento.month, paciente.data_nascimento.day
        )
        self._data_nascimento_input.setDate(qdate_nascimento)

        sexo_index = list(_SEXO_LABELS.keys()).index(paciente.sexo)
        self._sexo_combo.setCurrentIndex(sexo_index)

        self._convenio_input.setText(paciente.convenio or "")
        self._qp_input.setPlainText(paciente.qp or "")
        self._hda_input.setPlainText(paciente.hda or "")
        self._antecedentes_input.setPlainText(paciente.antecedentes or "")
        self._exame_fisico_input.setPlainText(paciente.exame_fisico or "")
        self._observacoes_input.setPlainText(paciente.observacoes or "")

    def _on_save_clicked(self) -> None:
        qdate = self._data_nascimento_input.date()

        dados = {
            "nome": self._nome_input.text(),
            "endereco": self._endereco_input.text() or None,
            "cidade": self._cidade_input.text() or None,
            "telefone": self._telefone_field.get_value() or None,
            "data_nascimento": date(qdate.year(), qdate.month(), qdate.day()),
            "sexo": self._sexo_combo.currentData(),
            "convenio": self._convenio_input.text() or None,
            "qp": self._qp_input.toPlainText() or None,
            "hda": self._hda_input.toPlainText() or None,
            "antecedentes": self._antecedentes_input.toPlainText() or None,
            "exame_fisico": self._exame_fisico_input.toPlainText() or None,
            "observacoes": self._observacoes_input.toPlainText() or None,
        }
        self._view_model.save(dados)

    def _on_save_succeeded(self, paciente_id: int) -> None:
        QMessageBox.information(self, "Sucesso", "Paciente salvo com sucesso.")
        self.patient_saved.emit(paciente_id)

    def _show_error(self, mensagem: str) -> None:
        QMessageBox.warning(self, "Erro ao salvar", mensagem)
