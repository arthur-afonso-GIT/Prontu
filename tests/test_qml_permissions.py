from pathlib import Path

from ui.qml_controller import QmlAppController


ROOT = Path(__file__).resolve().parents[1]


class _DatabaseRoleFake:
    def __init__(self, papel):
        self._papel = papel

    def obter_papel_atual(self):
        return self._papel

    def obter_plano_atual(self):
        return "equipe"


def _controller(papel):
    return QmlAppController(
        _DatabaseRoleFake(papel),
        ROOT / "ui" / "assets" / "prontu_logo.png",
    )


def test_proprietario_pode_acessar_equipe_e_fichas():
    controller = _controller("proprietario")
    assert controller.podeGerenciarEquipe is True
    assert controller.podeVerFichas is True

    controller.navegar("equipe")
    assert controller.paginaAtual == "equipe"


def test_profissional_acessa_fichas_mas_nao_equipe():
    controller = _controller("profissional")
    assert controller.podeGerenciarEquipe is False
    assert controller.podeVerFichas is True

    controller.navegar("equipe")
    assert controller.paginaAtual == "home"
    controller.navegar("fichas")
    assert controller.paginaAtual == "fichas"


def test_secretaria_nao_acessa_equipe_nem_fichas():
    controller = _controller("secretaria")
    assert controller.podeGerenciarEquipe is False
    assert controller.podeVerFichas is False

    controller.navegar("fichas")
    assert controller.paginaAtual == "home"
    controller.navegar("equipe")
    assert controller.paginaAtual == "home"
