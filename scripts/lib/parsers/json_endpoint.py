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

Returns a deduplicated list of domain strings sorted in DNS order
(rightmost label most significant), e.g. `example.com` precedes
`a.example.com`.
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
    return sorted(set(domains), key=lambda d: tuple(reversed(d.split("."))))
