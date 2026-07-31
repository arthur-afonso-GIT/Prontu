"""Controlador assíncrono da tela de acesso QML."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import Property, QObject, Signal, Slot

from services.auth_service import (
    normalizar_email,
    validar_chave,
    validar_convite,
    validar_email,
    validar_login,
    validar_nova_senha,
)


class LoginController(QObject):
    estadoAlterado = Signal()
    feedback = Signal(str, str)
    autenticado = Signal()
    cancelado = Signal()
    _resultado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-login"
        )
        self._ocupado = False
        self._ativacao_pronta = False
        self._autenticado = False
        self._resultado.connect(self._receber_resultado)

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(bool, notify=estadoAlterado)
    def ativacaoPronta(self) -> bool:
        return self._ativacao_pronta

    @Property(bool, notify=estadoAlterado)
    def estaAutenticado(self) -> bool:
        return self._autenticado

    @Property(bool, constant=True)
    def conexaoDisponivel(self) -> bool:
        return bool(getattr(self._database, "supabase", None))

    def _definir_ocupado(self, valor: bool) -> None:
        if self._ocupado != valor:
            self._ocupado = valor
            self.estadoAlterado.emit()

    def _enviar(self, operacao: str, tarefa) -> None:
        if self._ocupado:
            return
        self._definir_ocupado(True)
        futuro = self._executor.submit(tarefa)

        def concluido(resultado: Future):
            try:
                self._resultado.emit((operacao, resultado.result()), None)
            except Exception as erro:
                self._resultado.emit((operacao, None), erro)

        futuro.add_done_callback(concluido)

    def _concluir_autenticacao(self) -> None:
        self._autenticado = True
        self._ativacao_pronta = False
        self.estadoAlterado.emit()
        self.autenticado.emit()

    @Slot(str, str, bool)
    def entrar(self, email: str, senha: str, lembrar: bool) -> None:
        erro = validar_login(email, senha)
        if erro:
            self.feedback.emit("warning", erro)
            return
        if not self.conexaoDisponivel:
            self.feedback.emit(
                "error",
                "A conexão com o Prontu não foi carregada. "
                "Reinstale a versão mais recente ou fale com o suporte.",
            )
            return
        self._enviar(
            "entrar",
            lambda: self._database.entrar_com_email(
                normalizar_email(email), senha, bool(lembrar)
            ),
        )

    @Slot(str, str, str, str)
    def aceitarConvite(
        self, codigo: str, email: str, senha: str, confirmacao: str
    ) -> None:
        erro = validar_convite(codigo, email, senha, confirmacao)
        if erro:
            self.feedback.emit("warning", erro)
            return
        self._enviar(
            "convite",
            lambda: self._database.aceitar_convite_equipe(
                str(codigo).strip().upper(),
                normalizar_email(email),
                senha,
            ),
        )

    @Slot(str)
    def ativarChave(self, chave: str) -> None:
        erro = validar_chave(chave)
        if erro:
            self.feedback.emit("warning", erro)
            return
        self._enviar(
            "ativar",
            lambda: self._database.validar_chave_acesso(str(chave).strip()),
        )

    @Slot(str, str, str)
    def criarProprietario(
        self, email: str, senha: str, confirmacao: str
    ) -> None:
        if not validar_email(email):
            self.feedback.emit("warning", "Informe um e-mail válido.")
            return
        erro = validar_nova_senha(senha, confirmacao)
        if erro:
            self.feedback.emit("warning", erro)
            return
        self._enviar(
            "proprietario",
            lambda: self._database.criar_login_proprietario(
                normalizar_email(email), senha
            ),
        )

    @Slot(str)
    def solicitarRedefinicao(self, email: str) -> None:
        if not validar_email(email):
            self.feedback.emit("warning", "Informe um e-mail válido.")
            return
        self._enviar(
            "recuperar",
            lambda: self._database.solicitar_redefinicao_senha(
                normalizar_email(email)
            ),
        )

    @Slot()
    def cancelarCriacaoProprietario(self) -> None:
        if self._ativacao_pronta and not self._autenticado:
            self._database.desativar_dispositivo()
            self._ativacao_pronta = False
            self.estadoAlterado.emit()

    @Slot()
    def cancelar(self) -> None:
        self.cancelarCriacaoProprietario()
        self.cancelado.emit()

    @Slot(object, object)
    def _receber_resultado(self, pacote, erro) -> None:
        self._definir_ocupado(False)
        operacao, resultado = pacote or ("", None)
        if erro:
            self.feedback.emit(
                "error",
                "Não foi possível concluir a operação. "
                "Verifique sua conexão e tente novamente.",
            )
            return

        if operacao == "entrar":
            if resultado:
                self._concluir_autenticacao()
            else:
                self.feedback.emit(
                    "error",
                    "E-mail ou senha incorretos. No primeiro acesso, "
                    "use a opção “Usar convite”.",
                )
            return

        if operacao == "convite":
            if resultado:
                self.feedback.emit("success", "Seu acesso foi criado.")
                self._concluir_autenticacao()
            else:
                detalhe = self._database.obter_ultimo_erro_funcao()
                self.feedback.emit("error", detalhe)
            return

        if operacao == "ativar":
            if resultado:
                self._ativacao_pronta = True
                self.estadoAlterado.emit()
                self.feedback.emit(
                    "success",
                    "Chave validada. Agora crie o login do proprietário.",
                )
            else:
                self.feedback.emit(
                    "error",
                    "A chave não foi encontrada ou não está mais ativa.",
                )
            return

        if operacao == "proprietario":
            if resultado:
                self.feedback.emit("success", "Login do proprietário criado.")
                self._concluir_autenticacao()
            else:
                self.feedback.emit(
                    "error",
                    "Esse e-mail pode já estar em uso. Tente outro e-mail.",
                )
            return

        if operacao == "recuperar":
            if resultado:
                self.feedback.emit(
                    "success",
                    "Se existe uma conta com esse e-mail, o link de "
                    "recuperação foi enviado.",
                )
            else:
                self.feedback.emit(
                    "error",
                    "Não foi possível enviar o link agora. Tente novamente.",
                )
