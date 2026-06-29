"""
Service Layer de Pacientes.

A camada de serviço é o único lugar onde regras de negócio relacionadas
a pacientes são aplicadas. Controllers/ViewModels chamam métodos daqui;
nunca acessam repositórios ou sessões de banco diretamente. Isso garante
que a mesma regra (ex: validação de telefone, normalização de dados)
seja aplicada de forma consistente independentemente de qual tela da UI
disparou a ação.
"""

from __future__ import annotations

from pydantic import ValidationError

from database.database import get_session
from database.models import Paciente
from database.repositories.appointment_repository import AppointmentRepository
from database.repositories.formulario_repository import RespostaFormularioRepository
from database.repositories.patient_repository import PatientRepository
from forms.patient_schemas import PacienteCreateSchema, PacienteUpdateSchema
from utils.logger import get_logger

logger = get_logger(__name__)


class PatientServiceError(Exception):
    """Erro de negócio ao manipular pacientes (ex: validação, conflito)."""
    pass


class PatientService:
    """Orquestra operações de negócio relacionadas a pacientes."""

    def create_patient(self, data: dict) -> int:
        """Valida e persiste um novo paciente.

        Args:
            data: Dicionário com os campos brutos vindos da UI.

        Returns:
            O ID do paciente recém-criado.

        Raises:
            PatientServiceError: Se a validação dos dados falhar.
        """
        try:
            validated = PacienteCreateSchema(**data)
        except ValidationError as exc:
            logger.warning("Falha de validação ao criar paciente: %s", exc)
            raise PatientServiceError(self._format_validation_error(exc)) from exc

        with get_session() as session:
            repo = PatientRepository(session)
            paciente = Paciente(**validated.model_dump())
            repo.add(paciente)
            logger.info("Paciente criado: id=%s nome=%s", paciente.id, paciente.nome)
            return paciente.id

    def update_patient(self, paciente_id: int, data: dict) -> None:
        """Valida e atualiza um paciente existente.

        Raises:
            PatientServiceError: Se a validação falhar ou o paciente não existir.
        """
        try:
            validated = PacienteUpdateSchema(**data)
        except ValidationError as exc:
            logger.warning("Falha de validação ao atualizar paciente: %s", exc)
            raise PatientServiceError(self._format_validation_error(exc)) from exc

        with get_session() as session:
            repo = PatientRepository(session)
            paciente = repo.get_by_id(paciente_id)
            if paciente is None:
                raise PatientServiceError(f"Paciente com id={paciente_id} não encontrado.")

            for field, value in validated.model_dump().items():
                setattr(paciente, field, value)

            logger.info("Paciente atualizado: id=%s", paciente_id)

    def delete_patient(self, paciente_id: int) -> None:
        """Remove um paciente e todos os seus dados associados (cascade)."""
        with get_session() as session:
            repo = PatientRepository(session)
            paciente = repo.get_by_id(paciente_id)
            if paciente is None:
                raise PatientServiceError(f"Paciente com id={paciente_id} não encontrado.")
            repo.delete(paciente)
            logger.info("Paciente removido: id=%s", paciente_id)

    def get_patient(self, paciente_id: int) -> Paciente | None:
        """Retorna o paciente completo (com relacionamentos) ou None."""
        with get_session() as session:
            repo = PatientRepository(session)
            paciente = repo.get_by_id(paciente_id)
            if paciente:
                session.refresh(paciente)
            return paciente

    def search_patients(
        self,
        texto: str | None = None,
        cidade: str | None = None,
        convenio: str | None = None,
        pasta_id: int | None = None,
        order_by: str = "nome",
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Paciente], int]:
        """Busca paginada e filtrada de pacientes (delega ao repositório)."""
        with get_session() as session:
            repo = PatientRepository(session)
            return repo.search(
                texto=texto,
                cidade=cidade,
                convenio=convenio,
                pasta_id=pasta_id,
                order_by=order_by,
                page=page,
                page_size=page_size,
            )

    def list_recent_patients(self, limit: int = 10) -> list[Paciente]:
        """Lista os pacientes mais recentes, para exibição na Home."""
        with get_session() as session:
            repo = PatientRepository(session)
            return repo.list_recent(limit=limit)

    def list_distinct_cidades(self) -> list[str]:
        with get_session() as session:
            return PatientRepository(session).list_distinct_cidades()

    def list_distinct_convenios(self) -> list[str]:
        with get_session() as session:
            return PatientRepository(session).list_distinct_convenios()

    def get_patient_appointment_history(self, paciente_id: int):
        """Retorna o histórico de consultas de um paciente."""
        with get_session() as session:
            return AppointmentRepository(session).list_by_patient(paciente_id)

    def get_patient_form_history(self, paciente_id: int):
        """Retorna o histórico de fichas dinâmicas respondidas por um paciente."""
        with get_session() as session:
            return RespostaFormularioRepository(session).list_by_patient(paciente_id)

    @staticmethod
    def _format_validation_error(exc: ValidationError) -> str:
        """Converte erros do Pydantic em uma mensagem legível para o usuário."""
        mensagens = []
        for error in exc.errors():
            campo = error["loc"][0] if error["loc"] else "campo"
            mensagens.append(f"{campo}: {error['msg']}")
        return " | ".join(mensagens)
