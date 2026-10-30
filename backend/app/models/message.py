import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid7


class Channel(enum.StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"


class MessageStatus(enum.StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[Channel] = mapped_column(
        Enum(Channel, name="channel", create_constraint=True, native_enum=True),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    angle: Mapped[str | None] = mapped_column(Text)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status", create_constraint=True, native_enum=True),
        default=MessageStatus.DRAFT,
    )
    send_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    partner = relationship("Partner", back_populates="messages")
