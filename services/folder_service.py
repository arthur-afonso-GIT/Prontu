"""
Service Layer de Pastas (organização visual de pacientes na Home).
"""

from __future__ import annotations

from database.database import get_session
from database.models import Pasta
from database.repositories.folder_repository import FolderRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class FolderServiceError(Exception):
    """Erro de negócio ao manipular pastas."""
    pass


class FolderService:
    """Orquestra operações de negócio relacionadas a pastas de organização."""

    def create_folder(self, nome: str, cor: str = "#6366F1") -> int:
        """Cria uma nova pasta, posicionando-a no final da lista existente."""
        nome = nome.strip()
        if not nome:
            raise FolderServiceError("O nome da pasta não pode ser vazio.")

        with get_session() as session:
            repo = FolderRepository(session)
            pasta = Pasta(nome=nome, cor=cor, ordem=repo.get_next_order_index())
            repo.add(pasta)
            logger.info("Pasta criada: id=%s nome=%s", pasta.id, pasta.nome)
            return pasta.id

    def rename_folder(self, pasta_id: int, novo_nome: str) -> None:
        novo_nome = novo_nome.strip()
        if not novo_nome:
            raise FolderServiceError("O nome da pasta não pode ser vazio.")

        with get_session() as session:
            repo = FolderRepository(session)
            pasta = repo.get_by_id(pasta_id)
            if pasta is None:
                raise FolderServiceError(f"Pasta id={pasta_id} não encontrada.")
            pasta.nome = novo_nome

    def update_folder_color(self, pasta_id: int, cor: str) -> None:
        with get_session() as session:
            repo = FolderRepository(session)
            pasta = repo.get_by_id(pasta_id)
            if pasta is None:
                raise FolderServiceError(f"Pasta id={pasta_id} não encontrada.")
            pasta.cor = cor

    def reorder_folders(self, pasta_ids_em_ordem: list[int]) -> None:
        with get_session() as session:
            FolderRepository(session).reorder(pasta_ids_em_ordem)

    def delete_folder(self, pasta_id: int) -> None:
        """Exclui a pasta. Pacientes vinculados NÃO são excluídos (ver FK SET NULL)."""
        with get_session() as session:
            repo = FolderRepository(session)
            pasta = repo.get_by_id(pasta_id)
            if pasta is None:
                raise FolderServiceError(f"Pasta id={pasta_id} não encontrada.")
            repo.delete(pasta)
            logger.info("Pasta removida: id=%s", pasta_id)

    def list_folders(self) -> list[Pasta]:
        with get_session() as session:
            return FolderRepository(session).list_ordered()
