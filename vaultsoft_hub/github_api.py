"""Talks to the GitHub REST API to resolve each app's latest release.

Deliberately dependency-light: only `requests`. No GitHub token is required for
the request volume a single user's Hub generates (60 unauthenticated
requests/hour is comfortably enough for a handful of apps), but set the
VAULTSOFT_HUB_GH_TOKEN environment variable to a personal access token
(no scopes needed, just to raise the rate limit) if you ever hit 403s.
"""
from __future__ import annotations

import os
import re
from typing import Optional

import requests

from .models import ReleaseInfo

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


def normalize_version(tag_name: str) -> str:
    """'v1.2.3' -> '1.2.3'; leaves already-bare versions untouched."""
    return tag_name[1:] if tag_name.lower().startswith("v") else tag_name


def _version_key(version: str) -> tuple:
    """Best-effort sortable key for dotted numeric versions.

    "1.0.0-beta" sorts below "1.0.0": a suffix after the numbers marks a
    pre-release, and pre-releases of the same number compare by suffix.
    Tags with no leading number sort below every numbered one, by string.
    """
    match = re.match(r"(\d+(?:\.\d+)*)(.*)$", version.strip())
    if not match:
        return ((), 0, version)
    numbers = tuple(int(p) for p in match.group(1).split("."))
    suffix = match.group(2).lstrip("-_.+ ")
    return (numbers, 0 if suffix else 1, suffix)


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


def fetch_latest_release(
    repo: str, executable_hint: str = "", include_prereleases: bool = False
) -> ReleaseInfo:
    """Fetch the latest published release for `owner/repo`.

    GitHub's /releases/latest skips pre-releases, so an app whose only release
    is a beta (BatteryVault) would look unreleased. With include_prereleases
    the newest non-draft release of any kind is used instead.
    """
    if include_prereleases:
        url = f"{API_ROOT}/repos/{repo}/releases?per_page=10"
    else:
        url = f"{API_ROOT}/repos/{repo}/releases/latest"
    try:
        resp = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            raise GitHubApiError(f"{repo} has no published releases yet.")
        resp.raise_for_status()
        data = resp.json()
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise GitHubApiError("Couldn't reach GitHub. Check your internet connection.") from exc
    except (requests.RequestException, ValueError) as exc:
        raise GitHubApiError(f"Could not reach GitHub for {repo}: {exc}") from exc

    if include_prereleases:
        published = [r for r in data if isinstance(r, dict) and not r.get("draft")]
        if not published:
            raise GitHubApiError(f"{repo} has no published releases yet.")
        data = published[0]  # the API lists newest first

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
