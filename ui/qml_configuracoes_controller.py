"""Controlador assíncrono da tela QML de Configurações."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from services.backup_crypto import BackupCryptoError, BackupIntegrityError
from services.backup_service import BackupService
from services.configuracoes_service import (
    CHAVES_CONFIGURACAO,
    preparar_auditoria,
    preparar_configuracoes,
    validar_senhas_backup,
)
from utils.diagnostics import log_file_path


class ConfiguracoesController(QObject):
    estadoAlterado = Signal()
    feedback = Signal(str, str)
    dadosCarregados = Signal("QVariantMap")
    arquivoRestauracaoSelecionado = Signal(str)
    progressoBackup = Signal(str)
    sessaoDesativada = Signal()
    _resultado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-configuracoes"
        )
        self._ocupado = False
        self._dados: dict = {}
        self._auditoria_todos: list[dict] = []
        self._auditoria: list[dict] = []
        self._lembretes: list[dict] = []
        self._resumo_lembretes = "Nenhum lembrete carregado."
        self._franquia_lembretes = ""
        self._resultado.connect(self._receber_resultado)

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(bool, constant=True)
    def proprietario(self) -> bool:
        return (
            str(self._database.obter_papel_atual()).lower() == "proprietario"
        )

    @Property(bool, constant=True)
    def automacaoWhatsApp(self) -> bool:
        return bool(self._database.possui_recurso("whatsapp_automatico"))

    @Property(str, constant=True)
    def papelTexto(self) -> str:
        return {
            "proprietario": "Proprietário da clínica",
            "profissional": "Profissional",
            "secretaria": "Secretária",
        }.get(
            str(self._database.obter_papel_atual()).lower(),
            "Integrante da equipe",
        )

    @Property("QVariantList", notify=estadoAlterado)
    def auditoria(self) -> list[dict]:
        return self._auditoria

    @Property("QVariantList", notify=estadoAlterado)
    def lembretes(self) -> list[dict]:
        return self._lembretes

    @Property(str, notify=estadoAlterado)
    def resumoLembretes(self) -> str:
        return self._resumo_lembretes

    @Property(str, notify=estadoAlterado)
    def franquiaLembretes(self) -> str:
        return self._franquia_lembretes

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

    def _carregar_tudo(self) -> dict:
        resumo = self._database.obter_resumo_assinatura()
        nome = self._database.obter_nome_profissional()
        valores = self._database.obter_configuracoes(CHAVES_CONFIGURACAO)
        return preparar_configuracoes(resumo, nome, valores)

    @Slot()
    def carregar(self) -> None:
        if not self._ocupado:
            self._enviar("carregar", self._carregar_tudo)

    @Slot(str)
    def salvarPerfil(self, nome: str) -> None:
        nome = str(nome or "").strip()
        if not nome:
            self.feedback.emit("warning", "Informe seu nome de exibição.")
            return
        if not self._ocupado:
            self._enviar(
                "salvar_perfil",
                lambda: self._database.salvar_nome_profissional(nome),
            )

    @Slot(str, str)
    def salvarMensagens(self, manual: str, lembrete: str) -> None:
        manual = str(manual or "").strip()
        lembrete = str(lembrete or "").strip()
        if not manual or not lembrete:
            self.feedback.emit("warning", "Preencha as duas mensagens.")
            return

        def salvar():
            if not self._database.salvar_configuracao(
                "whatsapp_mensagem_manual", manual
            ):
                return False
            if not self._database.salvar_configuracao(
                "whatsapp_mensagem_lembrete", lembrete
            ):
                return False
            confirmado = self._database.obter_configuracoes([
                "whatsapp_mensagem_manual",
                "whatsapp_mensagem_lembrete",
            ])
            return (
                confirmado.get("whatsapp_mensagem_manual") == manual
                and confirmado.get("whatsapp_mensagem_lembrete") == lembrete
            )

        if not self._ocupado:
            self._enviar("salvar_mensagens", salvar)

    @Slot(result=str)
    def escolherPastaBackup(self) -> str:
        atual = str(self._dados.get("backup_dir") or "")
        return QFileDialog.getExistingDirectory(
            None, "Escolha a pasta dos backups", atual
        )

    @Slot()
    def escolherArquivoRestauracao(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            None, "Selecionar backup", "", "Backup Prontu (*.prntbk)"
        )
        if caminho:
            self.arquivoRestauracaoSelecionado.emit(caminho)

    @Slot(str, str, str, int, bool)
    def executarBackup(
        self,
        destino: str,
        senha: str,
        confirmacao: str,
        retencao: int,
        anexos: bool,
    ) -> None:
        destino = str(destino or "").strip()
        if not destino:
            self.feedback.emit("warning", "Escolha a pasta do backup.")
            return
        problema = validar_senhas_backup(senha, confirmacao)
        if problema:
            self.feedback.emit("warning", problema)
            return

        def executar():
            Path(destino).mkdir(parents=True, exist_ok=True)
            configuracoes = {
                "backup_dir": destino,
                "backup_freq": "manual",
                "backup_retencao": str(max(1, int(retencao))),
                "backup_include_attachments": "1" if anexos else "0",
            }
            for chave, valor in configuracoes.items():
                if not self._database.salvar_configuracao(chave, valor):
                    raise RuntimeError(
                        "Não foi possível salvar as configurações do backup."
                    )
            servico = BackupService(self._database)
            resultado = servico.create_backup(
                destino,
                senha,
                include_attachments=bool(anexos),
                retention_days=max(1, int(retencao)),
                on_progress=lambda texto: self.progressoBackup.emit(texto),
            )
            BackupService.update_backup_status(self._database, resultado)
            return resultado

        if not self._ocupado:
            self._enviar("backup", executar)

    @Slot(str, str, bool, str)
    def restaurarBackup(
        self,
        caminho: str,
        senha: str,
        substituir: bool,
        confirmacao: str,
    ) -> None:
        if not caminho or not senha:
            self.feedback.emit(
                "warning", "Selecione o arquivo e informe sua senha."
            )
            return
        if substituir and str(confirmacao).strip().upper() != "SUBSTITUIR":
            self.feedback.emit(
                "warning", "Digite SUBSTITUIR para confirmar esta operação."
            )
            return

        def restaurar():
            return BackupService(self._database).restore_backup(
                caminho,
                senha,
                safe_mode=not substituir,
                replace_existing=substituir,
                on_progress=lambda texto: self.progressoBackup.emit(texto),
            )

        if not self._ocupado:
            self._enviar("restaurar", restaurar)

    @Slot()
    def abrirDiagnostico(self) -> None:
        pasta = log_file_path().parent
        pasta.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))

    @Slot()
    def carregarAuditoria(self) -> None:
        if not self.proprietario:
            self.feedback.emit(
                "warning", "A auditoria é exclusiva do proprietário."
            )
            return
        if not self._ocupado:
            self._enviar(
                "auditoria", self._database.listar_eventos_auditoria
            )

    @Slot(str)
    def filtrarAuditoria(self, area: str) -> None:
        area = str(area or "")
        self._auditoria = [
            item for item in self._auditoria_todos
            if not area or item.get("area_codigo") == area
        ]
        self.estadoAlterado.emit()

    @Slot()
    def carregarLembretes(self) -> None:
        if not self.automacaoWhatsApp:
            self.feedback.emit(
                "warning",
                "A automação ainda não está habilitada neste consultório.",
            )
            return
        if not self._ocupado:
            self._enviar(
                "lembretes",
                self._database.listar_lembretes_whatsapp_interface,
            )

    @Slot()
    def desativarDispositivo(self) -> None:
        self._database.desativar_dispositivo()
        self.sessaoDesativada.emit()

    @Slot(object, object)
    def _receber_resultado(self, pacote, erro) -> None:
        self._definir_ocupado(False)
        operacao, resultado = pacote or ("", None)
        if erro:
            if isinstance(
                erro,
                (
                    BackupCryptoError,
                    BackupIntegrityError,
                    RuntimeError,
                    ValueError,
                ),
            ):
                mensagem = str(erro)
            else:
                mensagem = "Não foi possível concluir esta operação."
            if operacao == "backup":
                BackupService.update_backup_status(
                    self._database, None, str(erro)
                )
            self.feedback.emit("error", mensagem)
            return
        if operacao == "carregar":
            self._dados = dict(resultado or {})
            self.dadosCarregados.emit(self._dados)
            self.estadoAlterado.emit()
            return
        if operacao == "salvar_perfil":
            self.feedback.emit(
                "success" if resultado else "error",
                "Perfil atualizado."
                if resultado else "Não foi possível salvar seu perfil.",
            )
            return
        if operacao == "salvar_mensagens":
            self.feedback.emit(
                "success" if resultado else "error",
                "Mensagens salvas e confirmadas."
                if resultado else "Não foi possível confirmar as mensagens.",
            )
            return
        if operacao == "backup":
            tamanho = int((resultado or {}).get("size_bytes") or 0) // 1024
            removidos = int((resultado or {}).get("expired_removed") or 0)
            mensagem = f"Backup concluído ({tamanho} KB)."
            if removidos:
                mensagem += f" {removidos} arquivo(s) antigo(s) removido(s)."
            self.feedback.emit("success", mensagem)
            self.carregar()
            return
        if operacao == "restaurar":
            dados = resultado or {}
            self.feedback.emit(
                "success",
                "Restauração concluída: "
                f"{dados.get('inserted', 0)} inserido(s), "
                f"{dados.get('skipped', 0)} ignorado(s) e "
                f"{dados.get('removed', 0)} removido(s).",
            )
            self.carregar()
            return
        if operacao == "auditoria":
            self._auditoria_todos = preparar_auditoria(resultado or [])
            self._auditoria = list(self._auditoria_todos)
            self.estadoAlterado.emit()
            return
        if operacao == "lembretes":
            dados = resultado or {}
            self._lembretes = list(dados.get("lembretes") or [])
            self._resumo_lembretes = str(
                dados.get("resumo") or "Nenhum lembrete encontrado."
            )
            self._franquia_lembretes = str(dados.get("franquia") or "")
            self.estadoAlterado.emit()
