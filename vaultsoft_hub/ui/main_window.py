from __future__ import annotations

import webbrowser
from urllib.parse import urlparse

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
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

from .. import APPS_URL, __version__
from ..github_api import is_newer
from ..installer import InstallError, launch
from ..models import AppEntry, Manifest, ReleaseInfo
from ..state import StateStore
from .app_card import AppCard
from .icons import logo
from .workers import InstallWorker, ManifestWorker, ReleaseCheckWorker, SelfUpdateWorker

NARROW_BELOW = 480  # window width (px) under which the header drops "by VaultSoft"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"VaultSoft Hub v{__version__}")
        self.resize(580, 700)
        self.setMinimumWidth(340)

        self.state = StateStore()
        self.cards: dict[str, AppCard] = {}
        self.releases: dict[str, ReleaseInfo] = {}
        self._manifest: Manifest | None = None
        self._pending: set[str] = set()  # app ids whose release check hasn't landed
        self._threads: list = []  # keep references so QThreads aren't GC'd mid-run

        self._build_shell()
        self._start_manifest_load()
        self._start_self_update_check()

    # ---- layout scaffolding -------------------------------------------------

    def _build_shell(self) -> None:
        central = QWidget()
        central.setObjectName("Central")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar: logo, name, "by VaultSoft", version pill, Refresh.
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(64)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 0, 16, 0)
        h.setSpacing(10)
        logo_label = QLabel()
        logo_label.setPixmap(logo(28, self.devicePixelRatioF()))
        logo_label.setFixedSize(28, 28)
        h.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("VaultSoft Hub")
        title.setObjectName("Title")
        h.addWidget(title, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.brand_label = QLabel("by VaultSoft")
        self.brand_label.setObjectName("Brand")
        h.addWidget(self.brand_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        h.addSpacing(2)
        version = QLabel(f"v{__version__}")
        version.setObjectName("Version")
        h.addWidget(version, alignment=Qt.AlignmentFlag.AlignVCenter)
        h.addStretch(1)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("Outline")
        self.refresh_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_button.clicked.connect(self._start_manifest_load)
        h.addWidget(self.refresh_button)
        root.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(16, 14, 16, 16)
        body.setSpacing(12)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(4, 0, 4, 0)
        status_row.setSpacing(8)
        self.status_pill = QLabel("Offline")
        self.status_pill.setObjectName("Pill")
        self.status_pill.setProperty("kind", "offline")
        self.status_pill.setVisible(False)
        status_row.addWidget(self.status_pill, alignment=Qt.AlignmentFlag.AlignTop)
        self.status_line = QLabel("Loading your apps…")
        self.status_line.setObjectName("StatusLine")
        self.status_line.setWordWrap(True)
        status_row.addWidget(self.status_line, stretch=1)
        body.addLayout(status_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName("Viewport")
        self.list_container = QWidget()
        self.list_container.setObjectName("ListContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        scroll.setWidget(self.list_container)
        body.addWidget(scroll, stretch=1)

        # Cross-promo card (text and link from apps.json's hub_promo).
        self.promo_card = QFrame()
        self.promo_card.setObjectName("PromoCard")
        self.promo_card.setVisible(False)
        p = QHBoxLayout(self.promo_card)
        p.setContentsMargins(16, 12, 14, 12)
        p.setSpacing(14)
        promo_text_col = QVBoxLayout()
        promo_text_col.setSpacing(2)
        self.promo_kicker = QLabel("")
        self.promo_kicker.setObjectName("PromoKicker")
        promo_text_col.addWidget(self.promo_kicker)
        self.promo_label = QLabel("")
        self.promo_label.setObjectName("PromoText")
        self.promo_label.setWordWrap(True)
        promo_text_col.addWidget(self.promo_label)
        p.addLayout(promo_text_col, stretch=1)
        self.promo_button = QPushButton("Learn more")
        self.promo_button.setObjectName("Secondary")
        self.promo_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        p.addWidget(self.promo_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        body.addWidget(self.promo_card)

        root.addLayout(body, stretch=1)
        self.setCentralWidget(central)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.brand_label.setVisible(self.width() >= NARROW_BELOW)

    # ---- manifest / status loading ------------------------------------------

    def _start_manifest_load(self) -> None:
        self.status_pill.setVisible(False)
        self.status_line.setText("Loading your apps…")
        self.refresh_button.setEnabled(False)
        worker = ManifestWorker(APPS_URL)
        worker.succeeded.connect(self._on_manifest_loaded)
        worker.failed.connect(self._on_manifest_failed)
        worker.finished.connect(lambda: self._forget_thread(worker))
        self._threads.append(worker)
        worker.start()

    def _on_manifest_failed(self, message: str) -> None:
        self.status_pill.setVisible(True)
        self.status_line.setText(f"Couldn't load the app list. {message}")
        self.refresh_button.setEnabled(True)

    def _on_manifest_loaded(self, manifest: Manifest) -> None:
        self._manifest = manifest
        self.refresh_button.setEnabled(True)
        self._render_cards(manifest)
        self._configure_promo(manifest)
        self._pending = {a.id for a in manifest.apps if a.mode == "install"}
        self._update_status()
        for app in manifest.apps:
            if app.mode == "install":
                self._check_release(app)

    def _update_status(self) -> None:
        """One line under the header: offline notice, progress, or a summary."""
        m = self._manifest
        if m is None:
            return
        n = len(m.apps)
        apps = f"{n} app" if n == 1 else f"{n} apps"
        if m.source in ("saved", "bundled"):
            where = f"the list saved on {m.saved_at}" if m.source == "saved" else "the list built into this Hub"
            self.status_pill.setVisible(True)
            self.status_line.setText(f"Showing {where} · {apps}")
            return
        if self._pending:
            self.status_pill.setVisible(False)
            self.status_line.setText(f"{apps} · checking for updates…")
            return
        # List is live but GitHub isn't: cards have no pill, so flag it here.
        offline = any(c.offline for c in self.cards.values())
        self.status_pill.setVisible(offline)
        if offline:
            self.status_line.setText(f"{apps} · couldn't reach GitHub to check for updates")
            return
        updates = sum(1 for c in self.cards.values() if c.mode == "update")
        if updates:
            self.status_line.setText(f"{apps} · {updates} update{'s' if updates > 1 else ''} available")
        else:
            self.status_line.setText(apps)

    def _render_cards(self, manifest: Manifest) -> None:
        # Clear existing cards, headings and the trailing stretch (simple
        # approach - fine for a handful of apps; re-fetching the list is rare).
        self.cards.clear()
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Category headings in the website's order.
        order = manifest.categories or []
        groups: dict[str, list[AppEntry]] = {}
        for app in manifest.apps:
            groups.setdefault(app.category, []).append(app)
        ordered = [c for c in order if c in groups] + [c for c in groups if c not in order]

        for category in ordered:
            heading = QLabel(category.upper())
            heading.setObjectName("GroupTitle")
            self.list_layout.addWidget(heading)
            for app in groups[category]:
                card = AppCard(app)
                card.set_checking()
                card.install_requested.connect(self._on_install_clicked)
                card.update_requested.connect(self._on_install_clicked)
                card.launch_requested.connect(self._on_launch_clicked)
                card.open_page_requested.connect(self._on_open_page_clicked)
                card.retry_requested.connect(self._on_retry_clicked)
                self.list_layout.addWidget(card)
                self.cards[app.id] = card
                self._apply_known_state(app, card)
        self.list_layout.addStretch(1)

    def _apply_known_state(self, app: AppEntry, card: AppCard) -> None:
        if app.mode == "link":
            card.set_link()
            return
        installed = self.state.get(app.id)
        if installed:
            card.set_up_to_date(installed.version)  # provisional until release check lands

    def _configure_promo(self, manifest: Manifest) -> None:
        promo = manifest.cross_promo
        if not promo.enabled or not promo.text:
            self.promo_card.setVisible(False)
            return
        host = urlparse(promo.url).netloc.removeprefix("www.")
        self.promo_kicker.setText(host.upper())
        self.promo_kicker.setVisible(bool(host))
        self.promo_label.setText(promo.text)
        self.promo_card.setVisible(True)
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

    def _on_release_failed(self, app_id: str, message: str, offline: bool) -> None:
        card = self.cards.get(app_id)
        if card:
            card.set_error(message, offline)
        self._pending.discard(app_id)
        self._update_status()

    def _on_release_resolved(self, app_id: str, release: ReleaseInfo) -> None:
        self.releases[app_id] = release
        self._pending.discard(app_id)
        card = self.cards.get(app_id)
        if card:
            installed = self.state.get(app_id)
            if installed is None:
                card.set_not_installed(release.version, release.prerelease)
            elif is_newer(release.version, installed.version):
                card.set_update_available(installed.version, release.version)
            else:
                card.set_up_to_date(installed.version)
        self._update_status()

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
        self._update_status()

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

    def _on_retry_clicked(self, app_id: str) -> None:
        app = self._find_app(app_id)
        card = self.cards.get(app_id)
        if app and card:
            card.set_checking()
            self._pending.add(app_id)
            self._update_status()
            self._check_release(app)

    def _on_open_page_clicked(self, app_id: str) -> None:
        app = self._find_app(app_id)
        if app and app.homepage:
            webbrowser.open(app.homepage)

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
