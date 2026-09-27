# VaultSoft Hub

One portable launcher for every VaultSoft app. Install, update, and launch
PulseMonitor, SweptPC, WaveScout (and whatever you ship next) from a single
window — instead of each one being a separate GitHub Pages download that
people forget exists.

**Why this exists:** every VaultSoft app currently starts its download count
back at zero. The Hub flips that — ship a new app, add one entry to the
site's `apps.json`, and everyone who already has the Hub sees it appear with an
Install button. It also gives you one honest, non-spammy place to mention
StarPing to people who've already shown they'll install your software.

## How it works

- The app list is the site's **`apps.json`**, served at
  <https://vaultsoft.co.uk/apps.json> from the `vaultsoft.github.io` repo. The
  same file builds the homepage, so an app added to the site shows up in every
  Hub too. No Hub rebuild needed.
- The Hub resolves **version numbers and download links live** from each
  app's GitHub Releases (the newest non-draft release, betas included), so
  bumping an app's version never touches `apps.json` or the Hub.
- **Offline:** if `apps.json` can't be fetched, the Hub uses the last good copy
  it saved (`%LOCALAPPDATA%\VaultSoft\apps.json`), then the copy built into the
  exe (`vaultsoft_hub/bundled_apps.json`). The status line says when it does.
- Installed apps are extracted into `%LOCALAPPDATA%\VaultSoft\Apps\<id>` and
  tracked in a small local state file — no Windows installer, no registry
  writes, stays portable.
- The Hub checks its own GitHub repo the same way (stable releases only), so
  it can tell you when a newer Hub build exists.

```
apps.json (vaultsoft.co.uk)  ──►  Hub reads app list  (else saved copy, else built-in copy)
                     │
                     ▼
   for each app:  GitHub Releases API  ──►  newest version + download .zip
                     │
                     ▼
              install / update / launch   (or "Open page" for link-only apps)
```

## Adding a new app (do this instead of touching code)

Add the app to `apps.json` in the `vaultsoft.github.io` repo (its README
has the full field list), then rebuild and push the site. The Hub uses `id`,
`name`, `description`, `repo`, `link` and `badge`, plus an optional
Hub-only `hub` value that the site ignores:

| `hub` | What the Hub does |
|---|---|
| `{"exe": "YourNewApp.exe"}` | Installs from `repo`'s newest release and launches that exe. |
| `{"mode": "link"}` | Lists the app with an "Open page" button to `link`; no install (e.g. ScribeVault). |
| `false` | Doesn't list it (e.g. the Hub itself). |
| missing | Installs from `repo`, guessing the exe. |

The banner at the bottom comes from the top-level `hub_promo`
(`enabled`, `text`, `url`).

**`apps.json` can only gain fields, never remove or rename them.** Hubs
already on people's PCs read it and can't be updated from there.

Requirements on the app's side (same pattern WaveScout already follows):
- Publish releases on GitHub with a `.zip` asset — ideally with "Portable" in
  the filename (e.g. `YourNewApp_v1.0.0_Portable.zip`), matching your
  existing convention.
- `hub.exe` should match the .exe's filename exactly, so the Hub finds it
  even if the zip has files alongside it.

No Hub rebuild, no code change, no new release of the Hub itself required —
push the site change and every Hub out there sees the new app on its next
refresh. (`bundled_apps.json` is only the offline fallback; refresh it from
the site before a Hub release.)

An app can go into `apps.json` before its first GitHub release. Until
there is one, a Hub newer than v1.1.1 shows its card as **Coming soon** /
"Not released yet" (with an "Open page" button if it has a `link`),
rather than an error with a Retry button. A copy the Hub installed earlier still launches.

The icon comes from `vaultsoft_hub/icons/<file>.svg`, named by the entry's
`icon`. The website's `icons/` folder holds the same files, so copy a new
app's SVG in both places. An app with no icon file gets a drawn initial.

### FileFlow (ready, waiting for its first release)

The Hub side of FileFlow is done: its icon is `vaultsoft_hub/icons/fileflow.svg`,
and the "Coming soon" state covers the time before its release. Nothing
lists FileFlow yet, because the live app list is the site's `apps.json`.
`bundled_apps.json` is deliberately left alone: it must stay a copy of the
site, not get ahead of it.

When FileFlow is ready to appear, add this to the site's `apps.json`
(e.g. after SweptPC), copy `fileflow.svg` into the site's `icons/`, and
rebuild the site:

```json
{
  "id": "fileflow",
  "name": "FileFlow",
  "description": "Preview, organise and safely undo file moves. See every move before it happens; nothing is ever overwritten or deleted.",
  "category": "System & PC",
  "badge": "Free",
  "link": "TODO: FileFlow's page URL",
  "repo": "VaultSoft/FileFlow",
  "released": "TODO: YYYY-MM-DD",
  "icon": "icons/fileflow.svg",
  "hub": {"exe": "FileFlow.exe"}
}
```

Before or with that change:

- [ ] Create the public repo `VaultSoft/FileFlow` (it doesn't exist yet;
      if it gets another name, change `repo` above). It must be public:
      the Hub reads releases anonymously.
- [ ] Publish a release with `FileFlow_vX.Y.Z_Portable.zip` attached
      (what FileFlow's `build.py` makes). The zip holds a `FileFlow/`
      folder with `FileFlow.exe` and its DLLs. The Hub extracts the whole
      zip, finds `FileFlow.exe` by the `hub.exe` name, and starts it from
      that folder.
- [ ] Fill in `link` (FileFlow's page) and `released`, and confirm `badge`.
      There's no download URL to add: the Hub resolves it from the release.
- [ ] Before the next Hub release, refresh `bundled_apps.json` from the site
      as usual, which brings FileFlow into the offline copy too.

Safest order: publish FileFlow's release first, then add it to `apps.json`.
Every Hub then offers Install straight away. Listing it before the release
only looks right in Hubs that have the Coming soon state. v1.1.1 and older
would show "VaultSoft/FileFlow has no published releases yet." with a Retry
button until the release exists.

### manifest.json is frozen

`manifest.json` in this repo is what v1.0.x Hubs read. Leave it, and its
`cross_promo`, in place so they keep working; don't add new apps there.

## Project layout

```
vaultsoft_hub/
  app.py            entry point (QApplication + MainWindow)
  app_list.py        loads apps.json (live, saved copy, or built-in copy)
  github_api.py      talks to the GitHub REST API (releases)
  bundled_apps.json  offline copy of the site's apps.json
  installer.py       download / extract / find exe / launch / uninstall
  state.py           local JSON record of what's installed, at which version
  self_update.py     checks the Hub's own repo for a newer build
  models.py          plain dataclasses shared across modules
  ui/
    main_window.py    the window: app list, refresh, promo banner
    app_card.py        one app's row (status + single action button)
    workers.py         QThread wrappers so network/disk never block the UI
    styles.py          dark theme QSS
manifest.json         frozen app list for v1.0.x Hubs only
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
2. Confirm `APPS_URL` in `vaultsoft_hub/__init__.py` points at the site's
   `apps.json` (it already does, by default).
3. Tag `v1.0.0` and push — CI builds the first release.
4. Add a "Download the Hub" card/button to vaultsoft.github.io pointing at
   the release's portable zip, ideally above the individual app cards.
5. From then on: new app → add it to the site's `apps.json` → done. New Hub version → bump
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
- `hub_promo` in `apps.json` is a simple on/off + text + link. Turn it
  off entirely by setting `"enabled": false` if you'd rather the Hub stay
  purely a utility.
