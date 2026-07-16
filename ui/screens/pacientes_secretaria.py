from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHeaderView,
)


class SecretariaPacientesScreen(QWidget):
    """Cadastro operacional seguro: não carrega documentos, endereço ou ficha clínica."""

    def __init__(self, database):
        super().__init__()
        self.db = database
        self.setObjectName("TelaPacientesSecretaria")
        self.setStyleSheet("""
            #TelaPacientesSecretaria { background: #f8fafc; color: #0f172a; }
            #TelaPacientesSecretaria QLabel { color: #334155; background: transparent; border: none; }
            #TelaPacientesSecretaria QLineEdit, #TelaPacientesSecretaria QComboBox, #TelaPacientesSecretaria QDateEdit {
                background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 8px; min-height: 20px;
            }
            #TelaPacientesSecretaria QLineEdit:focus, #TelaPacientesSecretaria QComboBox:focus, #TelaPacientesSecretaria QDateEdit:focus { border: 2px solid #0284c7; }
            #TelaPacientesSecretaria QComboBox QAbstractItemView { background: #ffffff; color: #0f172a; selection-background-color: #e0f2fe; selection-color: #0f172a; }
            #TelaPacientesSecretaria QDateEdit QCalendarWidget QWidget { background: #ffffff; color: #0f172a; }
            #TelaPacientesSecretaria QDateEdit QCalendarWidget QAbstractItemView:enabled { background: #ffffff; color: #0f172a; selection-background-color: #0284c7; selection-color: #ffffff; }
        """)
        self.id_em_edicao = None
        self._estado_salvo = None
        self._montar()
        self.carregar_pacientes_tabela()
        self._marcar_salvo()

    def _montar(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        esquerda = QVBoxLayout()
        layout.addLayout(esquerda, 3)
        titulo = QLabel("Pacientes")
        titulo.setStyleSheet("font-size: 26px; font-weight: 700; color: #0f172a;")
        esquerda.addWidget(titulo)
        aviso = QLabel("Modo Secretaria: acesse somente dados cadastrais e operacionais dos pacientes.")
        aviso.setStyleSheet("color: #0369a1; font-size: 12px; font-weight: 600;")
        esquerda.addWidget(aviso)

        filtros = QHBoxLayout()
        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText("Buscar por nome ou telefone...")
        self.input_busca.textChanged.connect(self.carregar_pacientes_tabela)
        self.combo_filtro_pasta = QComboBox()
        self.combo_filtro_pasta.addItem("Todas as Pastas")
        self.combo_filtro_pasta.currentTextChanged.connect(self.carregar_pacientes_tabela)
        filtros.addWidget(self.input_busca, 1)
        filtros.addWidget(self.combo_filtro_pasta)
        esquerda.addLayout(filtros)

        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome", "Telefone", "Convênio", "Pasta"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.itemSelectionChanged.connect(self.carregar_paciente_selecionado)
        self.tabela.setStyleSheet("QTableWidget { background: white; color: #0f172a; border: 1px solid #dbe5f0; border-radius: 8px; gridline-color: #eef2f7; } QTableWidget::item { padding: 8px; } QHeaderView::section { background: #f8fafc; color: #475569; border: 0; border-bottom: 1px solid #dbe5f0; padding: 9px; font-weight: 700; }")
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for coluna in range(1, 5): cabecalho.setSectionResizeMode(coluna, QHeaderView.ResizeMode.Stretch)
        esquerda.addWidget(self.tabela, 1)

        cartao = QFrame()
        cartao.setObjectName("CadastroSecretaria")
        cartao.setFixedWidth(355)
        cartao.setStyleSheet("#CadastroSecretaria { background: white; border: 1px solid #dbe5f0; border-radius: 10px; } #CadastroSecretaria QLabel { color: #334155; background: transparent; } #CadastroSecretaria QLineEdit, #CadastroSecretaria QComboBox, #CadastroSecretaria QDateEdit { background: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; } #CadastroSecretaria QLineEdit:focus, #CadastroSecretaria QComboBox:focus, #CadastroSecretaria QDateEdit:focus { border: 2px solid #0284c7; }")
        layout.addWidget(cartao, 2)
        direita = QVBoxLayout(cartao)
        direita.setContentsMargins(20, 20, 20, 20)
        self.lbl_form = QLabel("Novo cadastro")
        self.lbl_form.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        direita.addWidget(self.lbl_form)
        descricao = QLabel("Informações necessárias para identificação e agendamento.")
        descricao.setWordWrap(True); descricao.setStyleSheet("color: #64748b; font-size: 12px;")
        direita.addWidget(descricao)
        formulario = QFormLayout()
        formulario.setSpacing(10)
        self.input_nome = QLineEdit(); self.input_nome.setPlaceholderText("Nome completo")
        self.input_telefone = QLineEdit(); self.input_telefone.setPlaceholderText("Ex.: 11999998888")
        self.input_nascimento = QDateEdit(); self.input_nascimento.setCalendarPopup(True); self.input_nascimento.setDisplayFormat("dd/MM/yyyy"); self.input_nascimento.setDate(QDate(1990, 1, 1))
        self.input_convenio = QLineEdit("PARTICULAR")
        self.input_pasta = QComboBox(); self.input_pasta.addItem("Geral")
        self.input_sexo = QComboBox(); self.input_sexo.addItems(["Não informado", "Masculino", "Feminino", "Outro"])
        formulario.addRow(self._rotulo("Nome:*"), self.input_nome)
        formulario.addRow(self._rotulo("Telefone:"), self.input_telefone)
        formulario.addRow(self._rotulo("Nascimento:"), self.input_nascimento)
        formulario.addRow(self._rotulo("Convênio:"), self.input_convenio)
        formulario.addRow(self._rotulo("Pasta:"), self.input_pasta)
        formulario.addRow(self._rotulo("Sexo:"), self.input_sexo)
        direita.addLayout(formulario)
        self.btn_salvar = QPushButton("Salvar cadastro")
        self.btn_salvar.clicked.connect(self.salvar_paciente)
        self.btn_salvar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: 0; border-radius: 6px; padding: 10px; font-weight: 700; } QPushButton:hover { background: #0369a1; }")
        direita.addWidget(self.btn_salvar)
        self.btn_novo = QPushButton("Limpar / novo cadastro")
        self.btn_novo.clicked.connect(self.limpar_formulario)
        self.btn_novo.setStyleSheet("QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px; font-weight: 600; }")
        direita.addWidget(self.btn_novo)
        direita.addStretch()

    @staticmethod
    def _rotulo(texto):
        rotulo = QLabel(texto)
        rotulo.setStyleSheet("color: #334155; background: transparent; border: none; font-size: 12px; font-weight: 600;")
        return rotulo

    def atualizar_combobox_pastas(self, pastas):
        atual = self.input_pasta.currentText() or "Geral"
        filtro = self.combo_filtro_pasta.currentText() or "Todas as Pastas"
        nomes = [str(item) for item in pastas if str(item).strip()]
        if "Geral" not in nomes: nomes.insert(0, "Geral")
        self.input_pasta.blockSignals(True); self.combo_filtro_pasta.blockSignals(True)
        self.input_pasta.clear(); self.input_pasta.addItems(nomes); self.input_pasta.setCurrentText(atual)
        self.combo_filtro_pasta.clear(); self.combo_filtro_pasta.addItem("Todas as Pastas"); self.combo_filtro_pasta.addItems(nomes); self.combo_filtro_pasta.setCurrentText(filtro)
        self.input_pasta.blockSignals(False); self.combo_filtro_pasta.blockSignals(False)

    def carregar_pacientes_tabela(self):
        busca = self.input_busca.text().strip()
        pasta = self.combo_filtro_pasta.currentText()
        dados = self.db.listar_pacientes_secretaria(busca or None)
        if pasta and pasta != "Todas as Pastas": dados = [item for item in dados if str(item.get("pasta") or "Geral") == pasta]
        self.tabela.setRowCount(0)
        for linha, paciente in enumerate(dados):
            self.tabela.insertRow(linha)
            valores = [paciente.get("id"), paciente.get("nome"), paciente.get("telefone"), paciente.get("convenio"), paciente.get("pasta")]
            for coluna, valor in enumerate(valores): self.tabela.setItem(linha, coluna, QTableWidgetItem(str(valor or "")))
        self.tabela.resizeRowsToContents()

    def carregar_paciente_selecionado(self):
        selecionados = self.tabela.selectedItems()
        if not selecionados: return
        paciente_id = int(self.tabela.item(self.tabela.currentRow(), 0).text())
        dados = self.db.obter_paciente_secretaria(paciente_id)
        if not dados: return
        self.id_em_edicao = paciente_id
        self.lbl_form.setText("Editar cadastro")
        self.input_nome.setText(str(dados.get("nome") or "")); self.input_telefone.setText(str(dados.get("telefone") or "")); self.input_convenio.setText(str(dados.get("convenio") or "PARTICULAR"))
        self.input_pasta.setCurrentText(str(dados.get("pasta") or "Geral")); self.input_sexo.setCurrentText(str(dados.get("sexo") or "Não informado"))
        data = QDate.fromString(str(dados.get("nascimento") or ""), "yyyy-MM-dd")
        self.input_nascimento.setDate(data if data.isValid() else QDate(1990, 1, 1))
        self._marcar_salvo()

    def salvar_paciente(self):
        nome = self.input_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Nome obrigatório", "Informe o nome do paciente."); return
        dados = {"nome": nome, "telefone": self.input_telefone.text().strip(), "nascimento": self.input_nascimento.date().toString("yyyy-MM-dd"), "convenio": self.input_convenio.text().strip(), "pasta": self.input_pasta.currentText().strip(), "sexo": self.input_sexo.currentText()}
        resultado = self.db.salvar_paciente_secretaria(self.id_em_edicao, dados)
        if resultado is None:
            QMessageBox.warning(self, "Não foi possível salvar", "O cadastro não foi salvo. Tente novamente."); return
        QMessageBox.information(self, "Cadastro salvo", "Os dados básicos do paciente foram salvos.")
        self.limpar_formulario(); self.carregar_pacientes_tabela()

    def limpar_formulario(self):
        self.id_em_edicao = None; self.lbl_form.setText("Novo cadastro"); self.input_nome.clear(); self.input_telefone.clear(); self.input_nascimento.setDate(QDate(1990, 1, 1)); self.input_convenio.setText("PARTICULAR"); self.input_pasta.setCurrentText("Geral"); self.input_sexo.setCurrentText("Não informado"); self.tabela.clearSelection(); self._marcar_salvo()

    def _estado(self):
        return (self.input_nome.text(), self.input_telefone.text(), self.input_nascimento.date().toString("yyyy-MM-dd"), self.input_convenio.text(), self.input_pasta.currentText(), self.input_sexo.currentText(), self.id_em_edicao)

    def _marcar_salvo(self): self._estado_salvo = self._estado()
    def tem_alteracoes_nao_salvas(self): return self._estado_salvo is not None and self._estado() != self._estado_salvo
    def descartar_alteracoes_nao_salvas(self): self.limpar_formulario()
