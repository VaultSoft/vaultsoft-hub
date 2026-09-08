# VaultSoft Hub

One portable launcher for every VaultSoft app. Install, update, and launch
PulseMonitor, SweptPC, WaveScout (and whatever you ship next) from a single
window — instead of each one being a separate GitHub Pages download that
people forget exists.

**Why this exists:** every VaultSoft app currently starts its download count
back at zero. The Hub flips that — ship a new app, add one entry to
`manifest.json`, and everyone who already has the Hub sees it appear with an
Install button. It also gives you one honest, non-spammy place to mention
StarPing to people who've already shown they'll install your software.

## How it works

- `manifest.json` (hosted on GitHub, edited directly — no rebuild needed)
  lists the apps: id, name, GitHub repo, description, category.
- The Hub resolves **version numbers and download links live** from each
  app's GitHub Releases (`/repos/{repo}/releases/latest`) — so bumping an
  app's version never touches the manifest or the Hub.
- Installed apps are extracted into `%LOCALAPPDATA%\VaultSoft\Apps\<id>` and
  tracked in a small local state file — no Windows installer, no registry
  writes, stays portable.
- The Hub checks its own GitHub repo the same way, so it can tell you when a
  newer Hub build exists.

```
manifest.json  ──►  Hub reads app list
                     │
                     ▼
   for each app:  GitHub Releases API  ──►  latest version + download .zip
                     │
                     ▼
              install / update / launch
```

## Adding a new app (do this instead of touching code)

Add an entry to `manifest.json`:

```json
{
  "id": "yournewapp",
  "name": "YourNewApp",
  "repo": "VaultSoft/YourNewApp",
  "category": "Utilities",
  "description": "One line, shown in the Hub.",
  "homepage": "https://vaultsoft.github.io/YourNewApp/",
  "executable_hint": "YourNewApp.exe"
}
```

Requirements on the app's side (same pattern WaveScout already follows):
- Publish releases on GitHub with a `.zip` asset — ideally with "Portable" in
  the filename (e.g. `YourNewApp_v1.0.0_Portable.zip`), matching your
  existing convention.
- `executable_hint` should match the .exe's filename exactly, so the Hub
  finds it even if the zip has files alongside it.

No Hub rebuild, no code change, no new release of the Hub itself required —
push the manifest change and every Hub out there sees the new app on its
next refresh.

## Project layout

```
vaultsoft_hub/
  app.py            entry point (QApplication + MainWindow)
  github_api.py      talks to the GitHub REST API (manifest + releases)
  installer.py       download / extract / find exe / launch / uninstall
  state.py           local JSON record of what's installed, at which version
  self_update.py     checks the Hub's own repo for a newer build
  models.py          plain dataclasses shared across modules
  ui/
    main_window.py    the window: app list, refresh, promo banner
    app_card.py        one app's row (status + single action button)
    workers.py         QThread wrappers so network/disk never block the UI
    styles.py          dark theme QSS
manifest.json         the editable app list (see above)
build.spec            PyInstaller spec (windowed, one-file)
.github/workflows/release.yml   builds + releases on every `vX.Y.Z` tag
tests/                unit tests (stdlib unittest, no extra deps needed)
```

## Running it locally (Windows, for development)

```
pip install -r requirements.txt
python -m vaultsoft_hub
```

## Building the portable .exe

Locally on Windows:
```
pip install -r requirements.txt pyinstaller
pyinstaller build.spec
# -> dist/VaultSoftHub.exe
```

Or just push a tag and let CI do it:
```
git tag v1.0.0
git push origin v1.0.0
```
`.github/workflows/release.yml` builds on `windows-latest`, zips the exe as
`VaultSoftHub_v1.0.0_Portable.zip` (matching your existing naming pattern),
and attaches it to a new GitHub Release automatically.

## Setup checklist (one-time)

1. Create the `VaultSoft/vaultsoft-hub` repo on GitHub and push this project.
2. Confirm `MANIFEST_URL` in `vaultsoft_hub/__init__.py` points at that
   repo's `manifest.json` on `main` (it already does, by default).
3. Tag `v1.0.0` and push — CI builds the first release.
4. Add a "Download the Hub" card/button to vaultsoft.github.io pointing at
   the release's portable zip, ideally above the individual app cards.
5. From then on: new app → add manifest entry → done. New Hub version → bump
   `__version__` in `vaultsoft_hub/__init__.py`, tag, push.

## Tests

```
python -m unittest discover -s tests -v
```
These only need `requests` (already a runtime dependency) — no PyQt6 needed
to run them, since they test the network/install/state logic in isolation
from the UI.

## Notes / things to decide later

- GitHub's unauthenticated API allows 60 requests/hour, which is plenty for
  a handful of apps checked on refresh. If you add many more apps, set the
  `VAULTSOFT_HUB_GH_TOKEN` env var to a personal access token (no scopes
  needed) to raise that ceiling.
- The Hub doesn't silently replace its own running .exe — it prompts and
  opens the download in your browser instead. Safer, and simple enough not
  to be worth the risk of a self-replacing Windows executable.
- `cross_promo` in `manifest.json` is a simple on/off + text + link. Turn it
  off entirely by setting `"enabled": false` if you'd rather the Hub stay
  purely a utility.
