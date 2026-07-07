import sqlite3
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame)
from PySide6.QtCore import Qt

from ui.screens.home import HomeScreen
from ui.screens.pacientes import PacientesScreen
from ui.screens.agenda import AgendaScreen  

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prontu — Prontuário Médico Inteligente")
        self.resize(1200, 750)
        
        # 1. 🗄️ Inicializa a estrutura e tabelas essenciais da base de dados
        self.init_db_estruturas()
        self.pastas_sistema = self.carregar_pastas_sqlite()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 2. SIDEBAR LATERAL ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
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
        sidebar_layout.addWidget(self.btn_fichas)
        
        sidebar_layout.addStretch()
        
        self.btn_config = QPushButton("⚙️ Configurações")
        self.btn_config.setCheckable(True)
        sidebar_layout.addWidget(self.btn_config)
        
        main_layout.addWidget(self.sidebar)
        
        # --- 3. ÁREA DE CONTEÚDO (STACKED WIDGET) ---
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f8fafc;")
        
        self.screen_home = HomeScreen(
            window_principal=self,
            on_novo_paciente_click=self.ir_para_tela_pacientes,
            on_pasta_click=self.processar_clique_pasta_home
        )
        self.screen_pacientes = PacientesScreen()
        self.screen_agenda = AgendaScreen()
        
        self.stack.addWidget(self.screen_home)
        self.stack.addWidget(self.screen_pacientes)
        self.stack.addWidget(self.screen_agenda)
        
        main_layout.addWidget(self.stack, stretch=1)
        
        # --- 4. ATUALIZAÇÕES E CONEXÕES REAIS ---
        self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        
        nomes_iniciais = []
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM pacientes")
            nomes_iniciais = [row[0].upper() for row in cursor.fetchall()]
            conn.close()
        except:
            pass
        
        self.screen_agenda.atualizar_lista_sugestoes(nomes_iniciais)
        
        # Renderização inicial segura
        self.screen_home.renderizar_lista_pastas()
        self.atualizar_dados_home()

    def init_db_estruturas(self):
        """Garante que todas as tabelas necessárias existem fisicamente no SQLite e cria a coluna pasta se faltar"""
        conn = sqlite3.connect("consultorio.db")
        cursor = conn.cursor()
        
        # Tabela de Pastas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pastas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        """)
        
        # Tabela da Agenda
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                horario TEXT NOT NULL,
                data TEXT NOT NULL,
                paciente TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        
        # 🛡️ PROTEÇÃO: Garante que a coluna 'pasta' existe na sua tabela de pacientes
        try:
            cursor.execute("ALTER TABLE pacientes ADD COLUMN pasta TEXT DEFAULT 'Geral'")
        except sqlite3.OperationalError:
            pass # A coluna já existe, tudo certo
            
        conn.commit()
        conn.close()

    def carregar_pastas_sqlite(self):
        """Carrega as pastas. Limpa as genéricas de teste antigas deixando só a 'Geral'"""
        conn = sqlite3.connect("consultorio.db")
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM pastas ORDER BY nome ASC")
        rows = cursor.fetchall()
        
        pastas_atuais = [row[0] for row in rows]
        # Se contiver os resquícios das pastas antigas genéricas, limpa imediatamente do banco
        if len(pastas_atuais) > 1 and ("Cardiologia" in pastas_atuais or "Pediatria" in pastas_atuais):
            cursor.execute("DELETE FROM pastas WHERE nome != 'Geral'")
            conn.commit()
            pastas_atuais = ["Geral"]
            
        conn.close()
        
        if pastas_atuais:
            return pastas_atuais
        
        # Caso esteja 100% vazia, insere unicamente a pasta padrão
        pastas_padrao = ["Geral"]
        conn = sqlite3.connect("consultorio.db")
        cursor = conn.cursor()
        for pasta in pastas_padrao:
            try:
                cursor.execute("INSERT INTO pastas (nome) VALUES (?)", (pasta,))
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        conn.close()
        return pastas_padrao

    def sincronizar_pastas_sistema(self, nova_lista):
        self.pastas_sistema = sorted(list(set(nova_lista)))
        conn = sqlite3.connect("consultorio.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pastas")
        for pasta in self.pastas_sistema:
            cursor.execute("INSERT INTO pastas (nome) VALUES (?)", (pasta,))
        conn.commit()
        conn.close()
        self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)

    def mudar_tela(self, destino_widget, botao_clicado):
        self.stack.setCurrentWidget(destino_widget)
        for btn in [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]:
            btn.setChecked(btn == botao_clicado)
            
        if destino_widget == self.screen_home:
            self.atualizar_dados_home()

    def ir_para_tela_pacientes(self):
        self.mudar_tela(self.screen_pacientes, self.btn_pacientes)

    def processar_clique_pasta_home(self, nome_pasta):
        self.screen_pacientes.filtrar_por_pasta_externo(nome_pasta)
        self.ir_para_tela_pacientes()

    def atualizar_dados_home(self):
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pacientes")
            total_pacientes = cursor.fetchone()[0]
            
            from PySide6.QtCore import QDate
            hoje_iso = QDate.currentDate().toString("yyyy-MM-dd")
            cursor.execute("SELECT COUNT(*) FROM agenda WHERE data = ?", (hoje_iso,))
            total_consultas = cursor.fetchone()[0]
            conn.close()
        except:
            total_pacientes = 0
            total_consultas = 0
            
        self.screen_home.card_pacientes.set_valor(str(total_pacientes))
        self.screen_home.card_consultas.set_valor(str(total_consultas))