"""
Builder do QSS (Qt Style Sheets) global da aplicação.

Gera a folha de estilo completa a partir dos `design_tokens.py`,
evitando que valores de cor/espaçamento fiquem hardcoded diretamente em
strings QSS espalhadas pelo código. Para alterar a identidade visual de
toda a aplicação, basta alterar os tokens — este arquivo apenas monta o
texto QSS final.
"""

from __future__ import annotations

from styles.design_tokens import Colors, Radius, Spacing, Typography


def build_global_stylesheet() -> str:
    """Constrói a folha de estilo QSS aplicada à `QApplication` inteira."""
    return f"""
        /* ---------- Base ---------- */
        QWidget {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT_PRIMARY};
            font-family: {Typography.FONT_FAMILY};
            font-size: {Typography.SIZE_BASE}px;
        }}

        QMainWindow {{
            background-color: {Colors.BACKGROUND};
        }}

        QToolTip {{
            background-color: {Colors.TEXT_PRIMARY};
            color: {Colors.SURFACE};
            border: none;
            border-radius: {Radius.SM}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-size: {Typography.SIZE_SM}px;
        }}

        /* ---------- Scrollbars (estilo discreto, fino) ---------- */
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.BORDER_STRONG};
            border-radius: {Radius.FULL}px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {Colors.TEXT_TERTIARY};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {Colors.BORDER_STRONG};
            border-radius: {Radius.FULL}px;
            min-width: 24px;
        }}

        /* ---------- Inputs ---------- */
        QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            padding: {Spacing.SM}px {Spacing.MD}px;
            color: {Colors.TEXT_PRIMARY};
            selection-background-color: {Colors.ACCENT_SOFT};
            selection-color: {Colors.TEXT_PRIMARY};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QDateEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1.5px solid {Colors.ACCENT};
        }}
        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {Colors.SURFACE_HOVER};
            color: {Colors.TEXT_TERTIARY};
        }}
        QLineEdit::placeholder {{
            color: {Colors.TEXT_TERTIARY};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            selection-background-color: {Colors.ACCENT_SOFT};
            selection-color: {Colors.TEXT_PRIMARY};
            padding: {Spacing.XS}px;
        }}

        /* ---------- Botões ---------- */
        QPushButton {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM}px;
            padding: {Spacing.SM}px {Spacing.LG}px;
            font-weight: {Typography.WEIGHT_MEDIUM};
        }}
        QPushButton:hover {{
            background-color: {Colors.SURFACE_HOVER};
            border-color: {Colors.BORDER_STRONG};
        }}
        QPushButton:pressed {{
            background-color: {Colors.SURFACE_PRESSED};
        }}
        QPushButton:disabled {{
            color: {Colors.TEXT_TERTIARY};
            background-color: {Colors.SURFACE_HOVER};
        }}

        QPushButton#primaryButton {{
            background-color: {Colors.ACCENT};
            color: {Colors.TEXT_ON_ACCENT};
            border: none;
        }}
        QPushButton#primaryButton:hover {{
            background-color: {Colors.ACCENT_HOVER};
        }}
        QPushButton#primaryButton:pressed {{
            background-color: {Colors.ACCENT_PRESSED};
        }}

        QPushButton#dangerButton {{
            background-color: {Colors.DANGER_SOFT};
            color: {Colors.DANGER};
            border: none;
        }}
        QPushButton#dangerButton:hover {{
            background-color: {Colors.DANGER};
            color: {Colors.TEXT_ON_ACCENT};
        }}

        QPushButton#ghostButton {{
            background-color: transparent;
            border: none;
            color: {Colors.TEXT_SECONDARY};
        }}
        QPushButton#ghostButton:hover {{
            background-color: {Colors.SURFACE_HOVER};
            color: {Colors.TEXT_PRIMARY};
        }}

        QPushButton#whatsappButton {{
            background-color: {Colors.SUCCESS_SOFT};
            color: {Colors.SUCCESS};
            border: none;
            border-radius: {Radius.FULL}px;
        }}
        QPushButton#whatsappButton:hover {{
            background-color: {Colors.SUCCESS};
            color: {Colors.TEXT_ON_ACCENT};
        }}

        /* ---------- Sidebar ---------- */
        QWidget#sidebar {{
            background-color: {Colors.SIDEBAR_BACKGROUND};
        }}
        QPushButton#sidebarItem {{
            background-color: transparent;
            color: {Colors.SIDEBAR_TEXT};
            border: none;
            border-radius: {Radius.SM}px;
            text-align: left;
            padding: {Spacing.SM + 2}px {Spacing.MD}px;
            font-weight: {Typography.WEIGHT_MEDIUM};
            font-size: {Typography.SIZE_MD}px;
        }}
        QPushButton#sidebarItem:hover {{
            background-color: {Colors.SIDEBAR_HOVER};
            color: {Colors.SIDEBAR_TEXT_ACTIVE};
        }}
        QPushButton#sidebarItem:checked {{
            background-color: {Colors.SIDEBAR_ACTIVE};
            color: {Colors.SIDEBAR_TEXT_ACTIVE};
        }}
        QWidget#sidebar QLabel#sidebarBrand {{
            background-color: transparent;
            color: {Colors.SIDEBAR_TEXT_ACTIVE};
            font-size: {Typography.SIZE_LG}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QWidget#sidebar QLabel#sidebarVersion {{
            background-color: transparent;
            color: {Colors.SIDEBAR_TEXT};
            font-size: {Typography.SIZE_XS}px;
            padding-left: 8px;
        }}

        /* ---------- Cards e superfícies ---------- */
        QFrame#card {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.LG}px;
        }}
        QFrame#cardFlat {{
            background-color: {Colors.SURFACE};
            border-radius: {Radius.MD}px;
        }}

        /* ---------- Tabelas ---------- */
        QTableView, QTableWidget {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.MD}px;
            gridline-color: {Colors.BORDER};
            selection-background-color: {Colors.ACCENT_SOFT};
            selection-color: {Colors.TEXT_PRIMARY};
            alternate-background-color: {Colors.BACKGROUND};
        }}
        QHeaderView::section {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT_SECONDARY};
            border: none;
            border-bottom: 1px solid {Colors.BORDER};
            padding: {Spacing.SM}px {Spacing.MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            font-size: {Typography.SIZE_SM}px;
        }}
        QTableView::item, QTableWidget::item {{
            padding: {Spacing.SM}px;
            border-bottom: 1px solid {Colors.BORDER};
        }}

        /* ---------- Labels semânticos ---------- */
        QLabel#pageTitle {{
            font-size: {Typography.SIZE_XXL}px;
            font-weight: {Typography.WEIGHT_BOLD};
            color: {Colors.TEXT_PRIMARY};
        }}
        QLabel#sectionTitle {{
            font-size: {Typography.SIZE_LG}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            color: {Colors.TEXT_PRIMARY};
        }}
        QLabel#fieldLabel {{
            font-size: {Typography.SIZE_SM}px;
            font-weight: {Typography.WEIGHT_MEDIUM};
            color: {Colors.TEXT_SECONDARY};
        }}
        QLabel#mutedText {{
            color: {Colors.TEXT_TERTIARY};
            font-size: {Typography.SIZE_SM}px;
        }}

        /* ---------- Tabs ---------- */
        QTabWidget::pane {{
            border: none;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {Colors.TEXT_SECONDARY};
            padding: {Spacing.SM}px {Spacing.LG}px;
            margin-right: {Spacing.XS}px;
            border-bottom: 2px solid transparent;
            font-weight: {Typography.WEIGHT_MEDIUM};
        }}
        QTabBar::tab:selected {{
            color: {Colors.ACCENT};
            border-bottom: 2px solid {Colors.ACCENT};
        }}
        QTabBar::tab:hover {{
            color: {Colors.TEXT_PRIMARY};
        }}

        /* ---------- Checkboxes e Radios ---------- */
        QCheckBox, QRadioButton {{
            spacing: {Spacing.SM}px;
            color: {Colors.TEXT_PRIMARY};
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 1.5px solid {Colors.BORDER_STRONG};
            border-radius: {Radius.SM - 2}px;
            background-color: {Colors.SURFACE};
        }}
        QRadioButton::indicator {{
            border-radius: {Radius.FULL}px;
        }}
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {Colors.ACCENT};
            border-color: {Colors.ACCENT};
        }}

        /* ---------- Menus e Dialogs ---------- */
        QMenu {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.MD}px;
            padding: {Spacing.XS}px;
        }}
        QMenu::item {{
            padding: {Spacing.SM}px {Spacing.LG}px;
            border-radius: {Radius.SM}px;
        }}
        QMenu::item:selected {{
            background-color: {Colors.SURFACE_HOVER};
        }}

        QDialog {{
            background-color: {Colors.BACKGROUND};
        }}

        /* ---------- Splitter ---------- */
        QSplitter::handle {{
            background-color: {Colors.BORDER};
        }}
    """
