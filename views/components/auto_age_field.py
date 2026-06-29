"""
Componente de exibição de Idade (somente leitura, calculada automaticamente).

Implementa a regra obrigatória do projeto: a idade NUNCA é digitável
diretamente pelo usuário; ela é sempre derivada da data de nascimento e
atualizada em tempo real conforme o campo de data é alterado.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QLineEdit, QWidget

from utils.age_calculator import calculate_age


class AutoAgeField(QLineEdit):
    """Campo somente-leitura que exibe a idade calculada a partir de uma data.

    Conecte este componente ao `dateChanged` de um `QDateEdit` de data
    de nascimento via `bind_to_birth_date_field` para manter a idade
    sempre sincronizada em tempo real.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("—")
        # Visualmente distinto de campos editáveis, sinalizando que não é interativo.
        self.setStyleSheet("background-color: #F1F4F7; color: #5B6675;")

    def update_from_birth_date(self, birth_date: date | None) -> None:
        """Recalcula e exibe a idade a partir de uma nova data de nascimento."""
        if birth_date is None:
            self.setText("")
            return

        try:
            idade = calculate_age(birth_date)
            self.setText(f"{idade} ano{'s' if idade != 1 else ''}")
        except ValueError:
            self.setText("Data inválida")

    def bind_to_birth_date_field(self, date_edit_widget) -> None:
        """Conecta este campo a um `QDateEdit`, atualizando a idade em tempo real.

        Args:
            date_edit_widget: Instância de `QDateEdit` (ou compatível,
                expondo o sinal `dateChanged` e o método `date()`).
        """
        def _on_date_changed(qdate) -> None:
            self.update_from_birth_date(qdate.toPython())

        date_edit_widget.dateChanged.connect(_on_date_changed)
        self.update_from_birth_date(date_edit_widget.date().toPython())
