"""App icons and the VaultSoft logo as crisp pixmaps.

App icons are the website's own icons/*.svg, bundled in vaultsoft_hub/icons
(see build.spec). They're drawn in the site's cyan, so they're recoloured to
the apps' teal here. An app with no icon file gets a drawn tile with its
initial, so a new app added to apps.json never shows a blank.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

from ..models import AppEntry
from .styles import ACCENT

ICON_DIR = Path(__file__).resolve().parent.parent / "icons"
SITE_ICON_COLOUR = "#2AFFD5"


def _canvas(size: int, dpr: float) -> QPixmap:
    pm = QPixmap(round(size * dpr), round(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


def _svg_pixmap(path: Path, size: int, dpr: float):
    try:
        svg = path.read_text(encoding="utf-8")
    except OSError:
        return None
    renderer = QSvgRenderer(QByteArray(svg.replace(SITE_ICON_COLOUR, ACCENT).encode("utf-8")))
    if not renderer.isValid():
        return None
    pm = _canvas(size, dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


def _fallback_pixmap(name: str, size: int, dpr: float) -> QPixmap:
    pm = _canvas(size, dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(ACCENT))
    pen.setWidthF(1.6)
    p.setPen(pen)
    inset = size * 0.12
    p.drawRoundedRect(QRectF(inset, inset, size - 2 * inset, size - 2 * inset), size * 0.18, size * 0.18)
    font = QFont("Segoe UI")
    font.setPixelSize(max(8, int(size * 0.45)))
    font.setBold(True)
    p.setFont(font)
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, (name[:1] or "?").upper())
    p.end()
    return pm


def app_icon(app: AppEntry, size: int, dpr: float = 1.0) -> QPixmap:
    """The app's site icon, else a drawn tile with its initial."""
    for name in (app.icon, f"{app.id}.svg"):
        if name and name.lower().endswith(".svg"):
            pm = _svg_pixmap(ICON_DIR / Path(name).name, size, dpr)
            if pm is not None:
                return pm
    return _fallback_pixmap(app.name, size, dpr)


def logo(size: int, dpr: float = 1.0) -> QPixmap:
    """The VaultSoft logo from the window icon (icon.ico), else a teal dot."""
    icon = QApplication.windowIcon()
    if not icon.isNull():
        pm = icon.pixmap(QSize(size, size), dpr)
        if not pm.isNull():
            return pm
    pm = _canvas(size, dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(ACCENT))
    p.drawEllipse(QRectF(size * 0.3, size * 0.3, size * 0.4, size * 0.4))
    p.end()
    return pm
