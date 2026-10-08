# AGENTS.md — dns-whitelist

> **Status: stub.** The repo is currently empty (no source, no manifest, no
> tooling). This file documents only what is verifiable *right now* and the
> minimal intent for a project named `dns-whitelist`. **Revise it as soon as
> real code, tooling, or conventions land** — every claim below is either a
> verified fact or an explicit assumption, never an unverified guess.

## Verified facts

- **Remote:** `git@github.com:MrLuciano/dns-whitelist.git`
- **Default branch:** `main`
- **Owner:** `MrLuciano`
- **Working tree:** empty (only `.git/`). GitHub reports the remote is empty too.
- **No commits yet.**

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
- Use `ssh` (not `https`) when interacting with the remote — only the SSH URL
  is configured in `.git/config`.
- SSH key-based auth to GitHub must be set up; `gh`/`git fetch` will fail
  with `Host key verification failed` until then.