import pytest

from scripts.lib.fetch import FetchError, fetch_url


class TestFetchUrl:
    def test_returns_parsed_json(self, monkeypatch, tmp_path):
        def fake_get(url, timeout=None, **kwargs):
            class FakeResp:
                status_code = 200
                text = '{"hello": "world"}'
                def json(self):
                    return {"hello": "world"}
                def raise_for_status(self):
                    pass
            return FakeResp()

        monkeypatch.setattr("scripts.lib.fetch.requests.get", fake_get)
        monkeypatch.setattr("scripts.lib.fetch._cache_path_for",
                            lambda url, cache_dir: tmp_path / "x.json")

        result = fetch_url("https://example.com/api", cache_dir=tmp_path)
        assert result == {"hello": "world"}

    def test_retries_on_5xx_then_succeeds(self, monkeypatch, tmp_path):
        attempts = []

        def fake_get(url, timeout=None, **kwargs):
            attempts.append(1)
            class FakeResp:
                status_code = 200 if len(attempts) >= 2 else 503
                text = '{"ok": true}'
                def json(self):
                    return {"ok": True}
                def raise_for_status(self):
                    if self.status_code >= 500:
                        raise RuntimeError("server error")
            return FakeResp()

        monkeypatch.setattr("scripts.lib.fetch.requests.get", fake_get)
        monkeypatch.setattr("scripts.lib.fetch._cache_path_for",
                            lambda url, cache_dir: tmp_path / "x.json")
        # Disable backoff sleep so the test is fast.
        monkeypatch.setattr("scripts.lib.fetch.time.sleep", lambda _s: None)

        result = fetch_url("https://example.com/api", cache_dir=tmp_path,
                           max_attempts=3)
        assert result == {"ok": True}
        assert len(attempts) == 2

    def test_raises_after_max_attempts(self, monkeypatch, tmp_path):
        def fake_get(url, timeout=None, **kwargs):
            class FakeResp:
                status_code = 503
                text = "boom"
                def json(self):
                    raise ValueError("not json")
                def raise_for_status(self):
                    raise RuntimeError("server error")
            return FakeResp()

        monkeypatch.setattr("scripts.lib.fetch.requests.get", fake_get)
        monkeypatch.setattr("scripts.lib.fetch._cache_path_for",
                            lambda url, cache_dir: tmp_path / "x.json")
        monkeypatch.setattr("scripts.lib.fetch.time.sleep", lambda _s: None)

        with pytest.raises(FetchError):
            fetch_url("https://example.com/api", cache_dir=tmp_path,
                      max_attempts=2)
