import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QFrame, 
                               QMessageBox, QCalendarWidget, QScrollArea,
                               QHeaderView, QTableView)
from PySide6.QtCore import Qt, QDate, QTime, QDateTime, QPoint

class AgendaScreen(QWidget):
    STATUS_CONSULTA = [
        "🕒 Agendado", "✅ Confirmado", "🏥 Em Atendimento",
        "✅ Realizada", "🚫 Cancelada", "❌ Faltou",
    ]
    HORARIOS_GRADE = [
        "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
        "17:00", "17:30", "18:00", "18:30", "19:00"
    ]

    def __init__(self, database_instancia):
        super().__init__()
        
        self.setStyleSheet("color: #0f172a;")
        
        # Recebe a conexão única já configurada e autenticada a partir da MainWindow
        self.db_gerenciador = database_instancia
        
        self.data_visualizada = QDate.currentDate()
        self.lista_pacientes_disponiveis = []
        self.db_agendamentos = {}
        
        self.carregar_agendamentos_db()
        
        # Layout Principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        
        # --- COLUNA DA ESQUERDA: CALENDÁRIO ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
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

        self.btn_hoje = QPushButton("Hoje")
        self.btn_hoje.setStyleSheet("""
            QPushButton { 
                background-color: #f1f5f9; color: #0284c7; font-size: 13px; font-weight: bold;
                border: 1px solid #cbd5e1; border-radius: 4px; padding: 0px 12px; height: 32px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_hoje.clicked.connect(self.ir_para_hoje)
        
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
        selector_layout.addWidget(self.btn_hoje)
        selector_layout.addStretch()
        selector_layout.addWidget(self.btn_data_central)
        selector_layout.addStretch()
        selector_layout.addWidget(self.btn_next_day)
        left_layout.addWidget(self.date_selector_container)
        
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
        # Remove o autocompletar embutido do Qt: ele fazia inline-completion
        # (sugeria e já deixava o restante do nome selecionado), o que
        # atrapalhava continuar digitando ou apagar com backspace. A gente
        # já filtra e mostra sugestões manualmente em filtrar_pacientes_ao_digitar.
        self.input_paciente.setCompleter(None)
        self.input_paciente.setPlaceholderText("Selecione ou digite para buscar...")
        self.input_paciente.lineEdit().textEdited.connect(self.filtrar_pacientes_ao_digitar)
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
        self.input_status.clear()
        self.input_status.addItems(self.STATUS_CONSULTA)
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

    def carregar_lista_pacientes_combobox(self):
        """Busca em tempo real a listagem de nomes cadastrados no Supabase para sugestões."""
        try:
            if hasattr(self.db_gerenciador, 'buscar_nomes_pacientes'):
                nomes = self.db_gerenciador.buscar_nomes_pacientes()
                self.atualizar_lista_sugestoes(nomes)
            elif hasattr(self.db_gerenciador, 'supabase') and self.db_gerenciador.supabase:
                resposta = self.db_gerenciador.supabase.table("pacientes")\
                    .select("nome")\
                    .eq("consultorio_id", self.db_gerenciador.consultorio_id)\
                    .is_("deleted_at", "null")\
                    .execute()
                nomes = [row["nome"] for row in resposta.data] if resposta.data else []
                self.atualizar_lista_sugestoes(nomes)
        except Exception as e:
            print(f"Erro ao popular combo de pacientes na Agenda: {e}")

    def carregar_agendamentos_db(self):
        """Carrega todos os agendamentos cadastrados no Supabase para o consultório atual."""
        self.db_agendamentos = {}
        if not self.db_gerenciador.supabase:
            return
        try:
            resposta = self.db_gerenciador.supabase.table("agenda")\
                .select("data, horario, paciente, status, procedimento, duracao_txt, observacao, tipo_bloco, slots_vinculados")\
                .eq("consultorio_id", self.db_gerenciador.consultorio_id)\
                .execute()
                
            if resposta.data:
                for row in resposta.data:
                    data = row["data"]
                    hora = row["horario"]
                    if data not in self.db_agendamentos:
                        self.db_agendamentos[data] = {}
                        
                    self.db_agendamentos[data][hora] = {
                        "tipo_bloco": row["tipo_bloco"],
                        "paciente": row["paciente"],
                        "status": row["status"],
                        "procedimento": row["procedimento"],
                        "duracao_txt": row["duracao_txt"],
                        "observacao": row["observacao"],
                        "slots_vinculados": (
                            row["slots_vinculados"] if isinstance(row["slots_vinculados"], list)
                            else json.loads(row["slots_vinculados"]) if row["slots_vinculados"] else []
                        )
                    }
        except Exception as e:
            print(f"Erro ao carregar agendamentos do Supabase: {e}")

    def salvar_agendamento_no_db(self, data, hora, dados_dict):
        """Grava ou atualiza de maneira atômica o agendamento na nuvem."""
        if not self.db_gerenciador.supabase:
            return False
        try:
            payload = {
                "consultorio_id": int(self.db_gerenciador.consultorio_id),
                "data": data,
                "horario": hora,
                "paciente": dados_dict.get("paciente", ""),
                "status": dados_dict.get("status", ""),
                "procedimento": dados_dict.get("procedimento", ""),
                "duracao_txt": dados_dict.get("duracao_txt", ""),
                "observacao": dados_dict.get("observacao", ""),
                "tipo_bloco": dados_dict.get("tipo_bloco", ""),
                "slots_vinculados": json.dumps(dados_dict.get("slots_vinculados", []))
            }
            tabela_agenda = self.db_gerenciador.supabase.table("agenda")
            existente = tabela_agenda.select("horario").eq(
                "consultorio_id", payload["consultorio_id"]
            ).eq("data", data).eq("horario", hora).execute()
            if existente.data:
                tabela_agenda.update(payload).eq(
                    "consultorio_id", payload["consultorio_id"]
                ).eq("data", data).eq("horario", hora).execute()
            else:
                tabela_agenda.insert(payload).execute()
            return True
        except Exception as e:
            print(f"Erro ao salvar agendamento no Supabase: {e}")
            self._ultimo_erro_agenda = str(e)
            return False

    def remover_agendamento_do_db(self, data, hora):
        """Apaga o slot da nuvem de forma imediata."""
        if not self.db_gerenciador.supabase:
            return
        try:
            self.db_gerenciador.supabase.table("agenda")\
                .delete()\
                .eq("consultorio_id", self.db_gerenciador.consultorio_id)\
                .eq("data", data)\
                .eq("horario", hora)\
                .execute()
        except Exception as e:
            print(f"Erro ao deletar agendamento: {e}")

    def atualizar_lista_sugestoes(self, nomes_pacientes):
        self.lista_pacientes_disponiveis = sorted(list(set(nomes_pacientes)))
        self.input_paciente.blockSignals(True)
        self.input_paciente.clear()
        self.input_paciente.addItems(self.lista_pacientes_disponiveis)
        self.input_paciente.setCurrentIndex(-1)
        self.input_paciente.blockSignals(False)

    def filtrar_pacientes_ao_digitar(self, texto_digitado):
        texto_norm = texto_digitado.strip().lower()
        self.input_paciente.blockSignals(True)
        self.input_paciente.clear()
        
        if not texto_norm:
            self.input_paciente.addItems(self.lista_pacientes_disponiveis)
            self.input_paciente.setCurrentIndex(-1)
            self.input_paciente.setEditText("")
        else:
            filtrados = [p for p in self.lista_pacientes_disponiveis if texto_norm in p.lower()]
            self.input_paciente.addItems(filtrados)
            self.input_paciente.setCurrentIndex(-1)
            self.input_paciente.setEditText(texto_digitado)
            if filtrados:
                self.input_paciente.showPopup()
                
        self.input_paciente.blockSignals(False)

    def abrir_mini_calendario(self):
        self.popup_calendario = QCalendarWidget()
        self.popup_calendario.setWindowFlags(Qt.WindowType.Popup)
        self.popup_calendario.setSelectedDate(self.data_visualizada)
        self.popup_calendario.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.popup_calendario.setGridVisible(False)
        self.popup_calendario.setFixedSize(300, 260)
        self.popup_calendario.setStyleSheet("""
            QCalendarWidget { background-color: white; border: 1px solid #cbd5e1; border-radius: 8px; color: #0f172a; }
            QCalendarWidget QTableView { background-color: white; selection-background-color: #0284c7; selection-color: white; outline: none; color: #0f172a; }
            QCalendarWidget QAbstractItemView:enabled { color: #0f172a; background-color: white; selection-background-color: #0284c7; selection-color: white; }
            QCalendarWidget QAbstractItemView:disabled { color: #cbd5e1; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: #0f172a; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QCalendarWidget QToolButton { color: white; font-weight: bold; border: none; background: transparent; }
            QCalendarWidget QToolButton:hover { background-color: #1e293b; border-radius: 4px; }
            QCalendarWidget QSpinBox { background-color: #1e293b; color: white; border: none; selection-background-color: #0284c7; }
            QCalendarWidget QMenu { background-color: white; color: #0f172a; }
        """)

        tabela_dias = self.popup_calendario.findChild(QTableView)
        if tabela_dias:
            cabecalho = tabela_dias.horizontalHeader()
            cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            cabecalho.setMinimumSectionSize(30)

        self.popup_calendario.clicked.connect(self.ao_escolher_data_popup)

        x_central = self.btn_data_central.mapToGlobal(QPoint(0, 0)).x() + (self.btn_data_central.width() // 2)
        y_abaixo = self.btn_data_central.mapToGlobal(QPoint(0, self.btn_data_central.height() + 6)).y()
        self.popup_calendario.move(x_central - (self.popup_calendario.width() // 2), y_abaixo)
        self.popup_calendario.show()

    def ao_escolher_data_popup(self, data):
        self.data_visualizada = data
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()
        self.popup_calendario.close()

    def converter_duracao_minutos(self, texto_duracao):
        if "15" in texto_duracao: return 15
        if "30" in texto_duracao: return 30
        if "45" in texto_duracao: return 45
        if "1 hora" == texto_duracao: return 60
        if "1h 30min" in texto_duracao: return 90
        if "2 horas" in texto_duracao: return 120
        return 30

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
            bloco_row.setObjectName("bloco_row")
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
                    status_txt = dados["status"]
                    cor_borda = "#0284c7"
                    if "Confirmado" in status_txt or "Realizada" in status_txt: cor_borda = "#10b981"
                    elif "Atendimento" in status_txt: cor_borda = "#f59e0b"
                    elif "Faltou" in status_txt or "Cancelada" in status_txt: cor_borda = "#ef4444"
                    
                    card_info = QFrame()
                    card_info.setStyleSheet(f"QFrame {{ background-color: white; border: 1px solid #e2e8f0; border-left: 5px solid {cor_borda}; border-radius: 6px; }}")
                    card_info_layout = QHBoxLayout(card_info)
                    card_info_layout.setContentsMargins(12, 10, 12, 10)
                    
                    vbox_detalhes = QVBoxLayout()
                    vbox_detalhes.setSpacing(2)
                    
                    lbl_paciente = QLabel(dados["paciente"])
                    lbl_paciente.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a; border: none;")
                    
                    texto_sub = f"📋 {dados['procedimento']} ({dados['duracao_txt']})  •  {status_txt}"
                    if dados.get("observacao"):
                        texto_sub += f"  •  📝 {dados['observacao']}"
                        
                    lbl_sub = QLabel(texto_sub)
                    lbl_sub.setWordWrap(True)
                    lbl_sub.setMinimumWidth(0)
                    lbl_sub.setStyleSheet("font-size: 12px; color: #64748b; border: none;")
                    
                    vbox_detalhes.addWidget(lbl_paciente)
                    vbox_detalhes.addWidget(lbl_sub)
                    card_info_layout.addLayout(vbox_detalhes, stretch=1)
                    
                    btn_remover = QPushButton("✕")
                    combo_status = QComboBox()
                    combo_status.addItems(self.STATUS_CONSULTA)
                    indice_status = combo_status.findText(status_txt)
                    if indice_status < 0:
                        combo_status.addItem(status_txt)
                        indice_status = combo_status.count() - 1
                    combo_status.setCurrentIndex(indice_status)
                    combo_status.setMaximumWidth(105)
                    combo_status.setStyleSheet(
                        "QComboBox { background: #f8fafc; color: #334155; border: 1px solid #cbd5e1; "
                        "border-radius: 5px; padding: 5px; font-size: 11px; min-width: 115px; }"
                    )
                    combo_status.currentTextChanged.connect(
                        lambda novo_status, h=hora: self.atualizar_status_agendamento(h, novo_status)
                    )
                    card_info_layout.addWidget(combo_status)

                    if "Realizada" in status_txt:
                        btn_ficha = QPushButton("Abrir ficha")
                        btn_ficha.setStyleSheet(
                            "QPushButton { background: #0284c7; color: white; border: none; border-radius: 5px; "
                            "padding: 6px 9px; font-weight: bold; font-size: 11px; } "
                            "QPushButton:hover { background: #0369a1; }"
                        )
                        btn_ficha.clicked.connect(lambda checked=False, h=hora: self.abrir_ficha_da_consulta(h))
                        btn_ficha.setMaximumWidth(78)
                        card_info_layout.addWidget(btn_ficha)

                    btn_remover.setFixedSize(24, 24)
                    btn_remover.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; border: none; font-weight: bold; font-size: 14px; } QPushButton:hover { color: #ef4444; }")
                    btn_remover.clicked.connect(lambda checked=False, h=hora: self.remover_agendamento(h))
                    card_info_layout.addWidget(btn_remover)
                    
                    bloco_layout.addWidget(card_info, stretch=1)
                else:
                    card_bloqueado = QFrame()
                    card_bloqueado.setStyleSheet("QFrame { background-color: #f1f5f9; border: 1px dashed #cbd5e1; border-left: 5px solid #cbd5e1; border-radius: 6px; }")
                    cb_layout = QHBoxLayout(card_bloqueado)
                    cb_layout.setContentsMargins(12, 6, 12, 6)
                    
                    lbl_bloqueio = QLabel(f"↳ Ocupado — Continuação do atendimento de {dados['paciente']}")
                    lbl_bloqueio.setStyleSheet("color: #475569; font-size: 12px; font-style: italic; border: none;")
                    cb_layout.addWidget(lbl_bloqueio)
                    
                    bloco_layout.addWidget(card_bloqueado, stretch=1)
            else:
                lbl_vazio = QLabel("— Horário Disponível —")
                lbl_vazio.setStyleSheet("color: #94a3b8; font-size: 13px; font-style: italic; background: transparent;")
                bloco_layout.addWidget(lbl_vazio, stretch=1)
                bloco_row.setStyleSheet("QFrame#bloco_row { background-color: white; border: 1px dashed #e2e8f0; border-radius: 6px; } QFrame#bloco_row:hover { border: 1px solid #cbd5e1; background-color: #f8fafc; }")
            
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

    def ir_para_hoje(self):
        self.data_visualizada = QDate.currentDate()
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def atualizar_visualizacao_data(self):
        self.btn_data_central.setText(self.data_visualizada.toString("dd 'de' MMMM 'de' yyyy"))

    def _paciente_do_slot(self, str_data, hora):
        dados = self.db_agendamentos[str_data][hora]
        return dados.get("paciente", "outro paciente")

    def salvar_agendamento_click(self):
        self.input_paciente.blockSignals(True)
        paciente = self.input_paciente.lineEdit().text().strip()
        
        if not paciente:
            self.input_paciente.blockSignals(False)
            msg = QMessageBox(self)
            msg.setWindowTitle("Campo Obrigatório")
            msg.setText("Por favor, selecione ou digite o nome de um paciente!")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setStyleSheet("QMessageBox { background-color: #ffffff; } QLabel { color: #0f172a; font-size: 13px; } QPushButton { background-color: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 15px; font-weight: bold; }")
            msg.exec()
            return
        
        qtime_inicial = QTime.fromString(self.input_hora.currentText(), "hh:mm")
        duracao_minutos = self.converter_duracao_minutos(self.input_duracao.currentText())
        str_data = self.data_visualizada.toString("dd/MM/yyyy")

        datahora_agendamento = QDateTime(self.data_visualizada, qtime_inicial)
        if datahora_agendamento < QDateTime.currentDateTime():
            msg = QMessageBox(self)
            msg.setWindowTitle("⏰ Horário no Passado")
            msg.setText(f"O horário das {qtime_inicial.toString('hh:mm')} em {self.data_visualizada.toString('dd/MM/yyyy')} já passou.\n\nDeseja registrar esse agendamento mesmo assim?")
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            msg.setStyleSheet("QMessageBox { background-color: #ffffff; } QLabel { color: #0f172a; font-size: 13px; } QPushButton { background-color: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 15px; font-weight: bold; }")
            if msg.exec() != QMessageBox.StandardButton.Yes:
                self.input_paciente.blockSignals(False)
                return
        
        if str_data not in self.db_agendamentos:
            self.db_agendamentos[str_data] = {}
            
        horarios_a_reservar = []
        minutos_acumulados = 0
        
        while minutos_acumulados < duracao_minutos:
            slot_hora = qtime_inicial.addSecs(minutos_acumulados * 60).toString("hh:mm")
            horarios_a_reservar.append(slot_hora)
            minutos_acumulados += 30

        for slot in horarios_a_reservar:
            if slot in self.db_agendamentos[str_data]:
                paciente_conflito = self._paciente_do_slot(str_data, slot)
                msg = QMessageBox(self)
                msg.setWindowTitle("⚠️ Conflito de Agenda")
                msg.setText(f"Não foi possível agendar. O horário das {slot} já está ocupado por {paciente_conflito}!")
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setStyleSheet("QMessageBox { background-color: #ffffff; } QLabel { color: #0f172a; font-size: 13px; } QPushButton { background-color: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 15px; font-weight: bold; }")
                msg.exec()
                self.input_paciente.blockSignals(False)
                return

        hora_inicial_str = horarios_a_reservar[0]
        bloco_principal = {
            "tipo_bloco": "principal",
            "paciente": paciente.upper(),
            "procedimento": self.input_procedimento.currentText(),
            "status": self.input_status.currentText(),
            "duracao_txt": self.input_duracao.currentText(),
            "observacao": self.input_obs.text().strip(),
            "slots_vinculados": horarios_a_reservar
        }
        
        self.db_agendamentos[str_data][hora_inicial_str] = bloco_principal
        if not self.salvar_agendamento_no_db(str_data, hora_inicial_str, bloco_principal):
            del self.db_agendamentos[str_data][hora_inicial_str]
            self.input_paciente.blockSignals(False)
            detalhe = getattr(self, "_ultimo_erro_agenda", "Motivo não informado pelo Supabase.")
            QMessageBox.critical(
                self,
                "Consulta não salva",
                "Não foi possível salvar a consulta no Supabase. Ela não será mantida apenas na memória.\n\n"
                f"Detalhe para correção: {detalhe}",
            )
            return
        
        for slot_sequencia in horarios_a_reservar[1:]:
            bloco_continua = {
                "tipo_bloco": "continua",
                "paciente": paciente.upper(),
                "hora_origem": hora_inicial_str,
                "status": "",
                "procedimento": "",
                "duracao_txt": "",
                "observacao": "",
                "slots_vinculados": []
            }
            self.db_agendamentos[str_data][slot_sequencia] = bloco_continua
            self.salvar_agendamento_no_db(str_data, slot_sequencia, bloco_continua)
        
        self.input_paciente.blockSignals(False)
        self.atualizar_lista_sugestoes(self.lista_pacientes_disponiveis)
        self.input_obs.clear()

        ultimo_slot_ocupado = QTime.fromString(horarios_a_reservar[-1], "hh:mm")
        proximo_slot = ultimo_slot_ocupado.addSecs(30 * 60).toString("hh:mm")
        if proximo_slot in self.HORARIOS_GRADE:
            self.input_hora.setCurrentText(proximo_slot)
        
        self.renderizar_timeline_calendario()

    def atualizar_status_agendamento(self, hora, novo_status):
        """Atualiza o status sem alterar o horário ou os dados da consulta."""
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        dados = self.db_agendamentos.get(str_data, {}).get(hora)
        if not dados or dados.get("tipo_bloco") != "principal":
            return
        if dados.get("status") == novo_status:
            return
        dados["status"] = novo_status
        self.salvar_agendamento_no_db(str_data, hora, dados)
        self.renderizar_timeline_calendario()

    def abrir_ficha_da_consulta(self, hora):
        """Localiza o paciente da consulta realizada e abre uma nova ficha."""
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        dados = self.db_agendamentos.get(str_data, {}).get(hora)
        if not dados or "Realizada" not in dados.get("status", ""):
            return
        if not self.db_gerenciador.supabase:
            return
        try:
            resposta = self.db_gerenciador.supabase.table("pacientes").select("id").eq(
                "consultorio_id", self.db_gerenciador.consultorio_id
            ).ilike("nome", dados["paciente"]).is_("deleted_at", "null").execute()
            if not resposta.data:
                QMessageBox.warning(self, "Paciente não encontrado", "Não foi possível localizar o paciente desta consulta.")
                return
            janela = getattr(self, "window_principal", None)
            if janela and hasattr(janela, "abrir_nova_ficha_para_paciente"):
                janela.abrir_nova_ficha_para_paciente(resposta.data[0]["id"])
        except Exception as e:
            print(f"Erro ao abrir ficha pela agenda: {e}")
            QMessageBox.warning(self, "Não foi possível abrir", "Não foi possível abrir a ficha deste paciente agora.")

    def remover_agendamento(self, hora):
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        if str_data not in self.db_agendamentos or hora not in self.db_agendamentos[str_data]:
            return

        dados = self.db_agendamentos[str_data][hora]
        if dados["tipo_bloco"] != "principal":
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar Cancelamento")
        msg.setText(f"Cancelar o agendamento de {dados['paciente']} às {hora} ({dados['duracao_txt']})?\n\nEsta ação não poderá ser desfeita.")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("QMessageBox { background-color: #ffffff; } QLabel { color: #0f172a; font-size: 13px; } QPushButton { background-color: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 15px; font-weight: bold; }")
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        # Deleta todos os slots associados a essa consulta
        for slot in dados["slots_vinculados"]:
            if slot in self.db_agendamentos[str_data]:
                del self.db_agendamentos[str_data][slot]
                self.remover_agendamento_do_db(str_data, slot)

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
                QComboBox QLineEdit { color: #0f172a; background-color: white; selection-background-color: #0284c7; selection-color: white; }
                QComboBox QAbstractItemView { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; selection-background-color: #0284c7; selection-color: white; padding: 4px; }
            """)
