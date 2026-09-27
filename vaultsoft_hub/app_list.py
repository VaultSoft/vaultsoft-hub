"""Loads the list of apps from the VaultSoft site's apps.json.

That file also builds the vaultsoft.co.uk homepage, and Hubs already out in the
wild read it, so it only ever gains fields: parse defensively and ignore
anything unknown.
"""
from __future__ import annotations

import json

import requests

from .github_api import GitHubApiError
from .models import AppEntry, Manifest

REQUEST_TIMEOUT = 15


def parse_app_list(data: dict) -> Manifest:
    """Turn a decoded apps.json into a Manifest. Raises GitHubApiError if it isn't one."""
    if not isinstance(data, dict) or not isinstance(data.get("apps"), list):
        raise GitHubApiError("The app list is not in the expected format.")

    apps = []
    for a in data["apps"]:
        if not isinstance(a, dict) or not a.get("id") or not a.get("name"):
            continue
        apps.append(
            AppEntry(
                id=a["id"],
                name=a["name"],
                repo=a.get("repo", ""),
                category=a.get("category", "Other"),
                description=a.get("description", ""),
                homepage=a.get("link", ""),
                badge=a.get("badge", ""),
            )
        )
    return Manifest(apps=apps)


def fetch_app_list(url: str) -> Manifest:
    """Download and parse apps.json."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise GitHubApiError(f"Could not load the app list from {url}: {exc}") from exc
    return parse_app_list(data)
