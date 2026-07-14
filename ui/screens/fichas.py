import os
import json
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QScrollArea, 
                               QFrame, QCheckBox, QTextEdit, QFileDialog, QMessageBox, QListView, QDialog)
from PySide6.QtCore import Qt
from database import Database  # Importa o gerenciador de banco de dados unificado

try:
    from docx import Document
    DOCX_DISPONIVEL = True
except ImportError:
    Document = None
    DOCX_DISPONIVEL = False


class CustomInputDialog(QDialog):
    def __init__(self, titulo, mensagem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setFixedWidth(420)
        self.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        self.label = QLabel(mensagem)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: #0f172a !important; font-size: 13px !important; font-weight: 500 !important; background: transparent;")
        layout.addWidget(self.label)
        
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("""
            QLineEdit { 
                background-color: #ffffff !important; 
                color: #0f172a !important; 
                border: 1px solid #cbd5e1 !important; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 13px; 
            }
            QLineEdit:focus { border: 1px solid #0284c7 !important; }
        """)
        layout.addWidget(self.input_field)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setStyleSheet("QPushButton { background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; padding: 7px 14px; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #e2e8f0; }")
        self.btn_cancelar.clicked.connect(self.reject)
        
        self.btn_confirmar = QPushButton("Confirmar")
        self.btn_confirmar.setStyleSheet("QPushButton { background-color: #0284c7; color: white; padding: 7px 14px; border-radius: 5px; font-weight: bold; border: none; } QPushButton:hover { background-color: #0369a1; }")
        self.btn_confirmar.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_confirmar)
        layout.addLayout(btn_layout)

    def get_text(self):
        return self.input_field.text().strip()


class FichasScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.db = Database()  # Instancia a conexão unificada com o Supabase
        self.modelo_atual_campos = [] 
        self.widgets_dinamicos = {}   
        self.modo_criacao = False 
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        # --- COLUNA ESQUERDA: Configurações ---
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(320)
        self.left_panel.setStyleSheet("""
            QFrame { 
                background-color: white; 
                border: 1px solid #e2e8f0; 
                border-radius: 12px; 
            } 
            QLabel { 
                color: #0f172a !important; 
                font-weight: 500; 
                font-size: 13px; 
                border: none; 
                background-color: transparent;
            }
            QComboBox { 
                background-color: #ffffff !important; 
                color: #0f172a !important; 
                border: 1px solid #cbd5e1 !important; 
                border-radius: 6px; 
                padding: 6px; 
            }
        """)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setSpacing(12)
        self.left_layout.setContentsMargins(20, 20, 20, 20)
        
        titulo_painel = QLabel("📋 Prontuário & Anamnese")
        titulo_painel.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a !important;")
        self.left_layout.addWidget(titulo_painel)
        
        self.left_layout.addWidget(QLabel("1. Selecione o Paciente:"))
        self.combo_paciente = QComboBox()
        self.combo_paciente.setView(QListView())
        self.combo_paciente.view().setStyleSheet("QListView { background-color: #ffffff !important; color: #0f172a !important; selection-background-color: #0284c7; }")
        self.left_layout.addWidget(self.combo_paciente)
        
        self.left_layout.addWidget(QLabel("2. Modelo de Ficha Clínica:"))
        self.combo_modelo = QComboBox()
        self.combo_modelo.setView(QListView())
        self.combo_modelo.view().setStyleSheet("QListView { background-color: #ffffff !important; color: #0f172a !important; selection-background-color: #0284c7; }")
        self.left_layout.addWidget(self.combo_modelo)
        
        self.btn_importar = QPushButton("📥 Importar Ficha (.docx)")
        self.btn_importar.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; padding: 10px; font-weight: bold; border-radius: 6px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        self.btn_importar.clicked.connect(self.importar_modelo_word)
        self.left_layout.addWidget(self.btn_importar)
        
        self.btn_criar_modelo = QPushButton("🛠️ Montar Novo Modelo")
        self.btn_criar_modelo.setStyleSheet("""
            QPushButton { background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; padding: 10px; font-weight: bold; border-radius: 6px; }
            QPushButton:hover { background-color: #dcfce7; }
        """)
        self.btn_criar_modelo.clicked.connect(self.iniciar_criacao_modelo)
        self.left_layout.addWidget(self.btn_criar_modelo)
        
        self.left_layout.addStretch()
        
        self.btn_salvar_atendimento = QPushButton("💾 Salvar Ficha Preenchida")
        self.btn_salvar_atendimento.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 12px; font-weight: bold; border-radius: 6px; font-size: 14px; border: none; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_salvar_atendimento.clicked.connect(self.salvar_ficha_preenchida)
        self.left_layout.addWidget(self.btn_salvar_atendimento)
        
        self.main_layout.addWidget(self.left_panel)
        
        # --- COLUNA DIREITA: Container Dinâmico ---
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; border-radius: 12px; background-color: white; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("#ScrollContent { background-color: white; }")
        
        self.dinamic_form_layout = QVBoxLayout(self.scroll_content)
        self.dinamic_form_layout.setSpacing(14)
        self.dinamic_form_layout.setContentsMargins(25, 25, 25, 25)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.right_layout.addWidget(self.scroll_area)
        
        self.main_layout.addWidget(self.right_container, stretch=3)
        
        # Inicialização Segura baseada no Supabase
        self.carregar_modelos_iniciais_combo()
        self.carregar_pacientes_combo()
        self.gerar_modelo_padrao()
        
        self.combo_modelo.currentTextChanged.connect(self.alterar_modelo_ficha)

    def carregar_pacientes_combo(self):
        self.combo_paciente.clear()
        if not self.db.supabase:
            return
        try:
            # Seleciona os pacientes vinculados ao consultório logado
            resposta = self.db.supabase.table("pacientes")\
                .select("id, nome")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .order("nome", desc=False)\
                .execute()
                
            if resposta.data:
                for row in resposta.data:
                    self.combo_paciente.addItem(f"👤 {row['nome']} (ID: {row['id']})", row['id'])
            else:
                self.combo_paciente.addItem("Nenhum paciente cadastrado")
        except Exception as e:
            print(f"Erro ao carregar pacientes do Supabase: {e}")
            self.combo_paciente.addItem("Nenhum paciente cadastrado")

    def carregar_modelos_iniciais_combo(self):
        """Busca modelos de ficha cadastrados na nuvem para o consultório logado."""
        self.combo_modelo.clear()
        self.combo_modelo.addItem("Ficha de Consulta Geral (Padrão)")
        if not self.db.supabase:
            return
        try:
            resposta = self.db.supabase.table("modelos_fichas")\
                .select("nome_modelo")\
                .eq("consultorio_id", self.db.consultorio_id)\
                .order("id", desc=True)\
                .execute()
                
            if resposta.data:
                for m in resposta.data:
                    self.combo_modelo.addItem(m["nome_modelo"])
        except Exception as e:
            print(f"Erro ao carregar modelos do Supabase: {e}")

    def alterar_modelo_ficha(self, nome_modelo):
        if self.modo_criacao or not nome_modelo:
            return
        if "Padrão" in nome_modelo:
            self.gerar_modelo_padrao()
        else:
            if not self.db.supabase:
                return
            try:
                resposta = self.db.supabase.table("modelos_fichas")\
                    .select("estrutura_json")\
                    .eq("consultorio_id", self.db.consultorio_id)\
                    .eq("nome_modelo", nome_modelo)\
                    .maybe_single()\
                    .execute()
                    
                if resposta.data:
                    self.modelo_atual_campos = json.loads(resposta.data["estrutura_json"])
                    self.renderizar_formulario_dinamico()
            except Exception as e:
                print(f"Erro ao obter modelo de ficha: {e}")

    def exibir_popup(self, tipo, titulo, mensagem):
        msg = QMessageBox(self)
        if tipo == "info": msg.setIcon(QMessageBox.Information)
        elif tipo == "aviso": msg.setIcon(QMessageBox.Warning)
        elif tipo == "erro": msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(titulo)
        msg.setText(mensagem)
        msg.setStyleSheet("""
            QMessageBox { background-color: #ffffff !important; }
            QLabel { color: #0f172a !important; font-size: 13px !important; font-weight: 500 !important; }
            QPushButton { background-color: #0284c7 !important; color: white !important; border-radius: 4px; padding: 6px 14px; min-width: 70px; }
            QPushButton:hover { background-color: #0369a1 !important; }
        """)
        msg.exec()

    def limpar_layout_completamente(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self.limpar_layout_completamente(sub_layout)

    def gerar_modelo_padrao(self):
        self.modo_criacao = False
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

    def iniciar_criacao_modelo(self):
        self.modo_criacao = True
        self.modelo_atual_campos = []
        self.widgets_dinamicos.clear()
        
        self.limpar_layout_completamente(self.dinamic_form_layout)
            
        lbl_info = QLabel("🛠️ Construtor de Ficha Personalizada (Modo Preview)")
        lbl_info.setStyleSheet("font-size: 18px; font-weight: bold; color: #0284c7; margin-bottom: 2px;")
        self.dinamic_form_layout.addWidget(lbl_info)
        
        lbl_sub = QLabel("Clique nos botões para adicionar campos. O formulário abaixo atualiza em tempo real:")
        lbl_sub.setStyleSheet("color: #64748b; font-size: 13px; margin-bottom: 12px;")
        self.dinamic_form_layout.addWidget(lbl_sub)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        btn_add_secao = QPushButton("+ Seção (Título)")
        btn_add_curto = QPushButton("+ Texto Curto")
        btn_add_longo = QPushButton("+ Texto Longo")
        btn_add_check = QPushButton("+ Caixa de Seleção")
        
        estilo_botoes_add = """
            QPushButton { background-color: #f8fafc; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px; font-weight: bold; font-size: 12px;}
            QPushButton:hover { background-color: #f1f5f9; border: 1px solid #94a3b8; }
        """
        for b in [btn_add_secao, btn_add_curto, btn_add_longo, btn_add_check]:
            b.setStyleSheet(estilo_botoes_add)
            btn_layout.addWidget(b)
            
        btn_add_secao.clicked.connect(lambda: self.adicionar_elemento_rascunho("secao"))
        btn_add_curto.clicked.connect(lambda: self.adicionar_elemento_rascunho("texto_curto"))
        btn_add_longo.clicked.connect(lambda: self.adicionar_elemento_rascunho("texto_longo"))
        btn_add_check.clicked.connect(lambda: self.adicionar_elemento_rascunho("checkbox"))
        
        self.dinamic_form_layout.addLayout(btn_layout)
        
        sep = QFrame()
        sep.setStyleSheet("background-color: #cbd5e1; max-height: 2px; border: none; margin: 15px 0 5px 0;")
        self.dinamic_form_layout.addWidget(sep)
        
        self.preview_layout = QVBoxLayout()
        self.preview_layout.setSpacing(12)
        self.dinamic_form_layout.addLayout(self.preview_layout)
        
        sep_bottom = QFrame()
        sep_bottom.setStyleSheet("background-color: #e2e8f0; max-height: 1px; border: none; margin-top: 20px;")
        self.dinamic_form_layout.addWidget(sep_bottom)
        
        acoes_layout = QHBoxLayout()
        acoes_layout.setContentsMargins(0, 10, 0, 0)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("QPushButton { background-color: #ef4444; color: white; padding: 11px 20px; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #dc2626; }")
        btn_cancelar.clicked.connect(self.gerar_modelo_padrao)
        
        btn_finalizar = QPushButton("💾 Concluir e Salvar Modelo")
        btn_finalizar.setStyleSheet("QPushButton { background-color: #16a34a; color: white; padding: 11px 24px; border-radius: 6px; font-weight: bold; border: none; } QPushButton:hover { background-color: #15803d; }")
        btn_finalizar.clicked.connect(self.salvar_modelo_customizado_db)
        
        acoes_layout.addWidget(btn_cancelar)
        acoes_layout.addStretch()
        acoes_layout.addWidget(btn_finalizar)
        self.dinamic_form_layout.addLayout(acoes_layout)
        
        self.atualizar_visualizacao_preview()

    def adicionar_elemento_rascunho(self, tipo):
        dialog_tit = "Nova Seção" if tipo == "secao" else "Novo Campo"
        dialog_msg = "Digite o título da seção divisor:" if tipo == "secao" else "Digite o nome da pergunta/campo (ex: Histórico Familiar):"
        
        dial = CustomInputDialog(dialog_tit, dialog_msg, self)
        if dial.exec() == QDialog.Accepted:
            texto = dial.get_text()
            if not texto: return
        else:
            return
            
        texto_limpo = "".join(c for c in texto if c.isalnum()).lower()
        id_campo = f"custom_{int(datetime.now().timestamp())}_{texto_limpo}"
        self.modelo_atual_campos.append({"tipo": tipo, "label": texto, "id": id_campo})
        
        self.atualizar_visualizacao_preview()

    def atualizar_visualizacao_preview(self):
        self.limpar_layout_completamente(self.preview_layout)
        
        if not self.modelo_atual_campos:
            lbl_vazio = QLabel("(Nenhum campo adicionado ainda. Monte sua estrutura clicando nos botões acima...)")
            lbl_vazio.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 13px; padding: 20px; text-align: center;")
            lbl_vazio.setAlignment(Qt.AlignCenter)
            self.preview_layout.addWidget(lbl_vazio)
            return

        estilo_label = "color: #334155 !important; font-weight: bold; font-size: 13px; margin-top: 4px; background-color: transparent;"
        estilo_input_curto = "QLineEdit { background-color: #f8fafc !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; border-radius: 6px; padding: 8px 12px; font-size: 13px; }"
        estilo_input_longo = "QTextEdit { background-color: #f8fafc !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; border-radius: 6px; padding: 8px 12px; font-size: 13px; }"

        for campo in self.modelo_atual_campos:
            tipo = campo.get("tipo")
            label = campo.get("label")
            
            if tipo == "secao":
                container = QWidget()
                lay = QVBoxLayout(container)
                lay.setContentsMargins(0, 10, 0, 4)
                secao_label = QLabel(label.upper())
                secao_label.setStyleSheet("color: #0284c7 !important; font-size: 14px; font-weight: bold; background-color: transparent;")
                secao_frame = QFrame()
                secao_frame.setStyleSheet("background-color: #cbd5e1 !important; max-height: 1px; border: none;")
                lay.addWidget(secao_label)
                lay.addWidget(secao_frame)
                self.preview_layout.addWidget(container)
                
            elif tipo == "texto_curto":
                lbl = QLabel(label)
                lbl.setStyleSheet(estilo_label)
                inp = QLineEdit()
                inp.setPlaceholderText("Área de Visualização do Input Curto")
                inp.setReadOnly(True)
                inp.setStyleSheet(estilo_input_curto)
                self.preview_layout.addWidget(lbl)
                self.preview_layout.addWidget(inp)
                
            elif tipo == "texto_longo":
                lbl = QLabel(label)
                lbl.setStyleSheet(estilo_label)
                inp = QTextEdit()
                inp.setPlaceholderText("Área de Visualização do Input Longo")
                inp.setReadOnly(True)
                inp.setMinimumHeight(50)
                inp.setMaximumHeight(70)
                inp.setStyleSheet(estilo_input_longo)
                self.preview_layout.addWidget(lbl)
                self.preview_layout.addWidget(inp)
                
            elif tipo == "checkbox":
                chk = QCheckBox(label)
                chk.setEnabled(False)
                chk.setStyleSheet("QCheckBox { color: #0f172a !important; font-size: 13px; font-weight: 500; padding: 4px; background-color: transparent; }")
                self.preview_layout.addWidget(chk)

        self.scroll_content.adjustSize()

    def salvar_modelo_customizado_db(self):
        if not self.modelo_atual_campos:
            self.exibir_popup("aviso", "Modelo Vazio", "Adicione pelo menos um campo antes de salvar.")
            return
            
        dial = CustomInputDialog("Salvar Modelo", "Dê um nome para este novo modelo de ficha:", self)
        if dial.exec() == QDialog.Accepted:
            nome_modelo = dial.get_text()
            if not nome_modelo: return
        else:
            return
            
        estrutura_json = json.dumps(self.modelo_atual_campos, ensure_ascii=False)
        
        if not self.db.supabase:
            return
            
        try:
            payload = {
                "consultorio_id": self.db.consultorio_id,
                "nome_modelo": nome_modelo,
                "estrutura_json": estrutura_json
            }
            
            # Executa o upsert para evitar duplicações de modelos dentro do mesmo consultório
            self.db.supabase.table("modelos_fichas").upsert(
                payload, 
                on_conflict="consultorio_id,nome_modelo"
            ).execute()
            
            self.modo_criacao = False
            self.carregar_modelos_iniciais_combo()
            self.combo_modelo.setCurrentText(nome_modelo)
            self.renderizar_formulario_dinamico()
            
            self.exibir_popup("info", "Sucesso!", f"O modelo '{nome_modelo}' foi gravado no banco de dados e já está pronto para uso!")
        except Exception as e:
            self.exibir_popup("erro", "Erro ao Salvar", f"Falha ao gravar no banco:\n{str(e)}")

    def importar_modelo_word(self):
        if not DOCX_DISPONIVEL or Document is None:
            self.exibir_popup("erro", "Módulo Ausente", "A biblioteca 'python-docx' é necessária.\npip install python-docx")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Ficha em Word", "", "Arquivos Word (*.docx)")
        if not file_path: return
            
        try:
            doc = Document(file_path)
            linhas_texto = []
            
            for p in doc.paragraphs:
                t = p.text.strip()
                if t: linhas_texto.append(t)
            
            for tabela in doc.tables:
                for row_tab in tabela.rows:
                    valores_celulas = [c.text.strip() for c in row_tab.cells if c.text.strip()]
                    for val in valores_celulas:
                        for sub_val in val.split('\n'):
                            if sub_val.strip() and sub_val.strip() not in linhas_texto:
                                rastro = sub_val.strip()
                                if rastro.replace(",", "").strip():
                                    linhas_texto.append(rastro)
            
            novos_campos = []
            chaves_existentes = set()
            
            for texto in linhas_texto:
                if ":" in texto:
                    partes = texto.split(":")
                    label_campo = partes[0].replace(",", "").replace("-", "").strip()
                    
                    if not label_campo or len(label_campo) < 2 or len(label_campo) > 60:
                        continue
                    
                    id_campo = "".join(c for c in label_campo if c.isalnum()).lower()
                    if id_campo in chaves_existentes: continue
                    chaves_existentes.add(id_campo)
                    
                    if "[" in texto or "]" in texto or "( )" in texto:
                        novos_campos.append({"tipo": "checkbox", "label": label_campo, "id": id_campo})
                    else:
                        id_min = id_campo.lower()
                        if any(x in id_min for x in ["qp", "hda", "conduta", "antecedentes", "historico", "outros", "medicamentos", "observacoes"]):
                            tipo_campo = "texto_longo"
                        else:
                            tipo_campo = "texto_curto"
                        novos_campos.append({"tipo": tipo_campo, "label": label_campo, "id": id_campo})
                
                elif len(texto) < 50 and (texto.isupper() or len(texto) < 30):
                    texto_limpo = texto.replace("-", "").replace(",", "").strip()
                    if texto_limpo and len(texto_limpo) > 2:
                        novos_campos.append({"tipo": "secao", "label": texto_limpo})

            if novos_campos:
                self.modo_criacao = False
                self.modelo_atual_campos = novos_campos
                self.renderizar_formulario_dinamico()
                
                nome_reduzido = os.path.basename(file_path)
                if self.combo_modelo.findText(f"✨ {nome_reduzido}") == -1:
                    self.combo_modelo.addItem(f"✨ {nome_reduzido}")
                self.combo_modelo.setCurrentText(f"✨ {nome_reduzido}")
                self.exibir_popup("info", "Sucesso", f"Modelo carregado!\n{len(novos_campos)} elementos criados.")
            else:
                self.exibir_popup("aviso", "Aviso", "Nenhum campo estruturado foi identificado.")
        except Exception as e:
            self.exibir_popup("erro", "Falha de Leitura", f"Erro:\n{str(e)}")

    def renderizar_formulario_dinamico(self):
        self.limpar_layout_completamente(self.dinamic_form_layout)
        self.widgets_dinamicos.clear()
        
        estilo_label = "color: #334155 !important; font-weight: bold; font-size: 13px; margin-top: 8px; background-color: transparent;"
        estilo_input_curto = """
            QLineEdit { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; border-radius: 6px; padding: 8px 12px; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #0284c7 !important; }
        """
        estilo_input_longo = """
            QTextEdit { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; border-radius: 6px; padding: 8px 12px; font-size: 13px; }
            QTextEdit:focus { border: 1px solid #0284c7 !important; }
        """
        
        for campo in self.modelo_atual_campos:
            tipo = campo.get("tipo")
            label = campo.get("label")
            id_campo = campo.get("id")
            
            if tipo == "secao":
                secao_frame = QFrame()
                secao_frame.setStyleSheet("background-color: #cbd5e1 !important; max-height: 1px; border: none; margin-top: 4px;")
                secao_label = QLabel(label.upper())
                secao_label.setStyleSheet("color: #0284c7 !important; font-size: 14px; font-weight: bold; margin-top: 18px; background-color: transparent;")
                self.dinamic_form_layout.addWidget(secao_label)
                self.dinamic_form_layout.addWidget(secao_frame)
                
            elif tipo == "texto_curto":
                lbl = QLabel(label)
                lbl.setStyleSheet(estilo_label)
                inp = QLineEdit()
                inp.setStyleSheet(estilo_input_curto)
                if "placeholder" in campo: inp.setPlaceholderText(campo["placeholder"])
                self.dinamic_form_layout.addWidget(lbl)
                self.dinamic_form_layout.addWidget(inp)
                self.widgets_dinamicos[id_campo] = ("texto_curto", inp)
                
            elif tipo == "texto_longo":
                lbl = QLabel(label)
                lbl.setStyleSheet(estilo_label)
                inp = QTextEdit()
                inp.setMinimumHeight(65)
                inp.setMaximumHeight(120)
                inp.setStyleSheet(estilo_input_longo)
                self.dinamic_form_layout.addWidget(lbl)
                self.dinamic_form_layout.addWidget(inp)
                self.widgets_dinamicos[id_campo] = ("texto_longo", inp)
                
            elif tipo == "checkbox":
                chk = QCheckBox(label)
                chk.setStyleSheet("QCheckBox { color: #0f172a !important; font-size: 13px; font-weight: 500; padding: 4px; background-color: transparent; }")
                self.dinamic_form_layout.addWidget(chk)
                self.widgets_dinamicos[id_campo] = ("checkbox", chk)

        self.dinamic_form_layout.addStretch()
        self.scroll_content.adjustSize()

    def salvar_ficha_preenchida(self):
        if self.modo_criacao:
            self.exibir_popup("aviso", "Modo Construtor", "Você está editando um modelo de ficha. Clique em 'Concluir' primeiro.")
            return
            
        paciente_id = self.combo_paciente.currentData()
        if not paciente_id:
            self.exibir_popup("aviso", "Erro", "Selecione um paciente antes de salvar a ficha.")
            return
        
        respostas = {}
        for id_campo, (tipo, widget) in self.widgets_dinamicos.items():
            if tipo == "texto_curto": respostas[id_campo] = widget.text().strip()
            elif tipo == "texto_longo": respostas[id_campo] = widget.toPlainText().strip()
            elif tipo == "checkbox": respostas[id_campo] = widget.isChecked()
                
        string_respostas = json.dumps(respostas, ensure_ascii=False)
        modelo_nome = self.combo_modelo.currentText()
        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        if not self.db.supabase:
            return
            
        try:
            payload = {
                "consultorio_id": self.db.consultorio_id,
                "paciente_id": paciente_id,
                "modelo_nome": modelo_nome,
                "dados_respostas": string_respostas,
                "data_atendimento": data_atual
            }
            
            self.db.supabase.table("fichas_preenchidas").insert(payload).execute()
            
            # Limpa os campos após salvar com sucesso
            for tipo, widget in self.widgets_dinamicos.values():
                if tipo == "texto_curto": widget.clear()
                elif tipo == "texto_longo": widget.clear()
                elif tipo == "checkbox": widget.setChecked(False)
                
            self.exibir_popup("info", "Ficha Salva", "O atendimento foi registrado com sucesso!")
        except Exception as e:
            self.exibir_popup("erro", "Erro", f"Falha no banco de dados:\n{str(e)}")