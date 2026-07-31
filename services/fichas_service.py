"""Regras puras dos modelos e formulários de fichas clínicas."""
from __future__ import annotations

import html
import re
import unicodedata
from datetime import datetime
from pathlib import Path


NOME_MODELO_PADRAO = "Ficha de Consulta Geral (Padrão)"

MODELO_PADRAO = [
    {"tipo": "secao", "label": "HISTÓRICO DA CONSULTA ATUAL"},
    {
        "tipo": "texto_longo",
        "label": "Queixa Principal (QP)",
        "id": "qp",
    },
    {
        "tipo": "texto_longo",
        "label": "Histórico da Doença Atual (HDA)",
        "id": "hda",
    },
    {"tipo": "secao", "label": "EXAME FÍSICO E SINAIS VITAIS"},
    {
        "tipo": "texto_curto",
        "label": "Pressão Arterial (PA)",
        "id": "pa",
        "placeholder": "Ex.: 120x80 mmHg",
    },
    {
        "tipo": "texto_curto",
        "label": "Frequência Cardíaca (FC)",
        "id": "fc",
        "placeholder": "Ex.: 75 bpm",
    },
    {"tipo": "secao", "label": "CONDUTA MÉDICA"},
    {
        "tipo": "texto_longo",
        "label": "Prescrição / Orientações Passadas",
        "id": "prescricao",
    },
]

TIPOS_SUPORTADOS = {
    "secao",
    "texto_curto",
    "texto_longo",
    "checkbox",
    "numero",
    "data",
    "multipla_escolha",
}


def _slug(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto or "campo"))
    sem_acentos = "".join(
        caractere for caractere in normalizado
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]+", "_", sem_acentos.casefold()).strip("_") or "campo"


def rotulo_legivel(campo: dict) -> str:
    """Remove identificadores antigos que chegaram a aparecer para o usuário."""
    label = " ".join(str(campo.get("label") or "").split())
    campo_id = str(campo.get("id") or "")
    partes = campo_id.split("_")
    if len(partes) >= 3 and partes[0].casefold() == "custom":
        identificador = partes[1]
        if label.casefold().startswith(f"{identificador.casefold()} "):
            label = label[len(identificador):].strip()
    if label:
        return label
    partes_id = [
        parte for parte in partes
        if parte and parte.casefold() != "custom"
        and not re.fullmatch(r"[0-9a-f]{8}", parte, re.IGNORECASE)
    ]
    return " ".join(partes_id).replace("_", " ").strip().capitalize() or "Campo"


def normalizar_estrutura(estrutura) -> list[dict]:
    """Entrega à interface somente campos válidos, estáveis e serializáveis."""
    if not isinstance(estrutura, list):
        return []
    normalizados = []
    ids_usados: set[str] = set()
    for indice, original in enumerate(estrutura):
        if not isinstance(original, dict):
            continue
        tipo = str(original.get("tipo") or "").strip()
        if tipo not in TIPOS_SUPORTADOS:
            continue
        campo = dict(original)
        campo["tipo"] = tipo
        campo["label"] = rotulo_legivel(campo)
        if tipo != "secao":
            campo_id = str(campo.get("id") or "").strip()
            if not campo_id:
                campo_id = f"campo_{indice}_{_slug(campo['label'])}"
            base = campo_id
            contador = 2
            while campo_id in ids_usados:
                campo_id = f"{base}_{contador}"
                contador += 1
            campo["id"] = campo_id
            ids_usados.add(campo_id)
            campo["obrigatorio"] = bool(campo.get("obrigatorio", False))
        if tipo == "multipla_escolha":
            campo["opcoes"] = [
                str(opcao).strip()
                for opcao in campo.get("opcoes", [])
                if str(opcao).strip()
            ]
        normalizados.append(campo)
    return normalizados


def respostas_iniciais(campos: list[dict]) -> dict:
    hoje = datetime.now().strftime("%d/%m/%Y")
    respostas = {}
    for campo in campos:
        campo_id = campo.get("id")
        if not campo_id:
            continue
        if campo.get("tipo") == "checkbox":
            respostas[campo_id] = False
        elif campo.get("tipo") == "data" and campo.get("preencher_hoje"):
            respostas[campo_id] = hoje
        else:
            respostas[campo_id] = ""
    return respostas


def validar_respostas(
    campos: list[dict], respostas: dict
) -> tuple[bool, list[str]]:
    vazios = []
    for campo in campos:
        if campo.get("tipo") == "secao" or not campo.get("obrigatorio"):
            continue
        valor = respostas.get(campo.get("id"))
        if valor is None or valor is False or not str(valor).strip():
            vazios.append(campo.get("label") or "Campo")
    return not vazios, vazios


