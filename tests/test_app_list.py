import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub.app_list import fetch_app_list, parse_app_list
from vaultsoft_hub.github_api import GitHubApiError

# Shaped like the real https://vaultsoft.co.uk/apps.json.
SAMPLE = {
    "categories": ["System & PC", "Network"],
    "apps": [
        {
            "id": "pulsemonitor",
            "name": "PulseMonitor",
            "description": "Real-time monitoring.",
            "category": "System & PC",
            "badge": "Free",
            "link": "https://vaultsoft.github.io/PulseMonitor/",
            "repo": "VaultSoft/PulseMonitor",
            "released": "2026-04-16",
            "icon": "icons/pulsemonitor.svg",
            "featured": 2,
        },
        {
            "id": "wavescout",
            "name": "WaveScout",
            "description": "Wi-Fi analyser.",
            "category": "Network",
            "badge": "Free",
            "link": "https://vaultsoft.github.io/WaveScout/",
            "repo": "VaultSoft/WaveScout",
            "released": "2026-06-05",
            "some_future_field": {"anything": True},
        },
    ],
}


def _response(data=None, json_error=False):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    if json_error:
        resp.json.side_effect = json.JSONDecodeError("bad", "doc", 0)
    else:
        resp.json.return_value = data
    return resp


class ParseAppListTests(unittest.TestCase):
    def test_maps_site_fields_onto_apps(self):
        manifest = parse_app_list(SAMPLE)
        self.assertEqual([a.id for a in manifest.apps], ["pulsemonitor", "wavescout"])
        pm = manifest.apps[0]
        self.assertEqual(pm.name, "PulseMonitor")
        self.assertEqual(pm.repo, "VaultSoft/PulseMonitor")
        self.assertEqual(pm.category, "System & PC")
        self.assertEqual(pm.homepage, "https://vaultsoft.github.io/PulseMonitor/")  # from "link"
        self.assertEqual(pm.badge, "Free")

    def test_unknown_fields_are_ignored(self):
        # apps.json only ever gains fields; old Hubs must shrug them off.
        self.assertEqual(parse_app_list(SAMPLE).apps[1].id, "wavescout")

    def test_entries_without_id_or_name_are_skipped(self):
        data = {"apps": [{"name": "NoId"}, {"id": "noname"}, "junk", SAMPLE["apps"][0]]}
        self.assertEqual([a.id for a in parse_app_list(data).apps], ["pulsemonitor"])

    def test_wrong_shape_raises(self):
        for bad in ([], {"apps": {}}, {"nope": []}):
            with self.assertRaises(GitHubApiError):
                parse_app_list(bad)


class HubSettingsTests(unittest.TestCase):
    def _one(self, **fields):
        app = dict(SAMPLE["apps"][0], **fields)
        return parse_app_list({"apps": [app]}).apps

    def test_exe_becomes_the_executable_hint(self):
        (app,) = self._one(hub={"exe": "PulseMonitor.exe"})
        self.assertEqual(app.mode, "install")
        self.assertEqual(app.executable_hint, "PulseMonitor.exe")

    def test_missing_hub_block_means_install_and_guess_the_exe(self):
        (app,) = self._one()
        self.assertEqual(app.mode, "install")
        self.assertEqual(app.executable_hint, "")

    def test_link_mode(self):
        (app,) = self._one(id="scribevault", badge="Free trial", hub={"mode": "link"})
        self.assertEqual(app.mode, "link")
        self.assertEqual(app.badge, "Free trial")
        self.assertEqual(app.homepage, "https://vaultsoft.github.io/PulseMonitor/")

    def test_hub_false_is_not_listed(self):
        self.assertEqual(self._one(hub=False), [])

    def test_no_repo_falls_back_to_link_mode(self):
        (app,) = self._one(repo="")
        self.assertEqual(app.mode, "link")

    def test_no_repo_and_no_link_is_skipped(self):
        self.assertEqual(self._one(repo="", link=""), [])

    def test_unexpected_hub_value_is_treated_as_missing(self):
        (app,) = self._one(hub="yes please")
        self.assertEqual((app.mode, app.executable_hint), ("install", ""))


class FetchAppListTests(unittest.TestCase):
    @patch("vaultsoft_hub.app_list.requests.get")
    def test_fetches_and_parses(self, mock_get):
        mock_get.return_value = _response(SAMPLE)
        manifest = fetch_app_list("https://example.invalid/apps.json")
        self.assertEqual(len(manifest.apps), 2)

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_bad_json_raises_apierror(self, mock_get):
        mock_get.return_value = _response(json_error=True)
        with self.assertRaises(GitHubApiError):
            fetch_app_list("https://example.invalid/apps.json")


if __name__ == "__main__":
    unittest.main()
