"""
Detector de tabelas (fase de Classificação da engine de parsing).

Converte uma `RawTable` extraída do documento em um `FieldDefinition` do
tipo TABELA, inferindo o tipo de cada coluna (número, texto) a partir do
cabeçalho e do conteúdo das primeiras linhas de dados.

Tabelas clínicas comuns que este detector reconhece bem: bioimpedância,
acompanhamento de peso/IMC, evolução de medidas antropométricas — todas
caracterizadas por um cabeçalho com nomes de medidas e linhas de dados
numéricos abaixo.
"""

from __future__ import annotations

import re

from forms.field_schema import FieldDefinition, FieldType, TableColumnDefinition
from parsers.raw_structures import RawTable

# Unidades comumente associadas a colunas de avaliação física/nutricional,
# usadas para enriquecer o label da coluna quando detectadas no cabeçalho.
_UNIT_PATTERNS: dict[str, re.Pattern] = {
    "kg": re.compile(r"\bkg\b", re.IGNORECASE),
    "cm": re.compile(r"\bcm\b", re.IGNORECASE),
    "%": re.compile(r"%"),
    "kcal": re.compile(r"\bkcal\b", re.IGNORECASE),
}

_NUMERIC_PATTERN = re.compile(r"^-?\d+([.,]\d+)?$")


class TableDetector:
    """Classifica tabelas extraídas em campos TABELA editáveis."""

    def detect_table_field(self, raw_table: RawTable, ordem: int) -> FieldDefinition:
        """Converte uma `RawTable` em um `FieldDefinition` do tipo TABELA.

        Args:
            raw_table: Tabela extraída pela fase de Extração.
            ordem: Posição de leitura da tabela no documento original.

        Returns:
            `FieldDefinition` com `colunas` preenchidas a partir do cabeçalho.
        """
        cabecalho = raw_table.header_row()
        matriz = raw_table.to_matrix()
        linhas_dados = matriz[1:] if len(matriz) > 1 else []

        colunas = [
            self._build_column(label=titulo_coluna, indice_coluna=indice, linhas_dados=linhas_dados)
            for indice, titulo_coluna in enumerate(cabecalho)
        ]

        label_tabela = self._infer_table_label(cabecalho)

        return FieldDefinition(
            id=f"tabela_{ordem}",
            tipo=FieldType.TABELA,
            label=label_tabela,
            ordem=ordem,
            colunas=colunas,
        )

    def _build_column(
        self, label: str, indice_coluna: int, linhas_dados: list[list[str]]
    ) -> TableColumnDefinition:
        """Infere o tipo e a unidade de uma coluna a partir do cabeçalho e dos dados."""
        unidade = self._detect_unit(label)
        tipo = self._infer_column_type(indice_coluna, linhas_dados)
        column_id = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or f"col_{indice_coluna}"

        return TableColumnDefinition(id=column_id, label=label, tipo=tipo, unidade=unidade)

    def _detect_unit(self, label: str) -> str | None:
        for unidade, pattern in _UNIT_PATTERNS.items():
            if pattern.search(label):
                return unidade
        return None

    def _infer_column_type(self, indice_coluna: int, linhas_dados: list[list[str]]):
        """Verifica se os valores de uma coluna são predominantemente numéricos."""
        from forms.field_schema import FieldType as FT

        valores = [
            linha[indice_coluna]
            for linha in linhas_dados
            if indice_coluna < len(linha) and linha[indice_coluna].strip()
        ]
        if not valores:
            return FT.TEXTO_SIMPLES

        numericos = sum(1 for v in valores if _NUMERIC_PATTERN.match(v.strip()))
        return FT.NUMERO if numericos / len(valores) > 0.6 else FT.TEXTO_SIMPLES

    def _infer_table_label(self, cabecalho: list[str]) -> str:
        """Tenta inferir um nome amigável para a tabela a partir do cabeçalho.

        Heurística: procura por palavras-chave conhecidas de fichas
        clínicas nos títulos de coluna; caso nenhuma seja encontrada,
        usa um nome genérico baseado na primeira coluna.
        """
        texto_cabecalho = " ".join(cabecalho).lower()

        palavras_chave = {
            "bioimpedância": ["bioimpedância", "massa gorda", "massa magra"],
            "avaliação antropométrica": ["imc", "circunferência", "peso"],
            "evolução clínica": ["evolução", "data", "observação"],
        }

        for nome_tabela, termos in palavras_chave.items():
            if any(termo in texto_cabecalho for termo in termos):
                return nome_tabela.capitalize()

        return cabecalho[0].capitalize() if cabecalho else "Tabela"
