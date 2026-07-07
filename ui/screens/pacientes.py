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
        self.search_input.setPlaceholderText(" 🔍   Buscar paciente por nome ou telefone...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px; font-size: 14px; 
                border: 1px solid #cbd5e1; border-radius: 6px; 
                background-color: white; color: #334155;
            }
            QLineEdit:focus { border: 1px solid #0284c7; }
        """)
        # Vincula a digitação ao filtro em tempo real
        self.search_input.textChanged.connect(self.filtrar_tabela)
        
        self.folder_filter = QComboBox()
        # Vincula a mudança de pasta ao filtro em tempo real
        self.folder_filter.currentIndexChanged.connect(self.filtrar_tabela)
        
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
        self.input_nasc.setDisplayFormat("dd/MM/yyyy")
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
        if row_index < 0:
            return
            
        self.row_em_edicao = row_index
        
        # Updates visual elements of form to Edit mode (Yellow Color)
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
        
        # Dispara o filtro para reposicionar se o paciente trocou de pasta
        self.filtrar_tabela()

    def open_whatsapp(self, telefone):
        num_limpo = "".join(filter(str.isdigit, telefone))
        if not num_limpo: return
        if not num_limpo.startswith("55"):
            num_limpo = "55" + num_limpo
        texto = urllib.parse.quote("Olá, confirmamos sua consulta no Prontu.")
        webbrowser.open(f"https://wa.me/{num_limpo}?text={texto}")

    def apply_form_styles(self):
        widgets = [self.input_nome, self.input_tel, self.input_nasc, self.input_convenio, 
                   self.input_endereco, self.input_qp]
        
        # Estilo para os campos editáveis comuns
        for w in widgets:
            w.setStyleSheet("""
                QLineEdit, QDateEdit, QTextEdit {
                    padding: 8px; 
                    border: 1px solid #cbd5e1; 
                    border-radius: 6px; 
                    background-color: #f8fafc; 
                    color: #0f172a; 
                    font-size: 13px;
                }
                QLineEdit:focus, QDateEdit:focus, QTextEdit:focus { 
                    border: 1px solid #0284c7; 
                    background-color: white;
                    color: #0f172a;
                }
            """)

        # Estilo específico e blindado para todos os QComboBox (Incluindo os dropdowns ocultos)
        combobox_style = """
            QComboBox {
                padding: 8px; 
                border: 1px solid #cbd5e1; 
                border-radius: 6px; 
                background-color: white; 
                color: #0f172a; 
                font-size: 13px;
            }
            QComboBox:focus { 
                border: 1px solid #0284c7; 
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                selection-background-color: #f1f5f9;
                selection-color: #0284c7;
                padding: 4px;
            }
        """
        
        self.input_sexo.setStyleSheet(combobox_style)
        self.input_pasta.setStyleSheet(combobox_style)
        
        # Estiliza o filtro superior esquerdo também para ficar idêntico e blindado
        self.folder_filter.setStyleSheet("""
            QComboBox {
                padding: 10px 15px; font-size: 14px; 
                border: 1px solid #cbd5e1; border-radius: 6px; 
                background-color: white; color: #0f172a;
            }
            QComboBox::drop-down { border: none; padding-right: 10px; }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                selection-background-color: #f1f5f9;
                selection-color: #0284c7;
                padding: 4px;
            }
        """)
            
    def preencher_formulario_via_importacao(self, dados):
        """Recebe dados extraídos de arquivos externos e alimenta os inputs visuais automaticamente."""
        self.input_nome.setText(dados.get("nome", ""))
        self.input_tel.setText(dados.get("telefone", ""))
        self.input_convenio.setText(dados.get("convenio", "PARTICULAR"))
        self.input_endereco.setText(dados.get("endereco", ""))
        self.input_qp.setText(dados.get("qp", ""))
        
        # Conversão e tratamento da Data de Nascimento
        str_data = dados.get("nascimento", "")
        try:
            dia, mes, ano = map(int, str_data.split("/"))
            self.input_nasc.setDate(QDate(ano, mes, dia))
        except:
            self.input_nasc.setDate(QDate(1980, 1, 1))

    def atualizar_combobox_pastas(self, lista_pastas):
        """Reconstrói os filtros e dropdowns baseando-se na lista global síncrona."""
        # Salva a seleção atual para restaurar após atualizar a lista
        current_filter = self.folder_filter.currentText()
        current_input = self.input_pasta.currentText()

        # 1. Atualiza o filtro de buscas superior da tabela
        self.folder_filter.blockSignals(True)
        self.folder_filter.clear()
        self.folder_filter.addItem("📂 Todos os Pacientes")
        for p in lista_pastas:
            self.folder_filter.addItem(p)
        
        idx_f = self.folder_filter.findText(current_filter)
        if idx_f >= 0: self.folder_filter.setCurrentIndex(idx_f)
        self.folder_filter.blockSignals(False)
            
        # 2. Atualiza o seletor interno do formulário de cadastro
        self.input_pasta.blockSignals(True)
        self.input_pasta.clear()
        self.input_pasta.addItems(lista_pastas)
        
        idx_i = self.input_pasta.findText(current_input)
        if idx_i >= 0: self.input_pasta.setCurrentIndex(idx_i)
        self.input_pasta.blockSignals(False)
        
        self.filtrar_tabela()
            
    def filtrar_por_pasta_externo(self, nome_pasta):
        """Muda o combo box de filtro superior para a pasta selecionada na Home."""
        index = self.folder_filter.findText(nome_pasta)
        if index >= 0:
            self.folder_filter.setCurrentIndex(index)

    def filtrar_tabela(self):
        """Filtra a QTableWidget cruzando o texto de busca com a pasta selecionada."""
        texto_busca = self.search_input.text().strip().lower()
        pasta_selecionada = self.folder_filter.currentText()
        
        for row in range(self.table.rowCount()):
            item_nome = self.table.item(row, 0)
            item_tel = self.table.item(row, 1)
            item_pasta = self.table.item(row, 4)
            
            nome = item_nome.text().lower() if item_nome else ""
            tel = item_tel.text().lower() if item_tel else ""
            pasta_do_paciente = item_pasta.text() if item_pasta else ""
            
            # Condição 1: Valida o termo de busca (no nome ou telefone)
            corresponde_busca = (texto_busca in nome) or (texto_busca in tel)
            
            # Condição 2: Valida a pasta selecionada
            if pasta_selecionada == "📂 Todos os Pacientes" or not pasta_selecionada:
                corresponde_pasta = True
            else:
                corresponde_pasta = (pasta_do_paciente == pasta_selecionada)
                
            # Exibe a linha se passar em ambos os filtros; senão, esconde
            if corresponde_busca and corresponde_pasta:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)