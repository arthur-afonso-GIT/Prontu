from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QFrame, 
                               QMessageBox, QCalendarWidget, QScrollArea,
                               QHeaderView, QTableView)
from PySide6.QtCore import Qt, QDate, QTime, QDateTime, QPoint

class AgendaScreen(QWidget):
    # Grade fixa de horários (07:00 às 19:00, blocos de 30 min).
    # Único ponto de verdade: usada tanto para renderizar a timeline quanto
    # para o seletor de horário do formulário, então é impossível agendar
    # um horário "fora da grade" (ex: 08:15).
    HORARIOS_GRADE = [
        "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
        "17:00", "17:30", "18:00", "18:30", "19:00"
    ]

    def __init__(self):
        super().__init__()
        
        self.data_visualizada = QDate.currentDate()
        self.lista_pacientes_disponiveis = []
        
        # Banco de dados em memória local (Dicionário estruturado por Data -> Hora)
        # Agora suporta o tipo: "principal" (onde fica o card) ou "continua" (bloqueado pela duração)
        self.db_agendamentos = {}
        
        # Layout Principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        
        # --- COLUNA DA ESQUERDA: NAVEGAÇÃO DE DATA E GRADE DE HORÁRIOS ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Seletor de Data Superior
        self.date_selector_container = QFrame()
        self.date_selector_container.setStyleSheet("QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        selector_layout = QHBoxLayout(self.date_selector_container)
        selector_layout.setContentsMargins(15, 8, 15, 8)
        
        self.btn_prev_day = QPushButton("‹")
        self.btn_prev_day.setStyleSheet("""
            QPushButton { 
                background-color: #f1f5f9; color: #0f172a; font-size: 20px; font-weight: bold;
                border: 1px solid #cbd5e1; border-radius: 4px; width: 32px; height: 32px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_prev_day.clicked.connect(self.navegar_dia_anterior)
        
        self.btn_data_central = QPushButton("")
        self.btn_data_central.setStyleSheet("""
            QPushButton {
                color: #0f172a; font-size: 16px; font-weight: bold;
                border: none; background: transparent; padding: 5px 15px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #f1f5f9; color: #0284c7; }
        """)
        self.btn_data_central.clicked.connect(self.abrir_mini_calendario)
        
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
        
        # --- ÁREA SCROLLÁVEL DO CALENDÁRIO ---
        self.scroll_agenda = QScrollArea()
        self.scroll_agenda.setWidgetResizable(True)
        self.scroll_agenda.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.container_timeline = QWidget()
        self.container_timeline.setStyleSheet("background-color: transparent;")
        self.layout_timeline = QVBoxLayout(self.container_timeline)
        self.layout_timeline.setContentsMargins(0, 0, 5, 0)
        self.layout_timeline.setSpacing(10)
        
        self.scroll_agenda.setWidget(self.container_timeline)
        left_layout.addWidget(self.scroll_agenda)
        
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
        self.input_hora = QComboBox()
        self.input_hora.addItems(self.HORARIOS_GRADE)
        self.input_hora.setCurrentText("08:00")
        vbox_hora.addWidget(self.input_hora)
        
        vbox_duracao = QVBoxLayout()
        vbox_duracao.addWidget(QLabel("Duração Estimada:"))
        self.input_duracao = QComboBox()
        self.input_duracao.addItems(["15 minutos", "30 minutos", "45 minutos", "1 hora", "1h 30min", "2 horas"])
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
        self.renderizar_timeline_calendario()

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
        completer.popup().setStyleSheet("QAbstractItemView { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; selection-background-color: #0284c7; selection-color: white; font-size: 13px; padding: 4px; }")
        self.input_paciente.setCompleter(completer)
        self.input_paciente.setCurrentIndex(-1)
        self.input_paciente.blockSignals(False)

    def abrir_mini_calendario(self):
        self.popup_calendario = QCalendarWidget()
        self.popup_calendario.setWindowFlags(Qt.WindowType.Popup)
        self.popup_calendario.setSelectedDate(self.data_visualizada)
        self.popup_calendario.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.popup_calendario.setGridVisible(False)
        self.popup_calendario.setFixedSize(300, 260)
        self.popup_calendario.setStyleSheet("""
            QCalendarWidget { background-color: white; border: 1px solid #cbd5e1; border-radius: 8px; }
            QCalendarWidget QTableView { background-color: white; selection-background-color: #0284c7; selection-color: white; outline: none; }
            QCalendarWidget QAbstractItemView:enabled { color: #0f172a; background-color: white; selection-background-color: #0284c7; selection-color: white; }
            QCalendarWidget QAbstractItemView:disabled { color: #cbd5e1; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #0f172a; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QCalendarWidget QToolButton { color: white; font-weight: bold; border: none; background: transparent; }
            QCalendarWidget QToolButton:hover { background-color: #1e293b; border-radius: 4px; }
            QCalendarWidget QSpinBox { background-color: #1e293b; color: white; border: none; selection-background-color: #0284c7; }
            QCalendarWidget QMenu { background-color: white; color: #0f172a; }
        """)

        # CORREÇÃO: o cabeçalho de dias da semana precisa de um modo de
        # redimensionamento explícito (Stretch). Sem isso, em temas nativos
        # (ex: Windows), o cálculo automático de largura das colunas pode
        # colapsar as colunas do meio (seg-sex) para quase 0px, deixando
        # só domingo e sábado visíveis.
        tabela_dias = self.popup_calendario.findChild(QTableView)
        if tabela_dias:
            cabecalho = tabela_dias.horizontalHeader()
            cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            cabecalho.setMinimumSectionSize(30)

        self.popup_calendario.clicked.connect(self.ao_escolher_data_popup)

        # Centraliza o popup embaixo do botão de data, em vez de alinhar
        # pela borda esquerda (que ficava desalinhado com textos longos)
        x_central = self.btn_data_central.mapToGlobal(QPoint(0, 0)).x() + (self.btn_data_central.width() // 2)
        y_abaixo = self.btn_data_central.mapToGlobal(QPoint(0, self.btn_data_central.height() + 6)).y()
        self.popup_calendario.move(x_central - (self.popup_calendario.width() // 2), y_abaixo)
        self.popup_calendario.show()

    def ao_escolher_data_popup(self, data):
        self.data_visualizada = data
        self.atualizar_visualizacao_data()
        self.popup_calendario.close()

    def converter_duracao_minutos(self, texto_duracao):
        """Mapeia as strings legíveis do combo box para inteiros computáveis."""
        if "15" in texto_duracao: return 15
        if "30" in texto_duracao: return 30
        if "45" in texto_duracao: return 45
        if "1 hora" == texto_duracao: return 60
        if "1h 30min" in texto_duracao: return 90
        if "2 horas" in texto_duracao: return 120
        return 30

    # --- NOVO SISTEMA DE TIMELINE COM RESERVA POR COMPRIMENTO ---
    def renderizar_timeline_calendario(self):
        while self.layout_timeline.count():
            item = self.layout_timeline.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
                
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        agendamentos_do_dia = self.db_agendamentos.get(str_data, {})
        
        todos_horarios = sorted(list(set(self.HORARIOS_GRADE + list(agendamentos_do_dia.keys()))))
        
        for hora in todos_horarios:
            bloco_row = QFrame()
            bloco_layout = QHBoxLayout(bloco_row)
            bloco_layout.setContentsMargins(15, 6, 15, 6)
            bloco_layout.setSpacing(15)
            
            lbl_hora = QLabel(hora)
            lbl_hora.setFixedWidth(55)
            lbl_hora.setStyleSheet("font-size: 14px; font-weight: bold; color: #475569;")
            bloco_layout.addWidget(lbl_hora)
            
            if hora in agendamentos_do_dia:
                dados = agendamentos_do_dia[hora]
                
                if dados["tipo_bloco"] == "principal":
                    # CARD DO COMPROMISSO REAL
                    status_txt = dados["status"]
                    cor_borda = "#0284c7"
                    if "Confirmado" in status_txt: cor_borda = "#10b981"
                    elif "Atendimento" in status_txt: cor_borda = "#f59e0b"
                    elif "Faltou" in status_txt: cor_borda = "#ef4444"
                    
                    card_info = QFrame()
                    card_info.setStyleSheet(f"QFrame {{ background-color: white; border: 1px solid #e2e8f0; border-left: 5px solid {cor_borda}; border-radius: 6px; }}")
                    card_layout = QHBoxLayout(card_info)
                    card_layout.setContentsMargins(12, 10, 12, 10)
                    
                    vbox_detalhes = QVBoxLayout()
                    vbox_detalhes.setSpacing(2)
                    
                    lbl_paciente = QLabel(dados["paciente"])
                    lbl_paciente.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a; border: none;")
                    
                    lbl_sub = QLabel(f"📋 {dados['procedimento']} ({dados['duracao_txt']})  •  {status_txt}")
                    lbl_sub.setStyleSheet("font-size: 12px; color: #64748b; border: none;")
                    
                    vbox_detalhes.addWidget(lbl_paciente)
                    vbox_detalhes.addWidget(lbl_sub)
                    card_layout.addLayout(vbox_detalhes)
                    card_layout.addStretch()
                    
                    btn_remover = QPushButton("✕")
                    btn_remover.setFixedSize(24, 24)
                    btn_remover.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; border: none; font-weight: bold; font-size: 14px; } QPushButton:hover { color: #ef4444; }")
                    btn_remover.clicked.connect(lambda checked=False, h=hora: self.remover_agendamento(h))
                    card_layout.addWidget(btn_remover)
                    
                    bloco_layout.addWidget(card_info, stretch=1)
                else:
                    # BLOCO DE CONTINUAÇÃO (RESERVADO PELA DURAÇÃO)
                    card_bloqueado = QFrame()
                    card_bloqueado.setStyleSheet("QFrame { background-color: #f1f5f9; border: 1px dashed #cbd5e1; border-left: 5px solid #cbd5e1; border-radius: 6px; }")
                    cb_layout = QHBoxLayout(card_bloqueado)
                    cb_layout.setContentsMargins(12, 6, 12, 6)
                    
                    lbl_bloqueio = QLabel(f"↳ Ocupado — Continuação do atendimento de {dados['paciente']}")
                    lbl_bloqueio.setStyleSheet("color: #475569; font-size: 12px; font-style: italic; border: none;")
                    cb_layout.addWidget(lbl_bloqueio)
                    
                    bloco_layout.addWidget(card_bloqueado, stretch=1)
            else:
                # HORÁRIO TOTALMENTE VAZIO
                lbl_vazio = QLabel("— Horário Disponível —")
                lbl_vazio.setStyleSheet("color: #94a3b8; font-size: 13px; font-style: italic;")
                bloco_layout.addWidget(lbl_vazio, stretch=1)
                bloco_row.setStyleSheet("QFrame { background-color: white; border: 1px dashed #e2e8f0; border-radius: 6px; } QFrame:hover { border: 1px solid #cbd5e1; background-color: #f8fafc; }")
            
            self.layout_timeline.addWidget(bloco_row)
            
        if hasattr(self, "parent") and self.parent() and hasattr(self.parent(), "parent"):
            window = self.parent().parent()
            if hasattr(window, "atualizar_dados_home"):
                window.atualizar_dados_home()

    def navegar_dia_anterior(self):
        self.data_visualizada = self.data_visualizada.addDays(-1)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def navegar_proximo_dia(self):
        self.data_visualizada = self.data_visualizada.addDays(1)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def atualizar_visualizacao_data(self):
        self.btn_data_central.setText(self.data_visualizada.toString("dd 'de' MMMM 'de' yyyy"))

    def _paciente_do_slot(self, str_data, hora):
        """Retorna o nome do paciente dono do slot informado, seja ele o bloco
        principal ou uma continuação (nesse caso resolve até o bloco de origem)."""
        dados = self.db_agendamentos[str_data][hora]
        return dados.get("paciente", "outro paciente")

    # --- LÓGICA DE SALVAMENTO MULTI-BLOCO ---
    def salvar_agendamento_click(self):
        paciente = self.input_paciente.currentText().strip()
        if not paciente:
            QMessageBox.warning(self, "Campo Obrigatório", "Por favor, selecione ou digite o nome de um paciente!")
            return
        
        qtime_inicial = QTime.fromString(self.input_hora.currentText(), "hh:mm")
        duracao_minutos = self.converter_duracao_minutos(self.input_duracao.currentText())
        str_data = self.data_visualizada.toString("dd/MM/yyyy")

        # Validação: avisa (sem bloquear) se a data/hora escolhida já passou
        datahora_agendamento = QDateTime(self.data_visualizada, qtime_inicial)
        if datahora_agendamento < QDateTime.currentDateTime():
            resposta = QMessageBox.question(
                self, "⏰ Horário no Passado",
                f"O horário das {qtime_inicial.toString('hh:mm')} em "
                f"{self.data_visualizada.toString('dd/MM/yyyy')} já passou.\n\n"
                "Deseja registrar esse agendamento mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
        
        if str_data not in self.db_agendamentos:
            self.db_agendamentos[str_data] = {}
            
        # 1. Mapeia todos os sub-horários afetados por essa duração (de 30 em 30 min)
        horarios_a_reservar = []
        minutos_acumulados = 0
        
        while minutos_acumulados < duracao_minutos:
            slot_hora = qtime_inicial.addSecs(minutos_acumulados * 60).toString("hh:mm")
            horarios_a_reservar.append(slot_hora)
            minutos_acumulados += 30  # Avança em frações padrão

        # 2. Varre se há algum conflito em qualquer um dos blocos gerados,
        # já identificando o paciente que está ocupando o horário
        for slot in horarios_a_reservar:
            if slot in self.db_agendamentos[str_data]:
                paciente_conflito = self._paciente_do_slot(str_data, slot)
                QMessageBox.critical(
                    self, "⚠️ Conflito de Agenda",
                    f"Não foi possível agendar. O horário das {slot} já está ocupado "
                    f"por {paciente_conflito}!",
                    QMessageBox.StandardButton.Ok
                )
                return

        # 3. Se estiver livre, grava o Bloco Principal
        hora_inicial_str = horarios_a_reservar[0]
        self.db_agendamentos[str_data][hora_inicial_str] = {
            "tipo_bloco": "principal",
            "paciente": paciente.upper(),
            "procedimento": self.input_procedimento.currentText(),
            "status": self.input_status.currentText(),
            "duracao_txt": self.input_duracao.currentText(),
            "slots_vinculados": horarios_a_reservar # Guarda a lista para remoção em lote depois
        }
        
        # 4. Grava os Blocos de Continuação/Bloqueio subsequentes
        for slot_sequencia in horarios_a_reservar[1:]:
            self.db_agendamentos[str_data][slot_sequencia] = {
                "tipo_bloco": "continua",
                "paciente": paciente.upper(),
                "hora_origem": hora_inicial_str
            }
        
        # Limpeza padrão do formulário
        self.input_paciente.setCurrentIndex(-1)
        self.input_obs.clear()

        # UX: avança o seletor de horário para o próximo slot livre logo após
        # esse atendimento, agilizando o cadastro de vários pacientes seguidos
        ultimo_slot_ocupado = QTime.fromString(horarios_a_reservar[-1], "hh:mm")
        proximo_slot = ultimo_slot_ocupado.addSecs(30 * 60).toString("hh:mm")
        if proximo_slot in self.HORARIOS_GRADE:
            self.input_hora.setCurrentText(proximo_slot)
        
        # Força o redesenho imediato
        self.renderizar_timeline_calendario()

    # --- REMOÇÃO EM LOTE DOS BLOCOS (com confirmação de segurança) ---
    def remover_agendamento(self, hora):
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        if str_data not in self.db_agendamentos or hora not in self.db_agendamentos[str_data]:
            return

        dados = self.db_agendamentos[str_data][hora]
        if dados["tipo_bloco"] != "principal":
            return

        resposta = QMessageBox.question(
            self, "Confirmar Cancelamento",
            f"Cancelar o agendamento de {dados['paciente']} às {hora} "
            f"({dados['duracao_txt']})?\n\nEsta ação não poderá ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        # Limpa todos os slots que esse agendamento reservou de uma vez só
        for slot in dados["slots_vinculados"]:
            if slot in self.db_agendamentos[str_data]:
                del self.db_agendamentos[str_data][slot]

        self.renderizar_timeline_calendario()

    def apply_form_styles(self):
        widgets = [self.input_obs]
        for w in widgets:
            w.setStyleSheet("""
                QLineEdit { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: #f8fafc; color: #0f172a; font-size: 13px; }
                QLineEdit:focus { border: 1px solid #0284c7; background-color: white; }
            """)
        combos = [self.input_paciente, self.input_hora, self.input_duracao, self.input_procedimento, self.input_status]
        for c in combos:
            c.setStyleSheet("""
                QComboBox { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; background-color: white; color: #0f172a; font-size: 13px; }
                QComboBox:focus { border: 1px solid #0284c7; }
                QComboBox QAbstractItemView { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; selection-background-color: #0284c7; selection-color: white; padding: 4px; }
            """)