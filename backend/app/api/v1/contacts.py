from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import NotFound
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate

router = APIRouter(tags=["contacts"])


@router.get("/partners/{partner_id}/contacts", response_model=list[ContactRead])
async def list_contacts(
    partner_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Contact).where(Contact.partner_id == partner_id))
    return [ContactRead.model_validate(c) for c in result.scalars().all()]


@router.post("/partners/{partner_id}/contacts", response_model=ContactRead, status_code=201)
async def create_contact(
    partner_id: uuid.UUID,
    data: ContactCreate,
    session: AsyncSession = Depends(get_session),
):
    contact = Contact(partner_id=partner_id, **data.model_dump())
    session.add(contact)
    await session.commit()
    return ContactRead.model_validate(contact)


@router.patch("/contacts/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFound(f"Contact {contact_id} not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    await session.commit()
    return ContactRead.model_validate(contact)


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFound(f"Contact {contact_id} not found")
    await session.delete(contact)
    await session.commit()
