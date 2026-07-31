from datetime import date

from services.financeiro_service import (
    calcular_resumo,
    calcular_status,
    moeda_br,
    numero_monetario,
    preparar_registros,
)


def test_converte_e_formata_valores_brasileiros():
    assert numero_monetario("R$ 1.250,50") == 1250.5
    assert numero_monetario("150,00") == 150
    assert numero_monetario("valor inválido") is None
    assert moeda_br(1250.5) == "R$ 1.250,50"


def test_status_e_calculado_pelos_valores_mantendo_isencao():
    assert calcular_status(200, 0) == "Pendente"
    assert calcular_status(200, 50) == "Parcial"
    assert calcular_status(200, 200) == "Pago"
    assert calcular_status(0, 10) == "Pago"
    assert calcular_status(200, 0, "Isento") == "Isento"


def test_agenda_sem_pagamento_aparece_como_pendente_atrasada():
    registros = preparar_registros(
        [{
            "data": "10/07/2026",
            "horario": "08:00",
            "paciente": "Arthur",
            "procedimento": "Consulta",
            "status": "Realizada",
        }],
        [],
        hoje=date(2026, 7, 20),
    )

    assert len(registros) == 1
    assert registros[0]["status_exibicao"] == "Pendente atrasado"
    assert registros[0]["valor"] == 0


def test_resumo_considera_apenas_mes_de_referencia():
    registros = preparar_registros(
        [
            {"data": "10/07/2026", "horario": "08:00", "paciente": "A"},
            {"data": "10/06/2026", "horario": "08:00", "paciente": "B"},
        ],
        [
            {
                "agenda_data": "10/07/2026",
                "agenda_horario": "08:00",
                "valor": 200,
                "valor_recebido": 150,
                "status": "Parcial",
            },
            {
                "agenda_data": "10/06/2026",
                "agenda_horario": "08:00",
                "valor": 100,
                "valor_recebido": 100,
                "status": "Pago",
            },
        ],
        hoje=date(2026, 7, 20),
    )

    resumo = calcular_resumo(registros, date(2026, 7, 20))
    assert resumo == {"recebido": 0, "a_receber": 50, "consultas": 2}
