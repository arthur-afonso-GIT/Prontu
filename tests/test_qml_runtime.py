from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QObject, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from ui.qml_controller import PatientsController, QmlAppController
from ui.qml_agenda_controller import AgendaController
from ui.qml_fichas_controller import FichasController
from ui.qml_financeiro_controller import FinanceiroController
from ui.qml_equipe_controller import EquipeController
from ui.qml_configuracoes_controller import ConfiguracoesController
from ui.qml_home_controller import HomeController
from ui.qml_login_controller import LoginController


ROOT = Path(__file__).resolve().parents[1]


class _Session:
    _session = {"nome_clinica": "Clínica Teste"}


class _DatabaseFake:
    session_manager = _Session()
    supabase = object()

    def obter_papel_atual(self):
        return "proprietario"

    def obter_plano_atual(self):
        return "equipe"

    def listar_pacientes_interface(self):
        return [{
            "id": 1,
            "nome": "Arthur",
            "telefone": "81999990000",
            "convenio": "PARTICULAR",
            "pasta": "Geral",
        }]

    def listar_pastas_interface(self):
        return ["Geral"]

    def listar_home_interface(self):
        return {
            "data_hoje": "28/07/2026",
            "pacientes": [{
                "id": 1,
                "nome": "Arthur",
                "pasta": "Geral",
            }],
            "pastas": [{"nome": "Geral", "cor": "#0284c7"}],
            "agenda": [{
                "data": "28/07/2026",
                "horario": "08:00",
                "paciente": "Arthur",
                "status": "Confirmado",
                "tipo_bloco": "principal",
            }],
            "retornos": [{
                "id": 7,
                "paciente_id": 1,
                "paciente_nome": "Arthur",
                "data_prevista": "2026-07-30",
                "motivo": "Acompanhamento",
            }],
        }

    def criar_pasta_interface(self, nome, cor):
        return bool(nome and cor)

    def renomear_pasta_interface(self, nome_atual, nome_novo):
        return bool(nome_atual and nome_novo)

    def excluir_pasta_interface(self, nome):
        return nome.casefold() != "geral"

    def atualizar_cor_pasta_interface(self, nome, cor):
        return bool(nome and cor)

    def mover_paciente_pasta_interface(self, paciente_id, pasta):
        return bool(paciente_id and pasta)

    def obter_paciente_interface(self, paciente_id):
        return {"id": paciente_id, "nome": "Arthur", "pasta": "Geral"}

    def listar_agenda_interface(self, data_consulta):
        return [{
            "data": data_consulta,
            "horario": "08:00",
            "paciente": "ARTHUR",
            "status": "🕒 Agendado",
            "procedimento": "Retorno",
            "duracao_txt": "30 minutos",
            "observacao": "",
            "tipo_bloco": "principal",
            "slots_vinculados": ["08:00"],
            "retorno_id": None,
        }]

    def listar_agenda_periodo_interface(self, datas_consulta):
        if not datas_consulta:
            return []
        return self.listar_agenda_interface(datas_consulta[0])

    def buscar_nomes_pacientes(self):
        return ["Arthur"]

    def listar_tipos_consulta_interface(self):
        return ["Primeira Consulta / Avaliação", "Retorno"]

    def listar_pacientes_fichas_interface(self):
        return [{"id": 1, "nome": "Arthur"}]

    def listar_modelos_fichas_interface(self):
        return [{
            "nome": "Ficha simples",
            "estrutura": [{
                "tipo": "texto_longo",
                "id": "queixa",
                "label": "Queixa principal",
                "obrigatorio": True,
            }],
        }]

    def listar_historico_fichas_interface(self, paciente_id):
        return [{
            "id": 9,
            "modelo_nome": "Ficha simples",
            "data_atendimento": "28/07/2026 18:00",
            "total_anexos": 0,
        }]

    def obter_ficha_interface(self, ficha_id):
        return {
            "id": ficha_id,
            "paciente_id": 1,
            "modelo_nome": "Ficha simples",
            "dados_respostas": {"queixa": "Acompanhamento"},
            "estrutura": [{
                "tipo": "texto_longo",
                "id": "queixa",
                "label": "Queixa principal",
                "obrigatorio": True,
            }],
            "anexos": [{
                "nome": "exame.pdf",
                "caminho": "1/9/exame.pdf",
            }],
        }

    def salvar_modelo_ficha_interface(self, nome, estrutura):
        return bool(nome and estrutura)

    def excluir_modelo_ficha_interface(self, nome):
        return nome != "Ficha de Consulta Geral (Padrão)"

    def criar_link_anexo_interface(self, caminho):
        return "https://example.invalid/anexo"

    def listar_financeiro_interface(self):
        return {
            "agenda": [{
                "data": "28/07/2026",
                "horario": "10:00",
                "paciente": "Arthur",
                "procedimento": "Consulta",
                "status": "Realizada",
            }],
            "pagamentos": [],
        }

    def salvar_pagamento_interface(self, payload):
        return True

    def possui_recurso(self, recurso):
        return recurso == "equipe"

    def listar_equipe(self):
        return {
            "max_usuarios": 5,
            "membros": [{
                "id": "owner-1",
                "nome": "Arthur",
                "email": "arthur@clinica.com",
                "papel": "proprietario",
            }],
            "convites": [{
                "id": "invite-1",
                "nome": "Maria",
                "email": "maria@clinica.com",
                "papel": "profissional",
                "expira_em": "2026-08-04T12:00:00+00:00",
            }],
        }

    def criar_convite_equipe(self, nome, email, papel):
        return {"codigo": "PRONTU-TESTE", "email": email}

    def alterar_papel_equipe(self, membro_id, papel):
        return True

    def revogar_acesso_equipe(self, tipo, identificador):
        return True

    def renovar_convite_equipe(self, convite_id):
        return {"codigo": "PRONTU-NOVO"}

    def obter_resumo_assinatura(self):
        return {
            "plano": "equipe",
            "status": "ativa",
            "max_usuarios": 5,
        }

    def obter_nome_profissional(self):
        return "Arthur"

    def obter_configuracoes(self, chaves):
        return {}

    def salvar_nome_profissional(self, nome):
        return bool(nome)

    def salvar_configuracao(self, chave, valor):
        return bool(chave)

    def listar_eventos_auditoria(self):
        return [{
            "acao": "INSERT",
            "entidade": "pacientes",
            "registro_id": 1,
            "criado_em": "2026-07-28T12:00:00+00:00",
        }]

    def listar_lembretes_whatsapp_interface(self):
        return {"lembretes": [], "resumo": "", "franquia": ""}

    def desativar_dispositivo(self):
        return None


