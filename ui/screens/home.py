import sqlite3
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QTableWidget, QHeaderView, QPushButton, 
                               QInputDialog, QMessageBox, QTableWidgetItem)
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
        
        btn_novo_paciente = QPushButton("➕ Novo Paciente")
        btn_novo_paciente.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; padding: 10px 18px; font-weight: bold; border-radius: 6px; font-size: 13px; border: none; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        if self.on_novo_paciente_click:
            btn_novo_paciente.clicked.connect(self.on_novo_paciente_click)
        header_layout.addWidget(btn_novo_paciente, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addLayout(header_layout)
        
        # --- 2. CARDS DE INDICADORES (Métricas REAIS) ---
        metricas_layout = QHBoxLayout()
        metricas_layout.setSpacing(20)
        
        self.card_pacientes = CardMetrica("Total de Pacientes", "0", "👤", "#e0f2fe", "#0369a1")
        self.card_consultas = CardMetrica("Consultas Hoje", "0", "📅", "#fef3c7", "#b45309")
        
        metricas_layout.addWidget(self.card_pacientes)
        metricas_layout.addWidget(self.card_consultas)
        main_layout.addLayout(metricas_layout)
        
        # --- 3. SEÇÃO INFERIOR: SELETOR DE PASTAS ---
        pastas_section = QVBoxLayout()
        pastas_section.setSpacing(12)
        
        pastas_header = QHBoxLayout()
        lbl_pastas_titulo = QLabel("📁 Pastas Clínicas / Especialidades")
        lbl_pastas_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        
        btn_add_pasta = QPushButton("✨ Criar Nova Pasta")
        btn_add_pasta.setStyleSheet("""
            QPushButton { background-color: #f1f5f9; color: #0f172a; padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: 500; font-size: 12px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        btn_add_pasta.clicked.connect(self.acao_criar_nova_pasta)
        
        pastas_header.addWidget(lbl_pastas_titulo)
        pastas_header.addWidget(btn_add_pasta, alignment=Qt.AlignmentFlag.AlignRight)
        pastas_section.addLayout(pastas_header)
        
        self.pastas_grid_layout = QHBoxLayout()
        self.pastas_grid_layout.setSpacing(15)
        self.pastas_grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        pastas_section.addLayout(self.pastas_grid_layout)
        main_layout.addLayout(pastas_section)
        
        # --- 4. SEÇÃO DO PAINEL DE TAREFAS ---
        split_tables_layout = QHBoxLayout()
        split_tables_layout.setSpacing(25)
        
        # Coluna Agenda do Dia
        agenda_vbox = QVBoxLayout()
        lbl_agenda_tit = QLabel("📋 Próximas Consultas (Hoje)")
        lbl_agenda_tit.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155;")
        agenda_vbox.addWidget(lbl_agenda_tit)
        
        self.table_agenda_resumo = QTableWidget()
        self.table_agenda_resumo.setColumnCount(3)
        self.table_agenda_resumo.setHorizontalHeaderLabels(["Horário", "Paciente", "Status"])
        self.table_agenda_resumo.verticalHeader().setVisible(False)
        self.table_agenda_resumo.setShowGrid(False)
        self.table_agenda_resumo.setFixedHeight(180)
        self.table_agenda_resumo.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; color: #334155; }
            QTableWidget::item { border-bottom: 1px solid #f1f5f9; padding: 6px; }
            QHeaderView::section { background-color: #f8fafc; font-weight: bold; color: #64748b; border: none; padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-align: left; }
        """)
        h_agenda = self.table_agenda_resumo.horizontalHeader()
        h_agenda.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h_agenda.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h_agenda.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        agenda_vbox.addWidget(self.table_agenda_resumo)
        split_tables_layout.addLayout(agenda_vbox, stretch=1)
        
        # Coluna Pacientes Recentes
        recentes_vbox = QVBoxLayout()
        lbl_rec_tit = QLabel("⏱️ Pacientes Adicionados Recentemente")
        lbl_rec_tit.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155;")
        recentes_vbox.addWidget(lbl_rec_tit)
        
        self.table_recentes = QTableWidget()
        self.table_recentes.setColumnCount(2)
        self.table_recentes.setHorizontalHeaderLabels(["Nome do Paciente", "Pasta / Grupo"])
        self.table_recentes.verticalHeader().setVisible(False)
        self.table_recentes.setShowGrid(False)
        self.table_recentes.setFixedHeight(180)
        self.table_recentes.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; color: #334155; }
            QTableWidget::item { border-bottom: 1px solid #f1f5f9; padding: 6px; }
            QHeaderView::section { background-color: #f8fafc; font-weight: bold; color: #64748b; border: none; padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-align: left; }
        """)
        h_rec = self.table_recentes.horizontalHeader()
        h_rec.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_rec.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        recentes_vbox.addWidget(self.table_recentes)
        split_tables_layout.addLayout(recentes_vbox, stretch=1)
        
        main_layout.addLayout(split_tables_layout)
        main_layout.addStretch()

    def renderizar_lista_pastas(self):
        while self.pastas_grid_layout.count():
            child = self.pastas_grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        lista_pastas = getattr(self.window_principal, 'pastas_sistema', ["Geral"])
        
        for nome_pasta in lista_pastas:
            qtd_pacientes = self.contar_pacientes_na_pasta_sqlite(nome_pasta)
            
            card = CardPasta(
                nome=nome_pasta, 
                quantidade=qtd_pacientes,
                on_clique=self.on_pasta_click,
                on_editar=self.acao_editar_pasta,
                on_excluir=self.acao_excluir_pasta
            )
            self.pastas_grid_layout.addWidget(card)
            
        self.carregar_dados_iniciais()

    def contar_pacientes_na_pasta_sqlite(self, nome_pasta):
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pacientes WHERE UPPER(pasta) = ?", (nome_pasta.strip().upper(),))
            total = cursor.fetchone()[0]
            conn.close()
            return total
        except:
            return 0

    def carregar_dados_iniciais(self):
        try:
            self.table_recentes.setRowCount(0)
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT nome, pasta FROM pacientes ORDER BY id DESC LIMIT 4")
            rows_pacientes = cursor.fetchall()
            
            for row_idx, data in enumerate(rows_pacientes):
                self.table_recentes.insertRow(row_idx)
                self.table_recentes.setItem(row_idx, 0, QTableWidgetItem(str(data[0]).upper()))
                self.table_recentes.setItem(row_idx, 1, QTableWidgetItem(str(data[1]).upper()))
                
            self.table_agenda_resumo.setRowCount(0)
            hoje_iso = QDate.currentDate().toString("yyyy-MM-dd")
            
            cursor.execute("SELECT horario, paciente, status FROM agenda WHERE data = ? ORDER BY horario ASC", (hoje_iso,))
            rows_agenda = cursor.fetchall()
            conn.close()
            
            for r_idx, (hora, pac, status) in enumerate(rows_agenda):
                self.table_agenda_resumo.insertRow(r_idx)
                self.table_agenda_resumo.setItem(r_idx, 0, QTableWidgetItem(str(hora)))
                self.table_agenda_resumo.setItem(r_idx, 1, QTableWidgetItem(str(pac).upper()))
                self.table_agenda_resumo.setItem(r_idx, 2, QTableWidgetItem(str(status)))
        except Exception as e:
            print(f"Erro ao inicializar tabelas reais da home: {e}")

    def acao_criar_nova_pasta(self):
        # 🎨 CORREÇÃO DO POP-UP: Estilo completo e limpo para impedir textos invisíveis e desalinhamentos
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Nova Pasta")
        dialog.setLabelText("Digite o nome da especialidade ou grupo:")
        dialog.setStyleSheet("""
            QInputDialog { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: 500; }
            QLineEdit { color: #0f172a; background-color: #ffffff; border: 1px solid #cbd5e1; padding: 6px; border-radius: 6px; font-size: 14px; min-width: 250px; }
            QPushButton { color: #334155; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 14px; border-radius: 6px; font-weight: 500; font-size: 13px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        ok = dialog.exec()
        nome_nova = dialog.textValue()
        
        if ok and nome_nova.strip():
            nome_limpo = nome_nova.strip()
            lista = list(getattr(self.window_principal, 'pastas_sistema', ["Geral"]))
            
            if nome_limpo in lista:
                QMessageBox.warning(self, "Aviso", "Esta pasta já existe no sistema.")
                return
                
            lista.append(nome_limpo)
            self.window_principal.sincronizar_pastas_sistema(lista)
            self.renderizar_lista_pastas()

    def acao_editar_pasta(self, nome_antigo):
        if nome_antigo.lower() == "geral":
            QMessageBox.warning(self, "Aviso", "A pasta padrão 'Geral' não pode ser renomeada.")
            return

        # 🎨 CORREÇÃO CRÍTICA DO POP-UP: Força o estilo unificado para o campo e botões do sistema
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Editar Pasta")
        dialog.setLabelText(f"Alterar o nome da pasta '{nome_antigo}' para:")
        dialog.setTextValue(nome_antigo)
        dialog.setStyleSheet("""
            QInputDialog { background-color: #ffffff; }
            QLabel { color: #0f172a; font-size: 13px; font-weight: 500; }
            QLineEdit { color: #0f172a; background-color: #ffffff; border: 1px solid #cbd5e1; padding: 6px; border-radius: 6px; font-size: 14px; min-width: 250px; }
            QPushButton { color: #334155; background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 14px; border-radius: 6px; font-weight: 500; font-size: 13px; }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        
        ok = dialog.exec()
        nome_novo = dialog.textValue()
        
        if ok and nome_novo.strip():
            nome_limpo = nome_novo.strip()
            lista = list(getattr(self.window_principal, 'pastas_sistema', ["Geral"]))
            
            if nome_limpo in lista and nome_limpo != nome_antigo:
                QMessageBox.warning(self, "Aviso", "Já existe outra pasta com esse nome.")
                return
                
            if nome_antigo in lista:
                idx = lista.index(nome_antigo)
                lista[idx] = nome_limpo
            
            self.atualizar_pasta_dos_pacientes_sqlite(nome_antigo, nome_limpo)
            self.window_principal.sincronizar_pastas_sistema(lista)
            self.renderizar_lista_pastas()

    def acao_excluir_pasta(self, nome_pasta):
        if nome_pasta.lower() == "geral":
            QMessageBox.warning(self, "Aviso", "A pasta padrão 'Geral' não pode ser apagada.")
            return

        resposta = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Tem certeza que deseja apagar a pasta '{nome_pasta}'?\nOs pacientes vinculados voltarão para o grupo 'Geral'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if resposta == QMessageBox.StandardButton.Yes:
            lista = list(getattr(self.window_principal, 'pastas_sistema', ["Geral"]))
            if nome_pasta in lista:
                lista.remove(nome_pasta)
                
                self.atualizar_pasta_dos_pacientes_sqlite(nome_pasta, "Geral")
                self.window_principal.sincronizar_pastas_sistema(lista)
                self.renderizar_lista_pastas()

    def atualizar_pasta_dos_pacientes_sqlite(self, de_pasta, para_pasta):
        try:
            conn = sqlite3.connect("consultorio.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE pacientes SET pasta = ? WHERE pasta = ?", (para_pasta, de_pasta))
            conn.commit()
            conn.close()
            if hasattr(self.window_principal, 'screen_pacientes'):
                self.window_principal.screen_pacientes.carregar_dados_sqlite()
        except Exception as e:
            print(f"Erro ao atualizar dados: {e}")

class CardMetrica(QFrame):
    def __init__(self, titulo, valor, icone, bg_cor, texto_cor):
        super().__init__()
        self.setFixedSize(220, 90)
        self.setStyleSheet("QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500; border: none; background: transparent;")
        self.lbl_valor = QLabel(valor)
        self.lbl_valor.setStyleSheet("color: #0f172a; font-size: 24px; font-weight: bold; border: none; background: transparent;")
        vbox.addWidget(self.lbl_titulo)
        vbox.addWidget(self.lbl_valor)
        layout.addLayout(vbox)
        
        self.lbl_icone = QLabel(icone)
        self.lbl_icone.setFixedSize(40, 40)
        self.lbl_icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icone.setStyleSheet(f"QLabel {{ background-color: {bg_cor}; color: {texto_cor}; font-size: 18px; border-radius: 6px; border: none; }}")
        layout.addWidget(self.lbl_icone)
        
    def set_valor(self, novo_valor):
        self.lbl_valor.setText(novo_valor)

class CardPasta(QFrame):
    def __init__(self, nome, quantidade, on_clique=None, on_editar=None, on_excluir=None):
        super().__init__()
        self.nome_pasta = nome
        self.on_clique_callback = on_clique
        
        self.setFixedSize(175, 125)
        self.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; }
            QFrame:hover { border: 1px solid #0284c7; background-color: #fafafa; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        top_btn_layout = QHBoxLayout()
        top_btn_layout.setSpacing(2)
        
        lbl_folder_icon = QLabel("📁")
        lbl_folder_icon.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        top_btn_layout.addWidget(lbl_folder_icon)
        top_btn_layout.addStretch()
        
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(18, 18)
        btn_edit.setStyleSheet("font-size: 10px; background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 3px; color: #0f172a;")
        btn_edit.clicked.connect(lambda: on_editar(self.nome_pasta) if on_editar else None)
        
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(18, 18)
        btn_del.setStyleSheet("font-size: 10px; background-color: #fee2e2; border: 1px solid #fca5a5; border-radius: 3px; color: #0f172a;")
        btn_del.clicked.connect(lambda: on_excluir(self.nome_pasta) if on_excluir else None)
        
        top_btn_layout.addWidget(btn_edit)
        top_btn_layout.addWidget(btn_del)
        layout.addLayout(top_btn_layout)
        
        self.lbl_nome = QLabel(nome)
        self.lbl_nome.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b; margin-top: 5px; border: none; background: transparent;")
        layout.addWidget(self.lbl_nome)
        
        self.lbl_qtd = QLabel(f"{quantidade} pacientes")
        self.lbl_qtd.setStyleSheet("font-size: 12px; color: #64748b; border: none; background: transparent;")
        layout.addWidget(self.lbl_qtd)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_clique_callback:
            self.on_clique_callback(self.nome_pasta)
        super().mousePressEvent(event)