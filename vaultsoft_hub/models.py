"""Plain data structures shared across the Hub."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppEntry:
    """One app, as listed in the site's apps.json."""

    id: str
    name: str
    repo: str  # "Owner/Repo" on GitHub
    category: str
    description: str
    homepage: str = ""
    executable_hint: str = ""
    badge: str = ""  # "Free", "Free trial", ...
    mode: str = "install"  # "install" from GitHub Releases, or "link" = just open homepage
    icon: str = ""  # file name in vaultsoft_hub/icons, from apps.json "icon"


@dataclass
class ReleaseInfo:
    """Resolved from the GitHub Releases API at runtime — never cached in the manifest."""

    tag_name: str
    version: str  # tag_name with a leading "v" stripped, if present
    download_url: str
    asset_name: str
    published_at: str = ""
    prerelease: bool = False


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
    categories: list[str] = field(default_factory=list)  # display order, as on the website
    source: str = "live"  # "live", "saved" (last good copy on this PC) or "bundled" (in the exe)
    saved_at: str = ""  # when the saved copy was fetched, e.g. "27 Sep 2026"
