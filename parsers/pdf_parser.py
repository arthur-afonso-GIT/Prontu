"""
Parser de documentos PDF.

Responsabilidade única: extrair texto e tabelas de um arquivo PDF e
retornar a estrutura intermediária `RawDocument`, sem realizar nenhuma
classificação semântica dos campos (isso é responsabilidade de
`field_detector.py`, mais adiante no pipeline).

Usa `pypdf` para extração de texto. A extração de tabelas em PDF é
inerentemente heurística (PDFs não têm um conceito nativo de "tabela",
apenas texto posicionado), então aplicamos uma heurística de
agrupamento por espaçamento horizontal consistente entre linhas.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from parsers.raw_structures import RawDocument, RawTable, RawTableCell, RawTextLine
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFParser:
    """Extrai texto e tabelas de arquivos PDF."""

    # Mínimo de espaços consecutivos para considerarmos uma quebra de "coluna"
    # ao tentar detectar tabelas baseadas em alinhamento de texto.
    MIN_SPACES_FOR_COLUMN_BREAK = 3

    def parse(self, file_path: str | Path) -> RawDocument:
        """Extrai todo o conteúdo textual e tabular de um PDF.

        Args:
            file_path: Caminho do arquivo .pdf no disco.

        Returns:
            `RawDocument` com linhas de texto e tabelas detectadas.
        """
        file_path = Path(file_path)
        logger.info("Iniciando parsing de PDF: %s", file_path.name)

        reader = PdfReader(str(file_path))
        document = RawDocument(nome_arquivo=file_path.name)

        ordem_global = 0
        for page_index, page in enumerate(reader.pages):
            texto_pagina = page.extract_text() or ""
            linhas_pagina = [l for l in texto_pagina.split("\n") if l.strip()]

            for linha_texto in linhas_pagina:
                tabela_candidata = self._try_detect_table_row(linha_texto)

                if tabela_candidata:
                    self._append_or_create_table(document, tabela_candidata, page_index, ordem_global)
                else:
                    document.linhas.append(
                        RawTextLine(texto=linha_texto.strip(), ordem=ordem_global, pagina=page_index)
                    )
                ordem_global += 1

        logger.info(
            "PDF parseado: %d linhas de texto, %d tabelas detectadas.",
            len(document.linhas), len(document.tabelas),
        )
        return document

    def _try_detect_table_row(self, linha_texto: str) -> list[str] | None:
        """Heurística simples: divide a linha em "colunas" por espaçamento largo.

        Retorna a lista de células se a linha parecer tabular (2+ colunas
        separadas por espaçamento consistente), ou None caso contrário.
        """
        import re

        partes = re.split(r"\s{" + str(self.MIN_SPACES_FOR_COLUMN_BREAK) + r",}", linha_texto.strip())
        partes = [p.strip() for p in partes if p.strip()]

        if len(partes) >= 2:
            return partes
        return None

    def _append_or_create_table(
        self, document: RawDocument, celulas_linha: list[str], pagina: int, ordem: int
    ) -> None:
        """Agrupa linhas tabulares consecutivas na mesma `RawTable`.

        Se a última tabela do documento foi criada "recentemente" (na
        linha anterior processada) e tem o mesmo número de colunas,
        consideramos que a nova linha pertence a essa mesma tabela.
        Caso contrário, iniciamos uma nova tabela.
        """
        num_colunas = len(celulas_linha)

        tabela_atual = document.tabelas[-1] if document.tabelas else None
        pertence_a_tabela_atual = (
            tabela_atual is not None
            and tabela_atual.pagina == pagina
            and tabela_atual.num_colunas == num_colunas
        )

        if not pertence_a_tabela_atual:
            tabela_atual = RawTable(num_colunas=num_colunas, pagina=pagina, ordem=ordem)
            document.tabelas.append(tabela_atual)

        linha_index = tabela_atual.num_linhas
        for coluna_index, valor in enumerate(celulas_linha):
            tabela_atual.celulas.append(
                RawTableCell(texto=valor, linha=linha_index, coluna=coluna_index)
            )
        tabela_atual.num_linhas += 1
