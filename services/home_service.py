"""Regras puras usadas pelo Painel Principal QML."""
from __future__ import annotations

from datetime import date


MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def normalizar_nome_pasta(valor) -> str:
    return " ".join(str(valor or "").strip().split())


def data_por_extenso(hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    return f"{hoje.day} de {MESES[hoje.month - 1]} de {hoje.year}"


def _data_retorno(valor: str) -> tuple[str, bool]:
    texto = str(valor or "").strip()
    if not texto:
        return "Data não informada", False
    try:
        prevista = date.fromisoformat(texto)
    except ValueError:
        return texto, False
    return prevista.strftime("%d/%m/%Y"), prevista < date.today()


def preparar_home(dados: dict | None, nome_profissional: str = "") -> dict:
    dados = dados if isinstance(dados, dict) else {}
    pacientes = list(dados.get("pacientes") or [])
    agenda = sorted(
        [
            item for item in (dados.get("agenda") or [])
            if str(item.get("tipo_bloco") or "principal") == "principal"
        ],
        key=lambda item: str(item.get("horario") or ""),
    )
    retornos = list(dados.get("retornos") or [])
    pastas_origem = list(dados.get("pastas") or [])

    unicas: dict[str, dict] = {}
    for item in [
        {"nome": "Geral", "cor": "#0284c7"},
        *pastas_origem,
        *({"nome": p.get("pasta") or "Geral"} for p in pacientes),
    ]:
        nome = normalizar_nome_pasta(item.get("nome")) or "Geral"
        chave = nome.casefold()
        if chave not in unicas:
            unicas[chave] = {
                "nome": nome,
                "cor": str(item.get("cor") or "#0284c7"),
            }

    pastas = []
    for item in sorted(
        unicas.values(),
        key=lambda pasta: (
            pasta["nome"].casefold() != "geral",
            pasta["nome"].casefold(),
        ),
    ):
        nome = item["nome"]
        quantidade = (
            len(pacientes)
            if nome.casefold() == "geral"
            else sum(
                normalizar_nome_pasta(p.get("pasta") or "Geral").casefold()
                == nome.casefold()
                for p in pacientes
            )
        )
        pastas.append({**item, "quantidade": quantidade})

    recentes = [{
        "id": int(item.get("id") or 0),
        "nome": str(item.get("nome") or "Paciente").upper(),
        "pasta": normalizar_nome_pasta(item.get("pasta")) or "Geral",
    } for item in pacientes[:8]]

    consultas = [{
        "data": str(item.get("data") or dados.get("data_hoje") or ""),
        "horario": str(item.get("horario") or ""),
        "paciente": str(item.get("paciente") or "Paciente").upper(),
        "status": str(item.get("status") or "Agendado"),
    } for item in agenda]

    retornos_preparados = []
    for item in retornos:
        prevista, atrasado = _data_retorno(item.get("data_prevista"))
        retornos_preparados.append({
            "id": int(item.get("id") or 0),
            "paciente_id": int(item.get("paciente_id") or 0),
            "paciente_nome": str(
                item.get("paciente_nome") or "Paciente"
            ).upper(),
            "data_prevista": str(item.get("data_prevista") or ""),
            "data_texto": prevista,
            "motivo": str(item.get("motivo") or ""),
            "atrasado": atrasado,
        })

    return {
        "saudacao": (
            f"Olá, {nome_profissional.strip()}"
            if str(nome_profissional or "").strip() else "Olá"
        ),
        "subtitulo": (
            "Aqui está o resumo do seu consultório para hoje, "
            f"{data_por_extenso()}."
        ),
        "total_pacientes": len(pacientes),
        "total_consultas": len(consultas),
        "total_retornos": len(retornos_preparados),
        "pastas": pastas,
        "pacientes_recentes": recentes,
        "consultas": consultas,
        "retornos": retornos_preparados,
    }
