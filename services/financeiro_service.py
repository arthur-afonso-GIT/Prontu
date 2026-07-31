"""Regras puras de valores, situação e indicadores financeiros."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def numero_monetario(valor) -> float | None:
    if isinstance(valor, (int, float, Decimal)):
        return float(valor)
    texto = str(valor or "0").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(Decimal(texto))
    except (InvalidOperation, ValueError):
        return None


def moeda_br(valor) -> str:
    return (
        f"R$ {float(valor or 0):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def calcular_status(valor, recebido, status_atual="Pendente") -> str:
    valor = float(valor or 0)
    recebido = float(recebido or 0)
    if str(status_atual) == "Isento" and recebido <= 0:
        return "Isento"
    if recebido <= 0:
        return "Pendente"
    if valor <= 0 or recebido >= valor:
        return "Pago"
    return "Parcial"


def _data_br(valor: str) -> date | None:
    try:
        return datetime.strptime(str(valor), "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def preparar_registros(
    agenda: list[dict],
    pagamentos: list[dict],
    hoje: date | None = None,
) -> list[dict]:
    hoje = hoje or date.today()
    por_consulta = {
        (item.get("agenda_data"), item.get("agenda_horario")): item
        for item in pagamentos or []
    }
    registros = []
    for consulta in agenda or []:
        pagamento = por_consulta.get(
            (consulta.get("data"), consulta.get("horario")), {}
        )
        valor = float(pagamento.get("valor") or 0)
        recebido = float(pagamento.get("valor_recebido") or 0)
        status = calcular_status(
            valor, recebido, pagamento.get("status") or "Pendente"
        )
        data_consulta = _data_br(consulta.get("data"))
        atrasado = bool(
            data_consulta
            and data_consulta < hoje
            and status in {"Pendente", "Parcial"}
        )
        registros.append({
            **consulta,
            **pagamento,
            "agenda_data": consulta.get("data") or "",
            "agenda_horario": consulta.get("horario") or "",
            "status_consulta": consulta.get("status") or "Agendada",
            "status_pagamento": status,
            "status_exibicao": (
                "Pendente atrasado"
                if atrasado and status == "Pendente"
                else status
            ),
            "atrasado": atrasado,
            "valor": valor,
            "valor_recebido": recebido,
        })
    return sorted(
        registros,
        key=lambda item: (
            _data_br(item.get("agenda_data")) or date.min,
            item.get("agenda_horario") or "",
        ),
        reverse=True,
    )


def calcular_resumo(
    registros: list[dict], referencia: date | None = None
) -> dict:
    referencia = referencia or date.today()
    recebido_mes = 0.0
    a_receber = 0.0
    for registro in registros or []:
        data_consulta = _data_br(registro.get("agenda_data"))
        if not data_consulta or (
            data_consulta.month,
            data_consulta.year,
        ) != (referencia.month, referencia.year):
            continue
        valor = float(registro.get("valor") or 0)
        recebido = float(registro.get("valor_recebido") or 0)
        if registro.get("status_pagamento") == "Pago":
            recebido_mes += recebido
        if registro.get("status_pagamento") != "Isento":
            a_receber += max(valor - recebido, 0)
    return {
        "recebido": recebido_mes,
        "a_receber": a_receber,
        "consultas": len(registros or []),
    }
