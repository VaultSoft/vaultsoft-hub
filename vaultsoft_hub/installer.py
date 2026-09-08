"""Download, extract, locate the executable, and launch an installed app."""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

from .models import AppEntry, InstalledState, ReleaseInfo
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


def install_or_update(
    app: AppEntry,
    release: ReleaseInfo,
    state: StateStore,
    on_progress: ProgressCallback = None,
) -> InstalledState:
    """Download `release`, replace any existing install of `app`, record state."""
    install_dir = apps_dir() / app.id
    tmp_zip = apps_dir() / f"_{app.id}_{release.version}.download"

    download_file(release.download_url, tmp_zip, on_progress)

    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    try:
        extract_zip(tmp_zip, install_dir)
    finally:
        tmp_zip.unlink(missing_ok=True)

    exe = find_executable(install_dir, app.executable_hint)
    installed = InstalledState(
        app_id=app.id,
        version=release.version,
        install_dir=str(install_dir),
        executable_path=str(exe) if exe else None,
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
