# VaultSoft rules for Claude Code

Git
- Always `git fetch` first and check local main == origin/main before starting.
- Never work in the main checkout. Create your own worktree and branch:
  `git worktree add ..\<repo>-<task> -b agent/claude/<task> origin/main`
- Never merge into main, push main, create or push tags, or publish releases unless Josh explicitly authorises it for that task.
- When authorised to update main: fast-forward only (`git merge --ff-only`). Never a plain `git merge`, never a merge commit, never force-push. If a fast-forward isn't possible, stop and ask.
- Don't touch other sessions' branches, uncommitted files or untracked folders. If the checkout or branches change under you, stop and report.
- A release tag must point at the exact tested commit, and that commit must already be on origin/main.
- Clean up your own worktree and branch when done, only after confirming the branch is contained in main.

Safety
- No secrets, personal paths or postal details in commits.
- Don't modify Cloudflare DNS or email settings.

VaultSoft Hub
- manifest.json is FROZEN for v1.0.x Hubs; only flip values, never restructure it.
- Before a Hub release, refresh vaultsoft_hub/bundled_apps.json from the live https://vaultsoft.co.uk/apps.json.
