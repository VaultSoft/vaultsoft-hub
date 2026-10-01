"""Download, extract, locate the executable, and launch an installed app."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

from ._vendor.vaultsoft_kit.safe_delete import CleanupOutcome, safe_delete_path, validate_cleanup_path
from .models import AppEntry, InstalledState, ReleaseInfo, is_valid_app_id
from .state import StateStore, apps_dir

REQUEST_TIMEOUT = 30
DOWNLOAD_CHUNK = 1024 * 256

ProgressCallback = Optional[Callable[[int, int], None]]  # (bytes_done, bytes_total)


class InstallError(RuntimeError):
    pass


def download_file(url: str, dest: Path, on_progress: ProgressCallback = None) -> None:
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if on_progress:
                        on_progress(done, total)
    except requests.RequestException as exc:
        raise InstallError(f"Download failed: {exc}") from exc


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
    except zipfile.BadZipFile as exc:
        raise InstallError(f"Downloaded file isn't a valid zip: {exc}") from exc


def find_executable(root: Path, executable_hint: str = "") -> Optional[Path]:
    """Locate the app's .exe inside an extracted (possibly nested) folder.

    Portable zips sometimes wrap contents in a single subfolder. We check the
    hinted filename first (exact, case-insensitive), then fall back to "the
    only .exe in the tree" heuristic.
    """
    candidates = list(root.rglob("*.exe"))
    if not candidates:
        return None

    if executable_hint:
        hint_lower = executable_hint.lower()
        for c in candidates:
            if c.name.lower() == hint_lower:
                return c

    if len(candidates) == 1:
        return candidates[0]

    # Multiple .exe with no hint match - prefer one at the shallowest depth
    # whose stem isn't an obvious uninstaller/helper.
    noisy = {"unins000", "uninstall", "uninstaller", "setup", "vcredist"}
    filtered = [c for c in candidates if c.stem.lower() not in noisy]
    pool = filtered or candidates
    return min(pool, key=lambda p: len(p.relative_to(root).parts))


def _issues(outcome: CleanupOutcome) -> list[str]:
    return [f"{r.target}: {r.error}" for r in outcome.blocked + outcome.failed]


def _remove_set_aside_copies(root: Path, app_id: str) -> CleanupOutcome:
    """Delete old versions earlier updates set aside, if they can be removed safely."""
    outcome = CleanupOutcome()
    for old in sorted(root.glob(f"_{app_id}.old-*")):
        outcome.add(safe_delete_path(old, approved_roots=[root], category=app_id))
    return outcome


def install_or_update(
    app: AppEntry,
    release: ReleaseInfo,
    state: StateStore,
    on_progress: ProgressCallback = None,
) -> InstalledState:
    """Download `release`, replace any existing install of `app`, record state.

    The old version is never deleted in place. It is renamed aside first, so a
    running app (locked files) stops the update before anything changes, and a
    failed extract can be put back. The set-aside copy is then removed with the
    kit's safe delete, which never follows junctions or symlinks and stays inside
    the Apps folder; anything it can't remove safely is left where it is, listed
    in the result's cleanup_issues, and tried again on the next update.
    """
    if not is_valid_app_id(app.id):
        raise InstallError(f"Refusing to install {app.name}: its id {app.id!r} isn't a safe folder name.")
    root = apps_dir()
    install_dir = root / app.id

    # The Apps folder and the app's folder must be real folders, not links elsewhere.
    target = install_dir if os.path.lexists(install_dir) else root
    check = validate_cleanup_path(target, [root], allow_root=True)
    if not check.ok:
        raise InstallError(f"Couldn't install {app.name} safely ({check.reason}). Nothing was changed.")

    cleanup = _remove_set_aside_copies(root, app.id)
    safe_version = re.sub(r"[^0-9A-Za-z.+-]", "_", release.version) or "download"
    tmp_zip = root / f"_{app.id}_{safe_version}.download"
    download_file(release.download_url, tmp_zip, on_progress)

    aside: Optional[Path] = None
    try:
        if os.path.lexists(install_dir):
            aside = root / f"_{app.id}.old-{time.time_ns()}"
            try:
                os.rename(install_dir, aside)
            except OSError as exc:
                raise InstallError(
                    f"Couldn't replace {app.name}: close it if it's running, then try again. "
                    f"Nothing was changed. ({exc.strerror or exc})"
                ) from exc
        install_dir.mkdir(parents=True)
        try:
            extract_zip(tmp_zip, install_dir)
        except InstallError:
            partial = safe_delete_path(install_dir, approved_roots=[root], category=app.id)
            if aside is not None and partial.deleted:
                os.rename(aside, install_dir)
            raise
    finally:
        tmp_zip.unlink(missing_ok=True)

    if aside is not None:
        cleanup.add(safe_delete_path(aside, approved_roots=[root], category=app.id))

    exe = find_executable(install_dir, app.executable_hint)
    installed = InstalledState(
        app_id=app.id,
        version=release.version,
        install_dir=str(install_dir),
        executable_path=str(exe) if exe else None,
        cleanup_issues=_issues(cleanup),
    )
    state.set(installed)
    return installed


def launch(installed: InstalledState) -> None:
    if not installed.executable_path:
        raise InstallError("No executable was found for this app after install.")
    exe = Path(installed.executable_path)
    if not exe.exists():
        raise InstallError(f"Expected executable is missing: {exe}")

    if sys.platform == "win32":
        subprocess.Popen([str(exe)], cwd=str(exe.parent))
    else:
        # Dev/testing on non-Windows: best effort, won't actually run a .exe.
        subprocess.Popen([str(exe)], cwd=str(exe.parent))


def uninstall(app_id: str, state: StateStore) -> None:
    installed = state.get(app_id)
    if installed and Path(installed.install_dir).exists():
        shutil.rmtree(installed.install_dir, ignore_errors=True)
    state.remove(app_id)
