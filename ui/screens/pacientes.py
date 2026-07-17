import webbrowser
import urllib.parse
import json
import unicodedata
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QComboBox, QDateEdit, QHeaderView, QFrame, QTextEdit, QMessageBox, 
                               QListWidget, QListWidgetItem, QDialog, QScrollArea, QCalendarWidget,
                               QFileDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from utils.operacao_segura import (
    finalizar_operacao,
    iniciar_operacao,
    mensagem_erro_usuario,
    registrar_falha,
)
from services.importador_pacientes import (
    ler_planilha, preparar_registros, classificar_registros, payload_novo, payload_atualizacao,
)


def normalizar_nome_pasta(valor):
    """Remove caracteres invisíveis e espaços extras de nomes de pasta."""
    texto = "".join(
        caractere for caractere in str(valor or "")
        if unicodedata.category(caractere) != "Cf"
    )
    texto = " ".join(texto.split())
    return texto if any(caractere.isalnum() for caractere in texto) else ""


def normalizar_cpf(valor):
    """Mantém somente os números do CPF para salvar e comparar."""
    return "".join(caractere for caractere in str(valor or "") if caractere.isdigit())[:11]


def formatar_cpf(valor):
    """Apresenta o CPF no padrão brasileiro sem alterar seu valor interno."""
    numeros = normalizar_cpf(valor)
    if len(numeros) <= 3:
        return numeros
    if len(numeros) <= 6:
        return f"{numeros[:3]}.{numeros[3:]}"
    if len(numeros) <= 9:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:]}"
    return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"


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
            respostas = dados_respostas if isinstance(dados_respostas, dict) else json.loads(dados_respostas)
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


