import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub import installer
from vaultsoft_hub.models import AppEntry, ReleaseInfo
from vaultsoft_hub.state import StateStore


def _make_zip_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class FindExecutableTests(unittest.TestCase):
    def test_finds_single_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "WaveScout.exe").write_bytes(b"stub")
            found = installer.find_executable(root)
            self.assertEqual(found.name, "WaveScout.exe")

    def test_prefers_hinted_name_over_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "readme_opener.exe").write_bytes(b"stub")
            (root / "WaveScout.exe").write_bytes(b"stub")
            found = installer.find_executable(root, executable_hint="WaveScout.exe")
            self.assertEqual(found.name, "WaveScout.exe")

    def test_ignores_uninstaller_when_no_hint_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unins000.exe").write_bytes(b"stub")
            sub = root / "app"
            sub.mkdir()
            (sub / "RealApp.exe").write_bytes(b"stub")
            found = installer.find_executable(root)
            self.assertEqual(found.name, "RealApp.exe")

    def test_returns_none_when_no_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(installer.find_executable(Path(tmp)))


class InstallOrUpdateTests(unittest.TestCase):
    def test_downloads_extracts_and_records_state(self):
        zip_bytes = _make_zip_bytes({"WaveScout.exe": b"fake-binary-content"})

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"Content-Length": str(len(zip_bytes))}
        mock_resp.iter_content.return_value = [zip_bytes]
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False

        app = AppEntry(
            id="wavescout",
            name="WaveScout",
            repo="VaultSoft/WaveScout",
            category="Network",
            description="WiFi analyser",
            executable_hint="WaveScout.exe",
        )
        release = ReleaseInfo(
            tag_name="v1.0.0",
            version="1.0.0",
            download_url="https://x/WaveScout_v1.0.0_Portable.zip",
            asset_name="WaveScout_v1.0.0_Portable.zip",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with patch("vaultsoft_hub.installer.requests.get", return_value=mock_resp), \
                 patch("vaultsoft_hub.installer.apps_dir", return_value=tmp_path):
                state = StateStore(path=tmp_path / "state.json")
                installed = installer.install_or_update(app, release, state)

            self.assertEqual(installed.version, "1.0.0")
            self.assertTrue(installed.executable_path.endswith("WaveScout.exe"))
            self.assertTrue(Path(installed.executable_path).exists())

            # Re-read state from disk to make sure it was actually persisted.
            reloaded = StateStore(path=tmp_path / "state.json")
            record = reloaded.get("wavescout")
            self.assertIsNotNone(record)
            self.assertEqual(record.version, "1.0.0")


if __name__ == "__main__":
    unittest.main()