def preparar_dados_exportacao(
    campos: list[dict],
    respostas: dict,
    paciente: str,
    modelo: str,
    clinica: str = "",
    profissional: str = "",
    data: str | None = None,
) -> dict:
    """Transforma o formulário dinâmico em dados estáveis para Word e PDF."""
    itens = []
    respostas = dict(respostas or {})
    for campo in normalizar_estrutura(campos):
        rotulo = rotulo_legivel(campo)
        if campo.get("tipo") == "secao":
            itens.append({"tipo": "secao", "rotulo": rotulo, "valor": ""})
            continue
        valor = respostas.get(campo.get("id"))
        if campo.get("tipo") == "checkbox":
            valor = "Sim" if bool(valor) else "Não"
        elif isinstance(valor, (list, tuple)):
            valor = ", ".join(str(item) for item in valor if str(item).strip())
        else:
            valor = str(valor or "").strip()
        itens.append({
            "tipo": "campo",
            "rotulo": rotulo,
            "valor": valor or "Não informado",
        })
    return {
        "paciente": str(paciente or "").strip(),
        "modelo": str(modelo or "Ficha Clínica").strip(),
        "clinica": str(clinica or "").strip(),
        "profissional": str(profissional or "").strip(),
        "data": data or datetime.now().strftime("%d/%m/%Y às %H:%M"),
        "itens": itens,
    }


def nome_arquivo_exportacao(dados: dict, extensao: str) -> str:
    nome = unicodedata.normalize("NFKD", str(dados.get("paciente") or "Paciente"))
    nome = "".join(
        caractere for caractere in nome
        if not unicodedata.combining(caractere)
    )
    nome = re.sub(r"[^A-Za-z0-9_-]+", "_", nome).strip("_") or "Paciente"
    extensao = extensao if extensao.startswith(".") else f".{extensao}"
    return f"Ficha_{nome}_{datetime.now().strftime('%Y%m%d_%H%M')}{extensao}"


def exportar_ficha_word(
    dados: dict,
    caminho: str,
    logo_path: str | Path | None = None,
) -> None:
    """Gera um documento Word legível e pronto para impressão."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    documento = Document()
    secao = documento.sections[0]
    secao.top_margin = Inches(0.65)
    secao.bottom_margin = Inches(0.65)

    if logo_path and Path(logo_path).is_file():
        paragrafo_logo = documento.add_paragraph()
        paragrafo_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragrafo_logo.add_run().add_picture(
            str(logo_path), width=Inches(0.62)
        )

    titulo = documento.add_heading(dados.get("modelo") or "Ficha Clínica", 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    documento.add_paragraph(
        f"Paciente: {dados.get('paciente') or 'Não informado'}"
    )
    documento.add_paragraph(f"Data: {dados.get('data') or ''}")
    if dados.get("clinica"):
        documento.add_paragraph(f"Clínica: {dados['clinica']}")
    if dados.get("profissional"):
        documento.add_paragraph(f"Profissional: {dados['profissional']}")

    for item in dados.get("itens") or []:
        if item.get("tipo") == "secao":
            documento.add_heading(item.get("rotulo") or "Seção", level=1)
            continue
        documento.add_heading(item.get("rotulo") or "Campo", level=2)
        documento.add_paragraph(str(item.get("valor") or "Não informado"))

    rodape = documento.add_paragraph("Documento gerado pelo Prontu.")
    rodape.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for execucao in rodape.runs:
        execucao.font.size = Pt(9)
        execucao.font.color.rgb = RGBColor(100, 116, 139)
    documento.save(str(caminho))


def html_exportacao_ficha(dados: dict) -> str:
    """Entrega o conteúdo seguro usado pelo exportador PDF do Qt."""
    blocos = []
    for item in dados.get("itens") or []:
        rotulo = html.escape(str(item.get("rotulo") or ""))
        if item.get("tipo") == "secao":
            blocos.append(f"<h2>{rotulo}</h2>")
            continue
        valor = html.escape(
            str(item.get("valor") or "Não informado")
        ).replace("\n", "<br>")
        blocos.append(f"<section><h3>{rotulo}</h3><p>{valor}</p></section>")
    profissional = (
        f"<p><strong>Profissional:</strong> "
        f"{html.escape(str(dados.get('profissional')))}</p>"
        if dados.get("profissional") else ""
    )
    clinica = (
        f"<p><strong>Clínica:</strong> "
        f"{html.escape(str(dados.get('clinica')))}</p>"
        if dados.get("clinica") else ""
    )
    return f"""
    <html><head><meta charset="utf-8"><style>
      body {{ font-family: Arial, sans-serif; color: #172033; }}
      header {{ border-bottom: 2px solid #0b8dca; padding-bottom: 12px; }}
      h1 {{ color: #075985; font-size: 24px; }}
      h2 {{ color: #075985; background: #eef8fe; padding: 7px; margin-top: 18px; }}
      h3 {{ font-size: 14px; margin-bottom: 4px; }}
      p {{ font-size: 12px; line-height: 1.45; margin-top: 0; }}
      footer {{ color: #64748b; margin-top: 28px; text-align: center; }}
    </style></head><body>
      <header>
        <h1>{html.escape(str(dados.get('modelo') or 'Ficha Clínica'))}</h1>
        <p><strong>Paciente:</strong> {html.escape(str(dados.get('paciente') or 'Não informado'))}</p>
        <p><strong>Data:</strong> {html.escape(str(dados.get('data') or ''))}</p>
        {clinica}{profissional}
      </header>
      {''.join(blocos) or '<p>Nenhuma resposta preenchida.</p>'}
      <footer>Documento gerado pelo Prontu.</footer>
    </body></html>
    """
