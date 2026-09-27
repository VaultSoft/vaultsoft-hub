"""One app's card in the Hub: icon, name + status pills, description, a status
line, and the single button whose label/behaviour changes with state
(Install -> Update -> Launch, or Open page / Retry).

Button tiers: Launch/Update = Primary, Install = Secondary, Open page =
Outline, Retry = Subtle. Status text is grey, or amber for an update, and is
never green: "installed" is shown by the pill, not by colouring text.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ..github_api import is_prerelease_version
from ..models import AppEntry
from .icons import app_icon
from .styles import repolish

ICON_TILE = 44
ICON_SIZE = 24
COMPACT_BELOW = 430  # card width (px) under which the button moves below the text


class AppCard(QFrame):
    install_requested = pyqtSignal(str)  # app_id
    update_requested = pyqtSignal(str)
    launch_requested = pyqtSignal(str)
    open_page_requested = pyqtSignal(str)
    retry_requested = pyqtSignal(str)

    def __init__(self, app: AppEntry, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("AppCard")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._mode = "checking"
        self._compact = False
        self._offline = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("AppIcon")
        self.icon_label.setFixedSize(ICON_TILE, ICON_TILE)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(app_icon(self.app, ICON_SIZE, self.devicePixelRatioF()))
        outer.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        self.text_col = QVBoxLayout()
        self.text_col.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_label = QLabel(self.app.name)
        name_label.setObjectName("AppName")
        name_row.addWidget(name_label)
        self.pill_row = QHBoxLayout()
        self.pill_row.setSpacing(6)
        name_row.addLayout(self.pill_row)
        name_row.addStretch(1)
        self.text_col.addLayout(name_row)

        desc_label = QLabel(self.app.description)
        desc_label.setObjectName("AppDescription")
        desc_label.setWordWrap(True)
        self.text_col.addWidget(desc_label)

        self.status_label = QLabel("Checking for updates…")
        self.status_label.setObjectName("AppStatus")
        # Errors can be long; unwrapped they'd widen the card past the window.
        self.status_label.setWordWrap(True)
        self.text_col.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        self.text_col.addWidget(self.progress)

        outer.addLayout(self.text_col, stretch=1)

        self.action_button = QPushButton("…")
        self.action_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.action_button.setMinimumWidth(104)
        self.action_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.action_button.clicked.connect(self._on_click)
        self.button_row = QHBoxLayout()  # used in compact mode
        self.button_row.setContentsMargins(0, 6, 0, 0)
        self.button_row.addStretch(1)
        outer.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        self._outer = outer

    @property
    def mode(self) -> str:
        """checking / install / update / launch / link / error"""
        return self._mode

    @property
    def offline(self) -> bool:
        """True if the last release check failed because GitHub was unreachable."""
        return self._mode == "error" and self._offline

    # ---- narrow windows ------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        compact = self.width() < COMPACT_BELOW
        if compact == self._compact:
            return
        self._compact = compact
        if compact:
            self._outer.removeWidget(self.action_button)
            self.button_row.insertWidget(0, self.action_button)
            self.text_col.addLayout(self.button_row)
        else:
            self.button_row.removeWidget(self.action_button)
            self.text_col.removeItem(self.button_row)
            self._outer.addWidget(self.action_button, alignment=Qt.AlignmentFlag.AlignVCenter)

    # ---- helpers ------------------------------------------------------------

    def _on_click(self) -> None:
        signal = {
            "install": self.install_requested,
            "update": self.update_requested,
            "launch": self.launch_requested,
            "link": self.open_page_requested,
            "error": self.retry_requested,
        }.get(self._mode)
        if signal is not None:
            signal.emit(self.app.id)

    def _set_button(self, text: str, tier: str, enabled: bool = True) -> None:
        self.action_button.setText(text)
        self.action_button.setObjectName(tier)
        self.action_button.setEnabled(enabled)
        repolish(self.action_button)

    def _set_status(self, text: str, tone: str = "") -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("tone", tone)
        repolish(self.status_label)

    def _set_pills(self, *pills: tuple[str, str]) -> None:
        """pills: (kind, text) pairs; kinds are styled in styles.py."""
        while self.pill_row.count():
            item = self.pill_row.takeAt(0)
            pill = item.widget()
            if pill:
                pill.setParent(None)  # detach now; deleteLater alone lags a frame
                pill.deleteLater()
        for kind, text in pills:
            pill = QLabel(text)
            pill.setObjectName("Pill")
            pill.setProperty("kind", kind)
            self.pill_row.addWidget(pill)

    def _badge_pill(self):
        """The apps.json badge, unless it's the plain "Free" every app has."""
        badge = self.app.badge.strip()
        if not badge or badge.lower() == "free":
            return None
        return ("trial" if "trial" in badge.lower() else "badge", badge)

    # ---- states -------------------------------------------------------------

    def set_checking(self) -> None:
        self._mode = "checking"
        self._set_pills()
        self._set_status("Checking for updates…")
        self._set_button("…", "Subtle", enabled=False)

    def set_error(self, message: str, offline: bool = False) -> None:
        # No per-card "Offline" pill: the window's status line shows one.
        self._mode = "error"
        self._offline = offline
        self._set_pills()
        self._set_status(message, "error")
        self._set_button("Retry", "Subtle")

    def set_link(self) -> None:
        """Apps the Hub doesn't install (e.g. ScribeVault): just point at the page."""
        self._mode = "link"
        badge = self._badge_pill()
        self._set_pills(*([badge] if badge else []))
        self._set_status("Opens in your browser")
        self._set_button("Open page", "Outline")

    def set_not_installed(self, latest_version: str, prerelease: bool = False) -> None:
        self._mode = "install"
        self._set_pills(*([("beta", "Beta")] if prerelease else []))
        self._set_status(f"Not installed · latest v{latest_version}")
        self._set_button("Install", "Secondary")

    def set_update_available(self, installed_version: str, latest_version: str) -> None:
        self._mode = "update"
        self._set_pills(("update", "Update available"))
        self._set_status(f"v{installed_version} installed → v{latest_version} available", "warn")
        self._set_button("Update", "Primary")

    def set_up_to_date(self, version: str) -> None:
        self._mode = "launch"
        pills = [("installed", "Installed ✓")]
        if is_prerelease_version(version):
            pills.append(("beta", "Beta"))
        self._set_pills(*pills)
        self._set_status(f"v{version} · up to date")
        self._set_button("Launch", "Primary")

    def set_installing(self, done: int, total: int) -> None:
        self.action_button.setEnabled(False)
        self.progress.setVisible(True)
        if total > 0:
            self.progress.setMaximum(total)
            self.progress.setValue(done)
            self._set_status(f"Downloading… {done * 100 // total}%")
        else:
            self.progress.setMaximum(0)  # size unknown: busy indicator
            self._set_status("Downloading…")

    def hide_progress(self) -> None:
        self.progress.setVisible(False)
