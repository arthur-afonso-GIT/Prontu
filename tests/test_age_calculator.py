"""Testes da regra de negócio: idade nunca armazenada, sempre calculada."""

from __future__ import annotations

from datetime import date

import pytest

from utils.age_calculator import calculate_age, format_age_label


class TestCalculateAge:
    def test_idade_exata_no_aniversario(self):
        nascimento = date(1990, 6, 29)
        referencia = date(2026, 6, 29)
        assert calculate_age(nascimento, referencia) == 36

    def test_idade_um_dia_antes_do_aniversario(self):
        nascimento = date(1990, 6, 29)
        referencia = date(2026, 6, 28)
        assert calculate_age(nascimento, referencia) == 35

    def test_idade_um_dia_apos_aniversario(self):
        nascimento = date(1990, 6, 29)
        referencia = date(2026, 6, 30)
        assert calculate_age(nascimento, referencia) == 36

    def test_recem_nascido_tem_idade_zero(self):
        nascimento = date(2026, 6, 29)
        referencia = date(2026, 6, 29)
        assert calculate_age(nascimento, referencia) == 0

    def test_data_futura_levanta_erro(self):
        nascimento = date(2030, 1, 1)
        referencia = date(2026, 6, 29)
        with pytest.raises(ValueError):
            calculate_age(nascimento, referencia)

    def test_ano_bissexto_29_fevereiro(self):
        nascimento = date(2000, 2, 29)
        referencia = date(2026, 3, 1)
        assert calculate_age(nascimento, referencia) == 26


class TestFormatAgeLabel:
    def test_plural_para_mais_de_um_ano(self):
        nascimento = date(1990, 1, 1)
        referencia = date(2026, 1, 1)
        assert format_age_label(nascimento, referencia) == "36 anos"

    def test_singular_para_um_ano(self):
        nascimento = date(2025, 1, 1)
        referencia = date(2026, 1, 1)
        assert format_age_label(nascimento, referencia) == "1 ano"
