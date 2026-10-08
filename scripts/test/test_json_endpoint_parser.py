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
