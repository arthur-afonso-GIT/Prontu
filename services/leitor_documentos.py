"""Leitura local de modelos e fichas clínicas em imagem, Word e PDF.

O módulo não envia documentos para serviços externos. Para fotos e PDFs
digitalizados, a leitura usa um OCR local e sempre devolve o resultado para
revisão humana antes de qualquer registro clínico ser salvo.
"""

from __future__ import annotations

import re
import tempfile
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
ROTULOS_PREENCHIDOS_CONHECIDOS = (
    "data de nascimento", "data nascimento", "data nasc", "nascimento",
    "nome completo", "estado civil", "tipo sanguíneo", "tipo sanguineo",
    "queixa principal", "histórico da doença atual",
    "historico da doenca atual", "antecedentes pessoais",
    "antecedentes familiares", "medicamentos em uso", "exame físico",
    "exame fisico", "pressão arterial", "pressao arterial",
    "frequência cardíaca", "frequencia cardiaca", "nome", "telefone",
    "celular", "whatsapp", "e-mail", "email", "cpf", "rg", "sexo",
    "gênero", "genero", "profissão", "profissao", "convênio", "convenio",
    "plano", "endereço", "endereco", "data", "idade", "peso", "altura",
    "temperatura", "observações", "observacoes", "diagnóstico",
    "diagnostico", "conduta", "prescrição", "prescricao", "qp", "hda",
    "pa", "fc",
)
EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
MARCADO_DETALHADO = re.compile(
    r"(\[\s*[xX✓✔]?\s*\]|\(\s*[xX✓✔]?\s*\)|☐|☑|□|■|○|◉)"
)
_MOTOR_OCR = None


class ErroDigitalizacao(RuntimeError):
    """Falha compreensível e segura durante a leitura de uma ficha."""


@dataclass(frozen=True)
class ResultadoDigitalizacao:
    campos: list[dict]
    respostas: dict
    confianca_media: float
    avisos: list[str]
    modo: str


@dataclass(frozen=True)
class BlocoDocumento:
    texto: str
    origem: str = "paragrafo"
    estilo: str = ""
    nivel_titulo: int = 0
    negrito: bool = False
    pagina: int | None = None
    confianca: float | None = None
    x: float | None = None
    y: float | None = None
    largura: float | None = None
    altura: float | None = None


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


def _caixa_ocr(caixa) -> tuple[float, float, float, float]:
    pontos = list(caixa) if caixa is not None else []
    xs = [float(ponto[0]) for ponto in pontos if len(ponto) >= 2]
    ys = [float(ponto[1]) for ponto in pontos if len(ponto) >= 2]
    if not xs or not ys:
        return 0.0, 0.0, 0.0, 0.0
    esquerda, direita = min(xs), max(xs)
    topo, base = min(ys), max(ys)
    return esquerda, topo, direita - esquerda, base - topo


def _agrupar_linhas_ocr(blocos: list[BlocoDocumento]) -> list[BlocoDocumento]:
    """Ordena caixas por linha e coluna sem fundir pergunta e resposta."""
    ordenados = sorted(
        blocos,
        key=lambda item: (
            int(item.pagina or 0),
            float(item.y or 0),
            float(item.x or 0),
        ),
    )
    linhas: list[list[BlocoDocumento]] = []
    for bloco in ordenados:
        centro = float(bloco.y or 0) + float(bloco.altura or 0) / 2
        destino = None
        for linha in reversed(linhas[-4:]):
            primeiro = linha[0]
            if primeiro.pagina != bloco.pagina:
                continue
            centro_linha = sum(
                float(item.y or 0) + float(item.altura or 0) / 2
                for item in linha
            ) / len(linha)
            tolerancia = max(
                8.0,
                max(float(item.altura or 0) for item in linha + [bloco]) * 0.62,
            )
            if abs(centro - centro_linha) <= tolerancia:
                destino = linha
                break
        if destino is None:
            linhas.append([bloco])
        else:
            destino.append(bloco)

    resultado: list[BlocoDocumento] = []
    for linha in linhas:
        linha.sort(key=lambda item: float(item.x or 0))
        resultado.extend(linha)
    return resultado


def _obter_motor_ocr():
    global _MOTOR_OCR
    try:
        from rapidocr import RapidOCR
    except ImportError as erro:
        raise ErroDigitalizacao(
            "O leitor local de imagens não está instalado nesta versão do Prontu."
        ) from erro

    if _MOTOR_OCR is None:
        try:
            _MOTOR_OCR = RapidOCR()
        except Exception as erro:
            raise ErroDigitalizacao(
                "Não foi possível iniciar o leitor local de imagens."
            ) from erro
    return _MOTOR_OCR


