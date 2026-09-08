from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import MANIFEST_URL, __version__
from ..github_api import is_newer
from ..installer import InstallError, launch
from ..models import AppEntry, Manifest, ReleaseInfo
from ..state import StateStore
from .app_card import AppCard
from .workers import InstallWorker, ManifestWorker, ReleaseCheckWorker, SelfUpdateWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"VaultSoft Hub v{__version__}")
        self.resize(560, 640)

        self.state = StateStore()
        self.cards: dict[str, AppCard] = {}
        self.releases: dict[str, ReleaseInfo] = {}
        self._threads: list = []  # keep references so QThreads aren't GC'd mid-run

        self._build_shell()
        self._start_manifest_load()
        self._start_self_update_check()

    # ---- layout scaffolding -------------------------------------------------

    def _build_shell(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("VaultSoft Hub")
        title.setStyleSheet("font-size: 16pt; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self._start_manifest_load)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        self.status_line = QLabel("Loading your apps…")
        self.status_line.setStyleSheet("color: #9aa4ae;")
        root.addWidget(self.status_line)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        scroll.setWidget(self.list_container)
        root.addWidget(scroll, stretch=1)

        self.promo_banner = QFrame()
        self.promo_banner.setObjectName("PromoBanner")
        self.promo_banner.setVisible(False)
        promo_layout = QHBoxLayout(self.promo_banner)
        self.promo_label = QLabel("")
        self.promo_label.setObjectName("PromoText")
        self.promo_label.setWordWrap(True)
        promo_layout.addWidget(self.promo_label, stretch=1)
        self.promo_button = QPushButton("Open")
        self.promo_button.setObjectName("SecondaryButton")
        promo_layout.addWidget(self.promo_button)
        root.addWidget(self.promo_banner)

        self.setCentralWidget(central)

    # ---- manifest / status loading ------------------------------------------

    def _start_manifest_load(self) -> None:
        self.status_line.setText("Loading your apps…")
        self.refresh_button.setEnabled(False)
        worker = ManifestWorker(MANIFEST_URL)
        worker.succeeded.connect(self._on_manifest_loaded)
        worker.failed.connect(self._on_manifest_failed)
        worker.finished.connect(lambda: self._forget_thread(worker))
        self._threads.append(worker)
        worker.start()

    def _on_manifest_failed(self, message: str) -> None:
        self.status_line.setText(f"Couldn't load the app list: {message}")
        self.refresh_button.setEnabled(True)

    def _on_manifest_loaded(self, manifest: Manifest) -> None:
        self.refresh_button.setEnabled(True)
        self.status_line.setText(f"{len(manifest.apps)} apps · checking for updates…")
        self._render_cards(manifest.apps)
        self._configure_promo(manifest)
        for app in manifest.apps:
            self._check_release(app)

    def _render_cards(self, apps: list[AppEntry]) -> None:
        # Clear existing cards + the trailing stretch (simple approach - fine
        # for a handful of apps; re-fetching the whole manifest is rare).
        self.cards.clear()
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for app in apps:
            card = AppCard(app)
            card.set_checking()
            card.install_requested.connect(self._on_install_clicked)
            card.update_requested.connect(self._on_install_clicked)
            card.launch_requested.connect(self._on_launch_clicked)
            self.list_layout.addWidget(card)
            self.cards[app.id] = card
            self._apply_known_state(app, card)
        self.list_layout.addStretch(1)

    def _apply_known_state(self, app: AppEntry, card: AppCard) -> None:
        installed = self.state.get(app.id)
        if installed:
            card.set_up_to_date(installed.version)  # provisional until release check lands

    def _configure_promo(self, manifest: Manifest) -> None:
        promo = manifest.cross_promo
        if not promo.enabled or not promo.text:
            self.promo_banner.setVisible(False)
            return
        self.promo_label.setText(promo.text)
        self.promo_banner.setVisible(True)
        try:
            self.promo_button.clicked.disconnect()
        except TypeError:
            pass
        self.promo_button.clicked.connect(lambda: webbrowser.open(promo.url))

    def _check_release(self, app: AppEntry) -> None:
        worker = ReleaseCheckWorker(app)
        worker.resolved.connect(self._on_release_resolved)
        worker.failed.connect(self._on_release_failed)
        worker.finished.connect(lambda: self._forget_thread(worker))
        self._threads.append(worker)
        worker.start()

    def _on_release_failed(self, app_id: str, message: str) -> None:
        card = self.cards.get(app_id)
        if card:
            card.set_error(message)

    def _on_release_resolved(self, app_id: str, release: ReleaseInfo) -> None:
        self.releases[app_id] = release
        card = self.cards.get(app_id)
        if not card:
            return
        installed = self.state.get(app_id)
        if installed is None:
            card.set_not_installed(release.version)
        elif is_newer(release.version, installed.version):
            card.set_update_available(installed.version, release.version)
        else:
            card.set_up_to_date(installed.version)

    # ---- install / update / launch ------------------------------------------

    def _on_install_clicked(self, app_id: str) -> None:
        release = self.releases.get(app_id)
        card = self.cards.get(app_id)
        if release is None or card is None:
            return
        app = self._find_app(app_id)
        if app is None:
            return

        card.set_installing(0, 0)
        worker = InstallWorker(app, release, self.state)
        worker.progress.connect(self._on_install_progress)
        worker.succeeded.connect(self._on_install_succeeded)
        worker.failed.connect(self._on_install_failed)
        worker.finished.connect(lambda: self._forget_thread(worker))
        self._threads.append(worker)
        worker.start()

    def _on_install_progress(self, app_id: str, done: int, total: int) -> None:
        card = self.cards.get(app_id)
        if card:
            card.set_installing(done, total)

    def _on_install_succeeded(self, app_id: str, installed) -> None:
        card = self.cards.get(app_id)
        if card:
            card.hide_progress()
            card.set_up_to_date(installed.version)

    def _on_install_failed(self, app_id: str, message: str) -> None:
        card = self.cards.get(app_id)
        if card:
            card.hide_progress()
            card.set_error(message)
        QMessageBox.warning(self, "Install failed", message)

    def _on_launch_clicked(self, app_id: str) -> None:
        installed = self.state.get(app_id)
        if not installed:
            return
        try:
            launch(installed)
        except InstallError as exc:
            QMessageBox.warning(self, "Couldn't launch", str(exc))

    # ---- self-update ---------------------------------------------------------

    def _start_self_update_check(self) -> None:
        worker = SelfUpdateWorker()
        worker.found.connect(self._on_self_update_found)
        worker.finished.connect(lambda: self._forget_thread(worker))
        self._threads.append(worker)
        worker.start()

    def _on_self_update_found(self, release: ReleaseInfo) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Update available")
        box.setText(
            f"A newer VaultSoft Hub is available (v{release.version}). "
            "Download it now?"
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            webbrowser.open(release.download_url)

    # ---- helpers ---------------------------------------------------------

    def _find_app(self, app_id: str) -> AppEntry | None:
        card = self.cards.get(app_id)
        return card.app if card else None

    def _forget_thread(self, worker) -> None:
        if worker in self._threads:
            self._threads.remove(worker)
