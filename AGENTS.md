# AGENTS.md — dns-whitelist

> **Status: Phase 1 complete.** Framework + Microsoft Teams + Microsoft
> Authenticator are live. The remaining 4 services (NetIQ, Cisco AnyConnect,
> Palo Alto GlobalProtect, Google Authenticator) ship as additive changes
> in Phase 2 — one YAML per service, optionally one parser, one PR.

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