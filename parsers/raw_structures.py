"""
Estruturas de dados intermediárias da engine de parsing.

Representam o resultado "bruto" da fase de Extração, antes de passar
pela fase de Classificação. Mantemos essas estruturas separadas de
`forms/field_schema.py` (que é o resultado FINAL, já classificado)
porque a fase de extração não sabe ainda que tipo de campo cada
elemento representa — ela só sabe "aqui tem uma linha de texto", "aqui
tem uma tabela com N colunas", etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawTextLine:
    """Uma linha de texto extraída do documento, com sua posição de leitura."""

    texto: str
    ordem: int
    pagina: int = 0


@dataclass
class RawTableCell:
    """Uma célula dentro de uma tabela extraída."""

    texto: str
    linha: int
    coluna: int


@dataclass
class RawTable:
    """Uma tabela extraída do documento (PDF ou DOCX)."""

    celulas: list[RawTableCell] = field(default_factory=list)
    num_linhas: int = 0
    num_colunas: int = 0
    ordem: int = 0
    pagina: int = 0

    def to_matrix(self) -> list[list[str]]:
        """Reconstrói a tabela como matriz de strings (linhas x colunas)."""
        matriz = [["" for _ in range(self.num_colunas)] for _ in range(self.num_linhas)]
        for celula in self.celulas:
            if 0 <= celula.linha < self.num_linhas and 0 <= celula.coluna < self.num_colunas:
                matriz[celula.linha][celula.coluna] = celula.texto
        return matriz

    def header_row(self) -> list[str]:
        """Retorna a primeira linha da tabela, normalmente o cabeçalho."""
        matriz = self.to_matrix()
        return matriz[0] if matriz else []


@dataclass
class RawDocument:
    """Resultado completo da fase de Extração: texto + tabelas, em ordem de leitura."""

    linhas: list[RawTextLine] = field(default_factory=list)
    tabelas: list[RawTable] = field(default_factory=list)
    nome_arquivo: str = ""
