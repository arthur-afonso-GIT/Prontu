"""Regras puras de apresentação e contagem da equipe."""
from __future__ import annotations

from datetime import datetime


PAPEIS_PERMITIDOS = {"profissional", "secretaria"}


def papel_texto(papel: str) -> str:
    return {
        "proprietario": "Proprietário",
        "profissional": "Profissional",
        "secretaria": "Secretária",
    }.get(str(papel or "").strip().lower(), str(papel or "").strip().title())


def formatar_expiracao(valor) -> str:
    try:
        data = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return data.strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return "Não informado"


def preparar_equipe(dados: dict | None) -> dict:
    dados = dados if isinstance(dados, dict) else {}
    membros = []
    for item in dados.get("membros") or []:
        if str(item.get("email") or "").lower().endswith("@prontu.device"):
            continue
        membros.append({
            "id": str(item.get("id") or ""),
            "nome": str(item.get("nome") or ""),
            "email": str(item.get("email") or ""),
            "papel": str(item.get("papel") or ""),
            "papel_texto": papel_texto(item.get("papel")),
            "proprietario": str(item.get("papel") or "") == "proprietario",
        })

    convites = [{
        "id": str(item.get("id") or ""),
        "nome": str(item.get("nome") or ""),
        "email": str(item.get("email") or ""),
        "papel": str(item.get("papel") or ""),
        "papel_texto": papel_texto(item.get("papel")),
        "expira_em": formatar_expiracao(item.get("expira_em")),
    } for item in (dados.get("convites") or [])]

    limite = int(dados.get("max_usuarios") or 0)
    usados = len(membros) + len(convites)
    return {
        "membros": membros,
        "convites": convites,
        "limite": limite,
        "usados": usados,
        "disponiveis": max(limite - usados, 0),
    }


def validar_convite(nome: str, email: str, papel: str) -> str:
    if not str(nome or "").strip():
        return "Informe o nome da pessoa."
    email = str(email or "").strip()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return "Informe um e-mail válido."
    if str(papel or "").strip().lower() not in PAPEIS_PERMITIDOS:
        return "Selecione um papel válido."
    return ""