class EditarFichaHistoricoDialog(QDialog):
    """Edição simples e segura das respostas de uma ficha já registrada."""
    def __init__(self, titulo_ficha, dados_respostas, ao_salvar, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar ficha: {titulo_ficha}")
        self.setMinimumSize(560, 520)
        self._ao_salvar = ao_salvar
        self._campos = {}

        try:
            self._respostas = dados_respostas if isinstance(dados_respostas, dict) else json.loads(dados_respostas)
        except (TypeError, json.JSONDecodeError):
            self._respostas = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel(f"Editar respostas — {titulo_ficha}")
        titulo.setStyleSheet("font-size: 17px; font-weight: bold; color: #0f172a;")
        explicacao = QLabel("Altere somente o que for necessário e clique em Salvar alterações.")
        explicacao.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(titulo)
        layout.addWidget(explicacao)

        area_rolagem = QScrollArea()
        area_rolagem.setWidgetResizable(True)
        area_rolagem.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; }")
        conteudo = QWidget()
        campos_layout = QVBoxLayout(conteudo)
        campos_layout.setContentsMargins(14, 14, 14, 14)
        campos_layout.setSpacing(10)

        if not self._respostas:
            campos_layout.addWidget(QLabel("Esta ficha não possui respostas para editar."))
        for campo, valor in self._respostas.items():
            nome_legivel = campo.replace("custom_", "").replace("_", " ").capitalize()
            campos_layout.addWidget(QLabel(nome_legivel))
            if isinstance(valor, bool):
                entrada = QComboBox()
                entrada.addItem("Sim", True)
                entrada.addItem("Não", False)
                entrada.setCurrentIndex(0 if valor else 1)
                entrada.setStyleSheet("QComboBox { padding: 7px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; }")
            else:
                entrada = QTextEdit()
                entrada.setPlainText("" if valor is None else str(valor))
                entrada.setFixedHeight(64)
                entrada.setStyleSheet("QTextEdit { padding: 7px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; }")
            self._campos[campo] = entrada
            campos_layout.addWidget(entrada)
        campos_layout.addStretch()
        area_rolagem.setWidget(conteudo)
        layout.addWidget(area_rolagem)

        botoes = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_salvar = QPushButton("Salvar alterações")
        btn_salvar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: none; border-radius: 6px; padding: 9px 16px; font-weight: bold; } QPushButton:hover { background: #0369a1; }")
        btn_salvar.clicked.connect(self.salvar)
        botoes.addStretch()
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        layout.addLayout(botoes)

    def salvar(self):
        respostas_atualizadas = {}
        for campo, entrada in self._campos.items():
            respostas_atualizadas[campo] = entrada.currentData() if isinstance(entrada, QComboBox) else entrada.toPlainText().strip()
        if self._ao_salvar(respostas_atualizadas):
            self.accept()


class ImportarPacientesDialog(QDialog):
    """Prévia e confirmação de importação de pacientes por CSV ou Excel."""
    def __init__(self, tela_pacientes):
        super().__init__(tela_pacientes)
        self.tela_pacientes = tela_pacientes
        self.registros_classificados = []
        self.campos_presentes = set()
        self.setWindowTitle("Importar pacientes")
        self.setMinimumSize(760, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        titulo = QLabel("Importar pacientes")
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a;")
        layout.addWidget(titulo)
        descricao = QLabel("Escolha uma planilha CSV ou Excel. O Prontu mostrará uma prévia antes de salvar qualquer dado.")
        descricao.setWordWrap(True)
        descricao.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(descricao)

        arquivo_layout = QHBoxLayout()
        self.lbl_arquivo = QLabel("Nenhum arquivo selecionado")
        self.lbl_arquivo.setStyleSheet("color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;")
        btn_arquivo = QPushButton("Escolher arquivo")
        btn_arquivo.setStyleSheet("QPushButton { background: #eff6ff; color: #0369a1; border: 1px solid #93c5fd; border-radius: 6px; padding: 8px 12px; font-weight: bold; } QPushButton:hover { background: #dbeafe; }")
        btn_arquivo.clicked.connect(self.escolher_arquivo)
        arquivo_layout.addWidget(self.lbl_arquivo, stretch=1)
        arquivo_layout.addWidget(btn_arquivo)
        layout.addLayout(arquivo_layout)

        modo_layout = QHBoxLayout()
        modo_layout.addWidget(QLabel("Ao encontrar paciente já cadastrado:"))
        self.combo_modo = QComboBox()
        self.combo_modo.addItem("Adicionar apenas novos (ignorar duplicados)", "adicionar")
        self.combo_modo.addItem("Atualizar dados dos pacientes encontrados", "atualizar")
        self.combo_modo.currentIndexChanged.connect(self.atualizar_previa)
        modo_layout.addWidget(self.combo_modo, stretch=1)
        layout.addLayout(modo_layout)

        self.lbl_resumo = QLabel("Selecione um arquivo para começar.")
        self.lbl_resumo.setWordWrap(True)
        self.lbl_resumo.setStyleSheet("background: #f0f9ff; color: #075985; border: 1px solid #bae6fd; border-radius: 6px; padding: 9px; font-weight: 500;")
        layout.addWidget(self.lbl_resumo)

        self.tabela_previa = QTableWidget()
        self.tabela_previa.setColumnCount(5)
        self.tabela_previa.setHorizontalHeaderLabels(["Linha", "Nome", "Telefone", "CPF", "Resultado"])
        self.tabela_previa.verticalHeader().setVisible(False)
        self.tabela_previa.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela_previa.setSelectionMode(QTableWidget.NoSelection)
        self.tabela_previa.setStyleSheet("QTableWidget { background: white; border: 1px solid #cbd5e1; border-radius: 7px; gridline-color: #e2e8f0; } QHeaderView::section { background: #f8fafc; color: #475569; font-weight: bold; padding: 7px; border: none; border-bottom: 1px solid #cbd5e1; }")
        cabecalho = self.tabela_previa.horizontalHeader()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for coluna in range(1, 5):
            cabecalho.setSectionResizeMode(coluna, QHeaderView.Stretch)
        layout.addWidget(self.tabela_previa, stretch=1)

        acoes = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        self.btn_importar = QPushButton("Confirmar importação")
        self.btn_importar.setEnabled(False)
        self.btn_importar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: none; border-radius: 6px; padding: 9px 16px; font-weight: bold; } QPushButton:hover { background: #0369a1; } QPushButton:disabled { background: #cbd5e1; color: #64748b; }")
        self.btn_importar.clicked.connect(self.confirmar_importacao)
        acoes.addStretch()
        acoes.addWidget(btn_cancelar)
        acoes.addWidget(self.btn_importar)
        layout.addLayout(acoes)

    def escolher_arquivo(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar planilha de pacientes", "", "Planilhas (*.csv *.xlsx)")
        if not caminho:
            return
        try:
            cabecalhos, linhas = ler_planilha(caminho)
            registros, campos_presentes, erros = preparar_registros(cabecalhos, linhas)
            if not registros:
                raise ValueError("Nenhuma linha válida foi encontrada. Verifique a coluna Nome.")
            resposta = self.tela_pacientes.db.supabase.table("pacientes") \
                .select("id, nome, cpf, telefone") \
                .eq("consultorio_id", self.tela_pacientes.db.consultorio_id) \
                .is_("deleted_at", "null") \
                .execute()
            self.registros_classificados = classificar_registros(registros, resposta.data or [])
            self.campos_presentes = campos_presentes
            self.lbl_arquivo.setText(caminho)
            if erros:
                self.lbl_resumo.setText(f"{len(erros)} linha(s) sem nome serão ignoradas. Revise a prévia abaixo.")
            self.atualizar_previa()
        except Exception as erro:
            self.registros_classificados = []
            self.btn_importar.setEnabled(False)
            QMessageBox.warning(self, "Arquivo não importado", str(erro))

    def atualizar_previa(self):
        if not self.registros_classificados:
            return
        modo = self.combo_modo.currentData()
        novos = atualizados = ignorados = 0
        self.tabela_previa.setRowCount(0)
        for indice, item in enumerate(self.registros_classificados):
            dados, existente = item["dados"], item["existente"]
            if item["duplicado_no_arquivo"]:
                resultado = "Ignorado: duplicado na planilha"
                ignorados += 1
            elif existente and modo == "adicionar":
                resultado = "Ignorado: já cadastrado"
                ignorados += 1
            elif existente:
                resultado = "Será atualizado"
                atualizados += 1
            else:
                resultado = "Será adicionado"
                novos += 1
            if indice < 12:
                linha = self.tabela_previa.rowCount()
                self.tabela_previa.insertRow(linha)
                valores = [str(dados["_linha"]), dados["nome"], dados["telefone"], dados["cpf"], resultado]
                for coluna, valor in enumerate(valores):
                    self.tabela_previa.setItem(linha, coluna, QTableWidgetItem(valor))
        total = len(self.registros_classificados)
        self.lbl_resumo.setText(f"Planilha analisada: {total} registro(s) válido(s). {novos} novo(s), {atualizados} atualização(ões) e {ignorados} ignorado(s). A prévia mostra os primeiros 12.")
        self.btn_importar.setEnabled(novos + atualizados > 0)

    def confirmar_importacao(self):
        modo = self.combo_modo.currentData()
        novos = sum(1 for item in self.registros_classificados if not item["existente"] and not item["duplicado_no_arquivo"])
        atualizados = sum(1 for item in self.registros_classificados if item["existente"] and not item["duplicado_no_arquivo"])
        if modo == "adicionar":
            atualizados = 0
        texto = f"Você vai importar {novos} paciente(s) novo(s)"
        if atualizados:
            texto += f" e atualizar {atualizados} cadastro(s) existente(s)"
        texto += ".\n\nDeseja continuar?"
        if QMessageBox.question(self, "Confirmar importação", texto, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        if not iniciar_operacao(self.btn_importar, "Importando..."):
            return
        adicionados = atualizados_ok = falhas = 0
        try:
            for item in self.registros_classificados:
                if item["duplicado_no_arquivo"]:
                    continue
                dados, existente = item["dados"], item["existente"]
                if existente:
                    if modo != "atualizar":
                        continue
                    alteracoes = payload_atualizacao(dados, self.campos_presentes)
                    if alteracoes:
                        self.tela_pacientes.db.supabase.table("pacientes") \
                            .update(alteracoes) \
                            .eq("id", existente["id"]) \
                            .eq("consultorio_id", self.tela_pacientes.db.consultorio_id) \
                            .execute()
                        atualizados_ok += 1
                else:
                    self.tela_pacientes.db.supabase.table("pacientes") \
                        .insert(payload_novo(dados, self.tela_pacientes.db.consultorio_id)) \
                        .execute()
                    adicionados += 1
        except Exception as erro:
            falhas += 1
            registrar_falha("importar pacientes", erro)
        finally:
            finalizar_operacao(self.btn_importar)

        self.tela_pacientes.carregar_pacientes_tabela()
        if falhas:
            QMessageBox.warning(self, "Importação parcialmente concluída", f"{adicionados} adicionado(s) e {atualizados_ok} atualizado(s). Ocorreu uma falha; confira os dados e tente novamente.")
            return
        QMessageBox.information(self, "Importação concluída", f"{adicionados} paciente(s) adicionado(s) e {atualizados_ok} atualizado(s).")
        self.accept()


class PacientesScreen(QWidget):
    def __init__(self, database_instancia):
        super().__init__()
        
        # Recebe a conexão única já configurada e autenticada a partir da MainWindow
        self.db = database_instancia
        
        self.id_em_edicao = -1
        self.row_em_edicao = -1
        self.pastas_cores = {}  # Preenchido pela MainWindow: {nome_da_pasta: "#hex"}
        
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

        self.btn_importar_pacientes = QPushButton("Importar pacientes")
        self.btn_importar_pacientes.setToolTip("Importe uma planilha CSV ou Excel com pacientes já cadastrados")
        self.btn_importar_pacientes.setStyleSheet("""
            QPushButton { background: #dbeafe; color: #075985; border: 1px solid #7dd3fc; border-radius: 6px; padding: 8px 12px; font-weight: bold; min-height: 20px; }
            QPushButton:hover { background: #bae6fd; border-color: #0ea5e9; }
        """)
        self.btn_importar_pacientes.clicked.connect(self.abrir_importador_pacientes)
        filter_layout.addWidget(self.btn_importar_pacientes)

        left_layout.addLayout(filter_layout)
        
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome", "Telefone", "Convênio", "Pasta", ""])
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
        
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for coluna in range(1, 5):
            cabecalho.setSectionResizeMode(coluna, QHeaderView.Stretch)
        cabecalho.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tabela.setColumnWidth(5, 46)
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
        self.input_cpf.setPlaceholderText("000.000.000-00")
        self.input_cpf.setMaxLength(14)
        self.input_cpf.textEdited.connect(self._formatar_cpf_ao_digitar)
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
        self.list_historico_fichas.setFixedHeight(115)
        self.list_historico_fichas.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.list_historico_fichas.setToolTip("Use a roda do mouse ou a barra lateral para ver fichas mais antigas.")
        self.list_historico_fichas.itemDoubleClicked.connect(self.abrir_ficha_historico_selecionada)
        right_layout.addWidget(self.list_historico_fichas)

        acoes_historico = QHBoxLayout()
        acoes_historico.setSpacing(6)
        self.btn_abrir_ficha = QPushButton("Abrir")
        self.btn_abrir_ficha.setStyleSheet(
            "QPushButton { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #93c5fd; "
            "border-radius: 6px; padding: 6px; font-weight: bold; }"
        )
        self.btn_abrir_ficha.clicked.connect(self.abrir_ficha_historico_atual)
        acoes_historico.addWidget(self.btn_abrir_ficha)

        self.btn_editar_ficha = QPushButton("Editar")
        self.btn_editar_ficha.setStyleSheet(
            "QPushButton { background-color: #ecfdf5; color: #047857; border: 1px solid #6ee7b7; "
            "border-radius: 6px; padding: 6px; font-weight: bold; }"
        )
        self.btn_editar_ficha.clicked.connect(self.editar_ficha_historico_selecionada)
        acoes_historico.addWidget(self.btn_editar_ficha)

        self.btn_excluir_ficha = QPushButton("Excluir ficha selecionada")
        self.btn_excluir_ficha.setStyleSheet(
            "QPushButton { background-color: #fff7ed; color: #c2410c; border: 1px solid #fdba74; "
            "border-radius: 6px; padding: 6px; font-weight: bold; }"
        )
        self.btn_excluir_ficha.clicked.connect(self.excluir_ficha_historico_selecionada)
        acoes_historico.addWidget(self.btn_excluir_ficha)
        right_layout.addLayout(acoes_historico)

        self.lbl_retornos = QLabel("↩ Retornos do paciente:")
        self.lbl_retornos.setStyleSheet("color: #334155; font-weight: bold; margin-top: 4px;")
        right_layout.addWidget(self.lbl_retornos)
        self.list_retornos = QListWidget()
        self.list_retornos.setFixedHeight(78)
        self.list_retornos.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_retornos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.list_retornos.setToolTip("Duplo clique para abrir o retorno na Agenda")
        self.list_retornos.setStyleSheet("""
            QListWidget { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; color: #0f172a; }
            QListWidget::item { padding: 5px 7px; border-bottom: 1px solid #e2e8f0; }
            QListWidget::item:hover { background: #eff6ff; color: #0369a1; }
            QListWidget::item:selected { background: #dbeafe; color: #0f172a; }
        """)
        self.list_retornos.itemSelectionChanged.connect(self._atualizar_acoes_retorno)
        self.list_retornos.itemDoubleClicked.connect(self.abrir_retorno_na_agenda)
        right_layout.addWidget(self.list_retornos)

        acoes_retornos = QVBoxLayout()
        acoes_retornos.setSpacing(6)
        self.btn_agendar_retorno = QPushButton("Agendar retorno")
        self.btn_agendar_retorno.setMinimumHeight(32)
        self.btn_agendar_retorno.setStyleSheet("QPushButton { background: #eff6ff; color: #0369a1; border: 1px solid #93c5fd; border-radius: 5px; padding: 6px 10px; font-weight: bold; } QPushButton:hover { background: #dbeafe; }")
        self.btn_agendar_retorno.clicked.connect(self.agendar_retorno_selecionado)
        acoes_retornos.addWidget(self.btn_agendar_retorno)
        self.btn_nao_retorno = QPushButton("Não retornará")
        self.btn_nao_retorno.setMinimumHeight(32)
        self.btn_nao_retorno.setStyleSheet("QPushButton { background: #fff7ed; color: #c2410c; border: 1px solid #fdba74; border-radius: 5px; padding: 6px 10px; font-weight: bold; } QPushButton:hover { background: #ffedd5; }")
        self.btn_nao_retorno.clicked.connect(lambda: self.alterar_status_retorno_selecionado("Não retornou"))
        acoes_retornos.addWidget(self.btn_nao_retorno)
        right_layout.addLayout(acoes_retornos)
        self._atualizar_acoes_retorno()
        
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
        self.combo_filtro_pasta.setStyleSheet(self.combo_filtro_pasta.styleSheet() + combobox_dropdown_style)
        
        main_layout.addWidget(self.right_container)
        self.carregar_pacientes_tabela()
        self._marcar_formulario_salvo()

    def _estado_formulario_atual(self):
        return (
            self.input_nome.text(), self.input_tel.text(), self.input_nasc.date().toString("yyyy-MM-dd"),
            self.input_convenio.text(), self.input_pasta.currentText(), self.input_sexo.currentText(),
            self.input_cpf.text(), self.input_rg.text(), self.input_civil.text(), self.input_profissao.text(),
            self.input_endereco.text(), self.input_qp.toPlainText(), self.id_em_edicao,
        )

    def abrir_importador_pacientes(self):
        if not self.db.supabase:
            self.mostrar_alerta_seguro("error", "Sem conexão", "Não há uma conexão segura ativa. Feche e abra o aplicativo novamente.")
            return
        ImportarPacientesDialog(self).exec()

    def _formatar_cpf_ao_digitar(self, texto):
        """Formata somente a exibição; o valor salvo continua só com números."""
        cpf_formatado = formatar_cpf(texto)
        if texto != cpf_formatado:
            self.input_cpf.setText(cpf_formatado)
            self.input_cpf.setCursorPosition(len(cpf_formatado))

    def _definir_cpf_no_campo(self, valor):
        self.input_cpf.setText(formatar_cpf(valor))

    def _marcar_formulario_salvo(self):
        self._estado_formulario_salvo = self._estado_formulario_atual()

    def tem_alteracoes_nao_salvas(self):
        return self._estado_formulario_atual() != getattr(self, "_estado_formulario_salvo", None)

    def descartar_alteracoes_nao_salvas(self):
        self.limpar_formulario()

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
            if not self.db.supabase:
                return
            try:
                resposta = self.db.supabase.table("pacientes")\
                    .select("id, nome, telefone, convenio, pasta")\
                    .eq("consultorio_id", self.db.consultorio_id)\
                    .is_("deleted_at", "null")\
                    .order("nome", desc=False)\
                    .execute()
                
                if resposta.data:
                    rows = [
                        (r["id"], r.get("nome", ""), r.get("telefone", ""), r.get("convenio", ""), r.get("pasta", ""))
                        for r in resposta.data
                    ]
                else:
                    rows = []
            except Exception as e:
                print(f"Erro ao obter pacientes do Supabase: {e}")
                rows = []
                
        # Índice da coluna "pasta" dentro de cada tupla de row_data (id, nome, telefone, convenio, pasta)
        indice_coluna_pasta = 4

        # Evita repintar a grade para cada paciente carregado.
        self.tabela.setUpdatesEnabled(False)
        for row_idx, row_data in enumerate(rows):
            self.tabela.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value if value is not None else ""))

                if col_idx == indice_coluna_pasta and value:
                    cor_hex = self.pastas_cores.get(str(value), None)
                    if cor_hex:
                        cor_qt = QColor(cor_hex)
                        item.setForeground(cor_qt)
                        cor_fundo = QColor(cor_hex)
                        cor_fundo.setAlpha(28)  # badge suave, não cobre o texto
                        item.setBackground(cor_fundo)
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

                self.tabela.setItem(row_idx, col_idx, item)

            paciente_id = row_data[0]
            nome_paciente = str(row_data[1] or "")
            btn_excluir_linha = QPushButton("×")
            btn_excluir_linha.setToolTip(f"Excluir {nome_paciente}")
            btn_excluir_linha.setFixedSize(30, 30)
            btn_excluir_linha.setStyleSheet("""
                QPushButton {
                    color: #dc2626;
                    background-color: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 6px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #fee2e2; border-color: #f87171; }
            """)
            btn_excluir_linha.clicked.connect(
                lambda _, pid=paciente_id, nome=nome_paciente: self.excluir_paciente_por_id(pid, nome)
            )
            celula_exclusao = QWidget()
            layout_celula = QHBoxLayout(celula_exclusao)
            layout_celula.setContentsMargins(0, 0, 0, 0)
            layout_celula.addWidget(btn_excluir_linha, alignment=Qt.AlignmentFlag.AlignCenter)
            self.tabela.setCellWidget(row_idx, 5, celula_exclusao)
            self.tabela.setRowHeight(row_idx, 38)
        self.tabela.setUpdatesEnabled(True)

    def carregar_paciente_selecionado(self):
        item_selecionado = self.tabela.selectedItems()
        if not item_selecionado:
            self.btn_excluir.setVisible(False)
            return
            
        self.row_em_edicao = self.tabela.currentRow()
        self.id_em_edicao = int(self.tabela.item(self.row_em_edicao, 0).text())
        
        if not self.db.supabase:
            return

        try:
            resposta = self.db.supabase.table("pacientes")\
                .select("nome, telefone, nascimento, convenio, pasta, sexo, cpf, rg, estado_civil, profissao, endereco, queixa")\
                .eq("id", self.id_em_edicao)\
                .eq("consultorio_id", self.db.consultorio_id)\
                .maybe_single()\
                .execute()
            
            p = resposta.data
            if p:
                self.lbl_form_titulo.setText("📝 Editando Prontuário")
                self.input_nome.setText(p.get("nome") or "")
                self.input_tel.setText(p.get("telefone") or "")
                
                try:
                    nasc_str = p.get("nascimento")
                    if nasc_str:
                        self.input_nasc.setDate(QDate.fromString(nasc_str, "yyyy-MM-dd"))
                    else:
                        self.input_nasc.setDate(QDate(1990, 1, 1))
                except:
                    self.input_nasc.setDate(QDate(1990, 1, 1))
                    
                self.input_convenio.setText(p.get("convenio") or "PARTICULAR")
                self.input_pasta.setCurrentText(p.get("pasta") or "")
                self.input_sexo.setCurrentText(p.get("sexo") or "Masculino")
                self._definir_cpf_no_campo(p.get("cpf"))
                self.input_rg.setText(p.get("rg") or "")
                self.input_civil.setText(p.get("estado_civil") or "")
                self.input_profissao.setText(p.get("profissao") or "")
                self.input_endereco.setText(p.get("endereco") or "")
                self.input_qp.setPlainText(p.get("queixa") or "")
                
                self.btn_excluir.setVisible(True)
                self._marcar_formulario_salvo()
        except Exception as e:
            print(f"Erro ao carregar dados de texto do paciente: {e}")
            
        self.carregar_historico_fichas_paciente(self.id_em_edicao)
        self.carregar_retornos_paciente(self.id_em_edicao)

    def carregar_historico_fichas_paciente(self, p_id):
        self.list_historico_fichas.clear()
        if not self.db.supabase:
            return
        try:
            resposta = self.db.supabase.table("fichas_preenchidas")\
                .select("id, modelo_nome, data_atendimento, dados_respostas")\
                .eq("paciente_id", p_id)\
                .eq("consultorio_id", self.db.consultorio_id)\
                .is_("deleted_at", "null")\
                .order("id", desc=True)\
                .execute()
            
            if resposta.data:
                for f in resposta.data:
                    w_item = QListWidgetItem(f"📄 {f['modelo_nome']} ({f['data_atendimento']})")
                    f_tuple = (f["id"], f["modelo_nome"], f["data_atendimento"], f["dados_respostas"])
                    w_item.setData(Qt.UserRole, f_tuple)
                    self.list_historico_fichas.addItem(w_item)
        except Exception as e:
            print(f"Erro ao buscar histórico de fichas no banco: {e}")

    def carregar_retornos_paciente(self, paciente_id):
        self.list_retornos.clear()
        if not hasattr(self.db, "listar_retornos_paciente"):
            return
        retornos = self.db.listar_retornos_paciente(paciente_id)
        for retorno in retornos:
            data = QDate.fromString(str(retorno.get("data_prevista") or ""), "yyyy-MM-dd")
            data_texto = data.toString("dd/MM/yyyy") if data.isValid() else "Data não informada"
            status = str(retorno.get("status") or "Pendente")
            motivo = str(retorno.get("motivo") or "").strip()
            icone = {"Pendente": "🟠", "Agendado": "🔵", "Concluído": "🟢", "Não retornou": "🔴", "Cancelado": "⚪"}.get(status, "•")
            texto = f"{icone} {data_texto} — {status}"
            if motivo and motivo != "Retorno criado após consulta realizada":
                texto += f" | {motivo}"
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, retorno)
            self.list_retornos.addItem(item)
        self._atualizar_acoes_retorno()

    def _atualizar_acoes_retorno(self):
        """Só libera ações quando existe uma pendência válida selecionada."""
        item = self.list_retornos.currentItem() if hasattr(self, "list_retornos") else None
        retorno = item.data(Qt.ItemDataRole.UserRole) if item else None
        pendente = bool(retorno and retorno.get("status") == "Pendente")
        if hasattr(self, "btn_agendar_retorno"):
            self.btn_agendar_retorno.setEnabled(pendente)
        if hasattr(self, "btn_nao_retorno"):
            self.btn_nao_retorno.setEnabled(pendente)

    def _retorno_selecionado(self):
        item = self.list_retornos.currentItem()
        if not item:
            self.mostrar_alerta_seguro("warning", "Selecione um retorno", "Clique em um retorno da lista primeiro.")
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def agendar_retorno_selecionado(self):
        retorno = self._retorno_selecionado()
        if not retorno:
            return
        if retorno.get("status") != "Pendente":
            self.mostrar_alerta_seguro("warning", "Retorno já tratado", "Somente retornos pendentes podem ser enviados para a Agenda.")
            return
        data_prevista = self._escolher_data_retorno()
        if not data_prevista:
            return
        if not self.db.definir_data_retorno(retorno.get("id"), data_prevista):
            self.mostrar_alerta_seguro("error", "Data não salva", "Não foi possível preparar o retorno para a Agenda.")
            return
        retorno["data_prevista"] = data_prevista
        retorno["paciente_nome"] = self.input_nome.text().strip()
        janela = getattr(self, "window_principal", None)
        if janela and hasattr(janela, "agendar_retorno_do_painel"):
            janela.agendar_retorno_do_painel(retorno)

    def abrir_retorno_na_agenda(self, item):
        """Abre o retorno no dia previsto; pendências sem data pedem agendamento."""
        retorno = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not retorno:
            return
        data = QDate.fromString(str(retorno.get("data_prevista") or ""), "yyyy-MM-dd")
        if not data.isValid() and retorno.get("status") == "Pendente":
            self.agendar_retorno_selecionado()
            return
        if not data.isValid():
            self.mostrar_alerta_seguro(
                "warning", "Data não definida", "Defina a data do retorno antes de abrir a Agenda."
            )
            return
        janela = getattr(self, "window_principal", None)
        if janela and hasattr(janela, "abrir_retorno_na_agenda"):
            janela.abrir_retorno_na_agenda(retorno)

    def _escolher_data_retorno(self):
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Agendar retorno")
        dialogo.setMinimumWidth(350)
        layout = QVBoxLayout(dialogo)
        layout.addWidget(QLabel("Escolha a data prevista para o retorno:"))
        campo_data = QDateEdit()
        campo_data.setCalendarPopup(True)
        campo_data.setDisplayFormat("dd/MM/yyyy")
        campo_data.setDate(QDate.currentDate().addDays(30))
        layout.addWidget(campo_data)
        botoes = QHBoxLayout()
        botoes.addStretch()
        cancelar = QPushButton("Cancelar")
        continuar = QPushButton("Abrir Agenda")
        continuar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: bold; } QPushButton:hover { background: #0369a1; }")
        cancelar.clicked.connect(dialogo.reject)
        continuar.clicked.connect(dialogo.accept)
        botoes.addWidget(cancelar)
        botoes.addWidget(continuar)
        layout.addLayout(botoes)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return ""
        return campo_data.date().toString("yyyy-MM-dd")

    def alterar_status_retorno_selecionado(self, novo_status):
        retorno = self._retorno_selecionado()
        if not retorno:
            return
        if retorno.get("status") == novo_status:
            return
        if novo_status in {"Não retornou", "Cancelado"}:
            confirmar = QMessageBox.question(
                self, "Confirmar alteração",
                f"Deseja marcar este retorno como '{novo_status}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmar != QMessageBox.StandardButton.Yes:
                return
        if self.db.atualizar_status_retorno(retorno.get("id"), novo_status):
            self.carregar_retornos_paciente(self.id_em_edicao)
            janela = getattr(self, "window_principal", None)
            if janela and hasattr(janela, "screen_home"):
                janela.screen_home.carregar_dados_iniciais()
        else:
            self.mostrar_alerta_seguro("error", "Status não alterado", "Não foi possível atualizar o retorno agora. Tente novamente.")

    def abrir_ficha_historico_selecionada(self, item):
        dados = item.data(Qt.UserRole)
        if dados: 
            VisualizarFichaHistoricoDialog(dados[1], dados[2], dados[3], self).exec()

    def abrir_ficha_historico_atual(self):
        item = self.list_historico_fichas.currentItem()
        if not item:
            self.mostrar_alerta_seguro("warning", "Selecione uma ficha", "Clique na ficha que deseja abrir primeiro.")
            return
        self.abrir_ficha_historico_selecionada(item)

    def editar_ficha_historico_selecionada(self):
        item = self.list_historico_fichas.currentItem()
        if not item:
            self.mostrar_alerta_seguro("warning", "Selecione uma ficha", "Clique na ficha que deseja editar primeiro.")
            return
        dados = item.data(Qt.UserRole)
        if not dados:
            return

        janela = getattr(self, "window_principal", None)
        if janela and hasattr(janela, "editar_ficha_preenchida"):
            janela.editar_ficha_preenchida(dados[0])
            return

        def salvar_respostas(respostas_atualizadas):
            if self.db.atualizar_respostas_ficha(dados[0], respostas_atualizadas):
                self.carregar_historico_fichas_paciente(self.id_em_edicao)
                return True
            self.mostrar_alerta_seguro("error", "Não foi possível salvar", "As alterações da ficha não foram salvas.")
            return False

        EditarFichaHistoricoDialog(dados[1], dados[3], salvar_respostas, self).exec()

    def excluir_ficha_historico_selecionada(self):
        item = self.list_historico_fichas.currentItem()
        if not item:
            self.mostrar_alerta_seguro("warning", "Selecione uma ficha", "Clique na ficha que deseja excluir primeiro.")
            return
        dados = item.data(Qt.UserRole)
        if not dados:
            return
        confirmar = QMessageBox.question(
            self, "Excluir ficha", "A ficha será removida da lista, mas permanecerá preservada no histórico clínico.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return
        if self.db.soft_delete_ficha(dados[0]):
            self.carregar_historico_fichas_paciente(self.id_em_edicao)
        else:
            self.mostrar_alerta_seguro("error", "Não foi possível excluir", "A ficha não foi removida.")

    def filtrar_pacientes(self):
        texto = self.input_busca.text().lower().strip()
        pasta_filtro = self.combo_filtro_pasta.currentText()
        
        if not self.db.supabase:
            return
            
        try:
            resposta = self.db.supabase.table("pacientes")\
                .select("id, nome, telefone, convenio, pasta, cpf, rg")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .is_("deleted_at", "null")\
                .order("nome", desc=False)\
                .execute()
            
            todos = resposta.data or []
            filtrados = []
            for p in todos:
                nome = str(p.get("nome") or "").lower()
                fone = str(p.get("telefone") or "").lower()
                conv = str(p.get("convenio") or "").lower()
                pasta = str(p.get("pasta") or "").strip() or "Geral"
                cpf = normalizar_cpf(p.get("cpf"))
                rg = str(p.get("rg") or "").lower()
                
                cpf_busca = normalizar_cpf(texto)
                match_cpf = bool(cpf_busca) and cpf_busca in cpf
                match_texto = not texto or (texto in nome or texto in fone or texto in conv or texto in rg or match_cpf)
                match_pasta = "Todas as Pastas" in pasta_filtro or pasta == pasta_filtro
                
                if match_texto and match_pasta:
                    filtrados.append((p["id"], p.get("nome") or "", p.get("telefone") or "", p.get("convenio") or "", pasta))
                    
            self.carregar_pacientes_tabela(filtrados)
        except Exception as e:
            print(f"Erro ao filtrar pacientes: {e}")

    def filtrar_por_pasta_externo(self, nome_pasta):
        self.combo_filtro_pasta.setCurrentText(nome_pasta)
        self.filtrar_pacientes()

    def selecionar_paciente_por_id(self, paciente_id):
        """Localiza a linha do paciente pelo ID e a seleciona, abrindo-o no
        formulário de edição — usado ao abrir um paciente vindo da Home."""
        for row in range(self.tabela.rowCount()):
            item_id = self.tabela.item(row, 0)
            if item_id and item_id.text() == str(paciente_id):
                self.tabela.selectRow(row)
                self.tabela.scrollToItem(item_id)
                return True
        return False

    def salvar_paciente(self):
        nome = self.input_nome.text().strip()
        fone = self.input_tel.text().strip()
        nasc = self.input_nasc.date().toString("yyyy-MM-dd")
        conv = self.input_convenio.text().strip()
        pasta = self.input_pasta.currentText().strip() or "Geral"
        sexo = self.input_sexo.currentText()
        cpf = normalizar_cpf(self.input_cpf.text())
        rg = self.input_rg.text().strip()
        civil = self.input_civil.text().strip()
        prof = self.input_profissao.text().strip()
        end = self.input_endereco.text().strip()
        queixa = self.input_qp.toPlainText().strip()
        
        if not nome:
            self.mostrar_alerta_seguro("warning", "Aviso", "O campo Nome Completo é obrigatório.")
            return
            
        if not self.db.supabase:
            self.mostrar_alerta_seguro(
                "error", "Sem conexão",
                "Não há uma conexão segura ativa. Feche e abra o aplicativo novamente."
            )
            return

        if not iniciar_operacao(self.btn_salvar, "Salvando..."):
            return

        try:
            payload = {
                "consultorio_id": self.db.consultorio_id,
                "nome": nome,
                "telefone": fone,
                "nascimento": nasc,
                "convenio": conv,
                "pasta": pasta,
                "sexo": sexo,
                "cpf": cpf,
                "rg": rg,
                "estado_civil": civil,
                "profissao": prof,
                "endereco": end,
                "queixa": queixa
            }
            
            if self.id_em_edicao == -1:
                self.db.supabase.table("pacientes").insert(payload).execute()
            else:
                self.db.supabase.table("pacientes")\
                    .update(payload)\
                    .eq("id", self.id_em_edicao)\
                    .eq("consultorio_id", self.db.consultorio_id)\
                    .execute()
                
            self.limpar_formulario()
            self.carregar_pacientes_tabela()
            self.mostrar_alerta_seguro("success", "Sucesso", "Prontuário do paciente salvo com sucesso!")
        except Exception as e:
            registrar_falha("salvar paciente", e)
            self.mostrar_alerta_seguro("error", "Não foi possível salvar", mensagem_erro_usuario("salvar o paciente"))
        finally:
            finalizar_operacao(self.btn_salvar)

    def excluir_paciente(self):
        if self.id_em_edicao == -1:
            return

        self.excluir_paciente_por_id(self.id_em_edicao, self.input_nome.text())

    def programar_retorno(self):
        if self.id_em_edicao == -1:
            self.mostrar_alerta_seguro("warning", "Selecione um paciente", "Abra o prontuário do paciente antes de programar um retorno.")
            return

        dialogo = QDialog(self)
        dialogo.setWindowTitle("Programar retorno")
        dialogo.setMinimumWidth(380)
        dialogo.setStyleSheet("""
            QDialog { background: #ffffff; }
            QLabel { color: #334155; font-size: 13px; }
            QLineEdit, QDateEdit {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 7px 9px; min-height: 20px;
            }
            QLineEdit:focus, QDateEdit:focus { border: 1px solid #0284c7; }
            QDateEdit::drop-down {
                border: none; width: 28px; background: #f8fafc;
                border-left: 1px solid #e2e8f0;
            }
            QPushButton {
                background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 8px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        layout = QVBoxLayout(dialogo)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(QLabel(f"Paciente: {self.input_nome.text().strip()}"))
        layout.addWidget(QLabel("Data prevista:"))
        data_prevista = QDateEdit()
        data_prevista.setCalendarPopup(True)
        data_prevista.setDisplayFormat("dd/MM/yyyy")
        data_prevista.setDate(QDate.currentDate().addDays(30))
        linha_data = QHBoxLayout()
        linha_data.addWidget(data_prevista, 1)
        btn_calendario = QPushButton("Calendário")
        btn_calendario.setToolTip("Abrir calendário para escolher a data")
        btn_calendario.clicked.connect(lambda: self.abrir_calendario_retorno(data_prevista))
        linha_data.addWidget(btn_calendario)
        layout.addLayout(linha_data)
        layout.addWidget(QLabel("Motivo do retorno (opcional):"))
        motivo = QLineEdit()
        motivo.setPlaceholderText("Ex: Revisar exames e evolução clínica")
        layout.addWidget(motivo)
        botoes = QHBoxLayout()
        botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_confirmar = QPushButton("Criar retorno")
        btn_confirmar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: none; border-radius: 6px; padding: 8px 14px; font-weight: bold; } QPushButton:hover { background: #0369a1; }")
        btn_cancelar.clicked.connect(dialogo.reject)
        btn_confirmar.clicked.connect(dialogo.accept)
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_confirmar)
        layout.addLayout(botoes)

        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        if self.db.criar_retorno(
            self.id_em_edicao,
            data_prevista.date().toString("yyyy-MM-dd"),
            motivo.text(),
        ):
            self.mostrar_alerta_seguro("success", "Retorno programado", "O retorno foi criado e aparecerá no Painel Principal.")
            janela = getattr(self, "window_principal", None)
            if janela and hasattr(janela, "screen_home"):
                janela.screen_home.carregar_dados_iniciais()
        else:
            self.mostrar_alerta_seguro("error", "Retorno não criado", "Não foi possível criar o retorno agora. Tente novamente.")

    def abrir_calendario_retorno(self, campo_data):
        """Abre um calendário simples, sem impedir a digitação manual da data."""
        calendario_popup = QDialog(self)
        calendario_popup.setWindowTitle("Escolher data do retorno")
        calendario_popup.setStyleSheet("""
            QDialog { background: #ffffff; }
            QCalendarWidget { background: #ffffff; color: #0f172a; }
            QCalendarWidget QWidget { background: #ffffff; color: #0f172a; }
            QCalendarWidget QWidget#qt_calendar_navigationbar { background: #0284c7; }
            QCalendarWidget QToolButton {
                background: #0284c7; color: #ffffff; border: none;
                font-weight: bold; padding: 5px;
            }
            QCalendarWidget QToolButton:hover { background: #0369a1; }
            QCalendarWidget QMenu, QCalendarWidget QSpinBox {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
            }
            QCalendarWidget QTableView {
                background: #ffffff; color: #0f172a;
                selection-background-color: #0284c7; selection-color: #ffffff;
                alternate-background-color: #f8fafc;
                gridline-color: #e2e8f0;
            }
            QCalendarWidget QTableView::item:disabled { color: #94a3b8; }
            QCalendarWidget QAbstractItemView:enabled {
                background: #ffffff; color: #0f172a;
                selection-background-color: #0284c7; selection-color: #ffffff;
            }
        """)
        layout = QVBoxLayout(calendario_popup)
        calendario = QCalendarWidget()
        calendario.setSelectedDate(campo_data.date())
        calendario.setGridVisible(True)
        calendario.clicked.connect(lambda data: (campo_data.setDate(data), calendario_popup.accept()))
        layout.addWidget(calendario)
        calendario_popup.exec()

    def excluir_paciente_por_id(self, paciente_id, nome_paciente):
        """Confirma e executa a exclusão lógica de um paciente."""
        
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
            if not self.db.supabase:
                return
            try:
                if self.db.soft_delete_paciente(paciente_id):
                    if self.id_em_edicao == paciente_id:
                        self.limpar_formulario()
                    self.carregar_pacientes_tabela()
                    self.mostrar_alerta_seguro("success", "Excluído", "O registro foi marcado como excluído (exclusão lógica).")
                else:
                    self.mostrar_alerta_seguro("error", "Erro", "Falha ao excluir registro.")
            except Exception as e:
                self.mostrar_alerta_seguro("error", "Erro", "Falha ao excluir registro.")

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
        self.list_retornos.clear()
        self.tabela.clearSelection()
        self.btn_excluir.setVisible(False)
        self._atualizar_acoes_retorno()
        # Sempre garante que "Geral" (ou a primeira pasta válida) fique
        # selecionada — nunca deixa o combo em branco (índice -1), que
        # antes podia gravar o paciente com pasta="" (invisível na contagem).
        indice_geral = self.input_pasta.findText("Geral")
        if indice_geral != -1:
            self.input_pasta.setCurrentIndex(indice_geral)
        elif self.input_pasta.count() > 0:
            self.input_pasta.setCurrentIndex(0)
        self._marcar_formulario_salvo()

    def preencher_formulario_via_importacao(self, dados):
        self.input_nome.setText(dados.get("nome", ""))
        self.input_tel.setText(dados.get("telefone", ""))
        self._definir_cpf_no_campo(dados.get("cpf", ""))
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
        
        # Filtra nomes vazios/só-espaço, que apareciam como um item "fantasma"
        # (ícone sem texto) no dropdown caso alguma pasta tivesse sido salva
        # com nome em branco em algum momento.
        nomes_adicionados = set()
        for p in lista_pastas:
            nome_limpo = normalizar_nome_pasta(p)
            chave_nome = nome_limpo.casefold()
            if not nome_limpo or chave_nome in nomes_adicionados:
                continue
            nomes_adicionados.add(chave_nome)
            self.combo_filtro_pasta.addItem(nome_limpo)
            self.input_pasta.addItem(nome_limpo)
            
        if self.combo_filtro_pasta.findText(pasta_atual_filtro) != -1:
            self.combo_filtro_pasta.setCurrentText(pasta_atual_filtro)
        if self.input_pasta.findText(pasta_atual_input) != -1:
            self.input_pasta.setCurrentText(pasta_atual_input)
        # Atualizar a lista de pastas pode mudar a selecao padrao do formulario.
        # Isso e uma atualizacao interna, nao uma alteracao feita pelo usuario.
        if self.id_em_edicao == -1:
            self._marcar_formulario_salvo()
