import json
from types import SimpleNamespace

import pytest

from database.database import (
    Database,
    ErroAnexoFicha,
    TAMANHO_MAXIMO_ANEXO_FICHA,
    _normalizar_anexos_ficha,
)


class _BucketComSignedUrl:
    def create_signed_url(self, caminho, duracao):
        assert caminho == "7/11/exame.pdf"
        assert duracao == 120
        return {
            "signedUrl": (
                "/storage/v1/object/sign/fichas-anexos/"
                "7/11/exame.pdf?token=teste"
            )
        }


class _Storage:
    def from_(self, nome):
        assert nome == "fichas-anexos"
        return _BucketComSignedUrl()


class _Supabase:
    storage = _Storage()


def test_normaliza_anexos_antigos_gravados_como_texto_json():
    anexos = _normalizar_anexos_ficha(json.dumps([{
        "nome": "resultado.pdf",
        "caminho": "7/11/resultado.pdf",
        "tipo": "application/pdf",
    }]))

    assert anexos == [{
        "nome": "resultado.pdf",
        "caminho": "7/11/resultado.pdf",
        "tipo": "application/pdf",
    }]


def test_link_assinado_aceita_chave_camel_case_do_supabase():
    database = Database.__new__(Database)
    database.supabase = _Supabase()
    database.supabase_url = "https://projeto.supabase.co"
    database.consultorio_id = 7

    url = database.criar_link_anexo_interface("7/11/exame.pdf")

    assert url == (
        "https://projeto.supabase.co/storage/v1/object/sign/"
        "fichas-anexos/7/11/exame.pdf?token=teste"
    )


def test_link_assinado_recusa_anexo_de_outro_consultorio():
    database = Database.__new__(Database)
    database.supabase = _Supabase()
    database.supabase_url = "https://projeto.supabase.co"
    database.consultorio_id = 7

    assert database.criar_link_anexo_interface("8/11/exame.pdf") == ""


class _QueryFicha:
    def __init__(self, supabase, operacao="select", payload=None):
        self.supabase = supabase
        self.operacao = operacao
        self.payload = payload

    def select(self, _colunas):
        return self

    def update(self, payload):
        return _QueryFicha(self.supabase, "update", dict(payload))

    def insert(self, payload):
        return _QueryFicha(self.supabase, "insert", dict(payload))

    def eq(self, _coluna, _valor):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        if self.operacao == "select":
            return SimpleNamespace(data={"anexos": list(self.supabase.anexos)})
        if self.operacao == "update":
            self.supabase.atualizacao = dict(self.payload)
            self.supabase.anexos = list(self.payload["anexos"])
            return SimpleNamespace(data=[{"id": 9}])
        if self.operacao == "insert":
            self.supabase.insercao = dict(self.payload)
            return SimpleNamespace(data=[{"id": 10}])
        raise AssertionError(self.operacao)


class _BucketGravacao:
    def __init__(self):
        self.uploads = []
        self.removidos = []

    def upload(self, caminho, conteudo, opcoes):
        self.uploads.append((caminho, conteudo, opcoes))

    def remove(self, caminhos):
        self.removidos.extend(caminhos)


class _StorageGravacao:
    def __init__(self, bucket):
        self.bucket = bucket

    def from_(self, nome):
        assert nome == "fichas-anexos"
        return self.bucket


class _SupabaseGravacao:
    def __init__(self, anexos=None):
        self.anexos = list(anexos or [])
        self.atualizacao = None
        self.insercao = None
        self.bucket = _BucketGravacao()
        self.storage = _StorageGravacao(self.bucket)

    def table(self, nome):
        assert nome == "fichas_preenchidas"
        return _QueryFicha(self)


def _database_gravacao(anexos=None):
    database = Database.__new__(Database)
    database.supabase = _SupabaseGravacao(anexos)
    database.consultorio_id = 7
    database.obter_papel_atual = lambda: "profissional"
    return database


def test_edicao_persiste_remocao_e_apaga_objeto_antigo():
    antigo = {
        "nome": "antigo.pdf",
        "caminho": "7/11/antigo.pdf",
        "tipo": "application/pdf",
    }
    database = _database_gravacao([antigo])

    ficha_id = database.salvar_ficha_interface(
        9,
        11,
        "Ficha simples",
        {"queixa": "Sem alterações"},
        [],
        [],
    )

    assert ficha_id == 9
    assert database.supabase.atualizacao["anexos"] == []
    assert database.supabase.bucket.removidos == ["7/11/antigo.pdf"]


def test_novo_anexo_e_enviado_e_vinculado_a_ficha(tmp_path):
    arquivo = tmp_path / "exame.pdf"
    arquivo.write_bytes(b"%PDF-1.4 teste")
    database = _database_gravacao()

    ficha_id = database.salvar_ficha_interface(
        None,
        11,
        "Ficha simples",
        {"queixa": "Exame anexado"},
        [str(arquivo)],
        [],
    )

    assert ficha_id == 10
    assert len(database.supabase.bucket.uploads) == 1
    anexo = database.supabase.insercao["anexos"][0]
    assert anexo["nome"] == "exame.pdf"
    assert anexo["caminho"].startswith("7/11/")
    assert anexo["tipo"] == "application/pdf"
    assert anexo["tamanho"] == arquivo.stat().st_size


def test_anexo_acima_do_limite_exibe_erro_compreensivel(
    tmp_path, monkeypatch
):
    arquivo = tmp_path / "grande.pdf"
    arquivo.write_bytes(b"x")
    database = _database_gravacao()
    monkeypatch.setattr(
        "database.database.os.path.getsize",
        lambda _caminho: TAMANHO_MAXIMO_ANEXO_FICHA + 1,
    )

    with pytest.raises(ErroAnexoFicha, match="limite de 15 MB"):
        database.salvar_ficha_interface(
            None,
            11,
            "Ficha simples",
            {},
            [str(arquivo)],
            [],
        )

    assert database.supabase.bucket.uploads == []
