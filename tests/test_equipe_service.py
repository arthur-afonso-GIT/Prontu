from services.equipe_service import (
    formatar_expiracao,
    papel_texto,
    preparar_equipe,
    validar_convite,
)


def test_papeis_e_data_sao_apresentados_em_portugues():
    assert papel_texto("proprietario") == "Proprietário"
    assert papel_texto("secretaria") == "Secretária"
    assert formatar_expiracao("2026-08-04T12:00:00+00:00") == "04/08/2026"


def test_preparar_equipe_oculta_usuario_tecnico_e_conta_vagas():
    equipe = preparar_equipe({
        "max_usuarios": 5,
        "membros": [
            {
                "id": "device",
                "email": "local@prontu.device",
                "papel": "proprietario",
            },
            {
                "id": "owner",
                "nome": "Arthur",
                "email": "arthur@clinica.com",
                "papel": "proprietario",
            },
        ],
        "convites": [{
            "id": "invite",
            "nome": "Maria",
            "email": "maria@clinica.com",
            "papel": "profissional",
        }],
    })

    assert len(equipe["membros"]) == 1
    assert len(equipe["convites"]) == 1
    assert equipe["usados"] == 2
    assert equipe["disponiveis"] == 3


def test_validacao_de_convite_exige_nome_email_e_papel():
    assert validar_convite("", "maria@clinica.com", "profissional")
    assert validar_convite("Maria", "email-invalido", "profissional")
    assert validar_convite("Maria", "maria@clinica.com", "administrador")
    assert validar_convite("Maria", "maria@clinica.com", "secretaria") == ""
