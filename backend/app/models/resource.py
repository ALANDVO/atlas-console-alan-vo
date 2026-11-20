from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ResourceType(str, PyEnum):
    FILE = "file"
    DIRECTORY = "directory"
    NOTE = "note"
    IMAGE = "image"


class ResourceStatus(str, PyEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[ResourceType] = mapped_column(
        SQLEnum(ResourceType), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=True)
    tags: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ResourceStatus] = mapped_column(
        SQLEnum(ResourceStatus), default=ResourceStatus.ACTIVE, nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, name={self.name}, type={self.type})>"
