import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub.models import InstalledState
from vaultsoft_hub.state import StateStore


class StateStoreTests(unittest.TestCase):
    def test_set_get_persist_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            store = StateStore(path=path)
            self.assertIsNone(store.get("sweptpc"))

            store.set(
                InstalledState(
                    app_id="sweptpc",
                    version="1.0.1",
                    install_dir=str(Path(tmp) / "Apps" / "sweptpc"),
                    executable_path=str(Path(tmp) / "Apps" / "sweptpc" / "SweptPC.exe"),
                )
            )

            self.assertTrue(path.exists())

            reloaded = StateStore(path=path)
            record = reloaded.get("sweptpc")
            self.assertEqual(record.version, "1.0.1")
            self.assertTrue(record.executable_path.endswith("SweptPC.exe"))

    def test_remove_deletes_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            store = StateStore(path=path)
            store.set(InstalledState(app_id="pulsemonitor", version="1.1.0", install_dir="x"))
            store.remove("pulsemonitor")
            self.assertIsNone(store.get("pulsemonitor"))

    def test_corrupt_state_file_is_ignored_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{not valid json", encoding="utf-8")
            store = StateStore(path=path)
            self.assertIsNone(store.get("anything"))


if __name__ == "__main__":
    unittest.main()
