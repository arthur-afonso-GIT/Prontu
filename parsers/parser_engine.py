"""
Engine de Parsing — orquestrador central do pipeline de importação de
fichas médicas em PDF/DOCX.

Pipeline (conforme especificado no projeto):

    1. Extração   -> `PDFParser` / `DOCXParser` produzem `RawDocument`
    2. Classificação -> `FieldDetector`, `TableDetector`, `ScoreDetector`
                        convertem `RawDocument` em `list[FieldDefinition]`
    3. Construção  -> consumida pela camada de UI (`views/dynamic_forms`)
                      para gerar os widgets Qt automaticamente

Este módulo é o único ponto de entrada que a camada de serviço
(`services/`) deve chamar. Nenhum código fora de `parsers/` deve
instanciar `PDFParser`, `DOCXParser` ou os detectores diretamente —
isso mantém a engine substituível como uma unidade coesa (ex: trocar a
biblioteca de extração de PDF no futuro não deve afetar nenhum outro
módulo do sistema).
"""

from __future__ import annotations

from pathlib import Path

from forms.field_schema import FieldDefinition
from parsers.docx_parser import DOCXParser
from parsers.field_detector import FieldDetector
from parsers.pdf_parser import PDFParser
from parsers.raw_structures import RawDocument
from parsers.score_detector import ScoreDetector
from parsers.table_detector import TableDetector
from utils.logger import get_logger

logger = get_logger(__name__)

# Quantas linhas de texto anteriores a uma tabela são consideradas como
# "contexto" para tentar identificar o nome de um score clínico conhecido
# (ex: o título "Escore CHA2DS2-VASc" geralmente aparece imediatamente
# antes da tabela de critérios).
SCORE_CONTEXT_LOOKBACK_LINES = 3


class ParserEngineError(Exception):
    """Erro genérico do pipeline de parsing (formato não suportado, arquivo corrompido etc.)."""
    pass


class ParserEngine:
    """Orquestra o pipeline completo de extração e classificação de documentos."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    def __init__(self) -> None:
        self._pdf_parser = PDFParser()
        self._docx_parser = DOCXParser()
        self._field_detector = FieldDetector()
        self._table_detector = TableDetector()
        self._score_detector = ScoreDetector()

    def parse_document(self, file_path: str | Path) -> list[FieldDefinition]:
        """Executa o pipeline completo sobre um arquivo PDF ou DOCX.

        Args:
            file_path: Caminho do documento a ser importado.

        Returns:
            Lista de `FieldDefinition` representando a estrutura
            completa do formulário, pronta para ser persistida em
            `Formulario.estrutura_json` ou renderizada na tela de
            revisão/construção de formulário.

        Raises:
            ParserEngineError: Se a extensão do arquivo não for suportada.
        """
        file_path = Path(file_path)
        extensao = file_path.suffix.lower()

        if extensao not in self.SUPPORTED_EXTENSIONS:
            raise ParserEngineError(
                f"Formato '{extensao}' não suportado. Use PDF ou DOCX."
            )

        logger.info("Iniciando pipeline de parsing para: %s", file_path.name)

        raw_document = self._extract(file_path, extensao)
        campos = self._classify(raw_document)

        logger.info(
            "Pipeline concluído: %d campos extraídos de '%s'.",
            len(campos), file_path.name,
        )
        return campos

    def _extract(self, file_path: Path, extensao: str) -> RawDocument:
        """Fase 1 (Extração): delega ao parser específico do formato."""
        if extensao == ".pdf":
            return self._pdf_parser.parse(file_path)
        return self._docx_parser.parse(file_path)

    def _classify(self, raw_document: RawDocument) -> list[FieldDefinition]:
        """Fase 2 (Classificação): converte elementos brutos em campos tipados.

        Estratégia de fusão de texto e tabelas em uma única lista
        ordenada: percorremos as linhas de texto e, na posição (`ordem`)
        em que uma tabela foi originalmente extraída, inserimos o campo
        TABELA ou SCORE correspondente, preservando a ordem visual
        original do documento.
        """
        campos_texto = self._field_detector.detect_fields(raw_document.linhas)
        campos_tabela = self._classify_tables(raw_document)

        todos_campos = campos_texto + campos_tabela
        todos_campos.sort(key=lambda campo: campo.ordem)
        return todos_campos

    def _classify_tables(self, raw_document: RawDocument) -> list[FieldDefinition]:
        """Classifica cada tabela extraída como SCORE (se reconhecida) ou TABELA genérica."""
        campos_tabela: list[FieldDefinition] = []

        for tabela in raw_document.tabelas:
            contexto = self._get_context_before_table(raw_document, tabela.ordem)

            score_conhecido = self._score_detector.try_detect_known_score(contexto)
            if score_conhecido:
                campos_tabela.append(
                    self._score_detector.build_score_field(score_conhecido, tabela.ordem)
                )
                continue

            score_generico = self._score_detector.try_build_generic_score_from_table(
                tabela, tabela.ordem
            )
            if score_generico:
                campos_tabela.append(score_generico)
                continue

            campos_tabela.append(self._table_detector.detect_table_field(tabela, tabela.ordem))

        return campos_tabela

    def _get_context_before_table(self, raw_document: RawDocument, ordem_tabela: int) -> str:
        """Concatena as N linhas de texto imediatamente anteriores à tabela."""
        linhas_anteriores = [
            linha.texto
            for linha in raw_document.linhas
            if linha.ordem < ordem_tabela
        ]
        return " ".join(linhas_anteriores[-SCORE_CONTEXT_LOOKBACK_LINES:])
