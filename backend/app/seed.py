from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_config
from app.models.activity import Activity, ActivityKind
from app.models.contact import Contact
from app.models.partner import Blocker, Partner, PartnerType, Stage
from app.models.signal import Signal
from app.scoring import SignalResult
from app.scoring.score import compute_scores

COUNTRIES = ["PH", "IN", "ZA", "JM", "GH", "KE"]
CITIES = {
    "PH": ["Manila", "Cebu", "Davao"],
    "IN": ["Bangalore", "Mumbai", "Delhi"],
    "ZA": ["Cape Town", "Johannesburg"],
    "JM": ["Kingston"],
    "GH": ["Accra"],
    "KE": ["Nairobi"],
}
TIMEZONES = {
    "PH": "Asia/Manila",
    "IN": "Asia/Kolkata",
    "ZA": "Africa/Johannesburg",
    "JM": "America/Jamaica",
    "GH": "Africa/Accra",
    "KE": "Africa/Nairobi",
}
STAGES = list(Stage)
BPO_NAMES = [
    "Example BPO",
    "Demo Outsourcing",
    "Sample Call Center",
    "Test Teleservices",
    "Synthetic Contact Hub",
    "Mock Solutions",
    "Placeholder Services",
    "Dummy Corp",
    "Fictitious Global BPO",
    "Specimen Outreach Co",
]


async def seed_partners(session: AsyncSession, count: int = 30) -> list[Partner]:
    # Fixed seed so every fresh setup shows the same demo pipeline.
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    partners = []

    for i in range(count):
        country = COUNTRIES[i % len(COUNTRIES)]
        city = rng.choice(CITIES[country])
        name_base = BPO_NAMES[i % len(BPO_NAMES)]
        name = f"{name_base} {city} {i + 1}"
        domain = f"example-bpo-{i + 1}.test"

        stage = STAGES[i % len(STAGES)]
        days_ago = rng.randint(1, 20)
        now - timedelta(days=days_ago)
        stage_entered = now - timedelta(days=rng.randint(0, days_ago))

        blocker = None
        if i == 5:
            blocker = Blocker.PRICING
        elif i == 12:
            blocker = Blocker.NO_RESPONSE

        partner = Partner(
            name=name,
            domain=domain,
            website=f"https://{domain}",
            country=country,
            city=city,
            timezone=TIMEZONES[country],
            type=PartnerType.BPO,
            stage=stage,
            stage_entered_at=stage_entered,
            blocker=blocker,
        )
        session.add(partner)
        partners.append(partner)

    await session.flush()

    # Add contacts for partners past 'found' stage
    for p in partners:
        if p.stage != Stage.FOUND:
            contact = Contact(
                partner_id=p.id,
                name=f"Contact for {p.name}",
                role="Operations Manager",
                email=f"contact@{p.domain}",
            )
            session.add(contact)

    # Synthetic evidence using the real signal keys and weights from scoring.yaml,
    # scored with the real formula, so every shown score traces back to its rows
    # and a weight change + `make recompute` re-ranks the seed like real data.
    for p in partners:
        results = _synthetic_signals(rng, p)
        for r in results:
            session.add(
                Signal(
                    partner_id=p.id,
                    criterion=r.criterion,
                    key=r.key,
                    value=r.value,
                    weight=r.weight,
                    source_url=r.source_url,
                    matched_text=r.matched_text,
                )
            )
        scores = compute_scores(results, app_config)
        p.score_total = scores.total
        for criterion in ("english", "insurance", "size", "compliance"):
            c = scores.criteria.get(criterion)
            setattr(p, f"score_{criterion}", c.score if c and c.coverage > 0 else None)

    # Add activities
    for p in partners:
        activity = Activity(
            partner_id=p.id,
            kind=ActivityKind.STAGE_CHANGE,
            body=f"Created in stage {p.stage.value} (seed)",
            at=p.created_at,
        )
        session.add(activity)

    await session.commit()
    return partners


def _synthetic_signals(rng: random.Random, p: Partner) -> list[SignalResult]:
    country = app_config.get_country(p.country)
    results = [
        SignalResult(
            criterion="english",
            key="english_baseline",
            value=country.english_baseline if country else 0.5,
            weight=app_config.signals["english"]["english_baseline"].weight,
            source_url="config/countries.yaml",
            matched_text=f"Country baseline for {p.country}",
        )
    ]
    criteria = ["english", "insurance", "size", "compliance"]
    for criterion in rng.sample(criteria, k=rng.randint(1, 4)):
        defs = {k: v for k, v in app_config.signals[criterion].items() if k != "english_baseline"}
        for key in rng.sample(sorted(defs), k=min(len(defs), rng.randint(1, 2))):
            results.append(
                SignalResult(
                    criterion=criterion,
                    key=key,
                    value=round(rng.uniform(0.3, 1.0), 2),
                    weight=defs[key].weight,
                    source_url=f"https://{p.domain}/about",
                    matched_text=f"Synthetic evidence: {defs[key].description}",
                )
            )
    return results
