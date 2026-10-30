import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid7


class ActivityKind(enum.StrEnum):
    TOUCH = "touch"
    REPLY = "reply"
    NOTE = "note"
    STAGE_CHANGE = "stage_change"
    BLOCKER = "blocker"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[ActivityKind] = mapped_column(
        Enum(ActivityKind, name="activity_kind", create_constraint=True, native_enum=True),
        nullable=False,
    )
    channel: Mapped[str | None] = mapped_column(String(50))
    body: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    partner = relationship("Partner", back_populates="activities")
