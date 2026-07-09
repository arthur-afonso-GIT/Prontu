import sqlite3
import webbrowser
import urllib.parse
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QComboBox, QDateEdit, QHeaderView, QFrame, QTextEdit, QMessageBox, 
                               QListWidget, QListWidgetItem, QDialog)  # <- CORRIGIDO AQUI
from PySide6.QtCore import Qt, QDate

class VisualizarFichaHistoricoDialog(QDialog):
    """Janela pop-up para ler uma ficha clínica antiga do histórico"""
    def __init__(self, titulo_ficha, data_atendimento, dados_respostas, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Histórico: {titulo_ficha}")
        self.setMinimumSize(500, 450)
        self.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        lbl_titulo = QLabel(f"📋 {titulo_ficha}")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284c7; background: transparent;")
        lbl_data = QLabel(f"📅 Atendimento realizado em: {data_atendimento}")
        lbl_data.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500; background: transparent;")
        
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_data)
        
        self.txt_conteudo = QTextEdit()
        self.txt_conteudo.setReadOnly(True)
        self.txt_conteudo.setStyleSheet("QTextEdit { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; color: #0f172a; font-size: 13px; }")
        
        texto_formatado = ""
        try:
            respostas = json.loads(dados_respostas)
            if respostas:
                for campo, valor in respostas.items():
                    campo_nome = campo.replace("custom_", "").replace("_", " ").upper()
                    valor_texto = "☑️ Sim" if valor is True else ("☐ Não" if valor is False else str(valor))
                    texto_formatado += f"■ {campo_nome}:\n{valor_texto if valor_texto.strip() else '(Vazio)'}\n\n"
            else:
                texto_formatado = "Nenhuma resposta registrada nesta ficha."
        except:
            texto_formatado = "Erro ao processar as respostas da ficha."
            
        self.txt_conteudo.setPlainText(texto_formatado)
        layout.addWidget(self.txt_conteudo)
        
        btn_fechar = QPushButton("Fechar Visualização")
        btn_fechar.setStyleSheet("QPushButton { background-color: #0284c7; color: white; padding: 8px; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #0369a1; }")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar)


class PacientesScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.init_db()
        
        self.id_em_edicao = -1
        self.row_em_edicao = -1
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # --- COLUNA DA ESQUERDA: BUSCA E LISTA ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        filter_layout = QHBoxLayout()
        
        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText("🔍 Buscar paciente por nome, CPF, RG ou telefone...")
        self.input_busca.setStyleSheet("""
            QLineEdit {
                padding: 9px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: white;
                color: #0f172a;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus { border: 1px solid #0284c7; }
        """)
        self.input_busca.textChanged.connect(self.filtrar_pacientes)
        filter_layout.addWidget(self.input_busca)
        
        self.combo_filtro_pasta = QComboBox()
        self.combo_filtro_pasta.addItem("📁 Todas as Pastas")
        self.combo_filtro_pasta.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: white;
                color: #0f172a;
                min-width: 150px;
                min-height: 20px;
            }
        """)
        self.combo_filtro_pasta.currentTextChanged.connect(self.filtrar_pacientes)
        filter_layout.addWidget(self.combo_filtro_pasta)
        
        left_layout.addLayout(filter_layout)
        
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome", "Telefone", "Convênio", "Pasta"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SingleSelection)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #0f172a;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected {
                background-color: #f0f9ff;
                color: #0369a1;
                font-weight: 500;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                padding: 8px;
            }
        """)
        
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabela.itemSelectionChanged.connect(self.carregar_paciente_selecionado)
        left_layout.addWidget(self.tabela)
        
        main_layout.addWidget(left_container, stretch=2)
        
        # --- COLUNA DA DIREITA: FORMULÁRIO DE CADASTRO ---
        self.right_container = QFrame()
        self.right_container.setObjectName("FormContainer")
        self.right_container.setStyleSheet("""
            QFrame#FormContainer {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QLabel {
                color: #334155;
                font-weight: 500;
                font-size: 11px;
            }
        """)
        self.right_container.setFixedWidth(420)
        
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(6)
        
        self.lbl_form_titulo = QLabel("👤 Novo Prontuário Clínico")
        self.lbl_form_titulo.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; padding-bottom: 2px;")
        right_layout.addWidget(self.lbl_form_titulo)
        
        input_style = """
            QLineEdit, QComboBox, QDateEdit {
                padding: 5px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: white;
                color: #0f172a;
                min-height: 24px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #0284c7;
            }
        """
        
        calendar_style = """
            QCalendarWidget QWidget { 
                background-color: #ffffff; 
                color: #0f172a; 
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #ffffff;
                color: #0f172a;
                selection-background-color: #0284c7;
                selection-color: white;
            }
            QCalendarWidget QMenu {
                background-color: #ffffff;
                color: #0f172a;
            }
            QCalendarWidget QSpinBox {
                background-color: #ffffff;
                color: #0f172a;
            }
        """
        
        right_layout.addWidget(QLabel("Nome Completo:*"))
        self.input_nome = QLineEdit()
        self.input_nome.setStyleSheet(input_style)
        right_layout.addWidget(self.input_nome)
        
        layout_tel_zap = QHBoxLayout()
        v_box_tel = QVBoxLayout()
        v_box_tel.addWidget(QLabel("Telefone / Celular:"))
        self.input_tel = QLineEdit()
        self.input_tel.setStyleSheet(input_style)
        self.input_tel.setPlaceholderText("Ex: 11999998888")
        v_box_tel.addWidget(self.input_tel)
        layout_tel_zap.addLayout(v_box_tel)
        
        self.btn_whatsapp = QPushButton("💬 Zap")
        self.btn_whatsapp.setStyleSheet("""
            QPushButton {
                background-color: #25d366;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 6px;
                margin-top: 15px;
                padding: 5px 12px;
                min-height: 24px;
            }
            QPushButton:hover { background-color: #128c7e; }
        """)
        self.btn_whatsapp.clicked.connect(self.abrir_whatsapp_paciente)
        layout_tel_zap.addWidget(self.btn_whatsapp)
        right_layout.addLayout(layout_tel_zap)
        
        row_nasc_sexo = QHBoxLayout()
        box_nasc = QVBoxLayout()
        box_nasc.addWidget(QLabel("Data de Nascimento:"))
        self.input_nasc = QDateEdit()
        self.input_nasc.setCalendarPopup(True)
        self.input_nasc.calendarWidget().setStyleSheet(calendar_style)
        self.input_nasc.setDisplayFormat("dd/MM/yyyy")
        self.input_nasc.setDate(QDate(1990, 1, 1))
        self.input_nasc.setStyleSheet(input_style)
        box_nasc.addWidget(self.input_nasc)
        row_nasc_sexo.addLayout(box_nasc)
        
        box_sexo = QVBoxLayout()
        box_sexo.addWidget(QLabel("Sexo Biológico:"))
        self.input_sexo = QComboBox()
        self.input_sexo.addItems(["Masculino", "Feminino", "Outro"])
        self.input_sexo.setStyleSheet(input_style)
        box_sexo.addWidget(self.input_sexo)
        row_nasc_sexo.addLayout(box_sexo)
        right_layout.addLayout(row_nasc_sexo)
        
        row_docs = QHBoxLayout()
        box_cpf = QVBoxLayout()
        box_cpf.addWidget(QLabel("CPF:"))
        self.input_cpf = QLineEdit()
        self.input_cpf.setStyleSheet(input_style)
        box_cpf.addWidget(self.input_cpf)
        row_docs.addLayout(box_cpf)
        
        box_rg = QVBoxLayout()
        box_rg.addWidget(QLabel("RG:"))
        self.input_rg = QLineEdit()
        self.input_rg.setStyleSheet(input_style)
        box_rg.addWidget(self.input_rg)
        row_docs.addLayout(box_rg)
        right_layout.addLayout(row_docs)
        
        row_social = QHBoxLayout()
        box_civil = QVBoxLayout()
        box_civil.addWidget(QLabel("Estado Civil:"))
        self.input_civil = QLineEdit()
        self.input_civil.setStyleSheet(input_style)
        box_civil.addWidget(self.input_civil)
        row_social.addLayout(box_civil)
        
        box_prof = QVBoxLayout()
        box_prof.addWidget(QLabel("Profissão:"))
        self.input_profissao = QLineEdit()
        self.input_profissao.setStyleSheet(input_style)
        box_prof.addWidget(self.input_profissao)
        row_social.addLayout(box_prof)
        right_layout.addLayout(row_social)
        
        right_layout.addWidget(QLabel("Endereço Residencial Completo:"))
        self.input_endereco = QLineEdit()
        self.input_endereco.setStyleSheet(input_style)
        right_layout.addWidget(self.input_endereco)
        
        row_conv_pasta = QHBoxLayout()
        box_conv = QVBoxLayout()
        box_conv.addWidget(QLabel("Convênio / Plano:"))
        self.input_convenio = QLineEdit("PARTICULAR")
        self.input_convenio.setStyleSheet(input_style)
        box_conv.addWidget(self.input_convenio)
        row_conv_pasta.addLayout(box_conv)
        
        box_pasta = QVBoxLayout()
        box_pasta.addWidget(QLabel("Alocar na Pasta:"))
        self.input_pasta = QComboBox()
        self.input_pasta.setStyleSheet(input_style)
        box_pasta.addWidget(self.input_pasta)
        row_conv_pasta.addLayout(box_pasta)
        right_layout.addLayout(row_conv_pasta)
        
        right_layout.addWidget(QLabel("Queixa Principal Inicial (Motivo da abertura):"))
        self.input_qp = QTextEdit()
        self.input_qp.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: white;
                color: #0f172a;
                padding: 6px;
            }
            QTextEdit:focus { border: 1px solid #0284c7; }
        """)
        self.input_qp.setFixedHeight(50)
        right_layout.addWidget(self.input_qp)
        
        sep = QFrame()
        sep.setStyleSheet("background-color: #e2e8f0; max-height: 1px; border: none; margin: 2px 0;")
        right_layout.addWidget(sep)
        right_layout.addWidget(QLabel("📋 Prontuários Ocorridos (Duplo clique para abrir):"))
        self.list_historico_fichas = QListWidget()
        self.list_historico_fichas.setStyleSheet("""
            QListWidget { 
                background-color: #f8fafc; 
                border: 1px solid #cbd5e1; 
                border-radius: 6px; 
                color: #0f172a; 
            } 
            QListWidget::item { 
                padding: 4px; 
                border-bottom: 1px solid #e2e8f0; 
            } 
            QListWidget::item:hover { 
                background-color: #e2e8f0; 
                border-radius: 4px; 
            }
        """)
        self.list_historico_fichas.setFixedHeight(75)
        self.list_historico_fichas.itemDoubleClicked.connect(self.abrir_ficha_historico_selecionada)
        right_layout.addWidget(self.list_historico_fichas)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 2, 0, 0)
        
        self.btn_limpar = QPushButton("🔄 Limpar / Novo")
        self.btn_limpar.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_limpar.clicked.connect(self.limpar_formulario)
        btn_layout.addWidget(self.btn_limpar)
        
        self.btn_salvar = QPushButton("💾 Salvar Registro")
        self.btn_salvar.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_salvar.clicked.connect(self.salvar_paciente)
        btn_layout.addWidget(self.btn_salvar)
        right_layout.addLayout(btn_layout)

        self.btn_excluir = QPushButton("❌ Excluir Paciente")
        self.btn_excluir.setVisible(False)
        self.btn_excluir.setStyleSheet("""
            QPushButton {
                background-color: #fef2f2;
                color: #dc2626;
                border: 1px solid #fee2e2;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                min-height: 20px;
                margin-top: 2px;
            }
            QPushButton:hover { background-color: #fee2e2; }
        """)
        self.btn_excluir.clicked.connect(self.excluir_paciente)
        right_layout.addWidget(self.btn_excluir)
        
        combobox_dropdown_style = """
            QComboBox { background-color: white; color: #0f172a; }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                selection-background-color: #0284c7;
                selection-color: white;
            }
        """
        self.input_sexo.setStyleSheet(self.input_sexo.styleSheet() + combobox_dropdown_style)
        self.input_pasta.setStyleSheet(self.input_pasta.styleSheet() + combobox_dropdown_style)
        
        main_layout.addWidget(self.right_container)
        self.carregar_pacientes_tabela()

    def mostrar_alerta_seguro(self, tipo, titulo, texto):
        msg = QMessageBox(self)
        msg.setWindowTitle(titulo)
        msg.setText(texto)
        if tipo == "warning":
            msg.setIcon(QMessageBox.Warning)
        elif tipo == "error":
            msg.setIcon(QMessageBox.Critical)
        else:
            msg.setIcon(QMessageBox.Information)
            
        msg.setStyleSheet("""
            QMessageBox { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: normal; }
            QPushButton { background-color: #0284c7; color: white; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        msg.exec()

    def init_db(self):
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pacientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    telefone TEXT,
                    nascimento TEXT,
                    convenio TEXT,
                    pasta TEXT
                )
            """)
            
            novas_colunas = [
                ("sexo", "TEXT"),
                ("cpf", "TEXT"),
                ("rg", "TEXT"),
                ("estado_civil", "TEXT"),
                ("profissao", "TEXT"),
                ("endereco", "TEXT"),
                ("queixa", "TEXT")
            ]
            
            for col_nome, col_tipo in novas_colunas:
                try:
                    cursor.execute(f"ALTER TABLE pacientes ADD COLUMN {col_nome} {col_tipo}")
                except sqlite3.OperationalError:
                    pass
                    
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Erro na migração do DB: {e}")

    def abrir_whatsapp_paciente(self):
        numero = "".join(c for c in self.input_tel.text().strip() if c.isdigit())
        if not numero:
            self.mostrar_alerta_seguro("warning", "WhatsApp", "Por favor, digite um número válido primeiro.")
            return
        if len(numero) <= 11: 
            numero = "55" + numero
        
        texto_padrao = urllib.parse.quote("Olá! Entramos em contato a partir do consultório médico.")
        webbrowser.open(f"https://web.whatsapp.com/send?phone={numero}&text={texto_padrao}")

    def carregar_pacientes_tabela(self, lista_customizada=None):
        self.tabela.setRowCount(0)
        rows = lista_customizada
        
        if rows is None:
            try:
                conn = sqlite3.connect("consultorio.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id, nome, telefone, convenio, pasta FROM pacientes ORDER BY nome ASC")
                rows = cursor.fetchall()
                conn.close()
            except:
                rows = []
                
        for row_idx, row_data in enumerate(rows):
            self.tabela.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                self.tabela.setItem(row_idx, col_idx, item)

    def carregar_paciente_selecionado(self):
        item_selecionado = self.tabela.selectedItems()
        if not item_selecionado:
            self.btn_excluir.setVisible(False)
            return
            
        self.row_em_edicao = self.tabela.currentRow()
        self.id_em_edicao = int(self.tabela.item(self.row_em_edicao, 0).text())
        
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nome, telefone, nascimento, convenio, pasta, 
                       sexo, cpf, rg, estado_civil, profissao, endereco, queixa 
                FROM pacientes WHERE id = ?
            """, (self.id_em_edicao,))
            p = cursor.fetchone()
            conn.close()
            
            if p:
                self.lbl_form_titulo.setText("📝 Editando Prontuário")
                self.input_nome.setText(p[0] if p[0] else "")
                self.input_tel.setText(p[1] if p[1] else "")
                
                try:
                    if p[2]:
                        self.input_nasc.setDate(QDate.fromString(p[2], "yyyy-MM-dd"))
                    else:
                        self.input_nasc.setDate(QDate(1990, 1, 1))
                except:
                    self.input_nasc.setDate(QDate(1990, 1, 1))
                    
                self.input_convenio.setText(p[3] if p[3] else "PARTICULAR")
                self.input_pasta.setCurrentText(p[4] if p[4] else "")
                self.input_sexo.setCurrentText(p[5] if p[5] else "Masculino")
                self.input_cpf.setText(p[6] if p[6] else "")
                self.input_rg.setText(p[7] if p[7] else "")
                self.input_civil.setText(p[8] if p[8] else "")
                self.input_profissao.setText(p[9] if p[9] else "")
                self.input_endereco.setText(p[10] if p[10] else "")
                self.input_qp.setPlainText(p[11] if p[11] else "")
                
                self.btn_excluir.setVisible(True)
        except Exception as e:
            print(f"Erro ao carregar dados de texto do paciente: {e}")
            
        # Fora do bloco Try/Except principal: as fichas carregarão mesmo com pendências de tabela
        self.carregar_historico_fichas_paciente(self.id_em_edicao)

    def carregar_historico_fichas_paciente(self, p_id):
        self.list_historico_fichas.clear()
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, modelo_nome, data_atendimento, dados_respostas 
                FROM fichas_preenchidas WHERE paciente_id = ? ORDER BY id DESC
            """, (p_id,))
            
            fichas = cursor.fetchall()
            conn.close()
            
            for f in fichas:
                w_item = QListWidgetItem(f"📄 {f[1]} ({f[2]})")
                w_item.setData(Qt.UserRole, f)
                self.list_historico_fichas.addItem(w_item)
        except Exception as e:
            print(f"Erro ao buscar histórico de fichas no banco: {e}")

    def abrir_ficha_historico_selecionada(self, item):
        dados = item.data(Qt.UserRole)
        if dados: 
            VisualizarFichaHistoricoDialog(dados[1], dados[2], dados[3], self).exec()

    def filtrar_pacientes(self):
        texto = self.input_busca.text().lower().strip()
        pasta_filtro = self.combo_filtro_pasta.currentText()
        
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, telefone, convenio, pasta, cpf, rg FROM pacientes ORDER BY nome ASC")
            todos = cursor.fetchall()
            conn.close()
            
            filtrados = []
            for p in todos:
                nome, fone, conv, pasta, cpf, rg = str(p[1]).lower(), str(p[2]).lower(), str(p[3]).lower(), str(p[4]), str(p[5]).lower(), str(p[6]).lower()
                
                match_texto = not texto or (texto in nome or texto in fone or texto in conv or texto in cpf or texto in rg)
                match_pasta = "Todas as Pastas" in pasta_filtro or pasta == pasta_filtro
                
                if match_texto and match_pasta:
                    filtrados.append(p[:5])
                    
            self.carregar_pacientes_tabela(filtrados)
        except:
            pass

    def filtrar_por_pasta_externo(self, nome_pasta):
        self.combo_filtro_pasta.setCurrentText(nome_pasta)
        self.filtrar_pacientes()

    def salvar_paciente(self):
        nome = self.input_nome.text().strip()
        fone = self.input_tel.text().strip()
        nasc = self.input_nasc.date().toString("yyyy-MM-dd")
        conv = self.input_convenio.text().strip()
        pasta = self.input_pasta.currentText()
        sexo = self.input_sexo.currentText()
        cpf = self.input_cpf.text().strip()
        rg = self.input_rg.text().strip()
        civil = self.input_civil.text().strip()
        prof = self.input_profissao.text().strip()
        end = self.input_endereco.text().strip()
        queixa = self.input_qp.toPlainText().strip()
        
        if not nome:
            self.mostrar_alerta_seguro("warning", "Aviso", "O campo Nome Completo é obrigatório.")
            return
            
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            
            if self.id_em_edicao == -1:
                cursor.execute("""
                    INSERT INTO pacientes (nome, telefone, nascimento, convenio, pasta, sexo, cpf, rg, estado_civil, profissao, endereco, queixa) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nome, fone, nasc, conv, pasta, sexo, cpf, rg, civil, prof, end, queixa))
            else:
                cursor.execute("""
                    UPDATE pacientes SET nome=?, telefone=?, nascimento=?, convenio=?, pasta=?, 
                                         sexo=?, cpf=?, rg=?, estado_civil=?, profissao=?, endereco=?, queixa=?
                    WHERE id=?
                """, (nome, fone, nasc, conv, pasta, sexo, cpf, rg, civil, prof, end, queixa, self.id_em_edicao))
                
            conn.commit()
            conn.close()
            
            self.limpar_formulario()
            self.carregar_pacientes_tabela()
            self.mostrar_alerta_seguro("success", "Sucesso", "Prontuário do paciente salvo com sucesso!")
        except Exception as e:
            self.mostrar_alerta_seguro("error", "Erro Crítico", f"Erro ao salvar no banco:\n{str(e)}")

    def excluir_paciente(self):
        if self.id_em_edicao == -1:
            return
            
        nome_paciente = self.input_nome.text()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar Exclusão")
        msg.setText(f"Tem certeza que deseja excluir o prontuário de '{nome_paciente}'?\nEsta ação não poderá ser desfeita.")
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; }
            QPushButton { background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 4px; padding: 5px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        if msg.exec() == QMessageBox.Yes:
            try:
                conn = sqlite3.connect("consultorio.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pacientes WHERE id = ?", (self.id_em_edicao,))
                cursor.execute("DELETE FROM fichas_preenchidas WHERE paciente_id = ?", (self.id_em_edicao,))
                conn.commit()
                conn.close()
                
                self.limpar_formulario()
                self.carregar_pacientes_tabela()
                self.mostrar_alerta_seguro("success", "Excluído", "O registro do paciente foi deletado com sucesso.")
            except Exception as e:
                self.mostrar_alerta_seguro("error", "Erro", f"Falha ao deletar registro:\n{str(e)}")

    def limpar_formulario(self):
        self.id_em_edicao = -1
        self.row_em_edicao = -1
        self.lbl_form_titulo.setText("👤 Novo Prontuário Clínico")
        self.input_nome.clear()
        self.input_tel.clear()
        self.input_nasc.setDate(QDate(1990, 1, 1))
        self.input_convenio.setText("PARTICULAR")
        self.input_sexo.setCurrentIndex(0)
        self.input_cpf.clear()
        self.input_rg.clear()
        self.input_civil.clear()
        self.input_profissao.clear()
        self.input_endereco.clear()
        self.input_qp.clear()
        self.list_historico_fichas.clear()
        self.tabela.clearSelection()
        self.btn_excluir.setVisible(False)
        if self.input_pasta.count() > 0: 
            self.input_pasta.setCurrentIndex(0)

    def preencher_formulario_via_importacao(self, dados):
        self.input_nome.setText(dados.get("nome", ""))
        self.input_tel.setText(dados.get("telefone", ""))
        self.input_convenio.setText(dados.get("convenio", "PARTICULAR"))
        self.input_endereco.setText(dados.get("endereco", ""))
        self.input_qp.setText(dados.get("qp", ""))
        
        str_data = dados.get("nascimento", "")
        try:
            dia, mes, ano = map(int, str_data.split("/"))
            self.input_nasc.setDate(QDate(ano, mes, dia))
        except:
            self.input_nasc.setDate(QDate(1980, 1, 1))

    def atualizar_combobox_pastas(self, lista_pastas):
        pasta_atual_filtro = self.combo_filtro_pasta.currentText()
        pasta_atual_input = self.input_pasta.currentText()
        
        self.combo_filtro_pasta.clear()
        self.combo_filtro_pasta.addItem("📁 Todas as Pastas")
        self.input_pasta.clear()
        
        for p in lista_pastas:
            self.combo_filtro_pasta.addItem(p)
            self.input_pasta.addItem(p)
            
        if self.combo_filtro_pasta.findText(pasta_atual_filtro) != -1:
            self.combo_filtro_pasta.setCurrentText(pasta_atual_filtro)
        if self.input_pasta.findText(pasta_atual_input) != -1:
            self.input_pasta.setCurrentText(pasta_atual_input)