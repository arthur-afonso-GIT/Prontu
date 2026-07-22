import json
import webbrowser
import urllib.parse
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QLineEdit, QPushButton, QComboBox, QFrame, 
                               QMessageBox, QCalendarWidget, QScrollArea,
                               QHeaderView, QTableView, QCheckBox, QCompleter, QDialog,
                               QInputDialog, QSizePolicy)
from PySide6.QtCore import Qt, QDate, QTime, QDateTime, QPoint
from ui.design_system import definir_variante
from utils.operacao_segura import mensagem_erro_usuario, registrar_falha


MENSAGEM_LEMBRETE_CONSULTA_PADRAO = (
    "Olá, {paciente}! Lembramos que sua consulta está marcada para {data} às {hora}. "
    "Procedimento: {procedimento}. Por favor, confirme sua presença."
)

class AgendaScreen(QWidget):
    TIPOS_CONSULTA_PADRAO = [
        "Primeira Consulta / Avaliação",
        "Retorno",
        "Procedimento Clínico",
        "Telemedicina",
    ]
    STATUS_CONSULTA = [
        "🕒 Agendado", "✅ Confirmado", "🏥 Em Atendimento",
        "✅ Realizada", "🚫 Cancelada", "❌ Faltou",
    ]
    HORARIOS_GRADE = [
        "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
        "17:00", "17:30", "18:00", "18:30", "19:00"
    ]
    MESES_PT = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    DIAS_SEMANA_PT = [
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo",
    ]

    def __init__(self, database_instancia):
        super().__init__()
        self.setObjectName("AgendaScreen")
        
        # Recebe a conexão única já configurada e autenticada a partir da MainWindow
        self.db_gerenciador = database_instancia
        
        self.data_visualizada = QDate.currentDate()
        self.lista_pacientes_disponiveis = []
        self.db_agendamentos = {}
        self.retornos_pendentes_por_paciente = {}
        self.alertas_respostas_whatsapp = {}
        self._retorno_em_agendamento = None
        self._formulario_editado_pelo_usuario = False
        
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
        self.date_selector_container.setObjectName("AgendaCard")
        selector_layout = QGridLayout(self.date_selector_container)
        selector_layout.setContentsMargins(15, 8, 15, 8)
        selector_layout.setColumnStretch(0, 1)
        selector_layout.setColumnStretch(1, 1)
        selector_layout.setColumnStretch(2, 1)
        
        self.btn_prev_day = QPushButton("‹")
        self.btn_prev_day.setFixedSize(34, 34)
        self.btn_prev_day.clicked.connect(self.navegar_dia_anterior)

        self.btn_hoje = QPushButton("Hoje")
        definir_variante(self.btn_hoje, "secondary")
        self.btn_hoje.clicked.connect(self.ir_para_hoje)
        
        self.btn_data_central = QPushButton("")
        definir_variante(self.btn_data_central, "ghost")
        fonte_data = self.btn_data_central.font()
        fonte_data.setPointSize(11)
        fonte_data.setBold(True)
        self.btn_data_central.setFont(fonte_data)
        self.btn_data_central.clicked.connect(self.abrir_mini_calendario)
        
        self.btn_next_day = QPushButton("›")
        self.btn_next_day.setFixedSize(34, 34)
        self.btn_next_day.clicked.connect(self.navegar_proximo_dia)
        
        controles_esquerda = QHBoxLayout()
        controles_esquerda.setContentsMargins(0, 0, 0, 0)
        controles_esquerda.setSpacing(6)
        controles_esquerda.addWidget(self.btn_prev_day)
        controles_esquerda.addWidget(self.btn_hoje)

        # As três colunas têm a mesma largura: assim a data fica no centro real
        # do cabeçalho, mesmo que os controles laterais tenham tamanhos diferentes.
        selector_layout.addLayout(controles_esquerda, 0, 0, Qt.AlignmentFlag.AlignLeft)
        selector_layout.addWidget(self.btn_data_central, 0, 1, Qt.AlignmentFlag.AlignCenter)
        selector_layout.addWidget(self.btn_next_day, 0, 2, Qt.AlignmentFlag.AlignRight)
        left_layout.addWidget(self.date_selector_container)

        self.resumo_container = QFrame()
        self.resumo_container.setObjectName("AgendaCard")
        resumo_layout = QHBoxLayout(self.resumo_container)
        resumo_layout.setContentsMargins(14, 9, 14, 9)
        resumo_layout.setSpacing(10)

        texto_resumo = QVBoxLayout()
        self.lbl_titulo_resumo = QLabel("Agenda do dia")
        self.lbl_titulo_resumo.setObjectName("TituloResumo")
        self.lbl_resumo_agenda = QLabel("")
        self.lbl_resumo_agenda.setObjectName("TextoResumo")
        texto_resumo.addWidget(self.lbl_titulo_resumo)
        texto_resumo.addWidget(self.lbl_resumo_agenda)
        resumo_layout.addLayout(texto_resumo)
        resumo_layout.addStretch()

        self.modo_visualizacao = QComboBox()
        self.modo_visualizacao.addItem("Visão diária", "dia")
        self.modo_visualizacao.addItem("Visão semanal", "semana")
        self.modo_visualizacao.addItem("Visão mensal", "mes")
        self.modo_visualizacao.setToolTip("Alternar entre agenda diária e semanal")
        self.modo_visualizacao.currentIndexChanged.connect(self.alterar_modo_visualizacao)
        resumo_layout.addWidget(self.modo_visualizacao)

        self.filtro_status = QComboBox()
        self.filtro_status.addItem("Todos os status", "")
        self.filtro_status.addItem("Agendadas", "Agendado")
        self.filtro_status.addItem("Confirmadas", "Confirmado")
        self.filtro_status.addItem("Em atendimento", "Atendimento")
        self.filtro_status.addItem("Realizadas", "Realizada")
        self.filtro_status.addItem("Canceladas ou faltas", "Cancelada|Faltou")
        self.filtro_status.setToolTip("Filtrar consultas pelo status")
        self.filtro_status.currentIndexChanged.connect(self.renderizar_timeline_calendario)
        resumo_layout.addWidget(self.filtro_status)

        self.chk_ocultar_disponiveis = QCheckBox("Ocultar horários disponíveis")
        self.chk_ocultar_disponiveis.setStyleSheet(
            "QCheckBox { color: #475569; font-size: 12px; border: none; }"
        )
        self.chk_ocultar_disponiveis.toggled.connect(self.renderizar_timeline_calendario)
        resumo_layout.addWidget(self.chk_ocultar_disponiveis)
        left_layout.addWidget(self.resumo_container)
        
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
        self.form_container.setObjectName("FormCard")
        
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
        # Sugestoes em popup sem completar o texto por conta propria nem
        # tirar o foco da pessoa enquanto ela ainda esta digitando.
        self.completer_pacientes = QCompleter(self.input_paciente.model(), self.input_paciente)
        self.completer_pacientes.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer_pacientes.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer_pacientes.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.input_paciente.setCompleter(self.completer_pacientes)
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
        self._popular_tipos_consulta()
        procedimento_layout = QHBoxLayout()
        procedimento_layout.setContentsMargins(0, 0, 0, 0)
        procedimento_layout.setSpacing(8)
        procedimento_layout.addWidget(self.input_procedimento, stretch=1)
        self.btn_adicionar_tipo_consulta = QPushButton("+")
        self.btn_adicionar_tipo_consulta.setToolTip("Adicionar tipo de consulta personalizado")
        self.btn_adicionar_tipo_consulta.setAccessibleName("Adicionar tipo de consulta")
        self.btn_adicionar_tipo_consulta.setFixedSize(36, 36)
        definir_variante(self.btn_adicionar_tipo_consulta, "secondary")
        self.btn_adicionar_tipo_consulta.clicked.connect(self.adicionar_tipo_consulta_personalizado)
        procedimento_layout.addWidget(self.btn_adicionar_tipo_consulta)
        form_layout.addLayout(procedimento_layout)
        
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
        definir_variante(self.btn_salvar, "primary")
        self.btn_salvar.clicked.connect(self.salvar_agendamento_click)
        form_layout.addWidget(self.btn_salvar)
        
        main_layout.addWidget(left_container, stretch=3)
        main_layout.addWidget(self.form_container, stretch=1)
        
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()
        self._conectar_monitoramento_formulario()
        self._marcar_formulario_salvo()

    def _tipos_consulta_personalizados(self):
        """Retorna os tipos extras salvos para a clínica atual."""
        try:
            valor = self.db_gerenciador.obter_configuracao(
                "agenda_tipos_consulta_personalizados", "[]"
            )
            tipos = json.loads(valor or "[]")
            if not isinstance(tipos, list):
                return []
            return [str(tipo).strip() for tipo in tipos if str(tipo).strip()]
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    def _popular_tipos_consulta(self, selecionado=None):
        """Atualiza o seletor sem perder o tipo selecionado pelo usuário."""
        if not hasattr(self, "input_procedimento"):
            return
        tipo_atual = selecionado or self.input_procedimento.currentText()
        tipos = list(self.TIPOS_CONSULTA_PADRAO)
        chaves = {tipo.casefold() for tipo in tipos}
        for tipo in self._tipos_consulta_personalizados():
            if tipo.casefold() not in chaves:
                tipos.append(tipo)
                chaves.add(tipo.casefold())
        self.input_procedimento.blockSignals(True)
        self.input_procedimento.clear()
        self.input_procedimento.addItems(tipos)
        indice = self.input_procedimento.findText(tipo_atual)
        self.input_procedimento.setCurrentIndex(indice if indice >= 0 else 0)
        self.input_procedimento.blockSignals(False)

    def adicionar_tipo_consulta_personalizado(self):
        """Permite que a clínica acrescente um procedimento ao seletor da Agenda."""
        tipo, confirmou = QInputDialog.getText(
            self,
            "Novo tipo de consulta",
            "Nome do tipo de consulta:",
        )
        tipo = tipo.strip()
        if not confirmou or not tipo:
            return

        existentes = self._tipos_consulta_personalizados()
        todos = [*self.TIPOS_CONSULTA_PADRAO, *existentes]
        if any(tipo.casefold() == existente.casefold() for existente in todos):
            QMessageBox.information(
                self,
                "Tipo já cadastrado",
                "Esse tipo de consulta já está disponível na lista.",
            )
            self._popular_tipos_consulta(tipo)
            return

        try:
            self.db_gerenciador.salvar_configuracao(
                "agenda_tipos_consulta_personalizados",
                json.dumps([*existentes, tipo], ensure_ascii=False),
            )
            self._popular_tipos_consulta(tipo)
        except Exception:
            QMessageBox.warning(
                self,
                "Não foi possível salvar",
                "Não foi possível adicionar o tipo de consulta agora. Tente novamente.",
            )

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
                .select("data, horario, paciente, status, procedimento, duracao_txt, observacao, tipo_bloco, slots_vinculados, retorno_id")\
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
                        "retorno_id": row.get("retorno_id"),
                        "slots_vinculados": (
                            row["slots_vinculados"] if isinstance(row["slots_vinculados"], list)
                            else json.loads(row["slots_vinculados"]) if row["slots_vinculados"] else []
                        )
                    }
        except Exception as e:
            print(f"Erro ao carregar agendamentos do Supabase: {e}")
        self.carregar_retornos_pendentes_cache()
        self.garantir_retornos_de_consultas_realizadas()
        self.carregar_alertas_respostas_whatsapp()

    @staticmethod
    def _chave_nome_paciente(nome):
        return " ".join(str(nome or "").strip().casefold().split())

    def carregar_retornos_pendentes_cache(self):
        """Mantém as decisões de retorno disponíveis na Agenda sem consultar por cartão."""
        self.retornos_pendentes_por_paciente = {}
        if not hasattr(self.db_gerenciador, "listar_retornos_pendentes"):
            return
        for retorno in self.db_gerenciador.listar_retornos_pendentes():
            chave = self._chave_nome_paciente(retorno.get("paciente_nome"))
            if chave:
                self.retornos_pendentes_por_paciente[chave] = retorno

    def garantir_retornos_de_consultas_realizadas(self):
        """Recupera consultas já concluídas que ficaram sem decisão de retorno."""
        if not hasattr(self.db_gerenciador, "criar_retorno_pendente_da_consulta"):
            return
        candidatos = {}
        for data_consulta, agenda_dia in self.db_agendamentos.items():
            for hora_consulta, dados in agenda_dia.items():
                if dados.get("tipo_bloco") != "principal":
                    continue
                if "Realizada" not in str(dados.get("status") or ""):
                    continue
                if str(dados.get("procedimento") or "").strip().casefold() == "retorno":
                    continue
                chave = self._chave_nome_paciente(dados.get("paciente"))
                if not chave or chave in self.retornos_pendentes_por_paciente:
                    continue
                momento = QDateTime.fromString(
                    f"{data_consulta} {hora_consulta}", "dd/MM/yyyy hh:mm"
                )
                anterior = candidatos.get(chave)
                if not anterior or momento > anterior[0]:
                    candidatos[chave] = (momento, data_consulta, hora_consulta, dados)

        # Somente a consulta concluída mais recente de cada paciente é recuperada.
        # Assim a atualização não transforma todo o histórico antigo em pendências.
        for chave, (_, data_consulta, hora_consulta, dados) in candidatos.items():
            retorno = self.db_gerenciador.criar_retorno_pendente_da_consulta(
                str(dados.get("paciente") or ""), data_consulta, hora_consulta
            )
            if retorno and retorno.get("status") == "Pendente":
                self.retornos_pendentes_por_paciente[chave] = retorno

    def carregar_alertas_respostas_whatsapp(self):
        """Busca respostas recebidas que ainda precisam de ação da equipe."""
        self.alertas_respostas_whatsapp = {}
        if not self.db_gerenciador.supabase or self.db_gerenciador.consultorio_id is None:
            return
        try:
            respostas = self.db_gerenciador.supabase.table("respostas_whatsapp")\
                .select("id, lembrete_id, conteudo, recebida_em")\
                .eq("consultorio_id", self.db_gerenciador.consultorio_id)\
                .eq("status", "a_revisar")\
                .order("recebida_em", desc=True)\
                .execute()
            pendentes = respostas.data or []
            lembrete_ids = [item.get("lembrete_id") for item in pendentes if item.get("lembrete_id")]
            if not lembrete_ids:
                return
            lembretes = self.db_gerenciador.supabase.table("lembretes_whatsapp")\
                .select("id, agenda_data, agenda_horario")\
                .in_("id", lembrete_ids)\
                .execute()
            agenda_por_lembrete = {item["id"]: item for item in (lembretes.data or [])}
            for resposta in pendentes:
                lembrete = agenda_por_lembrete.get(resposta.get("lembrete_id"))
                if lembrete:
                    chave = (lembrete.get("agenda_data"), lembrete.get("agenda_horario"))
                    self.alertas_respostas_whatsapp.setdefault(chave, resposta)
        except Exception as erro:
            # Antes da migration 021, a Agenda continua funcionando normalmente.
            print(f"Aviso: alertas de WhatsApp indisponíveis ({type(erro).__name__}).")

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
                "retorno_id": dados_dict.get("retorno_id"),
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
            registrar_falha("salvar agendamento", e)
            self._ultimo_erro_agenda = type(e).__name__
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
        """Mantido por compatibilidade; o QCompleter faz o filtro sem perder foco."""
        return

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

        if self.modo_visualizacao.currentData() == "semana":
            self.renderizar_grade_semanal()
            return
        if self.modo_visualizacao.currentData() == "mes":
            self.renderizar_visao_mensal()
            return

        self.scroll_agenda.setWidgetResizable(True)
        self.container_timeline.setMinimumWidth(0)
                
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        agendamentos_do_dia = self.db_agendamentos.get(str_data, {})
        self.atualizar_resumo_do_dia(agendamentos_do_dia)
        filtro_status = self.filtro_status.currentData()
        exibir_apenas_consultas = bool(filtro_status) or self.chk_ocultar_disponiveis.isChecked()
        
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
                    if not self._status_corresponde_ao_filtro(dados.get("status", ""), filtro_status):
                        continue
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
                    alerta_resposta = self.alertas_respostas_whatsapp.get((str_data, hora))
                    if alerta_resposta:
                        btn_resposta = QPushButton("Resposta para revisar")
                        btn_resposta.setToolTip("O paciente enviou uma resposta que precisa de ação da equipe")
                        btn_resposta.setFixedHeight(24)
                        btn_resposta.setStyleSheet(
                            "QPushButton { background: #fff7ed; color: #c2410c; border: 1px solid #fdba74; "
                            "border-radius: 5px; padding: 2px 8px; font-size: 11px; font-weight: 700; } "
                            "QPushButton:hover { background: #ffedd5; border-color: #f97316; }"
                        )
                        btn_resposta.clicked.connect(
                            lambda checked=False, h=hora: self.revisar_resposta_whatsapp(h)
                        )
                        vbox_detalhes.addWidget(btn_resposta)
                    card_info_layout.addLayout(vbox_detalhes, stretch=1)
                    
                    btn_remover = QPushButton("✕")
                    area_acoes = QWidget()
                    area_acoes_layout = QHBoxLayout(area_acoes)
                    area_acoes_layout.setContentsMargins(0, 0, 0, 0)
                    area_acoes_layout.setSpacing(8)
                    area_acoes_layout.setAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    area_acoes.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                    self.adicionar_acoes_rapidas_consulta(area_acoes_layout, hora, status_txt)

                    chave_paciente = self._chave_nome_paciente(dados.get("paciente"))
                    retorno_pendente = self.retornos_pendentes_por_paciente.get(chave_paciente)
                    if "Realizada" in status_txt and retorno_pendente:
                        btn_agendar_retorno = QPushButton("Agendar retorno")
                        btn_agendar_retorno.setToolTip("Escolher a data e preparar o retorno na Agenda")
                        btn_agendar_retorno.setFixedSize(126, 36)
                        btn_agendar_retorno.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                        definir_variante(btn_agendar_retorno, "secondary")
                        btn_agendar_retorno.clicked.connect(
                            lambda checked=False, h=hora: self.agendar_retorno_da_consulta(h)
                        )
                        area_acoes_layout.addWidget(btn_agendar_retorno)

                        btn_sem_retorno = QPushButton("Não retornará")
                        btn_sem_retorno.setToolTip("Registrar que não haverá retorno desta consulta")
                        btn_sem_retorno.setFixedSize(118, 36)
                        btn_sem_retorno.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                        definir_variante(btn_sem_retorno, "danger")
                        btn_sem_retorno.clicked.connect(
                            lambda checked=False, h=hora: self.marcar_sem_retorno_da_consulta(h)
                        )
                        area_acoes_layout.addWidget(btn_sem_retorno)

                    if not any(termo in status_txt for termo in ("Realizada", "Cancelada", "Faltou")):
                        btn_lembrete = QPushButton("Enviar lembrete")
                        btn_lembrete.setToolTip("Abrir o WhatsApp com o lembrete desta consulta preenchido")
                        btn_lembrete.setFixedHeight(34)
                        btn_lembrete.setMinimumWidth(124)
                        btn_lembrete.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                        definir_variante(btn_lembrete, "secondary")
                        btn_lembrete.clicked.connect(
                            lambda checked=False, h=hora: self.enviar_lembrete_whatsapp(h)
                        )
                        area_acoes_layout.addWidget(btn_lembrete)

                    if "Realizada" in status_txt:
                        btn_ficha = QPushButton("Abrir ficha")
                        btn_ficha.setStyleSheet(
                            "QPushButton { background: #0284c7; color: white; border: none; border-radius: 5px; "
                            "padding: 6px 9px; font-weight: bold; font-size: 11px; } "
                            "QPushButton:hover { background: #0369a1; }"
                        )
                        btn_ficha.clicked.connect(lambda checked=False, h=hora: self.abrir_ficha_da_consulta(h))
                        btn_ficha.setFixedSize(96, 36)
                        area_acoes_layout.addWidget(btn_ficha)

                    btn_remover.setFixedSize(24, 24)
                    btn_remover.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; border: none; font-weight: bold; font-size: 14px; } QPushButton:hover { color: #ef4444; }")
                    btn_remover.clicked.connect(lambda checked=False, h=hora: self.remover_agendamento(h))
                    card_info_layout.addWidget(area_acoes, alignment=Qt.AlignmentFlag.AlignVCenter)
                    card_info_layout.addWidget(btn_remover)
                    
                    bloco_layout.addWidget(card_info, stretch=1)
                else:
                    if filtro_status:
                        continue
                    card_bloqueado = QFrame()
                    card_bloqueado.setStyleSheet("QFrame { background-color: #f1f5f9; border: 1px dashed #cbd5e1; border-left: 5px solid #cbd5e1; border-radius: 6px; }")
                    cb_layout = QHBoxLayout(card_bloqueado)
                    cb_layout.setContentsMargins(12, 6, 12, 6)
                    
                    lbl_bloqueio = QLabel(f"↳ Ocupado — Continuação do atendimento de {dados['paciente']}")
                    lbl_bloqueio.setStyleSheet("color: #475569; font-size: 12px; font-style: italic; border: none;")
                    cb_layout.addWidget(lbl_bloqueio)
                    
                    bloco_layout.addWidget(card_bloqueado, stretch=1)
            else:
                if exibir_apenas_consultas:
                    continue
                lbl_vazio = QLabel("— Horário Disponível —")
                lbl_vazio.setStyleSheet("color: #94a3b8; font-size: 13px; font-style: italic; background: transparent;")
                bloco_layout.addWidget(lbl_vazio, stretch=1)
                bloco_row.setStyleSheet("QFrame#bloco_row { background-color: white; border: 1px dashed #e2e8f0; border-radius: 6px; } QFrame#bloco_row:hover { border: 1px solid #cbd5e1; background-color: #f8fafc; }")
            
            self.layout_timeline.addWidget(bloco_row)
            
        if hasattr(self, "parent") and self.parent() and hasattr(self.parent(), "parent"):
            window = self.parent().parent()
            if hasattr(window, "atualizar_dados_home"):
                window.atualizar_dados_home()

    def _inicio_da_semana(self):
        return self.data_visualizada.addDays(1 - self.data_visualizada.dayOfWeek())

    @staticmethod
    def _cor_do_status(status):
        if "Confirmado" in status or "Realizada" in status:
            return "#10b981"
        if "Atendimento" in status:
            return "#f59e0b"
        if "Faltou" in status or "Cancelada" in status:
            return "#ef4444"
        return "#0284c7"

    def renderizar_grade_semanal(self):
        """Renderiza a semana como uma grade com dias nas colunas e horários nas linhas."""
        self.scroll_agenda.setWidgetResizable(False)
        self.container_timeline.setMinimumWidth(1240)
        self.layout_timeline.setContentsMargins(0, 0, 0, 0)
        self.layout_timeline.setSpacing(0)

        inicio = self._inicio_da_semana()
        filtro_status = self.filtro_status.currentData()
        consultas_semana = []
        grade_semana = QFrame()
        grade_semana.setObjectName("GradeSemanalTabela")
        grade_semana.setStyleSheet(
            "QFrame#GradeSemanalTabela { background: #ffffff; border: 1px solid #aebed0; }"
        )
        layout_semana = QGridLayout(grade_semana)
        layout_semana.setContentsMargins(0, 0, 0, 0)
        layout_semana.setHorizontalSpacing(0)
        layout_semana.setVerticalSpacing(0)
        layout_semana.setColumnMinimumWidth(0, 68)

        canto = QLabel("Horário")
        canto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        canto.setFixedHeight(50)
        canto.setStyleSheet("background: #eef4fa; border: 1px solid #b8c7d9; color: #52657f; font-size: 11px; font-weight: 700;")
        layout_semana.addWidget(canto, 0, 0)

        dados_por_dia = {}
        for deslocamento in range(7):
            data = inicio.addDays(deslocamento)
            chave_data = data.toString("dd/MM/yyyy")
            dados_por_dia[chave_data] = self.db_agendamentos.get(chave_data, {})
            layout_semana.setColumnStretch(deslocamento + 1, 1)
            nome_dia = self.DIAS_SEMANA_PT[data.dayOfWeek() - 1].capitalize()
            titulo_dia = QPushButton(f"{nome_dia}\n{data.day():02d}/{data.month():02d}")
            titulo_dia.setToolTip("Abrir agenda detalhada deste dia")
            titulo_dia.setFixedHeight(50)
            titulo_dia.setStyleSheet(
                "QPushButton { background: #eef4fa; border: 1px solid #b8c7d9; border-radius: 0; "
                "color: #17233a; font-size: 11px; font-weight: 700; padding: 4px; } "
                "QPushButton:hover { background: #e4f3ff; color: #075985; border-color: #76b8e8; }"
            )
            titulo_dia.clicked.connect(lambda checked=False, d=QDate(data): self.abrir_dia_da_semana(d))
            layout_semana.addWidget(titulo_dia, 0, deslocamento + 1)

        horarios = list(self.HORARIOS_GRADE)
        if self.chk_ocultar_disponiveis.isChecked():
            horarios = [
                hora for hora in horarios
                if any(dados_por_dia[chave].get(hora, {}).get("tipo_bloco") == "principal" for chave in dados_por_dia)
            ]

        # A grade precisa de uma altura previsível. Sem isso, em semanas vazias
        # o Qt distribuía o espaço livre antes do cabeçalho e deixava a tabela
        # aparentemente "caída" no final da tela.
        grade_semana.setMinimumHeight(50 + (48 * len(horarios)))
        layout_semana.setRowStretch(len(horarios) + 1, 1)

        for linha, hora in enumerate(horarios, start=1):
            rotulo_hora = QLabel(hora)
            rotulo_hora.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rotulo_hora.setFixedHeight(48)
            rotulo_hora.setStyleSheet("background: #f4f7fb; border: 1px solid #b8c7d9; color: #475569; font-weight: 700;")
            layout_semana.addWidget(rotulo_hora, linha, 0)

            for deslocamento in range(7):
                data = inicio.addDays(deslocamento)
                chave_data = data.toString("dd/MM/yyyy")
                dados = dados_por_dia[chave_data].get(hora, {})
                principal = dados.get("tipo_bloco") == "principal"
                exibir = principal and self._status_corresponde_ao_filtro(dados.get("status", ""), filtro_status)
                celula = QFrame()
                celula.setFixedHeight(48)
                if exibir:
                    cor = self._cor_do_status(dados.get("status", ""))
                    celula.setCursor(Qt.CursorShape.PointingHandCursor)
                    celula.setToolTip("Clique para abrir a agenda detalhada deste dia")
                    celula.setStyleSheet(
                        f"QFrame {{ background: #ffffff; border: 1px solid #b8c7d9; border-left: 4px solid {cor}; }} "
                        "QFrame:hover { background: #edf8ff; }"
                    )
                    celula.mousePressEvent = lambda event, d=QDate(data): self.abrir_dia_da_semana(d)
                    layout_celula = QVBoxLayout(celula)
                    layout_celula.setContentsMargins(6, 3, 6, 3)
                    layout_celula.setSpacing(0)
                    paciente = QLabel(str(dados.get("paciente") or "Paciente"))
                    paciente.setStyleSheet("color: #17233a; font-size: 11px; font-weight: 700; border: none;")
                    procedimento = QLabel(str(dados.get("procedimento") or ""))
                    procedimento.setStyleSheet("color: #64748b; font-size: 9px; border: none;")
                    layout_celula.addWidget(paciente)
                    layout_celula.addWidget(procedimento)
                    consultas_semana.append(dados)
                else:
                    celula.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #c3cfdd; }")
                layout_semana.addWidget(celula, linha, deslocamento + 1)

        self.atualizar_resumo_do_periodo(consultas_semana, "Resumo da semana")
        self.layout_timeline.addWidget(grade_semana)

    def renderizar_visao_mensal(self):
        """Mostra os dias do mês e um resumo clicável das consultas em cada data."""
        self.scroll_agenda.setWidgetResizable(True)
        self.container_timeline.setMinimumWidth(980)
        self.layout_timeline.setContentsMargins(0, 0, 0, 0)
        self.layout_timeline.setSpacing(0)

        filtro_status = self.filtro_status.currentData()
        consultas_mes = []
        grade_mes = QFrame()
        layout_mes = QGridLayout(grade_mes)
        layout_mes.setContentsMargins(0, 0, 0, 0)
        layout_mes.setHorizontalSpacing(2)
        layout_mes.setVerticalSpacing(2)

        for coluna, nome in enumerate(("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")):
            cabecalho = QLabel(nome)
            cabecalho.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cabecalho.setFixedHeight(34)
            cabecalho.setStyleSheet("background: #f5f8fc; color: #52657f; border: 1px solid #d7e2ef; font-size: 11px; font-weight: 700;")
            layout_mes.addWidget(cabecalho, 0, coluna)
            layout_mes.setColumnStretch(coluna, 1)

        primeiro_dia = QDate(self.data_visualizada.year(), self.data_visualizada.month(), 1)
        ultimo_dia = primeiro_dia.addMonths(1).addDays(-1)
        inicio_grade = primeiro_dia.addDays(1 - primeiro_dia.dayOfWeek())

        for indice in range(42):
            data = inicio_grade.addDays(indice)
            linha, coluna = divmod(indice, 7)
            pertence_ao_mes = data.month() == self.data_visualizada.month()
            chave_data = data.toString("dd/MM/yyyy")
            consultas = [
                (hora, dados) for hora, dados in self.db_agendamentos.get(chave_data, {}).items()
                if dados.get("tipo_bloco") == "principal"
                and self._status_corresponde_ao_filtro(dados.get("status", ""), filtro_status)
            ] if pertence_ao_mes else []
            consultas.sort(key=lambda item: item[0])
            consultas_mes.extend(dados for _, dados in consultas)

            celula = QFrame()
            celula.setMinimumHeight(102)
            cor_fundo = "#ffffff" if pertence_ao_mes else "#f8fafc"
            cor_texto = "#17233a" if pertence_ao_mes else "#a7b5c6"
            celula.setStyleSheet(f"QFrame {{ background: {cor_fundo}; border: 1px solid #dfe8f2; }}")
            layout_celula = QVBoxLayout(celula)
            layout_celula.setContentsMargins(6, 5, 6, 5)
            layout_celula.setSpacing(3)

            dia = QPushButton(str(data.day()))
            dia.setCursor(Qt.CursorShape.PointingHandCursor)
            dia.setToolTip("Abrir agenda deste dia")
            dia.setFixedSize(28, 24)
            dia.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {cor_texto}; padding: 0; font-weight: 700; }} "
                "QPushButton:hover { background: #e4f3ff; color: #075985; border-radius: 5px; }"
            )
            dia.clicked.connect(lambda checked=False, d=QDate(data): self.abrir_dia_da_semana(d))
            layout_celula.addWidget(dia, alignment=Qt.AlignmentFlag.AlignLeft)

            for hora, dados in consultas[:2]:
                cor = self._cor_do_status(dados.get("status", ""))
                consulta = QPushButton(f"{hora}  {str(dados.get('paciente') or 'Paciente')}")
                consulta.setCursor(Qt.CursorShape.PointingHandCursor)
                consulta.setToolTip("Abrir agenda detalhada deste dia")
                consulta.setStyleSheet(
                    f"QPushButton {{ text-align: left; min-height: 0; padding: 3px 5px; background: #ffffff; color: #334155; "
                    f"border: 1px solid #d7e2ef; border-left: 3px solid {cor}; border-radius: 4px; font-size: 10px; }} "
                    "QPushButton:hover { background: #edf8ff; border-color: #76b8e8; }"
                )
                consulta.clicked.connect(lambda checked=False, d=QDate(data): self.abrir_dia_da_semana(d))
                layout_celula.addWidget(consulta)
            if len(consultas) > 2:
                restante = QLabel(f"+ {len(consultas) - 2} consulta(s)")
                restante.setStyleSheet("color: #0284c7; font-size: 10px; border: none;")
                layout_celula.addWidget(restante)
            layout_celula.addStretch()
            layout_mes.addWidget(celula, linha + 1, coluna)

        self.atualizar_resumo_do_periodo(consultas_mes, "Resumo do mês")
        self.layout_timeline.addWidget(grade_mes)

    def renderizar_visao_semanal(self):
        """Renderiza uma semana compacta e mantém o dia detalhado disponível."""
        self.scroll_agenda.setWidgetResizable(False)
        self.container_timeline.setMinimumWidth(1120)
        self.layout_timeline.setContentsMargins(0, 0, 0, 0)
        self.layout_timeline.setSpacing(0)

        inicio = self._inicio_da_semana()
        filtro_status = self.filtro_status.currentData()
        consultas_semana = []

        grade_semana = QFrame()
        grade_semana.setStyleSheet("QFrame#GradeSemanal { background: transparent; }")
        grade_semana.setObjectName("GradeSemanal")
        layout_semana = QHBoxLayout(grade_semana)
        layout_semana.setContentsMargins(0, 0, 0, 0)
        layout_semana.setSpacing(10)

        for deslocamento in range(7):
            data = inicio.addDays(deslocamento)
            chave_data = data.toString("dd/MM/yyyy")
            consultas_dia = [
                (hora, dados)
                for hora, dados in self.db_agendamentos.get(chave_data, {}).items()
                if dados.get("tipo_bloco") == "principal"
                and self._status_corresponde_ao_filtro(dados.get("status", ""), filtro_status)
            ]
            consultas_dia.sort(key=lambda item: item[0])
            consultas_semana.extend(dados for _, dados in consultas_dia)

            coluna_dia = QFrame()
            coluna_dia.setFixedWidth(150)
            coluna_dia.setStyleSheet(
                "QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }"
            )
            layout_dia = QVBoxLayout(coluna_dia)
            layout_dia.setContentsMargins(9, 9, 9, 9)
            layout_dia.setSpacing(8)

            nome_dia = self.DIAS_SEMANA_PT[data.dayOfWeek() - 1].capitalize()
            titulo_dia = QPushButton(f"{nome_dia}\n{data.day():02d}/{data.month():02d}")
            titulo_dia.setToolTip("Abrir agenda detalhada deste dia")
            titulo_dia.setStyleSheet(
                "QPushButton { color: #0f172a; background: #f8fafc; border: none; border-radius: 6px; "
                "padding: 7px; font-size: 12px; font-weight: bold; } "
                "QPushButton:hover { background: #e0f2fe; color: #0369a1; }"
            )
            titulo_dia.clicked.connect(lambda checked=False, d=QDate(data): self.abrir_dia_da_semana(d))
            layout_dia.addWidget(titulo_dia)

            if not consultas_dia:
                vazio = QLabel("Sem consultas")
                vazio.setWordWrap(True)
                vazio.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                vazio.setStyleSheet("color: #94a3b8; font-size: 11px; border: none; padding: 12px 4px;")
                layout_dia.addWidget(vazio)
            else:
                for hora, dados in consultas_dia:
                    cor = self._cor_do_status(dados.get("status", ""))
                    card = QFrame()
                    card.setStyleSheet(
                        f"QFrame {{ background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid {cor}; "
                        "border-radius: 5px; }}"
                    )
                    layout_card = QVBoxLayout(card)
                    layout_card.setContentsMargins(7, 6, 7, 6)
                    layout_card.setSpacing(2)
                    lbl_hora = QLabel(hora)
                    lbl_hora.setStyleSheet(f"color: {cor}; font-size: 11px; font-weight: bold; border: none;")
                    lbl_paciente = QLabel(dados.get("paciente", ""))
                    lbl_paciente.setWordWrap(True)
                    lbl_paciente.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: bold; border: none;")
                    lbl_procedimento = QLabel(dados.get("procedimento", ""))
                    lbl_procedimento.setWordWrap(True)
                    lbl_procedimento.setStyleSheet("color: #64748b; font-size: 10px; border: none;")
                    layout_card.addWidget(lbl_hora)
                    layout_card.addWidget(lbl_paciente)
                    layout_card.addWidget(lbl_procedimento)
                    layout_dia.addWidget(card)
            layout_dia.addStretch()
            layout_semana.addWidget(coluna_dia)

        self.atualizar_resumo_do_periodo(consultas_semana, "Resumo da semana")
        self.layout_timeline.addWidget(grade_semana)

    def abrir_dia_da_semana(self, data):
        self.data_visualizada = data
        self.modo_visualizacao.setCurrentIndex(0)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def alterar_modo_visualizacao(self):
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def navegar_dia_anterior(self):
        modo = self.modo_visualizacao.currentData()
        self.data_visualizada = self.data_visualizada.addMonths(-1) if modo == "mes" else self.data_visualizada.addDays(-7 if modo == "semana" else -1)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def navegar_proximo_dia(self):
        modo = self.modo_visualizacao.currentData()
        self.data_visualizada = self.data_visualizada.addMonths(1) if modo == "mes" else self.data_visualizada.addDays(7 if modo == "semana" else 1)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def ir_para_hoje(self):
        self.data_visualizada = QDate.currentDate()
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()

    def atualizar_visualizacao_data(self):
        if self.modo_visualizacao.currentData() == "semana":
            inicio = self._inicio_da_semana()
            fim = inicio.addDays(6)
            if inicio.month() == fim.month():
                periodo = f"{inicio.day()} a {fim.day()} de {self.MESES_PT[inicio.month() - 1]}"
            else:
                periodo = (
                    f"{inicio.day()} de {self.MESES_PT[inicio.month() - 1]} a "
                    f"{fim.day()} de {self.MESES_PT[fim.month() - 1]}"
                )
            self.btn_data_central.setText(f"Semana: {periodo} de {fim.year()}")
            return
        if self.modo_visualizacao.currentData() == "mes":
            mes = self.MESES_PT[self.data_visualizada.month() - 1]
            self.btn_data_central.setText(f"{mes.capitalize()} de {self.data_visualizada.year()}")
            return
        mes = self.MESES_PT[self.data_visualizada.month() - 1]
        dia_semana = self.DIAS_SEMANA_PT[self.data_visualizada.dayOfWeek() - 1]
        self.btn_data_central.setText(
            f"{self.data_visualizada.day()} de {mes} de {self.data_visualizada.year()} · {dia_semana}"
        )

    def _estado_formulario_atual(self):
        return (
            self.input_paciente.lineEdit().text(), self.input_hora.currentText(),
            self.input_duracao.currentText(), self.input_procedimento.currentText(),
            self.input_status.currentText(), self.input_obs.text(),
        )

    def _conectar_monitoramento_formulario(self):
        """Distingue digitação real de preenchimentos automáticos da tela."""
        self.input_paciente.lineEdit().textEdited.connect(self._registrar_edicao_do_usuario)
        self.input_hora.activated.connect(self._registrar_edicao_do_usuario)
        self.input_duracao.activated.connect(self._registrar_edicao_do_usuario)
        self.input_procedimento.activated.connect(self._registrar_edicao_do_usuario)
        self.input_status.activated.connect(self._registrar_edicao_do_usuario)
        self.input_obs.textEdited.connect(self._registrar_edicao_do_usuario)

    def _registrar_edicao_do_usuario(self, *_):
        self._formulario_editado_pelo_usuario = True

    def _marcar_formulario_salvo(self):
        self._estado_formulario_salvo = self._estado_formulario_atual()
        self._formulario_editado_pelo_usuario = False

    def tem_alteracoes_nao_salvas(self):
        return (
            self._formulario_editado_pelo_usuario
            and self._estado_formulario_atual() != getattr(self, "_estado_formulario_salvo", None)
        )

    def descartar_alteracoes_nao_salvas(self):
        self.input_paciente.setEditText("")
        self.input_hora.setCurrentText("08:00")
        self.input_duracao.setCurrentIndex(1)
        self.input_procedimento.setCurrentIndex(0)
        self.input_status.setCurrentIndex(0)
        self.input_obs.clear()
        self._retorno_em_agendamento = None
        self._marcar_formulario_salvo()

    def cancelar_retorno_em_agendamento(self):
        """Desvincula um retorno se o usuário sair da Agenda sem confirmar."""
        self._retorno_em_agendamento = None

    def preencher_agendamento_retorno(self, retorno):
        """Preenche a Agenda a partir de um retorno pendente do Painel Principal."""
        if not retorno:
            return
        data_prevista = QDate.fromString(str(retorno.get("data_prevista") or ""), "yyyy-MM-dd")
        if data_prevista.isValid():
            self.data_visualizada = data_prevista
            self.atualizar_visualizacao_data()
        self.carregar_lista_pacientes_combobox()
        self.input_paciente.setEditText(str(retorno.get("paciente_nome") or ""))
        indice_retorno = self.input_procedimento.findText("Retorno")
        if indice_retorno >= 0:
            self.input_procedimento.setCurrentIndex(indice_retorno)
        motivo = str(retorno.get("motivo") or "").strip()
        self.input_obs.setText(f"Retorno: {motivo}" if motivo else "Retorno programado")
        self._retorno_em_agendamento = retorno
        self.renderizar_timeline_calendario()
        self._marcar_formulario_salvo()

    def abrir_consulta_por_data_hora(self, consulta):
        """Posiciona a Agenda no compromisso escolhido no Painel Principal."""
        data = QDate.fromString(str(consulta.get("data") or ""), "dd/MM/yyyy")
        if data.isValid():
            self.data_visualizada = data
        self.modo_visualizacao.setCurrentIndex(0)
        hora = str(consulta.get("horario") or "")
        if hora and self.input_hora.findText(hora) >= 0:
            self.input_hora.setCurrentText(hora)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()
        self._marcar_formulario_salvo()

    def abrir_data_do_retorno(self, data_prevista):
        """Abre a visão diária na data já definida para um retorno."""
        data = QDate.fromString(str(data_prevista or ""), "yyyy-MM-dd")
        if not data.isValid():
            return
        self.abrir_dia_da_semana(data)
        self._marcar_formulario_salvo()

    @staticmethod
    def _status_corresponde_ao_filtro(status, filtro):
        if not filtro:
            return True
        return any(termo in status for termo in filtro.split("|"))

    def atualizar_resumo_do_dia(self, agendamentos_do_dia):
        """Mostra um resumo rápido sem fazer uma nova consulta ao Supabase."""
        consultas = [
            dados for dados in agendamentos_do_dia.values()
            if dados.get("tipo_bloco") == "principal"
        ]
        self.atualizar_resumo_do_periodo(consultas, "Agenda do dia")

    def revisar_resposta_whatsapp(self, hora):
        """Mostra a resposta recebida e permite resolvê-la sem sair da Agenda."""
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        alerta = self.alertas_respostas_whatsapp.get((str_data, hora))
        if not alerta:
            return

        dialogo = QMessageBox(self)
        dialogo.setWindowTitle("Resposta do paciente")
        dialogo.setIcon(QMessageBox.Icon.Information)
        dialogo.setText("O paciente enviou uma resposta que precisa ser tratada.")
        dialogo.setInformativeText(str(alerta.get("conteudo") or "(sem texto)"))
        btn_confirmar = dialogo.addButton("Confirmar consulta", QMessageBox.ButtonRole.AcceptRole)
        btn_cancelar = dialogo.addButton("Cancelar consulta", QMessageBox.ButtonRole.DestructiveRole)
        btn_tratar = dialogo.addButton("Marcar como tratada", QMessageBox.ButtonRole.ActionRole)
        dialogo.addButton("Fechar", QMessageBox.ButtonRole.RejectRole)
        dialogo.exec()

        escolhido = dialogo.clickedButton()
        if escolhido is btn_confirmar:
            self.atualizar_status_agendamento(hora, "✅ Confirmado")
        elif escolhido is btn_cancelar:
            self.atualizar_status_agendamento(hora, "🚫 Cancelada")
        elif escolhido is btn_tratar:
            pass
        else:
            return

        try:
            self.db_gerenciador.supabase.table("respostas_whatsapp").update({
                "status": "tratada",
                "tratada_em": QDateTime.currentDateTimeUtc().toString(Qt.DateFormat.ISODate),
            }).eq("id", alerta["id"]).eq(
                "consultorio_id", self.db_gerenciador.consultorio_id
            ).execute()
            self.alertas_respostas_whatsapp.pop((str_data, hora), None)
            self.renderizar_timeline_calendario()
        except Exception as erro:
            print(f"Erro ao concluir alerta de resposta ({type(erro).__name__}).")

    def adicionar_acoes_rapidas_consulta(self, layout, hora, status):
        """Exibe apenas as próximas ações válidas, sem exigir um menu de status."""
        acoes = QWidget()
        acoes_layout = QHBoxLayout(acoes)
        acoes_layout.setContentsMargins(0, 0, 0, 0)
        acoes_layout.setSpacing(8)
        acoes_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        acoes.setFixedHeight(36)

        def adicionar_botao(texto, variante, novo_status, dica):
            botao = QPushButton(texto)
            botao.setToolTip(dica)
            botao.setFixedHeight(34)
            botao.setMinimumWidth(92)
            botao.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            definir_variante(botao, variante)
            # O cartão da consulta possui estilo próprio. Declarar também a
            # aparência local da ação evita que o texto branco do botão
            # primário fique invisível quando o Qt propaga esse estilo.
            estilos = {
                "primary": (
                    "QPushButton { background: #0284c7; color: #ffffff; border: 1px solid #0284c7; "
                    "border-radius: 7px; font-weight: 700; padding: 5px 10px; } "
                    "QPushButton:hover { background: #0369a1; border-color: #0369a1; }"
                ),
                "secondary": (
                    "QPushButton { background: #e8f4ff; color: #075985; border: 1px solid #9acdf1; "
                    "border-radius: 7px; font-weight: 700; padding: 5px 10px; } "
                    "QPushButton:hover { background: #d7edff; border-color: #58ace3; }"
                ),
                "danger": (
                    "QPushButton { background: #fff1f2; color: #be123c; border: 1px solid #fda4af; "
                    "border-radius: 7px; font-weight: 700; padding: 5px 10px; } "
                    "QPushButton:hover { background: #ffe4e6; border-color: #fb7185; }"
                ),
            }
            botao.setStyleSheet(estilos[variante])
            botao.clicked.connect(
                lambda checked=False, h=hora, s=novo_status: self.atualizar_status_agendamento(h, s)
            )
            acoes_layout.addWidget(botao)

        if "Agendado" in status:
            adicionar_botao("Confirmar", "primary", "✅ Confirmado", "Registrar que o paciente confirmou presença")
            btn_reagendar = QPushButton("Reagendar")
            btn_reagendar.setToolTip("Escolher uma nova data e horário sem redigitar a consulta")
            btn_reagendar.setFixedHeight(34)
            btn_reagendar.setMinimumWidth(98)
            btn_reagendar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            definir_variante(btn_reagendar, "secondary")
            btn_reagendar.clicked.connect(lambda checked=False, h=hora: self.abrir_reagendamento_guiado(h))
            acoes_layout.addWidget(btn_reagendar)
            adicionar_botao("Cancelar", "danger", "🚫 Cancelada", "Cancelar esta consulta")
        elif "Confirmado" in status:
            adicionar_botao("Iniciar", "secondary", "🏥 Em Atendimento", "Marcar que o atendimento começou")
            btn_reagendar = QPushButton("Reagendar")
            btn_reagendar.setToolTip("Escolher uma nova data e horário sem redigitar a consulta")
            btn_reagendar.setFixedHeight(34)
            btn_reagendar.setMinimumWidth(98)
            btn_reagendar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            definir_variante(btn_reagendar, "secondary")
            btn_reagendar.clicked.connect(lambda checked=False, h=hora: self.abrir_reagendamento_guiado(h))
            acoes_layout.addWidget(btn_reagendar)
            adicionar_botao("Cancelar", "danger", "🚫 Cancelada", "Cancelar esta consulta")
        elif "Atendimento" in status:
            adicionar_botao("Concluir", "primary", "✅ Realizada", "Concluir o atendimento")
            adicionar_botao("Cancelar", "danger", "🚫 Cancelada", "Cancelar esta consulta")
        elif "Realizada" in status:
            status_final = QLabel("Concluída")
            status_final.setStyleSheet("color: #047857; font-size: 12px; font-weight: 700; border: none;")
            status_final.setFixedHeight(36)
            status_final.setMinimumWidth(64)
            status_final.setAlignment(Qt.AlignmentFlag.AlignCenter)
            acoes_layout.addWidget(status_final)
        elif "Cancelada" in status:
            status_final = QLabel("Cancelada")
            status_final.setStyleSheet("color: #b91c1c; font-size: 12px; font-weight: 700; border: none;")
            acoes_layout.addWidget(status_final)
        elif "Faltou" in status:
            status_final = QLabel("Não compareceu")
            status_final.setStyleSheet("color: #b91c1c; font-size: 12px; font-weight: 700; border: none;")
            acoes_layout.addWidget(status_final)

        consulta_ja_passou = QDateTime(
            self.data_visualizada, QTime.fromString(hora, "hh:mm")
        ) < QDateTime.currentDateTime()
        if (
            consulta_ja_passou
            and not any(termo in status for termo in ("Realizada", "Cancelada", "Faltou"))
        ):
            adicionar_botao("Faltou", "danger", "❌ Faltou", "Marcar que o paciente não compareceu")

        layout.addWidget(acoes)

    def atualizar_resumo_do_periodo(self, consultas, titulo):
        self.lbl_titulo_resumo.setText(titulo)
        total = len(consultas)
        confirmadas = sum("Confirmado" in dados.get("status", "") for dados in consultas)
        pendentes = sum("Agendado" in dados.get("status", "") for dados in consultas)
        realizadas = sum("Realizada" in dados.get("status", "") for dados in consultas)
        self.lbl_resumo_agenda.setText(
            f"{total} consulta(s) · {confirmadas} confirmada(s) · "
            f"{pendentes} pendente(s) · {realizadas} realizada(s)"
        )

    def _paciente_do_slot(self, str_data, hora):
        dados = self.db_agendamentos[str_data][hora]
        return dados.get("paciente", "outro paciente")

    def enviar_lembrete_whatsapp(self, hora):
        """Prepara um lembrete manual usando o modelo salvo nas Configurações."""
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        dados = self.db_agendamentos.get(str_data, {}).get(hora)
        if not dados or dados.get("tipo_bloco") != "principal":
            return

        paciente = str(dados.get("paciente") or "").strip()
        telefone = self.db_gerenciador.obter_telefone_paciente_por_nome(paciente) or ""
        numero = "".join(caractere for caractere in telefone if caractere.isdigit())
        if not numero:
            QMessageBox.warning(
                self,
                "Telefone não informado",
                f"O paciente {paciente} não possui um telefone cadastrado para receber o lembrete.",
            )
            return
        if len(numero) <= 11:
            numero = "55" + numero

        modelo = self.db_gerenciador.obter_configuracao(
            "whatsapp_mensagem_lembrete", MENSAGEM_LEMBRETE_CONSULTA_PADRAO
        )
        profissional = self.db_gerenciador.obter_nome_profissional() or "a equipe da clínica"
        mensagem = str(modelo or MENSAGEM_LEMBRETE_CONSULTA_PADRAO)
        valores = {
            "{paciente}": paciente.title(),
            "{profissional}": profissional,
            "{data}": str_data,
            "{hora}": hora,
            "{procedimento}": str(dados.get("procedimento") or "Consulta"),
        }
        for marcador, valor in valores.items():
            mensagem = mensagem.replace(marcador, valor)
        url = f"https://web.whatsapp.com/send?phone={numero}&text={urllib.parse.quote(mensagem)}"
        try:
            if not webbrowser.open(url, new=2):
                raise RuntimeError("O navegador padrão não aceitou a abertura do link")
        except Exception:
            QMessageBox.warning(
                self,
                "WhatsApp não aberto",
                "Não foi possível abrir o WhatsApp no navegador. Verifique o navegador padrão e tente novamente.",
            )

    def _retorno_pendente_do_horario(self, hora):
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        dados = self.db_agendamentos.get(str_data, {}).get(hora, {})
        chave = self._chave_nome_paciente(dados.get("paciente"))
        return dados, self.retornos_pendentes_por_paciente.get(chave)

    def _escolher_data_retorno_consulta(self):
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Agendar retorno")
        dialogo.setMinimumWidth(420)
        layout = QVBoxLayout(dialogo)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Escolha a data prevista para o retorno:"))

        calendario = QCalendarWidget()
        calendario.setGridVisible(True)
        calendario.setMinimumDate(QDate.currentDate())
        calendario.setSelectedDate(QDate.currentDate().addDays(30))
        layout.addWidget(calendario)

        botoes = QHBoxLayout()
        botoes.addStretch()
        cancelar = QPushButton("Cancelar")
        continuar = QPushButton("Continuar para a Agenda")
        definir_variante(cancelar, "secondary")
        definir_variante(continuar, "primary")
        cancelar.clicked.connect(dialogo.reject)
        continuar.clicked.connect(dialogo.accept)
        botoes.addWidget(cancelar)
        botoes.addWidget(continuar)
        layout.addLayout(botoes)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return ""
        return calendario.selectedDate().toString("yyyy-MM-dd")

    def agendar_retorno_da_consulta(self, hora):
        """Escolhe a data e prepara na Agenda a pendência criada ao concluir a consulta."""
        dados, retorno = self._retorno_pendente_do_horario(hora)
        if not retorno:
            QMessageBox.information(self, "Retorno já tratado", "Esta consulta não possui retorno pendente.")
            return
        data_prevista = self._escolher_data_retorno_consulta()
        if not data_prevista:
            return
        if not self.db_gerenciador.definir_data_retorno(retorno.get("id"), data_prevista):
            QMessageBox.warning(self, "Data não salva", "Não foi possível preparar o retorno agora.")
            return
        retorno["data_prevista"] = data_prevista
        retorno["paciente_nome"] = str(dados.get("paciente") or retorno.get("paciente_nome") or "")
        self.preencher_agendamento_retorno(retorno)

    def marcar_sem_retorno_da_consulta(self, hora):
        """Encerra a pendência quando a equipe confirma que o paciente não retornará."""
        dados, retorno = self._retorno_pendente_do_horario(hora)
        if not retorno:
            return
        resposta = QMessageBox.question(
            self,
            "Confirmar ausência de retorno",
            f"Confirmar que {str(dados.get('paciente') or 'o paciente')} não retornará?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        if not self.db_gerenciador.atualizar_status_retorno(retorno.get("id"), "Não retornou"):
            QMessageBox.warning(self, "Retorno não atualizado", "Não foi possível concluir esta decisão agora.")
            return
        chave = self._chave_nome_paciente(dados.get("paciente"))
        self.retornos_pendentes_por_paciente.pop(chave, None)
        self._atualizar_home_apos_retorno()
        self.renderizar_timeline_calendario()

    def _atualizar_home_apos_retorno(self):
        janela = getattr(self, "window_principal", None) or self.window()
        tela_home = getattr(janela, "screen_home", None)
        if tela_home and hasattr(tela_home, "renderizar_lista_pastas"):
            tela_home.renderizar_lista_pastas(force=True)

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
            "retorno_id": self._retorno_em_agendamento.get("id") if self._retorno_em_agendamento else None,
            "slots_vinculados": horarios_a_reservar
        }
        
        self.db_agendamentos[str_data][hora_inicial_str] = bloco_principal
        if not self.salvar_agendamento_no_db(str_data, hora_inicial_str, bloco_principal):
            del self.db_agendamentos[str_data][hora_inicial_str]
            self.input_paciente.blockSignals(False)
            QMessageBox.critical(
                self,
                "Consulta não salva",
                mensagem_erro_usuario("salvar a consulta") +
                " A consulta não foi registrada e não ficará apenas na memória.",
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
                "retorno_id": None,
                "slots_vinculados": []
            }
            self.db_agendamentos[str_data][slot_sequencia] = bloco_continua
            self.salvar_agendamento_no_db(str_data, slot_sequencia, bloco_continua)

        if self._retorno_em_agendamento and hasattr(self.db_gerenciador, "atualizar_status_retorno"):
            retorno_atualizado = self.db_gerenciador.atualizar_status_retorno(
                self._retorno_em_agendamento.get("id"), "Agendado"
            )
            if retorno_atualizado:
                chave_retorno = self._chave_nome_paciente(
                    self._retorno_em_agendamento.get("paciente_nome") or paciente
                )
                self.retornos_pendentes_por_paciente.pop(chave_retorno, None)
                self._atualizar_home_apos_retorno()
                self._retorno_em_agendamento = None
        
        self.input_paciente.blockSignals(False)
        self.atualizar_lista_sugestoes(self.lista_pacientes_disponiveis)
        self.input_obs.clear()
        self._marcar_formulario_salvo()

        ultimo_slot_ocupado = QTime.fromString(horarios_a_reservar[-1], "hh:mm")
        proximo_slot = ultimo_slot_ocupado.addSecs(30 * 60).toString("hh:mm")
        if proximo_slot in self.HORARIOS_GRADE:
            self.input_hora.setCurrentText(proximo_slot)
        
        self.renderizar_timeline_calendario()

    def _slots_para_horario(self, hora_inicial, duracao_txt):
        """Retorna os blocos de 30 minutos ocupados pela duração escolhida."""
        inicio = QTime.fromString(hora_inicial, "hh:mm")
        if not inicio.isValid():
            return []
        minutos = 0
        slots = []
        while minutos < self.converter_duracao_minutos(duracao_txt):
            slots.append(inicio.addSecs(minutos * 60).toString("hh:mm"))
            minutos += 30
        return slots

    def _horarios_disponiveis_reagendamento(self, data, dados):
        chave_data = data.toString("dd/MM/yyyy")
        ocupados = self.db_agendamentos.get(chave_data, {})
        horarios = []
        for hora in self.HORARIOS_GRADE:
            slots = self._slots_para_horario(hora, dados.get("duracao_txt", "30 minutos"))
            if not slots or any(slot not in self.HORARIOS_GRADE for slot in slots):
                continue
            if QDateTime(data, QTime.fromString(hora, "hh:mm")) < QDateTime.currentDateTime():
                continue
            if all(slot not in ocupados for slot in slots):
                horarios.append(hora)
        return horarios

    def abrir_reagendamento_guiado(self, hora):
        """Permite escolher um novo horário preservando os dados da consulta atual."""
        data_original = self.data_visualizada.toString("dd/MM/yyyy")
        dados = self.db_agendamentos.get(data_original, {}).get(hora)
        if not dados or dados.get("tipo_bloco") != "principal":
            return

        dialogo = QDialog(self)
        dialogo.setWindowTitle("Reagendar consulta")
        dialogo.setMinimumWidth(390)
        dialogo.setStyleSheet(
            "QDialog { background: #ffffff; } QLabel { color: #334155; font-size: 13px; } "
            "QCalendarWidget QWidget { background: #ffffff; color: #0f172a; } "
            "QCalendarWidget QAbstractItemView:enabled { background: #ffffff; color: #0f172a; "
            "selection-background-color: #0284c7; selection-color: #ffffff; }"
        )
        layout = QVBoxLayout(dialogo)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        titulo = QLabel(f"Reagendar {dados.get('paciente', '')}")
        titulo.setStyleSheet("font-size: 16px; color: #0f172a; font-weight: 700;")
        layout.addWidget(titulo)
        layout.addWidget(QLabel(
            f"Consulta atual: {data_original} às {hora} · {dados.get('procedimento', 'Consulta')}"
        ))
        layout.addWidget(QLabel("Escolha a nova data:"))

        calendario = QCalendarWidget()
        calendario.setMinimumDate(QDate.currentDate())
        data_padrao = self.data_visualizada.addDays(1)
        if data_padrao < QDate.currentDate():
            data_padrao = QDate.currentDate()
        calendario.setSelectedDate(data_padrao)
        layout.addWidget(calendario)

        layout.addWidget(QLabel("Horários disponíveis:"))
        combo_horario = QComboBox()
        layout.addWidget(combo_horario)
        aviso_horario = QLabel()
        aviso_horario.setStyleSheet("color: #b45309; font-size: 12px;")
        layout.addWidget(aviso_horario)

        def atualizar_horarios():
            combo_horario.clear()
            horarios = self._horarios_disponiveis_reagendamento(calendario.selectedDate(), dados)
            combo_horario.addItems(horarios)
            aviso_horario.setText("" if horarios else "Não há horários disponíveis nesta data.")

        calendario.selectionChanged.connect(atualizar_horarios)
        atualizar_horarios()

        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        definir_variante(btn_cancelar, "secondary")
        btn_cancelar.clicked.connect(dialogo.reject)
        botoes.addWidget(btn_cancelar)
        btn_confirmar = QPushButton("Confirmar reagendamento")
        definir_variante(btn_confirmar, "primary")
        btn_confirmar.setEnabled(combo_horario.count() > 0)
        combo_horario.model().rowsInserted.connect(
            lambda *_: btn_confirmar.setEnabled(combo_horario.count() > 0)
        )
        calendario.selectionChanged.connect(
            lambda: btn_confirmar.setEnabled(combo_horario.count() > 0)
        )
        btn_confirmar.clicked.connect(dialogo.accept)
        botoes.addWidget(btn_confirmar)
        layout.addLayout(botoes)

        if dialogo.exec() != QDialog.DialogCode.Accepted or not combo_horario.currentText():
            return
        self.confirmar_reagendamento(
            data_original, hora, dados, calendario.selectedDate(), combo_horario.currentText()
        )

    def confirmar_reagendamento(self, data_original, hora_original, dados_originais, nova_data, nova_hora):
        """Cria primeiro a nova consulta e remove a antiga somente após sucesso."""
        nova_data_txt = nova_data.toString("dd/MM/yyyy")
        novos_slots = self._slots_para_horario(nova_hora, dados_originais.get("duracao_txt", "30 minutos"))
        ocupados = self.db_agendamentos.get(nova_data_txt, {})
        if not novos_slots or any(slot in ocupados for slot in novos_slots):
            QMessageBox.warning(self, "Horário indisponível", "Esse horário acabou de ser ocupado. Escolha outro.")
            return

        observacao_anterior = str(dados_originais.get("observacao") or "").strip()
        historico = f"Reagendado de {data_original} às {hora_original}."
        nova_observacao = f"{observacao_anterior} {historico}".strip()
        novo_principal = {
            **dados_originais,
            "tipo_bloco": "principal",
            "status": "🕒 Agendado",
            "observacao": nova_observacao,
            "slots_vinculados": novos_slots,
        }

        self.db_agendamentos.setdefault(nova_data_txt, {})[nova_hora] = novo_principal
        criados = [nova_hora]
        if not self.salvar_agendamento_no_db(nova_data_txt, nova_hora, novo_principal):
            del self.db_agendamentos[nova_data_txt][nova_hora]
            QMessageBox.critical(self, "Reagendamento não salvo", "Não foi possível salvar o novo horário.")
            return

        for slot in novos_slots[1:]:
            continuacao = {
                "tipo_bloco": "continua",
                "paciente": dados_originais.get("paciente", ""),
                "hora_origem": nova_hora,
                "status": "",
                "procedimento": "",
                "duracao_txt": "",
                "observacao": "",
                "retorno_id": None,
                "slots_vinculados": [],
            }
            self.db_agendamentos[nova_data_txt][slot] = continuacao
            criados.append(slot)
            if not self.salvar_agendamento_no_db(nova_data_txt, slot, continuacao):
                for criado in criados:
                    self.db_agendamentos[nova_data_txt].pop(criado, None)
                    self.remover_agendamento_do_db(nova_data_txt, criado)
                QMessageBox.critical(self, "Reagendamento não salvo", "Não foi possível reservar todos os horários necessários.")
                return

        # A auditoria já registra a remoção do horário antigo; a nova observação
        # preserva a origem do reagendamento para consulta da equipe.
        for slot in dados_originais.get("slots_vinculados", [hora_original]):
            self.db_agendamentos.get(data_original, {}).pop(slot, None)
            self.remover_agendamento_do_db(data_original, slot)

        if dados_originais.get("retorno_id") and hasattr(self.db_gerenciador, "atualizar_status_retorno"):
            self.db_gerenciador.atualizar_status_retorno(dados_originais["retorno_id"], "Agendado")

        self.data_visualizada = nova_data
        self.modo_visualizacao.setCurrentIndex(0)
        self.atualizar_visualizacao_data()
        self.renderizar_timeline_calendario()
        QMessageBox.information(self, "Consulta reagendada", "O novo horário foi salvo e o agendamento anterior foi liberado.")

    def atualizar_status_agendamento(self, hora, novo_status):
        """Atualiza o status sem alterar o horário ou os dados da consulta."""
        str_data = self.data_visualizada.toString("dd/MM/yyyy")
        dados = self.db_agendamentos.get(str_data, {}).get(hora)
        if not dados or dados.get("tipo_bloco") != "principal":
            return
        if dados.get("status") == novo_status:
            return
        if not self._salvar_status_agendamento_no_db(str_data, hora, novo_status):
            QMessageBox.warning(self, "Status não atualizado", "Não foi possível salvar o novo status da consulta.")
            return
        dados["status"] = novo_status
        self._sincronizar_retorno_da_consulta(dados, novo_status, str_data, hora)
        self.renderizar_timeline_calendario()

    def _salvar_status_agendamento_no_db(self, data, hora, novo_status):
        """Atualiza apenas a coluna modificada pela ação rápida."""
        if not self.db_gerenciador.supabase or self.db_gerenciador.consultorio_id is None:
            return False
        try:
            self.db_gerenciador.supabase.table("agenda").update({
                "status": novo_status,
            }).eq("consultorio_id", int(self.db_gerenciador.consultorio_id)).eq(
                "data", data
            ).eq("horario", hora).execute()
            return True
        except Exception as erro:
            registrar_falha("atualizar status do agendamento", erro)
            self._ultimo_erro_agenda = type(erro).__name__
            return False

    def _sincronizar_retorno_da_consulta(self, dados, status_consulta, data_consulta="", hora_consulta=""):
        """Mantem o retorno vinculado coerente com o destino da consulta."""
        retorno_id = dados.get("retorno_id")
        if not retorno_id:
            # Consultas comuns concluídas geram uma pendência para a equipe decidir
            # se o paciente terá retorno. Uma consulta de retorno não gera outra.
            procedimento = str(dados.get("procedimento") or "").strip().lower()
            if (
                "Realizada" in status_consulta
                and procedimento != "retorno"
                and hasattr(self.db_gerenciador, "criar_retorno_pendente_da_consulta")
            ):
                retorno_criado = self.db_gerenciador.criar_retorno_pendente_da_consulta(
                    str(dados.get("paciente") or ""), data_consulta, hora_consulta
                )
                if not retorno_criado:
                    QMessageBox.warning(
                        self,
                        "Retorno não criado",
                        "A consulta foi marcada como realizada, mas não foi possível criar o retorno pendente. "
                        "Verifique se a atualização de retornos foi executada no Supabase.",
                    )
                elif retorno_criado.get("status") == "Pendente":
                    chave = self._chave_nome_paciente(dados.get("paciente"))
                    self.retornos_pendentes_por_paciente[chave] = retorno_criado
                    self._atualizar_home_apos_retorno()
            return
        if not hasattr(self.db_gerenciador, "atualizar_status_retorno"):
            return
        if "Realizada" in status_consulta:
            novo_status = "Concluído"
        elif "Cancelada" in status_consulta or "Faltou" in status_consulta:
            novo_status = "Pendente"
        else:
            novo_status = "Agendado"
        self.db_gerenciador.atualizar_status_retorno(retorno_id, novo_status)

    def abrir_ficha_da_consulta(self, hora):
        """Localiza o paciente da consulta realizada e abre uma nova ficha."""
        if getattr(self.db_gerenciador, "obter_papel_atual", lambda: "proprietario")() == "secretaria":
            QMessageBox.information(self, "Acesso restrito", "A secretária não possui acesso a fichas clínicas.")
            return
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
            janela = getattr(self, "window_principal", None) or self.window()
            if janela and hasattr(janela, "abrir_nova_ficha_para_paciente"):
                janela.abrir_nova_ficha_para_paciente(resposta.data[0]["id"])
            else:
                QMessageBox.warning(
                    self,
                    "Navegação indisponível",
                    "Não foi possível abrir a tela de fichas agora. Reinicie o Prontu e tente novamente.",
                )
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

        # Uma consulta removida deixa o retorno disponível para novo agendamento.
        if dados.get("retorno_id") and hasattr(self.db_gerenciador, "atualizar_status_retorno"):
            self.db_gerenciador.atualizar_status_retorno(dados["retorno_id"], "Pendente")

        # Deleta todos os slots associados a essa consulta
        for slot in dados["slots_vinculados"]:
            if slot in self.db_agendamentos[str_data]:
                del self.db_agendamentos[str_data][slot]
                self.remover_agendamento_do_db(str_data, slot)

        self.renderizar_timeline_calendario()

    def apply_form_styles(self):
        """Os campos usam a mesma especificação global do aplicativo."""
        return
