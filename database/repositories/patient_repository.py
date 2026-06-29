"""
Repositório de Pacientes.

Concentra todas as queries específicas de paciente: busca textual,
filtros (cidade, convênio, pasta), ordenação e paginação. A camada de
serviço (`services/patient_service.py`) consome estes métodos sem nunca
precisar conhecer detalhes de SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import func, or_

from database.models import Consulta, Paciente
from database.repositories.base_repository import BaseRepository


class PatientRepository(BaseRepository[Paciente]):
    """Repositório especializado para a entidade `Paciente`."""

    model = Paciente

    def search(
        self,
        texto: str | None = None,
        cidade: str | None = None,
        convenio: str | None = None,
        pasta_id: int | None = None,
        order_by: str = "nome",
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Paciente], int]:
        """Busca paginada de pacientes com filtros combináveis.

        Args:
            texto: Busca textual (case-insensitive) em nome ou telefone.
            cidade: Filtro exato de cidade.
            convenio: Filtro exato de convênio.
            pasta_id: Filtro por pasta de organização.
            order_by: Campo de ordenação: "nome", "data_cadastro" ou
                "ultima_consulta".
            page: Número da página (1-indexado).
            page_size: Quantidade de registros por página.

        Returns:
            Tupla (lista de pacientes da página, total de registros que
            satisfazem o filtro, antes da paginação).
        """
        query = self.session.query(Paciente)

        if texto:
            termo = f"%{texto.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Paciente.nome).like(termo),
                    Paciente.telefone.like(f"%{texto}%"),
                )
            )

        if cidade:
            query = query.filter(Paciente.cidade == cidade)

        if convenio:
            query = query.filter(Paciente.convenio == convenio)

        if pasta_id is not None:
            query = query.filter(Paciente.pasta_id == pasta_id)

        total = query.count()

        if order_by == "data_cadastro":
            query = query.order_by(Paciente.data_cadastro.desc())
        else:
            # "ultima_consulta" exigiria um join/subquery; por simplicidade
            # e por já carregarmos consultas via lazy="selectin", a
            # ordenação por última consulta é resolvida em memória na
            # camada de serviço quando explicitamente solicitada.
            query = query.order_by(Paciente.nome.asc())

        offset = (page - 1) * page_size
        resultados = query.offset(offset).limit(page_size).all()

        return list(resultados), total

    def list_recent(self, limit: int = 10) -> list[Paciente]:
        """Retorna os pacientes mais recentemente cadastrados (para a Home)."""
        return list(
            self.session.query(Paciente)
            .order_by(Paciente.data_cadastro.desc())
            .limit(limit)
            .all()
        )

    def list_distinct_cidades(self) -> list[str]:
        """Lista cidades distintas cadastradas, para popular filtros na UI."""
        rows = (
            self.session.query(Paciente.cidade)
            .filter(Paciente.cidade.isnot(None))
            .distinct()
            .order_by(Paciente.cidade)
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def list_distinct_convenios(self) -> list[str]:
        """Lista convênios distintos cadastrados, para popular filtros na UI."""
        rows = (
            self.session.query(Paciente.convenio)
            .filter(Paciente.convenio.isnot(None))
            .distinct()
            .order_by(Paciente.convenio)
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def get_last_consulta_date(self, paciente_id: int):
        """Retorna a data da última consulta de um paciente, se existir."""
        result = (
            self.session.query(Consulta.data)
            .filter(Consulta.paciente_id == paciente_id)
            .order_by(Consulta.data.desc())
            .first()
        )
        return result[0] if result else None
