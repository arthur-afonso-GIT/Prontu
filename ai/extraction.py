"""
Serviço de Extração assistida por IA (camada de IA).

Orquestra `PromptBuilder` e `LLMAdapter` para oferecer funcionalidades
de IA opcionais e desacopladas do restante do sistema. Este é o único
módulo da camada `ai/` que a camada de serviço de negócio
(`services/`) pode importar — `prompt_builder.py` e `llm_adapter.py`
são detalhes de implementação internos a esta camada.

IMPORTANTE: nenhum destes recursos é necessário para o funcionamento
do sistema. Eles representam pontos de extensão futuros. Por padrão,
`AIExtractionService` é instanciado com um `NullLLMAdapter`
(ver `llm_adapter.py`), portanto todas as chamadas retornam
graciosamente "indisponível" até que um adaptador real seja configurado.
"""

from __future__ import annotations

from ai.llm_adapter import LLMAdapter, LLMResponse, NullLLMAdapter
from ai.prompt_builder import PromptBuilder
from forms.field_schema import FieldDefinition
from utils.logger import get_logger

logger = get_logger(__name__)


class AIExtractionService:
    """Fornece funcionalidades de IA opcionais sobre fichas clínicas.

    Args:
        llm_adapter: Implementação concreta de `LLMAdapter` a ser usada.
            Se omitido, usa `NullLLMAdapter` (IA desabilitada por padrão).
    """

    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm_adapter = llm_adapter or NullLLMAdapter()
        self._prompt_builder = PromptBuilder()

    def is_ai_enabled(self) -> bool:
        """Indica se há um provedor de IA real configurado nesta instalação."""
        return self._llm_adapter.is_available()

    def suggest_fields_from_text(self, texto_documento: str) -> LLMResponse:
        """Solicita ao LLM sugestões de campos a partir de texto livre não estruturado."""
        if not self.is_ai_enabled():
            logger.info("Extração assistida por IA solicitada, mas nenhum provedor está configurado.")
            return LLMResponse(texto="", modelo_usado="none", sucesso=False, erro="IA não configurada.")

        prompt = self._prompt_builder.build_field_extraction_prompt(texto_documento)
        return self._llm_adapter.complete(prompt)

    def generate_clinical_summary(
        self, campos: list[FieldDefinition], dados_preenchidos: dict
    ) -> LLMResponse:
        """Solicita ao LLM um resumo textual de uma ficha clínica preenchida."""
        if not self.is_ai_enabled():
            return LLMResponse(texto="", modelo_usado="none", sucesso=False, erro="IA não configurada.")

        prompt = self._prompt_builder.build_clinical_summary_prompt(campos, dados_preenchidos)
        return self._llm_adapter.complete(prompt, max_tokens=300)

    def explain_risk_score(self, nome_score: str, pontuacao: float, classificacao: str) -> LLMResponse:
        """Solicita ao LLM uma explicação textual sobre uma classificação de risco calculada."""
        if not self.is_ai_enabled():
            return LLMResponse(texto="", modelo_usado="none", sucesso=False, erro="IA não configurada.")

        prompt = self._prompt_builder.build_risk_explanation_prompt(nome_score, pontuacao, classificacao)
        return self._llm_adapter.complete(prompt, max_tokens=200)
