"""Testes do AppointmentService: agendamento e detecção de conflitos de horário."""

from __future__ import annotations

from datetime import date

import pytest

from database.models import SexoEnum
from services.appointment_service import AppointmentService, AppointmentServiceError
from services.patient_service import PatientService


def _criar_paciente_de_teste() -> int:
    service = PatientService()
    return service.create_patient({
        "nome": "Paciente Teste",
        "endereco": None, "cidade": None, "telefone": None,
        "data_nascimento": date(1990, 1, 1),
        "sexo": SexoEnum.OUTRO,
        "convenio": None, "pasta_id": None,
        "qp": None, "hda": None, "antecedentes": None,
        "exame_fisico": None, "observacoes": None,
    })


class TestCreateAppointment:
    def test_cria_consulta_sem_conflito(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()

        consulta_id = service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 30)
        assert consulta_id is not None

    def test_detecta_conflito_de_horario_exato(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()

        service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 30)

        with pytest.raises(AppointmentServiceError):
            service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 30)

    def test_detecta_conflito_de_horario_sobreposto(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()

        service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 60)

        # Consulta às 09:30 com duração de 30 min termina às 10:00,
        # mas a consulta existente (09:00-10:00) já ocupa esse intervalo.
        with pytest.raises(AppointmentServiceError):
            service.create_appointment(paciente_id, date(2026, 7, 1), "09:30", 30)

    def test_horarios_adjacentes_nao_conflitam(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()

        service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 30)
        # 09:30 começa exatamente quando a anterior termina (09:00 + 30min) — não deve conflitar.
        consulta_id = service.create_appointment(paciente_id, date(2026, 7, 1), "09:30", 30)
        assert consulta_id is not None

    def test_forcar_apesar_de_conflito_permite_sobreposicao(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()

        service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 30)
        consulta_id = service.create_appointment(
            paciente_id, date(2026, 7, 1), "09:00", 30, forcar_apesar_de_conflito=True
        )
        assert consulta_id is not None


class TestGetAppointmentsForPeriod:
    def test_consultas_do_dia(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()
        service.create_appointment(paciente_id, date(2026, 7, 1), "09:00", 30)
        service.create_appointment(paciente_id, date(2026, 7, 2), "09:00", 30)

        consultas = service.get_appointments_for_day(date(2026, 7, 1))
        assert len(consultas) == 1

    def test_consultas_da_semana(self):
        paciente_id = _criar_paciente_de_teste()
        service = AppointmentService()
        # Segunda-feira de referência.
        service.create_appointment(paciente_id, date(2026, 6, 29), "09:00", 30)
        service.create_appointment(paciente_id, date(2026, 7, 6), "09:00", 30)  # semana seguinte

        consultas = service.get_appointments_for_week(date(2026, 6, 29))
        assert len(consultas) == 1
