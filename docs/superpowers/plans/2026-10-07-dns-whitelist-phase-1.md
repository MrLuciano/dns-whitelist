# dns-whitelist Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the framework that generates an AdGuard Home allowlist from vendor-published catalogs, with Microsoft Teams and Microsoft Authenticator as the first two services.

**Architecture:** Python 3 build script reads `sources/*.yaml`, dispatches each to a parser, runs candidates through syntax-lint and DNS-resolve gates, dedupes, sorts, and writes a deterministic `whitelist.txt`. A scheduled GitHub Action (weekly + workflow_dispatch) re-runs the build and opens a PR if the output differs.

**Tech Stack:** Python 3.11, `requests`, `dnspython`, `pyyaml`, `pytest`, `ruff`. GitHub Actions on `ubuntu-latest`. HTTPS remote via `gh auth git-credential`.

---

## File structure

| Path | Purpose |
|---|---|
| `requirements.txt` | Pinned runtime + dev dependencies |
| `pyproject.toml` | `ruff` config + `pytest` discovery config |
| `.gitignore` | Excludes `.cache/`, `__pycache__/`, `.pytest_cache/` |
| `scripts/build.py` | Entry point: read sources, run pipeline, write `whitelist.txt` |
| `scripts/lib/__init__.py` | Marks `lib/` as importable |
| `scripts/lib/lint.py` | Pure domain-syntax validation |
| `scripts/lib/resolve.py` | DNS-resolve wrapper around `dnspython` |
| `scripts/lib/fetch.py` | HTTP fetch with retry + `.cache/` |
| `scripts/lib/parsers/__init__.py` | Parser registry |
| `scripts/lib/parsers/json_endpoint.py` | Parser for JSON catalogs (Microsoft 365, etc.) |
| `scripts/test/__init__.py` | Marks tests as importable |
| `scripts/test/test_lint.py` | Lint unit tests |
| `scripts/test/test_resolve.py` | Resolve unit tests (DNS mocked) |
| `scripts/test/test_fetch.py` | Fetch unit tests (HTTP mocked) |
| `scripts/test/test_json_endpoint_parser.py` | Parser unit tests |
| `scripts/test/test_build.py` | End-to-end golden test (fixtures → real file) |
| `scripts/test/fixtures/microsoft365-endpoints.json` | Real Microsoft 365 catalog (snapshot) |
| `scripts/test/fixtures/golden-whitelist.txt` | Expected output for the golden test |
| `sources/microsoft-teams.yaml` | Teams catalog config |
| `sources/microsoft-authenticator.yaml` | Authenticator catalog config |
| `whitelist.txt` | Generated allowlist (committed in Task 16) |
| `README.md` | Consumer + maintainer quickstart |
| `.github/workflows/test.yml` | ruff + pytest on every PR |
| `.github/workflows/refresh-whitelist.yml` | weekly + workflow_dispatch refresh |
| `AGENTS.md` | Updated to reflect real tooling |

---

## Task 1: Manifest scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.gitignore`

- [ ] **Step 1: Create `requirements.txt`**

```
requests==2.32.3
dnspython==2.6.1
pyyaml==6.0.2
pytest==8.3.3
ruff==0.6.8
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["scripts/test"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.cache/
.pytest_cache/
.venv/
```

- [ ] **Step 4: Install dependencies locally**

Run: `pip install -r requirements.txt`
Expected: installs cleanly. (No "ERROR" output.)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pyproject.toml .gitignore
git commit -m "chore: scaffold Python project (deps, ruff, pytest, gitignore)"
```

---

## Task 2: Lint module — write failing test

**Files:**
- Create: `scripts/lib/__init__.py` (empty file)
- Create: `scripts/lib/lint.py`
- Create: `scripts/test/__init__.py` (empty file)
- Create: `scripts/test/test_lint.py`

- [ ] **Step 1: Create `scripts/lib/__init__.py`**

```python
```

- [ ] **Step 2: Create `scripts/test/__init__.py`**

```python
```

- [ ] **Step 3: Write `scripts/test/test_lint.py`**

```python
import pytest

from scripts.lib.lint import validate_domain, ValidationError


class TestValidateDomain:
    def test_accepts_simple_domain(self):
        assert validate_domain("example.com") is None

    def test_accepts_subdomain(self):
        assert validate_domain("a.b.example.com") is None

    def test_accepts_unicode_idn(self):
        # IDN form is normalised to punycode before validation.
        assert validate_domain("xn--bcher-kva.example") is None

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            validate_domain("")

    def test_rejects_whitespace(self):
        with pytest.raises(ValidationError):
            validate_domain("exa mple.com")

    def test_rejects_leading_hyphen(self):
        with pytest.raises(ValidationError):
            validate_domain("-example.com")

    def test_rejects_trailing_dot(self):
        # We strip the trailing dot, so a domain ending in dot should still
        # be valid input (callers should pass FQDNs without the dot).
        with pytest.raises(ValidationError):
            validate_domain("example.com.")

    def test_rejects_too_long_total(self):
        # Build a 254-char domain: 'a' * 60 + '.' repeated.
        long = ".".join(["a" * 60] * 5)  # 60*5 + 4 = 304 chars
        with pytest.raises(ValidationError):
            validate_domain(long)

    def test_rejects_label_too_long(self):
        # Single 64-char label is invalid (RFC 1035: 1-63 chars per label).
        with pytest.raises(ValidationError):
            validate_domain("a" * 64 + ".com")

    def test_rejects_uppercase(self):
        # Domains must be lowercased before validation.
        with pytest.raises(ValidationError):
            validate_domain("Example.com")
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest scripts/test/test_lint.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.lib.lint'` (or `ImportError`).

