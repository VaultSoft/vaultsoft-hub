import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultsoft_hub._vendor import vaultsoft_kit


class VendoredKitTests(unittest.TestCase):
    def test_vendored_kit_matches_the_recorded_kit_commit(self):
        self.assertEqual([], vaultsoft_kit.vendored_drift(Path(vaultsoft_kit.__file__).parent))

    def test_installer_uses_the_vendored_safe_delete(self):
        from vaultsoft_hub import installer
        from vaultsoft_hub._vendor.vaultsoft_kit import safe_delete

        self.assertIs(installer.safe_delete_path, safe_delete.safe_delete_path)
        self.assertIs(installer.validate_cleanup_path, safe_delete.validate_cleanup_path)


if __name__ == "__main__":
    unittest.main()
