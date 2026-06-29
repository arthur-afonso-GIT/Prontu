"""
Construtor de prompts (camada de IA).

Centraliza a construção de prompts textuais enviados a um `LLMAdapter`.
Mantém os textos de prompt como dados estruturados/templates em vez de
strings espalhadas pelo código, facilitando revisão, versionamento e
testes do comportamento de IA sem precisar instanciar nenhum modelo.
"""

from __future__ import annotations

from forms.field_schema import FieldDefinition


class PromptBuilder:
    """Constrói prompts estruturados para tarefas de IA relacionadas a fichas clínicas."""

    def build_field_extraction_prompt(self, texto_documento: str) -> str:
        """Constrói um prompt para que um LLM sugira campos a partir de texto livre.

        Caso futuro de uso: complementar a engine de parsing heurística
        (`parsers/field_detector.py`) com sugestões de um LLM para textos
        ambíguos que a heurística não conseguiu classificar com confiança.
        """
        return (
            "Você é um assistente especializado em estruturar fichas médicas.\n"
            "Analise o texto abaixo, extraído de um documento clínico, e "
            "retorne APENAS um JSON com uma lista de campos identificados.\n"
            "Cada campo deve ter: id (snake_case), tipo "
            "(texto_simples|textarea|numero|data|checkbox), label.\n\n"
            f"TEXTO:\n{texto_documento}\n\n"
            "RESPONDA APENAS COM O JSON, SEM TEXTO ADICIONAL."
        )

    def build_clinical_summary_prompt(
        self, campos: list[FieldDefinition], dados_preenchidos: dict
    ) -> str:
        """Constrói um prompt para gerar um resumo clínico textual de uma ficha preenchida.

        Caso futuro de uso: gerar automaticamente um resumo em linguagem
        natural de uma evolução clínica preenchida, para revisão rápida
        do profissional.
        """
        linhas_campos = []
        for campo in campos:
            valor = dados_preenchidos.get(campo.id, "")
            if valor:
                linhas_campos.append(f"- {campo.label}: {valor}")

        conteudo = "\n".join(linhas_campos)
        return (
            "Você é um assistente clínico. Resuma de forma objetiva e "
            "profissional os dados abaixo, preenchidos em uma ficha médica, "
            "em no máximo 3 frases. Não invente informações que não estejam "
            "presentes nos dados.\n\n"
            f"DADOS DA FICHA:\n{conteudo}"
        )

    def build_risk_explanation_prompt(self, nome_score: str, pontuacao: float, classificacao: str) -> str:
        """Constrói um prompt para explicar o significado clínico de um score calculado.

        Caso futuro de uso: ao lado do score calculado automaticamente
        (ver `parsers/score_detector.py`), oferecer uma explicação textual
        gerada por IA sobre o que aquela classificação de risco implica.
        """
        return (
            f"Explique de forma breve e clara, para um profissional de saúde, "
            f"o significado clínico de uma pontuação de {pontuacao} no escore "
            f"'{nome_score}', classificada como '{classificacao}'. "
            "Máximo de 2 frases. Não sugira condutas terapêuticas específicas, "
            "apenas explique o significado da classificação de risco."
        )
