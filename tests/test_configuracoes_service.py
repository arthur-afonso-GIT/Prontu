from services.configuracoes_service import (
    montar_url_whatsapp_manual,
    preparar_auditoria,
    preparar_configuracoes,
    validar_senhas_backup,
)


def test_validacao_exige_duas_senhas_iguais():
    assert validar_senhas_backup("", "") != ""
    assert validar_senhas_backup("segura", "diferente") != ""
    assert validar_senhas_backup("segura", "segura") == ""


def test_link_manual_do_whatsapp_formata_numero_e_mensagem():
    url = montar_url_whatsapp_manual(
        "(81) 99999-8877",
        "Maria Silva",
        "Dra. Laura",
        "Olá, {paciente}! Aqui é {profissional}.",
    )

    assert "phone=5581999998877" in url
    assert "Maria%20Silva" in url
    assert "Dra.%20Laura" in url
    assert montar_url_whatsapp_manual("123", "Maria", "Laura") == ""


def test_configuracoes_preparam_plano_mensagens_e_backup():
    dados = preparar_configuracoes(
        {"plano": "equipe", "status": "ativa", "max_usuarios": 5},
        "Dra. Laura",
        {
            "whatsapp_mensagem_manual": "Olá, {paciente}",
            "backup_retencao": "45",
            "backup_include_attachments": "1",
        },
    )

    assert dados["nome"] == "Dra. Laura"
    assert dados["plano"] == "Prontu Equipe"
    assert dados["limite"] == "Até 5 usuários"
    assert dados["mensagem_manual"] == "Olá, {paciente}"
    assert dados["backup_retencao"] == 45
    assert dados["backup_anexos"] is True


def test_auditoria_resume_mudancas_sem_expor_dados_clinicos():
    resultado = preparar_auditoria([{
        "acao": "UPDATE",
        "entidade": "pacientes",
        "registro_id": 8,
        "criado_em": "2026-07-28T12:30:00+00:00",
        "ator_nome": "Maria Silva",
        "ator_papel": "secretaria",
        "valor_anterior": {"nome": "Ana", "telefone": "111"},
        "valor_novo": {"nome": "Ana Silva", "telefone": "222"},
    }])

    assert resultado[0]["area"] == "Pacientes"
    assert resultado[0]["resumo"] == "Alterado: Nome"
    assert resultado[0]["responsavel"] == "Maria Silva · Secretária"
    assert "111" not in resultado[0]["resumo"]
    assert "222" not in resultado[0]["resumo"]
