from types import SimpleNamespace

from database.database import Database


class _ConsultaConfiguracaoFake:
    def __init__(self, supabase, operacao="select", payload=None):
        self.supabase = supabase
        self.operacao = operacao
        self.payload = payload
        self.filtros = {}

    def select(self, *_args, **_kwargs):
        self.operacao = "select"
        return self

    def update(self, payload):
        self.operacao = "update"
        self.payload = payload
        return self

    def insert(self, payload):
        self.operacao = "insert"
        self.payload = payload
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def execute(self):
        chave = self.filtros.get("chave")
        if self.operacao == "select":
            if chave in self.supabase.valores:
                if self.payload == "valor":
                    return SimpleNamespace(data=[{"valor": self.supabase.valores[chave]}])
                return SimpleNamespace(data=[{"chave": chave}])
            return SimpleNamespace(data=[])
        if self.operacao == "update":
            self.supabase.valores[chave] = self.payload["valor"]
            return SimpleNamespace(data=[{"chave": chave, "valor": self.payload["valor"]}])
        if self.operacao == "insert":
            self.supabase.valores[self.payload["chave"]] = self.payload["valor"]
            return SimpleNamespace(data=[dict(self.payload)])
        raise AssertionError(f"Operação inesperada: {self.operacao}")


class _SupabaseConfiguracaoFake:
    def __init__(self):
        self.valores = {}

    def table(self, nome):
        assert nome == "configuracoes"
        consulta = _ConsultaConfiguracaoFake(self)
        original_select = consulta.select

        def select(colunas, **kwargs):
            consulta.payload = colunas
            return original_select(colunas, **kwargs)

        consulta.select = select
        return consulta


def _database_fake():
    db = Database.__new__(Database)
    db.supabase = _SupabaseConfiguracaoFake()
    db.consultorio_id = 1
    return db


def test_salvar_configuracao_insere_e_confirma_o_valor():
    db = _database_fake()

    assert db.salvar_configuracao("whatsapp_mensagem_manual", "Olá!") is True
    assert db.obter_configuracao("whatsapp_mensagem_manual") == "Olá!"


def test_salvar_configuracao_atualiza_sem_criar_duplicata():
    db = _database_fake()
    db.supabase.valores["whatsapp_mensagem_manual"] = "Mensagem antiga"

    assert db.salvar_configuracao("whatsapp_mensagem_manual", "Mensagem nova") is True
    assert db.supabase.valores == {
        "whatsapp_mensagem_manual": "Mensagem nova",
    }


def test_procedimentos_personalizados_podem_ser_criados_editados_e_excluidos():
    db = _database_fake()

    assert db.adicionar_tipo_consulta_interface("  Limpeza dental  ") is True
    assert db.adicionar_tipo_consulta_interface("limpeza DENTAL") is False
    assert "Limpeza dental" in db.listar_tipos_consulta_interface()

    assert db.editar_tipo_consulta_interface(
        "Limpeza dental", "Profilaxia"
    ) is True
    assert "Profilaxia" in db.listar_tipos_consulta_interface()
    assert "Limpeza dental" not in db.listar_tipos_consulta_interface()

    assert db.excluir_tipo_consulta_interface("profilaxia") is True
    assert db.listar_tipos_consulta_personalizados_interface() == []


def test_procedimentos_padrao_nao_podem_ser_renomeados_ou_excluidos():
    db = _database_fake()

    assert db.editar_tipo_consulta_interface("Retorno", "Revisão") is False
    assert db.excluir_tipo_consulta_interface("Retorno") is False
