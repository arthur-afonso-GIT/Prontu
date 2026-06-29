"""
Schema de definição de campos de formulário dinâmico.

Este módulo define o "contrato" de dados que flui entre três camadas
independentes do sistema:

    Parser (extrai e classifica o documento)
        -> produz uma lista de `FieldDefinition`
    Builder (constrói os widgets Qt dinamicamente)
        -> consome `FieldDefinition` e gera componentes de UI
    Persistência (Formulario.estrutura_json)
        -> armazena `FieldDefinition` serializado como JSON

Manter esse contrato em um único lugar evita que o parser e a UI
"divirjam" silenciosamente sobre o significado de cada `tipo` de campo.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class FieldType(str, enum.Enum):
    """Tipos de campo que a engine de parsing pode detectar e a UI sabe renderizar."""

    TEXTO_SIMPLES = "texto_simples"
    TEXTAREA = "textarea"
    NUMERO = "numero"
    DATA = "data"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TABELA = "tabela"
    SCORE = "score"
    TITULO = "titulo"
    SUBTITULO = "subtitulo"
    GRUPO = "grupo"


class ScoreItemDefinition(BaseModel):
    """Um item pontuável dentro de um score clínico (ex: 1 linha do CHA2DS2-VASc)."""

    id: str
    label: str
    pontos: float
    selecionado_por_padrao: bool = False


class ScoreRiskBand(BaseModel):
    """Faixa de risco associada a um intervalo de pontuação total do score."""

    pontuacao_min: float
    pontuacao_max: float
    classificacao: str  # ex: "Baixo risco", "Risco moderado", "Alto risco"
    cor: str = "#10B981"  # cor sugerida para exibição (verde por padrão)


class TableColumnDefinition(BaseModel):
    """Definição de uma coluna de tabela editável (ex: tabela de bioimpedância)."""

    id: str
    label: str
    tipo: FieldType = FieldType.NUMERO
    unidade: str | None = None  # ex: "kg", "%", "cm"


class FieldDefinition(BaseModel):
    """Definição completa de um campo dentro de um formulário dinâmico.

    Esta é a unidade atômica que compõe `Formulario.estrutura_json`
    (uma lista de `FieldDefinition` serializados).
    """

    id: str = Field(description="Identificador único e estável do campo dentro do formulário.")
    tipo: FieldType
    label: str
    obrigatorio: bool = False
    placeholder: str | None = None
    ordem: int = 0

    # Específico de GRUPO: campos filhos agrupados visualmente.
    campos_filhos: list["FieldDefinition"] = Field(default_factory=list)

    # Específico de TABELA.
    colunas: list[TableColumnDefinition] = Field(default_factory=list)

    # Específico de SCORE.
    itens_score: list[ScoreItemDefinition] = Field(default_factory=list)
    faixas_risco: list[ScoreRiskBand] = Field(default_factory=list)

    # Específico de RADIO/CHECKBOX com opções fixas.
    opcoes: list[str] = Field(default_factory=list)


# Necessário para o tipo recursivo `campos_filhos: list["FieldDefinition"]`.
FieldDefinition.model_rebuild()
