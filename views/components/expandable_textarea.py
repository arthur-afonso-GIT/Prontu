"""
Componente de TextArea expansível.

Usado em todos os campos clínicos longos (QP, HDA, Exame Físico,
Antecedentes, Plano Terapêutico, etc.), conforme exigido no projeto:
"Todas as áreas clínicas deverão utilizar TextArea expansível."

A expansão automática de altura conforme o conteúdo evita que o
profissional precise rolar dentro de uma caixa pequena para revisar um
texto longo já digitado.
"""

from __future__ import annotations

from PySide6.QtWidgets import QTextEdit, QWidget


class ExpandableTextArea(QTextEdit):
    """TextArea que cresce verticalmente conforme o conteúdo digitado.

    Args:
        placeholder: Texto exibido quando o campo está vazio.
        min_height: Altura mínima em pixels (mesmo quando vazio).
        max_height: Altura máxima antes de exibir scroll interno
            (evita que um texto extremamente longo "exploda" o layout
            da tela).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        placeholder: str = "",
        min_height: int = 80,
        max_height: int = 400,
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._min_height = min_height
        self._max_height = max_height
        self.setMinimumHeight(min_height)
        self.setAcceptRichText(False)

        self.textChanged.connect(self._adjust_height_to_content)

    def _adjust_height_to_content(self) -> None:
        """Recalcula a altura do widget com base no conteúdo atual."""
        altura_documento = int(self.document().size().height()) + 20
        nova_altura = max(self._min_height, min(altura_documento, self._max_height))
        self.setFixedHeight(nova_altura)
