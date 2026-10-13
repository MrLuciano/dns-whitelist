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

    def test_extra_urls_merged_with_catalog(self):
        # Hand-curated extras should be merged with the catalog output,
        # deduped, and sorted in DNS order. Wildcards are PRESERVED at
        # this layer — build.py strips the `*.` prefix during candidate
        # normalization (and emits the equivalent AdGuard `@@||apex^`).
        config = {
            "domain_keys": ["urls"],
            "extra_urls": [
                "t0.tiles.virtualearth.net",
                "*.bing.com",
                "platform.bing.com",
            ],
        }
        payload = [
            {"urls": ["login.microsoftonline.com", "example.com"]},
        ]
        result = parse(payload, config)
        # DNS-order sort: "com" < "com" < "com" < "com" < "net";
        # within the "com" group, 3-label "bing" < 2-label "example"
        # (because the tiebreaker at position 1 is 'b' < 'e').
        assert result == [
            "*.bing.com",
            "platform.bing.com",
            "example.com",
            "login.microsoftonline.com",
            "t0.tiles.virtualearth.net",
        ]

    def test_extra_urls_empty_list(self):
        config = {"domain_keys": ["urls"], "extra_urls": []}
        payload = [{"urls": ["example.com"]}]
        assert parse(payload, config) == ["example.com"]

    def test_extra_urls_without_filter_catalog(self):
        # Extra URLs work even when no filter is set.
        config = {
            "domain_keys": ["urls"],
            "extra_urls": ["custom.example.com"],
        }
        payload = [{"urls": ["catalog.example.com"]}]
        assert parse(payload, config) == [
            "catalog.example.com",
            "custom.example.com",
        ]
