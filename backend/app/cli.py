from __future__ import annotations

import asyncio
import logging

import typer

app = typer.Typer()


@app.command()
def seed(
    if_empty: bool = typer.Option(False, "--if-empty", help="Skip if partners already exist"),
):
    """Seed the database with 30 synthetic partners."""

    async def _seed():
        from sqlalchemy import func, select

        from app.db import async_session
        from app.models.partner import Partner
        from app.seed import seed_partners

        async with async_session() as session:
            count_q = select(func.count()).select_from(Partner)
            existing = (await session.execute(count_q)).scalar_one()
            if existing:
                if if_empty:
                    typer.echo(f"Skipping seed: {existing} partners already present.")
                    return
                typer.echo(f"Refusing to seed: {existing} partners already present.", err=True)
                raise typer.Exit(1)
            partners = await seed_partners(session)
            typer.echo(f"Seeded {len(partners)} partners.")

    asyncio.run(_seed())


@app.command()
def discover(
    country: str = typer.Option(..., help="Country code (e.g., PH)"),
    limit: int = typer.Option(30, help="Max results"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run discovery for a country."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    async def _discover():
        from app.db import async_session
        from app.services.discovery import start_discovery

        async with async_session() as session:
            run = await start_discovery(session, country, limit)
            await session.commit()
            typer.echo(f"Discovery complete: country={run.country} found={run.found} new={run.new}")

    asyncio.run(_discover())


@app.command()
def score(
    country: str = typer.Option(None, help="Country code to filter (optional)"),
    partner_id: str = typer.Option(None, "--partner", "-p", help="Score a single partner by ID"),
    recompute: bool = typer.Option(
        False, "--recompute", help="Only re-apply current config weights to stored evidence"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Score partners based on cached page content."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    async def _score():
        from app.db import async_session
        from app.services.scoring import recompute_scores, score_all_partners, score_partner

        async with async_session() as session:
            if recompute:
                count = await recompute_scores(session, country=country)
                await session.commit()
                typer.echo(f"Recomputed {count} partners with current weights")
            elif partner_id:
                import uuid

                result = await score_partner(session, uuid.UUID(partner_id))
                await session.commit()
                typer.echo(f"Scored: total={result.total} signals={len(result.signals)}")
            else:
                count = await score_all_partners(session, country=country)
                await session.commit()
                typer.echo(f"Scored {count} partners" + (f" in {country}" if country else ""))

    asyncio.run(_score())


if __name__ == "__main__":
    app()
