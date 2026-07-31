from datetime import date, datetime

from services.agenda_service import (
    consulta_deve_entrar_em_atendimento,
    data_extenso,
    duracao_em_minutos,
    horario_agendamento_ja_passou,
    slots_da_consulta,
    status_legivel,
)


def test_duracao_e_slots_respeitam_grade_de_meia_hora():
    assert duracao_em_minutos("1h 30min") == 90
    assert slots_da_consulta("08:00", "1h 30min") == [
        "08:00",
        "08:30",
        "09:00",
    ]


def test_duracao_de_15_minutos_reserva_um_bloco():
    assert slots_da_consulta("10:30", "15 minutos") == ["10:30"]


def test_data_e_status_sao_apresentados_em_portugues():
    assert data_extenso(date(2026, 7, 28)) == "28 de julho de 2026 · terça-feira"
    assert status_legivel("✅ Confirmado") == "Confirmado"


def test_avisa_quando_horario_escolhido_ja_passou():
    agora = datetime(2026, 7, 29, 14, 20)

    assert horario_agendamento_ja_passou(
        "29/07/2026", "14:00", agora
    )
    assert not horario_agendamento_ja_passou(
        "29/07/2026", "14:30", agora
    )
    assert not horario_agendamento_ja_passou(
        "30/07/2026", "08:00", agora
    )


def test_horario_atual_entra_em_atendimento_sem_finalizar_sozinho():
    agora = datetime(2026, 7, 29, 14, 20)

    assert consulta_deve_entrar_em_atendimento(
        "29/07/2026", "14:00", "30 minutos", "Confirmado", agora
    )
    assert not consulta_deve_entrar_em_atendimento(
        "29/07/2026", "13:00", "30 minutos", "Agendado", agora
    )
    assert not consulta_deve_entrar_em_atendimento(
        "29/07/2026", "14:00", "30 minutos", "Realizada", agora
    )
