from types import SimpleNamespace

import httpx

from database.database import Database


class _ConsultaLeituraFake:
    def __init__(self, supabase, tabela):
        self.supabase = supabase
        self.tabela = tabela

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def is_(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.supabase.execucoes += 1
        if self.supabase.falhas_restantes:
            self.supabase.falhas_restantes -= 1
            raise httpx.RemoteProtocolError("resposta interrompida")
        return SimpleNamespace(data=self.supabase.dados.get(self.tabela, []))


class _SupabaseLeituraFake:
    def __init__(self, dados, falhas=1):
        self.dados = dados
        self.falhas_restantes = falhas
        self.execucoes = 0

    def table(self, tabela):
        return _ConsultaLeituraFake(self, tabela)


def _database_fake(dados, falhas=1):
    database = Database.__new__(Database)
    database.supabase = _SupabaseLeituraFake(dados, falhas=falhas)
    database.consultorio_id = 7
    return database


def test_financeiro_repete_leitura_interrompida_sem_perder_dados(monkeypatch):
    monkeypatch.setattr("database.database.time.sleep", lambda _tempo: None)
    database = _database_fake({
        "agenda": [{"paciente": "Ana"}],
        "pagamentos_consultas": [{"status_pagamento": "Pago"}],
    })

    resultado = database.listar_financeiro_interface()

    assert resultado == {
        "agenda": [{"paciente": "Ana"}],
        "pagamentos": [{"status_pagamento": "Pago"}],
    }
    assert database.supabase.execucoes == 3


def test_retornos_repetem_leitura_interrompida_e_preservam_nome(monkeypatch):
    monkeypatch.setattr("database.database.time.sleep", lambda _tempo: None)
    database = _database_fake({
        "retornos_pacientes": [{
            "id": 3,
            "paciente_id": 11,
            "data_prevista": None,
            "motivo": "Consulta realizada",
            "status": "Pendente",
        }],
        "pacientes": [{"id": 11, "nome": "Arthur"}],
    })

    resultado = database.listar_retornos_pendentes()

    assert resultado[0]["paciente_nome"] == "Arthur"
    assert database.supabase.execucoes == 3


def test_erro_real_do_banco_nao_e_repetido(monkeypatch):
    monkeypatch.setattr("database.database.time.sleep", lambda _tempo: None)
    chamadas = 0

    def operacao():
        nonlocal chamadas
        chamadas += 1
        raise ValueError("consulta invalida")

    try:
        Database._executar_leitura_com_recuperacao(operacao)
    except ValueError:
        pass
    else:
        raise AssertionError("O erro real deveria ser preservado")

    assert chamadas == 1
