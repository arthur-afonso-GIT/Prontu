import os
import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame)
from PySide6.QtCore import Qt

from ui.screens.home import HomeScreen
from ui.screens.pacientes import PacientesScreen
from ui.screens.agenda import AgendaScreen 
from ui.screens.configuracoes import ConfiguracoesScreen

try:
    from ui.screens.fichas import FichasScreen
except ImportError:
    FichasScreen = QWidget

# Importando a nova conexão segura do Supabase
from database import Database
db = Database()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prontu — Prontuário Médico Inteligente")
        self.resize(1200, 750)
        
        # Inicializa a conexão com o banco de dados e garante os atributos
        self.db = db
        if not hasattr(self.db, 'consultorio_id'):
            from config_app import CONSULTORIO_ID
            self.db.consultorio_id = CONSULTORIO_ID

        self.init_db_estruturas()
        self.pastas_sistema = self.carregar_pastas_sqlite()
        
        # --- WIDGET CENTRAL ---
        # Isolamos o widget de fundo usando um ObjectName exclusivo
        central_widget = QWidget()
        central_widget.setObjectName("PainelCentralProntu")
        central_widget.setStyleSheet("#PainelCentralProntu { background-color: #f8fafc; }")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- SIDEBAR (MENU LATERAL) ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        
        # Isolando a sidebar por ID para não vazar a cor escura para popups e inputs internos
        self.sidebar.setObjectName("SidebarMenuLateral")
        self.sidebar.setStyleSheet("#SidebarMenuLateral { background-color: #0f172a; border-right: 1px solid #1e293b; }")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 25)
        sidebar_layout.setSpacing(8)
        
        # Título da Marca
        lbl_logo = QLabel("🏥 Prontu")
        lbl_logo.setStyleSheet("color: #f8fafc; font-size: 22px; font-weight: bold; margin-bottom: 25px; padding-left: 10px; background: transparent;")
        sidebar_layout.addWidget(lbl_logo)
        
        # Botões de Navegação
        style_botoes = """
            QPushButton {
                color: #94a3b8;
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                color: #f8fafc;
                background-color: #1e293b;
            }
            QPushButton:checked {
                color: #ffffff;
                background-color: #0284c7;
                font-weight: bold;
            }
        """
        
        self.btn_home = QPushButton("🏠 Início")
        self.btn_pacientes = QPushButton("👤 Pacientes")
        self.btn_agenda = QPushButton("📅 Agenda Médica")
        self.btn_fichas = QPushButton("📝 Fichas Clínicas")
        self.btn_config = QPushButton("⚙️ Configurações")
        
        self.botoes_menu = [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]
        for btn in self.botoes_menu:
            btn.setCheckable(True)
            btn.setStyleSheet(style_botoes)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # Informação de Rodapé do Usuário
        self.lbl_rodape_medico = QLabel("Médico Conectado")
        self.lbl_rodape_medico.setStyleSheet("color: #64748b; font-size: 11px; padding-left: 10px; font-weight: 500; background: transparent;")
        sidebar_layout.addWidget(self.lbl_rodape_medico)
        
        main_layout.addWidget(self.sidebar)
        
        # --- ÁREA DE CONTEÚDO DINÂMICO (STACKED WIDGET) ---
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("AreaConteudo")
        
        # CSS limpo para a área de conteúdo (apenas o fundo do StackedWidget, sem vazar para os filhos)
        self.content_stack.setStyleSheet("#AreaConteudo { background-color: #f8fafc; border: none; }")
        
        # Instanciação correta das Telas
        self.screen_home = HomeScreen(self, on_novo_paciente_click=self.navegar_para_novo_paciente, on_pasta_click=self.filtrar_pacientes_por_pasta)
        self.screen_pacientes = PacientesScreen()
        self.screen_agenda = AgendaScreen()
        self.screen_fichas = FichasScreen() if FichasScreen != QWidget else QWidget()
        self.screen_config = ConfiguracoesScreen(window_principal=self)
        
        self.content_stack.addWidget(self.screen_home)       # Índice 0
        self.content_stack.addWidget(self.screen_pacientes)  # Índice 1
        self.content_stack.addWidget(self.screen_agenda)     # Índice 2
        self.content_stack.addWidget(self.screen_fichas)     # Índice 3
        self.content_stack.addWidget(self.screen_config)     # Índice 4
        
        main_layout.addWidget(self.content_stack, stretch=1)
        
        # Conexões e Estado Inicial
        self.connect_signals()
        self.switch_screen(0)
        self.atualizar_nome_medico_sidebar()

    def connect_signals(self):
        self.btn_home.clicked.connect(lambda: self.switch_screen(0))
        self.btn_pacientes.clicked.connect(lambda: self.switch_screen(1))
        self.btn_agenda.clicked.connect(lambda: self.switch_screen(2))
        self.btn_fichas.clicked.connect(lambda: self.switch_screen(3))
        self.btn_config.clicked.connect(lambda: self.switch_screen(4))

    def switch_screen(self, index):
        for idx, btn in enumerate(self.botoes_menu):
            btn.setChecked(idx == index)
        self.content_stack.setCurrentIndex(index)
        
        # Gatilhos de atualização ao mudar de tela
        if index == 0:
            if hasattr(self.screen_home, 'renderizar_lista_pastas'):
                self.screen_home.renderizar_lista_pastas()
        elif index == 1:
            if hasattr(self.screen_pacientes, 'carregar_pacientes_tabela'):
                self.screen_pacientes.carregar_pacientes_tabela()
            if hasattr(self.screen_pacientes, 'atualizar_combobox_pastas'):
                self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        elif index == 2:
            if hasattr(self.screen_agenda, 'carregar_lista_pacientes_combobox'):
                self.screen_agenda.carregar_lista_pacientes_combobox()
            if hasattr(self.screen_agenda, 'renderizar_timeline_calendario'):
                self.screen_agenda.renderizar_timeline_calendario()
        elif index == 3:
            if hasattr(self.screen_fichas, 'atualizar_combobox_pacientes'):
                self.screen_fichas.atualizar_combobox_pacientes()

    def navegar_para_novo_paciente(self):
        if hasattr(self.screen_pacientes, 'limpar_formulario'):
            self.screen_pacientes.limpar_formulario()
        self.switch_screen(1)

    def filtrar_pacientes_por_pasta(self, nome_pasta):
        self.switch_screen(1)
        if hasattr(self.screen_pacientes, 'filtrar_por_pasta_externo'):
            self.screen_pacientes.filtrar_por_pasta_externo(nome_pasta)

    def atualizar_nome_medico_sidebar(self):
        nome = self.db.obter_nome_profissional()
        if nome:
            self.lbl_rodape_medico.setText(f"Dr(a). {nome}")
            if hasattr(self.screen_home, 'atualizar_saudacao_dinamica'):
                self.screen_home.atualizar_saudacao_dinamica()
        else:
            self.lbl_rodape_medico.setText("Profissional não Configurado")

    def init_db_estruturas(self):
        """Não há tabelas locais para criar no SQLite, as checagens rodam na nuvem."""
        pass

    def carregar_pastas_sqlite(self):
        """Carrega as pastas criadas na nuvem para este consultório."""
        if not self.db.supabase:
            return ["Geral"]
        try:
            resposta = self.db.supabase.table("pastas")\
                .select("nome")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .order("nome")\
                .execute()
            
            pastas_atuais = [row["nome"] for row in resposta.data]
            if pastas_atuais:
                return pastas_atuais
        except Exception as e:
            print(f"Erro ao carregar pastas: {e}")
        return ["Geral"]

    def sincronizar_pastas_sistema(self, nova_lista):
        """Sincroniza a nova listagem de pastas diretamente no Supabase."""
        if not self.db.supabase:
            return
        try:
            self.pastas_sistema = sorted(list(set(nova_lista)))
            
            # Remove pastas antigas do consultório no banco
            self.db.supabase.table("pastas")\
                .delete()\
                .eq("consultorio_id", self.db.consultorio_id)\
                .execute()
                
            # Adiciona a nova lista de pastas na nuvem
            payload = [{"consultorio_id": self.db.consultorio_id, "nome": pasta} for pasta in self.pastas_sistema]
            if payload:
                self.db.supabase.table("pastas").insert(payload).execute()
                
            if hasattr(self.screen_pacientes, 'atualizar_combobox_pastas'):
                self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        except Exception as e:
            print(f"Erro ao sincronizar pastas: {e}")