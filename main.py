"""Ponto de entrada oficial do Prontu.

A interface do aplicativo é construída em QML. Banco de dados, segurança e
regras de negócio continuam em Python para manter uma única arquitetura.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# O estilo precisa ser definido antes da criação do QApplication.
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from dotenv import load_dotenv
from PySide6.QtCore import QEventLoop, QSize, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from database import Database
from ui.qml_agenda_controller import AgendaController
from ui.qml_configuracoes_controller import ConfiguracoesController
from ui.qml_controller import PatientsController, QmlAppController
from ui.qml_equipe_controller import EquipeController
from ui.qml_fichas_controller import FichasController
from ui.qml_financeiro_controller import FinanceiroController
from ui.qml_home_controller import HomeController
from ui.qml_login_controller import LoginController
from utils.diagnostics import configure_diagnostics


SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
QML_DIR = RESOURCE_DIR / "ui" / "qml"
LOGO_PATH = RESOURCE_DIR / "ui" / "assets" / "prontu_logo.png"


def _ler_versao() -> str:
    for caminho in (RESOURCE_DIR / "VERSION", SOURCE_DIR / "VERSION"):
        try:
            versao = caminho.read_text(encoding="utf-8").strip()
            if versao:
                return versao
        except OSError:
            continue
    return "desconhecida"


APP_VERSION = _ler_versao()
logger = configure_diagnostics(APP_VERSION)


def _carregar_configuracao() -> None:
    """Carrega somente configurações públicas no instalador.

    O arquivo ``.env`` é usado apenas durante o desenvolvimento e nunca é
    empacotado. Segredos permanecem no Supabase.
    """
    publica = RESOURCE_DIR / "prontu_public.env"
    desenvolvimento = SOURCE_DIR / ".env"
    if publica.is_file():
        load_dotenv(publica, override=False, encoding="utf-8-sig")
    if desenvolvimento.is_file() and not getattr(sys, "frozen", False):
        load_dotenv(desenvolvimento, override=True, encoding="utf-8-sig")


def _recursos_ausentes() -> list[str]:
    obrigatorios = (
        QML_DIR / "Main.qml",
        QML_DIR / "Login.qml",
        LOGO_PATH,
    )
    return [str(caminho) for caminho in obrigatorios if not caminho.is_file()]


def _ajustar_janela_ao_monitor(janela, app: QApplication) -> None:
    """Mantém a janela utilizável em notebooks, DPI alto e monitores menores."""
    tela = janela.screen() or app.primaryScreen()
    if tela is None:
        return

    area = tela.availableGeometry()
    margem = 24
    largura_disponivel = max(1, area.width() - margem)
    altura_disponivel = max(1, area.height() - margem)
    largura_minima = min(720, largura_disponivel)
    altura_minima = min(500, altura_disponivel)

    janela.setMinimumSize(QSize(largura_minima, altura_minima))
    janela.resize(
        min(1280, largura_disponivel),
        min(800, altura_disponivel),
    )

    geometria = janela.frameGeometry()
    geometria.moveCenter(area.center())
    janela.setPosition(geometria.topLeft())


def validar_instalacao() -> int:
    """Validação rápida usada depois de empacotar o aplicativo."""
    ausentes = _recursos_ausentes()
    if ausentes:
        logger.error("Recursos obrigatórios ausentes: %s", ", ".join(ausentes))
        return 1
    logger.info("Validação do pacote concluída com sucesso")
    return 0


def _executar_login_qml(app: QApplication, banco: Database) -> bool:
    controller = LoginController(banco)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("loginController", controller)
    engine.rootContext().setContextProperty(
        "appLogoUrl", QUrl.fromLocalFile(str(LOGO_PATH))
    )

    estado = {"autenticado": False}
    espera = QEventLoop()

    def autenticado() -> None:
        estado["autenticado"] = True
        espera.quit()

    controller.autenticado.connect(autenticado)
    controller.cancelado.connect(espera.quit)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Login.qml")))
    if not engine.rootObjects():
        logger.error("Não foi possível carregar a tela de acesso")
        return False

    encerrava_ultima_janela = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    espera.exec()
    app.setQuitOnLastWindowClosed(encerrava_ultima_janela)

    janela = engine.rootObjects()[0] if engine.rootObjects() else None
    if janela and janela.isVisible():
        janela.close()
    return estado["autenticado"] and banco.esta_autenticado()


def executar_aplicativo() -> int:
    _carregar_configuracao()

    if "--validate-installation" in sys.argv:
        return validar_instalacao()

    ausentes = _recursos_ausentes()
    if ausentes:
        logger.error("Instalação incompleta. Recursos ausentes: %s", ", ".join(ausentes))
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("Prontu")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Prontu")
    app.setQuitOnLastWindowClosed(True)
    app.setWindowIcon(QIcon(str(LOGO_PATH)))

    try:
        banco = Database()
    except Exception:
        logger.exception("Falha ao inicializar banco e sessão")
        return 1

    if not banco.esta_autenticado() and not _executar_login_qml(app, banco):
        return 0

    controller = QmlAppController(banco, LOGO_PATH)
    controllers = {
        "appController": controller,
        "patientsController": PatientsController(banco),
        "agendaController": AgendaController(banco),
        "fichasController": FichasController(banco),
        "financeiroController": FinanceiroController(banco),
        "equipeController": EquipeController(banco),
        "configuracoesController": ConfiguracoesController(banco),
        "homeController": HomeController(banco),
    }

    engine = QQmlApplicationEngine()
    contexto = engine.rootContext()
    for nome, instancia in controllers.items():
        contexto.setContextProperty(nome, instancia)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        logger.error("Não foi possível carregar a janela principal")
        return 1

    _ajustar_janela_ao_monitor(engine.rootObjects()[0], app)

    logger.info("Aplicativo iniciado | versão=%s", APP_VERSION)
    codigo_saida = app.exec()

    # Desmonta a árvore QML enquanto os controladores Python ainda existem.
    for janela in list(engine.rootObjects()):
        janela.setVisible(False)
        janela.deleteLater()
    app.processEvents()
    engine.clearComponentCache()
    logger.info("Aplicativo encerrado | código=%s", codigo_saida)
    return codigo_saida


# Compatibilidade com chamadas antigas sem manter uma segunda interface.
inicializar_sistema = executar_aplicativo


if __name__ == "__main__":
    try:
        raise SystemExit(executar_aplicativo())
    except SystemExit:
        raise
    except Exception:
        logging.getLogger("prontu").exception("Falha inesperada na inicialização")
        raise
