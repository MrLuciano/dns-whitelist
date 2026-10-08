"""Parser for hand-curated domain lists.

Some services (e.g. NetIQ, Cisco AnyConnect, Palo Alto GlobalProtect)
don't publish a machine-readable catalog. For those, the curated FQDNs
are encoded directly in the sources YAML under a `urls:` key. The
parser just emits that list.

`payload` is ignored — there's no upstream fetch for hand-curated lists.
The build orchestrator skips the fetch when `fetch: false` is set in the
YAML's `fetch:` block; this parser is the one that needs to know that.
"""

from __future__ import annotations


def parse(payload, config: dict) -> list[str]:
    """Return the curated FQDN list from `config['urls']`, sorted and deduped.

    Args:
        payload: Ignored. (No upstream fetch for hand-curated lists.)
        config: The `fetch:` block of a sources/*.yaml file. Must contain
                a `urls:` key with a list of FQDN strings.
    """
    urls = config.get("urls", [])
    return sorted(set(urls))
