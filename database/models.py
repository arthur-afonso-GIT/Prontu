"""
Modelos ORM (SQLAlchemy) do Clinic Manager.

RELACIONAMENTOS GERAIS DO SCHEMA
---------------------------------

    Pasta (1) ──── (N) Paciente
        Uma pasta pode conter vários pacientes; um paciente pertence a,
        no máximo, uma pasta (FK opcional `pasta_id` em Paciente). Isso
        modela a organização "estilo Notion" pedida no projeto, onde
        pastas são apenas etiquetas de organização visual na Home —
        nunca uma dependência estrutural (excluir uma pasta não deve
        excluir pacientes; ver `on_delete` abaixo).

    Paciente (1) ──── (N) Consulta
        Um paciente pode ter várias consultas ao longo do tempo. Cada
        consulta pertence a exatamente um paciente. Exclusão de paciente
        em cascata remove suas consultas (uma consulta sem paciente não
        tem sentido de negócio).

    Paciente (1) ──── (N) RespostaFormulario
        Um paciente pode ter múltiplas respostas de fichas dinâmicas ao
        longo do tempo (ex: 5 avaliações de bioimpedância em datas
        diferentes, cada uma sendo uma `RespostaFormulario` distinta).
        Isso é o que permite o "histórico completo por paciente" e a
        "comparação temporal" pedidos no projeto.

    Formulario (1) ──── (N) RespostaFormulario
        Um modelo de formulário (ex: "Ficha de Bioimpedância v2") pode
        ser respondido várias vezes, por pacientes diferentes ou pelo
        mesmo paciente em datas diferentes. A FK `formulario_id` em
        `RespostaFormulario` aponta para qual estrutura de campos foi
        usada para gerar aquela resposta — isto é o que permite manter
        o histórico íntegro mesmo que o formulário seja **versionado**
        (ver campo `versao` em Formulario): respostas antigas continuam
        legíveis mesmo que a estrutura do formulário mude no futuro,
        pois cada resposta referencia a versão exata que a originou
        através de `formulario_versao_id` -> ver nota na classe.

POR QUE JSON EM VEZ DE EAV
---------------------------
    `Formulario.estrutura_json` guarda a definição dos campos (tipo,
    label, posição, validações) e `RespostaFormulario.dados_json` guarda
    os valores preenchidos pelo paciente/profissional. Avaliamos EAV
    (Entity-Attribute-Value, uma tabela genérica `atributo/valor` por
    campo) e descartamos por três razões:

    1. Performance: EAV exige N joins para reconstruir um único registro
       de formulário (um join por campo), o que degrada rapidamente em
       fichas com 30-60 campos como as de avaliação nutricional/score.
       JSON reconstrói o formulário inteiro em uma única leitura de linha.
    2. Flexibilidade de estrutura: cada tipo de ficha médica importada
       tem um conjunto de campos completamente diferente e não sabemos
       esses campos em tempo de design do schema (eles vêm de PDFs/DOCX
       arbitrários enviados pelo usuário). JSON aceita qualquer estrutura
       sem alteração de schema; EAV também aceita, mas ao custo de (1).
    3. Simplicidade de versionamento: ao evoluir um formulário, basta
       gravar um novo JSON de estrutura com versão incrementada. Em EAV,
       isso exigiria lógica adicional de migração de atributos.

    O custo aceito desta escolha é que buscas dentro do conteúdo do JSON
    (ex: "todos os pacientes com IMC > 30") exigem funções JSON do SQLite
    (`json_extract`) em vez de um simples WHERE relacional. Para os
    volumes de uma clínica (milhares, não milhões de registros), isso é
    plenamente aceitável e o SQLite moderno (>=3.38) tem suporte nativo
    a operadores JSON com performance adequada.
"""

from __future__ import annotations

import enum
import json
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from utils.age_calculator import calculate_age


class Base(DeclarativeBase):
    """Classe base declarativa compartilhada por todos os modelos."""
    pass


class SexoEnum(str, enum.Enum):
    """Enum de sexo biológico do paciente, usado para campos clínicos."""
    MASCULINO = "masculino"
    FEMININO = "feminino"
    OUTRO = "outro"


