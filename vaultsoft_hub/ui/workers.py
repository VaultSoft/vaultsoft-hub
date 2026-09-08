"""Background QThread workers so network/disk I/O never blocks the UI thread."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from .. import self_update
from ..github_api import GitHubApiError, fetch_latest_release, fetch_manifest
from ..installer import InstallError, install_or_update
from ..models import AppEntry, Manifest, ReleaseInfo
from ..state import StateStore


class ManifestWorker(QThread):
    succeeded = pyqtSignal(object)  # Manifest
    failed = pyqtSignal(str)

    def __init__(self, manifest_url: str, parent=None):
        super().__init__(parent)
        self.manifest_url = manifest_url

    def run(self) -> None:
        try:
            manifest = fetch_manifest(self.manifest_url)
        except GitHubApiError as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(manifest)


class ReleaseCheckWorker(QThread):
    """Resolves the latest release for one app."""

    resolved = pyqtSignal(str, object)  # app_id, ReleaseInfo
    failed = pyqtSignal(str, str)  # app_id, message

    def __init__(self, app: AppEntry, parent=None):
        super().__init__(parent)
        self.app = app

    def run(self) -> None:
        try:
            release = fetch_latest_release(self.app.repo, self.app.executable_hint)
        except GitHubApiError as exc:
            self.failed.emit(self.app.id, str(exc))
            return
        self.resolved.emit(self.app.id, release)


class InstallWorker(QThread):
    progress = pyqtSignal(str, int, int)  # app_id, done, total
    succeeded = pyqtSignal(str, object)  # app_id, InstalledState
    failed = pyqtSignal(str, str)  # app_id, message

    def __init__(self, app: AppEntry, release: ReleaseInfo, state: StateStore, parent=None):
        super().__init__(parent)
        self.app = app
        self.release = release
        self.state = state

    def run(self) -> None:
        try:
            installed = install_or_update(
                self.app,
                self.release,
                self.state,
                on_progress=lambda done, total: self.progress.emit(self.app.id, done, total),
            )
        except InstallError as exc:
            self.failed.emit(self.app.id, str(exc))
            return
        self.succeeded.emit(self.app.id, installed)


class SelfUpdateWorker(QThread):
    found = pyqtSignal(object)  # ReleaseInfo
    none_found = pyqtSignal()

    def run(self) -> None:
        release: Optional[ReleaseInfo] = self_update.check_for_update()
        if release:
            self.found.emit(release)
        else:
            self.none_found.emit()
