"""
Componente de Tabela Dinâmica editável.

Renderiza um campo do tipo TABELA (ver `forms/field_schema.py`) como uma
`QTableWidget` editável, permitindo adicionar novas linhas (ex: nova
avaliação de bioimpedância em uma consulta de retorno) e preservando o
histórico de todas as linhas já preenchidas — é o que viabiliza a
"comparação temporal" pedida no projeto.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from forms.field_schema import FieldDefinition
from views.components.buttons import ghost_button


class DynamicTableField(QWidget):
    """Widget de tabela editável gerado dinamicamente a partir de uma `FieldDefinition`.

    Args:
        field_definition: Definição da tabela (colunas, tipos, unidades).
        initial_rows: Linhas já preenchidas anteriormente (histórico),
            cada uma um dict `{coluna_id: valor}`.
    """

    def __init__(
        self,
        field_definition: FieldDefinition,
        initial_rows: list[dict] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._field_definition = field_definition

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(self)
        self._table.setColumnCount(len(field_definition.colunas))
        self._table.setHorizontalHeaderLabels(self._build_column_headers())
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)

        add_row_button = ghost_button("+ Adicionar avaliação")
        add_row_button.clicked.connect(self._add_empty_row)

        layout.addWidget(self._table)
        layout.addWidget(add_row_button)

        for linha in (initial_rows or []):
            self._add_row_with_data(linha)

        if not initial_rows:
            self._add_empty_row()

    def _build_column_headers(self) -> list[str]:
        headers = []
        for coluna in self._field_definition.colunas:
            label = coluna.label
            if coluna.unidade:
                label = f"{label} ({coluna.unidade})"
            headers.append(label)
        return headers

    def _add_empty_row(self) -> None:
        self._add_row_with_data({})

    def _add_row_with_data(self, dados_linha: dict) -> None:
        row_index = self._table.rowCount()
        self._table.insertRow(row_index)

        for col_index, coluna in enumerate(self._field_definition.colunas):
            valor = str(dados_linha.get(coluna.id, ""))
            self._table.setItem(row_index, col_index, QTableWidgetItem(valor))

    def get_data(self) -> list[dict]:
        """Extrai todos os dados preenchidos na tabela como lista de dicts."""
        linhas: list[dict] = []

        for row_index in range(self._table.rowCount()):
            linha_dados = {}
            tem_algum_valor = False

            for col_index, coluna in enumerate(self._field_definition.colunas):
                item = self._table.item(row_index, col_index)
                valor = item.text().strip() if item else ""
                if valor:
                    tem_algum_valor = True
                linha_dados[coluna.id] = valor

            if tem_algum_valor:
                linhas.append(linha_dados)

        return linhas
