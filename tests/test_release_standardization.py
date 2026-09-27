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

    def test_release_workflow_refuses_tags_not_on_main(self) -> None:
        # v1.1.1 was first published from a commit that was only on a local
        # main another session had moved. The guard must run before anything
        # is built or released, on a full-history checkout.
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("git fetch --no-tags origin main", workflow)
        self.assertIn('git merge-base --is-ancestor "$GITHUB_SHA" FETCH_HEAD', workflow)
        guard = workflow.index("Refuse tags that are not on origin/main")
        self.assertLess(workflow.index("actions/checkout"), guard)
        self.assertLess(guard, workflow.index("pyinstaller build.spec"))
        self.assertLess(guard, workflow.index("softprops/action-gh-release"))


if __name__ == "__main__":
    unittest.main()
