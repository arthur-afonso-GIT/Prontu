"""
Detector de campos (fase de Classificação da engine de parsing).

Recebe as linhas de texto extraídas (`RawTextLine`) e classifica cada
uma em um tipo de `FieldDefinition`: título, subtítulo, campo simples,
ou marcador de textarea/checkbox/radio.

A estratégia é baseada em um dicionário de padrões conhecidos de fichas
médicas (nomes de campos comuns) combinado com heurísticas estruturais
(texto terminado em ":", texto em CAIXA ALTA curto = provável título,
presença de "( )" ou "[ ]" = provável checkbox).

Este módulo é deliberadamente extensível: novos padrões de campo podem
ser adicionados a `KNOWN_FIELD_PATTERNS` sem alterar a lógica de
classificação.
"""

from __future__ import annotations

import re

from forms.field_schema import FieldDefinition, FieldType
from parsers.raw_structures import RawTextLine

# Padrões de campos clínicos conhecidos. A chave é o `id` estável do campo
# (usado em `dados_json`); o valor é uma lista de variações textuais
# (case-insensitive) que, se encontradas no início da linha, identificam
# aquele campo. A ordem importa: padrões mais específicos devem vir antes
# de padrões mais genéricos que poderiam capturá-los por engano.
KNOWN_FIELD_PATTERNS: dict[str, list[str]] = {
    "nome": ["nome completo", "nome do paciente", "nome"],
    "profissao": ["profissão", "ocupação"],
    "telefone": ["telefone", "celular", "contato"],
    "email": ["e-mail", "email"],
    "cidade": ["cidade", "município"],
    "endereco": ["endereço", "endereco"],
    "cpf": ["cpf"],
    "crm": ["crm"],
    "observacoes": ["observações", "observacoes", "obs."],
    "qp": ["queixa principal", "qp"],
    "hda": ["história da doença atual", "historia da doenca atual", "hda"],
    "exame_fisico": ["exame físico", "exame fisico"],
    "antecedentes": ["antecedentes pessoais", "antecedentes familiares", "antecedentes"],
    "medicamentos": ["medicamentos em uso", "medicações", "medicamentos"],
    "condutas": ["conduta", "plano terapêutico", "condutas"],
}

# Campos que, por natureza clínica, devem sempre virar TEXTAREA expansível
# mesmo que o documento original os apresente como uma única linha.
LONG_TEXT_FIELD_IDS = {
    "qp", "hda", "exame_fisico", "antecedentes", "condutas", "observacoes",
    "medicamentos",
}

_CHECKBOX_PATTERN = re.compile(r"[\(\[]\s*[xX]?\s*[\)\]]")
_TITLE_MAX_WORDS = 6


class FieldDetector:
    """Classifica linhas de texto extraídas em definições de campo."""

    def detect_fields(self, linhas: list[RawTextLine]) -> list[FieldDefinition]:
        """Classifica uma lista de linhas de texto em campos de formulário.

        Args:
            linhas: Linhas extraídas pela fase de Extração, em ordem de leitura.

        Returns:
            Lista de `FieldDefinition` na mesma ordem de leitura do documento.
        """
        campos: list[FieldDefinition] = []

        for ordem, linha in enumerate(linhas):
            texto = linha.texto.strip()
            if not texto:
                continue

            campo = self._classify_line(texto, ordem)
            if campo:
                campos.append(campo)

        return campos

    def _classify_line(self, texto: str, ordem: int) -> FieldDefinition | None:
        """Classifica uma única linha de texto em um `FieldDefinition`."""

        campo_conhecido = self._match_known_field(texto)
        if campo_conhecido:
            field_id, label_detectado = campo_conhecido
            tipo = FieldType.TEXTAREA if field_id in LONG_TEXT_FIELD_IDS else FieldType.TEXTO_SIMPLES
            return FieldDefinition(id=field_id, tipo=tipo, label=label_detectado, ordem=ordem)

        if _CHECKBOX_PATTERN.search(texto):
            return self._build_checkbox_field(texto, ordem)

        if self._looks_like_title(texto):
            tipo = FieldType.TITULO if len(texto.split()) <= 4 else FieldType.SUBTITULO
            return FieldDefinition(
                id=self._slugify(texto, ordem), tipo=tipo, label=texto, ordem=ordem
            )

        # Linha não reconhecida por nenhum padrão: tratamos como campo de
        # texto simples genérico, preservando o conteúdo para revisão
        # manual do profissional na tela de construção de formulário.
        return FieldDefinition(
            id=self._slugify(texto, ordem),
            tipo=FieldType.TEXTO_SIMPLES,
            label=texto.rstrip(":").strip(),
            ordem=ordem,
        )

    def _match_known_field(self, texto: str) -> tuple[str, str] | None:
        """Verifica se a linha corresponde a um padrão de campo conhecido."""
        texto_lower = texto.lower().rstrip(":").strip()

        for field_id, variacoes in KNOWN_FIELD_PATTERNS.items():
            for variacao in variacoes:
                if texto_lower == variacao or texto_lower.startswith(variacao + ":"):
                    label = self._humanize_label(field_id)
                    return field_id, label
        return None

    def _build_checkbox_field(self, texto: str, ordem: int) -> FieldDefinition:
        """Constrói um campo CHECKBOX a partir de uma linha com marcador "( )"."""
        label_limpo = _CHECKBOX_PATTERN.sub("", texto).strip(" :-")
        return FieldDefinition(
            id=self._slugify(label_limpo, ordem),
            tipo=FieldType.CHECKBOX,
            label=label_limpo or texto,
            ordem=ordem,
        )

    def _looks_like_title(self, texto: str) -> bool:
        """Heurística para identificar títulos/subtítulos de seção.

        Critérios: linha curta (poucas palavras), sem pontuação final de
        frase, e predominantemente em letras maiúsculas OU terminando
        sem ":" (diferenciando de um campo de formulário como "Nome:").
        """
        palavras = texto.split()
        if len(palavras) > _TITLE_MAX_WORDS:
            return False
        if texto.endswith(":"):
            return False
        if texto.endswith(".") or texto.endswith(","):
            return False

        proporcao_maiuscula = sum(1 for c in texto if c.isupper()) / max(len(texto), 1)
        return proporcao_maiuscula > 0.5

    @staticmethod
    def _humanize_label(field_id: str) -> str:
        """Converte um id de campo (snake_case) em um label legível."""
        especiais = {
            "qp": "Queixa Principal",
            "hda": "História da Doença Atual",
            "cpf": "CPF",
            "crm": "CRM",
        }
        if field_id in especiais:
            return especiais[field_id]
        return field_id.replace("_", " ").capitalize()

    @staticmethod
    def _slugify(texto: str, ordem: int) -> str:
        """Gera um id estável e único a partir de um texto livre."""
        slug = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")
        slug = slug or "campo"
        return f"{slug}_{ordem}"
