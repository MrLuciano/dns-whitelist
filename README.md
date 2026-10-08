# dns-whitelist

Curated allowlist of DNS names consumed by **AdGuard Home**, kept current
by an automated build that pulls from vendor-published catalogs.

## Consume

AdGuard Home → Filters → DNS allowlists → Add blocklist → URL:

```
https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt
```

## What it does

- Fetches the **Microsoft 365 endpoints catalog** weekly (and on manual
  trigger) and pulls the domains Teams and Microsoft Authenticator need.
- Validates each candidate with strict RFC-1035-ish syntax rules.
- Drops unresolvable domains (they can't be in any blocklist collision
  if they don't exist, so they don't belong in a *targeted* allowlist).
- Emits a deterministic `whitelist.txt` in AdGuard allowlist format
  (`@@||domain.com^`), with one section per service.

Currently covered:

- **Microsoft Teams** (`serviceArea=Skype` in the Microsoft 365 catalog)
- **Microsoft Authenticator** (`serviceArea=Common` in the Microsoft 365 catalog)

Phase 2 will add Google Authenticator, NetIQ, Cisco AnyConnect, and
Palo Alto GlobalProtect as additive YAML-only changes.

## Maintainers — local update

```bash
pip install -r requirements.txt
python scripts/build.py --out whitelist.txt
git diff  # review
git add whitelist.txt && git commit -m "chore: refresh whitelist"
```

`whitelist.txt` is **generated** — never hand-edit. To add a domain,
edit the source YAML or extend the parser.

## Add a new service

1. Drop a YAML in `sources/<service>.yaml` (see `sources/microsoft-teams.yaml`
   for the schema).
2. If your source isn't JSON, add a parser under `scripts/lib/parsers/`
   (mirror `parsers/json_endpoint.py`) and reference it via `fetch.type`.
3. Run `python scripts/build.py --out whitelist.txt` and review the diff.

## Tests

```bash
ruff check scripts/
python -m pytest -v
```

## Refresh schedule

A weekly GitHub Action re-runs the build and opens a PR if the output
changed. Manual refresh:

```bash
gh workflow run refresh-whitelist.yml
```

## Repo layout

```
sources/                  # one YAML per service (vendor URL + parser config)
scripts/build.py          # entry point
scripts/lib/{lint,resolve,fetch}.py
scripts/lib/parsers/      # one module per source family
scripts/test/             # pytest suite + fixtures
whitelist.txt             # GENERATED. Do not edit.
.github/workflows/        # test + refresh
```

## Caveats

- The Microsoft 365 catalog API requires a `?ClientRequestId=<UUID>`
  query parameter. Both sources YAMLs include a fixed client ID for
  tracking; you can change it, but the parameter must be a valid GUID.
- Many catalog entries (e.g. `*.static.microsoft`, `*.usercontent.microsoft`)
  don't resolve via public DNS, so they're dropped by the build. They're
  probably served by a wildcard CNAME that 1.1.1.1 / 8.8.8.8 can't see.
  Targeted-scope philosophy: if we can't see it, we can't add it.
- The build is gated on `pip install` succeeding. On Debian hosts, system
  Python is PEP 668-locked — use a venv (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
