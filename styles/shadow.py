"""
Utilitário de sombra leve para widgets Qt.

QSS não suporta `box-shadow` de forma confiável em todos os tipos de
widget. A forma correta de obter sombras suaves no Qt é aplicar um
`QGraphicsDropShadowEffect` programaticamente. Esta função centraliza
essa aplicação para que cards, modais e dialogs tenham exatamente a
mesma sombra em toda a aplicação (consistência visual), em vez de cada
componente reimplementar seus próprios parâmetros de sombra.
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from styles.design_tokens import Elevation


def apply_card_shadow(widget: QWidget, level: str = "low") -> None:
    """Aplica uma sombra leve a um widget, simulando elevação de card.

    Args:
        widget: O widget que receberá o efeito de sombra.
        level: "low" para cards comuns (listas, items), "medium" para
            elementos que devem se destacar mais (modais, popovers).
    """
    effect = QGraphicsDropShadowEffect(widget)

    if level == "medium":
        effect.setBlurRadius(Elevation.MEDIUM_BLUR_RADIUS)
        effect.setOffset(0, Elevation.MEDIUM_OFFSET_Y)
        effect.setColor(QColor(15, 23, 42, Elevation.MEDIUM_ALPHA))
    else:
        effect.setBlurRadius(Elevation.LOW_BLUR_RADIUS)
        effect.setOffset(0, Elevation.LOW_OFFSET_Y)
        effect.setColor(QColor(15, 23, 42, Elevation.LOW_ALPHA))

    widget.setGraphicsEffect(effect)
