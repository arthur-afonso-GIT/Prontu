"""Controlador assíncrono da Agenda QML."""
from __future__ import annotations

from calendar import monthrange
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, timedelta

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    QTimer,
    Qt,
    Signal,
    Slot,
)

from services.agenda_service import (
    DIAS_PT,
    DURACOES,
    HORARIOS_GRADE,
    MESES_PT,
    STATUS_CONSULTA,
    TIPOS_CONSULTA_PADRAO,
    cor_do_status,
    data_br_para_date,
    data_extenso,
    horario_agendamento_ja_passou,
    status_legivel,
)


class AgendaSlotsModel(QAbstractListModel):
    HorarioRole = Qt.ItemDataRole.UserRole + 1
    DisponivelRole = HorarioRole + 1
    ContinuacaoRole = DisponivelRole + 1
    PacienteRole = ContinuacaoRole + 1
    ProcedimentoRole = PacienteRole + 1
    DuracaoRole = ProcedimentoRole + 1
    StatusRole = DuracaoRole + 1
    StatusLabelRole = StatusRole + 1
    StatusColorRole = StatusLabelRole + 1
    ObservacaoRole = StatusColorRole + 1
    RetornoPendenteIdRole = ObservacaoRole + 1

    _ROLES = {
        HorarioRole: b"time",
        DisponivelRole: b"available",
        ContinuacaoRole: b"continuation",
        PacienteRole: b"patient",
        ProcedimentoRole: b"procedure",
        DuracaoRole: b"duration",
        StatusRole: b"statusValue",
        StatusLabelRole: b"statusLabel",
        StatusColorRole: b"statusColor",
        ObservacaoRole: b"notes",
        RetornoPendenteIdRole: b"pendingReturnDecisionId",
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
        valores = {
            self.HorarioRole: item.get("horario", ""),
            self.DisponivelRole: item.get("disponivel", True),
            self.ContinuacaoRole: item.get("continuacao", False),
            self.PacienteRole: item.get("paciente", ""),
            self.ProcedimentoRole: item.get("procedimento", ""),
            self.DuracaoRole: item.get("duracao_txt", ""),
            self.StatusRole: item.get("status", ""),
            self.StatusLabelRole: status_legivel(item.get("status", "")),
            self.StatusColorRole: cor_do_status(item.get("status", "")),
            self.ObservacaoRole: item.get("observacao", ""),
            self.RetornoPendenteIdRole: int(
                item.get("decisao_retorno_id") or 0
            ),
        }
        return valores.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, agendamentos: list[dict]) -> None:
        por_horario = {
            str(item.get("horario")): item
            for item in agendamentos
            if item.get("horario")
        }
        rows = []
        for horario in HORARIOS_GRADE:
            consulta = por_horario.get(horario)
            if not consulta:
                rows.append({"horario": horario, "disponivel": True})
                continue
            rows.append({
                **consulta,
                "horario": horario,
                "disponivel": False,
                "continuacao": consulta.get("tipo_bloco") == "continua",
            })
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class AgendaController(QObject):
    estadoAlterado = Signal()
    feedback = Signal(str, str)
    confirmacaoHorarioPassado = Signal(str, str)
    conflitoHorario = Signal(str, str)
    retornoProntoParaAgendar = Signal(object)
    _carregamentoFinalizado = Signal(object, object)
    _operacaoFinalizada = Signal(object, object)
    _sincronizacaoFinalizada = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._model = AgendaSlotsModel(self)
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-agenda"
        )
        self._data = date.today()
        self._modo = "dia"
        self._ocupado = False
        self._pacientes: list[str] = []
        self._procedimentos = list(TIPOS_CONSULTA_PADRAO)
        self._agendamentos: list[dict] = []
        self._agendamentos_periodo: list[dict] = []
        self._consulta_passada_pendente: dict | None = None
        self._timer_status = QTimer(self)
        self._timer_status.setInterval(30000)
        self._timer_status.timeout.connect(self.sincronizarEstadosAutomaticos)
        self._timer_status.start()
        self._carregamentoFinalizado.connect(self._receber_carregamento)
        self._operacaoFinalizada.connect(self._receber_operacao)
        self._sincronizacaoFinalizada.connect(
            self._receber_sincronizacao_automatica
        )

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(str, notify=estadoAlterado)
    def dataSelecionada(self) -> str:
        return self._data.strftime("%d/%m/%Y")

    @Property(str, notify=estadoAlterado)
    def dataExtenso(self) -> str:
        return data_extenso(self._data)

    @Property(str, notify=estadoAlterado)
    def modo(self) -> str:
        return self._modo

    @Property(str, notify=estadoAlterado)
    def tituloPeriodo(self) -> str:
        if self._modo == "semana":
            inicio = self._inicio_semana()
            fim = inicio + timedelta(days=6)
            return (
                f"Semana de {inicio.strftime('%d/%m')} a "
                f"{fim.strftime('%d/%m/%Y')}"
            )
        if self._modo == "mes":
            return f"{MESES_PT[self._data.month - 1].capitalize()} de {self._data.year}"
        return self.dataExtenso

    @Property(str, notify=estadoAlterado)
    def tituloResumo(self) -> str:
        return {
            "semana": "Resumo da semana",
            "mes": "Resumo do mês",
        }.get(self._modo, "Agenda do dia")

    @Property(list, notify=estadoAlterado)
    def diasSemana(self) -> list[dict]:
        inicio = self._inicio_semana()
        return [
            self._resumo_dia(inicio + timedelta(days=indice))
            for indice in range(7)
        ]

    @Property(list, notify=estadoAlterado)
    def diasMes(self) -> list[dict]:
        inicio = self._inicio_grade_mes()
        return [
            self._resumo_dia(
                inicio + timedelta(days=indice),
                mes_atual=(
                    inicio + timedelta(days=indice)
                ).month == self._data.month,
            )
            for indice in range(42)
        ]

    @Property(list, notify=estadoAlterado)
    def pacientes(self) -> list[str]:
        return self._pacientes

    @Property(list, notify=estadoAlterado)
    def procedimentos(self) -> list[str]:
        return self._procedimentos

    @Property(list, constant=True)
    def duracoes(self) -> list[str]:
        return DURACOES

    @Property(list, constant=True)
    def horarios(self) -> list[str]:
        return HORARIOS_GRADE

    @Property(list, constant=True)
    def statusDisponiveis(self) -> list[str]:
        return STATUS_CONSULTA

    @Property(int, notify=estadoAlterado)
    def totalConsultas(self) -> int:
        return len([
            item for item in self._itens_do_resumo()
            if item.get("tipo_bloco") == "principal"
        ])

    @Property(int, notify=estadoAlterado)
    def totalConfirmadas(self) -> int:
        return self._contar_status("Confirmado")

    @Property(int, notify=estadoAlterado)
    def totalPendentes(self) -> int:
        return self._contar_status("Agendado")

    @Property(int, notify=estadoAlterado)
    def totalRealizadas(self) -> int:
        return self._contar_status("Realizada")

    def _contar_status(self, trecho: str) -> int:
        return sum(
            item.get("tipo_bloco") == "principal"
            and trecho in str(item.get("status") or "")
            for item in self._itens_do_resumo()
        )

    def _itens_do_resumo(self) -> list[dict]:
        if self._modo == "dia":
            return self._agendamentos
        return self._agendamentos_periodo

    def _inicio_semana(self) -> date:
        return self._data - timedelta(days=self._data.weekday())

    def _inicio_grade_mes(self) -> date:
        primeiro = self._data.replace(day=1)
        return primeiro - timedelta(days=primeiro.weekday())

    def _datas_visiveis(self) -> list[date]:
        if self._modo == "semana":
            inicio = self._inicio_semana()
            return [inicio + timedelta(days=indice) for indice in range(7)]
        if self._modo == "mes":
            inicio = self._inicio_grade_mes()
            return [inicio + timedelta(days=indice) for indice in range(42)]
        return [self._data]

    def _resumo_dia(
        self, valor: date, mes_atual: bool = True
    ) -> dict:
        data_texto = valor.strftime("%d/%m/%Y")
        consultas = []
        for item in self._agendamentos_periodo:
            if (
                str(item.get("data") or "") == data_texto
                and item.get("tipo_bloco") == "principal"
            ):
                consultas.append({
                    **item,
                    "status_label": status_legivel(item.get("status", "")),
                    "status_color": cor_do_status(item.get("status", "")),
                })
        consultas.sort(key=lambda item: str(item.get("horario") or ""))
        return {
            "data": data_texto,
            "dia": valor.day,
            "dia_semana": DIAS_PT[valor.weekday()].capitalize(),
            "rotulo": (
                f"{DIAS_PT[valor.weekday()].capitalize()}\n"
                f"{valor.strftime('%d/%m')}"
            ),
            "mes_atual": mes_atual,
            "hoje": valor == date.today(),
            "consultas": consultas,
            "total": len(consultas),
        }

    def _definir_ocupado(self, valor: bool) -> None:
        if self._ocupado != valor:
            self._ocupado = valor
            self.estadoAlterado.emit()

    def _enviar(self, tarefa, sinal: Signal) -> None:
        self._definir_ocupado(True)
        futuro = self._executor.submit(tarefa)

        def concluido(resultado: Future):
            try:
                sinal.emit(resultado.result(), None)
            except Exception as erro:
                sinal.emit(None, str(erro))

        futuro.add_done_callback(concluido)

    @Slot()
    def carregar(self) -> None:
        if self._ocupado:
            return
        data_consulta = self.dataSelecionada
        datas_periodo = [
            valor.strftime("%d/%m/%Y") for valor in self._datas_visiveis()
        ]

        def tarefa():
            iniciar_consultas = getattr(
                self._database,
                "iniciar_consultas_no_horario_interface",
                None,
            )
            if callable(iniciar_consultas):
                agora = datetime.now()
                iniciar_consultas(
                    agora.strftime("%d/%m/%Y"),
                    agora.strftime("%H:%M"),
                )
            listar_periodo = getattr(
                self._database, "listar_agenda_periodo_interface", None
            )
            if callable(listar_periodo):
                agenda = listar_periodo(datas_periodo)
            else:
                agenda = []
                for data_periodo in datas_periodo:
                    agenda.extend(
                        self._database.listar_agenda_interface(data_periodo)
                    )
            listar_retornos = getattr(
                self._database, "listar_retornos_pendentes", None
            )
            return {
                "agenda": agenda,
                "pacientes": self._database.buscar_nomes_pacientes(),
                "procedimentos": self._database.listar_tipos_consulta_interface(),
                "retornos": listar_retornos() if callable(listar_retornos) else [],
            }

        self._enviar(tarefa, self._carregamentoFinalizado)

    @Slot(int)
    def navegarDias(self, quantidade: int) -> None:
        if self._ocupado:
            return
        quantidade = int(quantidade)
        if self._modo == "semana":
            self._data += timedelta(days=7 * quantidade)
        elif self._modo == "mes":
            indice_mes = (
                self._data.year * 12 + self._data.month - 1 + quantidade
            )
            ano, mes_zero = divmod(indice_mes, 12)
            mes = mes_zero + 1
            dia = min(self._data.day, monthrange(ano, mes)[1])
            self._data = date(ano, mes, dia)
        else:
            self._data += timedelta(days=quantidade)
        self.estadoAlterado.emit()
        self.carregar()

    @Slot()
    def irParaHoje(self) -> None:
        if self._ocupado:
            return
        self._data = date.today()
        self.estadoAlterado.emit()
        self.carregar()

    @Slot(str)
    def definirModo(self, modo: str) -> None:
        modo = str(modo or "").strip().casefold()
        if modo not in {"dia", "semana", "mes"} or modo == self._modo:
            return
        if self._ocupado:
            return
        self._modo = modo
        self.estadoAlterado.emit()
        self.carregar()

    @Slot(str)
    def abrirDia(self, data_br: str) -> None:
        if self._ocupado:
            return
        try:
            self._data = data_br_para_date(data_br)
        except ValueError:
            return
        self._modo = "dia"
        self.estadoAlterado.emit()
        self.carregar()

    @Slot(str)
    def definirData(self, data_br: str) -> None:
        if self._ocupado:
            return
        try:
            nova_data = data_br_para_date(data_br)
        except ValueError:
            self.feedback.emit("warning", "Informe a data no formato dia/mês/ano.")
            return
        self._data = nova_data
        self.estadoAlterado.emit()
        self.carregar()

    @Slot("QVariantMap")
    def criarConsulta(self, formulario: dict) -> None:
        if self._ocupado:
            return
        paciente = str(formulario.get("paciente") or "").strip()
        horario = str(formulario.get("horario") or "").strip()
        if not paciente:
            self.feedback.emit("warning", "Selecione um paciente cadastrado.")
            return
        if paciente.casefold() not in {
            nome.casefold() for nome in self._pacientes
        }:
            self.feedback.emit(
                "warning", "Escolha um paciente existente na lista."
            )
            return
        if horario not in HORARIOS_GRADE:
            self.feedback.emit("warning", "Selecione um horário válido.")
            return

        dados = {
            "paciente": paciente,
            "procedimento": str(
                formulario.get("procedimento") or TIPOS_CONSULTA_PADRAO[0]
            ),
            "status": str(formulario.get("status") or STATUS_CONSULTA[0]),
            "duracao_txt": str(formulario.get("duracao") or DURACOES[1]),
            "observacao": str(formulario.get("observacao") or "").strip(),
            "retorno_id": formulario.get("retorno_id"),
        }
        data_consulta = self.dataSelecionada
        if horario_agendamento_ja_passou(data_consulta, horario):
            self._consulta_passada_pendente = {
                "data": data_consulta,
                "horario": horario,
                "dados": dados,
            }
            self.confirmacaoHorarioPassado.emit(data_consulta, horario)
            return
        self._salvar_consulta(data_consulta, horario, dados)

    def _salvar_consulta(
        self, data_consulta: str, horario: str, dados: dict
    ) -> None:
        def tarefa():
            resposta = self._database.salvar_agendamento_interface(
                data_consulta, horario, dados
            )
            if not isinstance(resposta, dict):
                resposta = {"sucesso": bool(resposta)}
            return "criar", resposta

        self._enviar(tarefa, self._operacaoFinalizada)

    @Slot()
    def confirmarConsultaNoPassado(self) -> None:
        if self._ocupado or not self._consulta_passada_pendente:
            return
        consulta = self._consulta_passada_pendente
        self._consulta_passada_pendente = None
        self._salvar_consulta(
            str(consulta["data"]),
            str(consulta["horario"]),
            dict(consulta["dados"]),
        )

    @Slot()
    def cancelarConsultaNoPassado(self) -> None:
        self._consulta_passada_pendente = None

    @Slot(int, str, str)
    def prepararAgendamentoRetorno(
        self, retorno_id: int, data_br: str, paciente: str
    ) -> None:
        if self._ocupado or not retorno_id:
            return
        try:
            data_retorno = data_br_para_date(data_br)
        except ValueError:
            self.feedback.emit("warning", "Informe a data no formato dia/mês/ano.")
            return
        if data_retorno < date.today():
            self.feedback.emit("warning", "O retorno não pode ficar em uma data passada.")
            return

        data_iso = data_retorno.strftime("%Y-%m-%d")
        payload = {
            "id": int(retorno_id),
            "paciente_nome": str(paciente or "").strip(),
            "data_prevista": data_iso,
            "data_texto": data_retorno.strftime("%d/%m/%Y"),
            "motivo": "Retorno após consulta realizada",
        }

        def tarefa():
            sucesso = self._database.definir_data_retorno(
                int(retorno_id), data_iso
            )
            return "preparar_retorno", sucesso, payload

        self._enviar(tarefa, self._operacaoFinalizada)

    @Slot(int)
    def marcarSemRetorno(self, retorno_id: int) -> None:
        if self._ocupado or not retorno_id:
            return

        def tarefa():
            sucesso = self._database.atualizar_status_retorno(
                int(retorno_id), "Não retornou"
            )
            return "sem_retorno", sucesso

        self._enviar(tarefa, self._operacaoFinalizada)

    @Slot()
    def sincronizarEstadosAutomaticos(self) -> None:
        if self._ocupado:
            return
        sincronizar = getattr(
            self._database,
            "iniciar_consultas_no_horario_interface",
            None,
        )
        if not callable(sincronizar):
            return
        agora = datetime.now()

        def tarefa():
            return sincronizar(
                agora.strftime("%d/%m/%Y"),
                agora.strftime("%H:%M"),
            )

        futuro = self._executor.submit(tarefa)

        def concluido(resultado: Future):
            try:
                self._sincronizacaoFinalizada.emit(resultado.result(), None)
            except Exception as erro:
                self._sincronizacaoFinalizada.emit(None, str(erro))

        futuro.add_done_callback(concluido)

    @Slot(str, str)
    def atualizarStatus(self, horario: str, novo_status: str) -> None:
        if self._ocupado:
            return
        data_consulta = self.dataSelecionada

        def tarefa():
            sucesso = self._database.atualizar_status_agenda_interface(
                data_consulta, str(horario), str(novo_status)
            )
            return "status", sucesso

        self._enviar(tarefa, self._operacaoFinalizada)

    @Slot(object, object)
    def _receber_carregamento(self, resultado, erro) -> None:
        self._definir_ocupado(False)
        if erro or not isinstance(resultado, dict):
            self.feedback.emit("error", "Não foi possível carregar a agenda.")
            return
        retornos_por_paciente = {
            " ".join(
                str(item.get("paciente_nome") or "").strip().casefold().split()
            ): item
            for item in resultado.get("retornos") or []
            if item.get("id") and item.get("paciente_nome")
        }
        self._agendamentos_periodo = []
        for item_original in resultado.get("agenda") or []:
            item = dict(item_original)
            chave_paciente = " ".join(
                str(item.get("paciente") or "").strip().casefold().split()
            )
            retorno = retornos_por_paciente.get(chave_paciente)
            if (
                retorno
                and "Realizada" in str(item.get("status") or "")
                and str(item.get("procedimento") or "").strip().casefold()
                != "retorno"
            ):
                item["decisao_retorno_id"] = int(retorno["id"])
            self._agendamentos_periodo.append(item)
        self._agendamentos = [
            item for item in self._agendamentos_periodo
            if str(item.get("data") or "") == self.dataSelecionada
        ]
        self._pacientes = sorted(
            set(str(nome) for nome in resultado.get("pacientes") or [])
        )
        self._procedimentos = list(
            resultado.get("procedimentos") or TIPOS_CONSULTA_PADRAO
        )
        self._model.substituir(self._agendamentos)
        self.estadoAlterado.emit()

    @Slot(object, object)
    def _receber_operacao(self, resultado, erro) -> None:
        self._definir_ocupado(False)
        if erro or not resultado:
            self.feedback.emit(
                "error",
                "Não foi possível concluir a alteração. Tente novamente.",
            )
            return
        operacao = resultado[0]
        resposta = resultado[1]
        if operacao == "criar" and isinstance(resposta, dict):
            if not resposta.get("sucesso"):
                if resposta.get("motivo") == "conflito":
                    horarios = ", ".join(resposta.get("horarios") or [])
                    self.conflitoHorario.emit(
                        str(resposta.get("data") or self.dataSelecionada),
                        horarios,
                    )
                    self.carregar()
                    return
                self.feedback.emit(
                    "error",
                    "Não foi possível salvar a consulta agora. Tente novamente.",
                )
                return
        elif not resposta:
            self.feedback.emit(
                "error",
                "Não foi possível concluir a alteração. Tente novamente.",
            )
            return
        if operacao == "preparar_retorno":
            self.retornoProntoParaAgendar.emit(resultado[2])
            return
        self.feedback.emit(
            "success",
            {
                "criar": "Consulta agendada com sucesso.",
                "sem_retorno": "Decisão de retorno registrada.",
            }.get(operacao, "Status atualizado com sucesso."),
        )
        self.carregar()

    @Slot(object, object)
    def _receber_sincronizacao_automatica(self, resultado, erro) -> None:
        if erro:
            return
        if int(resultado or 0) > 0:
            self.carregar()
