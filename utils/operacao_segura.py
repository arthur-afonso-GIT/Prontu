"""Pequenas proteções reutilizáveis para operações sensíveis da interface."""

import logging


LOGGER = logging.getLogger("prontu.operacoes")


def iniciar_operacao(botao, texto_em_andamento: str) -> bool:
    """Evita que o mesmo botão dispare duas gravações consecutivas."""
    if botao.property("prontu_ocupado"):
        return False

    botao.setProperty("prontu_ocupado", True)
    botao.setProperty("prontu_texto_original", botao.text())
    botao.setText(texto_em_andamento)
    botao.setEnabled(False)
    return True


def finalizar_operacao(botao) -> None:
    """Restaura o botão após sucesso ou falha da operação."""
    texto_original = botao.property("prontu_texto_original")
    if texto_original:
        botao.setText(texto_original)
    botao.setProperty("prontu_ocupado", False)
    botao.setEnabled(True)


def registrar_falha(contexto: str, erro: Exception) -> None:
    """Registra apenas o tipo do erro, sem expor dados sensíveis na interface."""
    LOGGER.error("Falha em %s (%s)", contexto, type(erro).__name__)


def mensagem_erro_usuario(acao: str) -> str:
    return (
        f"Não foi possível {acao} agora. Verifique sua conexão e tente novamente. "
        "Se o problema continuar, entre em contato com o suporte."
    )
