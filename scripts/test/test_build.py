import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from scripts.build import build_whitelist

FIXTURES = Path(__file__).parent / "fixtures"


class FrozenDateTime:
    """datetime stub that returns a fixed instant for stable golden tests."""

    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 8, tzinfo=tz or UTC)


class TestBuildWhitelist:
    def test_golden_matches(self, tmp_path, monkeypatch):
        # Stub DNS resolve so every domain "succeeds" without hitting the
        # network. (Real resolve will fail for many entries in CI; the
        # golden was captured under the same mock.)
        from scripts.lib import resolve as resolve_mod
        monkeypatch.setattr(resolve_mod, "resolve_domain",
                            lambda d: ["1.2.3.4"])

        # Stub fetch_url to read the real catalog fixture.
        from scripts.lib import fetch as fetch_mod
        catalog = json.loads(
            (FIXTURES / "microsoft365-endpoints.json").read_text()
        )
        def fake_fetch(url, **_):
            return catalog
        monkeypatch.setattr(fetch_mod, "fetch_url", fake_fetch)

        # Freeze datetime so the header "Last refreshed:" line is stable.
        import scripts.build as build_mod
        monkeypatch.setattr(build_mod.datetime, "datetime", FrozenDateTime)

        # Use the real sources/ directory at the repo root.
        sources_dir = Path(__file__).parent.parent.parent / "sources"
        out = build_whitelist(sources_dir=sources_dir)
        golden = (FIXTURES / "golden-whitelist.txt").read_text()
        assert out == golden, (
            "build output differs from golden.\n"
            "Run `python scripts/build.py --out whitelist.txt && "
            "cp whitelist.txt scripts/test/fixtures/golden-whitelist.txt` "
            "and re-pin the date header to refresh the golden."
        )


class TestBuildWhitelistSources:
    """Smoke tests for source loading (don't depend on the golden)."""

    def test_loads_sources(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.dump({
            "service": "A",
            "source_url": "https://example.com/a",
            "fetch": {"type": "json_endpoint", "url": "https://x/a",
                      "domain_keys": ["urls"]},
            "output_section": "A",
        }))
        (tmp_path / "b.yaml").write_text(yaml.dump({
            "service": "B",
            "source_url": "https://example.com/b",
            "fetch": {"type": "json_endpoint", "url": "https://x/b",
                      "domain_keys": ["urls"]},
            "output_section": "B",
        }))
        # No mocks — just verify the loader reads the files.
        from scripts.build import _load_sources
        sources = _load_sources(tmp_path)
        assert [s["service"] for s in sources] == ["A", "B"]

    def test_sections_sorted_alphabetically(self, tmp_path):
        (tmp_path / "z.yaml").write_text(yaml.dump({
            "service": "Zebra",
            "source_url": "https://x/z",
            "fetch": {"type": "json_endpoint", "url": "https://x/z",
                      "domain_keys": ["urls"]},
            "output_section": "Zebra",
        }))
        (tmp_path / "a.yaml").write_text(yaml.dump({
            "service": "Apple",
            "source_url": "https://x/a",
            "fetch": {"type": "json_endpoint", "url": "https://x/a",
                      "domain_keys": ["urls"]},
            "output_section": "Apple",
        }))
        from scripts.build import _load_sources
        sources = _load_sources(tmp_path)
        # _load_sources reads via sorted() on filename; alphabetical a < z.
        assert [s["service"] for s in sources] == ["Apple", "Zebra"]
