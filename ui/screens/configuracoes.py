from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QMessageBox)
from PySide6.QtCore import Qt
from database import Database

class ConfiguracoesScreen(QWidget):
    def __init__(self, window_principal=None):
        super().__init__()
        self.window_principal = window_principal
        self.db = Database()
        
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
        
        # Empurra tudo para cima mantendo o layout limpo e elegante
        main_layout.addStretch()
        
        # Executa a busca inicial de dados para preencher a tela
        self.carregar_dados_configurados()

    def carregar_dados_configurados(self):
        """Busca do banco de dados e joga para o campo de texto."""
        nome_atual = self.db.obter_nome_profissional()
        self.input_nome.setText(nome_atual)

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