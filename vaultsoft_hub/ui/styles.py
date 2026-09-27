"""The shared VaultSoft look (PulseMonitor, SweptPC, WaveScout), as one QSS sheet.

Colours come from those apps' palettes: near-black #0D1117 background,
#131A23 cards with a thin blue-grey border, teal #00D4AA accent, amber for
anything that needs attention. Segoe UI throughout.

Only containers get a background. A blanket `QWidget { background }` rule
paints every label inside a card as a dark box, which is what v1.0/v1.1 did.
Widgets whose look depends on a dynamic property (pills, buttons, status)
must be re-polished after the property changes: see `repolish()`.
"""

BG = "#0D1117"
SURFACE = "#131A23"
SURFACE_HOVER = "#1B2535"
BORDER = "#1C2B3A"
BORDER_HI = "#263848"
TEXT = "#E2EAF4"
TEXT_SUB = "#A0AEC0"
TEXT_MUTED = "#617080"
TEXT_STATUS = "#7C8A9B"  # one step lighter than TEXT_MUTED, for the small status lines
ACCENT = "#00D4AA"
ACCENT_HOVER = "#00ECC0"
ACCENT_DIM = "#00A882"
AMBER = "#F0A500"
BLUE = "#7CC4FA"


def _tint(hex_colour: str, alpha: float) -> str:
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _pill(kind: str, colour: str) -> str:
    return (
        f'QLabel#Pill[kind="{kind}"] {{ color: {colour}; background: {_tint(colour, 0.10)};'
        f" border: 1px solid {_tint(colour, 0.30)}; }}"
    )


def repolish(widget) -> None:
    """Re-apply the stylesheet after changing an objectName or dynamic property."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


STYLESHEET = f"""
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}}
QLabel {{ background: transparent; }}

QMainWindow, QWidget#Central, QWidget#Viewport, QWidget#ListContainer {{
    background-color: {BG};
}}
QScrollArea {{ background: {BG}; border: none; }}

/* ---- header ---------------------------------------------------------- */
QFrame#Header {{
    background-color: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QLabel#Title {{ font-size: 14pt; font-weight: 700; color: #FFFFFF; }}
QLabel#Brand {{ color: {TEXT_MUTED}; font-size: 8.5pt; padding-top: 4px; }}
QLabel#Version {{
    color: {ACCENT}; background: {_tint(ACCENT, 0.09)}; border: 1px solid {_tint(ACCENT, 0.27)};
    border-radius: 4px; font-size: 8pt; font-weight: 600; padding: 1px 6px;
}}
QLabel#StatusLine {{ color: {TEXT_SUB}; font-size: 9pt; }}

/* ---- groups and cards -------------------------------------------------- */
QLabel#GroupTitle {{
    color: {TEXT_MUTED}; font-size: 8pt; font-weight: 700; letter-spacing: 1.5px;
    padding-top: 6px;
}}
QFrame#AppCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#AppCard:hover {{
    background-color: {SURFACE_HOVER};
    border: 1px solid {_tint(ACCENT, 0.35)};
}}
QLabel#AppIcon {{
    background: {_tint(ACCENT, 0.08)};
    border: 1px solid {_tint(ACCENT, 0.22)};
    border-radius: 10px;
}}
QLabel#AppName {{ font-size: 11.5pt; font-weight: 700; color: #FFFFFF; }}
QLabel#AppDescription {{ color: {TEXT_SUB}; font-size: 9.5pt; }}
QLabel#AppStatus {{ color: {TEXT_STATUS}; font-size: 8.5pt; }}
QLabel#AppStatus[tone="warn"] {{ color: {AMBER}; }}
QLabel#AppStatus[tone="error"] {{ color: {TEXT_SUB}; }}

QLabel#Pill {{
    border-radius: 4px; font-size: 7.5pt; font-weight: 700; padding: 1px 6px;
}}
{_pill("installed", ACCENT)}
{_pill("update", AMBER)}
{_pill("beta", BLUE)}
{_pill("trial", ACCENT)}
{_pill("badge", TEXT_SUB)}
{_pill("offline", TEXT_SUB)}

/* ---- buttons: Primary > Secondary > Outline > Subtle -------------------- */
QPushButton {{
    border-radius: 8px; padding: 7px 16px; font-size: 9.5pt; font-weight: 600;
    min-width: 72px;
}}
QPushButton#Primary {{
    background: {ACCENT}; color: {BG}; border: none; font-weight: 700;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_DIM}; }}
QPushButton#Secondary {{
    background: transparent; color: {ACCENT}; border: 1.5px solid {ACCENT};
}}
QPushButton#Secondary:hover {{
    background: {_tint(ACCENT, 0.13)}; color: {ACCENT_HOVER}; border-color: {ACCENT_HOVER};
}}
QPushButton#Secondary:pressed {{ background: {_tint(ACCENT_DIM, 0.2)}; }}
QPushButton#Outline {{
    background: transparent; color: {TEXT}; border: 1px solid {BORDER_HI};
}}
QPushButton#Outline:hover {{ background: {SURFACE_HOVER}; border-color: {TEXT_MUTED}; }}
QPushButton#Subtle {{
    background: transparent; color: {TEXT_SUB}; border: 1px solid transparent;
}}
QPushButton#Subtle:hover {{ background: {_tint("#FFFFFF", 0.06)}; color: {TEXT}; }}
QPushButton:disabled, QPushButton#Primary:disabled, QPushButton#Secondary:disabled,
QPushButton#Outline:disabled, QPushButton#Subtle:disabled {{
    background: transparent; color: {TEXT_MUTED}; border: 1px solid {BORDER};
}}

/* ---- promo card -------------------------------------------------------- */
QFrame#PromoCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {_tint(ACCENT, 0.10)}, stop:1 {SURFACE});
    border: 1px solid {_tint(ACCENT, 0.25)};
    border-radius: 10px;
}}
QLabel#PromoKicker {{ color: {ACCENT}; font-size: 7.5pt; font-weight: 700; letter-spacing: 1.2px; }}
QLabel#PromoText {{ color: {TEXT}; font-size: 9.5pt; }}

/* ---- misc -------------------------------------------------------------- */
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_HI}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QProgressBar {{
    background-color: {BORDER}; border: none; border-radius: 3px; max-height: 6px;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}

QToolTip {{
    background: {SURFACE_HOVER}; color: {TEXT}; border: 1px solid {BORDER_HI};
    padding: 4px 8px; border-radius: 4px;
}}
QMessageBox {{ background: {SURFACE}; }}
QMessageBox QPushButton {{
    background: {ACCENT}; color: {BG}; border: none; font-weight: 700; min-width: 80px;
}}
"""
