"""Tests for the static_list parser.

static_list is used for hand-curated FQDN lists where the source has
no machine-readable catalog (e.g. NetIQ, Cisco AnyConnect, Palo Alto
GlobalProtect).
"""

from scripts.lib.parsers.static_list import parse


class TestParse:
    def test_returns_static_urls(self):
        config = {"urls": ["a.example.com", "b.example.com"]}
        assert parse(None, config) == ["a.example.com", "b.example.com"]

    def test_dedupes_and_sorts(self):
        config = {"urls": ["b.example.com", "a.example.com", "a.example.com"]}
        assert parse(None, config) == ["a.example.com", "b.example.com"]

    def test_empty_config_returns_empty(self):
        assert parse(None, {}) == []
        assert parse(None, {"urls": []}) == []

    def test_ignores_payload(self):
        # The parser should not look at the payload — it reads the
        # config directly. Pass arbitrary payload to verify it's ignored.
        config = {"urls": ["example.com"]}
        assert parse({"unexpected": "data"}, config) == ["example.com"]
