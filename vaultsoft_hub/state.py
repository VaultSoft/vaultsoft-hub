"""Local persistence: which apps are installed, at which version, and where.

Lives in a JSON file under the OS's per-user data directory so the Hub itself
stays portable (no installer, no registry writes) while still remembering
state between runs.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from .models import InstalledState

STATE_FILENAME = "state.json"


def data_root() -> Path:
    """Per-user app-data directory, cross-platform, created if missing.

    Windows:  %LOCALAPPDATA%\\VaultSoft
    macOS:    ~/Library/Application Support/VaultSoft
    Linux:    ~/.local/share/VaultSoft   (dev/testing only — the shipped
              Hub targets Windows)
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    root = Path(base) / "VaultSoft"
    root.mkdir(parents=True, exist_ok=True)
    return root


def apps_dir() -> Path:
    d = data_root() / "Apps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path() -> Path:
    return data_root() / STATE_FILENAME


class StateStore:
    """Thin wrapper so the UI can hold one instance and call save() when it changes."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _state_path()
        self._data: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, app_id: str) -> Optional[InstalledState]:
        raw = self._data.get(app_id)
        if raw is None:
            return None
        return InstalledState(app_id=app_id, **raw)

    def set(self, installed: InstalledState) -> None:
        self._data[installed.app_id] = {
            "version": installed.version,
            "install_dir": installed.install_dir,
            "executable_path": installed.executable_path,
        }
        self.save()

    def remove(self, app_id: str) -> None:
        if app_id in self._data:
            del self._data[app_id]
            self.save()
