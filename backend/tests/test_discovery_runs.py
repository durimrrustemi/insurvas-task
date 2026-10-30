"""A discovery run remembers which partners it found, and which were new."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.discovery import Candidate
from app.discovery.runner import DiscoveryResult, EnrichedCandidate
from app.models.partner import Partner
from app.services import discovery as discovery_service


def fake_result(country: str, domains: list[str]) -> DiscoveryResult:
    now = datetime.now(timezone.utc)
    return DiscoveryResult(
        country=country,
        queries_used=["q"],
        candidates=[
            EnrichedCandidate(
                candidate=Candidate(url=f"https://{d}/", domain=d, name=d, country=country),
                homepage_text="Call center outsourcing with 200 seats. TCPA compliant.",
                title=d,
            )
            for d in domains
        ],
        started_at=now,
        finished_at=now,
        total_found=len(domains),
    )


async def test_run_lists_its_candidates_and_marks_new(
    client: AsyncClient, session: AsyncSession, monkeypatch
):
    session.add(Partner(name="Known", domain="known.test", country="PH"))
    await session.flush()

    async def fake_run_discovery(**kwargs):
        return fake_result(kwargs["country_code"], ["known.test", "fresh.test"])

    monkeypatch.setattr(discovery_service, "run_discovery", fake_run_discovery)

    resp = await client.post("/api/v1/discovery/runs", json={"country": "PH", "limit": 5})
    assert resp.status_code == 202, resp.text
    run = resp.json()
    assert (run["found"], run["new"]) == (2, 1)

    candidates = (await client.get(f"/api/v1/discovery/runs/{run['id']}/candidates")).json()
    assert {c["partner"]["domain"]: c["new"] for c in candidates} == {
        "known.test": False,
        "fresh.test": True,
    }


async def test_unknown_run_is_404(client: AsyncClient):
    resp = await client.get(
        "/api/v1/discovery/runs/0190f000-0000-7000-8000-000000000000/candidates"
    )
    assert resp.status_code == 404


async def test_rediscovery_refreshes_type_only_for_untouched_partners(
    session: AsyncSession, monkeypatch
):
    from app.models.partner import PartnerType, Stage

    untouched = Partner(name="A", domain="a.test", country="US", stage=Stage.FOUND)
    contacted = Partner(name="B", domain="b.test", country="US", stage=Stage.CONTACTED)
    session.add_all([untouched, contacted])
    await session.flush()

    result = fake_result("US", ["a.test", "b.test"])
    for e in result.candidates:
        e.homepage_text = "Exclusive final expense leads for sale. Pay per call."

    async def fake_run_discovery(**kwargs):
        return result

    monkeypatch.setattr(discovery_service, "run_discovery", fake_run_discovery)
    await discovery_service.start_discovery(session, "US", 2)

    assert untouched.type == PartnerType.VENDOR
    # Someone is already talking to B; a crawl doesn't overrule what they know.
    assert contacted.type == PartnerType.BPO
