from PySide6.QtWidgets import QCheckBox, QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget


class CriarAcessoProprietarioDialog(QDialog):
    """Cria o e-mail e a senha pessoal do proprietário após ativar a chave."""

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.db = database
        self.setWindowTitle("Criar login do proprietário")
        self.setMinimumWidth(390)
        self.setStyleSheet("QDialog { background: #f8fafc; } QLabel { color: #0f172a; } QLineEdit { color: #0f172a; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px; }")
        layout = QVBoxLayout(self)
        titulo = QLabel("Crie seu login pessoal")
        titulo.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(titulo)
        explicacao = QLabel("A chave ativou este dispositivo. Agora defina o e-mail e a senha que você usará nos próximos acessos.")
        explicacao.setWordWrap(True)
        explicacao.setStyleSheet("color: #64748b;")
        layout.addWidget(explicacao)
        form = QFormLayout()
        self.email, self.senha, self.confirmacao = QLineEdit(), QLineEdit(), QLineEdit()
        self.email.setPlaceholderText("seuemail@clinica.com")
        for campo in (self.senha, self.confirmacao):
            campo.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("E-mail:", self.email)
        form.addRow("Senha:", self.senha)
        form.addRow("Confirmar senha:", self.confirmacao)
        layout.addLayout(form)
        self.botao = QPushButton("Criar meu login")
        self.botao.setStyleSheet("QPushButton { background: #0284c7; color: white; border: 0; border-radius: 6px; padding: 10px; font-weight: 700; }")
        self.botao.clicked.connect(self.criar)
        layout.addWidget(self.botao)

    def criar(self):
        email, senha = self.email.text().strip(), self.senha.text()
        if "@" not in email or len(senha) < 8 or senha != self.confirmacao.text():
            QMessageBox.warning(self, "Dados inválidos", "Informe um e-mail válido e uma senha igual nos dois campos, com pelo menos 8 caracteres.")
            return
        self.botao.setEnabled(False)
        if self.db.criar_login_proprietario(email, senha):
            self.accept()
        else:
            self.botao.setEnabled(True)
            QMessageBox.warning(self, "Login não criado", "Esse e-mail pode já estar em uso. Tente outro e-mail.")


class RecuperarSenhaDialog(QDialog):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.db = database
        self.setWindowTitle("Recuperar senha")
        self.setMinimumWidth(370)
        self.setStyleSheet("QDialog { background: #f8fafc; } QLabel { color: #0f172a; } QLineEdit { color: #0f172a; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px; }")
        layout = QVBoxLayout(self)
        titulo = QLabel("Recuperar acesso")
        titulo.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(titulo)
        texto = QLabel("Informe seu e-mail. Se houver uma conta vinculada, enviaremos um link seguro para criar uma nova senha.")
        texto.setWordWrap(True)
        texto.setStyleSheet("color: #64748b;")
        layout.addWidget(texto)
        self.email = QLineEdit()
        self.email.setPlaceholderText("seuemail@clinica.com")
        layout.addWidget(self.email)
        botao = QPushButton("Enviar link de recuperação")
        botao.setStyleSheet("QPushButton { background: #0284c7; color: white; border: 0; border-radius: 6px; padding: 10px; font-weight: 700; }")
        botao.clicked.connect(self.enviar)
        layout.addWidget(botao)

    def enviar(self):
        email = self.email.text().strip()
        if "@" not in email:
            QMessageBox.warning(self, "E-mail inválido", "Informe um e-mail válido.")
            return
        if self.db.solicitar_redefinicao_senha(email):
            QMessageBox.information(self, "Confira seu e-mail", "Se existe uma conta com esse e-mail, o link de recuperação foi enviado. Ele pode levar alguns minutos para chegar.")
            self.accept()
        else:
            QMessageBox.warning(self, "Não foi possível enviar", "Verifique sua conexão e tente novamente.")


