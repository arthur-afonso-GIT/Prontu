"""
Normalização de números de telefone e geração de links do WhatsApp.

A regra de negócio aqui é: independentemente de como o usuário digitou o
telefone (com parênteses, espaços, traços, com ou sem DDI), o sistema
deve sempre conseguir gerar um link válido `https://wa.me/55DDDNUMERO`.
"""

from __future__ import annotations

import re

from config import config


def clean_phone_digits(raw_phone: str) -> str:
    """Remove toda formatação, deixando apenas dígitos.

    Args:
        raw_phone: Telefone como digitado pelo usuário, ex: "(81) 99876-5432".

    Returns:
        Apenas os dígitos, ex: "81998765432".
    """
    return re.sub(r"\D", "", raw_phone or "")


def format_phone_display(raw_phone: str) -> str:
    """Formata um telefone brasileiro para exibição: (DD) 9XXXX-XXXX.

    Se o formato não for reconhecido (ex: telefone internacional ou
    incompleto), retorna os dígitos limpos sem máscara, para nunca
    quebrar a exibição.
    """
    digits = clean_phone_digits(raw_phone)

    if len(digits) == 11:  # celular com DDD: 11 dígitos
        return f"({digits[0:2]}) {digits[2:7]}-{digits[7:11]}"
    if len(digits) == 10:  # fixo com DDD: 10 dígitos
        return f"({digits[0:2]}) {digits[2:6]}-{digits[6:10]}"

    return digits


def build_whatsapp_link(raw_phone: str) -> str | None:
    """Constrói o link `https://wa.me/55DDDNUMERO` a partir de um telefone.

    Args:
        raw_phone: Telefone em qualquer formato (com ou sem máscara,
            com ou sem o código do país).

    Returns:
        URL completa do WhatsApp, ou None se não houver dígitos
        suficientes para formar um número válido (DDD + número).
    """
    digits = clean_phone_digits(raw_phone)
    if not digits:
        return None

    # Remove o código do país se o usuário já tiver digitado (evita "5555...").
    if digits.startswith(config.DEFAULT_COUNTRY_CODE) and len(digits) > 11:
        digits = digits[len(config.DEFAULT_COUNTRY_CODE):]

    # Um número válido brasileiro com DDD tem 10 ou 11 dígitos.
    if len(digits) not in (10, 11):
        return None

    return f"https://wa.me/{config.DEFAULT_COUNTRY_CODE}{digits}"
