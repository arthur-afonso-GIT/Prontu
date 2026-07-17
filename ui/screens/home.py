import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QTableWidget, QHeaderView, QPushButton, 
                               QInputDialog, QMessageBox, QTableWidgetItem, QColorDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from ui.screens.pacientes import normalizar_nome_pasta
class HomeScreen(QWidget):
    def __init__(self, window_principal, on_novo_paciente_click=None, on_pasta_click=None, on_agendar_retorno_click=None, on_consulta_click=None):
        super().__init__()
        
        self.window_principal = window_principal
        self.on_novo_paciente_click = on_novo_paciente_click
        self.on_pasta_click = on_pasta_click
        self.on_agendar_retorno_click = on_agendar_retorno_click
        self.on_consulta_click = on_consulta_click
        self.db = window_principal.db
        
        # Layout Principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(26, 28, 26, 24)
        main_layout.setSpacing(18)
        
        # --- 1. CABEÇALHO DINÂMICO ---
        header_layout = QHBoxLayout()
        welcome_vbox = QVBoxLayout()
        welcome_vbox.setSpacing(5)
        
        hoje_extenso = self._data_por_extenso()
        
        self.title = QLabel("Olá,")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        
        self.subtitle = QLabel(f"Bem-vindo(a) de volta. Aqui está o resumo para hoje, {hoje_extenso}.")
        self.subtitle.setStyleSheet("font-size: 14px; color: #64748b;")
        
        welcome_vbox.addWidget(self.title)
        welcome_vbox.addWidget(self.subtitle)
        header_layout.addLayout(welcome_vbox)
        
        btn_novo_paciente = QPushButton("➕ Novo Paciente")
        btn_novo_paciente.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 10px 18px; font-weight: bold; border-radius: 6px; font-size: 13px; border: none; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        if self.on_novo_paciente_click:
            btn_novo_paciente.clicked.connect(self.on_novo_paciente_click)
        header_layout.addWidget(btn_novo_paciente, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addLayout(header_layout)
        
        # --- 2. CARDS DE INDICADORES ---
        metricas_layout = QHBoxLayout()
        metricas_layout.setSpacing(16)
        
        self.card_pacientes = CardMetrica("Total de Pacientes", "0", "👤", "#e0f2fe", "#0369a1")
        self.card_consultas = CardMetrica("Consultas Hoje", "0", "📅", "#fef3c7", "#b45309")
        self.card_retornos = CardMetrica("Retornos Pendentes", "0", "↩", "#fce7f3", "#be185d")
        
        metricas_layout.addWidget(self.card_pacientes)
        metricas_layout.addWidget(self.card_consultas)
        metricas_layout.addWidget(self.card_retornos)
        metricas_layout.addStretch()
        main_layout.addLayout(metricas_layout)
        
        # --- 3. SEÇÃO INFERIOR: SELETOR DE PASTAS ---
        pastas_section = QVBoxLayout()
        pastas_section.setSpacing(10)
        
        pastas_header = QHBoxLayout()
        lbl_pastas_titulo = QLabel("📁 Pastas Clínicas / Especialidades")
        lbl_pastas_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        
        btn_add_pasta = QPushButton("✨ Criar Nova Pasta")
        btn_add_pasta.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #0f172a; padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: 500; font-size: 12px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        btn_add_pasta.clicked.connect(self.acao_criar_nova_pasta)
        
        pastas_header.addWidget(lbl_pastas_titulo)
        pastas_header.addWidget(btn_add_pasta, alignment=Qt.AlignmentFlag.AlignRight)
        pastas_section.addLayout(pastas_header)
        
        self.pastas_grid_layout = QHBoxLayout()
        self.pastas_grid_layout.setSpacing(12)
        self.pastas_grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        pastas_section.addLayout(self.pastas_grid_layout)
        main_layout.addLayout(pastas_section)
        
        # --- 4. SEÇÃO DO PAINEL DE TAREFAS ---
        split_tables_layout = QHBoxLayout()
        split_tables_layout.setSpacing(20)
        
        # Coluna Agenda do Dia
        agenda_vbox = QVBoxLayout()
        agenda_vbox.setSpacing(8)
        lbl_agenda_tit = QLabel("📋 Próximas Consultas (Hoje)")
        lbl_agenda_tit.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155;")
        agenda_vbox.addWidget(lbl_agenda_tit)
        
        self.table_agenda_resumo = QTableWidget()
        self.table_agenda_resumo.setColumnCount(3)
        self.table_agenda_resumo.setHorizontalHeaderLabels(["Horário", "Paciente", "Status"])
        self.table_agenda_resumo.verticalHeader().setVisible(False)
        self.table_agenda_resumo.setShowGrid(False)
        self.table_agenda_resumo.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_agenda_resumo.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_agenda_resumo.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_agenda_resumo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_agenda_resumo.setMouseTracking(True)
        self.table_agenda_resumo.viewport().setMouseTracking(True)
        self.table_agenda_resumo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.table_agenda_resumo.setFixedHeight(210)
        self.table_agenda_resumo.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; color: #334155; }
            QTableWidget::item { border-bottom: 1px solid #f1f5f9; padding: 6px; }
            QTableWidget::item:hover { background-color: #eff6ff; color: #0369a1; }
            QHeaderView::section { background-color: #f8fafc; font-weight: bold; color: #64748b; border: none; padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-align: left; }
        """)
        h_agenda = self.table_agenda_resumo.horizontalHeader()
        h_agenda.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h_agenda.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h_agenda.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_agenda_resumo.cellDoubleClicked.connect(self.abrir_consulta_da_home)
        agenda_vbox.addWidget(self.table_agenda_resumo)
        split_tables_layout.addLayout(agenda_vbox, stretch=1)

        # Coluna de retornos que precisam de agendamento
        retornos_vbox = QVBoxLayout()
        retornos_vbox.setSpacing(8)
        lbl_retornos_tit = QLabel("↩ Retornos pendentes")
        lbl_retornos_tit.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155;")
        retornos_vbox.addWidget(lbl_retornos_tit)
        self.table_retornos = QTableWidget()
        self.table_retornos.setColumnCount(3)
        self.table_retornos.setHorizontalHeaderLabels(["Paciente", "Previsto", ""])
        self.table_retornos.verticalHeader().setVisible(False)
        self.table_retornos.setShowGrid(False)
        self.table_retornos.setFixedHeight(210)
        self.table_retornos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_retornos.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 12px; color: #334155; }
            QTableWidget::item { border-bottom: 1px solid #f1f5f9; padding: 6px; }
            QHeaderView::section { background-color: #f8fafc; font-weight: bold; color: #64748b; border: none; padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 11px; }
        """)
        h_retornos = self.table_retornos.horizontalHeader()
        h_retornos.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_retornos.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h_retornos.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        retornos_vbox.addWidget(self.table_retornos)
        split_tables_layout.addLayout(retornos_vbox, stretch=1)
        
        # Coluna Pacientes Recentes
        recentes_vbox = QVBoxLayout()
        recentes_vbox.setSpacing(8)
        lbl_rec_tit = QLabel("⏱️ Pacientes Adicionados Recentemente")
        lbl_rec_tit.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155;")
        recentes_vbox.addWidget(lbl_rec_tit)
        
        self.table_recentes = QTableWidget()
        self.table_recentes.setColumnCount(2)
        self.table_recentes.setHorizontalHeaderLabels(["Nome do Paciente", "Pasta / Grupo"])
        self.table_recentes.verticalHeader().setVisible(False)
        self.table_recentes.setShowGrid(False)
        self.table_recentes.setFixedHeight(210)
        self.table_recentes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_recentes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_recentes.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_recentes.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; color: #334155; }
            QTableWidget::item { border-bottom: 1px solid #f1f5f9; padding: 6px; }
            QTableWidget::item:selected { background-color: #e0f2fe; color: #0f172a; }
            QHeaderView::section { background-color: #f8fafc; font-weight: bold; color: #64748b; border: none; padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-align: left; }
        """)
        h_rec = self.table_recentes.horizontalHeader()
        h_rec.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_rec.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_recentes.cellDoubleClicked.connect(self.abrir_paciente_recente)
        recentes_vbox.addWidget(self.table_recentes)
        split_tables_layout.addLayout(recentes_vbox, stretch=1)
        
        main_layout.addLayout(split_tables_layout)
        main_layout.addStretch()
        
        self.atualizar_saudacao_dinamica()

    def atualizar_saudacao_dinamica(self):
        nome_medico = self.db.obter_nome_profissional()
        hoje_extenso = self._data_por_extenso()
        
        if nome_medico:
            self.title.setText(f"Olá, {nome_medico}")
            self.subtitle.setText(f"Aqui está o resumo do seu consultório para hoje, {hoje_extenso}.")
        else:
            self.title.setText("Olá,")
            self.subtitle.setText(f"Bem-vindo(a) de volta. Aqui está o resumo para hoje, {hoje_extenso}.")

    @staticmethod
    def _data_por_extenso():
        """Retorna a data em português, independentemente do idioma do Windows."""
        meses = (
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        )
        hoje = QDate.currentDate()
        return f"{hoje.day()} de {meses[hoje.month() - 1]} de {hoje.year()}"

    def renderizar_lista_pastas(self):
        while self.pastas_grid_layout.count():
            child = self.pastas_grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        lista_pastas = getattr(self.window_principal, 'pastas_sistema', ["Geral"])
        lista_pastas = [normalizar_nome_pasta(p) for p in lista_pastas if normalizar_nome_pasta(p)]
        cores_pastas = getattr(self.window_principal, 'pastas_cores', {})
        pacientes = self._buscar_pacientes_para_home()
        
        for nome_pasta in lista_pastas:
            qtd_pacientes = self._contar_pacientes_na_lista(pacientes, nome_pasta)
            cor_pasta = cores_pastas.get(nome_pasta, "#0284c7")
            
            card = CardPasta(
                nome=nome_pasta,
                quantidade=qtd_pacientes,
                cor=cor_pasta,
                on_clique=self.on_pasta_click,
                on_editar=self.acao_editar_pasta,
                on_excluir=self.acao_excluir_pasta,
                on_mudar_cor=self.acao_mudar_cor_pasta
            )
            self.pastas_grid_layout.addWidget(card)
            
        self.carregar_dados_iniciais(pacientes)

    def _buscar_pacientes_para_home(self):
        """Uma única consulta atende os cards de pastas e a lista de recentes."""
        if not self.db.supabase:
            return []
        try:
            resposta = self.db.supabase.table("pacientes")\
                .select("id, nome, pasta")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .is_("deleted_at", "null")\
                .order("id", desc=True)\
                .execute()
            return resposta.data or []
        except Exception as e:
            print(f"Erro ao carregar pacientes da home: {e}")
            return []

    @staticmethod
    def _contar_pacientes_na_lista(pacientes, nome_pasta):
        nome_limpo = nome_pasta.strip().lower()
        if nome_limpo == "geral":
            return sum(
                1 for paciente in pacientes
                if not (paciente.get("pasta") or "").strip()
                or (paciente.get("pasta") or "").strip().lower() == "geral"
            )
        return sum(
            1 for paciente in pacientes
            if (paciente.get("pasta") or "").strip().lower() == nome_limpo
        )

    def acao_mudar_cor_pasta(self, nome_pasta):
        """Abre o seletor de cores do sistema e salva a nova cor da pasta."""
        cores_pastas = getattr(self.window_principal, 'pastas_cores', {})
        cor_atual = QColor(cores_pastas.get(nome_pasta, "#0284c7"))

        cor_escolhida = QColorDialog.getColor(cor_atual, self, f"Cor da pasta '{nome_pasta}'")
        if cor_escolhida.isValid():
            if hasattr(self.window_principal, 'atualizar_cor_pasta'):
                self.window_principal.atualizar_cor_pasta(nome_pasta, cor_escolhida.name())
            self.renderizar_lista_pastas()

    def contar_pacientes_na_pasta_supabase(self, nome_pasta):
        if not self.db.supabase:
            return 0
        try:
            nome_limpo = nome_pasta.strip()
            query = self.db.supabase.table("pacientes")\
                .select("id", count="exact")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .is_("deleted_at", "null")

            if nome_limpo.lower() == "geral":
                # "Geral" também deve contar pacientes antigos que ficaram com
                # pasta em branco/nula no banco (cadastrados antes do valor
                # padrão "Geral" ser sempre garantido no formulário).
                query = query.or_(f"pasta.ilike.{nome_limpo},pasta.is.null,pasta.eq.")
            else:
                query = query.ilike("pasta", nome_limpo)

            resposta = query.execute()
            return resposta.count if resposta.count is not None else 0
        except Exception as e:
            print(f"Erro ao contar pacientes da pasta: {e}")
            return 0

    def abrir_paciente_recente(self, row, coluna):
        """Duplo-clique numa linha de 'Recentes': abre o prontuário desse paciente na tela de Pacientes."""
        item = self.table_recentes.item(row, 0)
        if not item:
            return
        paciente_id = item.data(Qt.ItemDataRole.UserRole)
        if paciente_id is not None and hasattr(self.window_principal, 'abrir_paciente_especifico'):
            self.window_principal.abrir_paciente_especifico(paciente_id)

    def carregar_dados_iniciais(self, pacientes=None):
        if not self.db.supabase:
            return
        try:
            self.table_recentes.setRowCount(0)
            
            # 1. Total de Pacientes e preenchimento dos Recentes
            if pacientes is None:
                pacientes = self._buscar_pacientes_para_home()

            total_p = len(pacientes)
            self.card_pacientes.set_valor(str(total_p))
            
            # Exibe os últimos 4 adicionados
            ultimos_pacientes = pacientes[:4]
            for row_idx, item in enumerate(ultimos_pacientes):
                self.table_recentes.insertRow(row_idx)
                item_nome = QTableWidgetItem(str(item["nome"]).upper())
                item_nome.setData(Qt.ItemDataRole.UserRole, item.get("id"))
                self.table_recentes.setItem(row_idx, 0, item_nome)
                self.table_recentes.setItem(row_idx, 1, QTableWidgetItem(str(item["pasta"]).upper()))
                
            # 2. Consultas da agenda para Hoje
            self.table_agenda_resumo.setRowCount(0)
            hoje_iso = QDate.currentDate().toString("dd/MM/yyyy")
            
            resposta_agenda = self.db.supabase.table("agenda")\
                .select("horario, paciente, status")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .eq("data", hoje_iso)\
                .execute()
            
            eventos_hoje = []
            if resposta_agenda.data:
                eventos_hoje = sorted(resposta_agenda.data, key=lambda x: x["horario"])
            
            self.card_consultas.set_valor(str(len(eventos_hoje)))
            
            for r_idx, item in enumerate(eventos_hoje):
                self.table_agenda_resumo.insertRow(r_idx)
                item_hora = QTableWidgetItem(str(item["horario"]))
                item_hora.setData(Qt.ItemDataRole.UserRole, {"data": hoje_iso, "horario": str(item["horario"])})
                self.table_agenda_resumo.setItem(r_idx, 0, item_hora)
                self.table_agenda_resumo.setItem(r_idx, 1, QTableWidgetItem(str(item["paciente"]).upper()))
                self.table_agenda_resumo.setItem(r_idx, 2, QTableWidgetItem(str(item["status"] if item["status"] else "Agendado")))

            # 3. Retornos pendentes — dados clínicos ficam no prontuário, não no painel.
            self.table_retornos.setRowCount(0)
            retornos = self.db.listar_retornos_pendentes() if hasattr(self.db, "listar_retornos_pendentes") else []
            self.card_retornos.set_valor(str(len(retornos)))
            hoje = QDate.currentDate().toString("yyyy-MM-dd")
            for linha, retorno in enumerate(retornos[:6]):
                self.table_retornos.insertRow(linha)
                self.table_retornos.setItem(linha, 0, QTableWidgetItem(str(retorno.get("paciente_nome", "Paciente")).upper()))
                data_prevista = str(retorno.get("data_prevista") or "")
                data_formatada = QDate.fromString(data_prevista, "yyyy-MM-dd")
                texto_data = data_formatada.toString("dd/MM/yyyy") if data_formatada.isValid() else data_prevista
                if data_prevista and data_prevista < hoje:
                    texto_data += " · Atrasado"
                item_data = QTableWidgetItem(texto_data)
                if data_prevista and data_prevista < hoje:
                    item_data.setForeground(QColor("#dc2626"))
                self.table_retornos.setItem(linha, 1, item_data)
                btn_agendar = QPushButton("Agendar")
                btn_agendar.setStyleSheet("QPushButton { color: #0369a1; background: #eff6ff; border: 1px solid #93c5fd; border-radius: 5px; padding: 4px 7px; font-weight: bold; font-size: 11px; } QPushButton:hover { background: #dbeafe; }")
                btn_agendar.clicked.connect(lambda checked=False, r=retorno: self.agendar_retorno(r))
                self.table_retornos.setCellWidget(linha, 2, btn_agendar)
        except Exception as e:
            print(f"Erro ao inicializar tabelas reais da home: {e}")

    def abrir_consulta_da_home(self, linha, _coluna):
        item = self.table_agenda_resumo.item(linha, 0)
        consulta = item.data(Qt.ItemDataRole.UserRole) if item else None
        if consulta and self.on_consulta_click:
            self.on_consulta_click(consulta)

    def agendar_retorno(self, retorno):
        if self.on_agendar_retorno_click:
            self.on_agendar_retorno_click(retorno)

    def mostrar_alerta_seguro(self, tipo, titulo, texto):
        """Exibe um QMessageBox com cores explícitas, evitando herdar o tema
        escuro do sistema operacional (o que deixava texto ilegível)."""
        msg = QMessageBox(self)
        msg.setWindowTitle(titulo)
        msg.setText(texto)
        if tipo == "warning":
            msg.setIcon(QMessageBox.Icon.Warning)
        elif tipo == "error":
            msg.setIcon(QMessageBox.Icon.Critical)
        else:
            msg.setIcon(QMessageBox.Icon.Information)

        msg.setStyleSheet("""
            QMessageBox { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: normal; }
            QPushButton { background-color: #0284c7; color: white; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        msg.exec()

    def acao_criar_nova_pasta(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Nova Pasta")
        dialog.setLabelText("Digite o nome da especialidade ou grupo:")
        dialog.setStyleSheet("""
            QInputDialog { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: 500; }
            QLineEdit { color: #0f172a; background-color: #ffffff; border: 1px solid #cbd5e1; padding: 6px; border-radius: 6px; font-size: 14px; min-width: 250px; }
            QPushButton { color: #334155; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 14px; border-radius: 6px; font-weight: 500; font-size: 13px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        ok = dialog.exec()
        nome_nova = dialog.textValue()
        
        if ok and nome_nova.strip():
            nome_limpo = normalizar_nome_pasta(nome_nova)
            if not nome_limpo:
                self.mostrar_alerta_seguro("warning", "Nome inválido", "Digite um nome de pasta válido.")
                return
            lista = list(getattr(self.window_principal, 'pastas_sistema', ["Geral"]))
            
            if nome_limpo in lista:
                self.mostrar_alerta_seguro("warning", "Aviso", "Esta pasta já existe no sistema.")
                return
                
            lista.append(nome_limpo)
            self.window_principal.sincronizar_pastas_sistema(lista)
            self.renderizar_lista_pastas()

    def acao_editar_pasta(self, nome_antigo):
        if nome_antigo.lower() == "geral":
            self.mostrar_alerta_seguro("warning", "Aviso", "A pasta padrão 'Geral' não pode ser renomeada.")
            return

        dialog = QInputDialog(self)
        dialog.setWindowTitle("Editar Pasta")
        dialog.setLabelText(f"Alterar o nome da pasta '{nome_antigo}' para:")
        dialog.setTextValue(nome_antigo)
        dialog.setStyleSheet("""
            QInputDialog { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: 500; }
            QLineEdit { color: #0f172a; background-color: #ffffff; border: 1px solid #cbd5e1; padding: 6px; border-radius: 6px; font-size: 14px; min-width: 250px; }
            QPushButton { color: #334155; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 14px; border-radius: 6px; font-weight: 500; font-size: 13px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        ok = dialog.exec()
        nome_novo = dialog.textValue()
        
        if ok and nome_novo.strip():
            nome_limpo = normalizar_nome_pasta(nome_novo)
            if not nome_limpo:
                self.mostrar_alerta_seguro("warning", "Nome inválido", "Digite um nome de pasta válido.")
                return
            lista = list(getattr(self.window_principal, 'pastas_sistema', ["Geral"]))
            
            if nome_limpo in lista and nome_limpo != nome_antigo:
                self.mostrar_alerta_seguro("warning", "Aviso", "Já existe outra pasta com esse nome.")
                return
                
            if nome_antigo in lista:
                idx = lista.index(nome_antigo)
                lista[idx] = nome_limpo
            
            self.atualizar_pasta_dos_pacientes_supabase(nome_antigo, nome_limpo)
            self.window_principal.sincronizar_pastas_sistema(lista)
            self.renderizar_lista_pastas()

    def acao_excluir_pasta(self, nome_pasta):
        if nome_pasta.lower() == "geral":
            self.mostrar_alerta_seguro("warning", "Aviso", "A pasta padrão 'Geral' não pode ser apagada.")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar Exclusão")
        msg.setText(f"Tem certeza que deseja apagar a pasta '{nome_pasta}'?\nOs pacientes vinculados voltarão para o grupo 'Geral'.")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: normal; }
            QPushButton { background-color: #0284c7; color: white; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        resposta = msg.exec()
        
        if resposta == QMessageBox.StandardButton.Yes:
            lista = list(getattr(self.window_principal, 'pastas_sistema', ["Geral"]))
            if nome_pasta in lista:
                lista.remove(nome_pasta)
                
                self.atualizar_pasta_dos_pacientes_supabase(nome_pasta, "Geral")
                self.window_principal.sincronizar_pastas_sistema(lista)
                self.renderizar_lista_pastas()

    def atualizar_pasta_dos_pacientes_supabase(self, de_pasta, para_pasta):
        if not self.db.supabase:
            return
        try:
            self.db.supabase.table("pacientes")\
                .update({"pasta": para_pasta})\
                .eq("consultorio_id", self.db.consultorio_id)\
                .eq("pasta", de_pasta)\
                .execute()
                
            if hasattr(self.window_principal, 'screen_pacientes'):
                if hasattr(self.window_principal.screen_pacientes, 'carregar_pacientes_tabela'):
                    self.window_principal.screen_pacientes.carregar_pacientes_tabela()
        except Exception as e:
            print(f"Erro ao atualizar dados: {e}")

class CardMetrica(QFrame):
    def __init__(self, titulo, valor, icone, bg_cor, texto_cor):
        super().__init__()
        self.setFixedSize(250, 96)
        self.setStyleSheet("QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500; border: none; background: transparent;")
        self.lbl_valor = QLabel(valor)
        self.lbl_valor.setStyleSheet("color: #0f172a; font-size: 24px; font-weight: bold; border: none; background: transparent;")
        vbox.addWidget(self.lbl_titulo)
        vbox.addWidget(self.lbl_valor)
        layout.addLayout(vbox)
        
        self.lbl_icone = QLabel(icone)
        self.lbl_icone.setFixedSize(40, 40)
        self.lbl_icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icone.setStyleSheet(f"QLabel {{ background-color: {bg_cor}; color: {texto_cor}; font-size: 18px; border-radius: 6px; border: none; }}")
        layout.addWidget(self.lbl_icone)
        
    def set_valor(self, novo_valor):
        self.lbl_valor.setText(novo_valor)

class CardPasta(QFrame):
    def __init__(self, nome, quantidade, cor="#0284c7", on_clique=None, on_editar=None, on_excluir=None, on_mudar_cor=None):
        super().__init__()
        self.nome_pasta = nome
        self.on_clique_callback = on_clique
        
        self.setFixedSize(175, 125)
        self.setStyleSheet(f"""
            QFrame {{ background-color: white; border: 1px solid #e2e8f0; border-top: 4px solid {cor}; border-radius: 8px; }}
            QFrame:hover {{ border: 1px solid #0284c7; border-top: 4px solid {cor}; background-color: #fafafa; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        top_btn_layout = QHBoxLayout()
        top_btn_layout.setSpacing(2)
        
        btn_cor = QPushButton("📁")
        btn_cor.setFixedSize(24, 24)
        btn_cor.setToolTip("Clique para mudar a cor desta pasta")
        btn_cor.setStyleSheet(f"font-size: 15px; border: none; border-radius: 4px; background-color: {cor}22;")
        btn_cor.clicked.connect(lambda: on_mudar_cor(self.nome_pasta) if on_mudar_cor else None)
        top_btn_layout.addWidget(btn_cor)
        top_btn_layout.addStretch()
        
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(18, 18)
        btn_edit.setStyleSheet("font-size: 10px; background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 3px; color: #0f172a;")
        btn_edit.clicked.connect(lambda: on_editar(self.nome_pasta) if on_editar else None)
        
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(18, 18)
        btn_del.setStyleSheet("font-size: 10px; background-color: #fee2e2; border: 1px solid #fca5a5; border-radius: 3px; color: #0f172a;")
        btn_del.clicked.connect(lambda: on_excluir(self.nome_pasta) if on_excluir else None)
        
        top_btn_layout.addWidget(btn_edit)
        top_btn_layout.addWidget(btn_del)
        layout.addLayout(top_btn_layout)
        
        self.lbl_nome = QLabel(nome)
        self.lbl_nome.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b; margin-top: 5px; border: none; background: transparent;")
        layout.addWidget(self.lbl_nome)
        
        self.lbl_qtd = QLabel(f"{quantidade} pacientes")
        self.lbl_qtd.setStyleSheet("font-size: 12px; color: #64748b; border: none; background: transparent;")
        layout.addWidget(self.lbl_qtd)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_clique_callback:
            self.on_clique_callback(self.nome_pasta)
        super().mousePressEvent(event)
