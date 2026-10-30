from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid7


class Stage(enum.StrEnum):
    FOUND = "found"
    CONTACTED = "contacted"
    REPLIED = "replied"
    IN_TALKS = "in_talks"
    TEST_CALLS = "test_calls"
    CONTRACT_REVIEW = "contract_review"
    SIGNED = "signed"
    LOST = "lost"


class Blocker(enum.StrEnum):
    NO_RESPONSE = "no_response"
    PRICING = "pricing"
    COMPLIANCE = "compliance"
    CAPACITY = "capacity"
    WAITING_ON_THEM = "waiting_on_them"
    WAITING_ON_US = "waiting_on_us"


class PartnerType(enum.StrEnum):
    BPO = "bpo"
    VENDOR = "vendor"


class Partner(TimestampMixin, Base):
    __tablename__ = "partners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str | None] = mapped_column(String(50))
    type: Mapped[PartnerType] = mapped_column(
        Enum(PartnerType, name="partner_type", create_constraint=True, native_enum=True),
        default=PartnerType.BPO,
    )
    stage: Mapped[Stage] = mapped_column(
        Enum(Stage, name="stage", create_constraint=True, native_enum=True),
        default=Stage.FOUND,
    )
    stage_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_note: Mapped[str | None] = mapped_column(Text)
    blocker: Mapped[Blocker | None] = mapped_column(
        Enum(Blocker, name="blocker", create_constraint=True, native_enum=True),
        nullable=True,
    )
    score_total: Mapped[float | None] = mapped_column(Float)
    score_english: Mapped[float | None] = mapped_column(Float)
    score_insurance: Mapped[float | None] = mapped_column(Float)
    score_size: Mapped[float | None] = mapped_column(Float)
    score_compliance: Mapped[float | None] = mapped_column(Float)
    engagement_terms: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    contacts = relationship("Contact", back_populates="partner", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="partner", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="partner", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="partner", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="partner", cascade="all, delete-orphan")
