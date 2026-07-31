"""Validações puras dos formulários de acesso do Prontu."""
from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_email(valor: str) -> str:
    return str(valor or "").strip().lower()


def validar_email(valor: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(normalizar_email(valor)))


def validar_login(email: str, senha: str) -> str:
    if not validar_email(email):
        return "Informe um e-mail válido."
    if not str(senha or ""):
        return "Informe sua senha."
    return ""


def validar_convite(
    codigo: str, email: str, senha: str, confirmacao: str
) -> str:
    if not str(codigo or "").strip():
        return "Informe o código recebido."
    if not validar_email(email):
        return "Informe o mesmo e-mail usado no convite."
    return validar_nova_senha(senha, confirmacao)


def validar_nova_senha(senha: str, confirmacao: str) -> str:
    if len(str(senha or "")) < 8:
        return "A senha deve ter pelo menos 8 caracteres."
    if senha != confirmacao:
        return "As duas senhas precisam ser iguais."
    return ""


def validar_chave(chave: str) -> str:
    if not str(chave or "").strip():
        return "Informe a chave de ativação."
    return ""
