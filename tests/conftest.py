"""
Fixtures compartilhadas de teste (pytest).

A variavel de ambiente CLINIC_MANAGER_DATABASE_URL (definida em
conftest.py na raiz do projeto, carregado antes deste) ja garante que
toda a suite de testes rode contra um arquivo SQLite temporario,
completamente isolado do banco de dados real do usuario.

Esta fixture garante adicionalmente que cada teste individual comece
com tabelas vazias, evitando que dados de um teste contaminem o proximo.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import close_all_sessions

from database.database import engine, init_database
from database.models import Base


@pytest.fixture(autouse=True)
def clean_database():
    """Recria o schema do banco de teste antes de cada funcao de teste."""
    close_all_sessions()
    Base.metadata.drop_all(bind=engine)
    init_database()
    yield
    close_all_sessions()
