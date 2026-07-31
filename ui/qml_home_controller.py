"""Controlador assíncrono do Painel Principal QML."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot

from services.home_service import normalizar_nome_pasta, preparar_home


class HomeController(QObject):
    estadoAlterado = Signal()
    feedback = Signal(str, str)
    abrirPacienteSolicitado = Signal(int)
    abrirConsultaSolicitada = Signal(str, str)
    agendarRetornoSolicitado = Signal("QVariantMap")
    novaPessoaSolicitada = Signal(str)
    abrirPastaSolicitada = Signal(str)
    _resultado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-home"
        )
        self._ocupado = False
        self._dados: dict = {}
        self._resultado.connect(self._receber_resultado)

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(str, notify=estadoAlterado)
    def saudacao(self) -> str:
        return str(self._dados.get("saudacao") or "Olá")

    @Property(str, notify=estadoAlterado)
    def subtitulo(self) -> str:
        return str(self._dados.get("subtitulo") or "")

    @Property(int, notify=estadoAlterado)
    def totalPacientes(self) -> int:
        return int(self._dados.get("total_pacientes") or 0)

    @Property(int, notify=estadoAlterado)
    def totalConsultas(self) -> int:
        return int(self._dados.get("total_consultas") or 0)

    @Property(int, notify=estadoAlterado)
    def totalRetornos(self) -> int:
        return int(self._dados.get("total_retornos") or 0)

    @Property("QVariantList", notify=estadoAlterado)
    def pastas(self) -> list[dict]:
        return list(self._dados.get("pastas") or [])

    @Property("QVariantList", notify=estadoAlterado)
    def consultas(self) -> list[dict]:
        return list(self._dados.get("consultas") or [])

    @Property("QVariantList", notify=estadoAlterado)
    def retornos(self) -> list[dict]:
        return list(self._dados.get("retornos") or [])

    @Property("QVariantList", notify=estadoAlterado)
    def pacientesRecentes(self) -> list[dict]:
        return list(self._dados.get("pacientes_recentes") or [])

    def _definir_ocupado(self, valor: bool) -> None:
        if self._ocupado != valor:
            self._ocupado = valor
            self.estadoAlterado.emit()

    def _enviar(self, operacao: str, tarefa) -> None:
        if self._ocupado:
            return
        self._definir_ocupado(True)
        futuro = self._executor.submit(tarefa)

        def concluido(resultado: Future):
            try:
                self._resultado.emit((operacao, resultado.result()), None)
            except Exception as erro:
                self._resultado.emit((operacao, None), erro)

        futuro.add_done_callback(concluido)

    @Slot()
    def carregar(self) -> None:
        def tarefa():
            dados = self._database.listar_home_interface()
            nome = self._database.obter_nome_profissional()
            return preparar_home(dados, nome)

        self._enviar("carregar", tarefa)

    @Slot(int)
    def abrirPaciente(self, paciente_id: int) -> None:
        if paciente_id:
            self.abrirPacienteSolicitado.emit(int(paciente_id))

    @Slot(str, str)
    def abrirConsulta(self, data_consulta: str, horario: str) -> None:
        self.abrirConsultaSolicitada.emit(
            str(data_consulta or ""), str(horario or "")
        )

    @Slot("QVariantMap")
    def agendarRetorno(self, retorno: dict) -> None:
        if retorno and retorno.get("id"):
            self.agendarRetornoSolicitado.emit(dict(retorno))

    @Slot(str)
    def novoPaciente(self, pasta: str = "Geral") -> None:
        self.novaPessoaSolicitada.emit(
            normalizar_nome_pasta(pasta) or "Geral"
        )

    @Slot(str)
    def abrirPasta(self, pasta: str) -> None:
        self.abrirPastaSolicitada.emit(
            normalizar_nome_pasta(pasta) or "Geral"
        )

    @Slot(str, str)
    def criarPasta(self, nome: str, cor: str) -> None:
        nome = normalizar_nome_pasta(nome)
        if not nome:
            self.feedback.emit("warning", "Informe um nome para a pasta.")
            return
        self._enviar(
            "criar_pasta",
            lambda: self._database.criar_pasta_interface(nome, str(cor)),
        )

    @Slot(str, str)
    def renomearPasta(self, nome_atual: str, nome_novo: str) -> None:
        nome_novo = normalizar_nome_pasta(nome_novo)
        if not nome_novo:
            self.feedback.emit("warning", "Informe o novo nome da pasta.")
            return
        self._enviar(
            "renomear_pasta",
            lambda: self._database.renomear_pasta_interface(
                str(nome_atual), nome_novo
            ),
        )

    @Slot(str)
    def excluirPasta(self, nome: str) -> None:
        self._enviar(
            "excluir_pasta",
            lambda: self._database.excluir_pasta_interface(str(nome)),
        )

    @Slot(str, str)
    def mudarCorPasta(self, nome: str, cor: str) -> None:
        self._enviar(
            "mudar_cor",
            lambda: self._database.atualizar_cor_pasta_interface(
                str(nome), str(cor)
            ),
        )

    @Slot(int, str)
    def moverPaciente(self, paciente_id: int, pasta: str) -> None:
        if not paciente_id:
            return
        self._enviar(
            "mover_paciente",
            lambda: self._database.mover_paciente_pasta_interface(
                int(paciente_id), str(pasta)
            ),
        )

    @Slot(object, object)
    def _receber_resultado(self, pacote, erro) -> None:
        self._definir_ocupado(False)
        operacao, resultado = pacote or ("", None)
        if erro:
            self.feedback.emit(
                "error", "Não foi possível concluir esta operação."
            )
            return
        if operacao == "carregar":
            self._dados = dict(resultado or {})
            self.estadoAlterado.emit()
            return
        if not resultado:
            mensagens = {
                "criar_pasta": "Esta pasta já existe ou não pôde ser criada.",
                "renomear_pasta": "A pasta não pôde ser renomeada.",
                "excluir_pasta": "A pasta não pôde ser excluída.",
                "mudar_cor": "A cor da pasta não pôde ser salva.",
                "mover_paciente": "O paciente não pôde ser movido.",
            }
            self.feedback.emit(
                "error", mensagens.get(operacao, "A operação não foi concluída.")
            )
            return
        mensagens = {
            "criar_pasta": "Pasta criada.",
            "renomear_pasta": "Pasta renomeada.",
            "excluir_pasta": "Pasta excluída. Os pacientes foram movidos para Geral.",
            "mudar_cor": "Cor da pasta atualizada.",
            "mover_paciente": "Paciente movido para a pasta.",
        }
        self.feedback.emit("success", mensagens.get(operacao, "Alteração salva."))
        self.carregar()
