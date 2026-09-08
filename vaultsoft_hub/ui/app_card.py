"""One app's row in the Hub: name, description, status, and the single button
whose label/behaviour changes with state (Install -> Update available ->
Launch).
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ..models import AppEntry


class AppCard(QFrame):
    install_requested = pyqtSignal(str)  # app_id
    update_requested = pyqtSignal(str)
    launch_requested = pyqtSignal(str)

    def __init__(self, app: AppEntry, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("AppCard")
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name_label = QLabel(self.app.name)
        name_label.setObjectName("AppName")
        text_col.addWidget(name_label)

        desc_label = QLabel(self.app.description)
        desc_label.setObjectName("AppDescription")
        desc_label.setWordWrap(True)
        text_col.addWidget(desc_label)

        self.status_label = QLabel("Checking…")
        self.status_label.setObjectName("AppStatus")
        text_col.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        text_col.addWidget(self.progress)

        outer.addLayout(text_col, stretch=1)

        self.action_button = QPushButton("...")
        self.action_button.setFixedWidth(140)
        self.action_button.clicked.connect(self._on_click)
        outer.addWidget(self.action_button)

        self._mode = "checking"

    def _on_click(self) -> None:
        if self._mode == "install":
            self.install_requested.emit(self.app.id)
        elif self._mode == "update":
            self.update_requested.emit(self.app.id)
        elif self._mode == "launch":
            self.launch_requested.emit(self.app.id)

    def set_checking(self) -> None:
        self._mode = "checking"
        self.status_label.setText("Checking…")
        self.status_label.setProperty("state", "")
        self.action_button.setText("...")
        self.action_button.setEnabled(False)

    def set_error(self, message: str) -> None:
        self._mode = "error"
        self.status_label.setText(message)
        self.status_label.setProperty("state", "")
        self.action_button.setText("Retry")
        self.action_button.setEnabled(True)

    def set_not_installed(self, latest_version: str) -> None:
        self._mode = "install"
        self.status_label.setText(f"Not installed · latest v{latest_version}")
        self.status_label.setProperty("state", "")
        self.action_button.setText("Install")
        self.action_button.setEnabled(True)

    def set_update_available(self, installed_version: str, latest_version: str) -> None:
        self._mode = "update"
        self.status_label.setText(f"v{installed_version} installed → v{latest_version} available")
        self.status_label.setProperty("state", "update")
        self.action_button.setText("Update")
        self.action_button.setEnabled(True)

    def set_up_to_date(self, version: str) -> None:
        self._mode = "launch"
        self.status_label.setText(f"v{version} installed · up to date")
        self.status_label.setProperty("state", "installed")
        self.action_button.setText("Launch")
        self.action_button.setEnabled(True)

    def set_installing(self, done: int, total: int) -> None:
        self.action_button.setEnabled(False)
        self.progress.setVisible(True)
        if total > 0:
            self.progress.setMaximum(total)
            self.progress.setValue(done)
        else:
            # Unknown size - show indeterminate-ish by pulsing 0..100 isn't
            # worth the complexity here; just show "busy".
            self.progress.setMaximum(0)
        self.status_label.setText("Downloading…")

    def hide_progress(self) -> None:
        self.progress.setVisible(False)
