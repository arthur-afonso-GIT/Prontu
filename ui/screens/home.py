from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QTableWidget, QHeaderView, QPushButton, 
                               QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, QDate

class HomeScreen(QWidget):
    def __init__(self, window_principal, on_novo_paciente_click=None, on_pasta_click=None):
        super().__init__()
        
        self.window_principal = window_principal
        self.on_novo_paciente_click = on_novo_paciente_click
        self.on_pasta_click = on_pasta_click
        
        # Layout Principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(25)
        
        # --- 1. CABEÇALHO ---
        header_layout = QHBoxLayout()
        welcome_vbox = QVBoxLayout()
        
        hoje_extenso = QDate.currentDate().toString("dd 'de' MMMM 'de' yyyy")
        
        title = QLabel("Olá, Dra. Laura")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        
        subtitle = QLabel(f"Bem-vinda de volta. Aqui está o resumo para hoje, {hoje_extenso}.")
        subtitle.setStyleSheet("font-size: 14px; color: #64748b;")
        
        welcome_vbox.addWidget(title)
        welcome_vbox.addWidget(subtitle)
        header_layout.addLayout(welcome_vbox)
        header_layout.addStretch()
        
        self.btn_atalho_cadastro = QPushButton("➕ Novo Paciente")
        self.btn_atalho_cadastro.setStyleSheet("""
            QPushButton { 
                background-color: #0284c7; color: white; padding: 10px 20px; 
                font-weight: bold; border-radius: 6px; border: none; font-size: 14px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        if self.on_novo_paciente_click:
            self.btn_atalho_cadastro.clicked.connect(self.on_novo_paciente_click)
            
        header_layout.addWidget(self.btn_atalho_cadastro)
        main_layout.addLayout(header_layout)
        
        # --- 2. CARD INDICADORES (KPIs) ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(20)
        
        self.card_pacientes = self.create_kpi_card("Total de Pacientes", "0", "#0284c7")
        self.card_consultas = self.create_kpi_card("Consultas Hoje", "0", "#10b981")
        self.card_pastas = self.create_kpi_card("Pastas Ativas", str(len(self.window_principal.pastas_sistema)), "#6366f1")
        
        kpi_layout.addWidget(self.card_pacientes)
        kpi_layout.addWidget(self.card_consultas)
        kpi_layout.addWidget(self.card_pastas)
        main_layout.addLayout(kpi_layout)
        
        # --- 3. SEÇÃO INFERIOR DIVIDIDA ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(25)
        
        # Bloco Esquerda: GERENCIADOR COMPLETO DE PASTAS
        self.pastas_container = QFrame()
        self.pastas_container.setStyleSheet("background-color: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        
        self.pastas_vbox = QVBoxLayout(self.pastas_container)
        self.pastas_vbox.setContentsMargins(20, 20, 20, 20)
        self.pastas_vbox.setSpacing(10)
        
        # Header do bloco de Pastas (Título + Botão Criar)
        pastas_header = QHBoxLayout()
        pastas_title = QLabel("📁 Pastas Especializadas")
        pastas_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; border: none;")
        
        btn_nova_pasta = QPushButton("➕ Nova")
        btn_nova_pasta.setStyleSheet("""
            QPushButton { 
                background-color: #f1f5f9; color: #0f172a; padding: 5px 12px; 
                font-size: 12px; font-weight: bold; border: 1px solid #cbd5e1; border-radius: 4px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        btn_nova_pasta.clicked.connect(self.acao_adicionar_pasta)
        
        pastas_header.addWidget(pastas_title)
        pastas_header.addStretch()
        pastas_header.addWidget(btn_nova_pasta)
        self.pastas_vbox.addLayout(pastas_header)
        
        # Container interno que guardará as linhas de cada pasta
        self.lista_pastas_layout = QVBoxLayout()
        self.lista_pastas_layout.setSpacing(8)
        self.pastas_vbox.addLayout(self.lista_pastas_layout)
        
        self.pastas_vbox.addStretch()
        
        # Renderiza a lista inicial de pastas do sistema
        self.renderizar_lista_pastas()
        
        # Bloco Direita: Agenda Expressa
        agenda_container = QFrame()
        agenda_container.setStyleSheet("background-color: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        agenda_vbox = QVBoxLayout(agenda_container)
        agenda_vbox.setContentsMargins(20, 20, 20, 20)
        agenda_vbox.setSpacing(15)
        
        agenda_title = QLabel("⏱️ Atendimentos de Hoje")
        agenda_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; border: none;")
        agenda_vbox.addWidget(agenda_title)
        
        self.table_hoje = QTableWidget()
        self.table_hoje.setColumnCount(3)
        self.table_hoje.setHorizontalHeaderLabels(["Horário", "Paciente", "Status"])
        self.table_hoje.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_hoje.verticalHeader().setVisible(False)
        self.table_hoje.setShowGrid(False)
        self.table_hoje.setRowCount(0)
        self.table_hoje.setStyleSheet("QTableWidget { background-color: white; border: none; }")
        
        self.lbl_agenda_vazia = QLabel("Nenhum paciente agendado para o dia de hoje.")
        self.lbl_agenda_vazia.setStyleSheet("color: #64748b; font-size: 13px; font-style: italic; border: none;")
        self.lbl_agenda_vazia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        agenda_vbox.addWidget(self.table_hoje)
        agenda_vbox.addWidget(self.lbl_agenda_vazia)
        
        bottom_layout.addWidget(self.pastas_container, stretch=1)
        bottom_layout.addWidget(agenda_container, stretch=2)
        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

    def create_kpi_card(self, title, val, color_hex):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 500; border: none;")
        
        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color_hex}; border: none;")
        
        # Garante identificação única apenas para a label numérica do card de Pastas
        if title == "Pastas Ativas":
            lbl_val.setObjectName("valor_pastas_kpi")
            
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        return card

    def renderizar_lista_pastas(self):
        # Limpa o layout anterior usando a referência correta (self.lista_pastas_layout)
        while self.lista_pastas_layout.count():
            item = self.lista_pastas_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        lista = self.window_principal.pastas_sistema
        for nome in lista:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 4, 8, 4)
            
            lbl_pasta = QLabel(f"📁  {nome}")
            lbl_pasta.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 500; border: none;")
            item_layout.addWidget(lbl_pasta)
            item_layout.addStretch()

            btn_editar = QPushButton("✏️")
            btn_editar.setFixedSize(28, 28)
            btn_editar.setStyleSheet("background-color: transparent; border: 1px solid #cbd5e1; border-radius: 4px; color: #64748b;")
            btn_editar.clicked.connect(lambda checked, n=nome: self.acao_editar_pasta(n))
            item_layout.addWidget(btn_editar)

            if nome != "Geral":
                btn_excluir = QPushButton("❌")
                btn_excluir.setFixedSize(28, 28)
                btn_excluir.setStyleSheet("background-color: transparent; border: 1px solid #fee2e2; border-radius: 4px; color: #ef4444;")
                btn_excluir.clicked.connect(lambda checked, n=nome: self.acao_excluir_pasta(n))
                item_layout.addWidget(btn_excluir)

            item_widget.setStyleSheet("QWidget { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; }")
            self.lista_pastas_layout.addWidget(item_widget)

        # Atualiza com precisão cirúrgica o número do KPI sem quebrar o título
        label_kpi = self.card_pastas.findChild(QLabel, "valor_pastas_kpi")
        if label_kpi:
            label_kpi.setText(str(len(lista)))

    # --- GESTÃO DE PASTAS COM BLINDAGEM DE INTERFACE ---
    def acao_adicionar_pasta(self):
        dialogo = QInputDialog(self)
        dialogo.setWindowTitle("Nova Pasta")
        dialogo.setLabelText("Digite o nome da nova especialidade/pasta:")
        dialogo.setStyleSheet("""
            QLabel { color: #0f172a; font-size: 13px; }
            QLineEdit { color: #0f172a; background-color: white; border: 1px solid #cbd5e1; padding: 6px; border-radius: 4px; }
            QPushButton { color: #0f172a; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        ok = dialogo.exec()
        nome_pasta = dialogo.textValue()

        if ok and nome_pasta.strip():
            nome_limpo = nome_pasta.strip()
            lista = self.window_principal.pastas_sistema
            if nome_limpo in lista:
                aviso = QMessageBox(self)
                aviso.setIcon(QMessageBox.Icon.Warning)
                aviso.setWindowTitle("Aviso")
                aviso.setText("Já existe uma pasta com esse nome.")
                aviso.setStyleSheet("QLabel { color: #0f172a; } QPushButton { color: #0f172a; }")
                aviso.exec()
                return
                
            lista.append(nome_limpo)
            self.window_principal.sincronizar_pastas_sistema(lista)
            self.renderizar_lista_pastas()

    def acao_editar_pasta(self, nome_antigo):
        dialogo = QInputDialog(self)
        dialogo.setWindowTitle("Editar Pasta")
        dialogo.setLabelText(f"Alterar o nome da pasta '{nome_antigo}' para:")
        dialogo.setTextValue(nome_antigo)
        dialogo.setStyleSheet("""
            QLabel { color: #0f172a; font-size: 13px; }
            QLineEdit { color: #0f172a; background-color: white; border: 1px solid #cbd5e1; padding: 6px; border-radius: 4px; }
            QPushButton { color: #0f172a; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        ok = dialogo.exec()
        nome_novo = dialogo.textValue()

        if ok and nome_novo.strip():
            nome_limpo = nome_novo.strip()
            lista = self.window_principal.pastas_sistema
            if nome_limpo in lista and nome_limpo != nome_antigo:
                aviso = QMessageBox(self)
                aviso.setIcon(QMessageBox.Icon.Warning)
                aviso.setWindowTitle("Aviso")
                aviso.setText("Já existe uma pasta com esse nome.")
                aviso.setStyleSheet("QLabel { color: #0f172a; } QPushButton { color: #0f172a; }")
                aviso.exec()
                return
                
            idx = lista.index(nome_antigo)
            lista[idx] = nome_limpo
            self.window_principal.sincronizar_pastas_sistema(lista)
            self.renderizar_lista_pastas()

    def acao_excluir_pasta(self, nome_pasta):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle("Confirmar Exclusão")
        msg_box.setText(f"Tem certeza que deseja apagar a pasta '{nome_pasta}'?\nPacientes vinculados a ela retornarão ao grupo Geral.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet("""
            QLabel { color: #0f172a; font-size: 13px; }
            QPushButton { color: #0f172a; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 14px; border-radius: 4px; font-weight: 500; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        resposta = msg_box.exec()
        if resposta == QMessageBox.StandardButton.Yes:
            lista = self.window_principal.pastas_sistema
            if nome_pasta in lista:
                lista.remove(nome_pasta)
                if not lista:
                    lista.append("Geral")
                self.window_principal.sincronizar_pastas_sistema(lista)
                self.renderizar_lista_pastas()