import os
import json
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QFrame, QMessageBox,
                               QComboBox, QCheckBox, QFileDialog, QInputDialog,
                               QSpinBox, QDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from ui.design_system import definir_variante

from services.backup_service import BackupService
from services.backup_worker import BackupWorker


MENSAGEM_WHATSAPP_MANUAL_PADRAO = (
    "Olá, {paciente}! Tudo bem? Aqui é {profissional}, da clínica. "
    "Como podemos ajudar?"
)
MENSAGEM_LEMBRETE_CONSULTA_PADRAO = (
    "Olá, {paciente}! Lembramos que sua consulta está marcada para {data} às {hora}. "
    "Procedimento: {procedimento}. Por favor, confirme sua presença."
)


class MensagensWhatsAppDialog(QDialog):
    """Centraliza os textos usados manualmente e pela futura automação."""

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.db = database
        self.setWindowTitle("Mensagens do WhatsApp")
        self.setMinimumWidth(590)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        titulo = QLabel("Mensagens do WhatsApp")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        layout.addWidget(titulo)
        explicacao = QLabel(
            "Use {paciente} e {profissional} na mensagem manual. "
            "No lembrete, também estão disponíveis {data}, {hora} e {procedimento}."
        )
        explicacao.setWordWrap(True)
        explicacao.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(explicacao)

        layout.addWidget(QLabel("Mensagem ao clicar no botão Zap:"))
        self.input_manual = QTextEdit()
        self.input_manual.setMinimumHeight(92)
        self.input_manual.setPlaceholderText(MENSAGEM_WHATSAPP_MANUAL_PADRAO)
        layout.addWidget(self.input_manual)

        layout.addWidget(QLabel("Mensagem de lembrete de consulta (para automação futura):"))
        self.input_lembrete = QTextEdit()
        self.input_lembrete.setMinimumHeight(108)
        self.input_lembrete.setPlaceholderText(MENSAGEM_LEMBRETE_CONSULTA_PADRAO)
        layout.addWidget(self.input_lembrete)

        botoes = QHBoxLayout()
        botoes.addStretch()
        cancelar = QPushButton("Cancelar")
        salvar = QPushButton("Salvar mensagens")
        definir_variante(salvar, "primary")
        cancelar.clicked.connect(self.reject)
        salvar.clicked.connect(self.salvar)
        botoes.addWidget(cancelar)
        botoes.addWidget(salvar)
        layout.addLayout(botoes)
        self.carregar()

    def carregar(self):
        valores = self.db.obter_configuracoes([
            "whatsapp_mensagem_manual", "whatsapp_mensagem_lembrete",
        ])
        self.input_manual.setPlainText(
            valores.get("whatsapp_mensagem_manual") or MENSAGEM_WHATSAPP_MANUAL_PADRAO
        )
        self.input_lembrete.setPlainText(
            valores.get("whatsapp_mensagem_lembrete") or MENSAGEM_LEMBRETE_CONSULTA_PADRAO
        )

    def salvar(self):
        manual = self.input_manual.toPlainText().strip()
        lembrete = self.input_lembrete.toPlainText().strip()
        if not manual or not lembrete:
            QMessageBox.warning(self, "Mensagens incompletas", "Preencha as duas mensagens antes de salvar.")
            return
        ok_manual = self.db.salvar_configuracao("whatsapp_mensagem_manual", manual)
        ok_lembrete = self.db.salvar_configuracao("whatsapp_mensagem_lembrete", lembrete)
        if not (ok_manual and ok_lembrete):
            QMessageBox.warning(self, "Não foi possível salvar", "As mensagens não foram salvas. Tente novamente.")
            return
        self.accept()


