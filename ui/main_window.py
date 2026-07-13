import sqlite3
import os
import sys # <--- IMPORTANTE: Adicionado para detectar o PyInstaller
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

# =====================================================================
# PASSO 4: FUNÇÃO PARA DETECTAR O CAMINHO SEGURO DO BANCO DE DADOS
# =====================================================================
def obter_caminho_db():
    """
    Retorna o caminho absoluto e seguro para o banco de dados.
    Se estiver compilado (PyInstaller), salva na pasta AppData/Local/Prontu do usuário,
    evitando erros de permissão de escrita no 'Arquivos de Programas'.
    Se estiver em desenvolvimento, salva na raiz do projeto.
    """
    if hasattr(sys, '_MEIPASS'):
        # Caminho comercial seguro: C:\Users\NomeUsuario\AppData\Local\Prontu
        appdata_local = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Prontu')
        # Garante que a pasta 'Prontu' exista dentro do AppData antes de criar o arquivo
        os.makedirs(appdata_local, exist_ok=True)
        return os.path.join(appdata_local, "consultorio.db")
    else:
        # Modo desenvolvimento: Raiz do projeto
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(base_path, "consultorio.db")
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prontu — Prontuário Médico Inteligente")
        self.resize(1200, 750)
        
        # Inicializa as estruturas de base de dados e carrega pastas
        self.init_db_estruturas()
        self.pastas_sistema = self.carregar_pastas_sqlite()
        
        # Widget central e Layout Principal da Janela
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- SIDEBAR LATERAL FIXA ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(220)
        self.sidebar.setStyleSheet("""
            QFrame { background-color: #0f172a; border: none; }
            QPushButton { 
                color: #94a3b8; font-size: 14px; font-weight: 500; text-align: left; 
                padding: 12px 20px; border: none; border-radius: 6px; background: transparent;
            }
            QPushButton:hover { color: white; background-color: #1e293b; }
            QPushButton:checked { color: white; background-color: #0284c7; font-weight: bold; }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 25)
        sidebar_layout.setSpacing(8)
        
        logo = QLabel("🧬 Prontu")
        logo.setStyleSheet("color: white; font-size: 22px; font-weight: bold; margin-bottom: 25px; padding-left: 10px;")
        sidebar_layout.addWidget(logo)
        
        # Botões do Menu Lateral
        self.btn_home = QPushButton("🏠 Home / Painel")
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.clicked.connect(lambda: self.mudar_tela(self.screen_home, self.btn_home))
        sidebar_layout.addWidget(self.btn_home)
        
        self.btn_pacientes = QPushButton("👥 Pacientes")
        self.btn_pacientes.setCheckable(True)
        self.btn_pacientes.clicked.connect(lambda: self.mudar_tela(self.screen_pacientes, self.btn_pacientes))
        sidebar_layout.addWidget(self.btn_pacientes)
        
        self.btn_agenda = QPushButton("📅 Agenda Médica")
        self.btn_agenda.setCheckable(True)
        self.btn_agenda.clicked.connect(lambda: self.mudar_tela(self.screen_agenda, self.btn_agenda))
        sidebar_layout.addWidget(self.btn_agenda)
        
        self.btn_fichas = QPushButton("📝 Fichas Clínicas")
        self.btn_fichas.setCheckable(True)
        self.btn_fichas.clicked.connect(lambda: self.mudar_tela(self.screen_fichas, self.btn_fichas))
        sidebar_layout.addWidget(self.btn_fichas)
        
        sidebar_layout.addStretch()
        
        self.btn_config = QPushButton("⚙️ Configurações")
        self.btn_config.setCheckable(True)
        self.btn_config.clicked.connect(lambda: self.mudar_tela(self.screen_config, self.btn_config))
        sidebar_layout.addWidget(self.btn_config)
        
        main_layout.addWidget(self.sidebar)
        
        # --- ÁREA DE CONTEÚDO (STACKED WIDGET) ---
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f8fafc;")
        
        # Instanciação de todas as Telas
        self.screen_home = HomeScreen(
            window_principal=self,
            on_novo_paciente_click=self.ir_para_tela_pacientes,
            on_pasta_click=self.processar_clique_pasta_home
        )
        self.screen_pacientes = PacientesScreen()
        self.screen_agenda = AgendaScreen()
        self.screen_fichas = FichasScreen() 
        self.screen_config = ConfiguracoesScreen(window_principal=self)
        
        # Adiciona os Widgets à Pilha
        self.stack.addWidget(self.screen_home)
        self.stack.addWidget(self.screen_pacientes)
        self.stack.addWidget(self.screen_agenda)
        self.stack.addWidget(self.screen_fichas)  
        self.stack.addWidget(self.screen_config)
        
        main_layout.addWidget(self.stack)
        
        # Inicializações de dados automáticas com tratamento contra falhas
        try:
            self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
            self.atualizar_sugestoes_agenda()
            self.screen_home.renderizar_lista_pastas()
            self.atualizar_dados_home()
        except Exception as e:
            print(f"Aviso na inicialização de dados: {e}")

    def atualizar_sugestoes_agenda(self):
        nomes_iniciais = []
        try:
            # CAMINHO CORRIGIDO AQUI
            conn = sqlite3.connect(obter_caminho_db())
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM pacientes")
            nomes_iniciais = [row[0].upper() for row in cursor.fetchall()]
            conn.close()
            self.screen_agenda.atualizar_lista_sugestoes(nomes_iniciais)
        except:
            pass

    def mudar_tela(self, destino_widget, botao_clicado):
        """Alterna a tela ativa de forma segura capturando qualquer exceção interna."""
        try:
            self.stack.setCurrentWidget(destino_widget)
            
            # Atualiza os estados visuais dos botões
            for btn in [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]:
                if btn:
                    btn.setChecked(btn == botao_clicado)
            
            # Gatilhos protegidos para atualizar dados ao navegar entre abas
            if destino_widget == self.screen_home:
                self.atualizar_dados_home()
            elif destino_widget == self.screen_fichas:
                if hasattr(self.screen_fichas, "carregar_pacientes_combo"):
                    self.screen_fichas.carregar_pacientes_combo()
            elif destino_widget == self.screen_agenda:
                self.atualizar_sugestoes_agenda()
                
        except Exception as e:
            print(f"Erro controlado ao mudar de tela: {e}")

    def ir_para_tela_pacientes(self):
        self.mudar_tela(self.screen_pacientes, self.btn_pacientes)

    def processar_clique_pasta_home(self, nome_pasta):
        try:
            self.screen_pacientes.filtrar_por_pasta_externo(nome_pasta)
            self.ir_para_tela_pacientes()
        except:
            pass

    def atualizar_dados_home(self):
        try:
            # CAMINHO CORRIGIDO AQUI
            conn = sqlite3.connect(obter_caminho_db())
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pacientes")
            total_pacientes = cursor.fetchone()[0]
            
            from PySide6.QtCore import QDate
            hoje_iso = QDate.currentDate().toString("yyyy-MM-dd")
            cursor.execute("SELECT COUNT(*) FROM agenda WHERE data = ?", (hoje_iso,))
            total_consultas = cursor.fetchone()[0]
            conn.close()
            
            if hasattr(self.screen_home, "card_pacientes"):
                self.screen_home.card_pacientes.set_valor(str(total_pacientes))
            if hasattr(self.screen_home, "card_consultas"):
                self.screen_home.card_consultas.set_valor(str(total_consultas))
        except:
            pass

    def init_db_estruturas(self):
        try:
            # CAMINHO CORRIGIDO AQUI
            conn = sqlite3.connect(obter_caminho_db())
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS pastas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, horario TEXT NOT NULL, data TEXT NOT NULL, paciente TEXT NOT NULL, status TEXT NOT NULL)")
            try:
                cursor.execute("ALTER TABLE pacientes ADD COLUMN pasta TEXT DEFAULT 'Geral'")
            except sqlite3.OperationalError:
                pass 
            conn.commit()
            conn.close()
        except:
            pass

    def carregar_pastas_sqlite(self):
        try:
            # CAMINHO CORRIGIDO AQUI
            conn = sqlite3.connect(obter_caminho_db())
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM pastas ORDER BY nome ASC")
            rows = cursor.fetchall()
            pastas_atuais = [row[0] for row in rows]
            if len(pastas_atuais) > 1 and ("Cardiologia" in pastas_atuais or "Pediatria" in pastas_atuais):
                cursor.execute("DELETE FROM pastas WHERE nome != 'Geral'")
                conn.commit()
                pastas_atuais = ["Geral"]
            conn.close()
            if pastas_atuais:
                return pastas_atuais
        except:
            pass
        return ["Geral"]

    def sincronizar_pastas_sistema(self, nova_lista):
        try:
            self.pastas_sistema = sorted(list(set(nova_lista)))
            # CAMINHO CORRIGIDO AQUI
            conn = sqlite3.connect(obter_caminho_db())
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pastas")
            for pasta in self.pastas_sistema:
                cursor.execute("INSERT INTO pastas (nome) VALUES (?)", (pasta,))
            conn.commit()
            conn.close()
            self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        except:
            pass