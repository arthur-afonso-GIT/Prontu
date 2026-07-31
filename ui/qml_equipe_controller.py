"""Controlador assíncrono da gestão de equipe em QML."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication

from services.equipe_service import preparar_equipe, validar_convite


class TeamMembersModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    NameRole = IdRole + 1
    EmailRole = NameRole + 1
    RoleRole = EmailRole + 1
    RoleLabelRole = RoleRole + 1
    OwnerRole = RoleLabelRole + 1

    _ROLES = {
        IdRole: b"memberId",
        NameRole: b"memberName",
        EmailRole: b"memberEmail",
        RoleRole: b"memberRole",
        RoleLabelRole: b"memberRoleLabel",
        OwnerRole: b"isOwner",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        item = self._rows[index.row()]
        return {
            self.IdRole: item.get("id") or "",
            self.NameRole: item.get("nome") or "",
            self.EmailRole: item.get("email") or "",
            self.RoleRole: item.get("papel") or "",
            self.RoleLabelRole: item.get("papel_texto") or "",
            self.OwnerRole: bool(item.get("proprietario")),
        }.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows or [])
        self.endResetModel()


class TeamInvitesModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    NameRole = IdRole + 1
    EmailRole = NameRole + 1
    RoleRole = EmailRole + 1
    RoleLabelRole = RoleRole + 1
    ExpiresRole = RoleLabelRole + 1

    _ROLES = {
        IdRole: b"inviteId",
        NameRole: b"inviteName",
        EmailRole: b"inviteEmail",
        RoleRole: b"inviteRole",
        RoleLabelRole: b"inviteRoleLabel",
        ExpiresRole: b"inviteExpires",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        item = self._rows[index.row()]
        return {
            self.IdRole: item.get("id") or "",
            self.NameRole: item.get("nome") or "",
            self.EmailRole: item.get("email") or "",
            self.RoleRole: item.get("papel") or "",
            self.RoleLabelRole: item.get("papel_texto") or "",
            self.ExpiresRole: item.get("expira_em") or "",
        }.get(role)

    def roleNames(self):
        return self._ROLES

    def substituir(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = list(rows or [])
        self.endResetModel()


class EquipeController(QObject):
    estadoAlterado = Signal()
    feedback = Signal(str, str)
    conviteCriado = Signal(str, str)
    _resultado = Signal(object, object)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self._database = database
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="prontu-qml-equipe"
        )
        self._membros = TeamMembersModel(self)
        self._convites = TeamInvitesModel(self)
        self._ocupado = False
        self._limite = 0
        self._usados = 0
        self._resultado.connect(self._receber_resultado)

    @Property(QObject, constant=True)
    def membrosModel(self):
        return self._membros

    @Property(QObject, constant=True)
    def convitesModel(self):
        return self._convites

    @Property(bool, notify=estadoAlterado)
    def ocupado(self) -> bool:
        return self._ocupado

    @Property(int, notify=estadoAlterado)
    def totalMembros(self) -> int:
        return self._membros.rowCount()

    @Property(int, notify=estadoAlterado)
    def totalConvites(self) -> int:
        return self._convites.rowCount()

    @Property(int, notify=estadoAlterado)
    def limite(self) -> int:
        return self._limite

    @Property(int, notify=estadoAlterado)
    def usados(self) -> int:
        return self._usados

    @Property(int, notify=estadoAlterado)
    def disponiveis(self) -> int:
        return max(self._limite - self._usados, 0)

    @Property(str, notify=estadoAlterado)
    def resumoVagas(self) -> str:
        if self._limite <= 0:
            return "Carregando vagas do plano..."
        return (
            f"{self._usados} de {self._limite} vagas usadas"
            " · convites pendentes também reservam vaga"
        )

    def _definir_ocupado(self, valor: bool) -> None:
        if self._ocupado != valor:
            self._ocupado = valor
            self.estadoAlterado.emit()

    def _enviar(self, operacao: str, tarefa) -> None:
        self._definir_ocupado(True)
        futuro = self._executor.submit(tarefa)

        def concluido(resultado: Future):
            try:
                self._resultado.emit((operacao, resultado.result()), None)
            except Exception as erro:
                self._resultado.emit((operacao, None), str(erro))

        futuro.add_done_callback(concluido)

    @Slot()
    def carregar(self) -> None:
        if self._ocupado:
            return
        if str(self._database.obter_papel_atual()).lower() != "proprietario":
            self.feedback.emit(
                "error", "A gestão da equipe é exclusiva do proprietário."
            )
            return
        if not self._database.possui_recurso("equipe"):
            self.feedback.emit(
                "warning", "A gestão de equipe não está disponível neste plano."
            )
            return
        self._enviar("carregar", self._database.listar_equipe)

    @Slot(str, str, str)
    def criarConvite(self, nome: str, email: str, papel: str) -> None:
        if self._ocupado:
            return
        problema = validar_convite(nome, email, papel)
        if problema:
            self.feedback.emit("warning", problema)
            return
        if self.disponiveis <= 0:
            self.feedback.emit("warning", "Todas as vagas do plano estão ocupadas.")
            return
        self._enviar(
            "convidar",
            lambda: self._database.criar_convite_equipe(
                str(nome).strip(), str(email).strip().lower(), str(papel)
            ),
        )

    @Slot(str, str)
    def alterarPapel(self, membro_id: str, papel: str) -> None:
        if self._ocupado or not membro_id:
            return
        if str(papel) not in {"profissional", "secretaria"}:
            self.feedback.emit("warning", "Selecione um papel válido.")
            return
        self._enviar(
            "alterar_papel",
            lambda: self._database.alterar_papel_equipe(membro_id, papel),
        )

    @Slot(str)
    def revogarMembro(self, membro_id: str) -> None:
        if not self._ocupado and membro_id:
            self._enviar(
                "revogar_membro",
                lambda: self._database.revogar_acesso_equipe("membro", membro_id),
            )

    @Slot(str)
    def cancelarConvite(self, convite_id: str) -> None:
        if not self._ocupado and convite_id:
            self._enviar(
                "cancelar_convite",
                lambda: self._database.revogar_acesso_equipe(
                    "convite", convite_id
                ),
            )

    @Slot(str, str)
    def renovarConvite(self, convite_id: str, email: str) -> None:
        if not self._ocupado and convite_id:
            self._enviar(
                "renovar_convite",
                lambda: {
                    "convite": self._database.renovar_convite_equipe(
                        convite_id
                    ),
                    "email": str(email or ""),
                },
            )

    @Slot(str)
    def copiarCodigo(self, codigo: str) -> None:
        QGuiApplication.clipboard().setText(str(codigo or ""))
        self.feedback.emit("success", "Código copiado.")

    @Slot(object, object)
    def _receber_resultado(self, pacote, erro) -> None:
        self._definir_ocupado(False)
        operacao, resultado = pacote or ("", None)
        if erro:
            self.feedback.emit("error", "Não foi possível concluir esta ação.")
            return
        if operacao == "carregar":
            if not resultado:
                mensagem = getattr(
                    self._database,
                    "obter_ultimo_erro_funcao",
                    lambda: "Não foi possível carregar a equipe.",
                )()
                self.feedback.emit("error", mensagem)
                return
            equipe = preparar_equipe(resultado)
            self._membros.substituir(equipe["membros"])
            self._convites.substituir(equipe["convites"])
            self._limite = equipe["limite"]
            self._usados = equipe["usados"]
            self.estadoAlterado.emit()
            return
        if not resultado:
            mensagem = getattr(
                self._database,
                "obter_ultimo_erro_funcao",
                lambda: "Não foi possível concluir esta ação.",
            )()
            self.feedback.emit("error", mensagem)
            return
        if operacao in {"convidar", "renovar_convite"}:
            convite = (
                resultado.get("convite")
                if operacao == "renovar_convite"
                else resultado
            )
            if not convite:
                self.feedback.emit("error", "Não foi possível gerar o código.")
                return
            codigo = str(convite.get("codigo") or "")
            if not codigo:
                self.feedback.emit("error", "O servidor não retornou o código.")
                return
            email = (
                resultado.get("email")
                if operacao == "renovar_convite"
                else resultado.get("email")
            )
            self.conviteCriado.emit(codigo, str(email or ""))
        mensagens = {
            "convidar": "Convite criado.",
            "renovar_convite": "Novo código gerado.",
            "alterar_papel": "Papel atualizado.",
            "revogar_membro": "Acesso revogado.",
            "cancelar_convite": "Convite cancelado.",
        }
        self.feedback.emit("success", mensagens.get(operacao, "Ação concluída."))
        self.carregar()
