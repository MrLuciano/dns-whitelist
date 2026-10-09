<p>
  <b>English</b> | <a href="README.pt-BR.md">Português (Brasil)</a> | <a href="README.fr.md">Français</a> | <a href="README.es.md">Español</a>
</p>

# dns-whitelist

Curated allowlist of DNS names consumed by **AdGuard Home**, kept current
by an automated build that pulls from vendor-published catalogs.

## Consume

AdGuard Home → Filters → DNS allowlists → Add blocklist → URL:

```
https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt
```

## What it does

- **Fetches live vendor catalogs** (Microsoft 365 endpoints) weekly and
  on manual trigger; pulls the domains Teams and Microsoft Authenticator
  need.
- **Loads hand-curated YAML lists** (Google Authenticator, NetIQ, Cisco
  AnyConnect, Palo Alto GlobalProtect) — for services that don't publish
  a machine-readable allowlist. See `sources/*.yaml` for the curated FQDN
  sets and the upstream docs they reference.
- Validates each candidate with strict RFC-1035-ish syntax rules.
- Drops unresolvable domains (they can't be in any blocklist collision
  if they don't exist, so they don't belong in a *targeted* allowlist).
- Emits a deterministic `whitelist.txt` in AdGuard allowlist format
  (`@@||domain.com^`), with one section per service.

Currently covered:

- **Microsoft Teams** — `serviceArea=Skype` in the Microsoft 365 catalog
- **Microsoft Authenticator** — `serviceArea=Common` in the Microsoft 365 catalog
- **Google Authenticator** — offline-first app; only the cloud-sync path
  needs network. Hand-curated.
- **NetIQ** (Access Manager + Identity Manager) — only the optional
  update/registration/catalog endpoints are vendor-owned. Hand-curated.
- **Cisco AnyConnect / Secure Client** — universal support domains
  plus Umbrella and Secure Access cloud endpoints. Hand-curated.
- **Palo Alto GlobalProtect** — only the customer's own portal FQDN is
  always required; we ship the optional Prisma Access / CIE / SLS cloud
  endpoints. Hand-curated. **Add your portal FQDN to the local AdGuard
  config; it can't be enumerated.**

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
2. Pick a parser:
   - **Machine-readable catalog** (e.g. JSON): use `json_endpoint` (or add
     a new parser under `scripts/lib/parsers/`, mirroring
     `parsers/json_endpoint.py`) and reference it via `fetch.type`.
   - **Hand-curated list** (no upstream catalog): use `static_list` with
     `fetch: false` and a `urls:` block. See `sources/netiq.yaml` for
     the schema. **Add a comment per entry citing the source URL** so
     the list stays auditable.
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
- **Deployment-specific FQDNs are not included.** The customer's own
  VPN/portal headend (e.g. `vpn.example.com`, GlobalProtect portal) is
  always required but cannot be enumerated by a generic allowlist. Add
  those entries to your local AdGuard config.
- The build is gated on `pip install` succeeding. On Debian hosts, system
  Python is PEP 668-locked — use a venv (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
