"""Regras puras usadas pela tela QML de Configurações."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


MENSAGEM_WHATSAPP_MANUAL_PADRAO = (
    "Olá, {paciente}! Tudo bem? Aqui é {profissional}, da clínica. "
    "Como podemos ajudar?"
)
MENSAGEM_LEMBRETE_CONSULTA_PADRAO = (
    "Olá, {paciente}! Lembramos que sua consulta está marcada para {data} "
    "às {hora}. Procedimento: {procedimento}. "
    "Por favor, confirme sua presença."
)


def montar_url_whatsapp_manual(
    telefone: object,
    paciente: object,
    profissional: object,
    modelo: object = None,
) -> str:
    """Monta o link do WhatsApp usado pelo botão manual do cadastro."""
    numero = "".join(caractere for caractere in str(telefone or "") if caractere.isdigit())
    if len(numero) < 10:
        return ""
    if len(numero) <= 11:
        numero = "55" + numero

    mensagem = str(modelo or MENSAGEM_WHATSAPP_MANUAL_PADRAO)
    mensagem = mensagem.replace("{paciente}", str(paciente or "").strip())
    mensagem = mensagem.replace(
        "{profissional}",
        str(profissional or "").strip() or "a equipe da clínica",
    )
    return (
        f"https://web.whatsapp.com/send?phone={numero}"
        f"&text={quote(mensagem)}"
    )

CHAVES_CONFIGURACAO = [
    "whatsapp_mensagem_manual",
    "whatsapp_mensagem_lembrete",
    "backup_dir",
    "backup_freq",
    "backup_retencao",
    "backup_include_attachments",
    "backup_last_success",
    "backup_last_path",
    "backup_last_size",
    "backup_last_error",
]


def pasta_backup_padrao() -> str:
    return str(Path.home() / "Documents" / "Prontu Backups")


def validar_senhas_backup(senha: str, confirmacao: str) -> str:
    if not senha or not confirmacao:
        return "Informe e confirme a senha de recuperação."
    if senha != confirmacao:
        return "A senha e a confirmação não coincidem."
    return ""


def preparar_configuracoes(
    resumo_assinatura: dict | None,
    nome: str,
    valores: dict | None,
) -> dict:
    valores = valores if isinstance(valores, dict) else {}
    assinatura = resumo_assinatura if isinstance(resumo_assinatura, dict) else {}
    plano = str(assinatura.get("plano") or "solo").lower()
    status = str(assinatura.get("status") or "ativa").lower()
    nomes_planos = {
        "solo": "Prontu Solo",
        "equipe": "Prontu Equipe",
        "personalizado": "Prontu Personalizado",
    }
    nomes_status = {
        "ativa": "Assinatura ativa",
        "teste": "Período de teste",
        "suspensa": "Assinatura suspensa",
        "cancelada": "Assinatura cancelada",
    }
    limite = int(assinatura.get("max_usuarios") or 1)
    ultimo = str(valores.get("backup_last_success") or "")
    erro = str(valores.get("backup_last_error") or "")
    caminho = str(valores.get("backup_last_path") or "")
    try:
        tamanho = int(valores.get("backup_last_size") or 0) // 1024
    except (TypeError, ValueError):
        tamanho = 0
    if ultimo:
        backup_status = (
            f"Último backup: {ultimo}\nDestino: {caminho} ({tamanho} KB)"
        )
    elif erro:
        backup_status = f"Erro no último backup: {erro[:120]}"
    else:
        backup_status = "Último backup: nunca executado"
    return {
        "nome": str(nome or ""),
        "plano": nomes_planos.get(plano, "Prontu Solo"),
        "status": nomes_status.get(status, "Status não informado"),
        "status_codigo": status,
        "limite": "1 usuário" if plano == "solo" else f"Até {limite} usuários",
        "mensagem_manual": (
            valores.get("whatsapp_mensagem_manual")
            or MENSAGEM_WHATSAPP_MANUAL_PADRAO
        ),
        "mensagem_lembrete": (
            valores.get("whatsapp_mensagem_lembrete")
            or MENSAGEM_LEMBRETE_CONSULTA_PADRAO
        ),
        "backup_dir": (
            valores.get("backup_dir") or pasta_backup_padrao()
        ),
        "backup_freq": valores.get("backup_freq") or "manual",
        "backup_retencao": max(
            1, _inteiro(valores.get("backup_retencao"), 30)
        ),
        "backup_anexos": (
            str(valores.get("backup_include_attachments") or "0") == "1"
        ),
        "backup_status": backup_status,
    }


def _inteiro(valor, padrao: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


NOMES_ACAO = {
    "INSERT": "Criado",
    "UPDATE": "Atualizado",
    "DELETE": "Excluído",
    "BACKUP_CREATED": "Backup concluído",
    "EXPORT": "Documento exportado",
}
NOMES_ENTIDADE = {
    "pacientes": "Pacientes",
    "agenda": "Agenda",
    "fichas_preenchidas": "Fichas clínicas",
    "modelos_fichas": "Modelos de ficha",
    "pastas": "Pastas",
    "configuracoes": "Configurações",
    "pagamentos_consultas": "Financeiro",
    "retornos_pacientes": "Retornos",
    "backup": "Backup",
}
NOMES_CAMPOS = {
    "nome": "Nome",
    "convenio": "Convênio",
    "pasta": "Pasta",
    "sexo": "Sexo",
    "status": "Status",
    "procedimento": "Procedimento",
    "data": "Data",
    "horario": "Horário",
    "duracao_txt": "Duração",
    "deleted_at": "Arquivamento",
    "status_pagamento": "Status do pagamento",
    "valor": "Valor da consulta",
    "valor_recebido": "Valor recebido",
    "forma_pagamento": "Forma de pagamento",
    "data_prevista": "Data prevista do retorno",
}
CAMPOS_PRIVADOS = {
    "id", "consultorio_id", "auth_user_id", "created_at", "updated_at",
    "criado_em", "dados_respostas", "anexos", "queixa", "queixa_principal",
    "endereco", "telefone", "nascimento", "cpf", "rg", "observacao",
    "valor_anterior", "valor_novo",
}


def _dicionario(valor) -> dict:
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        try:
            resultado = json.loads(valor)
            return resultado if isinstance(resultado, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def resumir_evento(evento: dict) -> str:
    acao = str(evento.get("acao") or "")
    entidade = str(evento.get("entidade") or "")
    contexto = _dicionario(evento.get("contexto"))
    if entidade == "pagamentos_consultas" and contexto.get("status_pagamento"):
        return f"Status do pagamento: {contexto['status_pagamento']}"
    if acao == "INSERT":
        return "Novo registro adicionado"
    if acao == "DELETE":
        return "Registro removido"
    anterior = _dicionario(evento.get("valor_anterior"))
    novo = _dicionario(evento.get("valor_novo"))
    campos = []
    for campo in set(anterior) | set(novo):
        if (
            campo in CAMPOS_PRIVADOS
            or anterior.get(campo) == novo.get(campo)
        ):
            continue
        campos.append(NOMES_CAMPOS.get(
            campo, campo.replace("_", " ").capitalize()
        ))
    if "Arquivamento" in campos:
        return "Registro arquivado"
    if campos:
        return "Alterado: " + ", ".join(sorted(campos)[:4])
    referencia = evento.get("registro_id")
    return (
        f"Registro #{referencia} atualizado"
        if referencia else "Registro atualizado"
    )


def preparar_auditoria(eventos: list[dict]) -> list[dict]:
    preparados = []
    for evento in eventos or []:
        try:
            data = datetime.fromisoformat(
                str(evento.get("criado_em")).replace("Z", "+00:00")
            ).astimezone().strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            data = str(evento.get("criado_em") or "Não informado")
        entidade = str(evento.get("entidade") or "")
        ator_nome = str(evento.get("ator_nome") or "").strip()
        ator_papel_codigo = str(evento.get("ator_papel") or "").strip().lower()
        ator_papel = {
            "proprietario": "Proprietário",
            "profissional": "Profissional",
            "secretaria": "Secretária",
            "sistema": "Sistema",
        }.get(ator_papel_codigo, ator_papel_codigo.title())
        if not ator_nome:
            ator_nome = "Registro anterior à identificação"
        responsavel = (
            f"{ator_nome} · {ator_papel}" if ator_papel else ator_nome
        )
        preparados.append({
            "data": data,
            "acao": NOMES_ACAO.get(
                str(evento.get("acao") or ""),
                str(evento.get("acao") or "Ação registrada"),
            ),
            "area": NOMES_ENTIDADE.get(
                entidade, entidade.replace("_", " ").capitalize()
            ),
            "area_codigo": entidade,
            "resumo": resumir_evento(evento),
            "responsavel": responsavel,
        })
    return preparados
