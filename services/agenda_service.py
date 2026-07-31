"""Regras de apresentação e validação usadas pela Agenda QML."""
from __future__ import annotations

from datetime import date, datetime, timedelta


HORARIOS_GRADE = [
    f"{hora:02d}:{minuto:02d}"
    for hora in range(7, 20)
    for minuto in (0, 30)
    if not (hora == 19 and minuto == 30)
]

DURACOES = [
    "15 minutos",
    "30 minutos",
    "45 minutos",
    "1 hora",
    "1h 30min",
    "2 horas",
]

TIPOS_CONSULTA_PADRAO = [
    "Primeira Consulta / Avaliação",
    "Retorno",
    "Procedimento Clínico",
    "Telemedicina",
]

STATUS_CONSULTA = [
    "🕒 Agendado",
    "✅ Confirmado",
    "🏥 Em Atendimento",
    "✅ Realizada",
    "🚫 Cancelada",
    "❌ Faltou",
]

MESES_PT = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

DIAS_PT = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


def duracao_em_minutos(texto: str) -> int:
    texto = str(texto or "").strip().casefold()
    mapa = {
        "15 minutos": 15,
        "30 minutos": 30,
        "45 minutos": 45,
        "1 hora": 60,
        "1h 30min": 90,
        "2 horas": 120,
    }
    return mapa.get(texto, 30)


def slots_da_consulta(horario: str, duracao: str) -> list[str]:
    inicio = datetime.strptime(str(horario), "%H:%M")
    minutos = duracao_em_minutos(duracao)
    quantidade = max(1, (minutos + 29) // 30)
    return [
        (inicio + timedelta(minutes=30 * indice)).strftime("%H:%M")
        for indice in range(quantidade)
    ]


def data_br_para_date(valor: str) -> date:
    return datetime.strptime(str(valor), "%d/%m/%Y").date()


def data_hora_da_consulta(data_consulta: str, horario: str) -> datetime:
    """Converte os textos usados na agenda para um instante local."""
    return datetime.strptime(
        f"{str(data_consulta).strip()} {str(horario).strip()}",
        "%d/%m/%Y %H:%M",
    )


def horario_agendamento_ja_passou(
    data_consulta: str,
    horario: str,
    agora: datetime | None = None,
) -> bool:
    """Informa se o início escolhido já ficou no passado."""
    momento_atual = (agora or datetime.now()).replace(second=0, microsecond=0)
    return data_hora_da_consulta(data_consulta, horario) < momento_atual


def consulta_deve_entrar_em_atendimento(
    data_consulta: str,
    horario: str,
    duracao: str,
    status: str,
    agora: datetime | None = None,
) -> bool:
    """Detecta consultas que começaram e ainda estão dentro da duração prevista."""
    status_atual = status_legivel(status).casefold()
    if status_atual not in {"agendado", "confirmado"}:
        return False

    inicio = data_hora_da_consulta(data_consulta, horario)
    fim = inicio + timedelta(minutes=duracao_em_minutos(duracao))
    momento_atual = agora or datetime.now()
    return inicio <= momento_atual < fim


def data_iso_para_br(valor: str) -> str:
    return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")


def data_extenso(valor: date) -> str:
    return (
        f"{valor.day} de {MESES_PT[valor.month - 1]} de {valor.year}"
        f" · {DIAS_PT[valor.weekday()]}"
    )


def status_legivel(status: str) -> str:
    texto = str(status or "").strip()
    partes = texto.split(maxsplit=1)
    if len(partes) == 2 and not partes[0][0].isalnum():
        return partes[1]
    return texto


def cor_do_status(status: str) -> str:
    texto = status_legivel(status).casefold()
    if "realizada" in texto or "confirmado" in texto:
        return "#15935c"
    if "cancelada" in texto or "faltou" in texto:
        return "#d64545"
    if "atendimento" in texto:
        return "#7c3aed"
    return "#0788c9"
