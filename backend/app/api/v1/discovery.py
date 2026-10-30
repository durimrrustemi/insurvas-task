from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import NotFound
from app.schemas.discovery import DiscoveryRunCreate, DiscoveryRunRead
from app.services import discovery as discovery_service

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/runs", response_model=list[DiscoveryRunRead])
async def list_runs(
    session: AsyncSession = Depends(get_session),
):
    runs = await discovery_service.list_discovery_runs(session)
    return [DiscoveryRunRead.model_validate(r) for r in runs]


@router.post("/runs", response_model=DiscoveryRunRead, status_code=202)
async def create_run(
    data: DiscoveryRunCreate,
    session: AsyncSession = Depends(get_session),
):
    run = await discovery_service.start_discovery(session, data.country, data.limit)
    await session.commit()
    return DiscoveryRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=DiscoveryRunRead)
async def get_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await discovery_service.get_discovery_run(session, run_id)
    if not run:
        raise NotFound(f"Discovery run {run_id} not found")
    return DiscoveryRunRead.model_validate(run)
