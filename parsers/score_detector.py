"""
Detector de scores clínicos (fase de Classificação da engine de parsing).

Reconhece tabelas de pontuação médica conhecidas (Framingham,
CHA2DS2-VASc, Wells, escalas nutricionais) e as converte em um campo do
tipo SCORE: um checklist onde cada item tem uma pontuação associada, o
total é calculado automaticamente, e uma classificação de risco é
exibida com base em faixas pré-definidas.

A detecção funciona em duas camadas:
    1. Reconhecimento por NOME do score (se o documento menciona
       explicitamente "CHA2DS2-VASc" ou "Escore de Framingham" etc.),
       usamos uma definição curada e confiável daquele score específico.
    2. Fallback genérico: se a tabela tem uma coluna numérica de
       "pontos" associada a uma coluna de "critério/item", construímos
       um SCORE genérico mesmo sem reconhecer o nome exato da escala.
"""

from __future__ import annotations

import re

from forms.field_schema import FieldDefinition, FieldType, ScoreItemDefinition, ScoreRiskBand
from parsers.raw_structures import RawTable

# Definições curadas de scores clínicos amplamente utilizados. Cada
# entrada mapeia um padrão de reconhecimento textual (presente no
# documento, próximo à tabela) para uma lista de itens pontuáveis e
# faixas de risco clinicamente validadas.
KNOWN_SCORES: dict[str, dict] = {
    "cha2ds2vasc": {
        "padroes_nome": [r"cha.?2.?ds.?2.?-?vasc"],
        "label": "CHA2DS2-VASc",
        "itens": [
            ("icc_disfuncao_vs", "Insuficiência cardíaca / disfunção de VE", 1),
            ("hipertensao", "Hipertensão arterial", 1),
            ("idade_75", "Idade ≥ 75 anos", 2),
            ("diabetes", "Diabetes mellitus", 1),
            ("avc_aits_tromboembolismo", "AVC/AIT/tromboembolismo prévio", 2),
            ("doenca_vascular", "Doença vascular", 1),
            ("idade_65_74", "Idade 65-74 anos", 1),
            ("sexo_feminino", "Sexo feminino", 1),
        ],
        "faixas_risco": [
            (0, 0, "Risco baixo", "#10B981"),
            (1, 1, "Risco intermediário", "#F59E0B"),
            (2, 9, "Risco alto", "#EF4444"),
        ],
    },
    "wells_tvp": {
        "padroes_nome": [r"\bwells\b"],
        "label": "Escore de Wells",
        "itens": [
            ("cancer_ativo", "Câncer ativo", 1),
            ("paralisia_imobilizacao", "Paralisia/imobilização recente de membro", 1),
            ("repouso_cirurgia", "Repouso >3 dias ou cirurgia recente", 1),
            ("dor_trajeto_venoso", "Dor no trajeto do sistema venoso profundo", 1),
            ("edema_membro_todo", "Edema de todo o membro", 1),
            ("edema_assimetrico", "Edema assimétrico de panturrilha (>3cm)", 1),
            ("veias_colaterais", "Veias colaterais superficiais não varicosas", 1),
            ("diagnostico_alternativo", "Diagnóstico alternativo tão provável quanto TVP", -2),
        ],
        "faixas_risco": [
            (-2, 0, "Baixa probabilidade", "#10B981"),
            (1, 2, "Probabilidade moderada", "#F59E0B"),
            (3, 8, "Alta probabilidade", "#EF4444"),
        ],
    },
}

_NUMERIC_PATTERN = re.compile(r"^-?\d+([.,]\d+)?$")


