"""Controlador assíncrono das fichas clínicas em QML."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
    QUrl,
)
from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QFileDialog

from services.fichas_service import (
    MODELO_PADRAO,
    NOME_MODELO_PADRAO,
    exportar_ficha_word,
    html_exportacao_ficha,
    nome_arquivo_exportacao,
    normalizar_estrutura,
    preparar_dados_exportacao,
    respostas_iniciais,
    validar_respostas,
)
from services.leitor_documentos import (
    extrair_blocos_docx,
    extrair_blocos_pdf,
    interpretar_blocos,
)


class FichasHistoryModel(QAbstractListModel):
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
            self.IdRole: item.get("id"),
            self.ModeloRole: item.get("modelo_nome") or "Ficha Clínica",
            self.DataRole: item.get("data_atendimento") or "",
            self.AnexosRole: int(item.get("total_anexos") or 0),
        }.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows or [])
        self.endResetModel()


class FichasController(QObject):
    estadoAlterado = Signal()
    anexosVisualizacaoAlterados = Signal()
    feedback = Signal(str, str)
    formularioCarregado = Signal("QVariantMap")
    modeloImportado = Signal(str)
    visualizacaoAnexosPronta = Signal(str)
    _resultado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-fichas"
        )
        self._history = FichasHistoryModel(self)
        self._ocupado = False
        self._pacientes: list[dict] = []
        self._modelos: list[dict] = [{
            "nome": NOME_MODELO_PADRAO,
            "estrutura": normalizar_estrutura(MODELO_PADRAO),
        }]
        self._modelo_nome = NOME_MODELO_PADRAO
        self._campos = normalizar_estrutura(MODELO_PADRAO)
        self._paciente_id = 0
        self._ficha_id = 0
        self._anexos_existentes: list[dict] = []
        self._anexos_locais: list[str] = []
        self._anexos_visualizacao: list[dict] = []
        self._construindo = False
        self._campos_construtor: list[dict] = []
        self._resultado.connect(self._receber_resultado)

    @Property(QObject, constant=True)
    def historicoModel(self):
        return self._history

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(list, notify=estadoAlterado)
    def pacientes(self) -> list[dict]:
        return self._pacientes

    @Property(list, notify=estadoAlterado)
    def nomesModelos(self) -> list[str]:
        return [modelo["nome"] for modelo in self._modelos]

    @Property(list, notify=estadoAlterado)
    def camposModelo(self) -> list[dict]:
        return self._campos

    @Property(str, notify=estadoAlterado)
    def modeloSelecionado(self) -> str:
        return self._modelo_nome

    @Property(int, notify=estadoAlterado)
    def pacienteSelecionadoId(self) -> int:
        return self._paciente_id

    @Property(int, notify=estadoAlterado)
    def fichaEmEdicaoId(self) -> int:
        return self._ficha_id

    @Property(bool, notify=estadoAlterado)
    def editando(self) -> bool:
        return self._ficha_id > 0

    @Property(int, notify=estadoAlterado)
    def totalHistorico(self) -> int:
        return self._history.rowCount()

    @Property(list, notify=estadoAlterado)
    def anexos(self) -> list[dict]:
        remotos = [
            {
                "nome": str(item.get("nome") or "Anexo"),
                "local": False,
                "caminho": str(item.get("caminho") or ""),
            }
            for item in self._anexos_existentes
            if isinstance(item, dict) and item.get("caminho")
        ]
        locais = [
            {"nome": Path(caminho).name, "local": True, "caminho": caminho}
            for caminho in self._anexos_locais
        ]
        return remotos + locais

    @Property(list, notify=anexosVisualizacaoAlterados)
    def anexosVisualizacao(self) -> list[dict]:
        return list(self._anexos_visualizacao)

    @Property(bool, notify=estadoAlterado)
    def construindoModelo(self) -> bool:
        return self._construindo

    @Property(list, notify=estadoAlterado)
    def camposConstrutor(self) -> list[dict]:
        return self._campos_construtor

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
                self._resultado.emit((operacao, None), erro)

        futuro.add_done_callback(concluido)

    def _modelo_por_nome(self, nome: str) -> dict:
        return next(
            (
                modelo for modelo in self._modelos
                if modelo["nome"] == str(nome)
            ),
            self._modelos[0],
        )

    @Slot()
    def carregar(self) -> None:
        if self._ocupado:
            return

        def tarefa():
            return {
                "pacientes": self._database.listar_pacientes_fichas_interface(),
                "modelos": self._database.listar_modelos_fichas_interface(),
            }

        self._enviar("carregar", tarefa)

    @Slot(int)
    def selecionarPaciente(self, paciente_id: int) -> None:
        paciente_id = int(paciente_id or 0)
        if self._ocupado or paciente_id == self._paciente_id:
            return
        self._paciente_id = paciente_id
        self._ficha_id = 0
        self.estadoAlterado.emit()
        if not paciente_id:
            self._history.substituir([])
            return
        self._enviar(
            "historico",
            lambda: self._database.listar_historico_fichas_interface(
                paciente_id
            ),
        )

    @Slot(str)
    def selecionarModelo(self, nome: str) -> None:
        if self._ocupado:
            return
        modelo = self._modelo_por_nome(str(nome))
        self._modelo_nome = modelo["nome"]
        self._campos = normalizar_estrutura(modelo["estrutura"])
        self._ficha_id = 0
        self.estadoAlterado.emit()
        self.formularioCarregado.emit(respostas_iniciais(self._campos))

    @Slot()
    def novaFicha(self) -> None:
        self._ficha_id = 0
        self._anexos_existentes = []
        self._anexos_locais = []
        modelo = self._modelo_por_nome(self._modelo_nome)
        self._campos = normalizar_estrutura(modelo["estrutura"])
        self.estadoAlterado.emit()
        self.formularioCarregado.emit(respostas_iniciais(self._campos))

    @Slot(int)
    def abrirFicha(self, ficha_id: int) -> None:
        if self._ocupado or not ficha_id:
            return
        self._enviar(
            "abrir",
            lambda: self._database.obter_ficha_interface(int(ficha_id)),
        )

    @Slot(int)
    def visualizarAnexosFicha(self, ficha_id: int) -> None:
        if self._ocupado or not ficha_id:
            return
        self._enviar(
            "visualizar_anexos",
            lambda: self._database.obter_ficha_interface(int(ficha_id)),
        )

    @Slot()
    def escolherAnexos(self) -> None:
        caminhos, _ = QFileDialog.getOpenFileNames(
            None,
            "Selecionar fotos ou PDFs",
            "",
            "Arquivos suportados (*.jpg *.jpeg *.png *.webp *.pdf)",
        )
        adicionados = 0
        ignorados = 0
        permitidas = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
        for caminho in caminhos:
            arquivo = Path(caminho)
            if (
                not arquivo.is_file()
                or arquivo.suffix.casefold() not in permitidas
                or caminho in self._anexos_locais
            ):
                ignorados += 1
                continue
            self._anexos_locais.append(caminho)
            adicionados += 1
        if adicionados:
            self.estadoAlterado.emit()
            self.feedback.emit(
                "success",
                (
                    f"{adicionados} arquivo(s) adicionado(s). "
                    "Eles serão enviados quando a ficha for salva."
                ),
            )
        elif caminhos and ignorados:
            self.feedback.emit(
                "warning",
                "Os arquivos escolhidos já estavam na ficha ou não são suportados.",
            )

    @Slot()
    def importarModeloDocumento(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            None,
            "Importar modelo de ficha",
            "",
            "Documentos suportados (*.docx *.pdf)",
        )
        if not caminho:
            return

        def tarefa():
            extensao = Path(caminho).suffix.casefold()
            blocos = (
                extrair_blocos_docx(caminho)
                if extensao == ".docx"
                else extrair_blocos_pdf(caminho)
            )
            return Path(caminho).stem, normalizar_estrutura(
                interpretar_blocos(blocos)
            )

        self._enviar("importar_modelo", tarefa)

    @Slot(int)
    def removerAnexo(self, indice: int) -> None:
        indice = int(indice)
        if 0 <= indice < len(self._anexos_existentes):
            self._anexos_existentes.pop(indice)
            self.estadoAlterado.emit()
            self.feedback.emit(
                "success",
                "O anexo será removido quando você salvar as alterações.",
            )
            return
        indice_local = indice - len(self._anexos_existentes)
        if 0 <= indice_local < len(self._anexos_locais):
            self._anexos_locais.pop(indice_local)
            self.estadoAlterado.emit()

    @Slot(int)
    def abrirAnexo(self, indice: int) -> None:
        anexos = self.anexos
        if not 0 <= int(indice) < len(anexos):
            return
        item = anexos[int(indice)]
        if item["local"]:
            if not QDesktopServices.openUrl(
                QUrl.fromLocalFile(item["caminho"])
            ):
                self.feedback.emit(
                    "error",
                    "Não foi possível abrir este arquivo no computador.",
                )
            return
        self._enviar(
            "abrir_anexo",
            lambda: self._database.criar_link_anexo_interface(item["caminho"]),
        )

    @Slot(int)
    def abrirAnexoVisualizacao(self, indice: int) -> None:
        indice = int(indice)
        if not 0 <= indice < len(self._anexos_visualizacao):
            return
        item = self._anexos_visualizacao[indice]
        caminho = str(item.get("caminho") or "")
        if not caminho:
            return
        self._enviar(
            "abrir_anexo",
            lambda: self._database.criar_link_anexo_interface(caminho),
        )

    def _dados_exportacao(self, respostas: dict) -> dict | None:
        if not self._paciente_id:
            self.feedback.emit(
                "warning",
                "Selecione um paciente antes de exportar a ficha.",
            )
            return None
        paciente = next(
            (
                item for item in self._pacientes
                if int(item.get("id") or 0) == self._paciente_id
            ),
            {},
        )
        sessao = (
            getattr(
                getattr(self._database, "session_manager", None),
                "_session",
                None,
            )
            or {}
        )
        obter_profissional = getattr(
            self._database, "obter_nome_profissional", lambda: ""
        )
        return preparar_dados_exportacao(
            self._campos,
            dict(respostas or {}),
            paciente.get("nome") or "Paciente",
            self._modelo_nome,
            sessao.get("nome_clinica") or "",
            obter_profissional() or "",
        )

    @Slot("QVariantMap")
    def exportarWord(self, respostas: dict) -> None:
        dados = self._dados_exportacao(respostas)
        if not dados:
            return
        sugestao = nome_arquivo_exportacao(dados, ".docx")
        caminho, _ = QFileDialog.getSaveFileName(
            None,
            "Exportar ficha para Word",
            sugestao,
            "Documento Word (*.docx)",
        )
        if not caminho:
            return
        if not caminho.casefold().endswith(".docx"):
            caminho += ".docx"
        try:
            logo = Path(__file__).parent / "assets" / "prontu_logo.png"
            exportar_ficha_word(dados, caminho, logo)
            self.feedback.emit("success", "Ficha exportada em Word com sucesso.")
        except Exception:
            self.feedback.emit(
                "error",
                "Não foi possível gerar o arquivo Word.",
            )

    @Slot("QVariantMap")
    def exportarPdf(self, respostas: dict) -> None:
        dados = self._dados_exportacao(respostas)
        if not dados:
            return
        sugestao = nome_arquivo_exportacao(dados, ".pdf")
        caminho, _ = QFileDialog.getSaveFileName(
            None,
            "Exportar ficha para PDF",
            sugestao,
            "Documento PDF (*.pdf)",
        )
        if not caminho:
            return
        if not caminho.casefold().endswith(".pdf"):
            caminho += ".pdf"
        try:
            documento = QTextDocument()
            documento.setHtml(html_exportacao_ficha(dados))
            impressora = QPrinter(QPrinter.PrinterMode.HighResolution)
            impressora.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            impressora.setOutputFileName(caminho)
            documento.print_(impressora)
            self.feedback.emit("success", "Ficha exportada em PDF com sucesso.")
        except Exception:
            self.feedback.emit(
                "error",
                "Não foi possível gerar o arquivo PDF.",
            )

    @Slot(bool)
    def iniciarConstrutor(self, editar_atual: bool = False) -> None:
        modelo = self._modelo_por_nome(self._modelo_nome)
        if editar_atual and "padrão" in modelo["nome"].casefold():
            self.feedback.emit(
                "warning",
                "O modelo padrão não pode ser alterado. Crie um novo modelo.",
            )
            return
        self._campos_construtor = (
            normalizar_estrutura(modelo["estrutura"]) if editar_atual else []
        )
        self._construindo = True
        self.estadoAlterado.emit()

    @Slot()
    def cancelarConstrutor(self) -> None:
        self._construindo = False
        self._campos_construtor = []
        self.estadoAlterado.emit()

    @Slot("QVariantMap")
    def adicionarCampoConstrutor(self, campo: dict) -> None:
        novos = list(self._campos_construtor)
        novos.append(dict(campo or {}))
        self._campos_construtor = normalizar_estrutura(novos)
        self.estadoAlterado.emit()

    @Slot(int, "QVariantMap")
    def atualizarCampoConstrutor(self, indice: int, campo: dict) -> None:
        if not 0 <= int(indice) < len(self._campos_construtor):
            return
        novo = dict(campo or {})
        novo["id"] = self._campos_construtor[int(indice)].get("id")
        self._campos_construtor[int(indice)] = novo
        self._campos_construtor = normalizar_estrutura(self._campos_construtor)
        self.estadoAlterado.emit()

    @Slot(int, int)
    def moverCampoConstrutor(self, indice: int, direcao: int) -> None:
        destino = int(indice) + int(direcao)
        if 0 <= int(indice) < len(self._campos_construtor) and 0 <= destino < len(
            self._campos_construtor
        ):
            self._campos_construtor[int(indice)], self._campos_construtor[destino] = (
                self._campos_construtor[destino],
                self._campos_construtor[int(indice)],
            )
            self.estadoAlterado.emit()

    @Slot(int)
    def removerCampoConstrutor(self, indice: int) -> None:
        if 0 <= int(indice) < len(self._campos_construtor):
            self._campos_construtor.pop(int(indice))
            self.estadoAlterado.emit()

    @Slot(str)
    def salvarModelo(self, nome: str) -> None:
        nome = str(nome or "").strip()
        if not nome:
            self.feedback.emit("warning", "Informe um nome para o modelo.")
            return
        if not self._campos_construtor:
            self.feedback.emit("warning", "Adicione pelo menos um campo ao modelo.")
            return
        estrutura = normalizar_estrutura(self._campos_construtor)
        self._enviar(
            "salvar_modelo",
            lambda: (
                self._database.salvar_modelo_ficha_interface(nome, estrutura),
                nome,
            ),
        )

    @Slot(str)
    def excluirModelo(self, nome: str) -> None:
        if "padrão" in str(nome).casefold():
            self.feedback.emit("warning", "O modelo padrão não pode ser excluído.")
            return
        self._enviar(
            "excluir_modelo",
            lambda: self._database.excluir_modelo_ficha_interface(str(nome)),
        )

    @Slot(int, str, "QVariantMap")
    def salvar(
        self, paciente_id: int, modelo_nome: str, respostas: dict
    ) -> None:
        if self._ocupado:
            return
        paciente_id = int(paciente_id or 0)
        if not paciente_id:
            self.feedback.emit("warning", "Selecione um paciente antes de salvar.")
            return
        valido, vazios = validar_respostas(self._campos, dict(respostas or {}))
        if not valido:
            self.feedback.emit(
                "warning",
                "Preencha os campos obrigatórios: " + ", ".join(vazios) + ".",
            )
            return
        ficha_id = self._ficha_id or None
        nome = str(modelo_nome or self._modelo_nome)

        def tarefa():
            return self._database.salvar_ficha_interface(
                ficha_id,
                paciente_id,
                nome,
                dict(respostas or {}),
                list(self._anexos_locais),
                list(self._anexos_existentes),
            )

        self._enviar("salvar", tarefa)

    @Slot(object, object)
    def _receber_resultado(self, pacote, erro) -> None:
        self._definir_ocupado(False)
        operacao, resultado = pacote or ("", None)
        if erro:
            if (
                operacao == "salvar"
                and erro.__class__.__name__ == "ErroAnexoFicha"
            ):
                self.feedback.emit("error", str(erro))
                return
            self.feedback.emit("error", "Não foi possível concluir esta operação.")
            return

        if operacao == "carregar":
            dados = resultado or {}
            self._pacientes = list(dados.get("pacientes") or [])
            self._modelos = list(dados.get("modelos") or self._modelos)
            if self._pacientes and not self._paciente_id:
                self._paciente_id = int(self._pacientes[0].get("id") or 0)
            modelo = self._modelo_por_nome(self._modelo_nome)
            self._modelo_nome = modelo["nome"]
            self._campos = normalizar_estrutura(modelo["estrutura"])
            self.estadoAlterado.emit()
            self.formularioCarregado.emit(respostas_iniciais(self._campos))
            if self._paciente_id:
                paciente_id = self._paciente_id
                self._enviar(
                    "historico",
                    lambda: self._database.listar_historico_fichas_interface(
                        paciente_id
                    ),
                )
            return

        if operacao == "historico":
            self._history.substituir(list(resultado or []))
            self.estadoAlterado.emit()
            return

        if operacao == "abrir":
            if not resultado:
                self.feedback.emit("error", "Não foi possível abrir esta ficha.")
                return
            ficha = dict(resultado)
            self._ficha_id = int(ficha.get("id") or 0)
            self._paciente_id = int(ficha.get("paciente_id") or 0)
            self._modelo_nome = str(
                ficha.get("modelo_nome") or NOME_MODELO_PADRAO
            )
            self._campos = normalizar_estrutura(ficha.get("estrutura") or [])
            anexos = ficha.get("anexos") or []
            self._anexos_existentes = list(anexos) if isinstance(anexos, list) else []
            self._anexos_locais = []
            self.estadoAlterado.emit()
            self.formularioCarregado.emit(
                dict(ficha.get("dados_respostas") or {})
            )
            return

        if operacao == "visualizar_anexos":
            ficha = dict(resultado or {})
            anexos = ficha.get("anexos") or []
            if not isinstance(anexos, list):
                anexos = []
            self._anexos_visualizacao = [
                {
                    "nome": str(item.get("nome") or "Anexo"),
                    "caminho": str(item.get("caminho") or ""),
                }
                for item in anexos
                if isinstance(item, dict) and item.get("caminho")
            ]
            self.anexosVisualizacaoAlterados.emit()
            if not self._anexos_visualizacao:
                self.feedback.emit(
                    "warning",
                    "Esta ficha não possui fotos ou PDFs anexados.",
                )
                return
            self.visualizacaoAnexosPronta.emit(
                str(ficha.get("modelo_nome") or "Ficha clínica")
            )
            return

        if operacao == "salvar":
            if not resultado:
                self.feedback.emit("error", "Não foi possível salvar a ficha.")
                return
            estava_editando = self._ficha_id > 0
            self._ficha_id = 0
            self._anexos_existentes = []
            self._anexos_locais = []
            self.estadoAlterado.emit()
            self.feedback.emit(
                "success",
                "Alterações salvas no atendimento original."
                if estava_editando
                else "Atendimento registrado com sucesso.",
            )
            paciente_id = self._paciente_id
            self.formularioCarregado.emit(respostas_iniciais(self._campos))
            if paciente_id:
                self._enviar(
                    "historico",
                    lambda: self._database.listar_historico_fichas_interface(
                        paciente_id
                    ),
                )
            return

        if operacao == "abrir_anexo":
            abriu = bool(resultado) and QDesktopServices.openUrl(
                QUrl.fromUserInput(str(resultado))
            )
            if not abriu:
                self.feedback.emit("error", "Não foi possível abrir o anexo.")
            return

        if operacao == "importar_modelo":
            nome, campos = resultado or ("", [])
            if not campos:
                self.feedback.emit(
                    "warning",
                    "Não encontramos campos nesse documento. "
                    "Se for um PDF digitalizado, use um arquivo com texto selecionável.",
                )
                return
            self._campos_construtor = list(campos)
            self._construindo = True
            self.estadoAlterado.emit()
            self.modeloImportado.emit(str(nome))
            return

        if operacao == "salvar_modelo":
            sucesso, nome = resultado or (False, "")
            if not sucesso:
                self.feedback.emit("error", "Não foi possível salvar o modelo.")
                return
            self._construindo = False
            self._campos_construtor = []
            self._modelo_nome = str(nome)
            self.feedback.emit("success", "Modelo salvo e pronto para uso.")
            self.carregar()
            return

        if operacao == "excluir_modelo":
            if not resultado:
                self.feedback.emit("error", "Não foi possível excluir o modelo.")
                return
            self._modelo_nome = NOME_MODELO_PADRAO
            self.feedback.emit(
                "success",
                "Modelo excluído. As fichas já preenchidas foram preservadas.",
            )
            self.carregar()
