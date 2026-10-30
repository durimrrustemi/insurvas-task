"""Bad sites must never crash discovery: fetch and runner degrade to empty results."""

from __future__ import annotations

import httpx
import pytest

from app.config import load_config
from app.discovery import Candidate
from app.discovery import fetch as fetch_mod
from app.discovery import runner as runner_mod


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_mod, "CACHE_DIR", tmp_path)


def use_transport(monkeypatch, handler) -> None:
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(fetch_mod.httpx, "AsyncClient", factory)


def html_site(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    return httpx.Response(200, html="<html><title>Ok</title><p>hello</p></html>")


def raises(exc_type):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc_type("boom", request=request)

    return handler


@pytest.mark.parametrize(
    ("handler", "expected_status", "has_html"),
    [
        (raises(httpx.ConnectError), 0, False),
        (raises(httpx.ReadTimeout), 0, False),
        (lambda r: httpx.Response(500, html="oops"), 500, True),
        (
            lambda r: httpx.Response(
                200, content=b"%PDF", headers={"content-type": "application/pdf"}
            ),
            200,
            False,
        ),
        # Unknown charset and invalid bytes: decoded with replacement, not a crash.
        (
            lambda r: httpx.Response(
                200,
                content=b"\xff\xfe bad <p>bytes</p>",
                headers={"content-type": "text/html; charset=nope"},
            ),
            200,
            True,
        ),
    ],
    ids=["dns", "timeout", "server_error", "not_html", "unknown_charset"],
)
async def test_bad_site_returns_result_not_exception(
    monkeypatch, handler, expected_status, has_html
):
    use_transport(monkeypatch, handler)
    result = await fetch_mod.fetch_page("https://broken.test/")
    assert result["status"] == expected_status
    assert bool(result["html"]) is has_html


async def test_invalid_url_does_not_raise():
    result = await fetch_mod.fetch_page("http://exa mple .test/")
    assert result["status"] == 0
    assert result["html"] == ""


async def test_robots_disallow_all_blocks(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        return httpx.Response(200, html="<p>secret</p>")

    use_transport(monkeypatch, handler)
    result = await fetch_mod.fetch_page("https://private.test/")
    assert result["status"] == 403
    assert result["html"] == ""


async def test_good_site_is_cached(monkeypatch):
    use_transport(monkeypatch, html_site)
    first = await fetch_mod.fetch_page("https://ok.test/")
    second = await fetch_mod.fetch_page("https://ok.test/")
    assert "hello" in first["html"]
    assert first["from_cache"] is False
    assert second["from_cache"] is True


async def test_runner_survives_broken_source_and_sites(monkeypatch):
    class BrokenSource:
        def __init__(self, key: str) -> None:
            pass

        async def search(self, query: str, country: str) -> list[Candidate]:
            raise ValueError("unexpected payload")

    class GoodSource(BrokenSource):
        async def search(self, query: str, country: str) -> list[Candidate]:
            return [
                Candidate(url="https://ok.test/", domain="ok.test", name="Ok", country=country),
                Candidate(
                    url="https://down.test/", domain="down.test", name="Down", country=country
                ),
            ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "down.test":
            raise httpx.ConnectError("dns", request=request)
        return html_site(request)

    monkeypatch.setattr(runner_mod, "SerperSource", BrokenSource)
    monkeypatch.setattr(runner_mod, "PlacesSource", GoodSource)
    use_transport(monkeypatch, handler)

    result = await runner_mod.run_discovery(
        load_config(), "PH", limit=5, serper_key="x", places_key="y"
    )
    by_domain = {e.candidate.domain: e for e in result.candidates}
    assert set(by_domain) == {"ok.test", "down.test"}
    assert "hello" in by_domain["ok.test"].homepage_text
    assert by_domain["down.test"].homepage_text == ""
