from app.config import CountryConfig
from app.discovery.queries import build_queries


def _ph():
    return CountryConfig(
        code="PH",
        name="Philippines",
        english_baseline=0.75,
        timezone="Asia/Manila",
        preferred_channels=["email"],
        cities=["Manila", "Cebu"],
    )


def test_build_queries_expands_cities():
    templates = ["call center {city}"]
    queries = build_queries(_ph(), templates, max_queries=25)
    assert "call center Manila" in queries
    assert "call center Cebu" in queries


def test_build_queries_country_only():
    templates = ["BPO {country}"]
    queries = build_queries(_ph(), templates, max_queries=25)
    assert "BPO Philippines" in queries


def test_build_queries_respects_limit():
    templates = [
        "call center {city}",
        "BPO {city}",
        "outsource {city}",
    ]
    queries = build_queries(_ph(), templates, max_queries=3)
    assert len(queries) <= 3


def test_build_queries_deduplicates():
    templates = ["BPO {country}", "bpo {country}"]
    queries = build_queries(_ph(), templates, max_queries=25)
    assert len(queries) == 1
