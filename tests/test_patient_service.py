"""Testes do PatientService: validação, criação, atualização e exclusão de pacientes."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from database.models import SexoEnum
from services.patient_service import PatientService, PatientServiceError


def _dados_paciente_validos(**overrides) -> dict:
    base = {
        "nome": "Maria Silva",
        "endereco": None,
        "cidade": "Recife",
        "telefone": "81998765432",
        "data_nascimento": date(1985, 5, 20),
        "sexo": SexoEnum.FEMININO,
        "convenio": "Unimed",
        "pasta_id": None,
        "qp": None,
        "hda": None,
        "antecedentes": None,
        "exame_fisico": None,
        "observacoes": None,
    }
    base.update(overrides)
    return base


class TestCreatePatient:
    def test_cria_paciente_com_dados_validos(self):
        service = PatientService()
        paciente_id = service.create_patient(_dados_paciente_validos())
        assert paciente_id is not None

        paciente = service.get_patient(paciente_id)
        assert paciente.nome == "Maria Silva"
        assert paciente.idade >= 0  # idade é derivada, nunca armazenada diretamente

    def test_nome_vazio_levanta_erro(self):
        service = PatientService()
        with pytest.raises(PatientServiceError):
            service.create_patient(_dados_paciente_validos(nome=""))

    def test_data_nascimento_futura_levanta_erro(self):
        service = PatientService()
        data_futura = date.today() + timedelta(days=10)
        with pytest.raises(PatientServiceError):
            service.create_patient(_dados_paciente_validos(data_nascimento=data_futura))

    def test_telefone_incompleto_levanta_erro(self):
        service = PatientService()
        with pytest.raises(PatientServiceError):
            service.create_patient(_dados_paciente_validos(telefone="123"))

    def test_telefone_none_e_aceito(self):
        service = PatientService()
        paciente_id = service.create_patient(_dados_paciente_validos(telefone=None))
        assert paciente_id is not None


class TestUpdatePatient:
    def test_atualiza_paciente_existente(self):
        service = PatientService()
        paciente_id = service.create_patient(_dados_paciente_validos())

        service.update_patient(paciente_id, _dados_paciente_validos(nome="Maria Souza"))

        paciente = service.get_patient(paciente_id)
        assert paciente.nome == "Maria Souza"

    def test_atualizar_paciente_inexistente_levanta_erro(self):
        service = PatientService()
        with pytest.raises(PatientServiceError):
            service.update_patient(99999, _dados_paciente_validos())


class TestDeletePatient:
    def test_exclui_paciente_existente(self):
        service = PatientService()
        paciente_id = service.create_patient(_dados_paciente_validos())

        service.delete_patient(paciente_id)

        assert service.get_patient(paciente_id) is None

    def test_excluir_paciente_inexistente_levanta_erro(self):
        service = PatientService()
        with pytest.raises(PatientServiceError):
            service.delete_patient(99999)


class TestSearchPatients:
    def test_busca_por_nome(self):
        service = PatientService()
        service.create_patient(_dados_paciente_validos(nome="Ana Paula"))
        service.create_patient(_dados_paciente_validos(nome="Carlos Souza"))

        resultados, total = service.search_patients(texto="Ana")
        assert total == 1
        assert resultados[0].nome == "Ana Paula"

    def test_busca_sem_filtro_retorna_todos(self):
        service = PatientService()
        service.create_patient(_dados_paciente_validos(nome="Paciente 1"))
        service.create_patient(_dados_paciente_validos(nome="Paciente 2"))

        resultados, total = service.search_patients()
        assert total == 2

    def test_paginacao_limita_resultados(self):
        service = PatientService()
        for i in range(5):
            service.create_patient(_dados_paciente_validos(nome=f"Paciente {i}"))

        resultados, total = service.search_patients(page=1, page_size=2)
        assert total == 5
        assert len(resultados) == 2
