from pathlib import Path

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
        monkeypatch.setattr(fetch_mod, "fetch_url", fake_fetch)

        golden = (
            Path(__file__).parent / "fixtures" / "golden-whitelist.txt"
        ).read_text()

        # Build against the sources dir.
        out = build_whitelist(sources_dir=sources_dir)
        assert out == golden
