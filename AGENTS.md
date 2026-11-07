# AGENTS.md — dns-whitelist

> **Status: All 6 services live.** Framework + Microsoft Teams + Microsoft
> Authenticator (Phase 1, fetched from the Microsoft 365 catalog) and
> Google Authenticator + NetIQ + Cisco AnyConnect + Palo Alto GlobalProtect
> (Phase 2, hand-curated via `static_list` parser — no upstream catalog).
> 26/26 tests pass; ruff clean.

## Verified facts

- **Remote:** `https://github.com/MrLuciano/dns-whitelist.git` (HTTPS — see
  *Working in this repo* below for why)
- **Default branch:** `main`
- **Owner:** `MrLuciano`
- **First commit:** `AGENTS.md` only (initial stub; no code yet).
- **GitHub repo:** `isEmpty=false`, `defaultBranchRef.name=main` after init.

## Output format (verified)

`whitelist.txt` is **generated** in AdGuard Home allowlist syntax:

```
# === Microsoft Teams ===
# Source: https://learn.microsoft.com/.../urls-and-ip-address-ranges
@@||teams.microsoft.com^
@@||teams.live.com^
```

Each section is delimited by `# === Service Name ===` and preceded by a
`# Source:` line. Rules are global (no `$client` modifier). Entries
within a section are sorted alphabetically. The file is deterministic;
do not hand-edit.

## Conventions

- **Language / runtime:** Python 3.11
- **Test runner:** `python -m pytest -v` (single test: `python -m pytest scripts/test/test_<name>.py::TestClass::test_method -v`)
- **Lint / formatter:** `ruff check scripts/`
- **Build / generate:** `python scripts/build.py --out whitelist.txt`
- **CI:** `.github/workflows/test.yml` (PR + push to main) + `.github/workflows/refresh-whitelist.yml` (weekly + manual dispatch)
- **Commit-message convention:** Conventional Commits (`feat(scope):`, `chore:`, `docs:`, `ci:`, `test:`, `fix:`, `style:`, `refactor:`)
- **Single-test command:** `python -m pytest scripts/test/test_<name>.py -v`

## Repo layout

```
sources/                  # one YAML per service (vendor URL + parser config)
scripts/build.py          # entry point
scripts/lib/{lint,resolve,fetch}.py
scripts/lib/parsers/      # one module per source family
scripts/test/             # pytest suite + fixtures
whitelist.txt             # GENERATED. Do not edit.
.github/workflows/        # test + refresh
docs/superpowers/         # design spec + implementation plan
```

## Updating the whitelist

- **Local:** `python scripts/build.py --out whitelist.txt` — review, commit.
- **CI:** weekly refresh workflow re-runs the build and opens a PR on diff.
- **Add a service:** drop a YAML in `sources/` (see README "Add a new service").
- **`whitelist.txt` is generated — never hand-edit it.**

## Working in this repo

- Prefer `git status` before and after edits.
- HTTPS is the configured remote and `gh auth git-credential` is the
  credential helper for `https://github.com`, so `git push`/`fetch` "just
  works" as long as `gh auth status` shows an active login.
- SSH (`git@github.com:…`) is not currently configured (no keys in
  `~/.ssh/`). If you switch the remote URL back to SSH, set up
  `ssh-agent` + an added key first, or `git push` will fail with
  `Permission denied (publickey)`.
- **Python on Debian hosts is PEP 668-locked.** Use a venv:
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`,
  then `.venv/bin/pytest` and `.venv/bin/ruff` for local checks.
- **Microsoft 365 catalog API requires `?ClientRequestId=<UUID>`.** Both
  sources YAMLs include a fixed client ID; change it freely, but the
  parameter must be a valid GUID or the response is `400 Bad Request`.
- **Never DNS-resolve a wildcard candidate.** Many vendor domains are
  CNAME-only at the apex (no A record) while their subdomains are real
  services. The AdGuard `@@||apex^` rule covers all subdomains anyway,
  so `_gather_section` skips the resolve check for wildcard entries.
  Dropping them broke Bing Maps (Authenticator location map hung) and
  the whole Microsoft auth/push surface (Authenticator approval never
  returned). Prefer a wildcard over enumerating subdomains.
- **A blocked third-party channel can break an app that "looks" fine.**
  The Authenticator app received its push challenge but could not return
  the approval, because the *upstream* channel is Google FCM
  (`mtalk.google.com`, `fcm.googleapis.com`, `firebaseinstallations.
  googleapis.com`, `android.apis.google.com`, `device-provisioning.
  googleapis.com`) — Google publishes an official FCM allowlist at
  firebase.google.com/docs/cloud-messaging/network-configuration.
  When an app receives a push but never gets a response back, suspect
  the response channel, not the sign-in one.
- **`dig` is not installed on this host.** Use the project's own
  resolver: `from scripts.lib.resolve import resolve_domain`. Empty
  `dig` output here means a missing binary, not missing DNS.
- **The weekly refresh regenerates `whitelist.txt` and merges via PR,
  so `main` moves under you.** If a push is rejected, `git pull --rebase
  origin main`; if `whitelist.txt` conflicts, delete it and re-run
  `python scripts/build.py --out whitelist.txt` — the YAMLs are the
  source of truth, never hand-merge a generated file.
- **The refresh workflow needs a repo setting, not just YAML
  permissions.** `can_approve_pull_request_reviews: false` at the repo
  level overrides the workflow's `pull-requests: write` and the PR step
  fails with `403 ... not permitted to create or approve pull requests`.
  Fix: `gh api -X PUT repos/OWNER/REPO/actions/permissions/workflow
  -F default_workflow_permissions=write
  -F can_approve_pull_request_reviews=true`.
  
  ## Cleanup
  - clean up local temporary changes after pushing to git. 