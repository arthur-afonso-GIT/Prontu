"""
Configuração da engine SQLAlchemy e gerenciamento de sessões.

Centraliza a criação da engine, da fábrica de sessões e da inicialização
das tabelas. Nenhum outro módulo deve criar uma engine própria — isso
garante uma única fonte de verdade para a conexão com o SQLite e evita
problemas de concorrência (ex: múltiplas conexões de escrita simultâneas
no mesmo arquivo .db).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import config
from database.models import Base
from utils.logger import get_logger

logger = get_logger(__name__)

# `check_same_thread=False` é necessário porque a interface Qt pode, em
# operações específicas, acessar o banco fora da thread principal (ex:
# workers de importação de PDF). A responsabilidade de não compartilhar
# uma mesma `Session` entre threads continua sendo de quem consome esta
# engine — por isso o padrão de uso é sempre `get_session()` por operação,
# nunca uma sessão de longa duração compartilhada.
engine: Engine = create_engine(
    config.database_url(),
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
    """Habilita o enforcement de FOREIGN KEY no SQLite.

    O SQLite, por padrão, não valida integridade referencial a menos que
    isso seja explicitamente habilitado por conexão. Sem isso, seria
    possível, por exemplo, excluir um paciente que ainda possui consultas
    vinculadas, corrompendo a integridade dos dados.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database() -> None:
    """Cria todas as tabelas definidas nos modelos, se ainda não existirem.

    Esta função é idempotente: pode ser chamada a cada inicialização da
    aplicação sem efeitos colaterais quando as tabelas já existem. Após
    criar o baseline via `create_all`, aplica também quaisquer migrations
    estruturais pendentes (ver `database/migrations.py`).
    """
    from database.migrations import run_pending_migrations  # import local evita ciclo

    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados inicializado/verificado com sucesso.")

    with SessionLocal() as session:
        run_pending_migrations(session)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco de dados com commit/rollback automáticos.

    Uso recomendado (sempre via `with`):
        with get_session() as session:
            session.add(objeto)

    Em caso de exceção dentro do bloco `with`, a transação é revertida
    (rollback) e a exceção é re-lançada para que a camada de serviço
    possa tratá-la adequadamente.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Erro durante transação de banco de dados; rollback executado.")
        raise
    finally:
        session.close()