def _preparar_imagem_ocr(caminho: str | Path, destino: str | Path) -> None:
    try:
        from PIL import Image, ImageEnhance, ImageOps

        with Image.open(str(caminho)) as original:
            imagem = ImageOps.exif_transpose(original).convert("L")
            maior_lado = max(imagem.size)
            if maior_lado < 1800:
                escala = 1800 / max(1, maior_lado)
                imagem = imagem.resize(
                    (int(imagem.width * escala), int(imagem.height * escala)),
                    Image.Resampling.LANCZOS,
                )
            imagem = ImageOps.autocontrast(imagem, cutoff=1)
            imagem = ImageEnhance.Contrast(imagem).enhance(1.12)
            imagem.save(str(destino), format="PNG", optimize=True)
    except Exception as erro:
        raise ErroDigitalizacao(
            "Não foi possível preparar a foto. Verifique se o arquivo não está corrompido."
        ) from erro


def _executar_ocr_imagem(caminho: str | Path, pagina: int = 1) -> list[BlocoDocumento]:
    try:
        motor = _obter_motor_ocr()
        with tempfile.TemporaryDirectory(prefix="prontu_foto_") as temporario:
            preparada = Path(temporario) / "imagem_preparada.png"
            _preparar_imagem_ocr(caminho, preparada)
            resultado = motor(str(preparada))
    except Exception as erro:
        if isinstance(erro, ErroDigitalizacao):
            raise
        raise ErroDigitalizacao(
            "Não foi possível ler a imagem. Use uma foto nítida, bem iluminada e sem cortes."
        ) from erro

    textos_brutos = getattr(resultado, "txts", None)
    caixas_brutas = getattr(resultado, "boxes", None)
    confiancas_brutas = getattr(resultado, "scores", None)
    textos = list(textos_brutos) if textos_brutos is not None else []
    caixas = list(caixas_brutas) if caixas_brutas is not None else []
    confiancas = list(confiancas_brutas) if confiancas_brutas is not None else []
    blocos: list[BlocoDocumento] = []
    for indice, texto_bruto in enumerate(textos):
        texto = _texto_visivel(texto_bruto)
        if not texto:
            continue
        caixa = caixas[indice] if indice < len(caixas) else []
        x, y, largura, altura = _caixa_ocr(caixa)
        confianca = (
            float(confiancas[indice]) if indice < len(confiancas) else None
        )
        blocos.append(BlocoDocumento(
            texto=texto,
            origem="ocr",
            pagina=pagina,
            confianca=confianca,
            x=x,
            y=y,
            largura=largura,
            altura=altura,
        ))
    return _agrupar_linhas_ocr(blocos)


def extrair_blocos_ficha(caminho: str | Path) -> tuple[list[BlocoDocumento], str]:
    """Extrai uma ficha preenchida, priorizando texto exato antes do OCR."""
    arquivo = Path(caminho)
    extensao = arquivo.suffix.casefold()
    if extensao in EXTENSOES_IMAGEM:
        return _executar_ocr_imagem(arquivo), "ocr_local"
    if extensao != ".pdf":
        raise ErroDigitalizacao("Selecione uma foto ou um arquivo PDF.")

    blocos_texto = extrair_blocos_pdf(arquivo)
    caracteres = sum(len(bloco.texto) for bloco in blocos_texto)
    if caracteres >= 40:
        return blocos_texto, "texto_pdf"

    try:
        import fitz
    except ImportError as erro:
        raise ErroDigitalizacao(
            "O leitor de PDFs digitalizados não está instalado nesta versão do Prontu."
        ) from erro

    blocos: list[BlocoDocumento] = []
    try:
        documento = fitz.open(str(arquivo))
        with tempfile.TemporaryDirectory(prefix="prontu_ocr_") as temporario:
            for numero, pagina_pdf in enumerate(documento, start=1):
                matriz = fitz.Matrix(2.2, 2.2)
                imagem = pagina_pdf.get_pixmap(matrix=matriz, alpha=False)
                destino = Path(temporario) / f"pagina_{numero}.png"
                imagem.save(str(destino))
                blocos.extend(_executar_ocr_imagem(destino, numero))
        documento.close()
    except ErroDigitalizacao:
        raise
    except Exception as erro:
        raise ErroDigitalizacao(
            "Não foi possível transformar o PDF em uma ficha legível."
        ) from erro
    return blocos, "ocr_local"


