"""Regras puras de apresentação e validação de pacientes."""
from __future__ import annotations

import unicodedata
from datetime import datetime


ESTADOS_CIVIS = (
    "Não informado",
    "Solteiro(a)",
    "Casado(a)",
    "União estável",
    "Separado(a)",
    "Divorciado(a)",
    "Viúvo(a)",
    "Outro",
)


def normalizar_texto(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


def somente_numeros(valor, limite: int | None = None) -> str:
    numeros = "".join(c for c in str(valor or "") if c.isdigit())
    return numeros[:limite] if limite else numeros


def formatar_telefone(valor) -> str:
    numeros = somente_numeros(valor, 11)
    if len(numeros) <= 2:
        return numeros
    if len(numeros) <= 6:
        return f"({numeros[:2]}) {numeros[2:]}"
    if len(numeros) <= 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"


def formatar_cpf(valor) -> str:
    numeros = somente_numeros(valor, 11)
    partes = []
    if numeros:
        partes.append(numeros[:3])
    if len(numeros) > 3:
        partes.append(numeros[3:6])
    if len(numeros) > 6:
        partes.append(numeros[6:9])
    formatado = ".".join(partes)
    if len(numeros) > 9:
        formatado += f"-{numeros[9:11]}"
    return formatado


def normalizar_rg(valor) -> str:
    return "".join(
        caractere
        for caractere in str(valor or "").strip().upper()
        if caractere.isalnum()
    )[:14]


def formatar_rg(valor) -> str:
    normalizado = normalizar_rg(valor)
    if not normalizado:
        return ""
    if normalizado.isdigit() and len(normalizado) <= 9:
        if len(normalizado) <= 2:
            return normalizado
        if len(normalizado) <= 5:
            return f"{normalizado[:2]}.{normalizado[2:]}"
        if len(normalizado) <= 8:
            return f"{normalizado[:2]}.{normalizado[2:5]}.{normalizado[5:]}"
        return (
            f"{normalizado[:2]}.{normalizado[2:5]}."
            f"{normalizado[5:8]}-{normalizado[8]}"
        )
    return normalizado


def normalizar_estado_civil(valor) -> str:
    normalizado = normalizar_texto(valor)
    equivalencias = {
        "": "Não informado",
        "nao informado": "Não informado",
        "solteiro": "Solteiro(a)",
        "solteira": "Solteiro(a)",
        "solteiro(a)": "Solteiro(a)",
        "casado": "Casado(a)",
        "casada": "Casado(a)",
        "casado(a)": "Casado(a)",
        "uniao estavel": "União estável",
        "separado": "Separado(a)",
        "separada": "Separado(a)",
        "separado(a)": "Separado(a)",
        "divorciado": "Divorciado(a)",
        "divorciada": "Divorciado(a)",
        "divorciado(a)": "Divorciado(a)",
        "viuvo": "Viúvo(a)",
        "viuva": "Viúvo(a)",
        "viuvo(a)": "Viúvo(a)",
        "outro": "Outro",
    }
    return equivalencias.get(normalizado, "Outro")


def paciente_corresponde_busca(paciente: dict, busca: str) -> bool:
    termo = normalizar_texto(busca)
    if not termo:
        return True
    if normalizar_texto(paciente.get("nome")).startswith(termo):
        return True
    numeros = somente_numeros(termo)
    if not numeros:
        return False
    return any(
        numeros in somente_numeros(paciente.get(campo))
        for campo in ("telefone", "cpf", "rg")
    )


def data_br_para_iso(valor: str) -> str | None:
    valor = str(valor or "").strip()
    if not valor:
        return None
    numeros = somente_numeros(valor, 8)
    candidatos = [valor]
    if len(numeros) == 8:
        candidatos.append(f"{numeros[:2]}/{numeros[2:4]}/{numeros[4:]}")
    for candidato, formato in (
        (candidatos[0], "%d/%m/%Y"),
        (candidatos[-1], "%d/%m/%Y"),
        (valor[:10], "%Y-%m-%d"),
    ):
        try:
            return datetime.strptime(candidato, formato).date().isoformat()
        except ValueError:
            continue
    return None


def data_iso_para_br(valor: str) -> str:
    valor = str(valor or "").strip()
    if not valor:
        return ""
    try:
        return datetime.strptime(valor[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return valor
