__version__ = "1.0.2"

# The GitHub repo this Hub itself is published from, used for self-update checks.
SELF_REPO = "VaultSoft/vaultsoft-hub"

# Where the manifest of apps is fetched from. Pointing at "main" means Joshua can
# add/remove apps by editing manifest.json in the repo — no Hub rebuild required.
MANIFEST_URL = (
    "https://raw.githubusercontent.com/VaultSoft/vaultsoft-hub/main/manifest.json"
)