def _marcador_esta_selecionado(marcador: str) -> bool:
    marcador = str(marcador or "")
    return bool(re.search(r"[xX✓✔☑■◉]", marcador))


def _opcoes_preenchidas(texto: str) -> tuple[str, list[str], list[str]]:
    marcadores = list(MARCADO_DETALHADO.finditer(texto))
    if not marcadores:
        return "", [], []
    prefixo = _limpar_rotulo(texto[:marcadores[0].start()])
    opcoes: list[str] = []
    selecionadas: list[str] = []
    for indice, marcador in enumerate(marcadores):
        fim = marcadores[indice + 1].start() if indice + 1 < len(marcadores) else len(texto)
        opcao = _limpar_rotulo(texto[marcador.end():fim])
        if not opcao:
            continue
        opcoes.append(opcao)
        if _marcador_esta_selecionado(marcador.group(0)):
            selecionadas.append(opcao)
    return prefixo, opcoes, selecionadas


def _parece_rotulo_preenchido(texto: str, bloco: BlocoDocumento) -> bool:
    limpo = _limpar_rotulo(texto)
    if not limpo or len(limpo) > 100:
        return False
    if texto.rstrip().endswith((":", "?")):
        return True
    chave = _chave(limpo)
    conhecido = any(
        _contem_termo(chave, item)
        for item in (
            PALAVRAS_TEXTO_LONGO
            + PALAVRAS_DATA
            + ROTULOS_CURTOS_CONHECIDOS
            + tuple(UNIDADES_NUMERICAS)
        )
    )
    return conhecido or bloco.origem.startswith("tabela")


def _dividir_pares_preenchidos(texto: str) -> list[tuple[str, str]]:
    """Separa vários pares rótulo/resposta reconhecidos na mesma linha."""
    alternativas = "|".join(
        re.escape(rotulo)
        for rotulo in sorted(
            ROTULOS_PREENCHIDOS_CONHECIDOS, key=len, reverse=True
        )
    )
    padrao = re.compile(
        rf"(?:^|\s+|[|;]\s*)"
        rf"({alternativas})\s*[:=]\s*",
        re.IGNORECASE,
    )
    marcadores = list(padrao.finditer(texto))
    if len(marcadores) < 2:
        return []
    pares: list[tuple[str, str]] = []
    for indice, marcador in enumerate(marcadores):
        fim = (
            marcadores[indice + 1].start()
            if indice + 1 < len(marcadores)
            else len(texto)
        )
        valor = _texto_visivel(texto[marcador.end():fim]).strip(" |;,.-")
        if valor:
            pares.append((_limpar_rotulo(marcador.group(1)), valor))
    return pares if len(pares) >= 2 else []


def _mapear_respostas_por_posicao(
    blocos: list[BlocoDocumento],
) -> tuple[dict[int, int], set[int]]:
    """Relaciona rótulos e respostas usando as coordenadas produzidas pelo OCR."""
    rotulos = [
        indice
        for indice, bloco in enumerate(blocos)
        if bloco.x is not None
        and bloco.y is not None
        and _parece_rotulo_preenchido(bloco.texto, bloco)
        and not re.search(r"[:=]\s*\S+", bloco.texto)
    ]
    candidatos = [
        indice
        for indice, bloco in enumerate(blocos)
        if bloco.x is not None
        and bloco.y is not None
        and indice not in rotulos
        and not _parece_secao(bloco, bloco.texto)
    ]
    possibilidades: list[tuple[float, int, int]] = []
    for indice_rotulo in rotulos:
        rotulo = blocos[indice_rotulo]
        rx = float(rotulo.x or 0)
        ry = float(rotulo.y or 0)
        rw = max(float(rotulo.largura or 0), 1.0)
        rh = max(float(rotulo.altura or 0), 1.0)
        rcentro_y = ry + rh / 2
        for indice_valor in candidatos:
            valor = blocos[indice_valor]
            if valor.pagina != rotulo.pagina:
                continue
            vx = float(valor.x or 0)
            vy = float(valor.y or 0)
            vw = max(float(valor.largura or 0), 1.0)
            vh = max(float(valor.altura or 0), 1.0)
            vcentro_y = vy + vh / 2
            mesma_linha = (
                vx >= rx + rw * 0.55
                and abs(vcentro_y - rcentro_y) <= max(rh, vh) * 0.8
            )
            sobreposicao_x = min(rx + rw, vx + vw) - max(rx, vx)
            mesma_coluna = (
                vy >= ry + rh * 0.45
                and vy - (ry + rh) <= max(140.0, rh * 5)
                and (
                    sobreposicao_x > 0
                    or abs(vx - rx) <= max(rw, vw) * 0.42
                )
            )
            if mesma_linha:
                pontuacao = (
                    max(0.0, vx - (rx + rw))
                    + abs(vcentro_y - rcentro_y) * 3
                )
            elif mesma_coluna:
                pontuacao = (
                    400 + max(0.0, vy - (ry + rh)) * 3 + abs(vx - rx)
                )
            else:
                continue
            possibilidades.append((pontuacao, indice_rotulo, indice_valor))

    mapa: dict[int, int] = {}
    usados: set[int] = set()
    for _, indice_rotulo, indice_valor in sorted(possibilidades):
        if indice_rotulo not in mapa and indice_valor not in usados:
            mapa[indice_rotulo] = indice_valor
            usados.add(indice_valor)
    return mapa, usados


