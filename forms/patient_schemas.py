"""
Schemas Pydantic (DTOs) relacionados a Paciente.

Por que usar Pydantic aqui além do SQLAlchemy:
    Os modelos SQLAlchemy (`database/models.py`) representam a estrutura
    de PERSISTÊNCIA. Estes schemas representam a estrutura de DADOS DE
    ENTRADA validados, vindos da UI (formulário Qt) antes de tocarem o
    banco. Separar os dois evita que regras de validação (ex: "telefone
    deve ter ao menos 10 dígitos") fiquem misturadas com a definição de
    colunas do banco, e permite validar o dado ANTES de abrir uma sessão
    de banco — falhando rápido, sem transação desnecessária.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from database.models import SexoEnum
from utils.phone_utils import clean_phone_digits


class PacienteCreateSchema(BaseModel):
    """Dados necessários para criar um novo paciente."""

    nome: str = Field(min_length=2, max_length=150)
    endereco: str | None = Field(default=None, max_length=255)
    cidade: str | None = Field(default=None, max_length=100)
    telefone: str | None = Field(default=None, max_length=30)
    data_nascimento: date
    sexo: SexoEnum
    convenio: str | None = Field(default=None, max_length=100)
    pasta_id: int | None = None

    qp: str | None = None
    hda: str | None = None
    antecedentes: str | None = None
    exame_fisico: str | None = None
    observacoes: str | None = None

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_vazio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome do paciente não pode ser vazio.")
        return value

    @field_validator("data_nascimento")
    @classmethod
    def data_nascimento_nao_pode_ser_futura(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("A data de nascimento não pode estar no futuro.")
        return value

    @field_validator("telefone")
    @classmethod
    def telefone_deve_ter_digitos_suficientes(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        digits = clean_phone_digits(value)
        if len(digits) < 10:
            raise ValueError("Telefone deve conter DDD + número (mínimo 10 dígitos).")
        return value


class PacienteUpdateSchema(PacienteCreateSchema):
    """Dados para atualização de um paciente existente (mesmas regras de criação)."""
    pass


class PacienteListItemSchema(BaseModel):
    """Representação leve de paciente para exibição em tabelas/listas.

    Usado pelo ViewModel para popular a tabela da Home e da tela de
    Pacientes sem precisar expor o objeto ORM inteiro para a View.
    """

    model_config = {"from_attributes": True}

    id: int
    nome: str
    convenio: str | None
    telefone: str | None
    idade: int
    sexo: SexoEnum
