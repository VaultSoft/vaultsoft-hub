"""A small dark QSS theme matching the "clean desktop overlay" look already
used across VaultSoft apps (PulseMonitor etc). Centralised here so every
window/widget looks consistent without repeating colours everywhere.
"""

BG = "#121417"
SURFACE = "#1b1f24"
SURFACE_ALT = "#22272e"
BORDER = "#2a2f36"
TEXT = "#e6e9ec"
TEXT_MUTED = "#9aa4ae"
ACCENT = "#4da6ff"
ACCENT_HOVER = "#6bb6ff"
SUCCESS = "#3ddc97"
WARN = "#ffb454"

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 10.5pt;
}}

QMainWindow {{
    background-color: {BG};
}}

QFrame#AppCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#AppCard:hover {{
    border: 1px solid {ACCENT};
}}

QLabel#AppName {{
    font-size: 12pt;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#AppDescription {{
    color: {TEXT_MUTED};
}}

QLabel#AppStatus {{
    color: {TEXT_MUTED};
    font-size: 9pt;
}}

QLabel#AppStatus[state="update"] {{
    color: {WARN};
}}

QLabel#AppStatus[state="installed"] {{
    color: {SUCCESS};
}}

QPushButton {{
    background-color: {ACCENT};
    color: #0b0d10;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton:disabled {{
    background-color: {SURFACE_ALT};
    color: {TEXT_MUTED};
}}

QPushButton#SecondaryButton {{
    background-color: {SURFACE_ALT};
    color: {TEXT};
}}

QPushButton#SecondaryButton:hover {{
    background-color: {BORDER};
}}

QFrame#PromoBanner {{
    background-color: {SURFACE_ALT};
    border: 1px dashed {BORDER};
    border-radius: 8px;
}}

QLabel#PromoText {{
    color: {TEXT_MUTED};
}}

QScrollArea {{
    border: none;
}}

QProgressBar {{
    background-color: {SURFACE_ALT};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 4px;
}}
"""
