import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QScrollArea, QLineEdit
from PySide6.QtCore import Qt

from ui.screens.configuracoes import ConfiguracoesScreen, validar_senhas_backup
from ui.main_window import MainWindow
from ui.screens.pacientes import PacientesScreen, paciente_corresponde_busca
from ui.screens.home import HomeScreen, TabelaPacientesRecentes, MIME_PACIENTE_ID


class _DatabaseFake:
    supabase = None
    consultorio_id = 1

    def possui_recurso(self, _recurso):
        return False

    def obter_papel_atual(self):
        return "proprietario"

    def obter_configuracoes(self, _chaves):
        return {}

    def obter_nome_profissional(self):
        return "Profissional de teste"

    def obter_resumo_assinatura(self):
        return {"plano": "equipe", "status": "ativa", "max_usuarios": 5}


class _JanelaFake:
    def __init__(self):
        self.db = _DatabaseFake()


class _DatabaseComRetorno(_DatabaseFake):
    def __init__(self):
        self.retorno = {
            "id": 10,
            "data_prevista": None,
            "motivo": "Retorno após consulta",
            "status": "Pendente",
        }
        self.data_definida = None
        self.status_definido = None

    def listar_retornos_paciente(self, _paciente_id):
        return [dict(self.retorno)]

    def definir_data_retorno(self, retorno_id, data_prevista):
        self.data_definida = (retorno_id, data_prevista)
        self.retorno["data_prevista"] = data_prevista
        return True

    def atualizar_status_retorno(self, retorno_id, status):
        self.status_definido = (retorno_id, status)
        self.retorno["status"] = status
        return True


class _JanelaRetornoFake:
    def __init__(self):
        self.retorno_agendado = None

    def agendar_retorno_do_painel(self, retorno):
        self.retorno_agendado = dict(retorno)


class _ConsultaPastasFake:
    def __init__(self, supabase):
        self.supabase = supabase

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def is_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.supabase.respostas.pop(0))


class _SupabasePastasFake:
    def __init__(self):
        self.respostas = [
            [{"nome": "Geral", "cor": "#0284c7"}],
            [{"pasta": "Neurologia"}, {"pasta": "neurologia"}, {"pasta": None}],
        ]

    def table(self, _nome):
        return _ConsultaPastasFake(self)


def _app():
    return QApplication.instance() or QApplication([])


def test_formulario_pacientes_rola_sem_alargar_ao_redimensionar():
    app = _app()
    tela = PacientesScreen(_DatabaseFake())

    for largura, altura, compacto in (
        (700, 600, True),
        (1126, 768, False),
        (824, 768, True),
        (700, 600, True),
    ):
        tela.resize(largura, altura)
        tela.show()
        app.processEvents()

        assert tela._filtros_compactos is compacto
        tela._ajustar_altura_formulario()
        assert tela.right_container.minimumHeight() >= tela.right_layout.sizeHint().height()
        assert tela.right_container.width() <= tela.right_scroll.viewport().width()
        assert tela.right_container.height() >= tela.right_scroll.viewport().height()
        if altura <= 768:
            assert tela.right_scroll.verticalScrollBar().maximum() > 0

    tela.close()


def test_configuracoes_usa_rolagem_vertical_em_altura_reduzida():
    app = _app()
    tela = ConfiguracoesScreen(_JanelaFake())
    area = tela.findChild(QScrollArea, "ConfiguracoesScroll")

    for largura, altura in ((824, 600), (1126, 900), (824, 600)):
        tela.resize(largura, altura)
        tela.show()
        app.processEvents()
        assert area.widget().height() >= area.viewport().height()

    assert area.verticalScrollBar().maximum() > 0
    tela.close()


def test_configuracoes_mostra_e_oculta_as_duas_senhas_do_backup():
    tela = ConfiguracoesScreen(_JanelaFake())
    tela.input_backup_senha.setText("segredo")
    tela.input_backup_senha_confirmacao.setText("segredo")

    tela.chk_mostrar_senhas_backup.setChecked(True)
    assert tela.input_backup_senha.echoMode() == QLineEdit.EchoMode.Normal
    assert tela.input_backup_senha_confirmacao.echoMode() == QLineEdit.EchoMode.Normal

    tela.chk_mostrar_senhas_backup.setChecked(False)
    assert tela.input_backup_senha.echoMode() == QLineEdit.EchoMode.Password
    assert tela.input_backup_senha_confirmacao.echoMode() == QLineEdit.EchoMode.Password
    tela.close()


def test_tabela_de_recentes_transporta_o_id_do_paciente():
    tabela = TabelaPacientesRecentes()
    tabela.setColumnCount(2)
    from PySide6.QtWidgets import QTableWidgetItem
    item = QTableWidgetItem("Arthur")
    item.setData(Qt.ItemDataRole.UserRole, 17)

    mime = tabela.mimeData([item])

    assert mime.hasFormat(MIME_PACIENTE_ID)
    assert bytes(mime.data(MIME_PACIENTE_ID)).decode("utf-8") == "17"
    tabela.close()


