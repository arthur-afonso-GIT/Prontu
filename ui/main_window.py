import os
import sys
import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from ui.screens.home import HomeScreen
from ui.screens.pacientes import PacientesScreen, normalizar_nome_pasta
from ui.screens.agenda import AgendaScreen 
from ui.screens.financeiro import FinanceiroScreen
from ui.screens.configuracoes import ConfiguracoesScreen

try:
    from ui.screens.fichas import FichasScreen
except ImportError:
    FichasScreen = None


class MainWindow(QMainWindow):
    def __init__(self, database_instancia):
        super().__init__()
        caminho_logo = os.path.join(os.path.dirname(__file__), "assets", "prontu_logo.png")
        if os.path.exists(caminho_logo):
            self.setWindowIcon(QIcon(caminho_logo))
        self.setWindowTitle("Prontu — Gerenciamento Inteligente")
        self.resize(1200, 750)
        
        # Recebe a conexão única do Supabase ativada no main.py
        self.db = database_instancia
        self._ultima_atualizacao_tela = {}

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
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(4, 0, 0, 24)
        logo_layout.setSpacing(10)
        logo_icone = QLabel()
        logo_icone.setFixedSize(48, 48)
        if os.path.exists(caminho_logo):
            logo_icone.setPixmap(QPixmap(caminho_logo).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        logo_layout.addWidget(logo_icone)
        logo_label = QLabel("Prontu")
        logo_label.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)
        
        # Botões de Navegação
        self.btn_home = QPushButton(" 🏠 Painel Principal")
        self.btn_pacientes = QPushButton(" 👤 Pacientes")
        self.btn_agenda = QPushButton(" 📅 Agenda de Consultas")
        self.btn_fichas = QPushButton(" 📝 Fichas Clínicas")
        self.btn_config = QPushButton(" ⚙️ Configurações")
        
        self.btn_financeiro = QPushButton(" 💰 Financeiro")
        self.botoes_menu = [self.btn_home, self.btn_pacientes, self.btn_agenda, self.btn_fichas, self.btn_financeiro, self.btn_config]
        
        for btn in self.botoes_menu:
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # Rodapé da Sidebar
        self.lbl_status_sessao = QLabel()
        self.lbl_status_sessao.setStyleSheet("font-size: 11px; padding-left: 8px;")
        sidebar_layout.addWidget(self.lbl_status_sessao)
        
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
            on_agendar_retorno_click=self.agendar_retorno_do_painel,
        )
        self.screen_pacientes = PacientesScreen(self.db)
        self.screen_agenda = AgendaScreen(self.db)
        self.screen_fichas = FichasScreen(self.db) if FichasScreen is not None else QWidget()
        self.screen_financeiro = FinanceiroScreen(self.db)
        self.screen_pacientes.window_principal = self
        self.screen_agenda.window_principal = self
        if hasattr(self.screen_fichas, "__dict__"):
            self.screen_fichas.window_principal = self
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
        self.painel_telas.addWidget(self.screen_financeiro)

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
        self.btn_financeiro.clicked.connect(lambda: self.mudar_tela(5, self.btn_financeiro))
        
        # Define a tela padrão inicial (Home)
        self.mudar_tela(0, self.btn_home)
        self.atualizar_status_sessao()

    def atualizar_status_sessao(self):
        """Exibe somente um estado que o aplicativo consegue afirmar com segurança."""
        sessao_ativa = bool(getattr(self.db, "esta_autenticado", lambda: False)())
        if sessao_ativa:
            self.lbl_status_sessao.setText("Sessão segura ativa")
            self.lbl_status_sessao.setStyleSheet("color: #86efac; font-size: 11px; padding-left: 8px;")
        else:
            self.lbl_status_sessao.setText("Sessão precisa ser revalidada")
            self.lbl_status_sessao.setStyleSheet("color: #fbbf24; font-size: 11px; padding-left: 8px;")

    def mudar_tela(self, indice, botao_ativo, atualizar=True):
        """Muda o painel visível, atualiza o estado visual do botão selecionado
        e dispara o refresh de dados da tela que acabou de ficar visível —
        garantindo que cada aba sempre mostre dados atuais do banco."""
        tela_anterior = self.painel_telas.currentWidget()
        if indice != self.painel_telas.currentIndex() and not self.confirmar_descarte_de_alteracoes():
            return

        if tela_anterior is self.screen_agenda and indice != 2:
            cancelar_retorno = getattr(self.screen_agenda, "cancelar_retorno_em_agendamento", None)
            if cancelar_retorno:
                cancelar_retorno()

        self.painel_telas.setCurrentIndex(indice)
        
        for btn in self.botoes_menu:
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        botao_ativo.setProperty("active", "true")
        botao_ativo.style().unpolish(botao_ativo)
        botao_ativo.style().polish(botao_ativo)

        # --- Gatilhos de atualização por tela ---
        if not atualizar:
            return

        agora = time.monotonic()
        ultima = self._ultima_atualizacao_tela.get(indice, 0)
        if agora - ultima < 2.0:
            return
        self._ultima_atualizacao_tela[indice] = agora
        QTimer.singleShot(40, lambda: self._atualizar_tela_visivel(indice))

    def confirmar_descarte_de_alteracoes(self, proxima_acao="trocar de tela"):
        """Evita perder dados digitados antes de trocar de tela ou fechar o app."""
        tela_atual = self.painel_telas.currentWidget()
        possui_alteracoes = getattr(tela_atual, "tem_alteracoes_nao_salvas", lambda: False)
        if not possui_alteracoes():
            return True

        dialogo = QMessageBox(self)
        dialogo.setWindowTitle("Alterações não salvas")
        dialogo.setText("Existem alterações que ainda não foram salvas.")
        dialogo.setInformativeText(f"Deseja descartar essas alterações e {proxima_acao}?")
        dialogo.setIcon(QMessageBox.Icon.Warning)
        dialogo.setStandardButtons(
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        dialogo.setDefaultButton(QMessageBox.StandardButton.Cancel)
        dialogo.setStyleSheet(
            "QMessageBox { background: #ffffff; } QLabel { color: #0f172a; font-size: 13px; } "
            "QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; "
            "border-radius: 5px; padding: 6px 14px; font-weight: bold; }"
        )
        if dialogo.exec() != QMessageBox.StandardButton.Discard:
            return False

        descartar = getattr(tela_atual, "descartar_alteracoes_nao_salvas", None)
        if descartar:
            descartar()
        return True

    def closeEvent(self, event):
        """Impede que o fechamento da janela descarte formulários em andamento."""
        if self.confirmar_descarte_de_alteracoes("fechar o aplicativo"):
            event.accept()
        else:
            event.ignore()

    def _atualizar_tela_visivel(self, indice):
        """Atualiza dados depois que a tela escolhida já foi desenhada."""
        if self.painel_telas.currentIndex() != indice:
            return

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
        elif indice == 5:
            if hasattr(self.screen_financeiro, 'carregar_dados'):
                self.screen_financeiro.carregar_dados()

    def navegar_para_novo_paciente(self):
        """Callback do botão 'Novo Paciente' da Home: limpa o formulário e vai para a aba de Pacientes."""
        if hasattr(self.screen_pacientes, 'limpar_formulario'):
            self.screen_pacientes.limpar_formulario()
        self.mudar_tela(1, self.btn_pacientes)

    def editar_ficha_preenchida(self, ficha_id):
        """Navega para a ficha e a abre após a atualização visual da tela."""
        self.mudar_tela(3, self.btn_fichas, atualizar=False)
        QTimer.singleShot(
            0,
            lambda: self.screen_fichas.abrir_ficha_para_edicao(ficha_id)
            if hasattr(self.screen_fichas, "abrir_ficha_para_edicao") else None,
        )

    def abrir_nova_ficha_para_paciente(self, paciente_id):
        """Abre uma nova ficha já vinculada ao paciente atendido na agenda."""
        self.mudar_tela(3, self.btn_fichas, atualizar=False)
        QTimer.singleShot(
            0,
            lambda: self.screen_fichas.iniciar_nova_ficha_para_paciente(paciente_id)
            if hasattr(self.screen_fichas, "iniciar_nova_ficha_para_paciente") else None,
        )

    def agendar_retorno_do_painel(self, retorno):
        """Abre a Agenda já preenchida a partir de um retorno pendente."""
        self.mudar_tela(2, self.btn_agenda, atualizar=False)
        if self.painel_telas.currentIndex() != 2:
            return
        QTimer.singleShot(
            0,
            lambda: self.screen_agenda.preencher_agendamento_retorno(retorno)
            if hasattr(self.screen_agenda, "preencher_agendamento_retorno") else None,
        )

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
            
            pastas_atuais = []
            for row in resposta.data:
                nome = normalizar_nome_pasta(row.get("nome"))
                if nome and nome.casefold() not in {p.casefold() for p in pastas_atuais}:
                    pastas_atuais.append(nome)
            self.pastas_cores = {
                normalizar_nome_pasta(row.get("nome")): (row.get("cor") or "#0284c7")
                for row in resposta.data if normalizar_nome_pasta(row.get("nome"))
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
            self.pastas_sistema = sorted({
                normalizar_nome_pasta(p)
                for p in nova_lista
                if normalizar_nome_pasta(p)
            })
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
