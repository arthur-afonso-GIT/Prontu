"""
Cálculo de idade a partir de data de nascimento.

Regra de negócio crítica do projeto: a idade NUNCA é armazenada no banco
de dados. Ela é sempre derivada da `data_nascimento` no momento em que é
exibida, evitando dados desatualizados (um paciente cadastrado há 3 anos
não pode continuar mostrando a idade que tinha no dia do cadastro).
"""

from __future__ import annotations

from datetime import date


def calculate_age(birth_date: date, reference_date: date | None = None) -> int:
    """Calcula a idade em anos completos.

    Args:
        birth_date: Data de nascimento do paciente.
        reference_date: Data de referência para o cálculo. Se omitida,
            usa a data atual do sistema. Parametrizável principalmente
            para permitir testes determinísticos.

    Returns:
        Idade em anos completos (inteiro, sempre >= 0).

    Raises:
        ValueError: Se `birth_date` estiver no futuro em relação à
            `reference_date`.
    """
    if reference_date is None:
        reference_date = date.today()

    if birth_date > reference_date:
        raise ValueError("Data de nascimento não pode ser no futuro.")

    age = reference_date.year - birth_date.year
    # Ajusta caso o aniversário deste ano ainda não tenha ocorrido.
    has_not_had_birthday_yet = (reference_date.month, reference_date.day) < (
        birth_date.month,
        birth_date.day,
    )
    if has_not_had_birthday_yet:
        age -= 1

    return age


def format_age_label(birth_date: date, reference_date: date | None = None) -> str:
    """Formata a idade para exibição amigável na UI (ex: "34 anos")."""
    age = calculate_age(birth_date, reference_date)
    return f"{age} ano" if age == 1 else f"{age} anos"
