import webbrowser
import urllib.parse
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QComboBox, QDateEdit, QHeaderView, QFrame, QTextEdit)
from PySide6.QtCore import Qt, QDate

class PacientesScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        # Variável de controle para saber se estamos editando alguém (-1 significa Novo Cadastro)
        self.row_em_edicao = -1
        
        # Layout Principal (Horizontal: Listagem à esquerda, Cadastro à direita)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        
        # --- COLUNA DA ESQUERDA: BUSCA E LISTA ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Linha de Filtros (Busca + Filtro de Pasta)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(" 🔍  Buscar paciente por nome ou telefone...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px; font-size: 14px; 
                border: 1px solid #cbd5e1; border-radius: 6px; 
                background-color: white; color: #334155;
            }
            QLineEdit:focus { border: 1px solid #0284c7; }
        """)
        
        self.folder_filter = QComboBox()
        self.folder_filter.addItems(["📂 Todos os Pacientes", "Geral", "Nutrição", "Cardiologia", "Pediatria"])
        self.folder_filter.setStyleSheet("""
            QComboBox {
                padding: 10px 15px; font-size: 14px; 
                border: 1px solid #cbd5e1; border-radius: 6px; 
                background-color: white; color: #334155;
            }
            QComboBox::drop-down { border: none; padding-right: 10px; }
        """)
        
        filter_layout.addWidget(self.search_input, stretch=3)
        filter_layout.addWidget(self.folder_filter, stretch=1)
        left_layout.addLayout(filter_layout)
        
        # Tabela de Pacientes
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Nome", "Telefone", "Idade", "Convênio", "Pasta", "Ações"])
        
        # Ajuste Fixo e Seguro para as colunas não cortarem o botão do Whats
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Nome expande
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Telefone livre
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Idade compacta
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Convênio livre
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Pasta compacta
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Ações travado
        
        self.table.setColumnWidth(1, 130)  # Largura Telefone
        self.table.setColumnWidth(3, 110)  # Largura Convênio
        self.table.setColumnWidth(5, 100)  # Espaço ideal apenas para o botão "Whats"
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; color: #334155;
            }
            QTableWidget::item { padding-left: 10px; padding-right: 10px; border-bottom: 1px solid #f1f5f9; }
            QTableWidget::item:selected { background-color: #e0f2fe; color: #0369a1; }
            QHeaderView::section { 
                background-color: #f8fafc; padding: 12px 10px; border: none; border-bottom: 2px solid #e2e8f0;
                font-weight: bold; color: #475569; font-size: 13px; text-align: left;
            }
        """)
        
        # VÍNCULO DE DUPLO CLIQUE NA LINHA
        self.table.cellDoubleClicked.connect(self.ao_dar_double_click)
        
        # DUMMY DATA REMOVIDA DAQUI (A tabela agora inicia com rowCount = 0)
        self.table.setRowCount(0)
        
        left_layout.addWidget(self.table)
        
        # --- COLUNA DA DIREITA: FORMULÁRIO DE CADASTRO / EDIÇÃO ---
        self.form_container = QFrame()
        self.form_container.setFixedWidth(360)
        self.form_container.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }
            QLabel { color: #334155; font-weight: 500; font-size: 12px; border: none; }
        """)
        
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)
        
        # Título do Formulário Dinâmico
        self.form_title = QLabel("Novo Cadastro / Ficha")
        self.form_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        form_layout.addWidget(self.form_title)
        
        form_layout.addWidget(QLabel("Nome Completo:"))
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex: Francisca de Alencar Costa")
        form_layout.addWidget(self.input_nome)
        
        form_layout.addWidget(QLabel("Telefone celular:"))
        self.input_tel = QLineEdit()
        self.input_tel.setPlaceholderText("Ex: 81984358219")
        form_layout.addWidget(self.input_tel)
        
        nasc_idade_layout = QHBoxLayout()
        vbox_nasc = QVBoxLayout()
        vbox_nasc.addWidget(QLabel("Nascimento:"))
        self.input_nasc = QDateEdit()
        self.input_nasc.setCalendarPopup(True)
        self.input_nasc.setDate(QDate(1980, 1, 1))
        self.input_nasc.dateChanged.connect(self.calculate_age)
        vbox_nasc.addWidget(self.input_nasc)
        
        vbox_idade = QVBoxLayout()
        vbox_idade.addWidget(QLabel("Idade:"))
        self.label_idade = QLabel("46 anos")
        self.label_idade.setStyleSheet("font-weight: bold; color: #0284c7; font-size: 15px; border: none;")
        vbox_idade.addWidget(self.label_idade)
        
        nasc_idade_layout.addLayout(vbox_nasc)
        nasc_idade_layout.addLayout(vbox_idade)
        form_layout.addLayout(nasc_idade_layout)
        
        convenio_sexo_layout = QHBoxLayout()
        vbox_conv = QVBoxLayout()
        vbox_conv.addWidget(QLabel("Convênio:"))
        self.input_convenio = QLineEdit()
        self.input_convenio.setPlaceholderText("Particular / Unimed...")
        vbox_conv.addWidget(self.input_convenio)
        
        vbox_sexo = QVBoxLayout()
        vbox_sexo.addWidget(QLabel("Sexo:"))
        self.input_sexo = QComboBox()
        self.input_sexo.addItems(["Feminino", "Masculino", "Não Informado"])
        vbox_sexo.addWidget(self.input_sexo)
        
        convenio_sexo_layout.addLayout(vbox_conv)
        convenio_sexo_layout.addLayout(vbox_sexo)
        form_layout.addLayout(convenio_sexo_layout)
        
        form_layout.addWidget(QLabel("Endereço Residencial:"))
        self.input_endereco = QLineEdit()
        self.input_endereco.setPlaceholderText("Rua, Número, Bairro, Cidade")
        form_layout.addWidget(self.input_endereco)

        form_layout.addWidget(QLabel("Vincular à Pasta:"))
        self.input_pasta = QComboBox()
        self.input_pasta.addItems(["Geral", "Nutrição", "Cardiologia", "Pediatria"])
        form_layout.addWidget(self.input_pasta)
        
        form_layout.addWidget(QLabel("Queixa Principal (QP):"))
        self.input_qp = QTextEdit()
        self.input_qp.setPlaceholderText("Escreva aqui o motivo principal da consulta do paciente...")
        self.input_qp.setMaximumHeight(90)
        form_layout.addWidget(self.input_qp)
        
        self.apply_form_styles()
        form_layout.addStretch()
        
        # Botão de Ação do Formulário
        self.btn_salvar = QPushButton("Salvar Ficha e Paciente")
        self.btn_salvar.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px;}
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_salvar.clicked.connect(self.salvar_paciente_click)
        form_layout.addWidget(self.btn_salvar)
        
        main_layout.addWidget(left_container, stretch=3)
        main_layout.addWidget(self.form_container, stretch=1)

    def calculate_age(self, date):
        hoje = QDate.currentDate()
        anos = hoje.year() - date.year()
        if (hoje.month() < date.month()) or (hoje.month() == date.month() and hoje.day() < date.day()):
            anos -= 1
        self.label_idade.setText(f"{anos} anos")

    def format_row_item(self, text, center=False):
        item = QTableWidgetItem(text)
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return item

    def create_action_buttons(self, tel):
        """Gera apenas o botão do WhatsApp na coluna de Ações."""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 2, 5, 2)
        actions_layout.setSpacing(0)
        
        btn_wa = QPushButton("💬 Whats")
        btn_wa.setStyleSheet("""
            QPushButton { background-color: #25d366; color: white; border: none; border-radius: 4px; font-size: 12px; font-weight: bold; padding: 6px 12px; }
            QPushButton:hover { background-color: #1cbd55; }
        """)
        btn_wa.clicked.connect(lambda checked=False, t=tel: self.open_whatsapp(t))
        
        actions_layout.addWidget(btn_wa)
        return actions_widget

    def ao_dar_double_click(self, row, column):
        """Gatilho automático disparado ao clicar duas vezes em qualquer célula da linha."""
        self.carregar_para_edicao(row)

    def carregar_para_edicao(self, row_index):
        """Coleta os dados atuais da tabela e preenche o formulário para edição."""
        # Se a linha clicada for inválida por algum motivo, aborta
        if row_index < 0:
            return
            
        self.row_em_edicao = row_index
        
        # Atualiza elementos visuais do formulário para o modo de Edição (Cor Amarela)
        self.form_title.setText("✏️ Editar Cadastro / Ficha")
        self.btn_salvar.setText("Atualizar Ficha")
        self.btn_salvar.setStyleSheet("""
            QPushButton { background-color: #eab308; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px;}
            QPushButton:hover { background-color: #ca8a04; }
        """)

        # Coleta os textos da linha selecionada com segurança
        nome = self.table.item(row_index, 0).text() if self.table.item(row_index, 0) else ""
        tel = self.table.item(row_index, 1).text() if self.table.item(row_index, 1) else ""
        convenio = self.table.item(row_index, 3).text() if self.table.item(row_index, 3) else ""
        pasta = self.table.item(row_index, 4).text() if self.table.item(row_index, 4) else ""
        
        # Preenche os campos editáveis
        self.input_nome.setText(nome)
        self.input_tel.setText(tel)
        self.input_convenio.setText(convenio)
        
        # Localiza a pasta correta no combobox
        index_pasta = self.input_pasta.findText(pasta)
        if index_pasta >= 0:
            self.input_pasta.setCurrentIndex(index_pasta)
            
        # Simulação em memória no protótipo para campos adicionais
        self.input_endereco.setText("Endereço resgatado via duplo clique...")
        self.input_qp.setText("Queixa principal carregada via duplo clique...")

    def salvar_paciente_click(self):
        """Gerencia se salva um novo registro ou se atualiza uma linha existente."""
        nome = self.input_nome.text().strip()
        tel = self.input_tel.text().strip()
        idade = self.label_idade.text().replace(" anos", "")
        convenio = self.input_convenio.text().strip() or "Particular"
        pasta = self.input_pasta.currentText()
        
        if not nome:
            self.input_nome.setPlaceholderText("⚠️ O Nome é obrigatório!")
            return
            
        if self.row_em_edicao == -1:
            # MODO: NOVO CADASTRO
            target_row = self.table.rowCount()
            self.table.insertRow(target_row)
        else:
            # MODO: EDIÇÃO DE PACIENTE EXISTENTE
            target_row = self.row_em_edicao

        # Insere ou atualiza os dados na tabela
        self.table.setItem(target_row, 0, self.format_row_item(nome.upper()))
        self.table.setItem(target_row, 1, self.format_row_item(tel))
        self.table.setItem(target_row, 2, self.format_row_item(idade, center=True))
        self.table.setItem(target_row, 3, self.format_row_item(convenio.upper()))
        self.table.setItem(target_row, 4, self.format_row_item(pasta, center=True))
        
        # Atualiza o botão do WhatsApp
        actions = self.create_action_buttons(tel)
        self.table.setCellWidget(target_row, 5, actions)
        
        # Limpar Campos e Restaurar Estado Original do Formulário
        self.row_em_edicao = -1
        self.form_title.setText("Novo Cadastro / Ficha")
        self.btn_salvar.setText("Salvar Ficha e Paciente")
        self.btn_salvar.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; font-size: 14px;}
            QPushButton:hover { background-color: #0369a1; }
        """)
        
        self.input_nome.clear()
        self.input_tel.clear()
        self.input_convenio.clear()
        self.input_endereco.clear()
        self.input_qp.clear()

    def open_whatsapp(self, telefone):
        num_limpo = "".join(filter(str.isdigit, telefone))
        if not num_limpo: return
        if not num_limpo.startswith("55"):
            num_limpo = "55" + num_limpo
        texto = urllib.parse.quote("Olá, confirmamos sua consulta no Prontu.")
        webbrowser.open(f"https://wa.me/{num_limpo}?text={texto}")

    def apply_form_styles(self):
        widgets = [self.input_nome, self.input_tel, self.input_nasc, self.input_convenio, 
                   self.input_sexo, self.input_endereco, self.input_pasta, self.input_qp]
        for w in widgets:
            w.setStyleSheet("""
                padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; 
                background-color: #f8fafc; color: #0f172a; font-size: 13px;
            """)