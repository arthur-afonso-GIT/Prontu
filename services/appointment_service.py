"""
Service Layer de Consultas (Agenda).

Concentra as regras de negócio do módulo de calendário: criação,
reagendamento, cancelamento e detecção de conflitos de horário.
"""

from __future__ import annotations

from datetime import date, timedelta

from database.database import get_session
from database.models import Consulta, StatusConsultaEnum
from database.repositories.appointment_repository import AppointmentRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class AppointmentServiceError(Exception):
    """Erro de negócio ao manipular consultas (ex: conflito de horário)."""
    pass


class AppointmentService:
    """Orquestra operações de negócio relacionadas a consultas/agenda."""

    def create_appointment(
        self,
        paciente_id: int,
        data_consulta: date,
        horario: str,
        duracao_minutos: int = 30,
        observacoes: str | None = None,
        forcar_apesar_de_conflito: bool = False,
    ) -> int:
        """Cria uma nova consulta, verificando conflito de horário antes.

        Args:
            forcar_apesar_de_conflito: Se True, ignora a verificação de
                conflito (usado quando o profissional confirma
                explicitamente que deseja sobrepor horários, ex: encaixe).

        Raises:
            AppointmentServiceError: Se houver conflito e
                `forcar_apesar_de_conflito` for False.
        """
        with get_session() as session:
            repo = AppointmentRepository(session)

            if not forcar_apesar_de_conflito and repo.has_conflict(
                data_consulta, horario, duracao_minutos
            ):
                raise AppointmentServiceError(
                    "Já existe uma consulta agendada neste horário."
                )

            consulta = Consulta(
                paciente_id=paciente_id,
                data=data_consulta,
                horario=horario,
                duracao_minutos=duracao_minutos,
                observacoes=observacoes,
                status=StatusConsultaEnum.AGENDADA,
            )
            repo.add(consulta)
            logger.info(
                "Consulta criada: id=%s paciente_id=%s data=%s horario=%s",
                consulta.id, paciente_id, data_consulta, horario,
            )
            return consulta.id

    def update_appointment_status(self, consulta_id: int, status: StatusConsultaEnum) -> None:
        """Atualiza o status do ciclo de vida de uma consulta."""
        with get_session() as session:
            repo = AppointmentRepository(session)
            consulta = repo.get_by_id(consulta_id)
            if consulta is None:
                raise AppointmentServiceError(f"Consulta id={consulta_id} não encontrada.")
            consulta.status = status
            logger.info("Status da consulta id=%s atualizado para %s", consulta_id, status)

    def reschedule_appointment(
        self, consulta_id: int, nova_data: date, novo_horario: str
    ) -> None:
        """Reagenda uma consulta para nova data/horário, validando conflito."""
        with get_session() as session:
            repo = AppointmentRepository(session)
            consulta = repo.get_by_id(consulta_id)
            if consulta is None:
                raise AppointmentServiceError(f"Consulta id={consulta_id} não encontrada.")

            if repo.has_conflict(
                nova_data, novo_horario, consulta.duracao_minutos, exclude_consulta_id=consulta_id
            ):
                raise AppointmentServiceError(
                    "Já existe uma consulta agendada no novo horário escolhido."
                )

            consulta.data = nova_data
            consulta.horario = novo_horario
            logger.info("Consulta id=%s reagendada para %s %s", consulta_id, nova_data, novo_horario)

    def delete_appointment(self, consulta_id: int) -> None:
        """Remove (cancela definitivamente) uma consulta."""
        with get_session() as session:
            repo = AppointmentRepository(session)
            consulta = repo.get_by_id(consulta_id)
            if consulta is None:
                raise AppointmentServiceError(f"Consulta id={consulta_id} não encontrada.")
            repo.delete(consulta)
            logger.info("Consulta removida: id=%s", consulta_id)

    def get_appointments_for_day(self, target_date: date) -> list[Consulta]:
        """Retorna as consultas de um único dia (modo Diário do calendário)."""
        with get_session() as session:
            return AppointmentRepository(session).list_by_date_range(target_date, target_date)

    def get_appointments_for_week(self, any_date_in_week: date) -> list[Consulta]:
        """Retorna as consultas da semana (segunda a domingo) que contém a data dada."""
        start_of_week = any_date_in_week - timedelta(days=any_date_in_week.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        with get_session() as session:
            return AppointmentRepository(session).list_by_date_range(start_of_week, end_of_week)

    def get_appointments_for_month(self, any_date_in_month: date) -> list[Consulta]:
        """Retorna as consultas do mês (1º dia ao último dia) que contém a data dada."""
        start_of_month = any_date_in_month.replace(day=1)
        if start_of_month.month == 12:
            end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = start_of_month.replace(month=start_of_month.month + 1, day=1) - timedelta(days=1)

        with get_session() as session:
            return AppointmentRepository(session).list_by_date_range(start_of_month, end_of_month)