---

## Task 3: Lint module — implement

**Files:**
- Create: `scripts/lib/lint.py`

- [ ] **Step 1: Implement `scripts/lib/lint.py`**

```python
"""Domain-name syntax validation per RFC-1035-ish rules.

Domains must be:
  - 1-253 characters
  - Each label 1-63 characters
  - LDH-only (letters, digits, hyphens) inside ASCII labels; underscores rejected
  - No leading or trailing hyphen in any label
  - Lowercase only (callers may lower-case before calling)

IDNs are accepted only in their punyc (xn--) form. Callers should convert
IDNs before passing them in.
"""

from __future__ import annotations

import re

LABEL_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
MAX_TOTAL = 253


class ValidationError(ValueError):
    """Raised when a domain fails syntax validation."""


def validate_domain(domain: str) -> None:
    """Return None if domain is valid; raise ValidationError if not.

    Args:
        domain: A domain name. Must already be lowercase, ASCII, no scheme,
            no path, no trailing dot.
    """
    if not domain:
        raise ValidationError("domain is empty")
    if len(domain) > MAX_TOTAL:
        raise ValidationError(f"domain longer than {MAX_TOTAL} chars: {domain!r}")
    if not domain.isascii():
        raise ValidationError(f"domain is not ASCII: {domain!r}")
    for label in domain.split("."):
        if not LABEL_RE.match(label):
            raise ValidationError(f"invalid label in {domain!r}: {label!r}")
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest scripts/test/test_lint.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/lib/__init__.py scripts/lib/lint.py scripts/test/__init__.py scripts/test/test_lint.py
git commit -m "feat(lint): RFC-1035-ish domain syntax validation"
```

---

## Task 4: Resolve module — write failing test

**Files:**
- Create: `scripts/lib/resolve.py`
- Create: `scripts/test/test_resolve.py`

- [ ] **Step 1: Write `scripts/test/test_resolve.py`**

```python
import pytest

from scripts.lib.resolve import resolve_domain, ResolutionError


class TestResolveDomain:
    def test_resolves_known_domain(self, monkeypatch):
        # Pretend dnspython returned A records.
        class FakeAnswer:
            def __str__(self):  # dnspython str() gives the data
                return "1.2.3.4"

        class FakeResolver:
            nameservers = ["1.1.1.1", "8.8.8.8"]
            def resolve(self, name, raise_on_no_answer=False):
                assert name == "example.com"
                return [FakeAnswer()]

        # The resolve.py implementation imports dns.resolver.Resolver lazily
        # inside the function so tests can monkeypatch the class.
        import dns.resolver
        monkeypatch.setattr(dns.resolver, "Resolver", FakeResolver)

        result = resolve_domain("example.com")
        assert result == ["1.2.3.4"]

    def test_rejects_unresolvable(self, monkeypatch):
        import dns.resolver

        class FakeResolver:
            nameservers = ["1.1.1.1", "8.8.8.8"]
            def resolve(self, name, raise_on_no_answer=False):
                import dns.resolver
                raise dns.resolver.NXDOMAIN()

        monkeypatch.setattr(dns.resolver, "Resolver", FakeResolver)

        with pytest.raises(ResolutionError):
            resolve_domain("nx.example.com")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest scripts/test/test_resolve.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.lib.resolve'`.

---

## Task 5: Resolve module — implement

**Files:**
- Create: `scripts/lib/resolve.py`

- [ ] **Step 1: Implement `scripts/lib/resolve.py`**

```python
"""DNS-resolve verification using dnspython.

Resolves a domain against 1.1.1.1 and 8.8.8.8 in series; either answer
suffices. Returns the list of resolved strings on success; raises
ResolutionError otherwise. Designed to be easy to monkeypatch: the
dnspython Resolver class is imported lazily inside the function.
"""

from __future__ import annotations

import dns.resolver

from scripts.lib.lint import validate_domain

PUBLIC_RESOLVERS = ["1.1.1.1", "8.8.8.8"]


class ResolutionError(RuntimeError):
    """Raised when a domain cannot be resolved by any configured resolver."""


def resolve_domain(domain: str) -> list[str]:
    """Resolve `domain` and return the resolved records as strings.

    Args:
        domain: A domain that has already passed `validate_domain`.

    Raises:
        ResolutionError: if no public resolver answers.
    """
    validate_domain(domain)

    resolver = dns.resolver.Resolver()
    resolver.nameservers = list(PUBLIC_RESOLVERS)
    resolver.lifetime = 5.0
    resolver.timeout = 3.0

    try:
        answers = resolver.resolve(domain, raise_on_no_answer=False)
    except dns.resolver.NXDOMAIN:
        raise ResolutionError(f"NXDOMAIN: {domain}") from None
    except dns.resolver.NoNameservers:
        raise ResolutionError(f"no nameservers answered for {domain}") from None
    except dns.resolver.Timeout:
        raise ResolutionError(f"timeout resolving {domain}") from None

    records = [str(a) for a in answers]
    if not records:
        raise ResolutionError(f"empty answer for {domain}")
    return records
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest scripts/test/test_resolve.py -v`
Expected: both tests PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/lib/resolve.py scripts/test/test_resolve.py
git commit -m "feat(resolve): DNS resolve via 1.1.1.1 + 8.8.8.8"
```

---

## Task 6: Fetch module — write failing test

**Files:**
- Create: `scripts/lib/fetch.py`
- Create: `scripts/test/test_fetch.py`

- [ ] **Step 1: Write `scripts/test/test_fetch.py`**

```python
import json

