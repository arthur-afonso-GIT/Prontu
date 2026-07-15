import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QFrame, QMessageBox,
                               QComboBox, QCheckBox, QFileDialog, QInputDialog,
                               QSpinBox)
from PySide6.QtCore import Qt

from services.backup_service import BackupService
from services.backup_worker import BackupWorker


class ConfiguracoesScreen(QWidget):
    def __init__(self, window_principal=None):
        super().__init__()
        self.window_principal = window_principal
        self.db = window_principal.db if window_principal else None
        self._backup_worker = None
        self._pasta_backup_padrao = os.path.join(
            os.path.expanduser("~"), "Documents", "Prontu Backups"
        )
        
        # Layout Principal com margens confortáveis
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # --- CABEÇALHO ---
        lbl_titulo = QLabel("⚙️ Configurações do Sistema")
        lbl_titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        main_layout.addWidget(lbl_titulo)
        
        lbl_subtitulo = QLabel("Personalize os dados do aplicativo que serão exibidos nas telas e relatórios.")
        lbl_subtitulo.setStyleSheet("font-size: 14px; color: #64748b; margin-bottom: 10px;")
        main_layout.addWidget(lbl_subtitulo)
        
        # --- PAINEL DE PERFIL DO PROFISSIONAL ---
        container_perfil = QFrame()
        container_perfil.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }
            QLabel { color: #334155; font-weight: 500; font-size: 13px; border: none; }
        """)
        
        perfil_layout = QVBoxLayout(container_perfil)
        perfil_layout.setContentsMargins(20, 20, 20, 20)
        perfil_layout.setSpacing(12)
        
        lbl_secao = QLabel("Perfil do Usuário / Médico")
        lbl_secao.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        perfil_layout.addWidget(lbl_secao)
        
        perfil_layout.addWidget(QLabel("Nome do Profissional (Ex: Dra. Laura Silva, Dr. Carlos):"))
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Digite como deseja ser saudado na página inicial...")
        self.input_nome.setStyleSheet("""
            QLineEdit { padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc; color: #0f172a; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #0284c7; background-color: white; }
        """)
        perfil_layout.addWidget(self.input_nome)
        
        # Layout inferior para botões de ação
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_salvar = QPushButton("💾 Salvar Alterações")
        self.btn_salvar.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 10px 20px; font-weight: bold; border-radius: 6px; border: none; font-size: 13px; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_salvar.clicked.connect(self.salvar_configuracoes)
        btn_layout.addWidget(self.btn_salvar)
        
        perfil_layout.addLayout(btn_layout)
        main_layout.addWidget(container_perfil)

        # --- PAINEL DE BACKUP LOCAL CRIPTOGRAFADO ---
        container_backup = QFrame()
        container_backup.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }
            QLabel { color: #334155; font-weight: 500; font-size: 13px; border: none; }
            QLineEdit, QComboBox, QSpinBox {
                min-height: 34px; padding: 4px 10px; color: #0f172a;
                background-color: #ffffff; border: 1px solid #94a3b8; border-radius: 6px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid #0284c7; }
            QComboBox::drop-down { width: 28px; border: none; }
            QComboBox QAbstractItemView { color: #0f172a; background: #ffffff; selection-background-color: #bae6fd; }
            QCheckBox { color: #334155; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #64748b; border-radius: 3px; background: #ffffff; }
            QCheckBox::indicator:checked { background: #0284c7; border-color: #0284c7; }
            QPushButton { min-height: 34px; padding: 4px 12px; color: #ffffff; background-color: #0284c7; border: none; border-radius: 6px; font-weight: 600; }
            QPushButton:hover { background-color: #0369a1; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
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
        btn_escolher_pasta.clicked.connect(self._escolher_pasta_backup)
        pasta_row.addWidget(self.input_backup_dir)
        pasta_row.addWidget(btn_escolher_pasta)
        backup_layout.addLayout(pasta_row)

        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("Frequência:"))
        self.combo_backup_freq = QComboBox()
        self.combo_backup_freq.addItems(["manual", "diaria", "semanal"])
        freq_row.addWidget(self.combo_backup_freq)
        freq_row.addWidget(QLabel("Retenção (dias):"))
        self.input_retencao = QSpinBox()
        self.input_retencao.setRange(1, 3650)
        self.input_retencao.setValue(30)
        self.input_retencao.setFixedWidth(60)
        freq_row.addWidget(self.input_retencao)
        freq_row.addStretch()
        backup_layout.addLayout(freq_row)

        self.chk_incluir_anexos = QCheckBox("Incluir metadados de anexos no backup")
        backup_layout.addWidget(self.chk_incluir_anexos)

        senha_row = QHBoxLayout()
        senha_row.addWidget(QLabel("Senha de recuperação:"))
        self.input_backup_senha = QLineEdit()
        self.input_backup_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_backup_senha.setPlaceholderText("Defina e confirme ao executar backup")
        senha_row.addWidget(self.input_backup_senha)
        backup_layout.addLayout(senha_row)

        self.lbl_backup_status = QLabel("Último backup: nunca executado")
        self.lbl_backup_status.setWordWrap(True)
        self.lbl_backup_status.setStyleSheet("color: #64748b; font-size: 12px;")
        backup_layout.addWidget(self.lbl_backup_status)

        btn_backup_row = QHBoxLayout()
        self.btn_backup_agora = QPushButton("Executar backup agora")
        self.btn_backup_agora.clicked.connect(self._executar_backup_manual)
        self.btn_restaurar = QPushButton("Restaurar backup...")
        self.btn_restaurar.clicked.connect(self._restaurar_backup)
        self.btn_desativar = QPushButton("Desativar dispositivo")
        self.btn_desativar.clicked.connect(self._desativar_dispositivo)
        btn_backup_row.addWidget(self.btn_backup_agora)
        btn_backup_row.addWidget(self.btn_restaurar)
        btn_backup_row.addStretch()
        btn_backup_row.addWidget(self.btn_desativar)
        backup_layout.addLayout(btn_backup_row)

        main_layout.addWidget(container_backup)
        main_layout.addStretch()
        
        # Executa a busca inicial de dados para preencher a tela
        self.carregar_dados_configurados()

    def _abrir_seletor_pasta_backup(self, event):
        self._escolher_pasta_backup()

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
            self.db, dest, senha, include_attachments=self.chk_incluir_anexos.isChecked()
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
        QMessageBox.information(self, "Backup concluído", "Backup criptografado gerado com sucesso.")

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
        senha, ok = QInputDialog.getText(
            self, "Senha de recuperação", "Informe a senha do backup:", QLineEdit.EchoMode.Password
        )
        if not ok or not senha:
            return
        safe = QMessageBox.question(
            self,
            "Modo de restauração",
            "Restaurar em modo seguro (não sobrescreve IDs existentes)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

        confirm = QMessageBox.warning(
            self,
            "Confirmação forte",
            "Esta operação importará dados do backup. Deseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            service = BackupService(self.db)
            stats = service.restore_backup(path, senha, safe_mode=safe)
            QMessageBox.information(
                self, "Restauração",
                f"Concluída. Inseridos: {stats['inserted']}, ignorados: {stats['skipped']}."
            )
            self.carregar_dados_configurados()
        except Exception:
            QMessageBox.critical(self, "Restauração", "Falha na restauração. Verifique senha e arquivo.")

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

    def carregar_dados_configurados(self):
        """Busca do banco de dados e preenche os campos."""
        if not self.db:
            return
        nome_atual = self.db.obter_nome_profissional()
        self.input_nome.setText(nome_atual)

        self.input_backup_dir.setText(
            self.db.obter_configuracao("backup_dir", self._pasta_backup_padrao)
            or self._pasta_backup_padrao
        )
        freq = self.db.obter_configuracao("backup_freq", "manual")
        idx = self.combo_backup_freq.findText(freq)
        if idx >= 0:
            self.combo_backup_freq.setCurrentIndex(idx)
        try:
            self.input_retencao.setValue(
                int(self.db.obter_configuracao("backup_retencao", "30"))
            )
        except ValueError:
            self.input_retencao.setValue(30)
        self.chk_incluir_anexos.setChecked(
            self.db.obter_configuracao("backup_include_attachments", "0") == "1"
        )
        last = self.db.obter_configuracao("backup_last_success", "")
        path = self.db.obter_configuracao("backup_last_path", "")
        size = self.db.obter_configuracao("backup_last_size", "0")
        err = self.db.obter_configuracao("backup_last_error", "")
        if last:
            self.lbl_backup_status.setText(
                f"Último backup: {last}\nDestino: {path} ({int(size) // 1024} KB)"
            )
        elif err:
            self.lbl_backup_status.setText(f"Erro no último backup: {err[:120]}")

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
