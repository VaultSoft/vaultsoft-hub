__version__ = "1.1.0"

# The GitHub repo this Hub itself is published from, used for self-update checks.
SELF_REPO = "VaultSoft/vaultsoft-hub"

# The app list: the same apps.json that builds the vaultsoft.co.uk homepage, so
# adding an app to the site adds it to every Hub too, with no Hub rebuild.
# (manifest.json in this repo is only still there for v1.0.x Hubs.)
APPS_URL = "https://vaultsoft.co.uk/apps.json"
