from __future__ import annotations

from app.config import AppConfig, CountryConfig


def build_queries(
    country: CountryConfig,
    templates: list[str],
    max_queries: int = 25,
) -> list[str]:
    """Build search queries for a country from templates.

    Templates can contain {country}, {city}, and {code} placeholders.
    Each template is expanded for each city, then deduplicated and capped.
    """
    queries: list[str] = []
    seen: set[str] = set()

    for template in templates:
        placeholders = {
            "country": country.name,
            "code": country.code,
        }
        if "{city}" in template:
            for city in country.cities:
                q = template.format(city=city, **placeholders)
                q_lower = q.lower()
                if q_lower not in seen:
                    seen.add(q_lower)
                    queries.append(q)
        else:
            q = template.format(city="", **placeholders).strip()
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                queries.append(q)

        if len(queries) >= max_queries:
            break

    return queries[:max_queries]


def build_queries_from_config(config: AppConfig, country_code: str) -> list[str]:
    """Convenience: build queries for a country code using app config."""
    country = config.get_country(country_code)
    if not country:
        raise ValueError(f"Unknown country code: {country_code}")
    return build_queries(
        country,
        config.query_templates,
        config.max_queries_per_country,
    )
