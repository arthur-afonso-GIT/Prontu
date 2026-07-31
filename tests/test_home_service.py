from datetime import date

from services import home_service


def test_preparar_home_monta_resumo_e_geral_como_guarda_chuva(monkeypatch):
    monkeypatch.setattr(home_service, "date", _FixedDate)
    resultado = home_service.preparar_home(
        {
            "data_hoje": "28/07/2026",
            "pacientes": [
                {"id": 2, "nome": "Bia", "pasta": "Cardiologia"},
                {"id": 1, "nome": "Ana", "pasta": "Geral"},
            ],
            "pastas": [
                {"nome": "Cardiologia", "cor": "#ef4444"},
            ],
            "agenda": [
                {
                    "data": "28/07/2026",
                    "horario": "09:00",
                    "paciente": "Bia",
                    "status": "Confirmado",
                    "tipo_bloco": "principal",
                },
                {
                    "data": "28/07/2026",
                    "horario": "09:30",
                    "paciente": "Bia",
                    "status": "Confirmado",
                    "tipo_bloco": "continuação",
                },
            ],
            "retornos": [
                {
                    "id": 3,
                    "paciente_id": 1,
                    "paciente_nome": "Ana",
                    "data_prevista": "2026-07-27",
                },
            ],
        },
        "Arthur",
    )

    assert resultado["saudacao"] == "Olá, Arthur"
    assert resultado["total_pacientes"] == 2
    assert resultado["total_consultas"] == 1
    assert resultado["total_retornos"] == 1
    assert resultado["pastas"][0]["nome"] == "Geral"
    assert resultado["pastas"][0]["quantidade"] == 2
    assert resultado["pastas"][1] == {
        "nome": "Cardiologia",
        "cor": "#ef4444",
        "quantidade": 1,
    }
    assert resultado["retornos"][0]["data_texto"] == "27/07/2026"
    assert resultado["retornos"][0]["atrasado"] is True


def test_normalizar_nome_pasta_remove_espacos_excedentes():
    assert home_service.normalizar_nome_pasta("  Saúde   da Mulher ") == (
        "Saúde da Mulher"
    )


class _FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 28)
