"""
Adaptador de LLM (camada de IA).

Define a interface abstrata que qualquer provedor de LLM (Anthropic
Claude, OpenAI, modelo local, etc.) deve implementar para ser usado pelo
sistema. Nenhum outro módulo do projeto deve importar um SDK de LLM
específico diretamente — toda comunicação passa por esta interface.

Isto implementa o princípio de Inversão de Dependência (SOLID): a
camada de IA depende apenas desta abstração, nunca de uma implementação
concreta. Trocar de provedor de LLM no futuro significa escrever uma
nova classe que implementa `LLMAdapter`, sem tocar em nenhuma linha de
`extraction.py`, `prompt_builder.py` ou qualquer código de UI.

ARQUITETURA DE CAMADAS (conforme especificado no projeto):

    AI Layer (este módulo)
        |
        v
    Parser  (parsers/parser_engine.py)
        |
        v
    Builder (camada que converte FieldDefinition em widgets — views/dynamic_forms)
        |
        v
    Interface (Qt Widgets)

A camada de IA NUNCA importa PySide6 nem qualquer módulo de `views/`.
Ela apenas produz/consome dados estruturados (texto, JSON), que outras
camadas decidem como exibir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Resposta padronizada de qualquer adaptador de LLM.

    Padronizar a resposta (em vez de repassar o formato bruto de cada
    SDK) é o que permite que `extraction.py` e futuros consumidores
    funcionem identicamente independente do provedor configurado.
    """

    texto: str
    modelo_usado: str
    sucesso: bool
    erro: str | None = None


class LLMAdapter(ABC):
    """Interface abstrata para qualquer provedor de LLM.

    Implementações concretas (ex: `AnthropicLLMAdapter`) devem ser
    criadas como subclasses desta classe e instanciadas via injeção de
    dependência onde forem necessárias (ex: em `extraction.py`), nunca
    instanciadas diretamente dentro de lógica de negócio genérica.
    """

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        """Envia um prompt ao LLM e retorna a resposta completa (não-streaming).

        Args:
            prompt: Texto completo do prompt, já formatado.
            max_tokens: Limite de tokens da resposta.

        Returns:
            `LLMResponse` com o texto gerado ou informação de erro.
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se este adaptador está configurado e pronto para uso
        (ex: chave de API presente, serviço local acessível).
        """
        raise NotImplementedError


class NullLLMAdapter(LLMAdapter):
    """Adaptador nulo (Null Object Pattern) usado quando nenhuma IA está configurada.

    Por que isto existe:
        O sistema deve funcionar perfeitamente bem SEM nenhuma
        integração de IA habilitada (esta é uma característica central
        do requisito do projeto: "preparado para futuras integrações",
        não uma dependência obrigatória). Em vez de espalhar checagens
        `if llm_adapter is not None` por todo o código consumidor, usamos
        este adaptador nulo como padrão, que sempre responde de forma
        previsível indicando indisponibilidade.
    """

    def complete(self, prompt: str, max_tokens: int = 1000) -> LLMResponse:
        return LLMResponse(
            texto="",
            modelo_usado="none",
            sucesso=False,
            erro="Nenhum provedor de IA está configurado nesta instalação.",
        )

    def is_available(self) -> bool:
        return False
