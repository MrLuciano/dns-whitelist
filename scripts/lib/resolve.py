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
