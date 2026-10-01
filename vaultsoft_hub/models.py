"""Plain data structures shared across the Hub."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# An app's id names its folder under the Hub's Apps folder, so it must be a plain
# lowercase slug: no separators, no "..", no drive letters, nothing to escape with.
APP_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")


def is_valid_app_id(app_id: object) -> bool:
    return isinstance(app_id, str) and APP_ID_PATTERN.fullmatch(app_id) is not None


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
    # Not saved: anything from the old version an update couldn't remove safely.
    cleanup_issues: list[str] = field(default_factory=list)


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
