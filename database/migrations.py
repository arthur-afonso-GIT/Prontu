"""
Sistema de migrations leve para o Clinic Manager.

Por que não usar Alembic:
    Alembic é a ferramenta padrão para projetos SQLAlchemy de médio/grande
    porte, mas adiciona uma camada de complexidade (diretório de versões,
    `env.py`, comandos de CLI) desproporcional para um aplicativo desktop
    que distribui um único arquivo SQLite por instalação. Em vez disso,
    implementamos um mecanismo simples e auditável: uma tabela de controle
    (`schema_migrations`) que registra quais migrations já foram aplicadas,
    e uma lista ordenada de funções Python idempotentes.

    Isso é suficiente para o caso de uso (uma máquina, um arquivo .db) e
    mantém o empacotamento simples — sem depender de templates externos
    de migration que o PyInstaller precisaria embutir como dados.

Quando usar isto:
    Toda vez que o schema precisar evoluir de forma incompatível com
    `create_all()` (ex: renomear uma coluna, alterar um tipo, popular
    dados em uma coluna nova obrigatória), adicione uma nova entrada na
    lista `MIGRATIONS` abaixo. Migrations aditivas simples (nova coluna
    opcional, nova tabela) já são cobertas automaticamente por
    `Base.metadata.create_all()` em `database.py` e não precisam de
    entrada aqui.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from utils.logger import get_logger

logger = get_logger(__name__)

MigrationFunc = Callable[[Session], None]


def _migration_0001_initial_schema_marker(session: Session) -> None:
    """Marco inicial — não executa alterações, apenas documenta o baseline.

    Esta migration existe para que o histórico de migrations comece a
    partir da versão 1 do schema definido em `database/models.py`. Toda
    alteração estrutural futura deve ser registrada como uma nova função
    `_migration_000N_descricao` e adicionada à lista `MIGRATIONS`.
    """
    logger.info("Migration 0001: schema inicial registrado (sem alterações).")


# Lista ordenada de migrations. A ordem da lista define a ordem de execução.
MIGRATIONS: list[tuple[str, MigrationFunc]] = [
    ("0001_initial_schema_marker", _migration_0001_initial_schema_marker),
]


def _ensure_migrations_table(session: Session) -> None:
    """Cria a tabela de controle de migrations se não existir."""
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
    )


def _is_applied(session: Session, migration_id: str) -> bool:
    result = session.execute(
        text("SELECT 1 FROM schema_migrations WHERE id = :id"), {"id": migration_id}
    ).first()
    return result is not None


def _mark_applied(session: Session, migration_id: str) -> None:
    session.execute(
        text("INSERT INTO schema_migrations (id) VALUES (:id)"), {"id": migration_id}
    )


def run_pending_migrations(session: Session) -> None:
    """Executa, em ordem, todas as migrations ainda não aplicadas.

    Deve ser chamada após `init_database()` ter criado as tabelas base
    via `create_all()`, garantindo que as migrations rodem sobre um
    schema já existente.
    """
    _ensure_migrations_table(session)

    for migration_id, migration_func in MIGRATIONS:
        if _is_applied(session, migration_id):
            continue

        logger.info("Aplicando migration: %s", migration_id)
        migration_func(session)
        _mark_applied(session, migration_id)
        session.commit()

    logger.info("Todas as migrations pendentes foram aplicadas.")
