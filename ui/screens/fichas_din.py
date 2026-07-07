from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QFrame, QTextEdit)
from PySide6.QtCore import Qt
from utils.docx_parser import extrair_dados_docx

class FichasDinScreen(QWidget):
    def __init__(self, callback_importar_paciente=None):
        super().__init__()
        
        # Guarda a função para enviar o paciente extraído para a tela de cadastros
        self.callback_importar_paciente = callback_importar_paciente
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Cabeçalho
        title = QLabel("📥 Importador Inteligente de Fichas Antigas")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a;")
        layout.addWidget(title)
        
        desc = QLabel("Selecione os arquivos de anamnese (.docx) antigos para migrar os dados para o prontuário digital automaticamente.")
        desc.setStyleSheet("font-size: 14px; color: #64748b; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Área de Upload / Ação
        self.box_upload = QFrame()
        self.box_upload.setStyleSheet("""
            QFrame { background-color: white; border: 2px dashed #cbd5e1; border-radius: 8px; }
        """)
        upload_layout = QVBoxLayout(self.box_upload)
        upload_layout.setContentsMargins(40, 40, 40, 40)
        upload_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel("📄")
        lbl_icon.setStyleSheet("font-size: 48px; border: none; margin-bottom: 10px;")
        upload_layout.addWidget(lbl_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.btn_selecionar = QPushButton("Selecionar Arquivo Word (.docx)")
        self.btn_selecionar.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; font-weight: bold; padding: 12px 24px; border-radius: 6px; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_selecionar.clicked.connect(self.abrir_seletor_arquivos)
        upload_layout.addWidget(self.btn_selecionar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.box_upload)
        
        # Painel de Pré-visualização do resultado da leitura
        self.preview_box = QFrame()
        self.preview_box.setStyleSheet("background-color: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        self.preview_box.setVisible(False) # Escondido até o upload
        
        preview_layout = QVBoxLayout(self.preview_box)
        self.lbl_status_leitura = QLabel("✅ Ficha lida com sucesso! Verifique os dados abaixo:")
        self.lbl_status_leitura.setStyleSheet("font-weight: bold; color: #10b981; font-size: 14px; border: none;")
        preview_layout.addWidget(self.lbl_status_leitura)
        
        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setStyleSheet("border: 1px solid #cbd5e1; background-color: #f8fafc; font-size: 13px; color: #334155;")
        preview_layout.addWidget(self.txt_preview)
        
        self.btn_confirmar_migracao = QPushButton("⚡ Enviar Dados para Formulário de Cadastro")
        self.btn_confirmar_migracao.setStyleSheet("""
            QPushButton { background-color: #10b981; color: white; font-weight: bold; padding: 12px; border-radius: 6px; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_confirmar_migracao.clicked.connect(self.enviar_para_cadastro)
        preview_layout.addWidget(self.btn_confirmar_migracao)
        
        layout.addWidget(self.preview_box)
        layout.addStretch()
        
        # Guarda os dados temporários extraídos
        self.dados_carregados = None

    def abrir_seletor_arquivos(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecione a Ficha Word", "", "Arquivos Word (*.docx)")
        if caminho:
            dados = extrair_dados_docx(caminho)
            if dados:
                self.dados_carregados = dados
                texto_preview = (
                    f"Paciente Identificado: {dados['nome']}\n"
                    f"Telefone extraído: {dados['telefone']}\n"
                    f"Data de Nascimento: {dados['nascimento']}\n"
                    f"Convênio: {dados['convenio']}\n"
                    f"Endereço: {dados['endereco']}\n"
                    f"Queixa Principal (QP): {dados['qp']}"
                )
                self.txt_preview.setText(texto_preview)
                self.preview_box.setVisible(True)

    def enviar_para_cadastro(self):
        if self.dados_carregados and self.callback_importar_paciente:
            self.callback_importar_paciente(self.dados_carregados)
            self.preview_box.setVisible(False)
            self.dados_carregados = None