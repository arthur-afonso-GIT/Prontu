import sys
import os

# Garante que o Python encontre a pasta raiz para as importações
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from ui.main_window import MainWindow
from ui.screens.home import HomeScreen
from ui.screens.agenda import AgendaScreen
from ui.screens.configuracoes import ConfiguracoesScreen

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProntuApp - Prontuário Eletrônico")
        self.setMinimumSize(1200, 700)
        
        # Janela Base que contém o Menu Lateral (Sidebar)
        self.main_window_layout = MainWindow()
        self.setCentralWidget(self.main_window_layout)
        
        # O QStackedWidget gerencia a troca de telas na área de conteúdo
        self.content_stack = QStackedWidget()
        
        # Se a sua MainWindow já tiver um layout para o conteúdo central, 
        # nós inserimos o stack dentro dele.
        if hasattr(self.main_window_layout, "container_conteudo"):
            self.main_window_layout.container_conteudo.layout().addWidget(self.content_stack)
        elif hasattr(self.main_window_layout, "main_layout"):
            # Fallback caso o layout principal seja direto
            self.main_window_layout.main_layout.addWidget(self.content_stack, stretch=4)

        # Instanciação Completa das Telas Passando a Janela Principal como referência
        self.screen_home = HomeScreen(window_principal=self)
        self.screen_agenda = AgendaScreen()
        self.screen_configuracoes = ConfiguracoesScreen(window_principal=self)
        
        # Adiciona as telas ao gerenciador de empilhamento
        self.content_stack.addWidget(self.screen_home)         # Índice 0
        self.content_stack.addWidget(self.screen_agenda)       # Índice 1
        self.content_stack.addWidget(self.screen_configuracoes) # Índice 2
        
        # Conecta os botões do menu lateral para trocar o índice do stack
        self.conectar_botoes_sidebar()
        
        # Inicializa mostrando a tela Home
        self.content_stack.setCurrentIndex(0)

    def conectar_botoes_sidebar(self):
        """Conecta os cliques dos botões da Sidebar às funções de troca de tela."""
        # Mapeamento dinâmico baseado nos atributos comuns da sua MainWindow
        if hasattr(self.main_window_layout, "btn_home"):
            self.main_window_layout.btn_home.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
            
        if hasattr(self.main_window_layout, "btn_agenda"):
            self.main_window_layout.btn_agenda.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
            
        if hasattr(self.main_window_layout, "btn_config"):
            self.main_window_layout.btn_config.clicked.connect(lambda: self.content_stack.setCurrentIndex(2))
        elif hasattr(self.main_window_layout, "btn_configuracoes"):
            self.main_window_layout.btn_configuracoes.clicked.connect(lambda: self.content_stack.setCurrentIndex(2))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Define um estilo nativo limpo para evitar conflitos de cores no Windows
    app.setStyle("Fusion")
    
    window = MainApp()
    window.showMaximized()
    sys.exit(app.exec())