from types import SimpleNamespace

from database.database import Database


class FakeResponse:
    status_code = 409

    def json(self):
        return {"error": "O convite não possui mais uma vaga disponível."}


def test_funcao_preserva_mensagem_de_erro_do_servidor(monkeypatch):
    db = Database.__new__(Database)
    db.supabase_url = "https://example.supabase.co"
    db.supabase_key = "anon-key"
    db.session_manager = None
    db.ultimo_erro_funcao = None
    monkeypatch.setattr("database.database.httpx.post", lambda *args, **kwargs: FakeResponse())

    assert db._chamar_funcao_auth("aceitar-convite", {}) is None
    assert db.obter_ultimo_erro_funcao() == "O convite não possui mais uma vaga disponível."


def test_aceite_normaliza_codigo_e_email():
    db = Database.__new__(Database)
    capturado = {}

    def chamar(nome, corpo):
        capturado.update({"nome": nome, "corpo": corpo})
        return {"access_token": "token", "consultorio_id": 2}

    db._chamar_funcao_auth = chamar
    db._adotar_sessao_de_login = lambda dados, lembrar=True: SimpleNamespace(
        dados=dados, lembrar=lembrar
    )

    resultado = db.aceitar_convite_equipe(
        "  prontu-ab12  ", "  Pessoa@Example.COM ", "12345678"
    )

    assert capturado["nome"] == "aceitar-convite"
    assert capturado["corpo"] == {
        "codigo": "PRONTU-AB12",
        "email": "pessoa@example.com",
        "senha": "12345678",
    }
    assert resultado.lembrar is True
