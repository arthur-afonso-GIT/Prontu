import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget

from ui.design_system import definir_variante


def campo_senha_com_visibilidade(campo: QLineEdit) -> QWidget:
    """Cria um campo de senha com um botão visível para conferência."""
    campo.setEchoMode(QLineEdit.EchoMode.Password)
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(campo, 1)
    botao = QPushButton("Mostrar")
    botao.setFixedWidth(76)
    botao.setToolTip("Mostrar senha")
    definir_variante(botao, "secondary")
    layout.addWidget(botao)

    def alternar() -> None:
        visivel = campo.echoMode() == QLineEdit.EchoMode.Password
        campo.setEchoMode(
            QLineEdit.EchoMode.Normal if visivel else QLineEdit.EchoMode.Password
        )
        botao.setText("Ocultar" if visivel else "Mostrar")
        botao.setToolTip("Ocultar senha" if visivel else "Mostrar senha")

    botao.clicked.connect(alternar)
    return container


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
        form.addRow("E-mail:", self.email)
        form.addRow("Senha:", campo_senha_com_visibilidade(self.senha))
        form.addRow("Confirmar senha:", campo_senha_com_visibilidade(self.confirmacao))
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
        self.setObjectName("LoginDialog")
        self.setMinimumSize(500, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(14)

        marca = QHBoxLayout()
        logo = QLabel()
        logo.setFixedSize(42, 42)
        caminho_logo = os.path.join(os.path.dirname(__file__), "assets", "prontu_logo.png")
        if os.path.exists(caminho_logo):
            logo.setPixmap(QPixmap(caminho_logo).scaled(
                42, 42, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        marca.addWidget(logo)
        titulo = QLabel("Prontu")
        titulo.setObjectName("LoginBrand")
        marca.addWidget(titulo)
        marca.addStretch()
        layout.addLayout(marca)

        titulo_acesso = QLabel("Acesse sua clínica")
        titulo_acesso.setStyleSheet("font-size: 20px; font-weight: 750; color: #17233a;")
        layout.addWidget(titulo_acesso)
        subtitulo = QLabel("Entre com seu e-mail, aceite um convite ou ative a clínica neste dispositivo.")
        subtitulo.setObjectName("LoginSubtitle")
        subtitulo.setWordWrap(True)
        layout.addWidget(subtitulo)

        abas = QTabWidget()
        abas.setObjectName("LoginCard")
        abas.addTab(self._login(), "Entrar")
        abas.addTab(self._convite(), "Usar convite")
        abas.addTab(self._ativacao(), "Ativar clínica")
        layout.addWidget(abas)

    def _botao(self, texto, acao):
        botao = QPushButton(texto)
        botao.clicked.connect(acao)
        definir_variante(botao, "primary")
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
        pagina = self._pagina(
            [("E-mail:", self.email_login), ("Senha:", campo_senha_com_visibilidade(self.senha_login))],
            "",
            "Entrar",
            self.entrar,
        )
        self.checkbox_lembrar = QCheckBox("Lembrar de mim neste dispositivo")
        self.checkbox_lembrar.setChecked(True)
        self.checkbox_lembrar.setToolTip("Deixe marcado apenas em um computador pessoal e protegido.")
        pagina.layout().insertWidget(1, self.checkbox_lembrar)
        recuperar = QPushButton("Esqueci minha senha")
        definir_variante(recuperar, "ghost")
        recuperar.clicked.connect(lambda: RecuperarSenhaDialog(self.db, self).exec())
        pagina.layout().insertWidget(2, recuperar)
        return pagina

    def _convite(self):
        self.codigo, self.email, self.senha, self.confirmacao = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.codigo.setPlaceholderText("PRONTU-XXXXXXXX")
        self.email.setPlaceholderText("O mesmo e-mail do convite")
        return self._pagina(
            [
                ("Código:", self.codigo),
                ("E-mail:", self.email),
                ("Senha:", campo_senha_com_visibilidade(self.senha)),
                ("Confirmar senha:", campo_senha_com_visibilidade(self.confirmacao)),
            ],
            "Use o código enviado pelo proprietário para criar sua senha. A senha deve ter pelo menos 8 caracteres.",
            "Criar meu acesso",
            self.aceitar_convite,
        )

    def _ativacao(self):
        self.chave = QLineEdit(); self.chave.setPlaceholderText("PRONTU-...")
        return self._pagina([("Chave de acesso:", self.chave)], "Use somente para ativar o primeiro dispositivo do proprietário.", "Ativar clínica", self.ativar)

    def entrar(self):
        if not self.db.supabase:
            QMessageBox.warning(
                self,
                "Conexao indisponivel",
                "O Prontu nao conseguiu carregar a configuracao de conexao. "
                "Reinstale a versao mais recente ou entre em contato com o suporte.",
            )
            return
        if self.db.entrar_com_email(self.email_login.text().strip(), self.senha_login.text(), self.checkbox_lembrar.isChecked()): self.accept()
        else: QMessageBox.warning(self, "Não foi possível entrar", "Confira o e-mail e a senha. No primeiro acesso, use a aba 'Usar convite'.")

    def aceitar_convite(self):
        codigo = self.codigo.text().strip().upper()
        email = self.email.text().strip().lower()
        senha = self.senha.text()
        if not codigo or "@" not in email or len(senha) < 8 or senha != self.confirmacao.text():
            QMessageBox.warning(self, "Dados inválidos", "Confira o código, o e-mail e as senhas. A senha deve ter ao menos 8 caracteres."); return
        if self.db.aceitar_convite_equipe(codigo, email, senha):
            QMessageBox.information(self, "Acesso criado", "Seu acesso foi criado com sucesso."); self.accept()
        else:
            QMessageBox.warning(
                self,
                "Convite não aceito",
                self.db.obter_ultimo_erro_funcao(),
            )

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
