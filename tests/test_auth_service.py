from services.auth_service import (
    normalizar_email,
    validar_chave,
    validar_convite,
    validar_email,
    validar_login,
    validar_nova_senha,
)


def test_email_e_normalizado_e_validado():
    assert normalizar_email("  Pessoa@Clinica.COM ") == "pessoa@clinica.com"
    assert validar_email("pessoa@clinica.com") is True
    assert validar_email("pessoa-sem-dominio") is False


def test_login_exige_email_e_senha():
    assert validar_login("invalido", "12345678") == "Informe um e-mail válido."
    assert validar_login("pessoa@clinica.com", "") == "Informe sua senha."
    assert validar_login("pessoa@clinica.com", "12345678") == ""


def test_convite_exige_codigo_e_senhas_iguais():
    assert validar_convite("", "pessoa@clinica.com", "12345678", "12345678")
    assert validar_convite(
        "PRONTU-TESTE", "pessoa@clinica.com", "12345678", "diferente"
    ) == "As duas senhas precisam ser iguais."
    assert validar_convite(
        "PRONTU-TESTE", "pessoa@clinica.com", "12345678", "12345678"
    ) == ""


def test_nova_senha_e_chave_tem_validacao_minima():
    assert validar_nova_senha("123", "123") == (
        "A senha deve ter pelo menos 8 caracteres."
    )
    assert validar_chave("") == "Informe a chave de ativação."
    assert validar_chave("PRONTU-TESTE") == ""
