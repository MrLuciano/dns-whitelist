# AGENTS.md — dns-whitelist

> **Status: stub.** The repo is currently empty (no source, no manifest, no
> tooling). This file documents only what is verifiable *right now* and the
> minimal intent for a project named `dns-whitelist`. **Revise it as soon as
> real code, tooling, or conventions land** — every claim below is either a
> verified fact or an explicit assumption, never an unverified guess.

## Verified facts

- **Remote:** `https://github.com/MrLuciano/dns-whitelist.git` (HTTPS — see
  *Working in this repo* below for why)
- **Default branch:** `main`
- **Owner:** `MrLuciano`
- **First commit:** `AGENTS.md` only (initial stub; no code yet).
- **GitHub repo:** `isEmpty=false`, `defaultBranchRef.name=main` after init.

## Assumed intent (flag for the user; revise when code lands)

- The name suggests a **plaintext domain allowlist** consumable by common
  DNS-level blockers (Pi-hole, AdGuard Home, NextDNS, dnsmasq, BIND RPZ).
- Assume the canonical list is **`whitelist.txt`**, one domain per line, no
  scheme, no trailing dot, lowercase. (`#` introduces a comment. Blank lines
  ignored. `*.example.com` for wildcards where the consumer supports it.)
- File is read-only from the consumer's perspective; entries are added via
  PRs, not direct edits on a running server.

> If the actual format differs (e.g. hosts-file `0.0.0.0 example.com`,
> JSON/YAML config, generated from sources), **fix this section first**.

## Conventions to confirm and document later

These are required but unknowable today. Add the real values when the
toolchain is chosen; leave them as TODOs in the meantime.

- **Language / runtime:** TODO
- **Test runner & single-test command:** TODO
- **Lint / formatter:** TODO (e.g. `prettier -w .`, `gofmt`, `ruff check`)
- **Build / generate:** TODO
- **CI:** TODO (see `.github/workflows/` once added)
- **Code style / commit-message convention:** TODO

## What this file deliberately does *not* contain

- No guessed commands. Anything not yet decided is `TODO`, not invented.
- No tutorial on Pi-hole / NextDNS / etc. — link to upstream docs when needed.
- No generic advice about Git, DNS, or domains.

## Working in this repo

- Prefer `git status` before and after edits; the working copy has nothing to
  anchor expectations.
- HTTPS is the configured remote and `gh auth git-credential` is the
  credential helper for `https://github.com`, so `git push`/`fetch` "just
  works" as long as `gh auth status` shows an active login.
- SSH (`git@github.com:…`) is not currently configured (no keys in
  `~/.ssh/`). If you switch the remote URL back to SSH, set up
  `ssh-agent` + an added key first, or `git push` will fail with
  `Permission denied (publickey)`.