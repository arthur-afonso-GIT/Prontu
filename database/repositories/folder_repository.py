"""Repositório de Pastas (organização visual de pacientes na Home)."""

from __future__ import annotations

from database.models import Pasta
from database.repositories.base_repository import BaseRepository


class FolderRepository(BaseRepository[Pasta]):
    """Repositório especializado para a entidade `Pasta`."""

    model = Pasta

    def list_ordered(self) -> list[Pasta]:
        """Lista todas as pastas respeitando a ordem definida pelo usuário."""
        return list(self.session.query(Pasta).order_by(Pasta.ordem.asc()).all())

    def get_next_order_index(self) -> int:
        """Calcula o próximo índice de ordem para uma nova pasta (no final da lista)."""
        max_ordem = self.session.query(Pasta.ordem).order_by(Pasta.ordem.desc()).first()
        return (max_ordem[0] + 1) if max_ordem else 0

    def reorder(self, pasta_ids_em_ordem: list[int]) -> None:
        """Atualiza o campo `ordem` de várias pastas conforme a nova sequência.

        Args:
            pasta_ids_em_ordem: Lista de IDs de pasta na ordem desejada
                (índice 0 = primeira posição).
        """
        for index, pasta_id in enumerate(pasta_ids_em_ordem):
            pasta = self.get_by_id(pasta_id)
            if pasta:
                pasta.ordem = index
        self.session.flush()
