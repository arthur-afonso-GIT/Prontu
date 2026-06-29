"""
Service Layer de Fichas Dinâmicas (Formulários).

Conecta a `ParserEngine` (camada `parsers/`) à persistência (camada
`database/`), e gerencia o ciclo de vida de formulários (criação,
versionamento) e de respostas de pacientes a esses formulários.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from database.database import get_session
from database.models import Formulario, RespostaFormulario, TipoFormularioEnum
from database.repositories.formulario_repository import (
    FormularioRepository,
    RespostaFormularioRepository,
)
from forms.field_schema import FieldDefinition
from parsers.parser_engine import ParserEngine, ParserEngineError
from utils.logger import get_logger

logger = get_logger(__name__)


class DynamicFormServiceError(Exception):
    """Erro de negócio ao manipular fichas dinâmicas."""
    pass


class DynamicFormService:
    """Orquestra importação, versionamento e respostas de fichas dinâmicas."""

    def __init__(self) -> None:
        self._parser_engine = ParserEngine()

    def import_document_as_form(
        self,
        file_path: str | Path,
        nome_formulario: str,
        tipo: TipoFormularioEnum = TipoFormularioEnum.OUTRO,
        copiar_para_uploads: bool = True,
    ) -> tuple[int, list[FieldDefinition]]:
        """Importa um PDF/DOCX e o converte em um novo `Formulario`.

        Se já existir um formulário com o mesmo nome, cria automaticamente
        uma nova versão (incrementando `versao`) em vez de sobrescrever,
        preservando o histórico de respostas antigas (ver docstring do
        modelo `Formulario`).

        Args:
            file_path: Caminho do arquivo PDF/DOCX a importar.
            nome_formulario: Nome amigável que o usuário deu ao formulário.
            tipo: Categoria clínica do formulário.
            copiar_para_uploads: Se True, copia o arquivo original para
                o diretório de uploads da aplicação (preservando o
                documento-fonte para referência futura).

        Returns:
            Tupla (id do formulário criado, lista de campos detectados),
            permitindo que a UI exiba os campos para revisão antes de
            confirmar a criação definitiva, se desejado.

        Raises:
            DynamicFormServiceError: Se o parsing falhar.
        """
        file_path = Path(file_path)

        try:
            campos = self._parser_engine.parse_document(file_path)
        except ParserEngineError as exc:
            raise DynamicFormServiceError(str(exc)) from exc

        nome_arquivo_salvo = file_path.name
        if copiar_para_uploads:
            nome_arquivo_salvo = self._copy_to_uploads(file_path)

        with get_session() as session:
            repo = FormularioRepository(session)
            versao_anterior = repo.get_latest_version(nome_formulario)
            nova_versao = (versao_anterior.versao + 1) if versao_anterior else 1

            formulario = Formulario(
                nome=nome_formulario,
                versao=nova_versao,
                tipo=tipo,
                origem_arquivo=nome_arquivo_salvo,
            )
            formulario.set_estrutura([campo.model_dump(mode="json") for campo in campos])
            repo.add(formulario)

            logger.info(
                "Formulário importado: id=%s nome=%s v%s (%d campos)",
                formulario.id, nome_formulario, nova_versao, len(campos),
            )
            return formulario.id, campos

    def _copy_to_uploads(self, file_path: Path) -> str:
        """Copia o documento original para o diretório de uploads persistente."""
        from config import config

        destino = config.uploads_dir() / file_path.name
        contador = 1
        while destino.exists():
            destino = config.uploads_dir() / f"{file_path.stem}_{contador}{file_path.suffix}"
            contador += 1

        shutil.copy2(file_path, destino)
        return destino.name

    def update_form_structure(self, formulario_id: int, campos: list[FieldDefinition]) -> None:
        """Atualiza a estrutura de um formulário (ex: após edição manual na UI de revisão)."""
        with get_session() as session:
            repo = FormularioRepository(session)
            formulario = repo.get_by_id(formulario_id)
            if formulario is None:
                raise DynamicFormServiceError(f"Formulário id={formulario_id} não encontrado.")
            formulario.set_estrutura([campo.model_dump(mode="json") for campo in campos])

    def deactivate_form(self, formulario_id: int) -> None:
        """Marca um formulário como inativo (não exclui, preserva histórico)."""
        with get_session() as session:
            repo = FormularioRepository(session)
            formulario = repo.get_by_id(formulario_id)
            if formulario is None:
                raise DynamicFormServiceError(f"Formulário id={formulario_id} não encontrado.")
            formulario.ativo = False

    def list_active_forms(self) -> list[Formulario]:
        with get_session() as session:
            return FormularioRepository(session).list_active()

    def list_forms_by_type(self, tipo: TipoFormularioEnum) -> list[Formulario]:
        with get_session() as session:
            return FormularioRepository(session).list_by_tipo(tipo)

    def get_form(self, formulario_id: int) -> Formulario | None:
        with get_session() as session:
            repo = FormularioRepository(session)
            formulario = repo.get_by_id(formulario_id)
            if formulario:
                session.refresh(formulario)
            return formulario

    # ------------------------------------------------------------------
    # Respostas de pacientes
    # ------------------------------------------------------------------

    def save_response(self, paciente_id: int, formulario_id: int, dados: dict) -> int:
        """Persiste a resposta de um paciente a um formulário dinâmico."""
        with get_session() as session:
            repo = RespostaFormularioRepository(session)
            resposta = RespostaFormulario(paciente_id=paciente_id, formulario_id=formulario_id)
            resposta.set_dados(dados)
            repo.add(resposta)
            logger.info(
                "Resposta de formulário salva: paciente_id=%s formulario_id=%s resposta_id=%s",
                paciente_id, formulario_id, resposta.id,
            )
            return resposta.id

    def update_response(self, resposta_id: int, dados: dict) -> None:
        """Atualiza os dados de uma resposta já existente."""
        with get_session() as session:
            repo = RespostaFormularioRepository(session)
            resposta = repo.get_by_id(resposta_id)
            if resposta is None:
                raise DynamicFormServiceError(f"Resposta id={resposta_id} não encontrada.")
            resposta.set_dados(dados)

    def get_patient_responses_for_form(
        self, paciente_id: int, formulario_id: int
    ) -> list[RespostaFormulario]:
        """Retorna o histórico de respostas de um paciente a um formulário
        específico, ordenado cronologicamente — usado para comparação temporal
        (ex: gráfico de evolução de peso/IMC ao longo das avaliações).
        """
        with get_session() as session:
            return RespostaFormularioRepository(session).list_by_patient_and_formulario(
                paciente_id, formulario_id
            )

    def get_patient_response_history(self, paciente_id: int) -> list[RespostaFormulario]:
        """Retorna todo o histórico de fichas respondidas por um paciente."""
        with get_session() as session:
            return RespostaFormularioRepository(session).list_by_patient(paciente_id)
