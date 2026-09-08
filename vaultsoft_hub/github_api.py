"""Talks to the GitHub REST API to resolve manifest + latest releases.

Deliberately dependency-light: only `requests`. No GitHub token is required for
the request volume a single user's Hub generates (60 unauthenticated
requests/hour is comfortably enough for a handful of apps), but set the
VAULTSOFT_HUB_GH_TOKEN environment variable to a personal access token
(no scopes needed, just to raise the rate limit) if you ever hit 403s.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests

from .models import AppEntry, CrossPromo, Manifest, ReleaseInfo

API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT = 15


class GitHubApiError(RuntimeError):
    """Raised for any network/parse failure talking to GitHub."""


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("VAULTSOFT_HUB_GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_manifest(url: str) -> Manifest:
    """Fetch and parse manifest.json (app list + cross-promo block)."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        raise GitHubApiError(f"Could not load manifest from {url}: {exc}") from exc

    apps = [
        AppEntry(
            id=a["id"],
            name=a["name"],
            repo=a["repo"],
            category=a.get("category", "Other"),
            description=a.get("description", ""),
            homepage=a.get("homepage", ""),
            executable_hint=a.get("executable_hint", ""),
        )
        for a in data.get("apps", [])
    ]
    promo_data = data.get("cross_promo", {})
    cross_promo = CrossPromo(
        enabled=bool(promo_data.get("enabled", False)),
        text=promo_data.get("text", ""),
        url=promo_data.get("url", ""),
    )
    return Manifest(apps=apps, cross_promo=cross_promo)


def normalize_version(tag_name: str) -> str:
    """'v1.2.3' -> '1.2.3'; leaves already-bare versions untouched."""
    return tag_name[1:] if tag_name.lower().startswith("v") else tag_name


def _version_key(version: str) -> tuple:
    """Best-effort sortable key for dotted numeric versions.

    Falls back to treating the whole string as a single component so
    unconventional tags don't crash comparisons — they just compare as
    "newer than any parseable version" is NOT assumed; they sort by string.
    """
    parts = re.findall(r"\d+", version)
    if parts:
        return tuple(int(p) for p in parts)
    return (version,)


def is_newer(candidate: str, baseline: str) -> bool:
    """True if `candidate` version is newer than `baseline`."""
    if candidate == baseline:
        return False
    try:
        return _version_key(candidate) > _version_key(baseline)
    except TypeError:
        # Mixed types (numeric key vs string fallback) - can't compare safely.
        return candidate != baseline


def _pick_asset(assets: list[dict], executable_hint: str) -> Optional[dict]:
    """Choose the right release asset out of possibly several.

    Preference order: a .zip with "portable" in the name (matches VaultSoft's
    existing naming convention, e.g. WaveScout_v1.0.0_Portable.zip), then any
    .zip, then whatever's first.
    """
    if not assets:
        return None
    zips = [a for a in assets if a.get("name", "").lower().endswith(".zip")]
    for a in zips:
        if "portable" in a["name"].lower():
            return a
    if zips:
        return zips[0]
    return assets[0]


def fetch_latest_release(repo: str, executable_hint: str = "") -> ReleaseInfo:
    """Fetch the latest published release for `owner/repo`."""
    url = f"{API_ROOT}/repos/{repo}/releases/latest"
    try:
        resp = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            raise GitHubApiError(f"{repo} has no published releases yet.")
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise GitHubApiError(f"Could not reach GitHub for {repo}: {exc}") from exc

    asset = _pick_asset(data.get("assets", []), executable_hint)
    if asset is None:
        raise GitHubApiError(f"{repo}'s latest release has no downloadable asset.")

    tag_name = data.get("tag_name", "")
    return ReleaseInfo(
        tag_name=tag_name,
        version=normalize_version(tag_name),
        download_url=asset["browser_download_url"],
        asset_name=asset["name"],
        published_at=data.get("published_at", ""),
    )