def test_retorno_pendente_e_selecionado_e_libera_as_acoes():
    app = _app()
    tela = PacientesScreen(_DatabaseComRetorno())
    tela.carregar_retornos_paciente(1)
    app.processEvents()

    assert tela.list_retornos.currentItem() is not None
    assert tela.btn_agendar_retorno.isEnabled()
    assert tela.btn_nao_retorno.isEnabled()
    assert tela._retorno_selecionado()["id"] == 10
    tela.close()


def test_clique_em_agendar_retorno_salva_data_e_abre_agenda():
    app = _app()
    database = _DatabaseComRetorno()
    janela = _JanelaRetornoFake()
    tela = PacientesScreen(database)
    tela.window_principal = janela
    tela.id_em_edicao = 1
    tela.input_nome.setText("Arthur")
    tela.carregar_retornos_paciente(1)
    tela._escolher_data_retorno = lambda: "2026-08-22"

    tela.btn_agendar_retorno.click()
    app.processEvents()

    assert database.data_definida == (10, "2026-08-22")
    assert janela.retorno_agendado["id"] == 10
    assert janela.retorno_agendado["data_prevista"] == "2026-08-22"
    tela.close()


def test_clique_em_nao_retornara_atualiza_o_status(monkeypatch):
    app = _app()
    database = _DatabaseComRetorno()
    tela = PacientesScreen(database)
    tela.id_em_edicao = 1
    tela.carregar_retornos_paciente(1)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    tela.btn_nao_retorno.click()
    app.processEvents()

    assert database.status_definido == (10, "Não retornou")
    assert not tela.btn_agendar_retorno.isEnabled()
    assert not tela.btn_nao_retorno.isEnabled()
    tela.close()


def test_busca_de_paciente_exige_inicio_do_nome_e_ignora_acentos():
    pacientes = [
        {"nome": "Arthur", "telefone": "81991214670", "cpf": "", "rg": ""},
        {"nome": "Clara", "telefone": "81900000000", "cpf": "", "rg": ""},
        {"nome": "Cauã", "telefone": "81911111111", "cpf": "", "rg": ""},
    ]

    assert paciente_corresponde_busca(pacientes[0], "a")
    assert not paciente_corresponde_busca(pacientes[1], "a")
    assert paciente_corresponde_busca(pacientes[2], "caua")
    assert paciente_corresponde_busca(pacientes[0], "99121")


def test_pasta_vazia_nao_herda_a_selecao_do_paciente_anterior():
    tela = PacientesScreen(_DatabaseFake())
    tela.atualizar_combobox_pastas(["Geral", "Ortomolecular"])

    tela._selecionar_pasta_formulario("Ortomolecular")
    assert tela.input_pasta.currentText() == "Ortomolecular"

    tela._selecionar_pasta_formulario("")
    assert tela.input_pasta.currentText() == "Geral"

    tela._selecionar_pasta_formulario("Neurologia")
    assert tela.input_pasta.currentText() == "Neurologia"
    tela.close()


def test_pasta_aberta_vira_padrao_do_novo_paciente():
    tela = PacientesScreen(_DatabaseFake())
    tela.atualizar_combobox_pastas(["Geral", "Ortomolecular"])

    tela.filtrar_por_pasta_externo("Ortomolecular")
    assert tela.input_pasta.currentText() == "Ortomolecular"

    tela.limpar_formulario()
    assert tela.input_pasta.currentText() == "Ortomolecular"
    tela.close()


def test_geral_conta_todos_sem_duplicar_registros():
    pacientes = [
        {"id": 1, "pasta": "Geral"},
        {"id": 2, "pasta": "Ortomolecular"},
        {"id": 3, "pasta": "Neurologia"},
    ]

    assert HomeScreen._contar_pacientes_na_lista(pacientes, "Geral") == 3
    assert HomeScreen._contar_pacientes_na_lista(pacientes, "Ortomolecular") == 1


def test_senha_do_backup_exige_confirmacao_igual():
    assert validar_senhas_backup("segredo", "segredo") == (True, "")
    assert validar_senhas_backup("segredo", "")[0] is False
    assert validar_senhas_backup("segredo", "diferente")[0] is False


def test_pasta_existente_no_paciente_e_recuperada_para_a_home():
    objeto = SimpleNamespace(
        db=SimpleNamespace(supabase=_SupabasePastasFake(), consultorio_id=1),
        pastas_cores={},
    )

    pastas = MainWindow.carregar_pastas_sqlite(objeto)

    assert pastas == ["Geral", "Neurologia"]
    assert objeto.pastas_cores["Neurologia"] == "#0284c7"
