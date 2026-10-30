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
    result = dedupe_candidates(candidates)
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