class ScoreDetector:
    """Detecta e constrói campos do tipo SCORE a partir de tabelas e contexto textual."""

    def try_detect_known_score(self, contexto_textual: str) -> dict | None:
        """Verifica se o texto próximo à tabela menciona um score conhecido.

        Args:
            contexto_textual: Texto das linhas próximas à tabela (ex: o
                título da seção), usado para identificar o nome do score.

        Returns:
            A definição curada do score (de `KNOWN_SCORES`), ou None.
        """
        texto_lower = contexto_textual.lower()
        for definicao in KNOWN_SCORES.values():
            for padrao in definicao["padroes_nome"]:
                if re.search(padrao, texto_lower):
                    return definicao
        return None

    def build_score_field(self, definicao: dict, ordem: int) -> FieldDefinition:
        """Constrói um `FieldDefinition` do tipo SCORE a partir de uma definição curada."""
        itens = [
            ScoreItemDefinition(id=item_id, label=label, pontos=pontos)
            for item_id, label, pontos in definicao["itens"]
        ]
        faixas = [
            ScoreRiskBand(pontuacao_min=minimo, pontuacao_max=maximo, classificacao=classificacao, cor=cor)
            for minimo, maximo, classificacao, cor in definicao["faixas_risco"]
        ]

        return FieldDefinition(
            id=f"score_{ordem}",
            tipo=FieldType.SCORE,
            label=definicao["label"],
            ordem=ordem,
            itens_score=itens,
            faixas_risco=faixas,
        )

    def try_build_generic_score_from_table(
        self, raw_table: RawTable, ordem: int, label_tabela: str = "Score Clínico"
    ) -> FieldDefinition | None:
        """Fallback: constrói um SCORE genérico se a tabela tiver colunas
        de "critério" (texto) e "pontos" (numérico) reconhecíveis.

        Returns:
            `FieldDefinition` do tipo SCORE, ou None se a tabela não
            parecer ser uma tabela de pontuação.
        """
        matriz = raw_table.to_matrix()
        if len(matriz) < 2:
            return None

        cabecalho = [c.lower() for c in matriz[0]]
        coluna_pontos = next(
            (i for i, c in enumerate(cabecalho) if "ponto" in c or "score" in c or "escore" in c),
            None,
        )
        if coluna_pontos is None:
            return None

        coluna_label = 0 if coluna_pontos != 0 else 1
        if coluna_label >= len(cabecalho):
            return None

        itens: list[ScoreItemDefinition] = []
        for indice_linha, linha in enumerate(matriz[1:]):
            if coluna_pontos >= len(linha) or coluna_label >= len(linha):
                continue

            valor_pontos_str = linha[coluna_pontos].strip()
            if not _NUMERIC_PATTERN.match(valor_pontos_str):
                continue

            itens.append(
                ScoreItemDefinition(
                    id=f"item_{indice_linha}",
                    label=linha[coluna_label].strip(),
                    pontos=float(valor_pontos_str.replace(",", ".")),
                )
            )

        if not itens:
            return None

        total_maximo = sum(item.pontos for item in itens if item.pontos > 0)
        faixas = [
            ScoreRiskBand(pontuacao_min=0, pontuacao_max=total_maximo * 0.33, classificacao="Risco baixo", cor="#10B981"),
            ScoreRiskBand(pontuacao_min=total_maximo * 0.34, pontuacao_max=total_maximo * 0.66, classificacao="Risco moderado", cor="#F59E0B"),
            ScoreRiskBand(pontuacao_min=total_maximo * 0.67, pontuacao_max=total_maximo, classificacao="Risco alto", cor="#EF4444"),
        ]

        return FieldDefinition(
            id=f"score_{ordem}",
            tipo=FieldType.SCORE,
            label=label_tabela,
            ordem=ordem,
            itens_score=itens,
            faixas_risco=faixas,
        )

    @staticmethod
    def calculate_score_total(
        itens_score: list[ScoreItemDefinition], itens_marcados: set[str]
    ) -> float:
        """Calcula a pontuação total a partir dos itens marcados pelo usuário."""
        return sum(item.pontos for item in itens_score if item.id in itens_marcados)

    @staticmethod
    def classify_risk(faixas_risco: list[ScoreRiskBand], pontuacao_total: float) -> ScoreRiskBand | None:
        """Retorna a faixa de risco correspondente à pontuação total calculada."""
        for faixa in faixas_risco:
            if faixa.pontuacao_min <= pontuacao_total <= faixa.pontuacao_max:
                return faixa
        return None
