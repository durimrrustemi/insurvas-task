import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid_extensions import uuid7


def generate_uuid7() -> uuid.UUID:
    return uuid7()


class Base(DeclarativeBase):
    # Fetch server-side defaults (created_at/updated_at) via RETURNING on flush.
    # Without this they are expired after an UPDATE and serialising the row
    # triggers a lazy load outside the async context (MissingGreenlet).
    __mapper_args__ = {"eager_defaults": True}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
