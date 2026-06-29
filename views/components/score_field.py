"""
Componente de Score Clínico interativo.

Renderiza um campo do tipo SCORE (ver `forms/field_schema.py`) como um
checklist interativo: cada item pode ser marcado/desmarcado, a
pontuação total é recalculada em tempo real a cada alteração, e a
classificação de risco correspondente é exibida automaticamente —
exatamente conforme especificado no projeto ("calcular o score, mostrar
risco automaticamente, atualizar a interface em tempo real").
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from forms.field_schema import FieldDefinition
from parsers.score_detector import ScoreDetector
from styles.design_tokens import Radius, Spacing


class ScoreField(QWidget):
    """Widget de checklist de score clínico com cálculo automático de risco.

    Emite `score_changed(pontuacao_total, classificacao_label)` sempre
    que um item é marcado/desmarcado, permitindo que o container pai
    (ex: o builder de formulário) reaja a mudanças, se necessário (ex:
    para acionar uma explicação de IA sobre o risco calculado).
    """

    score_changed = Signal(float, str)

    def __init__(self, field_definition: FieldDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._field_definition = field_definition
        self._checkboxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        for item in field_definition.itens_score:
            checkbox = QCheckBox(f"{item.label}  (+{item.pontos:g} pts)" if item.pontos >= 0 else f"{item.label}  ({item.pontos:g} pts)")
            checkbox.setChecked(item.selecionado_por_padrao)
            checkbox.stateChanged.connect(self._recalculate)
            self._checkboxes[item.id] = checkbox
            layout.addWidget(checkbox)

        self._result_label = QLabel()
        self._result_label.setWordWrap(True)
        self._result_label.setContentsMargins(
            Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM
        )
        layout.addWidget(self._result_label)

        self._recalculate()

    def _recalculate(self) -> None:
        itens_marcados = {
            item_id for item_id, checkbox in self._checkboxes.items() if checkbox.isChecked()
        }
        total = ScoreDetector.calculate_score_total(self._field_definition.itens_score, itens_marcados)
        faixa = ScoreDetector.classify_risk(self._field_definition.faixas_risco, total)

        classificacao = faixa.classificacao if faixa else "Não classificado"
        cor = faixa.cor if faixa else "#9AA5B1"

        self._result_label.setText(f"Pontuação total: {total:g}  —  {classificacao}")
        self._result_label.setStyleSheet(
            f"background-color: {cor}22; color: {cor}; "
            f"border-radius: {Radius.SM}px; font-weight: 600;"
        )

        self.score_changed.emit(total, classificacao)

    def get_data(self) -> dict:
        """Retorna os itens marcados e o resultado calculado, para persistência."""
        itens_marcados = [
            item_id for item_id, checkbox in self._checkboxes.items() if checkbox.isChecked()
        ]
        total = ScoreDetector.calculate_score_total(self._field_definition.itens_score, set(itens_marcados))
        faixa = ScoreDetector.classify_risk(self._field_definition.faixas_risco, total)

        return {
            "itens_marcados": itens_marcados,
            "total": total,
            "classificacao": faixa.classificacao if faixa else None,
        }
