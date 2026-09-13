# VaultSoft Release Standard

This is the small release contract used by the desktop app repositories. It is intentionally lightweight; app-specific build details can remain in each repository.

## Branches and releases

- Work happens on an `agent/**` feature branch before merging to the default branch.
- Verification workflows run on the default branch, pull requests to the default branch, and `agent/**` branches.
- Release creation is separate from build verification. Verification workflows must not create tags, releases, or version bumps.

## Version metadata

- Each app has one authoritative version source.
- Packaging and ZIP names read from that source rather than hardcoding release versions in build scripts or workflows.
- Build or reliability work must not bump versions unless the task explicitly asks for it.

## Local and CI verification

- CI runs the full unit test suite with Python 3.11.
- CI performs a syntax/import check before packaging.
- CI builds the portable Windows package and verifies the expected executable and ZIP exist.
- Generated build outputs remain ignored by git.

## Packaging hygiene

- Runtime requirements and build-only requirements should be separate for apps that have both.
- Portable artifact uploads should contain the release ZIP, not the whole build directory.
- Build scripts should fail loudly if required packaged files are missing or if unexpected root-level DLL leakage is detected.
