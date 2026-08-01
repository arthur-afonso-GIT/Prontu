"""Controlador assíncrono do Financeiro em QML."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)

from services.financeiro_service import (
    calcular_resumo,
    calcular_status,
    classificar_alerta_pagamentos,
    moeda_br,
    numero_monetario,
    preparar_registros,
)


class FinancialListModel(QAbstractListModel):
    DateRole = Qt.ItemDataRole.UserRole + 1
    TimeRole = DateRole + 1
    PatientRole = TimeRole + 1
    ProcedureRole = PatientRole + 1
    ValueRole = ProcedureRole + 1
    ReceivedRole = ValueRole + 1
    StatusRole = ReceivedRole + 1
    LateRole = StatusRole + 1

    _ROLES = {
        DateRole: b"appointmentDate",
        TimeRole: b"appointmentTime",
        PatientRole: b"patientName",
        ProcedureRole: b"procedureName",
        ValueRole: b"consultationValue",
        ReceivedRole: b"receivedValue",
        StatusRole: b"paymentStatus",
        LateRole: b"overdue",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        item = self._rows[index.row()]
        return {
            self.DateRole: item.get("agenda_data") or "",
            self.TimeRole: item.get("agenda_horario") or "",
            self.PatientRole: item.get("paciente") or "",
            self.ProcedureRole: item.get("procedimento") or "",
            self.ValueRole: moeda_br(item.get("valor")),
            self.ReceivedRole: moeda_br(item.get("valor_recebido")),
            self.StatusRole: item.get("status_exibicao") or "Pendente",
            self.LateRole: bool(item.get("atrasado")),
        }.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows or [])
        self.endResetModel()


class FinanceiroController(QObject):
    estadoAlterado = Signal()
    feedback = Signal(str, str)
    formularioCarregado = Signal("QVariantMap")
    _resultado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-financeiro"
        )
        self._model = FinancialListModel(self)
        self._todos: list[dict] = []
        self._selecionado: dict = {}
        self._busca = ""
        self._filtro_status = "Todos os status"
        self._ocupado = False
        self._resumo = {"recebido": 0, "a_receber": 0, "consultas": 0}
        self._resultado.connect(self._receber_resultado)

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(int, notify=estadoAlterado)
    def total(self) -> int:
        return self._model.rowCount()

    @Property(str, notify=estadoAlterado)
    def recebidoMes(self) -> str:
        return moeda_br(self._resumo["recebido"])

    @Property(str, notify=estadoAlterado)
    def aReceber(self) -> str:
        return moeda_br(self._resumo["a_receber"])

    @Property(int, notify=estadoAlterado)
    def consultasAgenda(self) -> int:
        return int(self._resumo["consultas"])

    @Property(str, notify=estadoAlterado)
    def alertaPagamentos(self) -> str:
        return classificar_alerta_pagamentos(self._todos)

    @Property("QVariantMap", notify=estadoAlterado)
    def selecionado(self) -> dict:
        return self._selecionado

    @Property(bool, notify=estadoAlterado)
    def temSelecao(self) -> bool:
        return bool(self._selecionado)

    @Property(list, constant=True)
    def statusFiltros(self) -> list[str]:
        return [
            "Todos os status",
            "Pendente",
            "Parcial",
            "Pago",
            "Isento",
            "Pendente atrasado",
        ]

    def _definir_ocupado(self, valor: bool) -> None:
        if self._ocupado != valor:
            self._ocupado = valor
            self.estadoAlterado.emit()

    def _enviar(self, operacao: str, tarefa) -> None:
        self._definir_ocupado(True)
        futuro = self._executor.submit(tarefa)

        def concluido(resultado: Future):
            try:
                self._resultado.emit((operacao, resultado.result()), None)
            except Exception as erro:
                self._resultado.emit((operacao, None), str(erro))

        futuro.add_done_callback(concluido)

    def _filtrar(self) -> None:
        busca = self._busca.casefold()
        filtrados = []
        for item in self._todos:
            texto = " ".join([
                str(item.get("paciente") or ""),
                str(item.get("procedimento") or ""),
                str(item.get("agenda_data") or ""),
            ]).casefold()
            if busca and busca not in texto:
                continue
            if (
                self._filtro_status != "Todos os status"
                and item.get("status_exibicao") != self._filtro_status
                and item.get("status_pagamento") != self._filtro_status
            ):
                continue
            filtrados.append(item)
        self._model.substituir(filtrados)
        self.estadoAlterado.emit()

    @Slot()
    def carregar(self) -> None:
        if not self._ocupado:
            self._enviar("carregar", self._database.listar_financeiro_interface)

    @Slot(str)
    def definirBusca(self, texto: str) -> None:
        self._busca = str(texto or "").strip()
        self._filtrar()

    @Slot(str)
    def definirFiltroStatus(self, status: str) -> None:
        self._filtro_status = str(status or "Todos os status")
        self._filtrar()

    @Slot(str, str)
    def selecionar(self, data_consulta: str, horario: str) -> None:
        self._selecionado = next(
            (
                item for item in self._todos
                if item.get("agenda_data") == str(data_consulta)
                and item.get("agenda_horario") == str(horario)
            ),
            {},
        )
        self.estadoAlterado.emit()
        if self._selecionado:
            self.formularioCarregado.emit({
                "consulta": (
                    f"{self._selecionado.get('paciente', '')}\n"
                    f"{data_consulta} às {horario}"
                ),
                "valor": (
                    f"{float(self._selecionado.get('valor') or 0):.2f}"
                    .replace(".", ",")
                ),
                "recebido": (
                    f"{float(self._selecionado.get('valor_recebido') or 0):.2f}"
                    .replace(".", ",")
                ),
                "status": self._selecionado.get("status_pagamento") or "Pendente",
                "forma": self._selecionado.get("forma_pagamento") or "Não informado",
                "observacao": self._selecionado.get("observacao") or "",
            })

    @Slot(str, str, str, result=str)
    def calcularStatus(self, valor_texto: str, recebido_texto: str, atual: str) -> str:
        valor = numero_monetario(valor_texto)
        recebido = numero_monetario(recebido_texto)
        if valor is None or recebido is None:
            return str(atual or "Pendente")
        return calcular_status(valor, recebido, atual)

    @Slot(str, str, str, str, str)
    def salvar(
        self,
        valor_texto: str,
        recebido_texto: str,
        status: str,
        forma: str,
        observacao: str,
    ) -> None:
        if self._ocupado:
            return
        if not self._selecionado:
            self.feedback.emit("warning", "Selecione uma consulta na lista.")
            return
        valor = numero_monetario(valor_texto)
        recebido = numero_monetario(recebido_texto)
        if valor is None or recebido is None or valor < 0 or recebido < 0:
            self.feedback.emit(
                "warning", "Informe valores válidos, por exemplo: 150,00."
            )
            return
        status_final = calcular_status(valor, recebido, status)
        registro = dict(self._selecionado)
        payload = {
            "agenda_data": registro["agenda_data"],
            "agenda_horario": registro["agenda_horario"],
            "paciente": registro.get("paciente") or "",
            "procedimento": registro.get("procedimento") or "",
            "valor": valor,
            "valor_recebido": recebido,
            "status": status_final,
            "forma_pagamento": str(forma or "Não informado"),
            "observacao": str(observacao or "").strip(),
        }
        self._enviar(
            "salvar",
            lambda: self._database.salvar_pagamento_interface(payload),
        )

    @Slot(object, object)
    def _receber_resultado(self, pacote, erro) -> None:
        self._definir_ocupado(False)
        operacao, resultado = pacote or ("", None)
        if erro:
            self.feedback.emit(
                "error", "Não foi possível concluir a operação financeira."
            )
            return
        if operacao == "carregar":
            dados = resultado or {}
            if dados.get("erro"):
                self.feedback.emit(
                    "error",
                    "O Financeiro ainda não está configurado no banco de dados.",
                )
            self._todos = preparar_registros(
                dados.get("agenda") or [], dados.get("pagamentos") or []
            )
            self._resumo = calcular_resumo(self._todos)
            self._filtrar()
            return
        if operacao == "salvar":
            if not resultado:
                self.feedback.emit("error", "Não foi possível salvar o pagamento.")
                return
            self._selecionado = {}
            self.estadoAlterado.emit()
            self.feedback.emit("success", "Pagamento salvo com sucesso.")
            self.carregar()
