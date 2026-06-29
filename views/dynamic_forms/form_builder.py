"""
Builder Dinâmico de Formulário (fase de Construção do pipeline).

Recebe uma lista de `FieldDefinition` (produzida pela engine de parsing
ou recuperada de `Formulario.estrutura_json`) e constrói dinamicamente
os widgets Qt correspondentes, montando o formulário completo na tela.

Este é o componente que efetivamente implementa "Converter
automaticamente em componentes gráficos reutilizáveis", conforme
especificado na fase 3 (Construção) do projeto.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDateEdit, QDoubleSpinBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from forms.field_schema import FieldDefinition, FieldType
from styles.design_tokens import Spacing
from views.components.dynamic_table_field import DynamicTableField
from views.components.expandable_textarea import ExpandableTextArea
from views.components.score_field import ScoreField


class DynamicFormBuilder(QWidget):
    """Constrói e renderiza um formulário Qt completo a partir de `FieldDefinition`.

    Args:
        campos: Lista de definições de campo, na ordem em que devem
            aparecer na tela.
        dados_iniciais: Valores pré-existentes para popular o formulário
            (ex: ao reabrir uma resposta já salva para edição). Para
            campos do tipo TABELA, espera-se uma lista de dicts; para
            os demais, o valor bruto correspondente.
    """

    def __init__(
        self,
        campos: list[FieldDefinition],
        dados_iniciais: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._campos = campos
        self._dados_iniciais = dados_iniciais or {}
        self._field_widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)

        for campo in sorted(campos, key=lambda c: c.ordem):
            widget_campo = self._build_field_widget(campo)
            if widget_campo:
                layout.addWidget(widget_campo)

    def _build_field_widget(self, campo: FieldDefinition) -> QWidget | None:
        """Despacha a construção do widget de acordo com o tipo do campo."""
        builders = {
            FieldType.TITULO: self._build_titulo,
            FieldType.SUBTITULO: self._build_subtitulo,
            FieldType.TEXTO_SIMPLES: self._build_texto_simples,
            FieldType.TEXTAREA: self._build_textarea,
            FieldType.NUMERO: self._build_numero,
            FieldType.DATA: self._build_data,
            FieldType.TABELA: self._build_tabela,
            FieldType.SCORE: self._build_score,
            FieldType.CHECKBOX: self._build_texto_simples,  # checkbox isolado tratado como texto simples por padrão
            FieldType.GRUPO: self._build_grupo,
        }
        builder = builders.get(campo.tipo)
        return builder(campo) if builder else None

    def _wrap_with_label(self, campo: FieldDefinition, input_widget: QWidget) -> QWidget:
        """Envolve um widget de entrada com seu label acima, no padrão visual da aplicação."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(Spacing.XS)

        label_text = campo.label + (" *" if campo.obrigatorio else "")
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")

        container_layout.addWidget(label)
        container_layout.addWidget(input_widget)
        return container

    def _build_titulo(self, campo: FieldDefinition) -> QWidget:
        label = QLabel(campo.label)
        label.setObjectName("pageTitle")
        return label

    def _build_subtitulo(self, campo: FieldDefinition) -> QWidget:
        label = QLabel(campo.label)
        label.setObjectName("sectionTitle")
        return label

    def _build_texto_simples(self, campo: FieldDefinition) -> QWidget:
        input_widget = QLineEdit()
        input_widget.setPlaceholderText(campo.placeholder or "")
        valor_inicial = self._dados_iniciais.get(campo.id)
        if valor_inicial:
            input_widget.setText(str(valor_inicial))

        self._field_widgets[campo.id] = input_widget
        return self._wrap_with_label(campo, input_widget)

    def _build_textarea(self, campo: FieldDefinition) -> QWidget:
        input_widget = ExpandableTextArea(placeholder=campo.placeholder or "")
        valor_inicial = self._dados_iniciais.get(campo.id)
        if valor_inicial:
            input_widget.setPlainText(str(valor_inicial))

        self._field_widgets[campo.id] = input_widget
        return self._wrap_with_label(campo, input_widget)

    def _build_numero(self, campo: FieldDefinition) -> QWidget:
        input_widget = QDoubleSpinBox()
        input_widget.setRange(-999999, 999999)
        input_widget.setDecimals(2)
        valor_inicial = self._dados_iniciais.get(campo.id)
        if valor_inicial is not None:
            try:
                input_widget.setValue(float(valor_inicial))
            except (TypeError, ValueError):
                pass

        self._field_widgets[campo.id] = input_widget
        return self._wrap_with_label(campo, input_widget)

    def _build_data(self, campo: FieldDefinition) -> QWidget:
        from PySide6.QtCore import QDate

        input_widget = QDateEdit()
        input_widget.setCalendarPopup(True)
        input_widget.setDate(QDate.currentDate())

        self._field_widgets[campo.id] = input_widget
        return self._wrap_with_label(campo, input_widget)

    def _build_tabela(self, campo: FieldDefinition) -> QWidget:
        linhas_iniciais = self._dados_iniciais.get(campo.id)
        input_widget = DynamicTableField(campo, initial_rows=linhas_iniciais)

        self._field_widgets[campo.id] = input_widget
        return self._wrap_with_label(campo, input_widget)

    def _build_score(self, campo: FieldDefinition) -> QWidget:
        input_widget = ScoreField(campo)
        self._field_widgets[campo.id] = input_widget
        return self._wrap_with_label(campo, input_widget)

    def _build_grupo(self, campo: FieldDefinition) -> QWidget:
        grupo_container = QWidget()
        grupo_layout = QVBoxLayout(grupo_container)
        grupo_layout.setContentsMargins(0, 0, 0, 0)
        grupo_layout.setSpacing(Spacing.MD)

        titulo = QLabel(campo.label)
        titulo.setObjectName("sectionTitle")
        grupo_layout.addWidget(titulo)

        for sub_campo in sorted(campo.campos_filhos, key=lambda c: c.ordem):
            sub_widget = self._build_field_widget(sub_campo)
            if sub_widget:
                grupo_layout.addWidget(sub_widget)

        return grupo_container

    def collect_data(self) -> dict:
        """Extrai os valores atualmente preenchidos em todos os campos do formulário.

        Returns:
            Dicionário `{campo_id: valor}` pronto para ser persistido
            via `DynamicFormService.save_response()`.
        """
        dados: dict = {}

        for campo_id, widget in self._field_widgets.items():
            if isinstance(widget, ExpandableTextArea):
                dados[campo_id] = widget.toPlainText()
            elif isinstance(widget, QLineEdit):
                dados[campo_id] = widget.text()
            elif isinstance(widget, QDoubleSpinBox):
                dados[campo_id] = widget.value()
            elif isinstance(widget, QDateEdit):
                dados[campo_id] = widget.date().toPython().isoformat()
            elif isinstance(widget, (DynamicTableField, ScoreField)):
                dados[campo_id] = widget.get_data()

        return dados