def interpretar_ficha_preenchida(
    blocos: Iterable[BlocoDocumento | dict | str],
    modo: str = "ocr_local",
) -> ResultadoDigitalizacao:
    """Associa rótulos e respostas, preservando conteúdo incerto para revisão."""
    normalizados: list[BlocoDocumento] = []
    for bloco in blocos:
        if isinstance(bloco, BlocoDocumento):
            atual = bloco
        elif isinstance(bloco, dict):
            atual = BlocoDocumento(**{
                chave: valor for chave, valor in bloco.items()
                if chave in BlocoDocumento.__dataclass_fields__
            })
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
                confianca=atual.confianca,
                x=atual.x,
                y=atual.y,
                largura=atual.largura,
                altura=atual.altura,
            ))

    campos: list[dict] = []
    respostas: dict = {}
    ids: set[str] = set()
    nao_associados: list[str] = []
    confiancas = [
        float(bloco.confianca)
        for bloco in normalizados
        if bloco.confianca is not None
    ]
    baixa_confianca = 0
    respostas_posicionais, indices_respostas_posicionais = (
        _mapear_respostas_por_posicao(normalizados)
    )

    def adicionar(rotulo: str, valor: object = "", tipo: str | None = None, extras: dict | None = None, confianca: float | None = None) -> None:
        nonlocal baixa_confianca
        rotulo = _limpar_rotulo(rotulo)
        if len(rotulo) < 2 or len(rotulo) > 120:
            return
        tipo_inferido, extras_inferidos = _tipo_campo(rotulo)
        tipo_final = tipo or tipo_inferido
        campo = _novo_campo(tipo_final, rotulo, {**extras_inferidos, **(extras or {})})
        if tipo_final != "secao":
            base = campo.get("id") or "campo"
            campo_id = base
            contador = 2
            while campo_id in ids:
                campo_id = f"{base}_{contador}"
                contador += 1
            campo["id"] = campo_id
            ids.add(campo_id)
            if confianca is not None and confianca < 0.72:
                campo["ajuda"] = "Leitura com baixa confiança. Confira este campo."
                baixa_confianca += 1
            respostas[campo_id] = valor
        campos.append(campo)

    indice = 0
    while indice < len(normalizados):
        bloco = normalizados[indice]
        texto = bloco.texto

        if indice in indices_respostas_posicionais:
            indice += 1
            continue

        pares_preenchidos = _dividir_pares_preenchidos(texto)
        if pares_preenchidos:
            for rotulo, valor in pares_preenchidos:
                adicionar(rotulo, valor, confianca=bloco.confianca)
            indice += 1
            continue

        prefixo, opcoes, selecionadas = _opcoes_preenchidas(texto)
        if opcoes:
            rotulo_opcoes = prefixo or (
                opcoes[0] if len(opcoes) == 1 else "Opções identificadas"
            )
            if len(opcoes) == 1:
                adicionar(
                    rotulo_opcoes,
                    bool(selecionadas),
                    "checkbox",
                    {"texto_checkbox": opcoes[0]},
                    bloco.confianca,
                )
            else:
                adicionar(
                    rotulo_opcoes,
                    selecionadas[0] if selecionadas else "",
                    "multipla_escolha",
                    {"opcoes": opcoes},
                    bloco.confianca,
                )
            indice += 1
            continue

        encontrado = re.match(
            r"^(.{2,100}?)(?:\s*[:=]\s*|\s*[_.]{3,}\s*)(.*)$",
            texto,
        )
        if encontrado:
            rotulo = _limpar_rotulo(encontrado.group(1))
            valor = _texto_visivel(encontrado.group(2))
            confianca = bloco.confianca
            indice_posicional = respostas_posicionais.get(indice)
            if not valor and indice_posicional is not None:
                proximo = normalizados[indice_posicional]
                valor = proximo.texto
                confiancas_par = [
                    item for item in (bloco.confianca, proximo.confianca)
                    if item is not None
                ]
                confianca = (
                    sum(confiancas_par) / len(confiancas_par)
                    if confiancas_par else None
                )
            elif not valor and indice + 1 < len(normalizados):
                proximo = normalizados[indice + 1]
                if (
                    indice + 1 not in indices_respostas_posicionais
                    and not _parece_rotulo_preenchido(proximo.texto, proximo)
                ):
                    valor = proximo.texto
                    confiancas_par = [
                        item for item in (bloco.confianca, proximo.confianca)
                        if item is not None
                    ]
                    confianca = (
                        sum(confiancas_par) / len(confiancas_par)
                        if confiancas_par else None
                    )
                    indice += 1
            adicionar(rotulo, valor, confianca=confianca)
            indice += 1
            continue

        embutido = next(
            (
                re.match(
                    rf"^({re.escape(rotulo)})(?:\s+|\s*[-–—]\s*)(.+)$",
                    texto,
                    re.IGNORECASE,
                )
                for rotulo in ROTULOS_PREENCHIDOS_CONHECIDOS
                if re.match(
                    rf"^({re.escape(rotulo)})(?:\s+|\s*[-–—]\s*)(.+)$",
                    texto,
                    re.IGNORECASE,
                )
            ),
            None,
        )
        if embutido:
            adicionar(
                embutido.group(1),
                _texto_visivel(embutido.group(2)),
                confianca=bloco.confianca,
            )
            indice += 1
            continue

        if _parece_secao(bloco, texto):
            adicionar(texto, tipo="secao")
            indice += 1
            continue

        if _parece_rotulo_preenchido(texto, bloco):
            valor = ""
            confianca = bloco.confianca
            indice_posicional = respostas_posicionais.get(indice)
            if indice_posicional is not None:
                proximo = normalizados[indice_posicional]
                valor = proximo.texto
                confiancas_par = [
                    item for item in (bloco.confianca, proximo.confianca)
                    if item is not None
                ]
                confianca = (
                    sum(confiancas_par) / len(confiancas_par)
                    if confiancas_par else None
                )
            elif indice + 1 < len(normalizados):
                proximo = normalizados[indice + 1]
                if (
                    indice + 1 not in indices_respostas_posicionais
                    and not _parece_rotulo_preenchido(proximo.texto, proximo)
                ):
                    valor = proximo.texto
                    confiancas_par = [
                        item for item in (bloco.confianca, proximo.confianca)
                        if item is not None
                    ]
                    confianca = (
                        sum(confiancas_par) / len(confiancas_par)
                        if confiancas_par else None
                    )
                    indice += 1
            adicionar(texto, valor, confianca=confianca)
        else:
            nao_associados.append(texto)
        indice += 1

    if nao_associados:
        adicionar("Conteúdo adicional reconhecido", "\n".join(nao_associados), "texto_longo")

    avisos: list[str] = []
    if baixa_confianca:
        avisos.append(
            f"{baixa_confianca} campo(s) tiveram leitura incerta e precisam de conferência."
        )
    if nao_associados:
        avisos.append(
            "Alguns trechos não puderam ser associados a uma pergunta e foram preservados no final."
        )
    if not campos:
        avisos.append("Nenhum campo foi reconhecido.")

    return ResultadoDigitalizacao(
        campos=campos,
        respostas=respostas,
        confianca_media=(sum(confiancas) / len(confiancas)) if confiancas else 1.0,
        avisos=avisos,
        modo=modo,
    )


def digitalizar_ficha(caminho: str | Path) -> ResultadoDigitalizacao:
    blocos, modo = extrair_blocos_ficha(caminho)
    if not blocos:
        raise ErroDigitalizacao(
            "Nenhum texto foi encontrado. Tente outra foto com melhor iluminação e foco."
        )
    resultado = interpretar_ficha_preenchida(blocos, modo)
    if not any(campo.get("tipo") != "secao" for campo in resultado.campos):
        raise ErroDigitalizacao(
            "O texto foi lido, mas não foi possível identificar campos e respostas."
        )
    return resultado