class LoginDialog(QDialog):
    """Entrada do proprietário e dos integrantes convidados."""

    def __init__(self, database):
        super().__init__()
        self.db = database
        self.setWindowTitle("Acessar o Prontu")
        self.setMinimumWidth(430)
        self.setStyleSheet("""
            QDialog { background: #f8fafc; }
            QWidget { color: #0f172a; background: #f8fafc; }
            QTabWidget::pane { background: #ffffff; border: 1px solid #dbe5f0; border-radius: 7px; }
            QTabBar::tab { background: #e2e8f0; color: #334155; padding: 8px 12px; border: 0; border-top-left-radius: 5px; border-top-right-radius: 5px; }
            QTabBar::tab:selected { background: #ffffff; color: #0369a1; font-weight: 700; }
            QLabel { color: #0f172a; background: transparent; }
            QLineEdit { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 9px; }
            QLineEdit:focus { border: 2px solid #0284c7; }
        """)
        layout = QVBoxLayout(self)
        titulo = QLabel("Prontu")
        titulo.setStyleSheet("font-size: 25px; font-weight: 700;")
        layout.addWidget(titulo)
        layout.addWidget(QLabel("Acesse sua clínica com seus próprios dados."))
        abas = QTabWidget()
        abas.addTab(self._login(), "Entrar")
        abas.addTab(self._convite(), "Usar convite")
        abas.addTab(self._ativacao(), "Ativar clínica")
        layout.addWidget(abas)

    def _botao(self, texto, acao):
        botao = QPushButton(texto)
        botao.clicked.connect(acao)
        botao.setStyleSheet("QPushButton { background: #0284c7; color: white; border: 0; border-radius: 6px; padding: 10px; font-weight: 700; } QPushButton:hover { background: #0369a1; }")
        return botao

    def _pagina(self, campos, texto, botao, acao):
        pagina = QWidget(); layout = QVBoxLayout(pagina)
        if texto:
            rotulo = QLabel(texto); rotulo.setWordWrap(True); rotulo.setStyleSheet("color: #64748b; font-size: 12px;"); layout.addWidget(rotulo)
        form = QFormLayout()
        for nome, widget in campos: form.addRow(nome, widget)
        layout.addLayout(form); layout.addWidget(self._botao(botao, acao)); layout.addStretch()
        return pagina

    def _login(self):
        self.email_login, self.senha_login = QLineEdit(), QLineEdit()
        self.email_login.setPlaceholderText("seuemail@clinica.com")
        self.senha_login.setEchoMode(QLineEdit.EchoMode.Password)
        pagina = self._pagina([("E-mail:", self.email_login), ("Senha:", self.senha_login)], "", "Entrar", self.entrar)
        self.checkbox_lembrar = QCheckBox("Lembrar de mim neste dispositivo")
        self.checkbox_lembrar.setChecked(True)
        self.checkbox_lembrar.setToolTip("Deixe marcado apenas em um computador pessoal e protegido.")
        pagina.layout().insertWidget(1, self.checkbox_lembrar)
        recuperar = QPushButton("Esqueci minha senha")
        recuperar.setStyleSheet("QPushButton { background: transparent; color: #0369a1; border: 0; padding: 8px; text-align: left; } QPushButton:hover { text-decoration: underline; }")
        recuperar.clicked.connect(lambda: RecuperarSenhaDialog(self.db, self).exec())
        pagina.layout().insertWidget(2, recuperar)
        return pagina

    def _convite(self):
        self.codigo, self.email, self.senha, self.confirmacao = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.codigo.setPlaceholderText("PRONTU-XXXXXXXX")
        self.email.setPlaceholderText("O mesmo e-mail do convite")
        for campo in (self.senha, self.confirmacao): campo.setEchoMode(QLineEdit.EchoMode.Password)
        return self._pagina([("Código:", self.codigo), ("E-mail:", self.email), ("Senha:", self.senha), ("Confirmar senha:", self.confirmacao)], "Use o código enviado pelo proprietário para criar sua senha. A senha deve ter pelo menos 8 caracteres.", "Criar meu acesso", self.aceitar_convite)

    def _ativacao(self):
        self.chave = QLineEdit(); self.chave.setPlaceholderText("PRONTU-...")
        return self._pagina([("Chave de acesso:", self.chave)], "Use somente para ativar o primeiro dispositivo do proprietário.", "Ativar clínica", self.ativar)

    def entrar(self):
        if self.db.entrar_com_email(self.email_login.text().strip(), self.senha_login.text(), self.checkbox_lembrar.isChecked()): self.accept()
        else: QMessageBox.warning(self, "Não foi possível entrar", "Confira o e-mail e a senha. No primeiro acesso, use a aba 'Usar convite'.")

    def aceitar_convite(self):
        codigo, email, senha = self.codigo.text().strip(), self.email.text().strip(), self.senha.text()
        if not codigo or "@" not in email or len(senha) < 8 or senha != self.confirmacao.text():
            QMessageBox.warning(self, "Dados inválidos", "Confira o código, o e-mail e as senhas. A senha deve ter ao menos 8 caracteres."); return
        if self.db.aceitar_convite_equipe(codigo, email, senha):
            QMessageBox.information(self, "Acesso criado", "Seu acesso foi criado com sucesso."); self.accept()
        else: QMessageBox.warning(self, "Convite não aceito", "Confira o código e o e-mail. O convite pode ter expirado ou sido cancelado.")

    def ativar(self):
        if not self.db.validar_chave_acesso(self.chave.text().strip()):
            QMessageBox.warning(self, "Chave inválida", "A chave não foi encontrada ou não está mais ativa.")
            return
        configuracao = CriarAcessoProprietarioDialog(self.db, self)
        if configuracao.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Login criado", "Pronto. Nos próximos acessos, use a aba 'Entrar' com seu e-mail e senha.")
            self.accept()
        else:
            self.db.desativar_dispositivo()
            QMessageBox.information(self, "Login pendente", "A ativação foi cancelada para proteger sua conta. Ative novamente a chave e crie seu login pessoal.")
        return
        if self.db.validar_chave_acesso(self.chave.text().strip()): self.accept()
        else: QMessageBox.warning(self, "Chave inválida", "A chave não foi encontrada ou não está mais ativa.")
