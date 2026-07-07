import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame)
from PySide6.QtCore import Qt
from ui.screens.pacientes import PacientesScreen    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prontu — Gerenciador Clínico Local")
        self.resize(1100, 700)
        
        # Widget Central e Layout Principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Inicializar Componentes da UI
        self.setup_sidebar()
        self.setup_content_area()
        
        # Conectar botões do menu
        self.connect_signals()
        
        # Definir tela inicial por padrão (Home = índice 0)
        self.switch_screen(0)

    def setup_sidebar(self):
        """Cria a barra lateral de navegação."""
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("background-color: #1e293b; color: white;")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)
        
        # Logo ou Nome do App no topo
        self.logo_label = QLabel("PRONTU")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 20px; color: #38bdf8;")
        sidebar_layout.addWidget(self.logo_label)
        
        # Botões de Navegação
        self.btn_home = QPushButton("🏠 Home")
        self.btn_pacientes = QPushButton("👥 Pacientes")
        self.btn_agenda = QPushButton("📅 Agenda")
        self.btn_fichas = QPushButton("📄 Fichas Dinâmicas")
        self.btn_config = QPushButton("⚙️ Configurações")
        
        menu_buttons = [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]
        for btn in menu_buttons:
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left; padding: 12px; font-size: 14px; 
                    border: none; border-radius: 5px; color: #cbd5e1;
                }
                QPushButton:hover { background-color: #334155; color: white; }
                QPushButton:checked { background-color: #0284c7; color: white; font-weight: bold; }
            """)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        self.main_layout.addWidget(self.sidebar)

    def setup_content_area(self):
        """Cria o container onde as telas serão trocadas."""
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #f8fafc;")
        
        # Placeholders temporários (Estes continuam como QLabel)
        self.screen_home = QLabel("Tela Home - Pacientes Recentes e Pastas")
        self.screen_agenda = QLabel("Tela Agenda - Calendário Diário/Semanal/Mensal")
        self.screen_fichas = QLabel("Tela Ficha Dinâmica - Importador de PDF/DOCX")
        self.screen_config = QLabel("Tela Configurações - Caminho dos Dados")
        
        # Tela Real de Pacientes (Instanciada corretamente como QWidget)
        self.screen_pacientes = PacientesScreen() 
        
        # Aplica o alinhamento APENAS nas que ainda são placeholders (Labels)
        for screen in [self.screen_home, self.screen_agenda, self.screen_fichas, self.screen_config]:
            screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
            screen.setStyleSheet("font-size: 18px; color: #64748b;")
            
        # Adiciona todas as telas ao Stack na ordem correta dos índices
        self.content_stack.addWidget(self.screen_home)       # Índice 0
        self.content_stack.addWidget(self.screen_pacientes)  # Índice 1
        self.content_stack.addWidget(self.screen_agenda)     # Índice 2
        self.content_stack.addWidget(self.screen_fichas)     # Índice 3
        self.content_stack.addWidget(self.screen_config)     # Índice 4
        
        self.main_layout.addWidget(self.content_stack)

    def connect_signals(self):
        """Mapeia os cliques dos botões."""
        self.btn_home.clicked.connect(lambda: self.switch_screen(0))
        self.btn_pacientes.clicked.connect(lambda: self.switch_screen(1))
        self.btn_agenda.clicked.connect(lambda: self.switch_screen(2))
        self.btn_fichas.clicked.connect(lambda: self.switch_screen(3))
        self.btn_config.clicked.connect(lambda: self.switch_screen(4))

    def switch_screen(self, index):
        """Muda a tela ativa e gerencia o estado visual dos botões."""
        self.content_stack.setCurrentIndex(index)
        
        buttons = [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)