class StatusConsultaEnum(str, enum.Enum):
    """Status do ciclo de vida de uma consulta agendada."""
    AGENDADA = "agendada"
    CONFIRMADA = "confirmada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    FALTOU = "faltou"


class TipoFormularioEnum(str, enum.Enum):
    """Categoriza o formulário dinâmico para fins de filtro/ícone na UI."""
    EVOLUCAO_CLINICA = "evolucao_clinica"
    AVALIACAO_NUTRICIONAL = "avaliacao_nutricional"
    BIOIMPEDANCIA = "bioimpedancia"
    ORTOPEDIA = "ortopedia"
    DERMATOLOGIA = "dermatologia"
    CARDIOLOGIA = "cardiologia"
    PEDIATRIA = "pediatria"
    GINECOLOGIA = "ginecologia"
    SCORE_CLINICO = "score_clinico"
    OUTRO = "outro"


class Pasta(Base):
    """Pasta de organização visual de pacientes na Home (estilo Notion).

    Relacionamento:
        1 Pasta -> N Pacientes (ver `Paciente.pasta_id`).
        A exclusão de uma pasta NÃO exclui os pacientes nela contidos;
        a FK em Paciente usa `ondelete="SET NULL"`, então os pacientes
        simplesmente voltam a ficar "sem pasta".
    """

    __tablename__ = "pastas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    cor: Mapped[str] = mapped_column(String(20), nullable=False, default="#6366F1")
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    pacientes: Mapped[list["Paciente"]] = relationship(
        back_populates="pasta", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Pasta id={self.id} nome={self.nome!r}>"


class Paciente(Base):
    """Cadastro de paciente.

    Nota crítica de negócio: NÃO existe coluna de idade. A idade é
    sempre derivada via a property `idade`, calculada a partir de
    `data_nascimento` no momento da leitura — nunca persistida, para
    evitar que o dado fique desatualizado com o passar do tempo.

    Relacionamentos:
        N Paciente -> 1 Pasta (opcional).
        1 Paciente -> N Consulta (cascade delete: ao excluir o paciente,
            suas consultas são removidas, pois não fazem sentido órfãs).
        1 Paciente -> N RespostaFormulario (cascade delete pelo mesmo
            motivo, embora na prática a UI deva sempre confirmar
            explicitamente essa ação com o usuário antes de executá-la).
    """

    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    sexo: Mapped[SexoEnum] = mapped_column(Enum(SexoEnum), nullable=False)
    convenio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_cadastro: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Campos clínicos (ficha do paciente) — TextArea expansível na UI.
    qp: Mapped[str | None] = mapped_column(Text, nullable=True)  # Queixa Principal
    hda: Mapped[str | None] = mapped_column(Text, nullable=True)  # História da Doença Atual
    antecedentes: Mapped[str | None] = mapped_column(Text, nullable=True)
    exame_fisico: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pasta_id: Mapped[int | None] = mapped_column(
        ForeignKey("pastas.id", ondelete="SET NULL"), nullable=True
    )

    pasta: Mapped["Pasta | None"] = relationship(back_populates="pacientes", lazy="selectin")
    consultas: Mapped[list["Consulta"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
        order_by="desc(Consulta.data)",
        lazy="selectin",
    )
    respostas_formulario: Mapped[list["RespostaFormulario"]] = relationship(
        back_populates="paciente",
        cascade="all, delete-orphan",
        order_by="desc(RespostaFormulario.data)",
        lazy="selectin",
    )

    @property
    def idade(self) -> int:
        """Idade calculada em tempo real a partir da data de nascimento."""
        return calculate_age(self.data_nascimento)

    @property
    def ultima_consulta(self) -> "Consulta | None":
        """Retorna a consulta mais recente do paciente, se houver."""
        return self.consultas[0] if self.consultas else None

    def __repr__(self) -> str:
        return f"<Paciente id={self.id} nome={self.nome!r}>"


class Consulta(Base):
    """Consulta/compromisso agendado para um paciente.

    Relacionamento:
        N Consulta -> 1 Paciente (obrigatório; toda consulta pertence
        a um paciente específico).
    """

    __tablename__ = "consultas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horario: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    duracao_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[StatusConsultaEnum] = mapped_column(
        Enum(StatusConsultaEnum), nullable=False, default=StatusConsultaEnum.AGENDADA
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    paciente: Mapped["Paciente"] = relationship(back_populates="consultas", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Consulta id={self.id} paciente_id={self.paciente_id} data={self.data}>"


class Formulario(Base):
    """Modelo de formulário dinâmico (estrutura de campos em JSON).

    `estrutura_json` armazena uma lista de definições de campo conforme
    o schema produzido pela engine de parsing (ver `parsers/parser_engine.py`
    e `forms/field_schema.py`), por exemplo:

        [
          {"id": "qp", "tipo": "textarea", "label": "Queixa Principal"},
          {"id": "peso", "tipo": "numero", "label": "Peso (kg)"},
          {"id": "score_cha2ds2vasc", "tipo": "score", "label": "CHA2DS2-VASc",
           "itens": [...]}
        ]

    Relacionamento:
        1 Formulario -> N RespostaFormulario.

    Versionamento:
        Quando um formulário é editado de forma estrutural (campos
        adicionados/removidos), uma NOVA linha é criada com `nome` igual
        e `versao` incrementada, em vez de sobrescrever a estrutura
        existente. Isso garante que respostas antigas (que referenciam
        o `formulario_id` da versão antiga) continuem sendo exibidas
        corretamente com os campos que existiam quando foram preenchidas.
    """

    __tablename__ = "formularios"
    __table_args__ = (UniqueConstraint("nome", "versao", name="uq_formulario_nome_versao"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tipo: Mapped[TipoFormularioEnum] = mapped_column(
        Enum(TipoFormularioEnum), nullable=False, default=TipoFormularioEnum.OUTRO
    )
    estrutura_json: Mapped[str] = mapped_column(Text, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    origem_arquivo: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="Nome do PDF/DOCX original que originou este formulário."
    )

    respostas: Mapped[list["RespostaFormulario"]] = relationship(
        back_populates="formulario", lazy="selectin"
    )

    def get_estrutura(self) -> list[dict]:
        """Desserializa `estrutura_json` para uma lista de dicts Python."""
        return json.loads(self.estrutura_json)

    def set_estrutura(self, estrutura: list[dict]) -> None:
        """Serializa uma lista de dicts Python para `estrutura_json`."""
        self.estrutura_json = json.dumps(estrutura, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"<Formulario id={self.id} nome={self.nome!r} v{self.versao}>"


class RespostaFormulario(Base):
    """Resposta preenchida de um formulário dinâmico para um paciente.

    `dados_json` armazena um dict `{campo_id: valor}` espelhando os
    `id`s definidos em `Formulario.estrutura_json`, por exemplo:

        {"qp": "Dor lombar há 3 dias", "peso": 78.5,
         "score_cha2ds2vasc": {"itens_marcados": [...], "total": 4}}

    Relacionamentos:
        N RespostaFormulario -> 1 Paciente (obrigatório).
        N RespostaFormulario -> 1 Formulario (obrigatório; aponta para a
            versão exata da estrutura usada nesta resposta).
    """

    __tablename__ = "respostas_formulario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paciente_id: Mapped[int] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    formulario_id: Mapped[int] = mapped_column(
        ForeignKey("formularios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dados_json: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )

    paciente: Mapped["Paciente"] = relationship(back_populates="respostas_formulario", lazy="selectin")
    formulario: Mapped["Formulario"] = relationship(back_populates="respostas", lazy="selectin")

    def get_dados(self) -> dict:
        """Desserializa `dados_json` para um dict Python."""
        return json.loads(self.dados_json)

    def set_dados(self, dados: dict) -> None:
        """Serializa um dict Python para `dados_json`."""
        self.dados_json = json.dumps(dados, ensure_ascii=False, default=str)

    def __repr__(self) -> str:
        return (
            f"<RespostaFormulario id={self.id} paciente_id={self.paciente_id} "
            f"formulario_id={self.formulario_id}>"
        )