def configurar_visibilidade_senha(campo: QLineEdit) -> None:
    """Permite conferir uma senha sem deixá-la visível por padrão."""
    campo.setEchoMode(QLineEdit.EchoMode.Password)
    acao = QAction("Mostrar", campo)
    campo.addAction(acao, QLineEdit.ActionPosition.TrailingPosition)
    acao.setToolTip("Mostrar senha")

    def alternar() -> None:
        visivel = campo.echoMode() == QLineEdit.EchoMode.Password
        campo.setEchoMode(
            QLineEdit.EchoMode.Normal if visivel else QLineEdit.EchoMode.Password
        )
        acao.setText("Ocultar" if visivel else "Mostrar")
        acao.setToolTip("Ocultar senha" if visivel else "Mostrar senha")

    acao.triggered.connect(alternar)


class HistoricoAuditoriaDialog(QDialog):
    """Consulta apenas os metadados imutáveis do histórico do consultório."""

    NOMES_ACAO = {
        "INSERT": "Criado",
        "UPDATE": "Atualizado",
        "DELETE": "Excluído",
        "BACKUP_CREATED": "Backup concluído",
        "EXPORT": "Documento exportado",
    }
    NOMES_ENTIDADE = {
        "pacientes": "Pacientes",
        "agenda": "Agenda",
        "fichas_preenchidas": "Fichas clínicas",
        "modelos_fichas": "Modelos de ficha",
        "pastas": "Pastas",
        "configuracoes": "Configurações",
        "pagamentos_consultas": "Financeiro",
        "retornos_pacientes": "Retornos",
        "backup": "Backup",
    }
    NOMES_CAMPOS = {
        "nome": "Nome", "convenio": "Convênio", "pasta": "Pasta", "sexo": "Sexo",
        "status": "Status", "procedimento": "Procedimento", "data": "Data",
        "horario": "Horário", "duracao_txt": "Duração", "deleted_at": "Arquivamento",
        "status_pagamento": "Status do pagamento", "valor": "Valor da consulta",
        "valor_recebido": "Valor recebido", "forma_pagamento": "Forma de pagamento",
        "data_prevista": "Data prevista do retorno",
    }
    CAMPOS_PRIVADOS = {
        "id", "consultorio_id", "auth_user_id", "created_at", "updated_at", "criado_em",
        "dados_respostas", "anexos", "queixa", "queixa_principal", "endereco", "telefone",
        "nascimento", "cpf", "rg", "observacao", "valor_anterior", "valor_novo",
    }

    def __init__(self, database_instancia, parent=None):
        super().__init__(parent)
        self.db = database_instancia
        self.eventos = []
        self.setWindowTitle("Histórico de Auditoria")
        self.resize(900, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        titulo = QLabel("Histórico de Auditoria")
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #0f172a;")
        descricao = QLabel(
            "Acompanhe ações importantes do consultório. Dados clínicos e conteúdos de fichas não são exibidos aqui."
        )
        descricao.setWordWrap(True)
        descricao.setStyleSheet("font-size: 12px; color: #64748b;")
        layout.addWidget(titulo)
        layout.addWidget(descricao)

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Mostrar:"))
        self.combo_area = QComboBox()
        self.combo_area.addItem("Todas as áreas", "")
        for texto, valor in [
            ("Pacientes", "pacientes"), ("Agenda", "agenda"),
            ("Fichas clínicas", "fichas_preenchidas"), ("Financeiro", "pagamentos_consultas"),
            ("Retornos", "retornos_pacientes"), ("Configurações", "configuracoes"), ("Backup", "backup"),
        ]:
            self.combo_area.addItem(texto, valor)
        self.combo_area.currentIndexChanged.connect(self.renderizar_eventos)
        filtros.addWidget(self.combo_area)
        filtros.addStretch()
        btn_atualizar = QPushButton("Atualizar")
        definir_variante(btn_atualizar, "secondary")
        btn_atualizar.clicked.connect(self.carregar_eventos)
        filtros.addWidget(btn_atualizar)
        layout.addLayout(filtros)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(4)
        self.tabela.setHorizontalHeaderLabels(["Data e hora", "Ação", "Área", "O que mudou"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabela)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)
        self.carregar_eventos()

    def carregar_eventos(self):
        self.eventos = self.db.listar_eventos_auditoria() if self.db else []
        self.renderizar_eventos()

    @staticmethod
    def _formatar_data(valor):
        try:
            data = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
            return data.astimezone().strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            return str(valor or "Não informado")

    def renderizar_eventos(self):
        area = self.combo_area.currentData()
        eventos = [evento for evento in self.eventos if not area or evento.get("entidade") == area]
        self.tabela.setRowCount(0)
        for linha, evento in enumerate(eventos):
            self.tabela.insertRow(linha)
            acao = self.NOMES_ACAO.get(evento.get("acao"), str(evento.get("acao") or "Ação registrada"))
            entidade = evento.get("entidade") or ""
            area_nome = self.NOMES_ENTIDADE.get(entidade, entidade.replace("_", " ").capitalize())
            valores = [
                self._formatar_data(evento.get("criado_em")), acao, area_nome,
                self._resumir_alteracao(evento),
            ]
            for coluna, valor in enumerate(valores):
                self.tabela.setItem(linha, coluna, QTableWidgetItem(valor))

        self.lbl_status.setText(
            f"{len(eventos)} evento(s) exibido(s). O histórico é somente leitura."
        )

    @staticmethod
    def _como_dicionario(valor):
        if isinstance(valor, dict):
            return valor
        if isinstance(valor, str):
            try:
                return json.loads(valor)
            except json.JSONDecodeError:
                return {}
        return {}

    def _resumir_alteracao(self, evento):
        """Cria um resumo legível sem expor valores clínicos ou dados pessoais."""
        acao = evento.get("acao") or ""
        entidade = evento.get("entidade") or ""
        contexto = self._como_dicionario(evento.get("contexto"))

        if entidade == "pagamentos_consultas" and contexto.get("status_pagamento"):
            return f"Status do pagamento: {contexto['status_pagamento']}"
        if acao == "INSERT":
            return "Novo registro adicionado"
        if acao == "DELETE":
            return "Registro removido"

        anterior = self._como_dicionario(evento.get("valor_anterior"))
        novo = self._como_dicionario(evento.get("valor_novo"))
        campos = []
        for campo in set(anterior) | set(novo):
            if campo in self.CAMPOS_PRIVADOS or anterior.get(campo) == novo.get(campo):
                continue
            campos.append(self.NOMES_CAMPOS.get(campo, campo.replace("_", " ").capitalize()))

        if "Arquivamento" in campos:
            return "Registro arquivado"
        if campos:
            return "Alterado: " + ", ".join(sorted(campos)[:4])
        referencia = evento.get("registro_id")
        return f"Registro #{referencia} atualizado" if referencia else "Registro atualizado"


class ConfiguracoesScreen(QWidget):
    def __init__(self, window_principal=None):
        super().__init__()
        self.setObjectName("ConfiguracoesScreen")
        self.window_principal = window_principal
        self.db = window_principal.db if window_principal else None
        self._backup_worker = None
        self._pasta_backup_padrao = os.path.join(
            os.path.expanduser("~"), "Documents", "Prontu Backups"
        )
        
        # Layout Principal com margens confortáveis
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)
        
        # --- CABEÇALHO ---
        lbl_titulo = QLabel("⚙️ Configurações do Sistema")
        lbl_titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        main_layout.addWidget(lbl_titulo)
        
        lbl_subtitulo = QLabel("Personalize os dados do aplicativo que serão exibidos nas telas e relatórios.")
        lbl_subtitulo.setStyleSheet("font-size: 14px; color: #64748b; margin-bottom: 10px;")
        main_layout.addWidget(lbl_subtitulo)

        # --- RESUMO DO PLANO ---
        container_assinatura = QFrame()
        container_assinatura.setObjectName("SectionCard")
        assinatura_layout = QHBoxLayout(container_assinatura)
        assinatura_layout.setContentsMargins(18, 12, 18, 12)
        assinatura_layout.setSpacing(10)
        titulo_assinatura = QLabel("Plano atual")
        titulo_assinatura.setStyleSheet("font-size: 13px; font-weight: bold; color: #475569;")
        assinatura_layout.addWidget(titulo_assinatura)
        self.lbl_plano_atual = QLabel("Prontu Solo")
        self.lbl_plano_atual.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
        assinatura_layout.addWidget(self.lbl_plano_atual)
        assinatura_layout.addStretch()
        self.lbl_status_assinatura = QLabel("Assinatura ativa")
        self.lbl_status_assinatura.setStyleSheet(
            "background: #dcfce7; color: #15803d; border-radius: 12px; padding: 5px 10px; font-size: 12px; font-weight: bold;"
        )
        assinatura_layout.addWidget(self.lbl_status_assinatura)
        self.lbl_limite_assinatura = QLabel("")
        self.lbl_limite_assinatura.setStyleSheet("font-size: 12px; color: #64748b;")
        assinatura_layout.addWidget(self.lbl_limite_assinatura)
        main_layout.addWidget(container_assinatura)
        
        # --- PAINEL DE PERFIL DO PROFISSIONAL ---
        container_perfil = QFrame()
        container_perfil.setObjectName("FormCard")
        
        perfil_layout = QVBoxLayout(container_perfil)
        perfil_layout.setContentsMargins(20, 20, 20, 20)
        perfil_layout.setSpacing(12)
        
        lbl_secao = QLabel("Perfil do Usuário / Médico")
        lbl_secao.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        perfil_layout.addWidget(lbl_secao)
        
        perfil_layout.addWidget(QLabel("Nome do Profissional (Ex: Dra. Laura Silva, Dr. Carlos):"))
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Digite como deseja ser saudado na página inicial...")
        perfil_layout.addWidget(self.input_nome)
        
        # Layout inferior para botões de ação
        btn_layout = QHBoxLayout()
        self.btn_auditoria = QPushButton("Histórico de Auditoria")
        definir_variante(self.btn_auditoria, "secondary")
        self.btn_auditoria.clicked.connect(self.abrir_historico_auditoria)
        self.btn_auditoria.setVisible(
            bool(self.db) and self.db.obter_papel_atual() == "proprietario"
        )
        btn_layout.addWidget(self.btn_auditoria)
        btn_layout.addStretch()
        
        self.btn_salvar = QPushButton("💾 Salvar Alterações")
        definir_variante(self.btn_salvar, "primary")
        self.btn_salvar.clicked.connect(self.salvar_configuracoes)
        btn_layout.addWidget(self.btn_salvar)
        
        perfil_layout.addLayout(btn_layout)
        main_layout.addWidget(container_perfil)

        # --- MENSAGENS DO WHATSAPP ---
        container_mensagens = QFrame()
        container_mensagens.setObjectName("FormCard")
        mensagens_layout = QHBoxLayout(container_mensagens)
        mensagens_layout.setContentsMargins(20, 16, 20, 16)
        mensagens_layout.setSpacing(14)
        texto_mensagens = QVBoxLayout()
        titulo_mensagens = QLabel("Mensagens do WhatsApp")
        titulo_mensagens.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        descricao_mensagens = QLabel(
            "Personalize o texto enviado pelo botão Zap e deixe o lembrete automático pronto para quando ele for ativado."
        )
        descricao_mensagens.setWordWrap(True)
        descricao_mensagens.setStyleSheet("color: #64748b; font-size: 12px;")
        texto_mensagens.addWidget(titulo_mensagens)
        texto_mensagens.addWidget(descricao_mensagens)
        mensagens_layout.addLayout(texto_mensagens, 1)
        btn_mensagens = QPushButton("Configurar mensagens")
        definir_variante(btn_mensagens, "secondary")
        btn_mensagens.clicked.connect(self.abrir_configuracao_mensagens)
        mensagens_layout.addWidget(btn_mensagens)
        main_layout.addWidget(container_mensagens)

        # --- PAINEL DE BACKUP LOCAL CRIPTOGRAFADO ---
        container_backup = QFrame()
        container_backup.setObjectName("FormCard")
        backup_layout = QVBoxLayout(container_backup)
        backup_layout.setContentsMargins(20, 20, 20, 20)
        backup_layout.setSpacing(10)

        lbl_backup = QLabel("Backup Local Criptografado")
        lbl_backup.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        backup_layout.addWidget(lbl_backup)

        backup_layout.addWidget(QLabel("Pasta de destino:"))
        pasta_row = QHBoxLayout()
        self.input_backup_dir = QLineEdit()
        self.input_backup_dir.setText(self._pasta_backup_padrao)
        self.input_backup_dir.setReadOnly(True)
        self.input_backup_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.input_backup_dir.setToolTip("Clique para escolher onde os backups serao guardados")
        self.input_backup_dir.mousePressEvent = self._abrir_seletor_pasta_backup
        btn_escolher_pasta = QPushButton("Escolher...")
        btn_escolher_pasta.setFixedWidth(100)
        definir_variante(btn_escolher_pasta, "secondary")
        btn_escolher_pasta.clicked.connect(self._escolher_pasta_backup)
        pasta_row.addWidget(self.input_backup_dir)
        pasta_row.addWidget(btn_escolher_pasta)
        backup_layout.addLayout(pasta_row)

        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("Frequência:"))
        self.combo_backup_freq = QComboBox()
        self.combo_backup_freq.addItems(["manual", "diaria", "semanal"])
        self.combo_backup_freq.setFixedWidth(120)
        freq_row.addWidget(self.combo_backup_freq)
        freq_row.addWidget(QLabel("Retenção (dias):"))
        self.input_retencao = QSpinBox()
        self.input_retencao.setRange(1, 3650)
        self.input_retencao.setValue(30)
        self.input_retencao.setFixedWidth(90)
        freq_row.addWidget(self.input_retencao)
        freq_row.addStretch()
        backup_layout.addLayout(freq_row)

        self.chk_incluir_anexos = QCheckBox("Incluir metadados de anexos no backup")
        backup_layout.addWidget(self.chk_incluir_anexos)

        senha_row = QHBoxLayout()
        senha_row.addWidget(QLabel("Senha de recuperação:"))
        self.input_backup_senha = QLineEdit()
        configurar_visibilidade_senha(self.input_backup_senha)
        self.input_backup_senha.setPlaceholderText("Defina e confirme ao executar backup")
        senha_row.addWidget(self.input_backup_senha)
        backup_layout.addLayout(senha_row)

        self.lbl_backup_status = QLabel("Último backup: nunca executado")
        self.lbl_backup_status.setWordWrap(True)
        self.lbl_backup_status.setStyleSheet("color: #64748b; font-size: 12px;")
        backup_layout.addWidget(self.lbl_backup_status)

        btn_backup_row = QHBoxLayout()
        self.btn_backup_agora = QPushButton("Executar backup agora")
        self.btn_backup_agora.setFixedWidth(155)
        definir_variante(self.btn_backup_agora, "primary")
        self.btn_backup_agora.clicked.connect(self._executar_backup_manual)
        self.btn_restaurar = QPushButton("Restaurar backup...")
        self.btn_restaurar.setFixedWidth(140)
        definir_variante(self.btn_restaurar, "secondary")
        self.btn_restaurar.clicked.connect(self._restaurar_backup)
        self.btn_desativar = QPushButton("Desativar dispositivo")
        self.btn_desativar.setFixedWidth(155)
        definir_variante(self.btn_desativar, "danger")
        self.btn_desativar.clicked.connect(self._desativar_dispositivo)
        btn_backup_row.addWidget(self.btn_backup_agora)
        btn_backup_row.addWidget(self.btn_restaurar)
        btn_backup_row.addWidget(self.btn_desativar)
        backup_layout.addLayout(btn_backup_row)

        main_layout.addWidget(container_backup)
        main_layout.addStretch()
        
        # Executa a busca inicial de dados para preencher a tela
        self.carregar_dados_configurados()

    def _abrir_seletor_pasta_backup(self, event):
        self._escolher_pasta_backup()

    def abrir_historico_auditoria(self):
        if not self.db or not self.db.supabase:
            QMessageBox.warning(
                self, "Histórico indisponível",
                "Não há uma conexão segura ativa para consultar o histórico agora."
            )
            return
        HistoricoAuditoriaDialog(self.db, self).exec()

    def _escolher_pasta_backup(self):
        pasta_atual = self.input_backup_dir.text().strip() or self._pasta_backup_padrao
        pasta = QFileDialog.getExistingDirectory(
            self, "Escolha a pasta dos backups", pasta_atual
        )
        if pasta:
            self.input_backup_dir.setText(pasta)

    def _formulario_fichas_sujo(self) -> bool:
        if self.window_principal and hasattr(self.window_principal, "screen_fichas"):
            return getattr(self.window_principal.screen_fichas, "_formulario_sujo", False)
        return False

    def _executar_backup_manual(self):
        if not self.db:
            return
        if self._formulario_fichas_sujo():
            QMessageBox.warning(
                self, "Edição em andamento",
                "Salve ou descarte a ficha em edição antes de executar o backup."
            )
            return
        dest = self.input_backup_dir.text().strip()
        senha = self.input_backup_senha.text()
        if not dest or not senha:
            QMessageBox.warning(self, "Campos obrigatórios", "Informe pasta e senha de recuperação.")
            return
        confirm = QMessageBox.question(
            self, "Confirmar senha",
            "Confirme que memorizou a senha. Sem ela a restauração será impossível.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.db.salvar_configuracao("backup_dir", dest)
        self.db.salvar_configuracao("backup_freq", self.combo_backup_freq.currentText())
        self.db.salvar_configuracao("backup_retencao", str(self.input_retencao.value()))
        self.db.salvar_configuracao(
            "backup_include_attachments",
            "1" if self.chk_incluir_anexos.isChecked() else "0",
        )

        self.btn_backup_agora.setEnabled(False)
        self._backup_worker = BackupWorker(
            self.db,
            dest,
            senha,
            include_attachments=self.chk_incluir_anexos.isChecked(),
            retention_days=self.input_retencao.value(),
        )
        self._backup_worker.progress.connect(self._on_backup_progress)
        self._backup_worker.finished_ok.connect(self._on_backup_ok)
        self._backup_worker.finished_error.connect(self._on_backup_error)
        self._backup_worker.start()

    def _on_backup_progress(self, msg: str):
        self.lbl_backup_status.setText(f"Em andamento: {msg}")

    def _on_backup_ok(self, result: dict):
        self.btn_backup_agora.setEnabled(True)
        size_kb = result.get("size_bytes", 0) // 1024
        self.lbl_backup_status.setText(
            f"Último backup: {result.get('created_at', '')}\n"
            f"Arquivo: {result.get('filename', '')} ({size_kb} KB)"
        )
        removidos = int(result.get("expired_removed") or 0)
        detalhe = f"\n{removidos} backup(s) antigo(s) removido(s) pela retenção." if removidos else ""
        QMessageBox.information(self, "Backup concluído", f"Backup criptografado gerado com sucesso.{detalhe}")

    def _on_backup_error(self, err: str):
        self.btn_backup_agora.setEnabled(True)
        self.lbl_backup_status.setText(f"Erro no último backup: {err[:120]}")
        QMessageBox.critical(self, "Falha no backup", "Não foi possível concluir o backup.")

    def _restaurar_backup(self):
        if not self.db:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar backup", "", "Backup Prontu (*.prntbk)"
        )
        if not path:
            return
        senha = self._solicitar_senha_backup()
        if not senha:
            return

        escolha = QMessageBox(self)
        escolha.setWindowTitle("Modo de restauração")
        escolha.setIcon(QMessageBox.Icon.Question)
        escolha.setText("Como você deseja restaurar este backup?")
        escolha.setInformativeText(
            "Importar com segurança adiciona os dados do backup aos atuais. "
            "Substituir remove os dados atuais deste consultório antes de restaurar o arquivo."
        )
        importar = escolha.addButton(
            "Importar com segurança (recomendado)",
            QMessageBox.ButtonRole.AcceptRole,
        )
        substituir = escolha.addButton(
            "Substituir dados atuais", QMessageBox.ButtonRole.DestructiveRole
        )
        escolha.addButton(QMessageBox.StandardButton.Cancel)
        escolha.exec()
        botao_escolhido = escolha.clickedButton()
        if botao_escolhido not in (importar, substituir):
            return

        replace_existing = botao_escolhido is substituir
        if replace_existing:
            confirm = QMessageBox.warning(
                self,
                "Atenção: substituição de dados",
                "Os pacientes, fichas, agenda, retornos, pagamentos, pastas, modelos e configurações atuais "
                "deste consultório serão removidos e substituídos pelo backup.\n\n"
                "Contas da equipe, convites, auditoria e arquivos já armazenados não são removidos.\n\n"
                "Deseja continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            texto, confirmado = QInputDialog.getText(
                self,
                "Confirmação final",
                "Para confirmar, digite SUBSTITUIR:",
            )
            if not confirmado or texto.strip().upper() != "SUBSTITUIR":
                QMessageBox.information(self, "Restauração cancelada", "Nenhum dado foi alterado.")
                return
        else:
            confirm = QMessageBox.question(
                self,
                "Confirmar importação",
                "Importar os dados do backup sem remover os dados atuais?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        try:
            service = BackupService(self.db)
            stats = service.restore_backup(
                path,
                senha,
                safe_mode=not replace_existing,
                replace_existing=replace_existing,
            )
            resumo = (
                f"Concluída. Inseridos: {stats['inserted']}, ignorados: {stats['skipped']}."
            )
            if replace_existing:
                resumo += f" Registros removidos: {stats['removed']}."
            QMessageBox.information(
                self, "Restauração", resumo
            )
            self.carregar_dados_configurados()
        except Exception:
            QMessageBox.critical(self, "Restauração", "Falha na restauração. Verifique senha e arquivo.")

    def _solicitar_senha_backup(self) -> str:
        """Solicita a senha com opção de conferi-la antes de restaurar."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Senha de recuperação")
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Informe a senha usada para criar este backup:"))
        campo = QLineEdit()
        configurar_visibilidade_senha(campo)
        layout.addWidget(campo)
        acoes = QHBoxLayout()
        acoes.addStretch()
        cancelar = QPushButton("Cancelar")
        confirmar = QPushButton("Continuar")
        cancelar.clicked.connect(dialog.reject)
        confirmar.clicked.connect(dialog.accept)
        acoes.addWidget(cancelar)
        acoes.addWidget(confirmar)
        layout.addLayout(acoes)
        campo.returnPressed.connect(dialog.accept)
        campo.setFocus()
        return campo.text() if dialog.exec() == QDialog.DialogCode.Accepted else ""

    def _desativar_dispositivo(self):
        if not self.db:
            return
        if QMessageBox.question(
            self, "Desativar",
            "Encerrar sessão deste dispositivo? Será necessário revalidar a chave.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.db.desativar_dispositivo()
        QMessageBox.information(self, "Desativado", "Dispositivo desativado. Reinicie o aplicativo.")

    def abrir_configuracao_mensagens(self):
        if not self.db:
            return
        dialogo = MensagensWhatsAppDialog(self.db, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Mensagens salvas", "As mensagens do WhatsApp foram atualizadas.")

    def carregar_dados_configurados(self):
        """Busca do banco de dados e preenche os campos."""
        if not self.db:
            return
        self.atualizar_cartao_assinatura()
        defaults = {
            "nome_profissional": "",
            "backup_dir": self._pasta_backup_padrao,
            "backup_freq": "manual",
            "backup_retencao": "30",
            "backup_include_attachments": "0",
            "backup_last_success": "",
            "backup_last_path": "",
            "backup_last_size": "0",
            "backup_last_error": "",
        }
        valores = defaults | self.db.obter_configuracoes(list(defaults))
        nome_atual = valores["nome_profissional"]
        self.input_nome.setText(nome_atual)

        self.input_backup_dir.setText(
            valores["backup_dir"]
            or self._pasta_backup_padrao
        )
        freq = valores["backup_freq"]
        idx = self.combo_backup_freq.findText(freq)
        if idx >= 0:
            self.combo_backup_freq.setCurrentIndex(idx)
        try:
            self.input_retencao.setValue(
                int(valores["backup_retencao"])
            )
        except ValueError:
            self.input_retencao.setValue(30)
        self.chk_incluir_anexos.setChecked(
            valores["backup_include_attachments"] == "1"
        )
        last = valores["backup_last_success"]
        path = valores["backup_last_path"]
        size = valores["backup_last_size"]
        err = valores["backup_last_error"]
        if last:
            self.lbl_backup_status.setText(
                f"Último backup: {last}\nDestino: {path} ({int(size) // 1024} KB)"
            )
        elif err:
            self.lbl_backup_status.setText(f"Erro no último backup: {err[:120]}")

    def atualizar_cartao_assinatura(self):
        """Mostra o plano atual sem expor chave, tokens ou dados administrativos."""
        if not self.db or not hasattr(self.db, "obter_resumo_assinatura"):
            return
        dados = self.db.obter_resumo_assinatura() or {}
        plano = str(dados.get("plano") or "solo").lower()
        nomes_planos = {
            "solo": "Prontu Solo",
            "equipe": "Prontu Equipe",
            "personalizado": "Prontu Personalizado",
        }
        status = str(dados.get("status") or "ativa").lower()
        nomes_status = {
            "ativa": "Assinatura ativa",
            "teste": "Período de teste",
            "suspensa": "Assinatura suspensa",
            "cancelada": "Assinatura cancelada",
        }
        cores_status = {
            "ativa": ("#dcfce7", "#15803d"),
            "teste": ("#fef3c7", "#b45309"),
            "suspensa": ("#fee2e2", "#b91c1c"),
            "cancelada": ("#fee2e2", "#b91c1c"),
        }
        fundo, cor = cores_status.get(status, ("#e2e8f0", "#475569"))
        self.lbl_plano_atual.setText(nomes_planos.get(plano, "Prontu Solo"))
        self.lbl_status_assinatura.setText(nomes_status.get(status, "Status não informado"))
        self.lbl_status_assinatura.setStyleSheet(
            f"background: {fundo}; color: {cor}; border-radius: 12px; padding: 5px 10px; font-size: 12px; font-weight: bold;"
        )
        max_usuarios = dados.get("max_usuarios") or 1
        if plano == "solo":
            self.lbl_limite_assinatura.setText("1 usuário")
        else:
            self.lbl_limite_assinatura.setText(f"Até {max_usuarios} usuários")

    def salvar_configuracoes(self):
        """Grava as alterações e avisa a Home que ela precisa se atualizar."""
        nome_digitado = self.input_nome.text().strip()
        
        # Salva de forma persistente no SQLite
        self.db.salvar_nome_profissional(nome_digitado)
            
        # Alerta de Sucesso
        msg = QMessageBox(self)
        msg.setWindowTitle("Sucesso")
        msg.setText("Configurações atualizadas com sucesso!")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("QMessageBox { background-color: #ffffff; } QLabel { color: #0f172a; } QPushButton { background-color: #e2e8f0; color: #0f172a; padding: 5px 15px; border-radius: 4px; }")
        msg.exec()
        
        # Sincroniza dinamicamente a Home do aplicativo para atualizar a saudação sem reiniciar
        if self.window_principal and hasattr(self.window_principal, 'screen_home'):
            if hasattr(self.window_principal.screen_home, 'atualizar_saudacao_dinamica'):
                self.window_principal.screen_home.atualizar_saudacao_dinamica()
