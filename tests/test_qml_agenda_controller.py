from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from ui.qml_agenda_controller import AgendaController


class _AgendaReturnsFake:
    def __init__(self):
        self.data_retorno = None
        self.status_retorno = None

    def iniciar_consultas_no_horario_interface(self, data_consulta, horario):
        return 0

    def listar_agenda_periodo_interface(self, datas):
        return [{
            "data": datas[0],
            "horario": "08:00",
            "paciente": "ARTHUR",
            "status": "✅ Realizada",
            "procedimento": "Primeira Consulta / Avaliação",
            "duracao_txt": "30 minutos",
            "observacao": "",
            "tipo_bloco": "principal",
            "retorno_id": None,
        }]

    def buscar_nomes_pacientes(self):
        return ["Arthur"]

    def listar_tipos_consulta_interface(self):
        return ["Primeira Consulta / Avaliação", "Retorno"]

    def listar_retornos_pendentes(self):
        return [{
            "id": 44,
            "paciente_id": 1,
            "paciente_nome": "Arthur",
            "status": "Pendente",
        }]

    def definir_data_retorno(self, retorno_id, data_prevista):
        self.data_retorno = (retorno_id, data_prevista)
        return True

    def atualizar_status_retorno(self, retorno_id, status):
        self.status_retorno = (retorno_id, status)
        return True


def _esperar(milisegundos=300):
    espera = QEventLoop()
    QTimer.singleShot(milisegundos, espera.quit)
    espera.exec()


def test_consulta_realizada_expoe_decisao_de_retorno():
    QApplication.instance() or QApplication([])
    controller = AgendaController(_AgendaReturnsFake())

    controller.carregar()
    _esperar()

    role = next(
        numero
        for numero, nome in controller.model.roleNames().items()
        if bytes(nome) == b"pendingReturnDecisionId"
    )
    # 07:00, 07:30 e 08:00.
    assert controller.model.data(controller.model.index(2, 0), role) == 44


def test_agendar_ou_recusar_retorno_persiste_a_decisao():
    QApplication.instance() or QApplication([])
    banco = _AgendaReturnsFake()
    controller = AgendaController(banco)
    retornos_prontos = []
    controller.retornoProntoParaAgendar.connect(retornos_prontos.append)

    controller.prepararAgendamentoRetorno(44, "30/08/2099", "Arthur")
    _esperar()

    assert banco.data_retorno == (44, "2099-08-30")
    assert retornos_prontos[0]["id"] == 44

    controller.marcarSemRetorno(44)
    _esperar()

    assert banco.status_retorno == (44, "Não retornou")


class _AgendaConflictFake(_AgendaReturnsFake):
    def salvar_agendamento_interface(self, data_consulta, horario, dados):
        return {
            "sucesso": False,
            "motivo": "conflito",
            "data": data_consulta,
            "horarios": [horario, "08:30"],
        }


def test_conflito_de_horario_emite_aviso_especifico():
    QApplication.instance() or QApplication([])
    controller = AgendaController(_AgendaConflictFake())
    conflitos = []
    controller.conflitoHorario.connect(
        lambda data_consulta, horarios: conflitos.append(
            (data_consulta, horarios)
        )
    )
    controller.definirData("30/08/2099")
    _esperar()

    controller.criarConsulta({
        "paciente": "Arthur",
        "horario": "08:00",
        "duracao": "60 minutos",
        "procedimento": "Primeira Consulta / Avaliação",
        "status": "Agendado",
        "observacao": "",
    })
    _esperar()

    assert conflitos == [("30/08/2099", "08:00, 08:30")]
