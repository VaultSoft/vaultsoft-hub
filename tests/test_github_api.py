import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub.github_api import (
    GitHubApiError,
    fetch_latest_release,
    fetch_manifest,
    is_newer,
    normalize_version,
)


class VersionComparisonTests(unittest.TestCase):
    def test_normalize_version_strips_leading_v(self):
        self.assertEqual(normalize_version("v1.2.3"), "1.2.3")
        self.assertEqual(normalize_version("1.2.3"), "1.2.3")

    def test_is_newer_basic(self):
        self.assertTrue(is_newer("1.2.0", "1.1.9"))
        self.assertFalse(is_newer("1.1.9", "1.2.0"))
        self.assertFalse(is_newer("1.0.0", "1.0.0"))

    def test_is_newer_handles_different_segment_counts(self):
        self.assertTrue(is_newer("1.2.1", "1.2"))
        self.assertFalse(is_newer("1.2", "1.2.1"))

    def test_is_newer_falls_back_gracefully_on_unparseable_tags(self):
        # Should not raise even if a tag has no digits at all.
        self.assertFalse(is_newer("latest", "latest"))
        self.assertTrue(is_newer("latest", "stable") or True)  # just must not raise


class FetchManifestTests(unittest.TestCase):
    @patch("vaultsoft_hub.github_api.requests.get")
    def test_parses_apps_and_cross_promo(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "apps": [
                {
                    "id": "wavescout",
                    "name": "WaveScout",
                    "repo": "VaultSoft/WaveScout",
                    "description": "WiFi analyser",
                }
            ],
            "cross_promo": {"enabled": True, "text": "Try StarPing", "url": "https://starping.co.uk"},
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        manifest = fetch_manifest("https://example.invalid/manifest.json")

        self.assertEqual(len(manifest.apps), 1)
        self.assertEqual(manifest.apps[0].id, "wavescout")
        self.assertEqual(manifest.apps[0].category, "Other")  # default applied
        self.assertTrue(manifest.cross_promo.enabled)
        self.assertEqual(manifest.cross_promo.url, "https://starping.co.uk")

    @patch("vaultsoft_hub.github_api.requests.get")
    def test_bad_json_raises_apierror(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.side_effect = json.JSONDecodeError("bad", "doc", 0)
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        with self.assertRaises(GitHubApiError):
            fetch_manifest("https://example.invalid/manifest.json")


class FetchLatestReleaseTests(unittest.TestCase):
    @patch("vaultsoft_hub.github_api.requests.get")
    def test_prefers_portable_zip_asset(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "tag_name": "v1.0.1",
            "published_at": "2026-01-01T00:00:00Z",
            "assets": [
                {"name": "source.zip", "browser_download_url": "https://x/source.zip"},
                {
                    "name": "WaveScout_v1.0.1_Portable.zip",
                    "browser_download_url": "https://x/portable.zip",
                },
            ],
        }
        mock_get.return_value = mock_resp

        release = fetch_latest_release("VaultSoft/WaveScout")

        self.assertEqual(release.version, "1.0.1")
        self.assertEqual(release.asset_name, "WaveScout_v1.0.1_Portable.zip")
        self.assertEqual(release.download_url, "https://x/portable.zip")

    @patch("vaultsoft_hub.github_api.requests.get")
    def test_404_raises_apierror(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with self.assertRaises(GitHubApiError):
            fetch_latest_release("VaultSoft/NoReleasesYet")

    @patch("vaultsoft_hub.github_api.requests.get")
    def test_no_assets_raises_apierror(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"tag_name": "v1.0.0", "assets": []}
        mock_get.return_value = mock_resp

        with self.assertRaises(GitHubApiError):
            fetch_latest_release("VaultSoft/Empty")


if __name__ == "__main__":
    unittest.main()
