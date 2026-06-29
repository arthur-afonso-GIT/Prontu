"""
Repository base genérico.

Implementa o Repository Pattern: a camada de serviço nunca deve montar
queries SQLAlchemy diretamente. Toda comunicação com o banco passa por
um repositório, que encapsula os detalhes de persistência e expõe uma
interface orientada a domínio (ex: `get_by_id`, `list_all`), facilitando
testes (pode-se mockar o repositório) e trocas futuras de tecnologia de
persistência sem tocar nas regras de negócio.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from database.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Repositório genérico com operações CRUD reutilizáveis.

    Subclasses devem definir o atributo de classe `model` apontando para
    o modelo SQLAlchemy concreto que o repositório gerencia.
    """

    model: type[ModelType]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, entity_id: int) -> ModelType | None:
        """Busca uma entidade pela chave primária."""
        return self.session.get(self.model, entity_id)

    def list_all(self) -> list[ModelType]:
        """Retorna todas as entidades da tabela."""
        return list(self.session.query(self.model).all())

    def add(self, entity: ModelType) -> ModelType:
        """Adiciona uma nova entidade e dá flush para obter o ID gerado."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: ModelType) -> None:
        """Remove uma entidade existente."""
        self.session.delete(entity)
        self.session.flush()

    def commit(self) -> None:
        """Confirma a transação atual.

        Normalmente não é necessário chamar isto diretamente quando se
        usa o context manager `get_session()`, que já comita ao final do
        bloco `with`. Exposto aqui para casos em que a service precisa de
        controle explícito de commit dentro de uma única sessão.
        """
        self.session.commit()
