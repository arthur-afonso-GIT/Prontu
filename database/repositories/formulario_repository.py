"""
Repositório de Formulários Dinâmicos e suas Respostas.

Gerencia tanto os modelos de formulário (`Formulario`, a estrutura) como
as respostas preenchidas (`RespostaFormulario`), pois ambos compõem o
mesmo agregado de domínio "Fichas Dinâmicas".
"""

from __future__ import annotations

from database.models import Formulario, RespostaFormulario, TipoFormularioEnum
from database.repositories.base_repository import BaseRepository


class FormularioRepository(BaseRepository[Formulario]):
    """Repositório especializado para a entidade `Formulario`."""

    model = Formulario

    def list_active(self) -> list[Formulario]:
        """Lista apenas formulários ativos (não descontinuados)."""
        return list(
            self.session.query(Formulario)
            .filter(Formulario.ativo.is_(True))
            .order_by(Formulario.nome.asc())
            .all()
        )

    def list_by_tipo(self, tipo: TipoFormularioEnum) -> list[Formulario]:
        """Lista formulários ativos de uma categoria clínica específica."""
        return list(
            self.session.query(Formulario)
            .filter(Formulario.tipo == tipo, Formulario.ativo.is_(True))
            .order_by(Formulario.nome.asc())
            .all()
        )

    def get_latest_version(self, nome: str) -> Formulario | None:
        """Retorna a versão mais recente de um formulário pelo nome.

        Usado ao reimportar/editar um formulário existente: a nova versão
        deve ser criada com `versao = get_latest_version(nome).versao + 1`.
        """
        return (
            self.session.query(Formulario)
            .filter(Formulario.nome == nome)
            .order_by(Formulario.versao.desc())
            .first()
        )


class RespostaFormularioRepository(BaseRepository[RespostaFormulario]):
    """Repositório especializado para a entidade `RespostaFormulario`."""

    model = RespostaFormulario

    def list_by_patient(self, paciente_id: int) -> list[RespostaFormulario]:
        """Lista todas as respostas de formulário de um paciente (histórico)."""
        return list(
            self.session.query(RespostaFormulario)
            .filter(RespostaFormulario.paciente_id == paciente_id)
            .order_by(RespostaFormulario.data.desc())
            .all()
        )

    def list_by_patient_and_formulario(
        self, paciente_id: int, formulario_id: int
    ) -> list[RespostaFormulario]:
        """Lista respostas de um paciente para um formulário específico.

        Usado para construir a "comparação temporal" pedida no projeto:
        ex. todas as respostas de "Bioimpedância" de um mesmo paciente,
        ordenadas cronologicamente, para montar um gráfico de evolução.
        """
        return list(
            self.session.query(RespostaFormulario)
            .filter(
                RespostaFormulario.paciente_id == paciente_id,
                RespostaFormulario.formulario_id == formulario_id,
            )
            .order_by(RespostaFormulario.data.asc())
            .all()
        )
