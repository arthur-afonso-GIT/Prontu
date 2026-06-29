"""
Componente Card.

Container visual reutilizável (fundo branco, borda arredondada, sombra
leve) usado em toda a aplicação para agrupar conteúdo relacionado —
seções da Home, blocos da ficha do paciente, itens de lista, etc.
Centralizar este componente garante consistência visual e evita que
cada tela reimplemente seu próprio "card" com paddings diferentes.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from styles.design_tokens import Spacing
from styles.shadow import apply_card_shadow


class Card(QFrame):
    """Container com aparência de card (fundo, borda, raio, sombra).

    Args:
        parent: Widget pai.
        padding: Espaçamento interno em pixels (padrão: Spacing.LG).
        with_shadow: Se True, aplica sombra leve de elevação.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        padding: int = Spacing.LG,
        with_shadow: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(Spacing.MD)

        if with_shadow:
            apply_card_shadow(self, level="low")

    def add_widget(self, widget: QWidget) -> None:
        """Adiciona um widget ao corpo do card."""
        self._layout.addWidget(widget)

    @property
    def body_layout(self) -> QVBoxLayout:
        """Expõe o layout interno para composições mais customizadas."""
        return self._layout
