import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub.app_list import BUNDLED_PATH, fetch_app_list, load_app_list, parse_app_list
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


def _response(data=None, text=None):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.text = text if text is not None else json.dumps(data)
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

    def test_fileflow_entry_from_the_readme_installs_and_launches_its_exe(self):
        entry = {
            "id": "fileflow",
            "name": "FileFlow",
            "description": "Preview, organise and safely undo file moves.",
            "category": "System & PC",
            "badge": "Free",
            "repo": "VaultSoft/FileFlow",
            "icon": "icons/fileflow.svg",
            "hub": {"exe": "FileFlow.exe"},
        }
        app = parse_app_list({"apps": [entry]}).apps[0]
        self.assertEqual((app.mode, app.executable_hint, app.icon), ("install", "FileFlow.exe", "fileflow.svg"))
        self.assertEqual(app.repo, "VaultSoft/FileFlow")

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


class CategoryAndIconTests(unittest.TestCase):
    def test_categories_follow_the_site_order_then_new_ones(self):
        data = {"categories": ["Network", "System & PC"], "apps": SAMPLE["apps"] + [
            dict(SAMPLE["apps"][0], id="x", category="Brand New")]}
        self.assertEqual(parse_app_list(data).categories, ["Network", "System & PC", "Brand New"])

    def test_icon_is_reduced_to_a_file_name(self):
        self.assertEqual(parse_app_list(SAMPLE).apps[0].icon, "pulsemonitor.svg")
        self.assertEqual(parse_app_list(SAMPLE).apps[1].icon, "")


class FetchAppListTests(unittest.TestCase):
    @patch("vaultsoft_hub.app_list.requests.get")
    def test_fetches_and_parses(self, mock_get):
        mock_get.return_value = _response(SAMPLE)
        manifest = fetch_app_list("https://example.invalid/apps.json")
        self.assertEqual(len(manifest.apps), 2)

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_bad_json_raises_apierror(self, mock_get):
        mock_get.return_value = _response(text="{not json")
        with self.assertRaises(GitHubApiError):
            fetch_app_list("https://example.invalid/apps.json")


class HubPromoTests(unittest.TestCase):
    def test_hub_promo_becomes_the_banner(self):
        promo = {"enabled": True, "text": "Try StarPing", "url": "https://starping.co.uk"}
        manifest = parse_app_list(dict(SAMPLE, hub_promo=promo))
        self.assertTrue(manifest.cross_promo.enabled)
        self.assertEqual(manifest.cross_promo.text, "Try StarPing")
        self.assertEqual(manifest.cross_promo.url, "https://starping.co.uk")

    def test_missing_or_odd_hub_promo_means_no_banner(self):
        for promo in (None, False, "on", []):
            data = dict(SAMPLE) if promo is None else dict(SAMPLE, hub_promo=promo)
            self.assertFalse(parse_app_list(data).cross_promo.enabled)

    def test_the_real_bundled_copy_has_the_starping_promo(self):
        manifest = parse_app_list(json.loads(BUNDLED_PATH.read_text(encoding="utf-8")))
        self.assertTrue(manifest.cross_promo.enabled)
        self.assertIn("starping.co.uk", manifest.cross_promo.url)


class OldHubManifestTests(unittest.TestCase):
    """v1.0.x Hubs still read this repo's manifest.json; it must keep working for them."""

    def test_manifest_json_still_has_what_v1_0_hubs_read(self):
        data = json.loads((Path(__file__).resolve().parent.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(data["apps"])
        for app in data["apps"]:
            for key in ("id", "name", "repo"):
                self.assertTrue(app.get(key), f"{app} is missing {key}")
        self.assertTrue(data["cross_promo"]["enabled"])
        self.assertIn("starping.co.uk", data["cross_promo"]["url"])


OFFLINE = requests.ConnectionError("no network")


class LoadAppListFallbackTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.cache = self.dir / "apps.json"
        self.bundled = self.dir / "bundled.json"
        self.bundled.write_text(json.dumps({"apps": [SAMPLE["apps"][1]]}), encoding="utf-8")

    def _load(self):
        return load_app_list("https://example.invalid/apps.json", self.cache, self.bundled)

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_live_list_is_used_and_saved(self, mock_get):
        mock_get.return_value = _response(SAMPLE)
        manifest = self._load()
        self.assertEqual(manifest.source, "live")
        self.assertEqual(len(manifest.apps), 2)
        self.assertEqual(json.loads(self.cache.read_text(encoding="utf-8")), SAMPLE)

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_offline_uses_the_saved_copy(self, mock_get):
        self.cache.write_text(json.dumps(SAMPLE), encoding="utf-8")
        mock_get.side_effect = OFFLINE
        manifest = self._load()
        self.assertEqual(manifest.source, "saved")
        self.assertEqual(len(manifest.apps), 2)
        self.assertRegex(manifest.saved_at, r"^\d{1,2} [A-Z][a-z]{2} \d{4}$")

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_offline_with_no_saved_copy_uses_the_bundled_one(self, mock_get):
        mock_get.side_effect = OFFLINE
        manifest = self._load()
        self.assertEqual(manifest.source, "bundled")
        self.assertEqual([a.id for a in manifest.apps], ["wavescout"])

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_corrupt_saved_copy_falls_through_to_bundled(self, mock_get):
        self.cache.write_text("{truncated", encoding="utf-8")
        mock_get.side_effect = OFFLINE
        self.assertEqual(self._load().source, "bundled")

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_bad_live_list_is_not_saved_over_a_good_copy(self, mock_get):
        self.cache.write_text(json.dumps(SAMPLE), encoding="utf-8")
        mock_get.return_value = _response(text="<html>oops</html>")
        self.assertEqual(self._load().source, "saved")
        self.assertEqual(json.loads(self.cache.read_text(encoding="utf-8")), SAMPLE)

    @patch("vaultsoft_hub.app_list.requests.get")
    def test_nothing_available_raises_the_live_error(self, mock_get):
        self.bundled.unlink()
        mock_get.side_effect = OFFLINE
        with self.assertRaisesRegex(GitHubApiError, "no network"):
            self._load()

    def test_the_real_bundled_copy_parses(self):
        manifest = parse_app_list(json.loads(BUNDLED_PATH.read_text(encoding="utf-8")))
        ids = [a.id for a in manifest.apps]
        self.assertIn("pulsemonitor", ids)
        self.assertNotIn("vaultsoft-hub", ids)


if __name__ == "__main__":
    unittest.main()
