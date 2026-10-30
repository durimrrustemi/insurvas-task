from app.discovery import Candidate
from app.discovery.dedupe import dedupe_candidates, normalise_domain


def test_normalise_domain_with_scheme():
    assert normalise_domain("https://www.example.com/about") == "example.com"


def test_normalise_domain_no_scheme():
    assert normalise_domain("www.example.com") == "example.com"


def test_normalise_domain_bare():
    assert normalise_domain("example.com") == "example.com"


def test_normalise_domain_trailing_dot():
    assert normalise_domain("example.com.") == "example.com"


def test_dedupe_merges_same_domain():
    candidates = [
        Candidate(
            url="https://example.com/page1",
            domain="",
            name="Example",
            snippet="short",
            source="serper",
        ),
        Candidate(
            url="https://www.example.com/page2",
            domain="",
            name="Example Corp",
            snippet="a longer snippet with more info",
            source="places",
        ),
    ]
    result = dedupe_candidates(candidates)
    assert len(result) == 1
    assert result[0].domain == "example.com"
    # Should keep the longer snippet
    assert "longer" in result[0].snippet


def test_dedupe_filters_blacklisted():
    candidates = [
        Candidate(
            url="https://linkedin.com/company/foo",
            domain="",
            name="LinkedIn",
        ),
        Candidate(
            url="https://realbpo.com",
            domain="",
            name="Real BPO",
        ),
    ]
    result = dedupe_candidates(candidates, exclude_domains=["linkedin.com"])
    assert len(result) == 1
    assert result[0].domain == "realbpo.com"


def test_dedupe_preserves_city():
    candidates = [
        Candidate(
            url="https://bpo.com",
            domain="",
            name="BPO",
            city="",
        ),
        Candidate(
            url="https://bpo.com",
            domain="",
            name="BPO",
            city="Manila",
        ),
    ]
    result = dedupe_candidates(candidates)
    assert len(result) == 1
    assert result[0].city == "Manila"


def test_excluded_domain_matches_subdomains_only():
    candidates = [
        Candidate(url="https://en.wikipedia.org/wiki/BPO", domain="", name="BPO - Wikipedia"),
        Candidate(url="https://notwikipedia.org", domain="", name="Not Wikipedia BPO"),
    ]
    result = dedupe_candidates(candidates, exclude_domains=["wikipedia.org"])
    assert [c.domain for c in result] == ["notwikipedia.org"]


def test_listicle_titles_are_dropped_with_config_patterns():
    from app.config import load_config

    cfg = load_config()
    candidates = [
        Candidate(url="https://a.test", domain="", name="Top 40 call centers in the Philippines"),
        Candidate(url="https://b.test", domain="", name="10 Best BPO Companies in Cebu"),
        Candidate(url="https://c.test", domain="", name="Acme Contact Center | Cebu BPO"),
    ]
    result = dedupe_candidates(candidates, cfg.exclude_domains, cfg.exclude_title_patterns)
    assert [c.domain for c in result] == ["c.test"]


def test_partner_domain_drops_path():
    from app.services.partners import normalise_domain as partner_normalise

    url = "https://www.outsourcing.test/guide/top-call-centers"
    assert partner_normalise(url) == "outsourcing.test"
