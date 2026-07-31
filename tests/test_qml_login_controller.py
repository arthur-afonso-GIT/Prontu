from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from ui.qml_login_controller import LoginController


class _DatabaseLoginFake:
    supabase = object()

    def __init__(self):
        self.login = None
        self.convite = None
        self.chave = None
        self.proprietario = None
        self.desativado = False

    def entrar_com_email(self, email, senha, lembrar):
        self.login = (email, senha, lembrar)
        return {"consultorio_id": 1}

    def aceitar_convite_equipe(self, codigo, email, senha):
        self.convite = (codigo, email, senha)
        return {"consultorio_id": 1}

    def validar_chave_acesso(self, chave):
        self.chave = chave
        return {"consultorio_id": 1}

    def criar_login_proprietario(self, email, senha):
        self.proprietario = (email, senha)
        return True

    def solicitar_redefinicao_senha(self, email):
        return True

    def obter_ultimo_erro_funcao(self):
        return "Convite inválido."

    def desativar_dispositivo(self):
        self.desativado = True


def _esperar_sinal(objeto, sinal, acao):
    QApplication.instance() or QApplication([])
    espera = QEventLoop()
    sinal.connect(lambda *args: espera.quit())
    QTimer.singleShot(0, acao)
    QTimer.singleShot(1500, espera.quit)
    espera.exec()


def test_login_normaliza_email_e_preserva_opcao_lembrar():
    banco = _DatabaseLoginFake()
    controller = LoginController(banco)

    _esperar_sinal(
        controller,
        controller.autenticado,
        lambda: controller.entrar(
            "  Pessoa@Clinica.COM ", "12345678", False
        ),
    )

    assert banco.login == ("pessoa@clinica.com", "12345678", False)
    assert controller.estaAutenticado is True


def test_convite_normaliza_codigo_e_cria_sessao():
    banco = _DatabaseLoginFake()
    controller = LoginController(banco)

    _esperar_sinal(
        controller,
        controller.autenticado,
        lambda: controller.aceitarConvite(
            " prontu-teste ",
            " Pessoa@Clinica.COM ",
            "12345678",
            "12345678",
        ),
    )

    assert banco.convite == (
        "PRONTU-TESTE",
        "pessoa@clinica.com",
        "12345678",
    )
    assert controller.estaAutenticado is True


def test_cancelar_apos_validar_chave_remove_sessao_incompleta():
    banco = _DatabaseLoginFake()
    controller = LoginController(banco)

    _esperar_sinal(
        controller,
        controller.feedback,
        lambda: controller.ativarChave(" PRONTU-TESTE "),
    )
    assert controller.ativacaoPronta is True

    controller.cancelarCriacaoProprietario()

    assert banco.chave == "PRONTU-TESTE"
    assert banco.desativado is True
    assert controller.ativacaoPronta is False
