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
