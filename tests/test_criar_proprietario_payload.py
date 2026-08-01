from types import SimpleNamespace

from database.database import Database


def test_criar_proprietario_envia_contrato_atual_e_legado(monkeypatch):
    capturado = {}

    def post(_url, **kwargs):
        capturado.update(kwargs)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"access_token": "token"},
        )

    monkeypatch.setattr("database.database.httpx.post", post)
    db = Database.__new__(Database)
    db.supabase_url = "https://example.supabase.co"
    db.supabase_key = "anon"
    db.supabase = object()
    db.session_manager = SimpleNamespace(
        access_token="device-token",
        device_id="desktop-123",
        _session={"consultorio_id": 42, "auth_user_id": "device-user"},
    )
    db.ultimo_erro_funcao = None
    db._adotar_sessao_de_login = lambda dados, lembrar: dados

    assert db.criar_login_proprietario(" Pessoa@Clinica.COM ", "12345678")
    assert capturado["json"] == {
        "email": "pessoa@clinica.com",
        "senha": "12345678",
        "password": "12345678",
        "consultorio_id": 42,
        "auth_user_id": "device-user",
        "device_id": "desktop-123",
    }
    assert capturado["headers"]["Authorization"] == "Bearer device-token"
