"""Leitura local de modelos clínicos em Word e PDF.

O módulo não usa IA nem envia documentos para serviços externos. Ele transforma
o conteúdo do arquivo em campos que o construtor de fichas do Prontu já entende.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MARCADO_CHECKBOX = re.compile(r"(?:\(\s*[xX]?\s*\)|\[\s*[xX]?\s*\]|☐|☑|□|■|○)")
LINHA_AJUDA = re.compile(
    r"^(?:ex(?:emplo)?\.?|orienta(?:ção|cao)|ajuda|instru(?:ção|cao)|preencha|descreva|informe)\s*[:\-]",
    re.IGNORECASE,
)

PALAVRAS_TEXTO_LONGO = (
    "queixa", "qp", "hda", "conduta", "antecedente", "historico", "historia",
    "medicamento", "observacao", "evolucao", "anamnese", "avaliacao", "exame fisico",
    "prescricao", "orientacao", "diagnostico", "plano terapeutico", "descricao",
)
PALAVRAS_DATA = (
    "data", "nascimento", "validade", "retorno", "atendimento", "admissao",
)
UNIDADES_NUMERICAS = {
    "peso": "kg",
    "altura": "cm",
    "temperatura": "°C",
    "glicemia": "mg/dL",
    "frequencia cardiaca": "bpm",
    "idade": "anos",
}
ROTULOS_CURTOS_CONHECIDOS = (
    "nome", "telefone", "celular", "email", "cpf", "rg", "sexo", "genero",
    "profissao", "ocupacao", "convenio", "plano", "endereco", "cidade", "estado",
    "naturalidade", "nacionalidade", "alergia", "tipo sanguineo",
)


@dataclass(frozen=True)
class BlocoDocumento:
    texto: str
    origem: str = "paragrafo"
    estilo: str = ""
    nivel_titulo: int = 0
    negrito: bool = False
    pagina: int | None = None


def _texto_visivel(valor: object) -> str:
    texto = unicodedata.normalize("NFKC", str(valor or ""))
    texto = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]", "", texto)
    texto = texto.replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", texto).strip()


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _chave(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _sem_acento(texto).lower()).strip("_")


def _contem_termo(chave: str, termo: str) -> bool:
    termo_normalizado = _chave(termo)
    return bool(re.search(rf"(?:^|_){re.escape(termo_normalizado)}(?:s|es)?(?:_|$)", chave))


def _limpar_rotulo(texto: str) -> str:
    texto = MARCADO_CHECKBOX.sub("", texto)
    texto = re.sub(r"^[•·▪◦\-–—]+\s*", "", texto)
    texto = re.sub(r"(?:\s*[:\-–—]\s*|\s*[_.]{3,}\s*)$", "", texto)
    return texto.strip(" \t:;,.–—-_")


def _parece_secao(bloco: BlocoDocumento, texto: str) -> bool:
    if bloco.nivel_titulo > 0 or bloco.estilo.lower().startswith(("heading", "título", "titulo")):
        return True
    if ":" in texto or "?" in texto or MARCADO_CHECKBOX.search(texto):
        return False
    chave = _chave(texto)
    if chave in {"qp", "hda", "pa", "fc"}:
        return False
    palavras = texto.split()
    return (
        1 < len(palavras) <= 10
        and len(texto) <= 90
        and any(c.isalpha() for c in texto)
        and texto == texto.upper()
    )


def _opcoes_marcadas(texto: str) -> tuple[str, list[str]]:
    marcadores = list(MARCADO_CHECKBOX.finditer(texto))
    if not marcadores:
        return "", []
    prefixo = texto[: marcadores[0].start()].strip(" :;-")
    opcoes: list[str] = []
    for indice, marcador in enumerate(marcadores):
        fim = marcadores[indice + 1].start() if indice + 1 < len(marcadores) else len(texto)
        opcao = _limpar_rotulo(texto[marcador.end():fim])
        if opcao:
            opcoes.append(opcao)
    return prefixo, opcoes


def _opcoes_separadas(texto: str) -> tuple[str, list[str]]:
    if ":" not in texto:
        return "", []
    rotulo, valor = texto.split(":", 1)
    if "|" in valor:
        partes = valor.split("|")
    elif re.search(r"\s+/\s+", valor):
        partes = re.split(r"\s+/\s+", valor)
    else:
        return "", []
    opcoes = [_limpar_rotulo(parte) for parte in partes]
    opcoes = [opcao for opcao in opcoes if 0 < len(opcao) <= 45]
    return (_limpar_rotulo(rotulo), opcoes) if 2 <= len(opcoes) <= 8 else ("", [])


def _tipo_campo(rotulo: str) -> tuple[str, dict]:
    chave = _chave(rotulo)
    if any(_contem_termo(chave, palavra) for palavra in PALAVRAS_DATA):
        return "data", {}
    for palavra, unidade in UNIDADES_NUMERICAS.items():
        if _contem_termo(chave, palavra):
            return "numero", {"unidade": unidade}
    if any(_contem_termo(chave, palavra) for palavra in PALAVRAS_TEXTO_LONGO):
        return "texto_longo", {}
    return "texto_curto", {}


def _novo_campo(tipo: str, rotulo: str, extras: dict | None = None) -> dict:
    campo = {"tipo": tipo, "label": rotulo}
    if tipo != "secao":
        campo["id"] = _chave(rotulo) or "campo"
    if extras:
        campo.update(extras)
    return campo


def interpretar_blocos(blocos: Iterable[BlocoDocumento | dict | str]) -> list[dict]:
    """Converte blocos de um documento na estrutura usada pelo construtor."""
    normalizados: list[BlocoDocumento] = []
    for bloco in blocos:
        if isinstance(bloco, BlocoDocumento):
            atual = bloco
        elif isinstance(bloco, dict):
            atual = BlocoDocumento(**{k: v for k, v in bloco.items() if k in BlocoDocumento.__dataclass_fields__})
        else:
            atual = BlocoDocumento(str(bloco))
        texto = _texto_visivel(atual.texto)
        if texto:
            normalizados.append(BlocoDocumento(
                texto=texto,
                origem=atual.origem,
                estilo=atual.estilo,
                nivel_titulo=atual.nivel_titulo,
                negrito=atual.negrito,
                pagina=atual.pagina,
            ))

    campos: list[dict] = []
    rotulos_vistos: set[tuple[str, str]] = set()

    def adicionar(campo: dict) -> dict | None:
        rotulo = _limpar_rotulo(campo.get("label", ""))
        if len(rotulo) < 2 or len(rotulo) > 120:
            return None
        campo["label"] = rotulo
        assinatura = (campo["tipo"], _chave(rotulo))
        if assinatura in rotulos_vistos:
            return None
        rotulos_vistos.add(assinatura)
        if campo["tipo"] != "secao":
            base = _chave(rotulo) or "campo"
            ids = {item.get("id") for item in campos}
            identificador = base
            sufixo = 2
            while identificador in ids:
                identificador = f"{base}_{sufixo}"
                sufixo += 1
            campo["id"] = identificador
        campos.append(campo)
        return campo

    indice = 0
    while indice < len(normalizados):
        bloco = normalizados[indice]
        texto = bloco.texto

        if LINHA_AJUDA.match(texto):
            if campos and campos[-1]["tipo"] in ("texto_curto", "texto_longo"):
                campos[-1]["placeholder"] = texto
            indice += 1
            continue

        prefixo, opcoes = _opcoes_marcadas(texto)
        if MARCADO_CHECKBOX.search(texto) and prefixo and not opcoes:
            adicionar(_novo_campo("checkbox", prefixo, {"texto_checkbox": prefixo}))
            indice += 1
            continue
        if opcoes:
            if prefixo:
                tipo = "multipla_escolha" if len(opcoes) >= 2 else "checkbox"
                extras = {"opcoes": opcoes} if len(opcoes) >= 2 else {"texto_checkbox": opcoes[0]}
                adicionar(_novo_campo(tipo, prefixo, extras))
            elif not prefixo:
                # Formulários costumam colocar uma alternativa marcada por linha.
                proximo = indice + 1
                todas_opcoes = list(opcoes)
                while proximo < len(normalizados):
                    proximo_prefixo, proximas_opcoes = _opcoes_marcadas(normalizados[proximo].texto)
                    if proximo_prefixo or not proximas_opcoes:
                        break
                    todas_opcoes.extend(proximas_opcoes)
                    proximo += 1
                if campos and campos[-1]["tipo"] not in ("secao", "multipla_escolha"):
                    anterior = campos[-1]
                    anterior["tipo"] = "multipla_escolha" if len(todas_opcoes) >= 2 else "checkbox"
                    if len(todas_opcoes) >= 2:
                        anterior["opcoes"] = todas_opcoes
                        anterior.pop("placeholder", None)
                    else:
                        anterior["texto_checkbox"] = todas_opcoes[0]
                elif len(todas_opcoes) == 1:
                    adicionar(_novo_campo(
                        "checkbox",
                        todas_opcoes[0],
                        {"texto_checkbox": todas_opcoes[0]},
                    ))
                indice = proximo
                continue
            indice += 1
            continue

        rotulo_opcoes, opcoes = _opcoes_separadas(texto)
        if opcoes:
            adicionar(_novo_campo("multipla_escolha", rotulo_opcoes, {"opcoes": opcoes}))
            indice += 1
            continue

        if _parece_secao(bloco, texto):
            adicionar(_novo_campo("secao", texto))
            indice += 1
            continue

        encontrado = re.match(
            r"^(.{2,100}?)(?:\s*:\s*(.*)$|\s+[-–—]\s*(.*)$|\s*[_.]{3,}\s*$)",
            texto,
        )
        rotulo = ""
        complemento = ""
        if encontrado:
            rotulo = _limpar_rotulo(encontrado.group(1))
            complemento = _texto_visivel(encontrado.group(2) or encontrado.group(3) or "")
        else:
            chave = _chave(texto)
            conhecido = any(
                _contem_termo(chave, item)
                for item in PALAVRAS_TEXTO_LONGO + ROTULOS_CURTOS_CONHECIDOS
            )
            tabela = bloco.origem.startswith("tabela")
            pergunta = texto.endswith("?")
            if len(texto) <= 80 and (conhecido or tabela or pergunta):
                rotulo = _limpar_rotulo(texto)

        if rotulo:
            tipo, extras = _tipo_campo(rotulo)
            if complemento and len(complemento) <= 70:
                if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", complemento):
                    tipo = "data"
                elif tipo in ("texto_curto", "texto_longo"):
                    extras["placeholder"] = f"Exemplo: {complemento}"
            adicionar(_novo_campo(tipo, rotulo, extras))
        indice += 1

    return campos


def extrair_blocos_docx(caminho: str | Path) -> list[BlocoDocumento]:
    """Extrai parágrafos e tabelas de um DOCX preservando a ordem visual."""
    from docx import Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    documento = Document(str(caminho))
    blocos: list[BlocoDocumento] = []
    for elemento in documento.element.body.iterchildren():
        if isinstance(elemento, CT_P):
            paragrafo = Paragraph(elemento, documento)
            texto = _texto_visivel(paragrafo.text)
            if not texto:
                continue
            estilo = getattr(getattr(paragrafo, "style", None), "name", "") or ""
            titulo = re.search(r"(?:heading|t[íi]tulo)\s*(\d+)", estilo, re.IGNORECASE)
            runs_texto = [run for run in paragrafo.runs if _texto_visivel(run.text)]
            negrito = bool(runs_texto) and all(bool(run.bold) for run in runs_texto)
            blocos.append(BlocoDocumento(
                texto=texto,
                estilo=estilo,
                nivel_titulo=int(titulo.group(1)) if titulo else 0,
                negrito=negrito,
            ))
        elif isinstance(elemento, CT_Tbl):
            tabela = Table(elemento, documento)
            for numero_linha, linha in enumerate(tabela.rows, start=1):
                for numero_coluna, celula in enumerate(linha.cells, start=1):
                    for sublinha in celula.text.splitlines():
                        texto = _texto_visivel(sublinha)
                        if texto:
                            blocos.append(BlocoDocumento(
                                texto=texto,
                                origem=f"tabela:{numero_linha}:{numero_coluna}",
                            ))
    return blocos


def extrair_blocos_pdf(caminho: str | Path) -> list[BlocoDocumento]:
    """Extrai texto selecionável de PDF, mantendo páginas e colunas simples."""
    from pypdf import PdfReader

    blocos: list[BlocoDocumento] = []
    leitor = PdfReader(str(caminho))
    for numero_pagina, pagina in enumerate(leitor.pages, start=1):
        try:
            texto_pagina = pagina.extract_text(extraction_mode="layout") or ""
        except (TypeError, ValueError):
            texto_pagina = pagina.extract_text() or ""
        for linha in texto_pagina.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            # Três ou mais espaços normalmente representam colunas de formulário.
            partes = re.split(r"\s{3,}", linha)
            for parte in partes:
                texto = _texto_visivel(parte)
                if texto:
                    blocos.append(BlocoDocumento(texto=texto, origem="pdf", pagina=numero_pagina))
    return blocos
