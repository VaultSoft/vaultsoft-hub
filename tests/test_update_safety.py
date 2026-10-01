"""The update step replaces an app's folder without ever following links out of
the Hub's Apps folder. Everything here runs in temporary folders."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub import installer
from vaultsoft_hub.models import AppEntry, ReleaseInfo
from vaultsoft_hub.state import StateStore

APP = AppEntry(id="wavescout", name="WaveScout", repo="VaultSoft/WaveScout",
               category="Network", description="", executable_hint="WaveScout.exe")


def release(version):
    return ReleaseInfo(tag_name=f"v{version}", version=version,
                       download_url=f"https://example.invalid/WaveScout_v{version}.zip",
                       asset_name=f"WaveScout_v{version}.zip")


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class UpdateSafetyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.apps = self.base / "VaultSoft" / "Apps"
        self.apps.mkdir(parents=True)
        self.state = StateStore(path=self.base / "VaultSoft" / "state.json")
        self.downloads = []
        self.payload = zip_bytes({"WaveScout/WaveScout.exe": b"new", "WaveScout/README.txt": b"v2"})
        patches = [
            patch("vaultsoft_hub.installer.apps_dir", return_value=self.apps),
            patch("vaultsoft_hub.installer.download_file", side_effect=self._fake_download),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _fake_download(self, url, dest, on_progress=None):
        self.downloads.append(Path(dest))
        Path(dest).write_bytes(self.payload)

    def _junction_or_skip(self, link, target):
        if os.name != "nt":
            self.skipTest("junctions need Windows")
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest(f"could not create junction: {r.stdout or r.stderr}")
        self.addCleanup(lambda: os.path.lexists(link) and subprocess.run(["cmd", "/c", "rmdir", str(link)], capture_output=True))

    def _old_install(self, files=None):
        d = self.apps / "wavescout" / "WaveScout"
        d.mkdir(parents=True)
        for name, content in (files or {"WaveScout.exe": b"old", "old-only.txt": b"x"}).items():
            (d / name).write_bytes(content)
        return d

    def _set_aside(self):
        return sorted(self.apps.glob("_wavescout.old-*"))

    def test_update_replaces_old_version_and_removes_it(self):
        self._old_install()

        installed = installer.install_or_update(APP, release("2.0.0"), self.state)

        new_dir = self.apps / "wavescout" / "WaveScout"
        self.assertEqual(b"new", (new_dir / "WaveScout.exe").read_bytes())
        self.assertFalse((new_dir / "old-only.txt").exists())
        self.assertEqual([], self._set_aside())
        self.assertEqual([], installed.cleanup_issues)
        self.assertEqual("2.0.0", self.state.get("wavescout").version)
        self.assertEqual([], [p for p in self.apps.iterdir() if p.suffix == ".download"])

    def test_fresh_install_works(self):
        installed = installer.install_or_update(APP, release("1.0.0"), self.state)
        self.assertTrue(Path(installed.executable_path).is_file())

    def test_junction_inside_old_version_is_never_followed(self):
        bait = self.base / "Bait"
        bait.mkdir()
        (bait / "keep.txt").write_text("keep")
        old = self._old_install()
        self._junction_or_skip(old / "link-out", bait)

        installed = installer.install_or_update(APP, release("2.0.0"), self.state)

        self.assertEqual("keep", (bait / "keep.txt").read_text())
        self.assertEqual(b"new", (self.apps / "wavescout" / "WaveScout" / "WaveScout.exe").read_bytes())
        leftovers = self._set_aside()
        self.assertEqual(1, len(leftovers), "blocked old copy is left in place, not deleted")
        self.assertEqual(1, len(installed.cleanup_issues))
        self.assertIn("reparse-point", installed.cleanup_issues[0])

    def test_blocked_leftover_is_retried_and_removed_once_safe(self):
        bait = self.base / "Bait"
        bait.mkdir()
        (bait / "keep.txt").write_text("keep")
        old = self._old_install()
        link = old / "link-out"
        self._junction_or_skip(link, bait)
        installer.install_or_update(APP, release("2.0.0"), self.state)
        (leftover,) = self._set_aside()
        subprocess.run(["cmd", "/c", "rmdir", str(leftover / "WaveScout" / "link-out")], capture_output=True, check=True)

        installed = installer.install_or_update(APP, release("2.0.1"), self.state)

        self.assertEqual([], self._set_aside())
        self.assertEqual([], installed.cleanup_issues)
        self.assertEqual("keep", (bait / "keep.txt").read_text())

    def test_app_folder_that_is_a_junction_is_refused_before_anything_changes(self):
        outside = self.base / "Elsewhere"
        outside.mkdir()
        (outside / "precious.txt").write_text("precious")
        self._junction_or_skip(self.apps / "wavescout", outside)

        with self.assertRaises(installer.InstallError) as ctx:
            installer.install_or_update(APP, release("2.0.0"), self.state)

        self.assertIn("Nothing was changed", str(ctx.exception))
        self.assertEqual("precious", (outside / "precious.txt").read_text())
        self.assertEqual([], self.downloads)
        self.assertIsNone(self.state.get("wavescout"))

    def test_apps_folder_that_is_a_junction_is_refused(self):
        real = self.base / "RealApps"
        (real / "wavescout").mkdir(parents=True)
        (real / "wavescout" / "precious.txt").write_text("precious")
        linked_apps = self.base / "LinkedApps"
        self._junction_or_skip(linked_apps, real)

        with patch("vaultsoft_hub.installer.apps_dir", return_value=linked_apps):
            with self.assertRaises(installer.InstallError):
                installer.install_or_update(APP, release("2.0.0"), self.state)

        self.assertEqual("precious", (real / "wavescout" / "precious.txt").read_text())
        self.assertEqual([], self.downloads)

    def test_unsafe_app_id_is_refused_before_download(self):
        for bad in ("../evil", "..", "C:\\x", "Upper", "a/b"):
            app = AppEntry(id=bad, name="Evil", repo="x/y", category="", description="")
            with self.assertRaises(installer.InstallError):
                installer.install_or_update(app, release("1.0.0"), self.state)
        self.assertEqual([], self.downloads)

    def test_running_app_stops_the_update_with_nothing_changed(self):
        old = self._old_install()
        handle = open(old / "WaveScout.exe", "rb")  # an open file blocks renaming its folder on Windows
        self.addCleanup(handle.close)
        if os.name != "nt":
            self.skipTest("open-file locking is Windows behaviour")

        with self.assertRaises(installer.InstallError) as ctx:
            installer.install_or_update(APP, release("2.0.0"), self.state)

        self.assertIn("close it if it's running", str(ctx.exception))
        self.assertEqual(b"old", (old / "WaveScout.exe").read_bytes())
        self.assertTrue((old / "old-only.txt").exists())
        self.assertEqual([], self._set_aside())
        self.assertEqual([], [p for p in self.apps.iterdir() if p.suffix == ".download"])

    def test_bad_download_puts_the_old_version_back(self):
        old = self._old_install()
        self.payload = b"not a zip"

        with self.assertRaises(installer.InstallError):
            installer.install_or_update(APP, release("2.0.0"), self.state)

        self.assertEqual(b"old", (old / "WaveScout.exe").read_bytes())
        self.assertTrue((old / "old-only.txt").exists())
        self.assertEqual([], self._set_aside())

    def test_odd_version_text_cannot_move_the_download_outside_apps(self):
        installer.install_or_update(APP, release("1.0/../../escape"), self.state)

        (download,) = self.downloads
        self.assertEqual(self.apps, download.parent)
        self.assertFalse((self.base / "escape.download").exists())


if __name__ == "__main__":
    unittest.main()
