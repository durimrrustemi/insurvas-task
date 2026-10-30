"""API tests against Postgres (rolled back per test), MOCK_LLM=1."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.models.activity import Activity, ActivityKind
from app.models.partner import Blocker, Partner, Stage

TERMS = {
    "test_batch_size": 50,
    "price_per_transfer": 18,
    "daily_volume": 40,
    "hours": "9-17 EST",
    "quality_threshold": "60% contact rate",
}


async def create_partner(client: AsyncClient, domain: str = "example-bpo.test") -> dict:
    resp = await client.post(
        "/api/v1/partners",
        json={"name": "Example BPO Cebu", "domain": domain, "country": "PH"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def move(client: AsyncClient, pid: str, to: str, reason: str | None = None):
    return await client.post(f"/api/v1/partners/{pid}/stage", json={"to": to, "reason": reason})


async def confirm_gate(client: AsyncClient, pid: str, gate: str, ok: bool = True):
    return await client.post(
        f"/api/v1/partners/{pid}/signals",
        json={"criterion": "gate", "key": gate, "value": 1 if ok else 0},
    )


class TestPartners:
    async def test_create_normalises_domain_and_rejects_duplicate(self, client: AsyncClient):
        p = await create_partner(client, "https://www.Example-BPO.test/")
        assert p["domain"] == "example-bpo.test"
        assert p["stage"] == "found"

        resp = await client.post(
            "/api/v1/partners",
            json={"name": "Dup", "domain": "example-bpo.test", "country": "PH"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "conflict"

    async def test_list_shape(self, client: AsyncClient):
        await create_partner(client)
        body = (await client.get("/api/v1/partners?limit=5")).json()
        assert set(body) == {"items", "total", "limit", "offset"}
        assert body["total"] == 1
        assert body["limit"] == 5

    async def test_blocker_change_is_logged(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        await client.patch(f"/api/v1/partners/{pid}", json={"blocker": "pricing"})
        await client.patch(f"/api/v1/partners/{pid}", json={"blocker": None})
        acts = (await client.get(f"/api/v1/partners/{pid}/activities")).json()
        assert sorted(a["body"] for a in acts if a["kind"] == "blocker") == [
            "blocker: cleared",
            "blocker: pricing",
        ]

    async def test_filter_by_type(self, client: AsyncClient):
        await create_partner(client, "bpo.test")
        resp = await client.post(
            "/api/v1/partners",
            json={"name": "Leads Co", "domain": "leads.test", "country": "US", "type": "vendor"},
        )
        assert resp.status_code == 201
        vendors = (await client.get("/api/v1/partners?type=vendor")).json()
        assert [p["domain"] for p in vendors["items"]] == ["leads.test"]
        assert vendors["total"] == 1

    async def test_unknown_partner_is_404_with_error_shape(self, client: AsyncClient):
        resp = await client.get("/api/v1/partners/0190f000-0000-7000-8000-000000000000")
        assert resp.status_code == 404
        err = resp.json()["error"]
        assert err["code"] == "not_found"
        assert "message" in err and "details" in err


class TestStageFlow:
    async def test_invalid_transition_is_409(self, client: AsyncClient):
        p = await create_partner(client)
        resp = await move(client, p["id"], "signed")
        assert resp.status_code == 409
        err = resp.json()["error"]
        assert err["code"] == "invalid_transition"
        assert err["details"]["allowed"] == ["contacted", "lost"]

    async def test_found_to_signed_with_full_timeline(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        await client.post(f"/api/v1/partners/{pid}/contacts", json={"name": "Maria Santos"})
        for to in ["contacted", "replied", "in_talks"]:
            assert (await move(client, pid, to)).status_code == 200, to

        blocked = await move(client, pid, "test_calls")
        assert blocked.status_code == 422
        err = blocked.json()["error"]
        assert err["code"] == "gate_blocked"
        assert set(err["details"]["failed"]) == {
            "gate:us_hours",
            "gate:compliance",
            "terms:test_batch_size",
        }

        assert (await confirm_gate(client, pid, "us_hours")).status_code == 201
        assert (await confirm_gate(client, pid, "compliance")).status_code == 201
        patched = await client.patch(f"/api/v1/partners/{pid}", json={"engagement_terms": TERMS})
        assert patched.status_code == 200, patched.text

        readiness = (await client.get(f"/api/v1/partners/{pid}/readiness")).json()
        assert readiness["gates"] == {"us_hours": "confirmed", "compliance": "confirmed"}
        to_test = next(t for t in readiness["transitions"] if t["to"] == "test_calls")
        assert to_test["ready"] is True

        assert (await move(client, pid, "test_calls")).status_code == 200
        assert (await move(client, pid, "signed", "18 USD/transfer")).status_code == 200

        acts = (await client.get(f"/api/v1/partners/{pid}/activities")).json()
        stage_changes = [a["body"] for a in acts if a["kind"] == "stage_change"]
        assert stage_changes[0] == "test_calls -> signed: 18 USD/transfer"
        assert len(stage_changes) == 5

    async def test_in_talks_without_contact_is_blocked(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        await move(client, pid, "contacted")
        await move(client, pid, "replied")
        resp = await move(client, pid, "in_talks")
        # in_talks needs a named contact
        assert resp.status_code == 422
        assert resp.json()["error"]["details"]["failed"] == ["contact"]

    async def test_gate_no_moves_partner_to_lost(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        await move(client, pid, "contacted")
        await confirm_gate(client, pid, "compliance", ok=False)

        p = (await client.get(f"/api/v1/partners/{pid}")).json()
        assert p["stage"] == "lost"
        acts = (await client.get(f"/api/v1/partners/{pid}/activities")).json()
        assert any(a["body"] == "contacted -> lost: gate:compliance" for a in acts)

    async def test_unknown_gate_is_404(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        assert (await confirm_gate(client, pid, "no_such_gate")).status_code == 404

    async def test_rescore_keeps_manual_gate_ticks(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        await confirm_gate(client, pid, "compliance")
        assert (await client.post(f"/api/v1/partners/{pid}/score")).status_code == 200
        readiness = (await client.get(f"/api/v1/partners/{pid}/readiness")).json()
        assert readiness["gates"]["compliance"] == "confirmed"


class TestBoardAndAttention:
    async def test_board_has_every_stage(self, client: AsyncClient):
        await create_partner(client)
        board = (await client.get("/api/v1/board")).json()
        assert board["stages"] == [s.value for s in Stage]
        assert list(board["columns"]) == board["stages"]
        assert board["transitions"]["found"] == ["contacted", "lost"]
        assert len(board["columns"]["found"]) == 1

    async def test_attention_flags_untouched_and_blocked(self, client: AsyncClient, session):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=4)
        quiet = Partner(
            name="Quiet BPO",
            domain="quiet.test",
            country="PH",
            stage=Stage.CONTACTED,
            stage_entered_at=old,
        )
        blocked = Partner(
            name="Blocked BPO",
            domain="blocked.test",
            country="PH",
            stage=Stage.IN_TALKS,
            stage_entered_at=now,
            blocker=Blocker.PRICING,
        )
        fresh = Partner(
            name="Fresh BPO",
            domain="fresh.test",
            country="PH",
            stage=Stage.CONTACTED,
            stage_entered_at=now,
        )
        session.add_all([quiet, blocked, fresh])
        await session.flush()
        session.add_all(
            [
                Activity(partner_id=quiet.id, kind=ActivityKind.TOUCH, at=old),
                Activity(partner_id=blocked.id, kind=ActivityKind.TOUCH, at=now),
                Activity(partner_id=fresh.id, kind=ActivityKind.TOUCH, at=now),
            ]
        )
        await session.flush()

        items = (await client.get("/api/v1/attention")).json()["items"]
        by_name = {i["partner"]["name"]: i for i in items}
        assert "Fresh BPO" not in by_name
        assert "no touch for 4d" in by_name["Quiet BPO"]["reasons"]
        assert "blocker: pricing" in by_name["Blocked BPO"]["reasons"]


class TestOutreach:
    async def test_empty_body_uses_country_preferred_channels(self, client: AsyncClient):
        # The UI posts {} (no channel filter); this used to be a 422.
        pid = (await create_partner(client))["id"]  # PH: email + whatsapp
        resp = await client.post(f"/api/v1/partners/{pid}/outreach", json={})
        assert resp.status_code == 201, resp.text
        msgs = resp.json()
        assert {m["channel"] for m in msgs} == {"email", "whatsapp"}
        assert all(m["status"] == "draft" for m in msgs)

    async def test_generate_for_one_channel_respects_limit(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        resp = await client.post(
            f"/api/v1/partners/{pid}/outreach", json={"channels": ["whatsapp"]}
        )
        assert resp.status_code == 201, resp.text
        msgs = resp.json()
        assert msgs and {m["channel"] for m in msgs} == {"whatsapp"}
        assert all(len(m["body"]) <= 300 for m in msgs)

    async def test_unknown_channel_is_422(self, client: AsyncClient):
        pid = (await create_partner(client))["id"]
        resp = await client.post(f"/api/v1/partners/{pid}/outreach", json={"channels": ["fax"]})
        assert resp.status_code == 422
