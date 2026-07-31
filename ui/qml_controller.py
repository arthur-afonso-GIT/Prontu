"""Ponte pequena entre a interface QML e os serviços Python existentes."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices

from services.configuracoes_service import (
    MENSAGEM_WHATSAPP_MANUAL_PADRAO,
    montar_url_whatsapp_manual,
)
from services.pacientes_service import (
    data_br_para_iso,
    data_iso_para_br,
    formatar_cpf,
    formatar_rg,
    formatar_telefone,
    normalizar_estado_civil,
    normalizar_rg,
    paciente_corresponde_busca,
    somente_numeros,
)


class QmlAppController(QObject):
    paginaAlterada = Signal()

    _ROTULOS_PAGINAS = {
        "home": "Painel Principal",
        "pacientes": "Pacientes",
        "agenda": "Agenda de Consultas",
        "fichas": "Fichas Clínicas",
        "financeiro": "Financeiro",
        "equipe": "Equipe",
        "configuracoes": "Configurações",
    }
    _SUBTITULOS_PAGINAS = {
        "home": "Resumo da operação da clínica",
        "pacientes": "Cadastros, prontuários e retornos dos pacientes",
        "agenda": "Organização diária e semanal das consultas",
        "fichas": "Modelos e registros clínicos dos atendimentos",
        "financeiro": "Acompanhamento dos pagamentos das consultas",
        "equipe": "Acessos e responsabilidades dos integrantes",
        "configuracoes": "Perfil, mensagens, backup e segurança",
    }

    def __init__(self, database, logo_path: Path, parent=None):
        super().__init__(parent)
        self._database = database
        self._pagina_atual = "home"
        self._logo_url = QUrl.fromLocalFile(str(logo_path)) if logo_path.is_file() else QUrl()

    @Property(str, constant=True)
    def nomeClinica(self) -> str:
        sessao = getattr(getattr(self._database, "session_manager", None), "_session", None) or {}
        return str(sessao.get("nome_clinica") or "Clínica conectada")

    @Property(str, constant=True)
    def papelAtual(self) -> str:
        papel = getattr(self._database, "obter_papel_atual", lambda: "proprietario")()
        nomes = {
            "proprietario": "Proprietário",
            "profissional": "Profissional",
            "secretaria": "Secretária",
        }
        return nomes.get(str(papel).lower(), str(papel).title())

    @Property(str, constant=True)
    def planoAtual(self) -> str:
        plano = getattr(self._database, "obter_plano_atual", lambda: "solo")()
        nomes = {
            "solo": "Prontu Solo",
            "equipe": "Prontu Equipe",
            "personalizado": "Prontu Personalizado",
        }
        return nomes.get(str(plano).lower(), str(plano).title())

    @Property(bool, constant=True)
    def podeGerenciarEquipe(self) -> bool:
        papel = getattr(self._database, "obter_papel_atual", lambda: "proprietario")()
        return str(papel).lower() == "proprietario"

    @Property(bool, constant=True)
    def podeVerFichas(self) -> bool:
        papel = getattr(self._database, "obter_papel_atual", lambda: "proprietario")()
        return str(papel).lower() != "secretaria"

    @Property(QUrl, constant=True)
    def logoUrl(self) -> QUrl:
        return self._logo_url

    @Property(str, notify=paginaAlterada)
    def paginaAtual(self) -> str:
        return self._pagina_atual

    @Property(str, notify=paginaAlterada)
    def tituloPagina(self) -> str:
        return self._ROTULOS_PAGINAS.get(self._pagina_atual, "Prontu")

    @Property(str, notify=paginaAlterada)
    def subtituloPagina(self) -> str:
        return self._SUBTITULOS_PAGINAS.get(
            self._pagina_atual, "Gerenciamento Inteligente"
        )

    @Slot(str)
    def navegar(self, pagina: str) -> None:
        pagina = str(pagina).strip().lower()
        if pagina == "equipe" and not self.podeGerenciarEquipe:
            pagina = "home"
        if pagina == "fichas" and not self.podeVerFichas:
            pagina = "home"
        if pagina not in self._ROTULOS_PAGINAS or pagina == self._pagina_atual:
            return
        self._pagina_atual = pagina
        self.paginaAlterada.emit()


class PatientsListModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    NomeRole = IdRole + 1
    TelefoneRole = NomeRole + 1
    ConvenioRole = TelefoneRole + 1
    PastaRole = ConvenioRole + 1

    _ROLES = {
        IdRole: b"patientId",
        NomeRole: b"name",
        TelefoneRole: b"phone",
        ConvenioRole: b"insurance",
        PastaRole: b"folder",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        paciente = self._rows[index.row()]
        valores = {
            self.IdRole: paciente.get("id"),
            self.NomeRole: paciente.get("nome") or "",
            self.TelefoneRole: formatar_telefone(paciente.get("telefone")),
            self.ConvenioRole: paciente.get("convenio") or "",
            self.PastaRole: paciente.get("pasta") or "Geral",
        }
        return valores.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()


class PatientClinicalHistoryModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    ModeloRole = IdRole + 1
    DataRole = ModeloRole + 1
    AnexosRole = DataRole + 1

    _ROLES = {
        IdRole: b"recordId",
        ModeloRole: b"modelName",
        DataRole: b"appointmentDate",
        AnexosRole: b"attachmentCount",
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
            self.IdRole: int(item.get("id") or 0),
            self.ModeloRole: str(item.get("modelo_nome") or "Ficha clínica"),
            self.DataRole: str(item.get("data_atendimento") or ""),
            self.AnexosRole: int(item.get("total_anexos") or 0),
        }.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows or [])
        self.endResetModel()


class PatientsController(QObject):
    estadoAlterado = Signal()
    selecaoAlterada = Signal()
    feedback = Signal(str, str)
    fichaVisualizacaoPronta = Signal(str)
    _listaCarregada = Signal(object, object)
    _pacienteCarregado = Signal(object, object)
    _fichaCarregada = Signal(object, object)
    _anexoPreparado = Signal(object, object)
    _operacaoFinalizada = Signal(object, object)
    _whatsappPreparado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._model = PatientsListModel(self)
        self._historico = PatientClinicalHistoryModel(self)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prontu-qml")
        self._todos: list[dict] = []
        self._pastas = ["Todas as Pastas", "Geral"]
        self._busca = ""
        self._pasta = "Todas as Pastas"
        self._ocupado = False
        self._selecionado: dict = {}
        self._ficha_titulo = ""
        self._ficha_detalhes: list[dict] = []
        self._ficha_anexos: list[dict] = []
        self._listaCarregada.connect(self._receber_lista)
        self._pacienteCarregado.connect(self._receber_paciente)
        self._fichaCarregada.connect(self._receber_ficha)
        self._anexoPreparado.connect(self._abrir_url_anexo)
        self._operacaoFinalizada.connect(self._receber_operacao)
        self._whatsappPreparado.connect(self._abrir_url_whatsapp)

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(int, notify=estadoAlterado)
    def total(self) -> int:
        return self._model.rowCount()

    @Property(list, notify=estadoAlterado)
    def pastas(self) -> list[str]:
        return self._pastas

    @Property("QVariantMap", notify=selecaoAlterada)
    def pacienteSelecionado(self) -> dict:
        return self._selecionado

    @Property(QObject, constant=True)
    def historicoModel(self):
        return self._historico

    @Property(int, notify=estadoAlterado)
    def totalHistorico(self) -> int:
        return self._historico.rowCount()

    @Property(str, notify=estadoAlterado)
    def fichaVisualizacaoTitulo(self) -> str:
        return self._ficha_titulo

    @Property(list, notify=estadoAlterado)
    def fichaVisualizacaoDetalhes(self) -> list[dict]:
        return list(self._ficha_detalhes)

    @Property(list, notify=estadoAlterado)
    def fichaVisualizacaoAnexos(self) -> list[dict]:
        return list(self._ficha_anexos)

    @Property(bool, constant=True)
    def podeVerDadosClinicos(self) -> bool:
        papel = getattr(self._database, "obter_papel_atual", lambda: "proprietario")()
        return str(papel).lower() != "secretaria"

    def _definir_ocupado(self, valor: bool) -> None:
        if self._ocupado != valor:
            self._ocupado = valor
            self.estadoAlterado.emit()

    def _enviar(
        self,
        tarefa,
        sinal: Signal,
    ) -> None:
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

        def tarefa():
            pacientes = self._database.listar_pacientes_interface()
            pastas = self._database.listar_pastas_interface()
            return pacientes, pastas

        self._enviar(tarefa, self._listaCarregada)

    @Slot(str)
    def definirBusca(self, texto: str) -> None:
        self._busca = str(texto or "")
        self._aplicar_filtros()

    @Slot(str)
    def definirPasta(self, pasta: str) -> None:
        self._pasta = str(pasta or "Todas as Pastas")
        self._aplicar_filtros()

    def _aplicar_filtros(self) -> None:
        pasta = self._pasta.casefold()
        filtrados = [
            paciente
            for paciente in self._todos
            if paciente_corresponde_busca(paciente, self._busca)
            and (
                pasta in {"todas as pastas", "geral"}
                or str(paciente.get("pasta") or "Geral").casefold() == pasta
            )
        ]
        self._model.substituir(filtrados)
        self.estadoAlterado.emit()

    @Slot(int)
    def selecionar(self, paciente_id: int) -> None:
        if self._ocupado or not paciente_id:
            return

        def tarefa():
            paciente = self._database.obter_paciente_interface(int(paciente_id))
            historico = (
                self._database.listar_historico_fichas_interface(int(paciente_id))
                if self.podeVerDadosClinicos
                else []
            )
            return paciente, historico

        self._enviar(
            tarefa,
            self._pacienteCarregado,
        )

    @Slot()
    def novo(self) -> None:
        self._historico.substituir([])
        self._limpar_visualizacao_ficha()
        self._selecionado = {
            "id": None,
            "nome": "",
            "telefone": "",
            "nascimento": "",
            "convenio": "PARTICULAR",
            "pasta": "Geral",
            "sexo": "Não informado",
            "cpf": "",
            "rg": "",
            "estado_civil": "Não informado",
            "profissao": "",
            "endereco": "",
            "queixa": "",
            "lembretes_whatsapp_ativos": False,
        }
        self.selecaoAlterada.emit()
        self.estadoAlterado.emit()

    def _limpar_visualizacao_ficha(self) -> None:
        self._ficha_titulo = ""
        self._ficha_detalhes = []
        self._ficha_anexos = []

    @staticmethod
    def _valor_ficha_legivel(valor) -> str:
        if isinstance(valor, bool):
            return "Sim" if valor else "Não"
        if isinstance(valor, (list, tuple)):
            return ", ".join(str(item) for item in valor if str(item).strip())
        texto = str(valor or "").strip()
        return texto or "Não informado"

    @Slot(int)
    def visualizarFicha(self, ficha_id: int) -> None:
        if self._ocupado or not ficha_id or not self.podeVerDadosClinicos:
            return
        self._enviar(
            lambda: self._database.obter_ficha_interface(int(ficha_id)),
            self._fichaCarregada,
        )

    @Slot(int)
    def abrirAnexoFicha(self, indice: int) -> None:
        indice = int(indice)
        if self._ocupado or not 0 <= indice < len(self._ficha_anexos):
            return
        caminho = str(self._ficha_anexos[indice].get("caminho") or "")
        if not caminho:
            self.feedback.emit("error", "O endereço deste anexo não está disponível.")
            return
        self._enviar(
            lambda: self._database.criar_link_anexo_interface(caminho),
            self._anexoPreparado,
        )

    @Slot(str)
    def novoNaPasta(self, pasta: str) -> None:
        self.novo()
        self._selecionado["pasta"] = str(pasta or "Geral").strip() or "Geral"
        self.selecaoAlterada.emit()

    @Slot("QVariantMap")
    def salvar(self, formulario: dict) -> None:
        if self._ocupado:
            return
        nome = str(formulario.get("nome") or "").strip()
        if not nome:
            self.feedback.emit("warning", "Informe o nome completo do paciente.")
            return
        nascimento_digitado = str(formulario.get("nascimento") or "").strip()
        nascimento = data_br_para_iso(nascimento_digitado)
        if nascimento_digitado and nascimento is None:
            self.feedback.emit("warning", "Informe o nascimento no formato dia/mês/ano.")
            return

        dados = {
            "nome": nome,
            "telefone": somente_numeros(formulario.get("telefone")),
            "nascimento": nascimento,
            "convenio": str(formulario.get("convenio") or "PARTICULAR").strip(),
            "pasta": str(formulario.get("pasta") or "Geral").strip(),
            "sexo": str(formulario.get("sexo") or "Não informado"),
            "cpf": somente_numeros(formulario.get("cpf"), 11),
            "rg": normalizar_rg(formulario.get("rg")),
            "estado_civil": normalizar_estado_civil(
                formulario.get("estado_civil")
            ),
            "profissao": str(formulario.get("profissao") or "").strip(),
            "endereco": str(formulario.get("endereco") or "").strip(),
            "queixa": str(formulario.get("queixa") or "").strip(),
            "lembretes_whatsapp_ativos": bool(
                formulario.get("lembretes_whatsapp_ativos")
            ),
        }
        paciente_id = formulario.get("id")
        paciente_id = int(paciente_id) if paciente_id else None

        def tarefa():
            salvo = self._database.salvar_paciente_interface(paciente_id, dados)
            return "salvar", salvo

        self._enviar(tarefa, self._operacaoFinalizada)

    @Slot(int)
    def excluir(self, paciente_id: int) -> None:
        if self._ocupado or not paciente_id:
            return

        def tarefa():
            sucesso = self._database.soft_delete_paciente(int(paciente_id))
            return "excluir", sucesso

        self._enviar(tarefa, self._operacaoFinalizada)

    @Slot(str, str)
    def abrirWhatsApp(self, telefone: str, paciente: str) -> None:
        if self._ocupado:
            return
        if len(somente_numeros(telefone)) < 10:
            self.feedback.emit(
                "warning",
                "Informe um telefone com DDD para abrir o WhatsApp.",
            )
            return

        def tarefa():
            modelo = self._database.obter_configuracao(
                "whatsapp_mensagem_manual",
                MENSAGEM_WHATSAPP_MANUAL_PADRAO,
            )
            profissional = (
                self._database.obter_nome_profissional()
                or "a equipe da clínica"
            )
            return montar_url_whatsapp_manual(
                telefone,
                paciente,
                profissional,
                modelo,
            )

        self._enviar(tarefa, self._whatsappPreparado)

    @Slot(object, object)
    def _receber_lista(self, resultado, erro) -> None:
        self._definir_ocupado(False)
        if erro:
            self.feedback.emit("error", "Não foi possível carregar os pacientes.")
            return
        pacientes, pastas = resultado or ([], ["Geral"])
        self._todos = list(pacientes or [])
        nomes = ["Todas as Pastas", *(pastas or ["Geral"])]
        self._pastas = list(dict.fromkeys(nomes))
        self._aplicar_filtros()

    @Slot(object, object)
    def _receber_paciente(self, paciente, erro) -> None:
        self._definir_ocupado(False)
        if erro or not paciente or not paciente[0]:
            self.feedback.emit("error", "Não foi possível abrir este paciente.")
            return
        dados_paciente, historico = paciente
        dados = dict(dados_paciente)
        dados["nascimento"] = data_iso_para_br(dados.get("nascimento"))
        dados["telefone"] = formatar_telefone(dados.get("telefone"))
        dados["cpf"] = formatar_cpf(dados.get("cpf"))
        dados["rg"] = formatar_rg(dados.get("rg"))
        dados["estado_civil"] = normalizar_estado_civil(
            dados.get("estado_civil")
        )
        self._selecionado = dados
        self._historico.substituir(list(historico or []))
        self._limpar_visualizacao_ficha()
        self.selecaoAlterada.emit()
        self.estadoAlterado.emit()

    @Slot(object, object)
    def _receber_ficha(self, ficha, erro) -> None:
        self._definir_ocupado(False)
        if erro or not ficha:
            self.feedback.emit("error", "Não foi possível abrir esta ficha.")
            return
        ficha = dict(ficha)
        respostas = dict(ficha.get("dados_respostas") or {})
        detalhes = []
        for campo in ficha.get("estrutura") or []:
            if not isinstance(campo, dict):
                continue
            tipo = str(campo.get("tipo") or "").casefold()
            rotulo = str(campo.get("label") or campo.get("titulo") or "").strip()
            if tipo == "secao":
                if rotulo:
                    detalhes.append({
                        "label": rotulo,
                        "valor": "",
                        "secao": True,
                    })
                continue
            campo_id = str(campo.get("id") or "")
            if not rotulo:
                rotulo = campo_id.replace("_", " ").capitalize()
            detalhes.append({
                "label": rotulo or "Campo",
                "valor": self._valor_ficha_legivel(respostas.get(campo_id)),
                "secao": False,
            })

        anexos = ficha.get("anexos") or []
        self._ficha_titulo = str(ficha.get("modelo_nome") or "Ficha clínica")
        self._ficha_detalhes = detalhes
        self._ficha_anexos = [
            {
                "nome": str(item.get("nome") or "Anexo"),
                "caminho": str(item.get("caminho") or ""),
            }
            for item in anexos
            if isinstance(item, dict) and item.get("caminho")
        ]
        self.estadoAlterado.emit()
        self.fichaVisualizacaoPronta.emit(self._ficha_titulo)

    @Slot(object, object)
    def _abrir_url_anexo(self, url, erro) -> None:
        self._definir_ocupado(False)
        if erro or not url or not QDesktopServices.openUrl(QUrl(str(url))):
            self.feedback.emit(
                "error",
                "Não foi possível abrir o anexo. Tente novamente.",
            )

    @Slot(object, object)
    def _receber_operacao(self, resultado, erro) -> None:
        self._definir_ocupado(False)
        if erro or not resultado or not resultado[1]:
            self.feedback.emit("error", "A operação não pôde ser concluída.")
            return
        operacao = resultado[0]
        self.feedback.emit(
            "success",
            "Paciente salvo com sucesso."
            if operacao == "salvar"
            else "Paciente removido da lista.",
        )
        self.novo()
        self.carregar()

    @Slot(object, object)
    def _abrir_url_whatsapp(self, url, erro) -> None:
        self._definir_ocupado(False)
        if erro or not url:
            self.feedback.emit(
                "error",
                "Não foi possível preparar a mensagem do WhatsApp.",
            )
            return
        if not QDesktopServices.openUrl(QUrl(str(url))):
            self.feedback.emit(
                "error",
                "Não foi possível abrir o WhatsApp no navegador.",
            )
