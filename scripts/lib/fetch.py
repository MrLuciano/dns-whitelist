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
        except (
            requests.HTTPError,
            requests.ConnectionError,
            RuntimeError,
            json.JSONDecodeError,
        ) as e:
            last_error = e
            if attempt < max_attempts:
                time.sleep(2 ** attempt)

    raise FetchError(f"fetch failed after {max_attempts} attempts: {url}") from last_error