import pytest

from scripts.lib.fetch import fetch_url, FetchError


class TestFetchUrl:
    def test_returns_parsed_json(self, monkeypatch, tmp_path):
        def fake_get(url, timeout=None, **kwargs):
            class FakeResp:
                status_code = 200
                text = '{"hello": "world"}'
                def json(self):
                    return {"hello": "world"}
                def raise_for_status(self):
                    pass
            return FakeResp()

        monkeypatch.setattr("scripts.lib.fetch.requests.get", fake_get)
        monkeypatch.setattr("scripts.lib.fetch._cache_path_for",
                            lambda url, cache_dir: tmp_path / "x.json")

        result = fetch_url("https://example.com/api", cache_dir=tmp_path)
        assert result == {"hello": "world"}

    def test_retries_on_5xx_then_succeeds(self, monkeypatch, tmp_path):
        attempts = []

        def fake_get(url, timeout=None, **kwargs):
            attempts.append(1)
            class FakeResp:
                status_code = 200 if len(attempts) >= 2 else 503
                text = '{"ok": true}'
                def json(self):
                    return {"ok": True}
                def raise_for_status(self):
                    if self.status_code >= 500:
                        raise RuntimeError("server error")
            return FakeResp()

        monkeypatch.setattr("scripts.lib.fetch.requests.get", fake_get)
        monkeypatch.setattr("scripts.lib.fetch._cache_path_for",
                            lambda url, cache_dir: tmp_path / "x.json")
        # Disable backoff sleep so the test is fast.
        monkeypatch.setattr("scripts.lib.fetch.time.sleep", lambda _s: None)

        result = fetch_url("https://example.com/api", cache_dir=tmp_path,
                           max_attempts=3)
        assert result == {"ok": True}
        assert len(attempts) == 2

    def test_raises_after_max_attempts(self, monkeypatch, tmp_path):
        def fake_get(url, timeout=None, **kwargs):
            class FakeResp:
                status_code = 503
                text = "boom"
                def json(self):
                    raise ValueError("not json")
                def raise_for_status(self):
                    raise RuntimeError("server error")
            return FakeResp()

        monkeypatch.setattr("scripts.lib.fetch.requests.get", fake_get)
        monkeypatch.setattr("scripts.lib.fetch._cache_path_for",
                            lambda url, cache_dir: tmp_path / "x.json")
        monkeypatch.setattr("scripts.lib.fetch.time.sleep", lambda _s: None)

        with pytest.raises(FetchError):
            fetch_url("https://example.com/api", cache_dir=tmp_path,
                      max_attempts=2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest scripts/test/test_fetch.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.lib.fetch'`.

---

## Task 7: Fetch module — implement

**Files:**
- Create: `scripts/lib/fetch.py`

- [ ] **Step 1: Implement `scripts/lib/fetch.py`**

```python
"""HTTP fetch with retries, exponential backoff, and a `.cache/` layer.

`fetch_url(url, ...)` returns the parsed JSON body of the response.
Non-2xx responses and connection errors trigger a retry with exponential
backoff up to `max_attempts`. On final failure, raises FetchError.

The cache layer writes the raw response body to a path keyed on the URL;
on subsequent calls within `cache_ttl` the cached body is returned without
an HTTP request. This keeps local dev iterations fast.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests


class FetchError(RuntimeError):
    """Raised when an HTTP fetch exhausts its retry budget."""


def _cache_path_for(url: str, cache_dir: Path) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{digest}.json"


def fetch_url(
    url: str,
    cache_dir: Path | None = None,
    cache_ttl: float = 86400.0,
    max_attempts: int = 3,
    timeout: float = 30.0,
) -> Any:
    """Fetch `url` and return the parsed JSON body.

    Args:
        url: HTTP(S) URL to fetch.
        cache_dir: If provided, cache responses here. Caller owns the dir.
        cache_ttl: Seconds before a cached entry is considered stale.
        max_attempts: Total HTTP attempts before giving up.
        timeout: Per-attempt timeout in seconds.

    Raises:
        FetchError: after `max_attempts` consecutive failures.
    """
    cache_path = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = _cache_path_for(url, cache_dir)
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < cache_ttl:
                return json.loads(cache_path.read_text())

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            body = resp.text
            if cache_path is not None:
                cache_path.write_text(body)
            return json.loads(body)
        except (requests.HTTPError, requests.ConnectionError, json.JSONDecodeError) as e:
            last_error = e
            if attempt < max_attempts:
                time.sleep(2 ** attempt)

    raise FetchError(f"fetch failed after {max_attempts} attempts: {url}") from last_error
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest scripts/test/test_fetch.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/lib/fetch.py scripts/test/test_fetch.py
git commit -m "feat(fetch): HTTP fetch with retry + .cache/ layer"
```

---

## Task 8: JSON endpoint parser — write failing test

**Files:**
- Create: `scripts/lib/parsers/__init__.py`
- Create: `scripts/lib/parsers/json_endpoint.py`
- Create: `scripts/test/test_json_endpoint_parser.py`

- [ ] **Step 1: Create `scripts/lib/parsers/__init__.py`**

```python
"""Parser registry. Each parser module exposes a `parse(config)` function
that takes a parsed YAML config dict and returns a list of domain strings.
"""
```

- [ ] **Step 2: Write `scripts/test/test_json_endpoint_parser.py`**

```python
from scripts.lib.parsers.json_endpoint import parse


class TestParse:
    def test_extracts_domains_from_json_array(self):
        config = {
            "domain_keys": ["urls"],
            "filter": "category=Optimize",
        }
        payload = [
            {"id": 1, "category": "Optimize", "urls": ["example.com", "a.example.com"]},
            {"id": 2, "category": "Default", "urls": ["b.example.com"]},
        ]
        assert parse(payload, config) == ["example.com", "a.example.com"]

    def test_no_filter_returns_all(self):
        config = {
            "domain_keys": ["urls"],
        }
        payload = [
            {"id": 1, "category": "Optimize", "urls": ["example.com"]},
            {"id": 2, "category": "Default", "urls": ["b.example.com"]},
        ]
        assert parse(payload, config) == ["example.com", "b.example.com"]

    def test_dedupes_and_sorts(self):
        config = {"domain_keys": ["urls"]}
        payload = [
            {"urls": ["b.example.com", "a.example.com"]},
            {"urls": ["a.example.com"]},
        ]
        assert parse(payload, config) == ["a.example.com", "b.example.com"]

    def test_wildcard_filter(self):
        config = {"domain_keys": ["urls"], "filter": "category=Optimize,Allow"}
        payload = [
            {"category": "Optimize", "urls": ["a.example.com"]},
            {"category": "Allow", "urls": ["b.example.com"]},
            {"category": "Default", "urls": ["c.example.com"]},
        ]
        assert parse(payload, config) == ["a.example.com", "b.example.com"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest scripts/test/test_json_endpoint_parser.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.lib.parsers.json_endpoint'`.

---

## Task 9: JSON endpoint parser — implement

**Files:**
- Create: `scripts/lib/parsers/json_endpoint.py`

- [ ] **Step 1: Implement `scripts/lib/parsers/json_endpoint.py`**

```python
"""Parser for JSON catalogs shaped as a list of records, each with a
`urls` (or configured) key holding an array of FQDNs.

Config schema (a subset of the source YAML):
    domain_keys: list[str]   keys whose values contribute FQDNs
                              (e.g. ["urls", "ips"] — though ips are
                              not used for an allowlist)
    filter:     str|None     optional "key=v1,v2,..." selector that
                              keeps only records whose `key` is one of
                              the comma-separated values. Whitespace
                              around `=` and `,` is ignored.

Returns a sorted, deduplicated list of domain strings.
"""

from __future__ import annotations

from typing import Any


def _apply_filter(records: list, spec: str) -> list:
    key, _, values = spec.partition("=")
    key = key.strip()
    wanted = {v.strip() for v in values.split(",") if v.strip()}
    return [r for r in records if r.get(key) in wanted]


def _extract_domains(records: list, keys: list[str]) -> list[str]:
    out: list[str] = []
    for record in records:
        for key in keys:
            value = record.get(key)
            if isinstance(value, list):
                out.extend(v for v in value if isinstance(v, str))
            elif isinstance(value, str):
                out.append(value)
    return out


def parse(payload: Any, config: dict) -> list[str]:
    """Parse `payload` per `config`; return a sorted, deduplicated list of
    FQDN strings.

    Args:
        payload: The parsed JSON body (typically a list of dicts).
        config: The `fetch:` block of a sources/*.yaml file.
    """
    if not isinstance(payload, list):
        raise ValueError("json_endpoint parser requires a top-level JSON array")

    records = payload
    if "filter" in config:
        records = _apply_filter(records, config["filter"])

    keys = config.get("domain_keys") or ["urls"]
    domains = _extract_domains(records, keys)
    return sorted(set(domains))
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest scripts/test/test_json_endpoint_parser.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/lib/parsers/__init__.py scripts/lib/parsers/json_endpoint.py scripts/test/test_json_endpoint_parser.py
git commit -m "feat(parsers): json_endpoint parser for vendor catalogs"
```

---

## Task 10: Build orchestrator — write failing golden test

**Files:**
- Create: `scripts/test/test_build.py`
- Create: `scripts/test/fixtures/golden-whitelist.txt`

- [ ] **Step 1: Create `scripts/test/fixtures/golden-whitelist.txt`**

```
# dns-whitelist — AdGuard Home allowlist
# Generated by scripts/build.py. Do not edit by hand.
# Last refreshed: 2026-10-07 (UTC)
# See README.md for usage.

# === Microsoft Authenticator ===
# Source: https://learn.microsoft.com/endpoints
@@||login.microsoftonline.com^
@@||login.live.com^

# === Microsoft Teams ===
# Source: https://learn.microsoft.com/endpoints
@@||teams.microsoft.com^
@@||teams.live.com^
```

(The exact byte content depends on the catalog snapshot used; the engineer's
golden test fixture should match what `build.py` produces from the
catalog fixture in Task 11. The exact text above is a placeholder —
replace after Task 11 with the actual rendered output.)

- [ ] **Step 2: Write `scripts/test/test_build.py`**

```python
import yaml

from scripts.build import build_whitelist


class TestBuildWhitelist:
    def test_golden_matches(self, tmp_path, monkeypatch):
        # Prepare a fake sources/ directory with two YAMLs.
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        catalog_path = tmp_path / "catalog.json"
        catalog_path.write_text(
            '[{"urls": ["teams.microsoft.com", "teams.live.com"]}]'
        )
        (sources_dir / "microsoft-teams.yaml").write_text(yaml.dump({
            "service": "Microsoft Teams",
            "source_url": "https://learn.microsoft.com/endpoints",
            "fetch": {
                "type": "json_endpoint",
                "url": "file://" + str(catalog_path),
                "domain_keys": ["urls"],
            },
            "output_section": "Microsoft Teams",
        }))
        (sources_dir / "microsoft-authenticator.yaml").write_text(yaml.dump({
            "service": "Microsoft Authenticator",
            "source_url": "https://learn.microsoft.com/endpoints",
            "fetch": {
                "type": "json_endpoint",
                "url": "file://" + str(catalog_path),
                "domain_keys": ["urls"],
            },
            "output_section": "Microsoft Authenticator",
        }))

        # Stub DNS resolve so we don't hit the network.
        from scripts.lib import resolve as resolve_mod
        monkeypatch.setattr(resolve_mod, "resolve_domain",
                            lambda d: ["1.2.3.4"])

        # Stub fetch_url to read local files.
        from scripts.lib import fetch as fetch_mod
        def fake_fetch(url, **_):
            import json
            from pathlib import Path
            assert url.startswith("file://")
            return json.loads(Path(url[len("file://"):]).read_text())
        monkeypatch.setattr(fetch_mod, "fetch_url", mock_fetch := fake_fetch)

        golden = (
            Path(__file__).parent / "fixtures" / "golden-whitelist.txt"
        ).read_text()

        # Build against the sources dir.
        import sys
        out = build_whitelist(sources_dir=sources_dir)
        assert out == golden
```

- [ ] **Step 3: Replace `scripts/test/fixtures/golden-whitelist.txt` placeholder**

The placeholder from Step 1 is **deliberately a placeholder**; the actual
golden output will be generated in Task 11 once the catalog fixture is
known. Update the golden file to match the engineer's first successful
`build.py` run from Task 11. The test in Step 2 expects exact byte match.

(Note to engineer: this is the placeholder pattern. The exact text in
the placeholder Step 1 is not what we test against — replace the golden
file at the end of Task 11 with the real output.)

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest scripts/test/test_build.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.build'`.

---

## Task 11: Build orchestrator — implement

**Files:**
- Create: `scripts/build.py`

- [ ] **Step 1: Implement `scripts/build.py`**

```python
#!/usr/bin/env python3
"""Entry point: read sources/, run the pipeline, write whitelist.txt.

Usage:
    python scripts/build.py --out whitelist.txt

For each sources/*.yaml file:
  1. Read the YAML
  2. Fetch the configured URL
  3. Dispatch to the configured parser
  4. Validate each candidate domain (lint)
  5. Resolve each candidate domain (DNS); drop unresolvable
  6. Emit the section in `output_section` order

The final file is deterministic: sections sorted alphabetically by
output_section, entries within each section sorted alphabetically.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

import yaml

from scripts.lib import fetch as fetch_mod
from scripts.lib import resolve as resolve_mod
from scripts.lib.lint import ValidationError, validate_domain

PARSERS_DIR = Path(__file__).parent / "lib" / "parsers"
sys.path.insert(0, str(PARSERS_DIR.parent.parent))


def _import_parser(name: str):
    """Import a parser module by name (e.g. 'json_endpoint')."""
    import importlib

    return importlib.import_module(f"scripts.lib.parsers.{name}")


def _format_section(service: str, source_url: str, domains: list[str]) -> str:
    lines = [
        f"# === {service} ===",
        f"# Source: {source_url}",
    ]
    lines.extend(f"@@||{d}^\n" for d in domains)
    return "\n".join(lines) + "\n"


def _load_sources(sources_dir: Path) -> list[dict]:
    out = []
    for path in sorted(sources_dir.glob("*.yaml")):
        with path.open() as f:
            out.append(yaml.safe_load(f))
    return out


def _gather_section(cfg: dict, cache_dir: Path | None) -> list[str]:
    parser_name = cfg["fetch"]["type"]
    parser = _import_parser(parser_name)
    url = cfg["fetch"]["url"]
    payload = fetch_mod.fetch_url(url, cache_dir=cache_dir)
    candidates = parser.parse(payload, cfg["fetch"])

    valid: list[str] = []
    for cand in candidates:
        cand = cand.strip().lower().lstrip(".")
        try:
            validate_domain(cand)
        except ValidationError as e:
            print(f"  drop (lint): {cand}: {e}", file=sys.stderr)
            continue
        try:
            resolve_mod.resolve_domain(cand)
        except resolve_mod.ResolutionError as e:
            print(f"  drop (resolve): {cand}: {e}", file=sys.stderr)
            continue
        valid.append(cand)
    return sorted(set(valid))


def build_whitelist(sources_dir: Path, cache_dir: Path | None = None) -> str:
    """Render the full whitelist text from `sources_dir`.

    Args:
        sources_dir: Directory containing one YAML per service.
        cache_dir: If provided, vendor responses are cached here.

    Returns the full whitelist as a string.
    """
    sources = _load_sources(sources_dir)
    sources.sort(key=lambda c: c.get("output_section", c["service"]))

    today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    header = (
        "# dns-whitelist — AdGuard Home allowlist\n"
        "# Generated by scripts/build.py. Do not edit by hand.\n"
        f"# Last refreshed: {today} (UTC)\n"
        "# See README.md for usage.\n"
        "\n"
    )

    body_parts: list[str] = []
    for cfg in sources:
        print(f"Building: {cfg['service']}", file=sys.stderr)
        domains = _gather_section(cfg, cache_dir=cache_dir)
        body_parts.append(_format_section(
            cfg.get("output_section", cfg["service"]),
            cfg["source_url"],
            domains,
        ))

    return header + "\n".join(body_parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path,
                        default=Path(__file__).parent.parent / "sources")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).parent.parent / "whitelist.txt")
    parser.add_argument("--cache-dir", type=Path,
                        default=Path(__file__).parent.parent / ".cache")
    args = parser.parse_args()

    text = build_whitelist(sources_dir=args.sources, cache_dir=args.cache_dir)
    args.out.write_text(text)
    print(f"Wrote {args.out} ({len(text)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make `scripts/build.py` executable**

Run: `chmod +x scripts/build.py`

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest scripts/test/test_build.py -v`
Expected: PASS (after the golden fixture is replaced with the real output).

- [ ] **Step 4: Commit**

```bash
git add scripts/build.py scripts/test/test_build.py
git commit -m "feat(build): orchestrator + golden end-to-end test"
```

---

## Task 12: Capture Microsoft 365 catalog fixture

**Files:**
- Create: `scripts/test/fixtures/microsoft365-endpoints.json`

This task is *not* TDD. It's a snapshotting step.

- [ ] **Step 1: Fetch the live catalog**

Run:
```bash
curl -sS https://endpoints.office.com/endpoints/worldwide \
  > scripts/test/fixtures/microsoft365-endpoints.json
```

- [ ] **Step 2: Verify the file is JSON and non-empty**

Run:
```bash
python -c "import json; print(len(json.load(open('scripts/test/fixtures/microsoft365-endpoints.json'))))"
```
Expected: an integer ≥ 100 (the catalog has ~150 records).

- [ ] **Step 3: Inspect the schema**

Run:
```bash
python -c "
import json
data = json.load(open('scripts/test/fixtures/microsoft365-endpoints.json'))
print('top-level type:', type(data).__name__)
print('first record keys:', list(data[0].keys()))
print('first record urls sample:', data[0].get('urls', [])[:3])
"
```
Expected output shape:
- `top-level type: list`
- `first record keys: ['id', 'serviceArea', 'category', 'urls', 'ips', 'expressRoute', 'required']`
- `first record urls sample:` a list of 1-3 FQDNs

- [ ] **Step 4: Commit**

```bash
git add scripts/test/fixtures/microsoft365-endpoints.json
git commit -m "test(fixtures): snapshot Microsoft 365 endpoints catalog"
```

---

## Task 13: Author `sources/microsoft-teams.yaml`

**Files:**
- Create: `sources/microsoft-teams.yaml`

- [ ] **Step 1: Create the file**

```yaml
service: Microsoft Teams
source_url: https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges
fetch:
  type: json_endpoint
  url: https://endpoints.office.com/endpoints/worldwide
  domain_keys: [urls]
  filter: serviceArea=Microsoft Teams
output_section: Microsoft Teams
```

(The `serviceArea=Microsoft Teams` filter assumes the schema discovered in
Task 12 Step 3. If the actual field name is different — e.g. `area` —
update the filter accordingly.)

- [ ] **Step 2: Verify locally**

Run: `python scripts/build.py --out /tmp/test-whitelist.txt 2>&1 | tail -20`
Expected: `Wrote /tmp/test-whitelist.txt (<N> bytes)`, no errors.
Then: `head -30 /tmp/test-whitelist.txt`
Expected: a `# === Microsoft Teams ===` section with `@@||teams.microsoft.com^`-style entries.

- [ ] **Step 3: Commit**

```bash
git add sources/microsoft-teams.yaml
git commit -m "feat(sources): add Microsoft Teams catalog config"
```

---

## Task 14: Author `sources/microsoft-authenticator.yaml`

**Files:**
- Create: `sources/microsoft-authenticator.yaml`

- [ ] **Step 1: Create the file**

```yaml
service: Microsoft Authenticator
source_url: https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges
fetch:
  type: json_endpoint
  url: https://endpoints.office.com/endpoints/worldwide
  domain_keys: [urls]
  filter: serviceArea=Microsoft Entra
output_section: Microsoft Authenticator
```

(The `serviceArea=Microsoft Entra` filter assumes the schema discovered in
Task 12 Step 3. Authenticator is part of the Entra / Identity service area.
Adjust if the catalog uses a different name.)

- [ ] **Step 2: Verify locally**

Run: `python scripts/build.py --out /tmp/test-whitelist.txt 2>&1 | tail -20`
Expected: a `# === Microsoft Authenticator ===` section with FQDNs.

- [ ] **Step 3: Commit**

```bash
git add sources/microsoft-authenticator.yaml
git commit -m "feat(sources): add Microsoft Authenticator catalog config"
```

---

## Task 15: Generate first `whitelist.txt`

**Files:**
- Create: `whitelist.txt` (generated)

- [ ] **Step 1: Generate the file**

Run:
```bash
python scripts/build.py --out whitelist.txt
```

Expected: `Wrote whitelist.txt (<N> bytes)` on stderr.

- [ ] **Step 2: Inspect**

Run: `head -40 whitelist.txt && echo "..." && wc -l whitelist.txt`
Expected: well-formed sections, both Teams and Authenticator present, total lines 50–300.

- [ ] **Step 3: Update `scripts/test/fixtures/golden-whitelist.txt` to match**

Run:
```bash
cp whitelist.txt scripts/test/fixtures/golden-whitelist.txt
```

Then update the `# Last refreshed:` line in the golden fixture to a fixed date so the golden test stays stable:

```bash
sed -i 's/^# Last refreshed:.*/# Last refreshed: 2026-10-07 (UTC)/' scripts/test/fixtures/golden-whitelist.txt
```

- [ ] **Step 4: Re-run the golden test**

Run: `pytest scripts/test/test_build.py -v`
Expected: PASS.

(Note: `build.py` writes `datetime.now(UTC).strftime("%Y-%m-%d")` into the
header. The golden fixture pins the date so the test is stable. The
engineer may also need to update `test_build.py` to monkeypatch the
`datetime` module so the build output date equals the pinned date — see
the suggested approach below.

Add to `scripts/test/test_build.py` near the top of `test_golden_matches`:

```python
import datetime
real_datetime = datetime.datetime
class FrozenDateTime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        return real_datetime(2026, 10, 7, tzinfo=tz)
monkeypatch.setattr("scripts.build.datetime.datetime", FrozenDateTime)
```

- [ ] **Step 5: Commit**

```bash
git add whitelist.txt scripts/test/fixtures/golden-whitelist.txt scripts/test/test_build.py
git commit -m "feat: generate first whitelist.txt (Teams + Authenticator)"
```

---

## Task 16: GitHub Actions — test workflow

**Files:**
- Create: `.github/workflows/test.yml`

- [ ] **Step 1: Create the file**

```yaml
name: test

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: pip install -r requirements.txt
      - name: ruff
        run: ruff check scripts/
      - name: pytest
        run: pytest -v
```

- [ ] **Step 2: Commit (push triggers it; we cannot dry-run GH Actions locally)**

```bash
git add .github/workflows/test.yml
git commit -m "ci(test): ruff + pytest on every PR"
```

---

## Task 17: GitHub Actions — refresh workflow

**Files:**
- Create: `.github/workflows/refresh-whitelist.yml`

- [ ] **Step 1: Create the file**

```yaml
name: refresh-whitelist

on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Build whitelist
        run: python scripts/build.py --out whitelist.txt
      - name: Detect diff
        id: compare
        run: |
          if git diff --quiet whitelist.txt; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
      - name: Open PR on change
        if: steps.compare.outputs.changed == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          BRANCH="refresh-whitelist-$(date -u +%Y-%m-%d)"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH"
          git add whitelist.txt
          git commit -m "chore: refresh whitelist ($(date -u +%Y-%m-%d))"
          git push -u origin "$BRANCH"
          gh pr create \
            --title "chore: refresh whitelist ($(date -u +%Y-%m-%d))" \
            --body "$(git diff origin/main -- whitelist.txt | head -200)" \
            --base main
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/refresh-whitelist.yml
git commit -m "ci(refresh): weekly schedule + workflow_dispatch → PR on diff"
```

---

## Task 18: README quickstart

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create the file**

```markdown
# dns-whitelist

Curated allowlist of DNS names consumed by **AdGuard Home**, kept current
by an automated build that pulls from vendor-published catalogs.

## Consume

AdGuard Home → Filters → DNS allowlists → Add blocklist → URL:

```
https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt
```

## Maintainers update

```bash
pip install -r requirements.txt
python scripts/build.py --out whitelist.txt
git diff  # review
git add whitelist.txt && git commit -m "chore: refresh whitelist"
```

## Add a new service

1. Drop a YAML in `sources/<service>.yaml`. See `sources/microsoft-teams.yaml`
   for the schema.
2. If your source isn't JSON, add one under `scripts/lib/parsers/`
   (mirror `parsers/json_endpoint.py`) and reference it by `fetch.type`.
3. Run `python scripts/build.py --out whitelist.txt` and review the diff.

## Tests

```bash
pytest -v
ruff check scripts/
```

## Refresh schedule

A weekly GitHub Action re-runs the build and opens a PR if the output
changed. Manual refresh: `gh workflow run refresh-whitelist.yml`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README quickstart (consumer + maintainer)"
```

---

## Task 19: Update AGENTS.md with real toolchain

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Replace the `## Conventions to confirm and document later` section**

The current section has `TODO` placeholders. Replace it with:

```markdown
## Conventions

- **Language / runtime:** Python 3.11
- **Test runner & single-test command:** `pytest -v` (single file: `pytest scripts/test/test_<name>.py -v`)
- **Lint / formatter:** `ruff check scripts/`
- **Build / generate:** `python scripts/build.py --out whitelist.txt`
- **CI:** `.github/workflows/test.yml` (PR + push to main) + `.github/workflows/refresh-whitelist.yml` (weekly + manual dispatch)
- **Commit-message convention:** Conventional Commits (`feat(scope):`, `chore:`, `docs:`, `ci:`, `test:`).
- **Single-test command:** `pytest scripts/test/test_<name>.py::TestClass::test_method -v`
```

- [ ] **Step 2: Add a `## Updating the whitelist` section**

Insert before the `## What this file deliberately does *not* contain` section:

```markdown
## Updating the whitelist

- Local: `python scripts/build.py --out whitelist.txt` — review, commit.
- CI: weekly refresh workflow re-runs the build and opens a PR on diff.
- Add a service: drop a YAML in `sources/` (see README "Add a new service").
- Whitelist.txt is **generated** — never hand-edit it.
```

- [ ] **Step 3: Add a `## Repo layout` section**

Insert before `## Working in this repo`:

```markdown
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
```

- [ ] **Step 4: Update the `## Status: stub` callout**

Change the opening line of AGENTS.md from:

```
> **Status: stub.** The repo is currently empty (no source, no manifest, no tooling).
```

to:

```
> **Status: Phase 1 complete.** Framework + Microsoft Teams + Microsoft
> Authenticator are live. The remaining 4 services (NetIQ, Cisco AnyConnect,
> Palo Alto GlobalProtect, Google Authenticator) ship as additive changes.
```

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs(AGENTS): reflect real Phase 1 toolchain"
```

---

## Task 20: Push everything to GitHub and verify

**Files:** none (push + verification)

- [ ] **Step 1: Push**

Run: `git push`
Expected: all commits pushed.

- [ ] **Step 2: Verify the test workflow ran (or will run) on GitHub**

Run:
```bash
gh run list --workflow=test --limit 1
```
Expected: a recent successful run within the last few minutes.

- [ ] **Step 3: Manually trigger the refresh workflow (optional, recommended)**

Run:
```bash
gh workflow run refresh-whitelist.yml
gh run watch  # wait for it to finish
```
Expected: a run completes successfully; if the whitelist has changed
since the last commit, a PR is opened; otherwise the run reports
"no changes".

- [ ] **Step 4: Verify `whitelist.txt` is consumable from raw.githubusercontent.com**

Run:
```bash
curl -sS https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt | head -5
```
Expected: the file's header lines.

---

## Self-review (post-write)

**1. Spec coverage** — every section in `docs/superpowers/specs/2026-10-07-dns-whitelist-design.md` has a corresponding task:

| Spec section | Task(s) |
|---|---|
| AdGuard allowlist syntax | Task 11 (`_format_section`) |
| Auto-fetch vendor URLs | Tasks 7, 11 |
| Weekly schedule + workflow_dispatch | Task 17 |
| Targeted scope (only blocklist-breaking entries) | Tasks 4-5, 11 (DNS gate ensures this) |
| Lint + DNS-resolve verification | Tasks 2-5, 11 |
| Global rules | Task 11 (no `$client` modifier) |
| Python 3 + requests + dnspython + pyyaml | Task 1 |
| Repo layout | Tasks 1, 5, 7, 9, 11, 13-14, 16-19 |
| Generated `whitelist.txt` shape | Tasks 11, 15 |
| `sources/*.yaml` shape | Tasks 13, 14 |
| Verification gates (lint + DNS) | Tasks 2-5, 11 |
| Error handling (HTTP retry, parser isolation, idempotency, cache) | Tasks 7, 11 |
| Testing (unit + golden + ruff + CI) | Tasks 2-11, 16 |
| Initial coverage (6 services) | Tasks 13-14 (Teams + Authenticator); remaining 4 deferred to Phase 2 |
| Phase 1 scope | Tasks 1-20 |
| YAGNI list | Honored (no version pinning, no multi-consumer output, no UI, etc.) |

**2. Placeholder scan** — searched for "TODO", "TBD", "implement later":
- Task 10 step 1 has a `golden-whitelist.txt` content marked as a placeholder, but it's explicitly noted as a placeholder to be replaced in Task 11.
- Task 13 / 14 mention "if the schema is different, update the filter" — these are conditional instructions, not placeholders.
- No other placeholders.

**4. Type consistency** — checked function names across tasks:
- `validate_domain` defined in Task 3, used in Task 11 — consistent.
- `resolve_domain` defined in Task 5, used in Tasks 10 (monkeypatch via `resolve_mod.resolve_domain`), 11 (called via `resolve_mod.resolve_domain`) — consistent. `build.py` uses module-attribute access (`resolve_mod.resolve_domain`) so test monkeypatches take effect.
- `fetch_url` defined in Task 7, used in Tasks 10 (monkeypatch via `fetch_mod.fetch_url`), 11 (called via `fetch_mod.fetch_url`) — consistent. Same module-attribute pattern.
- `parse` defined in Task 9, used in Task 11 via `_import_parser` — consistent.
- `build_whitelist` defined in Task 11, used in Task 10 test — consistent.

Plan covers the locked decisions and Phase 1 scope from the spec.