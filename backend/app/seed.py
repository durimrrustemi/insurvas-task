from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityKind
from app.models.contact import Contact
from app.models.partner import Blocker, Partner, PartnerType, Stage
from app.models.signal import Signal

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

        score_total = round(rng.uniform(0.2, 0.95), 2) if stage != Stage.FOUND else None
        score_english = round(rng.uniform(0.3, 1.0), 2) if score_total else None
        score_insurance = round(rng.uniform(0.1, 0.9), 2) if score_total else None
        score_size = round(rng.uniform(0.2, 0.8), 2) if score_total else None
        score_compliance = round(rng.uniform(0.0, 0.7), 2) if score_total else None

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
            score_total=score_total,
            score_english=score_english,
            score_insurance=score_insurance,
            score_size=score_size,
            score_compliance=score_compliance,
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

    # Add some signals
    criteria = ["english", "insurance", "size", "compliance"]
    for p in partners:
        if p.score_total is not None:
            for criterion in rng.sample(criteria, k=rng.randint(1, 4)):
                signal = Signal(
                    partner_id=p.id,
                    criterion=criterion,
                    key=f"seed_{criterion}_signal",
                    value=round(rng.uniform(0.2, 1.0), 2),
                    weight=round(rng.uniform(0.5, 3.0), 2),
                    source_url=f"https://{p.domain}/about",
                    matched_text=f"Seed {criterion} evidence for {p.name}",
                )
                session.add(signal)

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
