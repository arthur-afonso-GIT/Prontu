from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)


class ConviteCriadoDialog(QDialog):
    """Mostra o código uma única vez, permitindo copiá-lo sem erros."""

    def __init__(self, codigo, email, parent=None):
        super().__init__(parent)
        self.codigo = codigo
        self.setWindowTitle("Convite criado")
        self.setMinimumWidth(440)
        self.setStyleSheet("QDialog { background: #ffffff; } QLabel { color: #0f172a; } QLineEdit { background: #f8fafc; color: #0f172a; border: 1px solid #93c5fd; border-radius: 6px; padding: 9px; font-family: Consolas, monospace; font-weight: 700; }")
        layout = QVBoxLayout(self)
        titulo = QLabel("Envie estes dados para a pessoa")
        titulo.setStyleSheet("font-size: 17px; font-weight: 700;")
        layout.addWidget(titulo)
        texto = QLabel("O código expira em 7 dias e é mostrado somente agora.")
        texto.setStyleSheet("color: #64748b;")
        layout.addWidget(texto)
        layout.addWidget(QLabel("Código de convite:"))
        linha = QHBoxLayout()
        self.campo_codigo = QLineEdit(codigo)
        self.campo_codigo.setReadOnly(True)
        self.campo_codigo.selectAll()
        linha.addWidget(self.campo_codigo, 1)
        copiar = QPushButton("Copiar código")
        copiar.clicked.connect(self.copiar_codigo)
        copiar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: 0; border-radius: 6px; padding: 9px 12px; font-weight: 700; }")
        linha.addWidget(copiar)
        layout.addLayout(linha)
        layout.addWidget(QLabel("E-mail do convite:"))
        campo_email = QLineEdit(email)
        campo_email.setReadOnly(True)
        layout.addWidget(campo_email)
        fechar = QPushButton("Concluído")
        fechar.clicked.connect(self.accept)
        fechar.setStyleSheet("QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px; font-weight: 700; }")
        layout.addWidget(fechar)

    def copiar_codigo(self):
        QApplication.clipboard().setText(self.codigo)
        self.campo_codigo.selectAll()


