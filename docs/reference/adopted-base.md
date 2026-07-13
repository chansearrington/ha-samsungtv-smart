# Adopted base (TheFab21 fork "C")

- **Upstream:** `fab21` = https://github.com/TheFab21/ha-samsungtv-smart.git
- **Pinned tag:** `8.3.3` (latest stable; 8.4.0b* are betas — never pin a beta)
- **Pinned commit:** `3b56d7d4343aefcd190201cd44f58c454df0d358`
- **Adopted on:** 2026-07-12
- **Verified latest stable:** yes — full tag list version-sorted; highest non-beta three-part tag is 8.3.3, and `fab21/master` manifest = 8.3.3.
- **How to re-sync (deliberate only, never auto-pull):**
  `git fetch fab21 --tags` then re-run the Task 0.4 tree-copy against the new tag.

- **NOTICE:** TheFab21 8.3.3 ships no NOTICE file; Apache-2.0 LICENSE is at repo root and retained. `api/art.py` keeps SPDX LGPL-3.0 + xchwarze/Garrett/Waterton attribution.
