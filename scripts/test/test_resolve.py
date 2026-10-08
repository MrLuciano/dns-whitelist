import pytest

from scripts.lib.resolve import ResolutionError, resolve_domain


class TestResolveDomain:
    def test_resolves_known_domain(self, monkeypatch):
        # Pretend dnspython returned A records.
        class FakeAnswer:
            def __str__(self):  # dnspython str() gives the data
                return "1.2.3.4"

        class FakeResolver:
            nameservers = ["1.1.1.1", "8.8.8.8"]
            def resolve(self, name, raise_on_no_answer=False):
                assert name == "example.com"
                return [FakeAnswer()]

        # The resolve.py implementation imports dns.resolver.Resolver lazily
        # inside the function so tests can monkeypatch the class.
        import dns.resolver
        monkeypatch.setattr(dns.resolver, "Resolver", FakeResolver)

        result = resolve_domain("example.com")
        assert result == ["1.2.3.4"]

    def test_rejects_unresolvable(self, monkeypatch):
        import dns.resolver

        class FakeResolver:
            nameservers = ["1.1.1.1", "8.8.8.8"]
            def resolve(self, name, raise_on_no_answer=False):
                import dns.resolver
                raise dns.resolver.NXDOMAIN()

        monkeypatch.setattr(dns.resolver, "Resolver", FakeResolver)

        with pytest.raises(ResolutionError):
            resolve_domain("nx.example.com")
