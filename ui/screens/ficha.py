import os
import sqlite3
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QScrollArea, 
                               QFrame, QCheckBox, QTextEdit, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
try:
    from docx import Document
except ImportError:
    Document = None

class FichasScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.init_db()
        self.modelo_atual_campos = [] # Guarda a estrutura dos campos gerados dinamicamente
        self.widgets_dinamicos = {}   # Guarda as referências dos inputs da tela para ler depois
        
        # Layout Principal (Horizontal)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- COLUNA ESQUERDA: Configurações, Paciente e Escolha do Modelo ---
        left_panel = QFrame()
        left_panel.setFixedWidth(320)
        left_panel.setStyleSheet("QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 12px; } QLabel { color: #0f172a; font-weight: 500; font-size: 13px; border: none; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        
        left_layout.addWidget(QLabel("📋 Prontuário & Anamnese"))
        
        # 1. Seleção do Paciente
        left_layout.addWidget(QLabel("1. Selecione o Paciente:"))
        self.combo_paciente = QComboBox()
        self.combo_paciente.setStyleSheet("QComboBox { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; }")
        left_layout.addWidget(self.combo_paciente)
        
        # 2. Seleção ou Importação do Modelo Clínico
        left_layout.addWidget(QLabel("2. Modelo de Ficha Clínica:"))
        self.combo_modelo = QComboBox()
        self.combo_modelo.setStyleSheet("QComboBox { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; }")
        self.combo_modelo.addItems(["Ficha de Consulta Geral (Padrão)", "Anamnese Ortomolecular (Importar .docx)"])
        self.combo_modelo.currentTextChanged.connect(self.alterar_modelo_ficha)
        left_layout.addWidget(self.combo_modelo)
        
        # Botão para Importar do Word
        self.btn_importar = QPushButton("📥 Importar Ficha (.docx)")
        self.btn_importar.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; padding: 10px; font-weight: bold; border-radius: 6px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_importar.clicked.connect(self.importar_modelo_word)
        left_layout.addWidget(self.btn_importar)
        
        left_layout.addStretch()
        
        # Botão de Ação Final: Salvar Atendimento
        self.btn_salvar_atendimento = QPushButton("💾 Salvar Ficha Preenchida")
        self.btn_salvar_atendimento.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 12px; font-weight: bold; border-radius: 6px; font-size: 14px; border: none; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_salvar_atendimento.clicked.connect(self.salvar_ficha_preenchida)
        left_layout.addWidget(self.btn_salvar_atendimento)
        
        main_layout.addWidget(left_panel)
        
        # --- COLUNA DIREITA: Ficha Clínica Gerada Dinamicamente (Com Scroll) ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area para conter fichas gigantescas (como a Ortomolecular)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc; }")
        
        # Conteúdo interno do scroll
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #f8fafc;")
        self.dinamic_form_layout = QVBoxLayout(self.scroll_content)
        self.dinamic_form_layout.setSpacing(12)
        self.dinamic_form_layout.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_area.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(right_container, stretch=3)
        
        # Inicializa carregando a lista de pacientes e o modelo base
        self.carregar_pacientes_combo()
        self.gerar_modelo_padrao()

    def init_db(self):
        """Cria as tabelas necessárias para armazenar as fichas preenchidas."""
        conn = sqlite3.connect("consultorio.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fichas_preenchidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER,
                modelo_nome TEXT,
                dados_respostas TEXT, -- Armazenará as respostas estruturadas
                data_atendimento TEXT
            )
        """)
        conn.commit()
        conn.close()

    def carregar_pacientes_combo(self):
        """Preenche o ComboBox com os pacientes cadastrados no banco de dados local."""
        self.combo_paciente.clear()
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome FROM pacientes ORDER BY nome ASC")
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                self.combo_paciente.addItem(f"👤 {row[1]} (ID: {row[0]})", row[0])
        except Exception as e:
            self.combo_paciente.addItem("Nenhum paciente cadastrado")

    def alterar_modelo_ficha(self, nome_modelo):
        """Monitora a troca de modelos na interface."""
        if "Padrão" in nome_modelo:
            self.gerar_modelo_padrao()

    def gerar_modelo_padrao(self):
        """Estrutura estática de um modelo básico de consulta."""
        self.modelo_atual_campos = [
            {"tipo": "secao", "label": "HISTÓRICO DA CONSULTA ATUAL"},
            {"tipo": "texto_longo", "label": "Queixa Principal (QP)", "id": "qp"},
            {"tipo": "texto_longo", "label": "Histórico da Doença Atual (HDA)", "id": "hda"},
            {"tipo": "secao", "label": "EXAME FÍSICO & SINAIS VITAIS"},
            {"tipo": "texto_curto", "label": "Pressão Arterial (PA)", "id": "pa", "placeholder": "120x80 mmHg"},
            {"tipo": "texto_curto", "label": "Frequência Cardíaca (FC)", "id": "fc", "placeholder": "75 bpm"},
            {"tipo": "secao", "label": "CONDUTA MÉDICA"},
            {"tipo": "texto_longo", "label": "Prescrição / Orientações Passadas", "id": "prescricao"}
        ]
        self.renderizar_formulario_dinamico()

    def importar_modelo_word(self):
        """Abre uma janela para ler arquivos .docx e converte parágrafos em inputs funcionais."""
        if not Document:
            QMessageBox.critical(self, "Erro de Dependência", "A biblioteca 'python-docx' não está instalada.\nExecute 'pip install python-docx' no seu terminal.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Ficha em Word", "", "Arquivos Word (*.docx)")
        if not file_path:
            return
            
        try:
            doc = Document(file_path)
            novos_campos = []
            secao_atual = "Dados Importados"
            
            # Varre os parágrafos do documento Word em busca de campos estruturados
            for p in doc.paragraphs:
                texto = p.text.strip()
                if not texto:
                    continue
                
                # Se o texto for curto e estiver em caixa alta, consideramos um Título de Seção
                if len(texto) < 40 and (texto.isupper() or texto.startswith("---") or texto.endswith(":")):
                    texto_limpo = texto.replace(":", "").replace("-", "").strip()
                    novos_campos.append({"tipo": "secao", "label": texto_limpo})
                    continue
                
                # Procura por estruturas de pergunta ou campos de preenchimento (ex: "Nome:")
                if ":" in texto:
                    partes = texto.split(":")
                    label_campo = partes[0].strip()
                    id_campo = "".join(filter(str.isalnum, label_campo)).lower()
                    
                    # Se houver colchetes, interpretamos como um checkbox de multipla escolha
                    if "[" in texto or "]" in texto:
                        novos_campos.append({"tipo": "checkbox", "label": label_campo, "id": id_campo})
                    else:
                        novos_campos.append({"tipo": "texto_longo" if len(texto) > 60 else "texto_curto", "label": label_campo, "id": id_campo})
            
            if novos_campos:
                self.modelo_atual_campos = novos_campos
                self.renderizar_formulario_dinamico()
                # Atualiza o nome no combobox para indicar sucesso
                self.combo_modelo.setItemText(1, f"✨ {os.path.basename(file_path)}")
                self.combo_modelo.setCurrentIndex(1)
                QMessageBox.information(self, "Sucesso", f"Modelo '{os.path.basename(file_path)}' processado com sucesso!\n{len(novos_campos)} campos gerados na tela.")
            else:
                QMessageBox.warning(self, "Aviso", "Não foi possível extrair campos estruturados do arquivo. Verifique a formatação do texto.")
        except Exception as e:
            QMessageBox.critical(self, "Erro na Leitura", f"Falha ao ler o arquivo Word:\n{str(e)}")

    def renderizar_formulario_dinamico(self):
        """Limpa a área da direita e constrói visualmente os inputs baseados no modelo ativo."""
        # Limpa widgets anteriores com segurança
        while self.dinamic_form_layout.count():
            item = self.dinamic_form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        self.widgets_dinamicos.clear()
        
        # Estilos reutilizáveis para os componentes dinâmicos
        estilo_label = "color: #475569; font-weight: bold; font-size: 12px; margin-top: 5px;"
        estilo_input = "background-color: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 13px;"
        
        for campo in self.modelo_atual_campos:
            tipo = campo.get("tipo")
            label = campo.get("label")
            id_campo = campo.get("id")
            
            if tipo == "secao":
                # Cria uma divisória visual impactante
                secao_frame = QFrame()
                secao_frame.setStyleSheet("background-color: #e2e8f0; max-height: 2px; border: none;")
                
                secao_label = QLabel(label.upper())
                secao_label.setStyleSheet("color: #0369a1; font-weight: 8px; font-size: 14px; font-weight: bold; margin-top: 15px; background: transparent;")
                
                self.dinamic_form_layout.addWidget(secao_label)
                self.dinamic_form_layout.addWidget(secao_frame)
                
            elif tipo == "texto_curto":
                lbl = QLabel(label)
                lbl.setStyleSheet(estilo_label)
                inp = QLineEdit()
                inp.setStyleSheet(estilo_input)
                if "placeholder" in campo:
                    inp.setPlaceholderText(campo["placeholder"])
                self.dinamic_form_layout.addWidget(lbl)
                self.dinamic_form_layout.addWidget(inp)
                self.widgets_dinamicos[id_campo] = ("texto_curto", inp)
                
            elif tipo == "texto_longo":
                lbl = QLabel(label)
                lbl.setStyleSheet(estilo_label)
                inp = QTextEdit()
                inp.setMinimumHeight(80)
                inp.setMaximumHeight(150)
                inp.setStyleSheet("QTextEdit { background-color: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 13px; }")
                self.dinamic_form_layout.addWidget(lbl)
                self.dinamic_form_layout.addWidget(inp)
                self.widgets_dinamicos[id_campo] = ("texto_longo", inp)
                
            elif tipo == "checkbox":
                chk = QCheckBox(label)
                chk.setStyleSheet("QCheckBox { color: #0f172a; font-size: 13px; font-weight: 500; padding: 4px; }")
                self.dinamic_form_layout.addWidget(chk)
                self.widgets_dinamicos[id_campo] = ("checkbox", chk)

        # Adiciona um espaçador no final para o formulário não ficar esticado se for pequeno
        self.dinamic_form_layout.addStretch()

    def salvar_ficha_preenchida(self):
        """Varre os campos gerados, captura as respostas do profissional e salva estruturado."""
        paciente_id = self.combo_paciente.currentData()
        if not paciente_id:
            QMessageBox.warning(self, "Erro", "Selecione um paciente antes de salvar a ficha.")
            return
            
        import json
        from datetime import datetime
        
        # Coleta os valores de cada widget dinâmico de forma mapeada
        respostas = {}
        for id_campo, (tipo, widget) in self.widgets_dinamicos.items():
            if tipo == "texto_curto":
                respostas[id_campo] = widget.text().strip()
            elif tipo == "texto_longo":
                respostas[id_campo] = widget.toPlainText().strip()
            elif tipo == "checkbox":
                respostas[id_campo] = widget.isChecked()
                
        # Transforma o dicionário em uma string JSON limpa para o banco SQL
        string_respostas = json.dumps(respostas, ensure_ascii=False)
        modelo_nome = self.combo_modelo.currentText()
        data_atual = datetime.now().strftime("%d/%M/%Y %H:%M")
        
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fichas_preenchidas (paciente_id, modelo_nome, dados_respostas, data_atendimento)
                VALUES (?, ?, ?, ?)
            """, (paciente_id, modelo_nome, string_respostas, data_atual))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Ficha Salva", "O atendimento e a ficha clínica foram registrados no histórico com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Gravar", f"Não foi possível salvar os dados no banco:\n{str(e)}")