class EquipeScreen(QWidget):
    """Tela exclusiva do proprietario para administrar vagas do plano Equipe."""

    def __init__(self, database):
        super().__init__()
        self.db = database
        self._montar_tela()

    def _montar_tela(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        titulo = QLabel("Equipe")
        titulo.setStyleSheet("font-size: 26px; font-weight: 700; color: #0f172a;")
        texto = QLabel("Crie acessos individuais para sua equipe e controle quem pode usar os dados da clínica.")
        texto.setStyleSheet("color: #64748b; font-size: 13px;")
        self.lbl_limite = QLabel("Carregando vagas...")
        self.lbl_limite.setStyleSheet("color: #0369a1; font-weight: 600;")
        layout.addWidget(titulo)
        layout.addWidget(texto)
        layout.addWidget(self.lbl_limite)

        conteudo = QHBoxLayout()
        conteudo.setSpacing(18)
        layout.addLayout(conteudo, 1)

        esquerda = QVBoxLayout()
        esquerda.setSpacing(16)
        conteudo.addLayout(esquerda, 3)
        esquerda.addWidget(self._titulo("Integrantes com acesso"))
        self.tabela_membros = self._criar_tabela(["Nome", "E-mail", "Papel", "Ação"])
        esquerda.addWidget(self.tabela_membros, 1)
        esquerda.addWidget(self._titulo("Convites pendentes"))
        self.tabela_convites = self._criar_tabela(["Nome", "E-mail", "Papel", "Expira em", "Ação"])
        esquerda.addWidget(self.tabela_convites, 1)

        cartao = QFrame()
        cartao.setObjectName("CartaoConviteEquipe")
        cartao.setStyleSheet("""
            #CartaoConviteEquipe { background: #ffffff; border: 1px solid #dbe5f0; border-radius: 10px; }
            #CartaoConviteEquipe QLabel { color: #0f172a; background: transparent; border: none; }
            #CartaoConviteEquipe QLineEdit, #CartaoConviteEquipe QComboBox {
                color: #0f172a; background: #ffffff; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 8px;
            }
            #CartaoConviteEquipe QLineEdit:focus, #CartaoConviteEquipe QComboBox:focus { border: 2px solid #0284c7; }
            #CartaoConviteEquipe QComboBox::drop-down { border: none; width: 24px; }
            #CartaoConviteEquipe QComboBox QAbstractItemView { color: #0f172a; background: #ffffff; selection-background-color: #e0f2fe; }
        """)
        cartao.setMaximumWidth(355)
        conteudo.addWidget(cartao, 2)
        form_layout = QVBoxLayout(cartao)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)
        cabecalho = QLabel("Convidar integrante")
        cabecalho.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        aviso = QLabel("A pessoa receberá um código único para criar a própria senha.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #64748b; font-size: 12px;")
        form_layout.addWidget(cabecalho)
        form_layout.addWidget(aviso)
        formulario = QFormLayout()
        formulario.setSpacing(10)
        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Ex.: Maria Silva")
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("nome@clinica.com")
        self.combo_papel = QComboBox()
        self.combo_papel.addItem("Profissional", "profissional")
        self.combo_papel.addItem("Secretária", "secretaria")
        formulario.addRow("Nome:", self.input_nome)
        formulario.addRow("E-mail:", self.input_email)
        formulario.addRow("Papel:", self.combo_papel)
        form_layout.addLayout(formulario)
        self.btn_convidar = QPushButton("Gerar convite")
        self.btn_convidar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convidar.clicked.connect(self.criar_convite)
        self.btn_convidar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: 0; border-radius: 6px; padding: 11px; font-weight: 700; } QPushButton:hover { background: #0369a1; }")
        form_layout.addWidget(self.btn_convidar)
        form_layout.addStretch()

    @staticmethod
    def _titulo(texto):
        label = QLabel(texto)
        label.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        return label

    @staticmethod
    def _criar_tabela(cabecalhos):
        tabela = QTableWidget(0, len(cabecalhos))
        tabela.setHorizontalHeaderLabels(cabecalhos)
        tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tabela.verticalHeader().setVisible(False)
        tabela.horizontalHeader().setStretchLastSection(True)
        tabela.setColumnWidth(len(cabecalhos) - 1, 190)
        tabela.setStyleSheet("""
            QTableWidget { background: #ffffff; color: #0f172a; border: 1px solid #dbe5f0; border-radius: 8px; gridline-color: #e2e8f0; }
            QTableWidget::item { color: #0f172a; background: #ffffff; padding: 7px; }
            QTableWidget::item:selected { color: #0f172a; background: #e0f2fe; }
            QHeaderView::section { background: #f8fafc; color: #475569; font-weight: 700; padding: 8px; border: 0; border-bottom: 1px solid #dbe5f0; }
            QTableWidget QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 5px; padding: 5px 7px; font-weight: 600; }
            QTableWidget QPushButton:hover { background: #e0f2fe; color: #0369a1; }
        """)
        return tabela

    @staticmethod
    def _papel_texto(papel):
        return {"proprietario": "Proprietário", "profissional": "Profissional", "secretaria": "Secretária"}.get(str(papel), str(papel))

    @staticmethod
    def _data_texto(valor):
        try:
            return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return "Não informado"

    @staticmethod
    def _botao_acao(texto, tipo):
        """Cria um botao de acao com dimensoes estaveis dentro da tabela."""
        botao = QPushButton(texto)
        botao.setCursor(Qt.CursorShape.PointingHandCursor)
        botao.setFixedHeight(30)
        botao.setMinimumWidth(132)
        if tipo == "perigo":
            botao.setStyleSheet(
                "QPushButton { color: #b91c1c; background: #fef2f2; border: 1px solid #fca5a5; "
                "border-radius: 6px; padding: 0 10px; font-weight: 700; font-size: 12px; } "
                "QPushButton:hover { background: #fee2e2; }"
            )
        else:
            botao.setStyleSheet(
                "QPushButton { color: #0369a1; background: #eff6ff; border: 1px solid #93c5fd; "
                "border-radius: 6px; padding: 0 10px; font-weight: 700; font-size: 12px; } "
                "QPushButton:hover { background: #dbeafe; }"
            )
        return botao

    @staticmethod
    def _celula_acoes(*botoes):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for botao in botoes:
            layout.addWidget(botao)
        return container

    def carregar_dados(self):
        dados = self.db.listar_equipe()
        if not dados:
            self.lbl_limite.setText("Não foi possível carregar a equipe. Tente novamente.")
            self.lbl_limite.setStyleSheet("color: #b91c1c; font-weight: 600;")
            return
        membros = [
            membro for membro in dados.get("membros", [])
            if not str(membro.get("email") or "").endswith("@prontu.device")
        ]
        convites = dados.get("convites", [])
        limite = int(dados.get("max_usuarios") or 0)
        usados = len(membros) + len(convites)
        self.lbl_limite.setText(f"Vagas usadas: {usados} de {limite} (convites pendentes também reservam uma vaga)")
        self.lbl_limite.setStyleSheet("color: #0369a1; font-weight: 600;")
        self._preencher_membros(membros)
        self._preencher_convites(convites)

    def _preencher_membros(self, membros):
        self.tabela_membros.setRowCount(len(membros))
        for linha, membro in enumerate(membros):
            for coluna, chave in enumerate(("nome", "email")):
                self.tabela_membros.setItem(linha, coluna, QTableWidgetItem(str(membro.get(chave) or "")))
            self.tabela_membros.setItem(linha, 2, QTableWidgetItem(self._papel_texto(membro.get("papel"))))
            if membro.get("papel") == "proprietario":
                self.tabela_membros.setItem(linha, 3, QTableWidgetItem("Proprietário"))
            else:
                alterar = self._botao_acao("Alterar papel", "primario")
                alterar.clicked.connect(lambda _, mid=membro.get("id"), atual=membro.get("papel"): self.alterar_papel(mid, atual))
                revogar = self._botao_acao("Revogar acesso", "perigo")
                revogar.clicked.connect(lambda _, mid=membro.get("id"): self.revogar("membro", mid))
                self.tabela_membros.setCellWidget(linha, 3, self._celula_acoes(alterar, revogar))
            self.tabela_membros.setRowHeight(linha, 42)
        self.tabela_membros.resizeColumnsToContents()
        self.tabela_membros.setColumnWidth(3, 310)

    def _preencher_convites(self, convites):
        self.tabela_convites.setRowCount(len(convites))
        for linha, convite in enumerate(convites):
            self.tabela_convites.setItem(linha, 0, QTableWidgetItem(str(convite.get("nome") or "")))
            self.tabela_convites.setItem(linha, 1, QTableWidgetItem(str(convite.get("email") or "")))
            self.tabela_convites.setItem(linha, 2, QTableWidgetItem(self._papel_texto(convite.get("papel"))))
            self.tabela_convites.setItem(linha, 3, QTableWidgetItem(self._data_texto(convite.get("expira_em"))))
            renovar = self._botao_acao("Gerar novo código", "primario")
            renovar.setMinimumWidth(145)
            renovar.clicked.connect(lambda _, cid=convite.get("id"), email=convite.get("email"): self.renovar_convite(cid, email))
            cancelar = self._botao_acao("Cancelar convite", "perigo")
            cancelar.clicked.connect(lambda _, cid=convite.get("id"): self.revogar("convite", cid))
            self.tabela_convites.setCellWidget(linha, 4, self._celula_acoes(renovar, cancelar))
            self.tabela_convites.setRowHeight(linha, 42)
        self.tabela_convites.resizeColumnsToContents()
        self.tabela_convites.setColumnWidth(4, 330)

    def criar_convite(self):
        nome, email = self.input_nome.text().strip(), self.input_email.text().strip()
        if not nome or "@" not in email:
            QMessageBox.warning(self, "Dados incompletos", "Informe o nome e um e-mail válido.")
            return
        resposta = self.db.criar_convite_equipe(nome, email, self.combo_papel.currentData())
        if not resposta or not resposta.get("codigo"):
            QMessageBox.warning(self, "Convite não criado", "Não foi possível criar o convite. Confira as vagas e tente novamente.")
            return
        self.input_nome.clear()
        self.input_email.clear()
        ConviteCriadoDialog(resposta["codigo"], email, self).exec()
        self.carregar_dados()

    def alterar_papel(self, membro_id, papel_atual):
        opcoes = ["Profissional", "Secretária"]
        atual = "Profissional" if papel_atual == "profissional" else "Secretária"
        escolhido, confirmado = QInputDialog.getItem(self, "Alterar papel", "Novo papel:", opcoes, opcoes.index(atual), False)
        if not confirmado or escolhido == atual:
            return
        papel = "profissional" if escolhido == "Profissional" else "secretaria"
        if self.db.alterar_papel_equipe(str(membro_id), papel):
            self.carregar_dados()
            QMessageBox.information(self, "Papel atualizado", "O novo nível de acesso será aplicado no próximo acesso da pessoa.")
        else:
            QMessageBox.warning(self, "Papel não alterado", "Não foi possível alterar o papel agora.")

    def renovar_convite(self, convite_id, email):
        if not convite_id:
            return
        resposta = self.db.renovar_convite_equipe(str(convite_id))
        if not resposta or not resposta.get("codigo"):
            QMessageBox.warning(self, "Convite não renovado", "Não foi possível gerar um novo código.")
            return
        ConviteCriadoDialog(resposta["codigo"], str(email or ""), self).exec()
        self.carregar_dados()

    def revogar(self, tipo, identificador):
        if not identificador:
            return
        mensagem = "Cancelar este convite?" if tipo == "convite" else "Revogar o acesso desta pessoa?"
        if QMessageBox.question(self, "Confirmar ação", mensagem) != QMessageBox.StandardButton.Yes:
            return
        if self.db.revogar_acesso_equipe(tipo, str(identificador)):
            self.carregar_dados()
        else:
            QMessageBox.warning(self, "Ação não concluída", "Não foi possível concluir a ação. Tente novamente.")
