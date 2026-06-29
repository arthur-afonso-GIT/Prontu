"""
Repositório de Consultas (Agenda).

Concentra queries específicas do calendário: busca por intervalo de
datas (necessária para os modos Diário/Semanal/Mensal) e verificação de
conflito de horário.
"""

from __future__ import annotations

from datetime import date

from database.models import Consulta
from database.repositories.base_repository import BaseRepository


class AppointmentRepository(BaseRepository[Consulta]):
    """Repositório especializado para a entidade `Consulta`."""

    model = Consulta

    def list_by_date_range(self, start_date: date, end_date: date) -> list[Consulta]:
        """Lista consultas dentro de um intervalo de datas (inclusivo).

        Usado pelos três modos do calendário: o modo Diário passa
        `start_date == end_date`, o Semanal passa o intervalo de 7 dias,
        e o Mensal passa o intervalo do primeiro ao último dia do mês.
        """
        return (
            self.session.query(Consulta)
            .filter(Consulta.data >= start_date, Consulta.data <= end_date)
            .order_by(Consulta.data.asc(), Consulta.horario.asc())
            .all()
        )

    def list_by_patient(self, paciente_id: int) -> list[Consulta]:
        """Lista todo o histórico de consultas de um paciente específico."""
        return (
            self.session.query(Consulta)
            .filter(Consulta.paciente_id == paciente_id)
            .order_by(Consulta.data.desc())
            .all()
        )

    def has_conflict(
        self,
        target_date: date,
        horario: str,
        duracao_minutos: int,
        exclude_consulta_id: int | None = None,
    ) -> bool:
        """Verifica se já existe consulta conflitante no mesmo horário.

        Implementa uma verificação simples de sobreposição: duas
        consultas conflitam se seus intervalos [início, fim) se
        sobrepõem no mesmo dia. Usado pela camada de serviço antes de
        criar/editar uma consulta, para alertar o profissional.
        """

        def to_minutes(hhmm: str) -> int:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        novo_inicio = to_minutes(horario)
        novo_fim = novo_inicio + duracao_minutos

        consultas_do_dia = (
            self.session.query(Consulta).filter(Consulta.data == target_date).all()
        )

        for consulta in consultas_do_dia:
            if exclude_consulta_id is not None and consulta.id == exclude_consulta_id:
                continue

            existente_inicio = to_minutes(consulta.horario)
            existente_fim = existente_inicio + consulta.duracao_minutos

            sobrepoe = novo_inicio < existente_fim and existente_inicio < novo_fim
            if sobrepoe:
                return True

        return False
