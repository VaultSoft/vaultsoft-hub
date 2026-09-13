from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseStandardizationTests(unittest.TestCase):
    def test_build_verification_workflow_builds_without_releasing(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-verification.yml").read_text(encoding="utf-8")

        self.assertIn("name: Build Verification", workflow)
        self.assertIn("python -B -m unittest discover -s tests -v", workflow)
        self.assertIn("python -B -m PyInstaller build.spec --noconfirm --clean", workflow)
        self.assertIn("actions/upload-artifact", workflow)
        self.assertIn("dist/VaultSoftHub_v*_Portable.zip", workflow)
        self.assertNotIn("softprops/action-gh-release", workflow)
        self.assertNotIn("gh release", workflow.lower())
        self.assertNotIn("git tag", workflow.lower())


if __name__ == "__main__":
    unittest.main()
