import os
import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame,
                               QScrollArea)
from PySide6.QtCore import Qt, QEvent, QTimer

from ui.screens.home import HomeScreen
from ui.screens.pacientes import PacientesScreen, normalizar_nome_pasta
from ui.screens.agenda import AgendaScreen 
from ui.screens.configuracoes import ConfiguracoesScreen
from ui.screens.financeiro import FinanceiroScreen
from ui.screens.equipe import EquipeScreen

try:
    from ui.screens.fichas import FichasScreen
except ImportError:
    FichasScreen = None


class MainWindow(QMainWindow):
    INDICE_HOME = 0
    INDICE_EQUIPE = 5

    def __init__(self, database_instancia):
        super().__init__()
        self.setWindowTitle("Prontu — Gerenciamento Inteligente")
        self.resize(1200, 750)
        self.setMinimumSize(900, 600)
        self._layout_refresh_timer = QTimer(self)
        self._layout_refresh_timer.setSingleShot(True)
        self._layout_refresh_timer.timeout.connect(self._recalcular_layout_visivel)
        
        # Recebe a conexão única do Supabase ativada no main.py
        self.db = database_instancia
        self.pode_gerenciar_equipe = self._usuario_pode_gerenciar_equipe(self.db)

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
        self.sidebar = sidebar
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
        self.btn_financeiro = QPushButton(" 💰 Financeiro")
        self.btn_equipe = QPushButton(" 👥 Equipe")
        self.btn_equipe.setVisible(self.pode_gerenciar_equipe)
        self.btn_config = QPushButton(" ⚙️ Configurações")
        
        self.botoes_menu = [
            self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas,
            self.btn_financeiro, self.btn_equipe, self.btn_config,
        ]
        
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
            on_pasta_click=self.filtrar_pacientes_por_pasta,
            on_agendar_retorno_click=self.agendar_retorno_da_home,
            on_consulta_click=self.abrir_consulta_da_home,
        )
        self.screen_pacientes = PacientesScreen(self.db)
        self.screen_agenda = AgendaScreen(self.db)
        self.screen_fichas = FichasScreen(self.db) if FichasScreen is not None else QWidget()
        self.screen_financeiro = FinanceiroScreen(self.db)
        # Perfis sem permissao nao recebem nem mesmo a tela de administracao no
        # cliente. A Edge Function continua sendo a protecao definitiva.
        self.screen_equipe = EquipeScreen(self.db) if self.pode_gerenciar_equipe else QWidget()
        # ConfiguracoesScreen também precisa da JANELA PRINCIPAL (self), não do banco,
        # para conseguir chamar self.screen_home.atualizar_saudacao_dinamica() ao salvar.
        self.screen_config = ConfiguracoesScreen(window_principal=self)

        # Telas que precisam navegar entre módulos recebem uma referência explícita
        # da janela principal. Isso evita cliques silenciosos em ações como
        # "Abrir ficha" na Agenda.
        self.screen_pacientes.window_principal = self
        self.screen_agenda.window_principal = self
        self.screen_fichas.window_principal = self
        
        self.painel_telas.addWidget(self.screen_home)      # Índice 0
        self.painel_telas.addWidget(self.screen_pacientes) # Índice 1
        self.painel_telas.addWidget(self.screen_agenda)    # Índice 2
        self.painel_telas.addWidget(self.screen_fichas)    # Índice 3
        self.painel_telas.addWidget(self.screen_financeiro) # Índice 4
        self.painel_telas.addWidget(self.screen_equipe)     # Índice 5
        self.painel_telas.addWidget(self.screen_config)     # Índice 6
        
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
        self.btn_financeiro.clicked.connect(lambda: self.mudar_tela(4, self.btn_financeiro))
        if self.pode_gerenciar_equipe:
            self.btn_equipe.clicked.connect(lambda: self.mudar_tela(self.INDICE_EQUIPE, self.btn_equipe))
        self.btn_config.clicked.connect(lambda: self.mudar_tela(6, self.btn_config))
        
        # Define a tela padrão inicial (Home)
        self.mudar_tela(0, self.btn_home)
        self._atualizar_sidebar_responsiva()

    def mudar_tela(self, indice, botao_ativo):
        """Muda o painel visível, atualiza o estado visual do botão selecionado
        e dispara o refresh de dados da tela que acabou de ficar visível —
        garantindo que cada aba sempre mostre dados atuais do banco."""
        # Bloqueia tambem navegacoes indiretas para a tela Equipe. Assim, mesmo
        # que algum callback antigo tente abrir o indice 5, nenhum dado e pedido.
        if indice == self.INDICE_EQUIPE and not self._usuario_pode_gerenciar_equipe(self.db):
            indice = self.INDICE_HOME
            botao_ativo = self.btn_home

        self.painel_telas.setCurrentIndex(indice)
        self._agendar_recalculo_layout()
        
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
            if hasattr(self.screen_financeiro, 'carregar_dados'):
                self.screen_financeiro.carregar_dados()
        elif indice == 5:
            if hasattr(self.screen_equipe, 'carregar_dados'):
                self.screen_equipe.carregar_dados()
        elif indice == 6:
            if hasattr(self.screen_config, 'carregar_dados_configurados'):
                self.screen_config.carregar_dados_configurados()

    @staticmethod
    def _usuario_pode_gerenciar_equipe(database):
        """Somente o proprietario pode visualizar e administrar a equipe."""
        try:
            return database.obter_papel_atual() == "proprietario"
        except (AttributeError, TypeError):
            return False

    def _agendar_recalculo_layout(self, atraso=40):
        """Agrupa eventos de redimensionamento e atualiza a tela somente ao final."""
        timer = getattr(self, "_layout_refresh_timer", None)
        if timer is not None:
            timer.start(atraso)

    def _recalcular_layout_visivel(self):
        """Corrige geometrias antigas que o Windows pode manter após maximizar."""
        self._atualizar_sidebar_responsiva()
        central = self.centralWidget()
        atual = self.painel_telas.currentWidget() if hasattr(self, "painel_telas") else None
        for widget in (central, getattr(self, "painel_telas", None), atual):
            if widget is None:
                continue
            widget.updateGeometry()
            layout = widget.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            widget.update()

        # Areas rolaveis possuem uma arvore de geometrias propria. Atualiza-las
        # explicitamente evita que conservem a largura/altura da janela anterior.
        if atual is not None:
            if hasattr(atual, "_ajustar_altura_formulario"):
                atual._ajustar_altura_formulario()
            for area in atual.findChildren(QScrollArea):
                conteudo = area.widget()
                if conteudo is not None:
                    conteudo.updateGeometry()
                    layout = conteudo.layout()
                    if layout is not None:
                        layout.invalidate()
                        layout.activate()
                area.viewport().update()

    def _atualizar_sidebar_responsiva(self):
        """Libera mais espaco para o conteudo em janelas de largura reduzida."""
        sidebar = getattr(self, "sidebar", None)
        if sidebar is None:
            return
        largura = 200 if self.width() < 1250 else 240
        if sidebar.width() != largura:
            sidebar.setFixedWidth(largura)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._agendar_recalculo_layout()

    def showEvent(self, evento):
        super().showEvent(evento)
        self._agendar_recalculo_layout(0)

    def changeEvent(self, evento):
        super().changeEvent(evento)
        if evento.type() == QEvent.Type.WindowStateChange:
            self._agendar_recalculo_layout(80)
            # No Windows a geometria final do modo maximizado pode chegar depois
            # do primeiro evento. Uma segunda passagem curta estabiliza o layout.
            QTimer.singleShot(220, self._recalcular_layout_visivel)

    def navegar_para_novo_paciente(self):
        """Callback do botão 'Novo Paciente' da Home: limpa o formulário e vai para a aba de Pacientes."""
        self.mudar_tela(1, self.btn_pacientes)
        if hasattr(self.screen_pacientes, 'preparar_novo_paciente'):
            self.screen_pacientes.preparar_novo_paciente("Geral")
        elif hasattr(self.screen_pacientes, 'limpar_formulario'):
            self.screen_pacientes.limpar_formulario()

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

    def abrir_consulta_da_home(self, consulta):
        """Abre a Agenda já posicionada na consulta escolhida no painel."""
        self.mudar_tela(2, self.btn_agenda)
        if hasattr(self.screen_agenda, "abrir_consulta_por_data_hora"):
            self.screen_agenda.abrir_consulta_por_data_hora(consulta)

    def abrir_nova_ficha_para_paciente(self, paciente_id):
        """Abre Fichas Clínicas e prepara uma nova ficha para o paciente informado."""
        self.mudar_tela(3, self.btn_fichas)
        if hasattr(self.screen_fichas, "iniciar_nova_ficha_para_paciente"):
            return self.screen_fichas.iniciar_nova_ficha_para_paciente(paciente_id)
        return False

    def agendar_retorno_da_home(self, retorno):
        """Leva um retorno pendente para o formulário da Agenda."""
        self.mudar_tela(2, self.btn_agenda)
        if hasattr(self.screen_agenda, "preencher_agendamento_retorno"):
            self.screen_agenda.preencher_agendamento_retorno(retorno)

    def agendar_retorno_do_painel(self, retorno):
        """Atalho usado pelo prontuário do paciente para preparar o retorno."""
        self.agendar_retorno_da_home(retorno)

    def abrir_retorno_na_agenda(self, retorno):
        """Abre a Agenda diretamente na data já definida para o retorno."""
        self.mudar_tela(2, self.btn_agenda)
        if hasattr(self.screen_agenda, "abrir_data_do_retorno"):
            self.screen_agenda.abrir_data_do_retorno(retorno.get("data_prevista"))

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
            
            pastas_atuais = [
                normalizar_nome_pasta(row.get("nome"))
                for row in (resposta.data or [])
                if normalizar_nome_pasta(row.get("nome"))
            ]
            self.pastas_cores = {
                normalizar_nome_pasta(row.get("nome")): (row.get("cor") or "#0284c7")
                for row in (resposta.data or []) if normalizar_nome_pasta(row.get("nome"))
            }

            # Recupera tambem pastas presentes em pacientes antigos ou vindos
            # de importacao. Assim nenhuma pasta some da Home apenas porque o
            # cadastro auxiliar ficou desatualizado.
            resposta_pacientes = self.db.supabase.table("pacientes")\
                .select("pasta")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .is_("deleted_at", "null")\
                .execute()
            pastas_atuais.extend(
                normalizar_nome_pasta(row.get("pasta")) or "Geral"
                for row in (resposta_pacientes.data or [])
            )

            unicas = {}
            for pasta in ["Geral", *pastas_atuais]:
                nome = normalizar_nome_pasta(pasta) or "Geral"
                unicas.setdefault(nome.casefold(), nome)
                self.pastas_cores.setdefault(nome, "#0284c7")
            return sorted(unicas.values(), key=lambda nome: (nome.casefold() != "geral", nome.casefold()))
        except Exception as e:
            print(f"Erro ao carregar pastas: {e}")
        return ["Geral"]

    def recarregar_pastas_sistema(self):
        """Reconcilia pastas e pacientes e atualiza imediatamente Home e formulário."""
        self.pastas_sistema = self.carregar_pastas_sqlite()
        if hasattr(self.screen_pacientes, "pastas_cores"):
            self.screen_pacientes.pastas_cores = self.pastas_cores
        if hasattr(self.screen_pacientes, "atualizar_combobox_pastas"):
            self.screen_pacientes.atualizar_combobox_pastas(self.pastas_sistema)
        if hasattr(self.screen_home, "renderizar_lista_pastas"):
            self.screen_home.renderizar_lista_pastas(force=True)

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
