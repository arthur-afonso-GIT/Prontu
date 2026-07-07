from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Importação das telas do sistema
from ui.screens.home import HomeScreen
from ui.screens.pacientes import PacientesScreen
from ui.screens.agenda import AgendaScreen  

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prontu — Prontuário Médico Inteligente")
        self.resize(1200, 750)
        
        # Lista global dinâmica de pastas do consultório
        self.pastas_sistema = ["Geral", "Nutrição", "Cardiologia", "Pediatria"]
        
        # Widget Central e Layout Principal Horizontal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 1. SIDEBAR LATERAL ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("""
            QFrame { background-color: #0f172a; border: none; }
            QPushButton { 
                color: #94a3b8; font-size: 14px; font-weight: 500; text-align: left;
                padding: 12px 20px; border: none; border-radius: 6px; background-color: transparent;
            }
            QPushButton:hover { background-color: #1e293b; color: white; }
            QPushButton:checked { background-color: #0284c7; color: white; font-weight: bold; }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 25)
        sidebar_layout.setSpacing(8)
        
        # Logo do Prontu
        logo = QLabel("🌱 Prontu")
        logo.setStyleSheet("color: white; font-size: 22px; font-weight: bold; padding-left: 10px; margin-bottom: 20px;")
        sidebar_layout.addWidget(logo)
        
        # Botões de Navegação
        self.btn_home = QPushButton("🏠   Início")
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.clicked.connect(lambda: self.mudar_tela(self.screen_home, self.btn_home))
        
        self.btn_pacientes = QPushButton("👥   Pacientes")
        self.btn_pacientes.setCheckable(True)
        self.btn_pacientes.clicked.connect(lambda: self.mudar_tela(self.screen_pacientes, self.btn_pacientes))
        
        self.btn_agenda = QPushButton("📅   Agenda")
        self.btn_agenda.setCheckable(True)
        self.btn_agenda.clicked.connect(lambda: self.mudar_tela(self.screen_agenda, self.btn_agenda))
        
        self.btn_fichas = QPushButton("📥   Importar Fichas")
        self.btn_fichas.setCheckable(True)
        self.btn_fichas.clicked.connect(lambda: self.mudar_tela(self.screen_fichas, self.btn_fichas))
        
        self.btn_config = QPushButton("⚙️   Configurações")
        self.btn_config.setCheckable(True)
        self.btn_config.clicked.connect(lambda: self.mudar_tela(self.screen_config, self.btn_config))
        
        sidebar_layout.addWidget(self.btn_home)
        sidebar_layout.addWidget(self.btn_pacientes)
        sidebar_layout.addWidget(self.btn_agenda)
        sidebar_layout.addWidget(self.btn_fichas)
        sidebar_layout.addWidget(self.btn_config)
        sidebar_layout.addStretch()
        
        main_layout.addWidget(self.sidebar)
        
        # --- 2. CONTÊINER DE TELAS DINÂMICAS (STACKED WIDGET) ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, stretch=1)
        
        # Instanciação Inicial das Telas Reais
        self.screen_home = HomeScreen(
            window_principal=self, 
            on_novo_paciente_click=self.ir_para_tela_pacientes
        )
        self.screen_pacientes = PacientesScreen()
        self.screen_agenda = AgendaScreen()  
        
        # Atualiza os componentes internos que dependem das pastas
        self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        
        # Telas secundárias que serão construídas posteriormente
        self.screen_fichas = QLabel("Tela de Importação Automática em Breve")
        self.screen_config = QLabel("Tela de Configurações em Breve")
        
        for screen in [self.screen_fichas, self.screen_config]:
            screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
            screen.setStyleSheet("font-size: 16px; color: #64748b; font-weight: 500;")
            
        self.stack.addWidget(self.screen_home)
        self.stack.addWidget(self.screen_pacientes)
        self.stack.addWidget(self.screen_agenda)
        self.stack.addWidget(self.screen_fichas)
        self.stack.addWidget(self.screen_config)

        # Atualiza as sugestões da agenda com base no banco SQL carregado
        self.atualizar_sugestoes_agenda()

    def atualizar_sugestoes_agenda(self):
        """Alimenta a barra de sugestões da agenda com os nomes vindos da tabela."""
        nomes_iniciais = []
        for r in range(self.screen_pacientes.table.rowCount()):
            item_nome = self.screen_pacientes.table.item(r, 0)
            if item_nome:
                nomes_iniciais.append(item_nome.text())
        
        self.screen_agenda.atualizar_lista_sugestoes(nomes_iniciais)

    def mudar_tela(self, destino_widget, botao_clicado):
        self.stack.setCurrentWidget(destino_widget)
        for btn in [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]:
            btn.setChecked(btn == botao_clicado)
            
        # Se o usuário clicar na tela da agenda, recarrega a lista de nomes atualizada para o autocompletar
        if destino_widget == self.screen_agenda:
            self.atualizar_sugestoes_agenda()

    def ir_para_tela_pacientes(self):
        self.mudar_tela(self.screen_pacientes, self.btn_pacientes)

    def processar_clique_pasta_home(self, nome_pasta):
        self.screen_pacientes.filtrar_por_pasta_externo(nome_pasta)
        self.ir_para_tela_pacientes()

    def sincronizar_pastas_sistema(self, nova_lista):
        """Atualiza a lista mestra global e força os componentes dependentes a se redesenharem."""
        self.pastas_sistema = nova_lista
        self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)