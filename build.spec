# PyInstaller spec for VaultSoft Hub.
# Build locally with:  pyinstaller build.spec
# CI builds this automatically on tag push - see .github/workflows/release.yml
block_cipher = None

a = Analysis(
    ["run_app.py"],
    pathex=[],
    binaries=[],
    # bundled_apps.json must land next to app_list.py (offline fallback list), and
    # icons/ next to it too: ui/icons.py finds both relative to the package.
    datas=[
        ("icon.ico", "."),
        ("vaultsoft_hub/bundled_apps.json", "vaultsoft_hub"),
        ("vaultsoft_hub/icons/*.svg", "vaultsoft_hub/icons"),  # app icons, from the site
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VaultSoftHub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)
