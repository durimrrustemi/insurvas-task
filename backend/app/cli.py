from __future__ import annotations

import asyncio
import logging

import typer

app = typer.Typer()


@app.command()
def seed():
    """Seed the database with 30 synthetic partners."""

    async def _seed():
        from app.db import async_session, engine
        from app.models import Base
        from app.seed import seed_partners

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
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


if __name__ == "__main__":
    app()
