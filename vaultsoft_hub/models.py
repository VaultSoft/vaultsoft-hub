"""Plain data structures shared across the Hub."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppEntry:
    """One app as declared in manifest.json."""

    id: str
    name: str
    repo: str  # "Owner/Repo" on GitHub
    category: str
    description: str
    homepage: str = ""
    executable_hint: str = ""


@dataclass
class ReleaseInfo:
    """Resolved from the GitHub Releases API at runtime — never cached in the manifest."""

    tag_name: str
    version: str  # tag_name with a leading "v" stripped, if present
    download_url: str
    asset_name: str
    published_at: str = ""


@dataclass
class InstalledState:
    """Persisted locally per installed app."""

    app_id: str
    version: str
    install_dir: str
    executable_path: Optional[str] = None


@dataclass
class CrossPromo:
    enabled: bool = False
    text: str = ""
    url: str = ""


@dataclass
class Manifest:
    apps: list[AppEntry] = field(default_factory=list)
    cross_promo: CrossPromo = field(default_factory=CrossPromo)
