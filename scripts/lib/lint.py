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
