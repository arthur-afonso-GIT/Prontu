from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QComboBox, QHeaderView, QFrame, QTimeEdit, QMessageBox,
                               QCalendarWidget)
from PySide6.QtCore import Qt, QDate, QTime, QPoint
from PySide6.QtGui import QFont

class AgendaScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.data_visualizada = QDate.currentDate()
        self.lista_pacientes_disponiveis = []
        
        # Layout Principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        
        # --- COLUNA DA ESQUERDA: NAVEGAÇÃO DE DATA E GRADE DE HORÁRIOS ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Seletor de Data (Estilo Print 2)
        self.date_selector_container = QFrame()
        self.date_selector_container.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }
        """)
        selector_layout = QHBoxLayout(self.date_selector_container)
        selector_layout.setContentsMargins(15, 8, 15, 8)
        
        # Botão Dia Anterior
        self.btn_prev_day = QPushButton("‹")
        self.btn_prev_day.setStyleSheet("""
            QPushButton { 
                background-color: #f1f5f9; color: #0f172a; font-size: 20px; font-weight: bold;
                border: 1px solid #cbd5e1; border-radius: 4px; width: 32px; height: 32px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_prev_day.clicked.connect(self.navegar_dia_anterior)
        
        # Botão Central da Data (Substituindo a antiga QLabel por um QPushButton invisível/estilizado)
        self.btn_data_central = QPushButton("")
        self.btn_data_central.setStyleSheet("""
            QPushButton {
                color: #0f172a; font-size: 16px; font-weight: bold;
                border: none; background: transparent; padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #f1f5f9; color: #0284c7; }
        """)
        self.btn_data_central.clicked.connect(self.abrir_mini_calendario)
        
        # Botão Próximo Dia
        self.btn_next_day = QPushButton("›")
        self.btn_next_day.setStyleSheet("""
            QPushButton { 
                background-color: #f1f5f9; color: #0f172a; font-size: 20px; font-weight: bold;
                border: 1px solid #cbd5e1; border-radius: 4px; width: 32px; height: 32px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_next_day.clicked.connect(self.navegar_proximo_dia)
        
        selector_layout.addWidget(self.btn_prev_day)
        selector_layout.addStretch()
        selector_layout.addWidget(self.btn_data_central)
        selector_layout.addStretch()
        selector_layout.addWidget(self.btn_next_day)
        left_layout.addWidget(self.date_selector_container)
        
        # Tabela / Grade de Horários
        self.table_horarios = QTableWidget()
        self.table_horarios.setColumnCount(4)
        self.table_horarios.setHorizontalHeaderLabels(["Horário", "Paciente", "Procedimento / Motivo", "Status"])
        
        header = self.table_horarios.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table_horarios.verticalHeader().setVisible(False)
        self.table_horarios.setShowGrid(False)
        self.table_horarios.verticalHeader().setDefaultSectionSize(45)
        self.table_horarios.setStyleSheet("""
            QTableWidget { 
                background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; color: #334155;
            }
            QTableWidget::item { padding-left: 10px; padding-right: 10px; border-bottom: 1px solid #f1f5f9; }
            QHeaderView::section { 
                background-color: #f8fafc; padding: 10px; border: none; border-bottom: 2px solid #e2e8f0;
                font-weight: bold; color: #475569; font-size: 13px; text-align: left;
            }
        """)
        left_layout.addWidget(self.table_horarios)
        
        # --- COLUNA DA DIREITA: FORMULÁRIO ---
        self.form_container = QFrame()
        self.form_container.setFixedWidth(360)
        self.form_container.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }
            QLabel { color: #334155; font-weight: 500; font-size: 12px; border: none; }
        """)
        
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)
        
        self.form_title = QLabel("Novo Agendamento")
        self.form_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        form_layout.addWidget(self.form_title)
        
        form_layout.addWidget(QLabel("Pesquisar Paciente Cadastrado:"))
        self.input_paciente = QComboBox()
        self.input_paciente.setEditable(True)
        self.input_paciente.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.input_paciente.setPlaceholderText("Selecione ou digite para buscar...")
        form_layout.addWidget(self.input_paciente)
        
        tempo_layout = QHBoxLayout()
        vbox_hora = QVBoxLayout()
        vbox_hora.addWidget(QLabel("Horário de Início:"))
        self.input_hora = QTimeEdit()
        self.input_hora.setTime(QTime(8, 0))
        vbox_hora.addWidget(self.input_hora)
        
        vbox_duracao = QVBoxLayout()
        vbox_duracao.addWidget(QLabel("Duração Estimada:"))
        self.input_duracao = QComboBox()
        self.input_duracao.addItems(["15 minutos", "30 minutos", "45 minutos", "1 hora", "1h 30min"])
        self.input_duracao.setCurrentIndex(1)
        vbox_duracao.addWidget(self.input_duracao)
        
        tempo_layout.addLayout(vbox_hora)
        tempo_layout.addLayout(vbox_duracao)
        form_layout.addLayout(tempo_layout)
        
        form_layout.addWidget(QLabel("Procedimento / Tipo de Consulta:"))
        self.input_procedimento = QComboBox()
        self.input_procedimento.addItems(["Primeira Consulta / Avaliação", "Retorno", "Procedimento Clínico", "Telemedicina"])
        form_layout.addWidget(self.input_procedimento)
        
        form_layout.addWidget(QLabel("Status Inicial:"))
        self.input_status = QComboBox()
        self.input_status.addItems(["🕒 Agendado", "✅ Confirmado", "🏥 Em Atendimento", "❌ Faltou"])
        form_layout.addWidget(self.input_status)
        
        form_layout.addWidget(QLabel("Observações (Opcional):"))
        self.input_obs = QLineEdit()
        self.input_obs.setPlaceholderText("Ex: Paciente solicitou preferência em encaixes.")
        form_layout.addWidget(self.input_obs)
        
        self.apply_form_styles()
        form_layout.addStretch()
        
        self.btn_salvar = QPushButton("Confirmar Agendamento")
        self.btn_salvar.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px;}
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_salvar.clicked.connect(self.salvar_agendamento_click)
        form_layout.addWidget(self.btn_salvar)
        
        main_layout.addWidget(left_container, stretch=3)
        main_layout.addWidget(self.form_container, stretch=1)
        
        self.atualizar_visualizacao_data()
        self.gerar_grade_horarios_vazia()

    def atualizar_lista_sugestoes(self, nomes_pacientes):
        self.lista_pacientes_disponiveis = sorted(list(set(nomes_pacientes)))
        self.input_paciente.blockSignals(True)
        self.input_paciente.clear()
        self.input_paciente.addItems(self.lista_pacientes_disponiveis)
        
        from PySide6.QtWidgets import QCompleter
        from PySide6.QtCore import QStringListModel
        model = QStringListModel(self.lista_pacientes_disponiveis)
        completer = QCompleter(model, self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        completer.popup().setStyleSheet("""
            QAbstractItemView { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; selection-background-color: #0284c7; selection-color: white; font-size: 13px; padding: 4px; }
        """)
        self.input_paciente.setCompleter(completer)
        self.input_paciente.setCurrentIndex(-1)
        self.input_paciente.setPlaceholderText("Selecione ou digite para buscar...")
        self.input_paciente.blockSignals(False)

    # --- LÓGICA DO MINI CALENDÁRIO FLUTUANTE (POPUP) ---
    # --- LÓGICA DO MINI CALENDÁRIO FLUTUANTE (DESIGN PREMIUM) ---
    def abrir_mini_calendario(self):
        """Abre um calendário flutuante elegantemente estilizado abaixo do botão de data."""
        self.popup_calendario = QCalendarWidget()
        self.popup_calendario.setWindowFlags(Qt.WindowType.Popup)  # Fecha sozinho ao clicar fora
        self.popup_calendario.setGridVisible(False)                # Remove aquelas linhas feias de grade
        self.popup_calendario.setSelectedDate(self.data_visualizada)
        
        # Redimensiona ligeiramente para ficar harmônico
        self.popup_calendario.setFixedSize(280, 250)
        
        # =========================================================================
        # ESTILIZAÇÃO PREMIUM (CSS COMPLETO PARA CADA PEDAÇO DO CALENDÁRIO)
        # =========================================================================
        self.popup_calendario.setStyleSheet("""
            /* Janela Principal do Calendário */
            QCalendarWidget {
                background-color: white;
            }
            
            /* Grade interna dos dias */
            QCalendarWidget QTableView {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: white;
                selection-background-color: #0284c7; /* Azul Prontu */
                selection-color: white;
            }
            
            /* Barra Superior de Navegação (Mês e Ano) */
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #0f172a; /* Slate escuro igual à Sidebar */
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 4px;
            }
            
            /* Botões de passar o mês (Mês anterior e Próximo mês) */
            QCalendarWidget QToolButton {
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                background: transparent;
                padding: 4px 8px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #1e293b;
            }
            
            /* Texto central do Mês e Ano */
            QCalendarWidget QToolButton#qt_calendar_monthbutton, 
            QCalendarWidget QToolButton#qt_calendar_yearbutton {
                color: white;
                font-size: 13px;
                font-weight: bold;
            }
            
            /* Menu suspenso flutuante de escolha rápida de mês/ano caso clique neles */
            QCalendarWidget QMenu {
                background-color: white;
                color: #0f172a;
                border: 1px solid #cbd5e1;
            }
            QCalendarWidget QMenu::item:selected {
                background-color: #0284c7;
                color: white;
            }
            
            /* Cabeçalho dos dias da semana (Dom, Seg, Ter...) */
            QCalendarWidget QWidget {
                alternate-background-color: transparent;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #f8fafc;
                color: #64748b;
                padding: 4px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            
            /* Dias normais do mês */
            QCalendarWidget QAbstractItemView:enabled {
                color: #334155;
                font-size: 12px;
            }
            
            /* Dias de outros meses (antecessor/sucessor na mesma grade) */
            QCalendarWidget QAbstractItemView:disabled {
                color: #cbd5e1;
            }
        """)
        # =========================================================================
        
        # Conecta o clique no dia para fechar e mudar a data
        self.popup_calendario.clicked.connect(self.ao_escolher_data_popup)
        
        # Centraliza e posiciona perfeitamente abaixo do botão central de data
        posicao_botao = self.btn_data_central.mapToGlobal(QPoint(0, self.btn_data_central.height() + 5))
        # Ajusta um pouquinho para a esquerda para alinhar pelo meio do botão
        posicao_botao.setX(posicao_botao.x() - (280 - self.btn_data_central.width()) // 2)
        
        self.popup_calendario.move(posicao_botao)
        self.popup_calendario.show()

    def ao_escolher_data_popup(self, data):
        self.data_visualizada = data
        self.atualizar_visualizacao_data()
        self.popup_calendario.close() # Fecha a caixinha automaticamente

    def gerar_grade_horarios_vazia(self):
        self.table_horarios.setRowCount(0)
        horarios = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00"]
        self.table_horarios.setRowCount(len(horarios))
        for index, hora in enumerate(horarios):
            item_hora = QTableWidgetItem(hora)
            fonte_hora = QFont(); fonte_hora.setBold(True); item_hora.setFont(fonte_hora)
            item_hora.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_horarios.setItem(index, 0, item_hora)
            self.table_horarios.setItem(index, 1, QTableWidgetItem("— Horário Livre —"))
            self.table_horarios.setItem(index, 2, QTableWidgetItem("-"))
            self.table_horarios.setItem(index, 3, QTableWidgetItem("Disponível"))

    def navegar_dia_anterior(self):
        self.data_visualizada = self.data_visualizada.addDays(-1)
        self.atualizar_visualizacao_data()

    def navegar_proximo_dia(self):
        self.data_visualizada = self.data_visualizada.addDays(1)
        self.atualizar_visualizacao_data()

    def atualizar_visualizacao_data(self):
        # Altera o texto do botão central exibindo a data formatada
        self.btn_data_central.setText(self.data_visualizada.toString("dd 'de' MMMM 'de' yyyy"))

    def salvar_agendamento_click(self):
        paciente = self.input_paciente.currentText().strip()
        if not paciente:
            QMessageBox.warning(self, "Campo Obrigatório", "Por favor, selecione ou digite o nome de um paciente!")
            return
        
        hora_desejada = self.input_hora.time().toString("hh:mm")
        conflito_detectado = False
        row_destino = -1
        
        for row in range(self.table_horarios.rowCount()):
            if self.table_horarios.item(row, 0).text() == hora_desejada:
                paciente_atual = self.table_horarios.item(row, 1).text()
                if paciente_atual != "— Horário Livre —" and paciente_atual != "-":
                    conflito_detectado = True
                row_destino = row
                break

        if conflito_detectado:
            resposta = QMessageBox.question(
                self, "⚠️ Conflito de Horário", 
                f"O horário das {hora_desejada} já possui um agendamento confirmado.\n\nDeseja realmente substituir ou sobrepor este horário?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if resposta == QMessageBox.StandardButton.No:
                return
        
        if row_destino != -1:
            self.table_horarios.setItem(row_destino, 1, QTableWidgetItem(paciente.upper()))
            self.table_horarios.setItem(row_destino, 2, QTableWidgetItem(self.input_procedimento.currentText()))
            self.table_horarios.setItem(row_destino, 3, QTableWidgetItem(self.input_status.currentText()))
        else:
            row_idx = self.table_horarios.rowCount()
            self.table_horarios.insertRow(row_idx)
            item_hora = QTableWidgetItem(hora_desejada)
            font = QFont(); font.setBold(True); item_hora.setFont(font)
            item_hora.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_horarios.setItem(row_idx, 0, item_hora)
            self.table_horarios.setItem(row_idx, 1, QTableWidgetItem(paciente.upper()))
            self.table_horarios.setItem(row_idx, 2, QTableWidgetItem(self.input_procedimento.currentText()))
            self.table_horarios.setItem(row_idx, 3, QTableWidgetItem(self.input_status.currentText()))
            
        self.table_horarios.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.input_paciente.setCurrentIndex(-1)
        self.input_paciente.setLineEdit(QLineEdit())
        self.input_paciente.setPlaceholderText("Selecione ou digite para buscar...")
        self.input_obs.clear()

    def apply_form_styles(self):
        widgets = [self.input_hora, self.input_obs]
        for w in widgets:
            w.setStyleSheet("""
                QLineEdit, QTimeEdit { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc; color: #0f172a; font-size: 13px; }
                QLineEdit:focus, QTimeEdit:focus { border: 1px solid #0284c7; background-color: white; }
            """)
        combos = [self.input_paciente, self.input_duracao, self.input_procedimento, self.input_status]
        for c in combos:
            c.setStyleSheet("""
                QComboBox { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: white; color: #0f172a; font-size: 13px; }
                QComboBox:focus { border: 1px solid #0284c7; }
                QComboBox QAbstractItemView { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; selection-background-color: #0284c7; selection-color: white; padding: 4px; }
                QComboBox QLineEdit { border: none; padding: 0; background-color: transparent; color: #0f172a; }
            """)