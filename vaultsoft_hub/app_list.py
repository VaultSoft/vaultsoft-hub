"""Loads the list of apps from the VaultSoft site's apps.json.

That file also builds the vaultsoft.co.uk homepage, and Hubs already out in the
wild read it, so it only ever gains fields: parse defensively and ignore
anything unknown.

Hub-only settings live in each app's optional "hub" value, which the site
ignores:
    {"exe": "PulseMonitor.exe"}   install from `repo`, launch that exe
    {"mode": "link"}              show the app, but only open its page
    false                         don't list it in the Hub
    missing / {}                  install from `repo`, guess the exe

The top-level "hub_promo" ({"enabled", "text", "url"}) is the banner at the
bottom of the window.

If the live file can't be loaded, the Hub falls back to the last good copy it
saved, then to the copy built into the exe, so it still works offline.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from .github_api import GitHubApiError
from .models import AppEntry, CrossPromo, Manifest
from .state import data_root

REQUEST_TIMEOUT = 15
CACHE_FILENAME = "apps.json"
# Snapshot of the site's apps.json at build time. PyInstaller bundles it next
# to this module (see build.spec), so the path works frozen and from source.
BUNDLED_PATH = Path(__file__).resolve().parent / "bundled_apps.json"


def parse_app_list(data: dict) -> Manifest:
    """Turn a decoded apps.json into a Manifest. Raises GitHubApiError if it isn't one."""
    if not isinstance(data, dict) or not isinstance(data.get("apps"), list):
        raise GitHubApiError("The app list is not in the expected format.")

    apps = []
    for a in data["apps"]:
        if not isinstance(a, dict) or not a.get("id") or not a.get("name"):
            continue
        hub = a.get("hub", {})
        if hub is False:
            continue
        if not isinstance(hub, dict):
            hub = {}
        repo = a.get("repo", "")
        homepage = a.get("link", "")
        mode = "link" if hub.get("mode") == "link" or not repo else "install"
        if mode == "link" and not homepage:
            continue  # nothing to install and nowhere to send people
        apps.append(
            AppEntry(
                id=a["id"],
                name=a["name"],
                repo=repo,
                category=a.get("category", "Other"),
                description=a.get("description", ""),
                homepage=homepage,
                executable_hint=hub.get("exe", "") or "",
                badge=a.get("badge", ""),
                mode=mode,
            )
        )
    promo = data.get("hub_promo")
    if not isinstance(promo, dict):
        promo = {}
    cross_promo = CrossPromo(
        enabled=bool(promo.get("enabled", False)),
        text=promo.get("text", "") or "",
        url=promo.get("url", "") or "",
    )
    return Manifest(apps=apps, cross_promo=cross_promo)


def _parse_text(text: str) -> Manifest:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise GitHubApiError(f"The app list is not valid JSON: {exc}") from exc
    return parse_app_list(data)


def _download(url: str) -> str:
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except requests.RequestException as exc:
        raise GitHubApiError(f"Could not load the app list from {url}: {exc}") from exc


def fetch_app_list(url: str) -> Manifest:
    """Download and parse apps.json, with no fallback."""
    return _parse_text(_download(url))


def load_app_list(
    url: str,
    cache_path: Optional[Path] = None,
    bundled_path: Path = BUNDLED_PATH,
) -> Manifest:
    """The live list if possible, else the saved copy, else the bundled one.

    A live list that parses is saved over the old copy. If all three fail, the
    live error is raised, since that's the one worth showing.
    """
    cache_path = cache_path or data_root() / CACHE_FILENAME
    try:
        text = _download(url)
        manifest = _parse_text(text)
    except GitHubApiError as live_error:
        try:
            manifest = _parse_text(cache_path.read_text(encoding="utf-8"))
            saved = datetime.fromtimestamp(cache_path.stat().st_mtime)
            manifest.source = "saved"
            manifest.saved_at = f"{saved.day} {saved:%b %Y}"
            return manifest
        except (OSError, GitHubApiError):
            pass
        try:
            manifest = _parse_text(bundled_path.read_text(encoding="utf-8"))
            manifest.source = "bundled"
            return manifest
        except (OSError, GitHubApiError):
            raise live_error from None

    try:
        cache_path.write_text(text, encoding="utf-8")
    except OSError:
        pass  # Not being able to save a copy mustn't stop the Hub working now.
    return manifest
