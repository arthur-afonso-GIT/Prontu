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
    FichasScreen = None


class MainWindow(QMainWindow):
    def __init__(self, database_instancia):
        super().__init__()
        self.setWindowTitle("Prontu — Prontuário Médico Inteligente")
        self.resize(1200, 750)
        
        # Recebe a conexão única do Supabase ativada no main.py
        self.db = database_instancia

        self.init_db_estruturas()
        self.pastas_sistema = self.carregar_pastas_sqlite()
        
        # --- WIDGET CENTRAL ---
        central_widget = QWidget()
        central_widget.setObjectName("PainelCentralProntu")
        central_widget.setStyleSheet("#PainelCentralProntu { background-color: #f8fafc; }")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 1. SIDEBAR LATERAL DE NAVEGAÇÃO ---
        sidebar = QFrame()
        sidebar.setObjectName("SidebarProntu")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            #SidebarProntu {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
            QPushButton {
                color: #94a3b8;
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #f8fafc;
                background-color: #1e293b;
            }
            QPushButton[active="true"] {
                color: #ffffff;
                background-color: #0284c7;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(8)
        
        # Logo / Título do App
        logo_label = QLabel("🏥 Prontu")
        logo_label.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold; margin-bottom: 24px; padding-left: 8px;")
        sidebar_layout.addWidget(logo_label)
        
        # Botões de Navegação
        self.btn_home = QPushButton(" 🏠 Painel Principal")
        self.btn_pacientes = QPushButton(" 👤 Pacientes")
        self.btn_agenda = QPushButton(" 📅 Agenda de Consultas")
        self.btn_fichas = QPushButton(" 📝 Fichas Clínicas")
        self.btn_config = QPushButton(" ⚙️ Configurações")
        
        self.botoes_menu = [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_config]
        
        for btn in self.botoes_menu:
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # Rodapé da Sidebar
        nome_clinica = "Conectado à Nuvem"
        footer_label = QLabel(nome_clinica)
        footer_label.setStyleSheet("color: #64748b; font-size: 11px; padding-left: 8px;")
        sidebar_layout.addWidget(footer_label)
        
        main_layout.addWidget(sidebar)
        
        # --- 2. PAINEL DE TELAS DINÂMICAS (STACKED WIDGET) ---
        self.painel_telas = QStackedWidget()
        
        # HomeScreen precisa da JANELA PRINCIPAL (self) — e não do banco — porque
        # é através dela que acessa self.pastas_sistema, self.sincronizar_pastas_sistema()
        # e self.screen_pacientes. Também precisa dos dois callbacks de navegação.
        self.screen_home = HomeScreen(
            self,
            on_novo_paciente_click=self.navegar_para_novo_paciente,
            on_pasta_click=self.filtrar_pacientes_por_pasta
        )
        self.screen_pacientes = PacientesScreen(self.db)
        self.screen_agenda = AgendaScreen(self.db)
        self.screen_fichas = FichasScreen() if FichasScreen is not None else QWidget()
        # ConfiguracoesScreen também precisa da JANELA PRINCIPAL (self), não do banco,
        # para conseguir chamar self.screen_home.atualizar_saudacao_dinamica() ao salvar.
        self.screen_config = ConfiguracoesScreen(window_principal=self)
        
        self.painel_telas.addWidget(self.screen_home)      # Índice 0
        self.painel_telas.addWidget(self.screen_pacientes) # Índice 1
        self.painel_telas.addWidget(self.screen_agenda)    # Índice 2
        self.painel_telas.addWidget(self.screen_fichas)    # Índice 3
        self.painel_telas.addWidget(self.screen_config)    # Índice 4
        
        # Sincroniza a lista de pastas já carregada com o combobox de Pacientes
        # assim que a tela é criada, sem precisar esperar o usuário trocar de aba.
        if hasattr(self.screen_pacientes, 'atualizar_combobox_pastas'):
            self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        self.screen_pacientes.pastas_cores = self.pastas_cores
        
        main_layout.addWidget(self.painel_telas)
        
        # --- 3. LOGICA DE ALTERAÇÃO DE TELA ---
        self.btn_home.clicked.connect(lambda: self.mudar_tela(0, self.btn_home))
        self.btn_pacientes.clicked.connect(lambda: self.mudar_tela(1, self.btn_pacientes))
        self.btn_agenda.clicked.connect(lambda: self.mudar_tela(2, self.btn_agenda))
        self.btn_fichas.clicked.connect(lambda: self.mudar_tela(3, self.btn_fichas))
        self.btn_config.clicked.connect(lambda: self.mudar_tela(4, self.btn_config))
        
        # Define a tela padrão inicial (Home)
        self.mudar_tela(0, self.btn_home)

    def mudar_tela(self, indice, botao_ativo):
        """Muda o painel visível, atualiza o estado visual do botão selecionado
        e dispara o refresh de dados da tela que acabou de ficar visível —
        garantindo que cada aba sempre mostre dados atuais do banco."""
        self.painel_telas.setCurrentIndex(indice)
        
        for btn in self.botoes_menu:
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        botao_ativo.setProperty("active", "true")
        botao_ativo.style().unpolish(botao_ativo)
        botao_ativo.style().polish(botao_ativo)

        # --- Gatilhos de atualização por tela ---
        if indice == 0:
            if hasattr(self.screen_home, 'renderizar_lista_pastas'):
                self.screen_home.renderizar_lista_pastas()
        elif indice == 1:
            if hasattr(self.screen_pacientes, 'carregar_pacientes_tabela'):
                self.screen_pacientes.carregar_pacientes_tabela()
            if hasattr(self.screen_pacientes, 'atualizar_combobox_pastas'):
                self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        elif indice == 2:
            if hasattr(self.screen_agenda, 'carregar_lista_pacientes_combobox'):
                self.screen_agenda.carregar_lista_pacientes_combobox()
            if hasattr(self.screen_agenda, 'renderizar_timeline_calendario'):
                self.screen_agenda.renderizar_timeline_calendario()
        elif indice == 3:
            if hasattr(self.screen_fichas, 'carregar_pacientes_combo'):
                self.screen_fichas.carregar_pacientes_combo()
            if hasattr(self.screen_fichas, 'carregar_modelos_iniciais_combo'):
                self.screen_fichas.carregar_modelos_iniciais_combo()
        elif indice == 4:
            if hasattr(self.screen_config, 'carregar_dados_configurados'):
                self.screen_config.carregar_dados_configurados()

    def navegar_para_novo_paciente(self):
        """Callback do botão 'Novo Paciente' da Home: limpa o formulário e vai para a aba de Pacientes."""
        if hasattr(self.screen_pacientes, 'limpar_formulario'):
            self.screen_pacientes.limpar_formulario()
        self.mudar_tela(1, self.btn_pacientes)

    def abrir_paciente_especifico(self, paciente_id):
        """Vai para a aba Pacientes e já abre o prontuário de um paciente específico
        (usado pelo duplo-clique na lista de 'Recentes' da Home)."""
        self.mudar_tela(1, self.btn_pacientes)
        if hasattr(self.screen_pacientes, 'selecionar_paciente_por_id'):
            self.screen_pacientes.selecionar_paciente_por_id(paciente_id)

    def filtrar_pacientes_por_pasta(self, nome_pasta):
        """Callback de clique num card de pasta na Home: vai para Pacientes já filtrado por essa pasta."""
        self.mudar_tela(1, self.btn_pacientes)
        if hasattr(self.screen_pacientes, 'filtrar_por_pasta_externo'):
            self.screen_pacientes.filtrar_por_pasta_externo(nome_pasta)

    def init_db_estruturas(self):
        """Cria as tabelas auxiliares necessárias se elas não existirem no Supabase."""
        if not self.db.supabase or self.db.consultorio_id is None:
            return
        try:
            # Verifica se a tabela 'pastas' está operacional
            self.db.supabase.table("pastas").select("id").limit(1).execute()
        except Exception:
            print("Aviso: Estrutura remota de pastas necessita de verificação manual no painel.")

    def carregar_pastas_sqlite(self):
        """Busca a lista de pastas (e suas cores) salvas na nuvem para este consultório.
        Preenche self.pastas_cores como efeito colateral e retorna só os nomes,
        pra manter compatibilidade com todo o código existente que trata
        pastas_sistema como uma lista simples de strings."""
        self.pastas_cores = {}
        if not self.db.supabase or self.db.consultorio_id is None:
            return ["Geral"]
        try:
            resposta = self.db.supabase.table("pastas")\
                .select("nome, cor")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .order("nome")\
                .execute()
            
            pastas_atuais = [row["nome"].strip() for row in resposta.data if (row.get("nome") or "").strip()]
            self.pastas_cores = {
                row["nome"].strip(): (row.get("cor") or "#0284c7")
                for row in resposta.data if (row.get("nome") or "").strip()
            }
            if pastas_atuais:
                return pastas_atuais
        except Exception as e:
            print(f"Erro ao carregar pastas: {e}")
        return ["Geral"]

    def sincronizar_pastas_sistema(self, nova_lista):
        """Persiste a nova lista de pastas no Supabase e propaga a atualização
        para todas as telas que dependem dela (Pacientes e a própria Home).
        Preserva a cor já escolhida de cada pasta existente; pastas novas
        recebem a cor padrão."""
        if not self.db.supabase or self.db.consultorio_id is None:
            return
        try:
            self.pastas_sistema = sorted(set(p.strip() for p in nova_lista if (p or "").strip()))
            if not self.pastas_sistema:
                self.pastas_sistema = ["Geral"]
            
            self.db.supabase.table("pastas")\
                .delete()\
                .eq("consultorio_id", self.db.consultorio_id)\
                .execute()
                
            payload = [
                {
                    "consultorio_id": self.db.consultorio_id,
                    "nome": pasta,
                    "cor": self.pastas_cores.get(pasta, "#0284c7")
                }
                for pasta in self.pastas_sistema
            ]
            if payload:
                self.db.supabase.table("pastas").insert(payload).execute()
                
            if hasattr(self.screen_pacientes, 'atualizar_combobox_pastas'):
                self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
            if hasattr(self.screen_pacientes, 'pastas_cores'):
                self.screen_pacientes.pastas_cores = self.pastas_cores
        except Exception as e:
            print(f"Erro ao sincronizar pastas: {e}")

    def atualizar_cor_pasta(self, nome_pasta, nova_cor):
        """Atualiza só a cor de uma pasta específica (sem mexer na lista de nomes)
        e propaga para a tela de Pacientes, que usa a cor pra colorir a coluna 'Pasta'."""
        if not self.db.supabase or self.db.consultorio_id is None:
            return
        self.pastas_cores[nome_pasta] = nova_cor
        try:
            self.db.supabase.table("pastas")\
                .update({"cor": nova_cor})\
                .eq("consultorio_id", self.db.consultorio_id)\
                .eq("nome", nome_pasta)\
                .execute()
        except Exception as e:
            print(f"Erro ao salvar cor da pasta: {e}")

        self.screen_pacientes.pastas_cores = self.pastas_cores
        if hasattr(self.screen_pacientes, 'carregar_pacientes_tabela'):
            self.screen_pacientes.carregar_pacientes_tabela()