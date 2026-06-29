"""Testes da regra de negócio: geração de link do WhatsApp a partir de telefone."""

from __future__ import annotations

from utils.phone_utils import build_whatsapp_link, clean_phone_digits, format_phone_display


class TestCleanPhoneDigits:
    def test_remove_formatacao_completa(self):
        assert clean_phone_digits("(81) 99876-5432") == "81998765432"

    def test_string_vazia(self):
        assert clean_phone_digits("") == ""

    def test_none_nao_quebra(self):
        assert clean_phone_digits(None) == ""


class TestFormatPhoneDisplay:
    def test_celular_com_ddd(self):
        assert format_phone_display("81998765432") == "(81) 99876-5432"

    def test_fixo_com_ddd(self):
        assert format_phone_display("8134561234") == "(81) 3456-1234"

    def test_numero_incompleto_retorna_sem_mascara(self):
        assert format_phone_display("123") == "123"


class TestBuildWhatsappLink:
    def test_gera_link_correto_para_celular(self):
        link = build_whatsapp_link("(81) 99876-5432")
        assert link == "https://wa.me/5581998765432"

    def test_remove_codigo_pais_duplicado(self):
        link = build_whatsapp_link("5581998765432")
        assert link == "https://wa.me/5581998765432"

    def test_numero_invalido_retorna_none(self):
        assert build_whatsapp_link("123") is None

    def test_string_vazia_retorna_none(self):
        assert build_whatsapp_link("") is None