def test_tela_pacientes_qml_carrega_com_modelo():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    patients_controller = PatientsController(banco)
    agenda_controller = AgendaController(banco)
    fichas_controller = FichasController(banco)
    app_controller.navegar("pacientes")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty(
        "patientsController", patients_controller
    )
    engine.rootContext().setContextProperty("agendaController", agenda_controller)
    engine.rootContext().setContextProperty("fichasController", fichas_controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert patients_controller.total == 1


def test_tela_login_qml_carrega_os_tres_fluxos():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    login_controller = LoginController(banco)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(
        "loginController", login_controller
    )
    engine.rootContext().setContextProperty(
        "appLogoUrl",
        QUrl.fromLocalFile(str(ROOT / "ui" / "assets" / "prontu_logo.png")),
    )
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Login.qml")))

    espera = QEventLoop()
    QTimer.singleShot(300, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert login_controller.conexaoDisponivel is True
    engine.rootObjects()[0].width = 760
    engine.rootObjects()[0].height = 560
    engine.rootObjects()[0].close()


def test_tela_home_qml_carrega_resumo_e_listas():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    home_controller = HomeController(banco)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty("homeController", home_controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(700, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert home_controller.totalPacientes == 1
    assert home_controller.totalConsultas == 1
    assert home_controller.totalRetornos == 1
    assert len(home_controller.pastas) == 1


def test_tela_agenda_qml_carrega_com_consulta():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    patients_controller = PatientsController(banco)
    agenda_controller = AgendaController(banco)
    fichas_controller = FichasController(banco)
    app_controller.navegar("agenda")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty(
        "patientsController", patients_controller
    )
    engine.rootContext().setContextProperty("agendaController", agenda_controller)
    engine.rootContext().setContextProperty("fichasController", fichas_controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(600, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert agenda_controller.totalConsultas == 1


def test_agenda_qml_oferece_visoes_diaria_semanal_e_mensal():
    app = QApplication.instance() or QApplication([])
    agenda_controller = AgendaController(_DatabaseFake())

    agenda_controller.carregar()
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert agenda_controller.modo == "dia"

    agenda_controller.definirModo("semana")
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert agenda_controller.modo == "semana"
    assert len(agenda_controller.diasSemana) == 7
    assert "Semana de" in agenda_controller.tituloPeriodo

    agenda_controller.definirModo("mes")
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert agenda_controller.modo == "mes"
    assert len(agenda_controller.diasMes) == 42
    assert " de " in agenda_controller.tituloPeriodo


def test_tela_fichas_qml_carrega_modelo_dinamico():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    patients_controller = PatientsController(banco)
    agenda_controller = AgendaController(banco)
    fichas_controller = FichasController(banco)
    app_controller.navegar("fichas")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty(
        "patientsController", patients_controller
    )
    engine.rootContext().setContextProperty("agendaController", agenda_controller)
    engine.rootContext().setContextProperty("fichasController", fichas_controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(600, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert fichas_controller.nomesModelos == ["Ficha simples"]
    assert fichas_controller.camposModelo[0]["id"] == "queixa"
    assert fichas_controller.pacienteSelecionadoId == 1
    assert fichas_controller.totalHistorico == 1


def test_fichas_qml_carrega_anexos_do_historico_para_visualizacao():
    app = QApplication.instance() or QApplication([])
    controller = FichasController(_DatabaseFake())
    titulos = []
    controller.visualizacaoAnexosPronta.connect(titulos.append)

    controller.visualizarAnexosFicha(9)
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert titulos == ["Ficha simples"]
    assert controller.anexosVisualizacao == [{
        "nome": "exame.pdf",
        "caminho": "1/9/exame.pdf",
    }]


def test_fichas_qml_permite_remover_anexo_existente_antes_de_salvar():
    app = QApplication.instance() or QApplication([])
    controller = FichasController(_DatabaseFake())

    controller.abrirFicha(9)
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert controller.anexos == [{
        "nome": "exame.pdf",
        "local": False,
        "caminho": "1/9/exame.pdf",
    }]

    controller.removerAnexo(0)

    assert controller.anexos == []


def test_pacientes_qml_carrega_historico_e_visualiza_ficha_com_anexos():
    app = QApplication.instance() or QApplication([])
    controller = PatientsController(_DatabaseFake())
    titulos = []
    controller.fichaVisualizacaoPronta.connect(titulos.append)

    controller.selecionar(1)
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert controller.pacienteSelecionado["id"] == 1
    assert controller.totalHistorico == 1

    controller.visualizarFicha(9)
    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()

    assert titulos == ["Ficha simples"]
    assert controller.fichaVisualizacaoDetalhes == [{
        "label": "Queixa principal",
        "valor": "Acompanhamento",
        "secao": False,
    }]
    assert controller.fichaVisualizacaoAnexos == [{
        "nome": "exame.pdf",
        "caminho": "1/9/exame.pdf",
    }]


def test_tela_financeiro_qml_carrega_consulta_sem_pagamento():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    patients_controller = PatientsController(banco)
    agenda_controller = AgendaController(banco)
    fichas_controller = FichasController(banco)
    financeiro_controller = FinanceiroController(banco)
    app_controller.navegar("financeiro")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty(
        "patientsController", patients_controller
    )
    engine.rootContext().setContextProperty("agendaController", agenda_controller)
    engine.rootContext().setContextProperty("fichasController", fichas_controller)
    engine.rootContext().setContextProperty(
        "financeiroController", financeiro_controller
    )
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(600, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert financeiro_controller.total == 1
    assert financeiro_controller.consultasAgenda == 1


def test_tela_equipe_qml_carrega_membros_e_convites():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    patients_controller = PatientsController(banco)
    agenda_controller = AgendaController(banco)
    fichas_controller = FichasController(banco)
    financeiro_controller = FinanceiroController(banco)
    equipe_controller = EquipeController(banco)
    app_controller.navegar("equipe")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty(
        "patientsController", patients_controller
    )
    engine.rootContext().setContextProperty("agendaController", agenda_controller)
    engine.rootContext().setContextProperty("fichasController", fichas_controller)
    engine.rootContext().setContextProperty(
        "financeiroController", financeiro_controller
    )
    engine.rootContext().setContextProperty("equipeController", equipe_controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(600, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    assert equipe_controller.totalMembros == 1
    assert equipe_controller.totalConvites == 1
    assert equipe_controller.disponiveis == 3


def test_tela_configuracoes_qml_carrega_perfil_e_plano():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    patients_controller = PatientsController(banco)
    agenda_controller = AgendaController(banco)
    fichas_controller = FichasController(banco)
    financeiro_controller = FinanceiroController(banco)
    equipe_controller = EquipeController(banco)
    configuracoes_controller = ConfiguracoesController(banco)
    app_controller.navegar("configuracoes")

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.rootContext().setContextProperty(
        "patientsController", patients_controller
    )
    engine.rootContext().setContextProperty("agendaController", agenda_controller)
    engine.rootContext().setContextProperty("fichasController", fichas_controller)
    engine.rootContext().setContextProperty(
        "financeiroController", financeiro_controller
    )
    engine.rootContext().setContextProperty("equipeController", equipe_controller)
    engine.rootContext().setContextProperty(
        "configuracoesController", configuracoes_controller
    )
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(700, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    pagina = engine.rootObjects()[0].findChild(
        QObject, "configuracoesPage"
    )
    assert pagina is not None
    assert configuracoes_controller.papelTexto == "Proprietário da clínica"


@pytest.mark.parametrize("pagina", [
    "home",
    "pacientes",
    "agenda",
    "fichas",
    "financeiro",
    "equipe",
    "configuracoes",
])
@pytest.mark.parametrize("tamanho", [(900, 620), (1440, 900)])
def test_todas_as_paginas_qml_abrem_em_resolucoes_suportadas(
    pagina, tamanho
):
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    controllers = {
        "homeController": HomeController(banco),
        "patientsController": PatientsController(banco),
        "agendaController": AgendaController(banco),
        "fichasController": FichasController(banco),
        "financeiroController": FinanceiroController(banco),
        "equipeController": EquipeController(banco),
        "configuracoesController": ConfiguracoesController(banco),
    }
    app_controller.navegar(pagina)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(
        "appController", app_controller
    )
    for nome, controller in controllers.items():
        engine.rootContext().setContextProperty(nome, controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(450, espera.quit)
    espera.exec()

    assert len(engine.rootObjects()) == 1
    janela = engine.rootObjects()[0]
    janela.width, janela.height = tamanho
    reajuste = QEventLoop()
    QTimer.singleShot(100, reajuste.quit)
    reajuste.exec()
    assert janela.width >= 900
    assert janela.height >= 620
    assert app_controller.paginaAtual == pagina
    janela.close()


def test_navegacao_completa_qml_troca_todas_as_telas_na_mesma_sessao():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    controllers = {
        "homeController": HomeController(banco),
        "patientsController": PatientsController(banco),
        "agendaController": AgendaController(banco),
        "fichasController": FichasController(banco),
        "financeiroController": FinanceiroController(banco),
        "equipeController": EquipeController(banco),
        "configuracoesController": ConfiguracoesController(banco),
    }
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(
        "appController", app_controller
    )
    for nome, controller in controllers.items():
        engine.rootContext().setContextProperty(nome, controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))
    assert len(engine.rootObjects()) == 1

    for pagina in [
        "pacientes",
        "agenda",
        "fichas",
        "financeiro",
        "equipe",
        "configuracoes",
        "home",
    ]:
        app_controller.navegar(pagina)
        espera = QEventLoop()
        QTimer.singleShot(220, espera.quit)
        espera.exec()
        assert app_controller.paginaAtual == pagina

    engine.rootObjects()[0].close()


def test_encerramento_qml_nao_le_controladores_ja_desmontados():
    app = QApplication.instance() or QApplication([])
    banco = _DatabaseFake()
    app_controller = QmlAppController(
        banco, ROOT / "ui" / "assets" / "prontu_logo.png"
    )
    controllers = {
        "homeController": HomeController(banco),
        "patientsController": PatientsController(banco),
        "agendaController": AgendaController(banco),
        "fichasController": FichasController(banco),
        "financeiroController": FinanceiroController(banco),
        "equipeController": EquipeController(banco),
        "configuracoesController": ConfiguracoesController(banco),
    }
    app_controller.navegar("configuracoes")

    avisos = []
    engine = QQmlApplicationEngine()
    engine.warnings.connect(
        lambda lista: avisos.extend(item.toString() for item in lista)
    )
    contexto = engine.rootContext()
    contexto.setContextProperty("appController", app_controller)
    for nome, controller in controllers.items():
        contexto.setContextProperty(nome, controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "ui" / "qml" / "Main.qml")))

    espera = QEventLoop()
    QTimer.singleShot(500, espera.quit)
    espera.exec()
    assert len(engine.rootObjects()) == 1

    contexto.setContextProperty("configuracoesController", None)
    contexto.setContextProperty("appController", None)
    contexto.setContextProperty("homeController", None)
    desmontagem = QEventLoop()
    QTimer.singleShot(150, desmontagem.quit)
    desmontagem.exec()

    mensagens = "\n".join(avisos)
    assert "Cannot read property" not in mensagens
    assert "Cannot read properties" not in mensagens
    assert "Binding loop" not in mensagens
    engine.rootObjects()[0].close()
