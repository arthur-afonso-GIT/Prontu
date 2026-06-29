"""
Tokens de design (Design Tokens) do Clinic Manager.

Centraliza TODAS as decisões de cor, espaçamento e tipografia em um
único lugar, como constantes Python. O arquivo `theme.qss` é gerado a
partir destes tokens (ver `styles/qss_builder.py`), em vez de ter cores
"mágicas" hardcoded espalhadas em folhas de estilo — isso permite, por
exemplo, trocar o accent principal da aplicação em um único lugar no
futuro (ex: para suportar tema por clínica/marca-branca).

IDENTIDADE VISUAL ESCOLHIDA
---------------------------
Em vez de réplicar o cinza neutro genérico comum em apps "estilo
Notion", a paleta abaixo foi pensada especificamente para o contexto de
uma clínica: calma, confiável, mas com clareza forte para reduzir
fadiga visual de quem usa o sistema o dia inteiro.

    Fundo:        quase-branco levemente azulado, não branco puro
                  (#FFFFFF puro cansa a vista em uso prolongado)
    Texto:        carvão-azulado, não preto puro (#1A2233)
    Accent:       "teal clínico" (#0F8B8D) — cor de confiança/saúde
                  sem ser o azul-hospital genérico
    Destaque:     terracota suave (#E8896B), usado APENAS para alertas
                  pontuais e nunca como cor estrutural

Elemento de assinatura: uma barra vertical fina e colorida à esquerda
de cards de paciente/consulta, indicando o convênio — funcional
(identificação visual rápida) e não puramente decorativa.
"""

from __future__ import annotations


class Colors:
    """Paleta de cores da aplicação."""

    # Superfícies
    BACKGROUND = "#FAFBFC"
    SURFACE = "#FFFFFF"
    SURFACE_HOVER = "#F1F4F7"
    SURFACE_PRESSED = "#E7EBEF"
    BORDER = "#E3E8EC"
    BORDER_STRONG = "#CBD3DA"

    # Texto
    TEXT_PRIMARY = "#1A2233"
    TEXT_SECONDARY = "#5B6675"
    TEXT_TERTIARY = "#9AA5B1"
    TEXT_ON_ACCENT = "#FFFFFF"

    # Accent principal ("teal clínico")
    ACCENT = "#0F8B8D"
    ACCENT_HOVER = "#0D7A7C"
    ACCENT_PRESSED = "#0B6A6C"
    ACCENT_SOFT = "#E3F3F3"

    # Destaque secundário (uso pontual: alertas, urgências)
    HIGHLIGHT = "#E8896B"
    HIGHLIGHT_SOFT = "#FBEAE3"

    # Estados semânticos
    SUCCESS = "#10A37F"
    SUCCESS_SOFT = "#E3F6EF"
    WARNING = "#D97706"
    WARNING_SOFT = "#FEF3E2"
    DANGER = "#DC4444"
    DANGER_SOFT = "#FCEAEA"

    # Sidebar (levemente mais escura que o conteúdo, criando profundidade)
    SIDEBAR_BACKGROUND = "#16202B"
    SIDEBAR_TEXT = "#C7D0D9"
    SIDEBAR_TEXT_ACTIVE = "#FFFFFF"
    SIDEBAR_HOVER = "#1F2C39"
    SIDEBAR_ACTIVE = "#0F8B8D"

    # Cores sugeridas para pastas/convênios (paleta harmônica e distinguível)
    FOLDER_PALETTE = [
        "#0F8B8D", "#6366F1", "#E8896B", "#10A37F",
        "#D97706", "#8B5CF6", "#EC4899", "#3B82F6",
    ]


class Typography:
    """Famílias e escala tipográfica."""

    FONT_FAMILY = "Inter, Segoe UI, -apple-system, sans-serif"
    FONT_FAMILY_MONO = "JetBrains Mono, Consolas, monospace"

    SIZE_XS = 11
    SIZE_SM = 12
    SIZE_BASE = 13
    SIZE_MD = 14
    SIZE_LG = 16
    SIZE_XL = 20
    SIZE_XXL = 26

    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


class Spacing:
    """Escala de espaçamento em pixels (múltiplos de 4)."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Radius:
    """Raios de borda para criar a estética arredondada/moderna."""

    SM = 6
    MD = 10
    LG = 14
    FULL = 999


class Elevation:
    """Sombras leves para criar hierarquia visual sutil (estilo Notion/Linear).

    Qt/QSS não suporta `box-shadow` nativamente em todos os widgets;
    sombras reais são aplicadas via `QGraphicsDropShadowEffect` em tempo
    de execução (ver `views/components/shadow.py`), mas os valores aqui
    documentam a intenção de design consistente entre os dois mecanismos.
    """

    LOW_BLUR_RADIUS = 12
    LOW_OFFSET_Y = 2
    LOW_ALPHA = 18  # 0-255

    MEDIUM_BLUR_RADIUS = 24
    MEDIUM_OFFSET_Y = 6
    MEDIUM_ALPHA = 28
