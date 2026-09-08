"""Checks whether a newer Hub release exists. Does NOT auto-replace the running
executable (self-replacing a running .exe on Windows is fiddly and risky) —
instead it hands back a ReleaseInfo so the UI can prompt the user to download
and run the new build, same as any other app in the manifest.
"""
from __future__ import annotations

from typing import Optional

from . import SELF_REPO, __version__
from .github_api import GitHubApiError, fetch_latest_release, is_newer
from .models import ReleaseInfo


def check_for_update() -> Optional[ReleaseInfo]:
    """Return the newer ReleaseInfo if one exists, else None.

    Swallows GitHubApiError (e.g. offline, no releases yet) — self-update
    checks should never block the app from starting.
    """
    try:
        release = fetch_latest_release(SELF_REPO, executable_hint="VaultSoftHub.exe")
    except GitHubApiError:
        return None

    if is_newer(release.version, __version__):
        return release
    return None
